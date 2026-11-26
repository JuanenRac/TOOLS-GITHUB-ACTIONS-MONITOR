# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Runs one plugin of another person in a separate process (plugin_worker_child.py): empty environment, a temporary folder of its own, a deadline after which it is killed, a ceiling on what it may say, and
on Windows a Job Object (memory ceiling, no child processes, dies with the monitor). What could NOT be isolated is said in the answer, never hidden: `network_isolated` is True only when the child really
left the network."""
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

CHILD = Path(__file__).with_name("plugin_worker_child.py")
MAX_CALLS = 300


class WorkerError(RuntimeError):
    """`code`: platform, start, timeout, output, protocol, failed."""

    def __init__(self, code, message=""):
        super().__init__(message or code)
        self.code = code


def platform_family(name=None):
    name = name or sys.platform
    return "windows" if name == "win32" else "darwin" if name == "darwin" else "linux" if name.startswith("linux") else name


def clean_environment(home):
    """Nothing of the monitor travels: only what the interpreter needs to start."""
    keep = {key: os.environ[key] for key in ("SystemRoot", "SYSTEMROOT") if key in os.environ}
    return dict(keep, HOME=str(home), USERPROFILE=str(home), TMPDIR=str(home), TEMP=str(home), TMP=str(home), PYTHONIOENCODING="utf-8")


def command():
    """The interpreter itself (not the launcher of a virtual environment, which would start a second process), isolated and without site packages."""
    return [getattr(sys, "_base_executable", "") or sys.executable, "-I", "-S", "-B", str(CHILD)]


def job_object(process, memory_mb):
    """Windows: the handle of a Job Object holding the child (keep it until the child is gone), or None when it could not be made."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64), ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD), ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class Counters(ctypes.Structure):
        _fields_ = [(n, ctypes.c_uint64) for n in ("Read", "Write", "Other", "ReadBytes", "WriteBytes", "OtherBytes")]

    class Extended(ctypes.Structure):
        _fields_ = [("Basic", Basic), ("Io", Counters), ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        return None
    limits = Extended()
    limits.Basic.LimitFlags = 0x2000 | 0x100 | 0x8      # kill on close, memory per process, active processes
    limits.Basic.ActiveProcessLimit = 1
    limits.ProcessMemoryLimit = int(memory_mb) * 1024 * 1024
    if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(job, int(process._handle)):      # noqa: SLF001
        kernel.CloseHandle(job)
        return None
    return job


def close_job(job):
    if job:
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32")
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(job)


def run(folder, manifest, broker, options=None, owner="", timeout_s=20, max_output_kb=256, memory_mb=256, platforms_ok=("linux", "windows", "darwin"), now=None):
    """(answer of run(ctx), {"network_isolated": bool, "job_object": bool}). `broker(method, args)` answers what the plugin asks and raises to refuse it."""
    if platform_family() not in platforms_ok:
        raise WorkerError("platform", "plugins of other people are not loaded on this system (plugins.worker.platforms_ok)")
    deadline = time.monotonic() + timeout_s
    budget = max_output_kb * 1024
    with tempfile.TemporaryDirectory(prefix="plugin_home_", ignore_cleanup_errors=True) as home:
        try:
            process = subprocess.Popen(command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=home, env=clean_environment(home), close_fds=True,
                                       creationflags=0x08000000 if os.name == "nt" else 0, start_new_session=os.name != "nt")
        except OSError as error:
            raise WorkerError("start", str(error)[:100]) from None
        job = None
        lines = queue.Queue()

        def reader():
            total = 0
            while True:
                line = process.stdout.readline(budget + 1)
                total += len(line)
                if not line:
                    break
                if total > budget:
                    lines.put(None)
                    break
                lines.put(line)
            lines.put(b"")

        def send(message):
            try:
                process.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
                process.stdin.flush()
            except (OSError, ValueError):
                raise WorkerError("protocol", "the plugin closed its input") from None

        def receive():
            try:
                line = lines.get(timeout=max(0.0, deadline - time.monotonic()))
            except queue.Empty:
                raise WorkerError("timeout", "the plugin did not finish in time") from None
            if line is None:
                raise WorkerError("output", "the plugin said more than allowed")
            if not line:
                raise WorkerError("protocol", "the plugin ended without an answer")
            try:
                message = json.loads(line.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise WorkerError("protocol", "the plugin said something that is not a message") from None
            if not isinstance(message, dict):
                raise WorkerError("protocol")
            return message

        try:
            job = job_object(process, memory_mb)      # before the child is told what to load: it waits for its first line
            threading.Thread(target=reader, daemon=True, name="plugin-reader").start()
            send({"folder": str(folder), "entry": manifest["entry"], "owner": owner, "options": options or {}, "now": time.time() if now is None else now, "memory_mb": memory_mb, "timeout_s": timeout_s})
            ready = receive()
            if ready.get("ready") is not True:
                raise WorkerError("protocol")
            isolation = {"network_isolated": ready.get("network_isolated") is True, "job_object": job is not None}
            for _count in range(MAX_CALLS):
                message = receive()
                if "result" in message:
                    return message["result"], isolation
                if "failed" in message:
                    raise WorkerError("failed", str(message["failed"])[:200])
                try:
                    send({"value": broker(str(message.get("call")), list(message.get("args") or []))})
                except WorkerError:
                    raise
                except Exception as error:   # noqa: BLE001 - a refused or failed read is told to the plugin
                    send({"error": str(error)[:200]})
            raise WorkerError("output", "the plugin asked too many times")
        finally:
            if process.poll() is None:
                process.kill()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            for stream in (process.stdin, process.stdout):
                try:
                    stream.close()
                except OSError:
                    pass
            close_job(job)
