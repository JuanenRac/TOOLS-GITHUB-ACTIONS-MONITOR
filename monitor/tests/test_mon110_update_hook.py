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


def run_tool(*args):
    done = subprocess.run([sys.executable, "-I", str(TOOL), *args], capture_output=True, text=True, timeout=240, env={**os.environ, "MONITOR_TEST_HOOKS": ""}, creationflags=0x08000000 if os.name == "nt" else 0)
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


def port_busy(port=8765):
    import socket
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


@unittest.skipIf(port_busy(), "a monitor is running on port 8765 of this computer: the updater refuses to work on top of it (the CI has the port free)")
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
