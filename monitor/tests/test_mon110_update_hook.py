# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The hook that lets a test point the updater of the page at a local zip instead of GitHub (MONITOR_TEST_HOOKS=1 plus MONITOR_TEST_UPDATE_ZIP), and the way the page's own call hands that zip to the
process that applies it. Then a real second process (the command line of the updater, the same one the page starts) applies the zip to an installation and goes back with the rollback: the
version, the files and the data come back as they were. No hook, no change; and the zip is checked like any other (a damaged one is refused)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_66_updater_engine as base  # noqa: E402
from github_actions_monitor.ops import updates  # noqa: E402

mu = base.mu
TOOL = HERE / "tools" / "monitor_updater.py"


def free_port():
    import socket
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def own_config():
    """The configuration of the test installation, on a port of its own (a monitor of the person may be running on 8765)."""
    cfg = base.config_from_defaults("2.0.8")
    cfg["ports"] = {"complete": free_port(), "lite": free_port()}
    return cfg


def clean_env():
    """The environment of the child without the MONITOR_* folders the test suite points at (the child must read the folders of the test installation, as a person's updater does)."""
    return {k: v for k, v in os.environ.items() if not k.startswith("MONITOR_")}


def run_tool(*args):
    done = subprocess.run([sys.executable, "-I", str(TOOL), *args], capture_output=True, text=True, timeout=240, env=clean_env(), creationflags=0x08000000 if os.name == "nt" else 0)
    return done.returncode, done.stdout + done.stderr


class Hook(unittest.TestCase):
    def test_both_variables_and_an_existing_file_are_needed(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = base.build_zip(Path(tmp) / "m.zip", "2.9.9")
            self.assertEqual(updates.test_zip({}), None)
            self.assertEqual(updates.test_zip({"MONITOR_TEST_UPDATE_ZIP": str(zip_path)}), None)
            self.assertEqual(updates.test_zip({"MONITOR_TEST_HOOKS": "1"}), None)
            self.assertEqual(updates.test_zip({"MONITOR_TEST_HOOKS": "1", "MONITOR_TEST_UPDATE_ZIP": str(Path(tmp) / "none.zip")}), None)
            self.assertEqual(updates.test_zip({"MONITOR_TEST_HOOKS": "yes", "MONITOR_TEST_UPDATE_ZIP": str(zip_path)}), None)
            self.assertEqual(updates.test_zip({"MONITOR_TEST_HOOKS": "1", "MONITOR_TEST_UPDATE_ZIP": str(zip_path)}), str(zip_path))

    def test_the_updater_of_the_page_reads_the_zip_and_hands_it_to_the_process_that_applies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = base.make_install(Path(tmp) / "inst", "2.0.8", cfg=own_config())
            zip_path = base.build_zip(Path(tmp) / "m.zip", "2.9.9")
            env = {"MONITOR_TEST_HOOKS": "1", "MONITOR_TEST_UPDATE_ZIP": str(zip_path)}
            spawned = []
            with mock.patch.object(updates, "ROOT", root), mock.patch.dict(os.environ, env), mock.patch.object(updates, "_spawn", lambda args, up: spawned.append(args)), \
                    mock.patch.object(updates, "reason_blocked", lambda *a, **k: ""), mock.patch.object(updates, "cooldown_left", lambda *a, **k: 0):
                mod, up = updates.updater()
                self.assertEqual(up.source.kind, "zip")
                try:
                    answer = updates.apply("latest", "conservative", True, "complete", "en")
                finally:
                    up.cleanup()
            self.assertTrue(answer["started"])
            self.assertEqual(answer["to"], "2.9.9")
            self.assertIn("--zip", spawned[0])
            self.assertEqual(spawned[0][spawned[0].index("--zip") + 1], str(zip_path))

    def test_without_the_hook_the_source_is_github(self):
        with mock.patch.dict(os.environ, {"MONITOR_TEST_HOOKS": "", "MONITOR_TEST_UPDATE_ZIP": ""}):
            mod, up = updates.updater()
            self.assertEqual(up.source.kind, "github")


STUB = """import http.server, json, os, sys
from pathlib import Path
from github_actions_monitor.tool_version import TOOL_VERSION
port = int(sys.argv[sys.argv.index("--port") + 1])


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"ok": True, "version": TOOL_VERSION}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


Path(os.environ["STUB_PID_FILE"]).write_text(str(os.getpid()))
server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
server.daemon_threads = True
server.serve_forever()
"""


def stub_files():
    """A monitor reduced to what the updater looks at: it answers /api/health with the version of the files it started from."""
    return {"src/github_actions_monitor/__main__.py": STUB.encode()}


def stop_pid_file(pid_file):
    """Stops the process a stub monitor wrote its number to (it was started by the updater, not by the test)."""
    try:
        pid = int(Path(pid_file).read_text())
    except (OSError, ValueError):
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, creationflags=0x08000000)
    else:
        import signal
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass


def reap(proc):
    if proc.poll() is None:
        proc.kill()
    proc.wait(timeout=20)


