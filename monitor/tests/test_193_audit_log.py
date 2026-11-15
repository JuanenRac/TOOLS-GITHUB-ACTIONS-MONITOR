# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The log of actions: every line follows from the one before, a changed or cut line is found, no secret and no value of a setting is ever written, the chain goes on after a rotation, the switch and the role decide what is written and who reads, and the places that change something write to it."""
import inspect
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.security import audit_log, auth  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
NOW = 1_800_000_000.0


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "audit_actions.jsonl"
        audit_log.FILE = self.file
        audit_log._last.update(path=None, hash="")
        self.addCleanup(lambda: (setattr(audit_log, "FILE", None), audit_log._last.update(path=None, hash="")))

    def lines(self):
        return self.file.read_text(encoding="utf-8").splitlines()


class Chain(Base):
    def write(self, n=4):
        for i in range(n):
            audit_log.record({}, "settings_change", "root", "admin", "alpha", "settings", details={"settings": [f"a.b{i}"]}, now=NOW + i)

    def test_every_line_follows_from_the_one_before(self):
        self.write()
        self.assertEqual(audit_log.verify(), {"ok": True, "entries": 4, "broken_at": None})
        rows = [json.loads(x) for x in self.lines()]
        self.assertEqual(rows[0]["prev"], "")
        self.assertTrue(all(rows[i]["prev"] == rows[i - 1]["hash"] for i in range(1, 4)))

    def test_a_changed_line_a_cut_line_and_a_swapped_pair_are_found(self):
        self.write()
        original = self.lines()
        changed = [json.loads(x) for x in original]
        changed[1]["user"] = "somebody-else"
        self.file.write_text("\n".join(json.dumps(x) for x in changed) + "\n", encoding="utf-8")
        self.assertEqual(audit_log.verify()["broken_at"], 2)
        self.file.write_text("\n".join(original[:1] + original[2:]) + "\n", encoding="utf-8")
        self.assertEqual(audit_log.verify()["broken_at"], 2)
        self.file.write_text("\n".join([original[0], original[2], original[1], original[3]]) + "\n", encoding="utf-8")
        self.assertFalse(audit_log.verify()["ok"])
        self.file.write_text(original[0] + "\nnot json\n", encoding="utf-8")
        self.assertEqual(audit_log.verify()["broken_at"], 2)

    def test_a_restart_goes_on_with_the_same_chain(self):
        self.write(2)
        audit_log._last.update(path=None, hash="")      # a new process
        audit_log.record({}, "alert_mute", "root", "admin", "alpha", "code:ci.stuck", now=NOW + 9)
        self.assertEqual(audit_log.verify(), {"ok": True, "entries": 3, "broken_at": None})

    def test_the_chain_goes_on_in_the_new_file_after_a_rotation(self):
        self.write(2)
        with mock.patch.dict(audit_log.DEFAULTS, {"max_mb": 0}):      # past a size of zero every write rotates
            with mock.patch.object(audit_log, "settings", lambda config: {"enabled": True, "max_mb": 0, "maintainers_can_read": False}):
                audit_log.record({}, "settings_change", "root", "admin", "alpha", "settings", now=NOW + 5)
        old = self.file.with_name(self.file.name + ".1")
        self.assertTrue(old.exists())
        first = json.loads(self.lines()[0])
        self.assertEqual(first["prev"], json.loads(old.read_text(encoding="utf-8").splitlines()[-1])["hash"])
        self.assertTrue(audit_log.verify()["ok"])


class Secrets(Base):
    def test_a_key_that_looks_like_a_secret_is_dropped_and_a_token_in_a_text_is_cleaned(self):
        token = "ghp_" + "a" * 36
        audit_log.record({}, "credential_set", "root", "admin", "alpha", "credential", details={"password": "hunter2hunter2", "api_token": token, "Authorization": "Bearer abc", "note": f"used {token}", "settings": ["a.b"]})
        text = self.file.read_text(encoding="utf-8")
        for secret in ("hunter2", token, "Bearer abc"):
            self.assertNotIn(secret, text)
        entry = json.loads(text)
        self.assertEqual(entry["details"]["settings"], ["a.b"])
        self.assertNotIn("password", entry["details"])

    def test_a_long_text_is_cut_and_the_depth_is_limited(self):
        audit_log.record({}, "settings_change", "root", "admin", "alpha", "x" * 500, details={"a": {"b": {"c": {"d": {"e": "deep"}}}}, "long": "y" * 900})
        entry = json.loads(self.lines()[0])
        self.assertLessEqual(len(entry["target"]), 200)
        self.assertLessEqual(len(entry["details"]["long"]), 200)
        self.assertNotIn("deep", json.dumps(entry))

    def test_an_action_name_that_is_not_a_plain_word_is_refused(self):
        for bad in ("", "Settings", "x y", "a" * 60, "../x", None):
            self.assertIsNone(audit_log.record({}, bad, "root"), bad)
        self.assertFalse(self.file.exists())


