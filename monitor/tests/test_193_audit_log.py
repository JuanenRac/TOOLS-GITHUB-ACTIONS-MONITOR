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
        self.assertEqual(audit_log.verify(), {"ok": True, "entries": 4, "broken_at": None, "segments": 1, "complete": True})
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
        self.assertEqual(audit_log.verify(), {"ok": True, "entries": 3, "broken_at": None, "segments": 1, "complete": True})

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



class SeveralProcesses(unittest.TestCase):
    """The supervisor and the accounts of a container share one file: three real processes write it at the same time and the chain must stay whole."""

    SCRIPT = (
        "import sys, os\n"
        "sys.path.insert(0, os.environ['MONITOR_SRC'])\n"
        "from github_actions_monitor.security import audit_log\n"
        "who = sys.argv[1]\n"
        "for i in range(40):\n"
        "    assert audit_log.record({}, 'settings_change', user=who, target='t%d' % i) is not None\n"
    )

    def test_three_processes_on_the_same_file_keep_one_chain(self):
        import os
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "writer.py"
            script.write_text(self.SCRIPT, encoding="utf-8")
            env = {**os.environ, "MONITOR_SRC": str(HERE / "src"), "MONITOR_STATE_DIR": str(Path(tmp) / "state")}
            procs = [subprocess.Popen([sys.executable, "-I", str(script), name], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for name in ("supervisor", "acc1", "acc2")]
            outputs = [p.communicate(timeout=120) for p in procs]
            for p, (_out, err) in zip(procs, outputs):
                self.assertEqual(p.returncode, 0, err.decode("utf-8", "replace")[-500:])
            target = Path(tmp) / "state" / audit_log.FILE_NAME
            self.assertEqual(len(target.read_text(encoding="utf-8").splitlines()), 120)
            self.assertEqual(audit_log.verify(target), {"ok": True, "entries": 120, "broken_at": None, "segments": 1, "complete": True})

    def test_the_tail_is_read_from_the_end_of_a_big_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit_log.FILE = Path(tmp) / "audit_actions.jsonl"
            self.addCleanup(lambda: setattr(audit_log, "FILE", None))
            for i in range(30):
                audit_log.record({}, "settings_change", user="u", target="x" * 100 + str(i))
            old = audit_log.TAIL_BYTES
            audit_log.TAIL_BYTES = 200      # shorter than one line: the whole file is read as a last resort
            try:
                before = audit_log.read(1)[0]["hash"]
                self.assertEqual(audit_log.record({}, "settings_change", user="u", target="last")["prev"], before)
            finally:
                audit_log.TAIL_BYTES = old
            self.assertTrue(audit_log.verify()["ok"])



class Segments(Base):
    def rotate(self):
        self.write_lines = lambda n: [audit_log.record({}, "settings_change", user="u", target=f"t{i}", now=NOW + i) for i in range(n)]
        self.write_lines(3)
        self.file.replace(self.file.with_name(self.file.name + ".1"))
        audit_log._last.update(path=None, hash="")
        audit_log.record({}, "settings_change", user="u", target="after", now=NOW + 9)

    def test_the_rotated_file_is_verified_with_the_link_to_the_active_one(self):
        self.rotate()
        self.assertEqual(audit_log.verify(), {"ok": True, "entries": 4, "broken_at": None, "segments": 2, "complete": True})

    def test_a_changed_line_of_the_rotated_file_is_found(self):
        self.rotate()
        old = self.file.with_name(self.file.name + ".1")
        old.write_text(old.read_text(encoding="utf-8").replace('"t1"', '"tX"'), encoding="utf-8")
        result = audit_log.verify()
        self.assertFalse(result["ok"])
        self.assertEqual((result["segment"], result["broken_at"]), ("rotated", 2))

    def test_a_rotated_file_that_was_deleted_leaves_a_whole_but_incomplete_chain(self):
        self.rotate()
        self.file.with_name(self.file.name + ".1").unlink()
        result = audit_log.verify()
        self.assertTrue(result["ok"])
        self.assertFalse(result["complete"])

    def test_a_rotated_file_that_is_not_the_one_before_breaks_the_link(self):
        self.rotate()
        other = Path(self.tmp.name) / "other.jsonl"
        audit_log.FILE = other
        audit_log._last.update(path=None, hash="")
        audit_log.record({}, "settings_change", user="x", target="foreign", now=NOW)
        self.file.with_name(self.file.name + ".1").write_bytes(other.read_bytes())
        audit_log.FILE = self.file
        result = audit_log.verify()
        self.assertFalse(result["ok"])
        self.assertEqual((result["segment"], result["broken_at"]), ("active", 1))


class PerAccount(Base):
    def test_the_log_of_an_account_is_its_own_file_and_the_read_keeps_only_its_lines(self):
        from github_actions_monitor.accounts import accounts
        self.assertIn(("github_actions_monitor.security.audit_log", "FILE", "audit_actions.jsonl"), accounts.STATE_FILES)
        audit_log.record({}, "settings_change", user="a", account="alpha", target="one")
        audit_log.record({}, "settings_change", user="b", account="beta", target="two")
        self.assertEqual([e["account"] for e in audit_log.read(10, "alpha")], ["alpha"])
        self.assertEqual([e["account"] for e in audit_log.read(10)], ["alpha", "beta"])

    def test_two_children_of_different_accounts_never_share_the_file(self):
        import os
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "child.py"
            script.write_text("import sys\nsys.path.insert(0, sys.argv[1])\nfrom pathlib import Path\nfrom github_actions_monitor.accounts import account_child\n"
                              "from github_actions_monitor.security import audit_log\nfolder = account_child.redirect(sys.argv[2], Path(sys.argv[3]))\n"
                              "audit_log.record({}, 'settings_change', user='u', account=sys.argv[2], target='t')\nprint(audit_log.path())\n", encoding="utf-8")
            paths = []
            for name in ("alpha", "beta"):
                done = subprocess.run([sys.executable, "-I", str(script), str(HERE / "src"), name, tmp], env={**os.environ, "MONITOR_STATE_DIR": str(Path(tmp) / "shared")},
                                      capture_output=True, text=True, timeout=120)
                self.assertEqual(done.returncode, 0, done.stderr[-500:])
                paths.append(Path(done.stdout.strip().splitlines()[-1]))
            self.assertNotEqual(paths[0], paths[1])
            self.assertEqual([p.parent.name for p in paths], ["alpha", "beta"])
            for p, name in zip(paths, ("alpha", "beta")):
                self.assertEqual([json.loads(line)["account"] for line in p.read_text(encoding="utf-8").splitlines()], [name])



class FableFindings(Base):
    def test_a_viewer_never_passes_the_door_of_the_log_of_actions(self):
        self.assertEqual(auth.required_role("GET", "/api/audit-log"), "maintainer")
        self.assertEqual(auth.required_role("GET", "/api/audit-log?account=beta"), "maintainer")

    def test_switching_the_log_off_leaves_its_own_line(self):
        self.assertIsNone(audit_log.record({"audit_log": {"enabled": False}}, "settings_change", user="root", target="settings"))
        line = audit_log.record({"audit_log": {"enabled": False}}, "settings_change", user="root", target="settings", details={"settings": ["audit_log.enabled"]}, force=True)
        self.assertEqual(line["details"], {"settings": ["audit_log.enabled"]})
        self.assertEqual(len(self.lines()), 1)

    def test_a_line_that_cannot_be_written_is_counted(self):
        before = audit_log.STATS["write_failures"]
        with mock.patch.object(audit_log.private_io, "open_append", side_effect=OSError("disk full")):
            self.assertIsNone(audit_log.record({}, "settings_change", user="u", target="t"))
        self.assertEqual(audit_log.STATS["write_failures"], before + 1)
        self.assertTrue(audit_log.STATS["last_write_error_at"])

    def test_failed_changes_of_ones_own_password_do_not_fill_the_log_of_actions(self):
        for _ in range(20):
            auth._record_action("password", "viewer1", "viewer", "/api/auth/password", "denied", "invalid_credentials")
        self.assertFalse(self.file.exists())
        auth._record_action("password", "viewer1", "viewer", "/api/auth/password", "ok", "")
        self.assertEqual(len(self.lines()), 1)


if __name__ == "__main__":
    unittest.main()
