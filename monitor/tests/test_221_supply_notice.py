# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The window that announces a newer version (on by default, silent on wall screens, a version can be dismissed) and the commands `keyring` and `verify-release`."""
import argparse
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import families  # noqa: E402
from github_actions_monitor.app import actions_monitor, updatecheck  # noqa: E402
from github_actions_monitor.cli import monitor_cli  # noqa: E402
from github_actions_monitor.families.supply import commands, notice  # noqa: E402
from github_actions_monitor.util import paths  # noqa: E402

PUBLIC = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"      # the public key of the first test vector of RFC 8032
INFO = {"newer": True, "latest": "9.0.0", "current": "2.2.0", "notes": {"en": "New", "es": "Nuevo"}, "url": "u", "changelog": "c", "command": "x", "dismissed": False}


class Notice(unittest.TestCase):
    def test_it_is_on_by_default_and_can_be_switched_off(self):
        self.assertTrue(actions_monitor.DEFAULTS["updates"]["notify_window"])
        self.assertTrue(notice.enabled({}))
        self.assertTrue(notice.enabled({"updates": {"check": True}}))
        self.assertFalse(notice.enabled({"updates": {"notify_window": False}}))

    def test_it_shows_the_summary_in_the_language_only_when_there_is_something_to_say(self):
        shown = notice.answer(INFO, {}, "es")
        self.assertEqual((shown["show"], shown["version"], shown["notes"]), (True, "9.0.0", "Nuevo"))
        self.assertEqual(notice.answer(INFO, {}, "ja")["notes"], "New")
        for info, config in ((dict(INFO, newer=False), {}), (dict(INFO, dismissed=True), {}), (INFO, {"updates": {"notify_window": False}})):
            self.assertEqual(notice.answer(info, config, "en"), {"show": False})

    def test_dismissing_keeps_the_version_and_refuses_anything_else(self):
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.object(actions_monitor, "state_dir", lambda: Path(folder)):
                ask = lambda body: notice.dismiss(families.Request("POST", "/api/supply/update-dismiss", {}, body, "", {}))
                self.assertEqual(ask({"version": "9.0.0"}), {"ok": True})
                for bad in ({}, {"version": 3}, {"version": "nightly"}, {"version": "9" * 80}):
                    self.assertEqual(ask(bad)[0], 400, bad)
            self.assertEqual(updatecheck._load(Path(folder) / "update_check.json")["dismissed"], "9.0.0")

    def test_the_page_script_is_silent_on_wall_screens_and_shows_the_text_as_text(self):
        script = (families.FOLDER / "supply" / "page.js").read_text(encoding="utf-8")
        self.assertIn('classList.contains("kiosk")', script)
        self.assertIn('classList.contains("allmode")', script)
        self.assertNotIn("innerHTML", script)
        self.assertIn('showTab("upd")', script)


class Commands(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "keyring.json"
        patch = mock.patch.object(commands, "keyring_file", lambda: self.file)
        patch.start()
        self.addCleanup(patch.stop)

    def run_keyring(self, action, **options):
        args = dict(key_id="", public_key="", key_scope="", expires="", document="")
        args.update(options)
        return commands.keyring_command({"action": action, "args": argparse.Namespace(**args)})

    def test_the_commands_exist_and_the_keyring_file_is_part_of_the_configuration(self):
        for name in ("keyring", "verify-release"):
            self.assertIn(name, monitor_cli.COMMANDS)
        self.assertEqual(paths.kind_of("keyring.json"), "config")

    def test_add_list_revoke_and_the_release_key_stays(self):
        self.assertEqual(self.run_keyring("add")[2], commands.USAGE)
        self.assertEqual(self.run_keyring("add", key_id="mine", public_key=PUBLIC, key_scope="release")[2], commands.USAGE)
        self.assertEqual(self.run_keyring("add", key_id="mine", public_key=PUBLIC, key_scope="plugins")[2], commands.OK)
        payload, lines, code = self.run_keyring("list")
        self.assertEqual(code, commands.OK)
        self.assertEqual([(k["id"], k["builtin"]) for k in payload["keys"]], [("monitor-release-1", True), ("mine", False)])
        self.assertEqual(len(lines), 2)
        self.assertEqual(self.run_keyring("revoke", key_id="mine")[2], commands.OK)
        self.assertEqual(self.run_keyring("revoke", key_id="monitor-release-1")[2], commands.USAGE)

    def test_a_folder_without_signature_is_not_a_release(self):
        ctx = {"args": argparse.Namespace(folder="")}
        self.assertEqual(commands.verify_release_command(ctx)[2], commands.USAGE)
        ctx = {"args": argparse.Namespace(folder=self.tmp.name)}
        report, lines, code = commands.verify_release_command(ctx)
        self.assertEqual((report["ok"], report["signature"], code), (False, "absent", commands.DEGRADED))
        document = Path(self.tmp.name) / "a.txt"
        document.write_text("x", encoding="utf-8")
        self.assertEqual(self.run_keyring("verify", document=str(document))[0]["result"], "absent")


if __name__ == "__main__":
    unittest.main()