class Switch(Base):
    def test_the_defaults_and_the_wrong_values(self):
        self.assertEqual(audit_log.settings({}), {"enabled": True, "max_mb": 10, "maintainers_can_read": False})
        self.assertEqual(audit_log.settings({"audit_log": {"enabled": "no", "max_mb": 0, "maintainers_can_read": 1}}), audit_log.DEFAULTS)

    def test_off_writes_nothing(self):
        self.assertIsNone(audit_log.record({"audit_log": {"enabled": False}}, "settings_change", "root"))
        self.assertFalse(self.file.exists())

    def test_who_reads_it(self):
        self.assertTrue(audit_log.may_read({}, "admin") and audit_log.may_read({}, ""))
        self.assertFalse(audit_log.may_read({}, "maintainer") or audit_log.may_read({}, "viewer"))
        self.assertTrue(audit_log.may_read({"audit_log": {"maintainers_can_read": True}}, "maintainer"))
        self.assertFalse(audit_log.may_read({"audit_log": {"maintainers_can_read": True}}, "viewer"))

    def test_the_settings_of_the_page_and_the_example_agree(self):
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["audit_log"], audit_log.DEFAULTS)
        keys = sorted(k for k in settings_api.FIELDS if k.startswith("audit_log."))
        self.assertEqual(keys, ["audit_log.enabled", "audit_log.maintainers_can_read", "audit_log.max_mb"])
        for key in keys:
            self.assertTrue(settings_api.check_value(key, audit_log.DEFAULTS[key.split(".")[1]])[0], key)

    def test_every_text_of_the_settings_is_in_the_eight_languages(self):
        used = {"ui.cfg_b_audit_log"} | {f"cfg.{p}.audit_log.{n}" for p in "fh" for n in ("enabled", "max_mb", "maintainers_can_read")}
        for lang in LANGS:
            keys = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(k for k in used if k not in keys), [], lang)


class Writers(Base):
    def test_a_change_of_the_access_audit_goes_to_the_log_of_actions_and_a_login_does_not(self):
        cfg = {"audit": True}
        with mock.patch.object(auth, "AUDIT_FILE", Path(self.tmp.name) / "access.jsonl"):
            auth.audit(cfg, "login", "root", "admin", "127.0.0.1", "/api/auth/login")
            auth.audit(cfg, "denied", "root", "viewer", "127.0.0.1", "/api/settings", "denied", "forbidden_role")
            self.assertFalse(self.file.exists())
            auth.audit(cfg, "user_update", "root", "admin", "127.0.0.1", "/api/auth/users/update?x=1", "ok", "")
        entry = json.loads(self.lines()[0])
        self.assertEqual((entry["action"], entry["user"], entry["target"]), ("user_update", "root", "/api/auth/users/update"))

    def test_the_places_that_change_something_call_the_log(self):
        source = inspect.getsource(actions_monitor)
        for needle in ('audit_action(self, "settings_change"', '_audit_plain("alert_mute"', '_audit_plain("alert_unmute"', 'path == "/api/audit-log"', "def audit_action"):
            self.assertIn(needle, source, needle)
        self.assertIn("/api/audit-log", actions_monitor.LITE_PATHS)

    def test_a_setting_write_keeps_only_the_names(self):
        class H:
            auth_user = {"user": "root", "role": "admin"}
        actions_monitor.audit_action(H(), "settings_change", "settings", {"settings": ["ai.provider"]})
        text = self.file.read_text(encoding="utf-8")
        self.assertIn("ai.provider", text)
        self.assertEqual(json.loads(text)["role"], "admin")
        self.assertFalse(re.search(r"sk-|ghp_|password", text))


if __name__ == "__main__":
    unittest.main()
