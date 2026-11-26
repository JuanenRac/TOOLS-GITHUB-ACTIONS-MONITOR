# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The separate process in which a plugin of another person runs. It is started with `python -I -S` and an empty environment, and talks to the monitor with one JSON object per line: it never receives a
token; every read of GitHub is asked to the monitor, which checks it. It uses only the standard library (it cannot import the monitor)."""
import importlib.util
import json
import os
import sys


def isolate_network():
    """True when this process is now without any network: on Linux, a new user and network namespace (refused by some systems). Nothing of the kind exists here for Windows or macOS."""
    if not sys.platform.startswith("linux"):
        return False
    try:
        import ctypes
        libc = ctypes.CDLL(None, use_errno=True)
        return libc.unshare(0x10000000 | 0x40000000) == 0      # CLONE_NEWUSER | CLONE_NEWNET
    except (OSError, AttributeError):
        return False


def limit_resources(memory_mb, seconds):
    try:
        import resource
    except ImportError:      # Windows: the monitor puts this process in a Job Object instead
        return
    for kind, value in ((resource.RLIMIT_CPU, int(seconds) + 1), (getattr(resource, "RLIMIT_AS", None), int(memory_mb) * 1024 * 1024), (resource.RLIMIT_CORE, 0), (resource.RLIMIT_FSIZE, 1 << 20)):
        if kind is None:
            continue
        try:
            resource.setrlimit(kind, (value, value))
        except (OSError, ValueError):
            pass


class Context:
    """The same ctx the official plugins receive, each method answered by the monitor."""

    def __init__(self, start, ask):
        self._ask = ask
        self.owner = start.get("owner", "")
        self.now = start.get("now", 0)
        self.options = start.get("options", {})

    def repos(self):
        return self._ask("repos", [])

    def get(self, path):
        return self._ask("get", [path])

    def discussions(self):
        return self._ask("discussions", [])


def main():
    channel_in, channel_out = sys.stdin, os.fdopen(os.dup(1), "w", encoding="utf-8", newline="\n")
    os.dup2(2, 1)                      # what the plugin prints goes to the error output, never into the protocol
    sys.stdout = sys.stderr

    def send(message):
        channel_out.write(json.dumps(message) + "\n")
        channel_out.flush()

    def receive():
        line = channel_in.readline()
        if not line:
            raise SystemExit(3)
        return json.loads(line)

    start = receive()
    limit_resources(start.get("memory_mb", 256), start.get("timeout_s", 20))
    send({"ready": True, "network_isolated": isolate_network()})

    def ask(method, args):
        send({"call": method, "args": args})
        answer = receive()
        if "error" in answer:
            raise RuntimeError(answer["error"])
        return answer["value"]

    try:
        folder = start["folder"]
        sys.path.insert(0, folder)
        spec = importlib.util.spec_from_file_location("plugin_entry", os.path.join(folder, start["entry"]))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        send({"result": module.run(Context(start, ask))})
    except BaseException as error:   # noqa: BLE001 - whatever the plugin raises is told to the monitor
        send({"failed": f"{type(error).__name__}: {error}"[:200]})


if __name__ == "__main__":
    main()