def health_version(port, wait=20):
    import time
    import urllib.request
    end = time.time() + wait
    while time.time() < end:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as reply:
                return json.loads(reply.read())["version"]
        except (OSError, ValueError, KeyError):
            time.sleep(0.3)
    return None


class Restart(unittest.TestCase):
    """The part after the files: --start brings the new version up and checks /api/health, and --handover waits for the monitor that asked for the update to stop. Both with a real second process."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pid_file = Path(self.tmp.name) / "stub.pid"
        self.addCleanup(stop_pid_file, self.pid_file)
        self.cfg = own_config()
        self.root = base.make_install(Path(self.tmp.name) / "inst", "2.0.8", cfg=self.cfg)
        base.write_tree(self.root, stub_files())
        self.zip = base.build_zip(Path(self.tmp.name) / "m.zip", "2.9.9", extra=stub_files())
        self.env = dict(clean_env(), STUB_PID_FILE=str(self.pid_file))

    def spawn(self, *more):
        return subprocess.Popen([sys.executable, "-I", str(TOOL), "apply", "--dir", str(self.root), "--to", "2.9.9", "--zip", str(self.zip), "--yes", "--backups", str(Path(self.tmp.name) / "backups"), "--json", *more],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=self.env, creationflags=0x08000000 if os.name == "nt" else 0)

    def finish(self, proc):
        out, _ = proc.communicate(timeout=240)
        return proc.returncode, out

    def apply(self, *more):
        return self.finish(self.spawn(*more))

    def shown(self, out):
        """The whole answer when it is short, its two ends when it is long (a failure must say why)."""
        return out if len(out) < 4000 else out[:1500] + " ... " + out[-2500:]

    def test_start_brings_up_the_new_version_and_checks_its_health(self):
        code, out = self.apply("--start")
        self.assertEqual(code, 0, self.shown(out))
        self.assertEqual(health_version(self.cfg["ports"]["complete"]), "2.9.9")

    def test_handover_waits_for_the_running_monitor_to_stop_then_starts_the_new_one(self):
        import time
        old = subprocess.Popen([sys.executable, "-m", "github_actions_monitor", "--port", str(self.cfg["ports"]["complete"])], cwd=str(self.root), env=dict(self.env, PYTHONPATH=str(self.root / "src")),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000 if os.name == "nt" else 0)
        self.addCleanup(reap, old)
        self.assertEqual(health_version(self.cfg["ports"]["complete"]), "2.0.8")
        status = Path(self.tmp.name) / "status.json"
        proc = self.spawn("--start", "--handover", "--status-file", str(status))
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        end = time.time() + 60
        while not status.is_file() and proc.poll() is None and time.time() < end:      # the updater is alive: now the monitor that asked for the update stops itself
            time.sleep(0.2)
        old.kill()
        code, out = self.finish(proc)
        self.assertEqual(code, 0, self.shown(out))
        self.assertEqual(health_version(self.cfg["ports"]["complete"]), "2.9.9")

    def test_a_running_monitor_blocks_the_update_when_no_handover_is_asked(self):
        old = subprocess.Popen([sys.executable, "-m", "github_actions_monitor", "--port", str(self.cfg["ports"]["complete"])], cwd=str(self.root), env=dict(self.env, PYTHONPATH=str(self.root / "src")),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000 if os.name == "nt" else 0)
        self.addCleanup(reap, old)
        self.assertEqual(health_version(self.cfg["ports"]["complete"]), "2.0.8")
        before = base.tree_hash(self.root)
        code, out = self.apply()
        self.assertEqual(code, 3, self.shown(out))
        self.assertEqual(base.tree_hash(self.root), before)


class TwoProcesses(unittest.TestCase):
    def test_a_real_process_applies_the_zip_and_a_second_one_goes_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = base.make_install(Path(tmp) / "inst", "2.0.8", cfg=own_config())
            backups = Path(tmp) / "backups"
            zip_path = base.build_zip(Path(tmp) / "m.zip", "2.9.9")
            before = base.tree_hash(root)
            code, out = run_tool("apply", "--dir", str(root), "--to", "2.9.9", "--zip", str(zip_path), "--yes", "--backups", str(backups), "--json")
            self.assertEqual(code, 0, out[-1500:])
            self.assertEqual(mu.read_tool_version(root), "2.9.9")
            code, out = run_tool("rollback", "--dir", str(root), "--yes", "--backups", str(backups), "--json")
            self.assertEqual(code, 0, out[-1500:])
            self.assertEqual(mu.read_tool_version(root), "2.0.8")
            self.assertEqual(base.tree_hash(root), before)

    def test_a_damaged_zip_is_refused_and_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = base.make_install(Path(tmp) / "inst", "2.0.8", cfg=own_config())
            bad = Path(tmp) / "bad.zip"
            bad.write_bytes(b"not a zip")
            before = base.tree_hash(root)
            code, out = run_tool("apply", "--dir", str(root), "--to", "2.9.9", "--zip", str(bad), "--yes", "--backups", str(Path(tmp) / "b"), "--json")
            self.assertNotEqual(code, 0)
            self.assertEqual(base.tree_hash(root), before)


if __name__ == "__main__":
    unittest.main()
