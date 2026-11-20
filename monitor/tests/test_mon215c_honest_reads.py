# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A refusal of GitHub to an action says why (no permission, no access to a private repository, wrong state, invalid inputs), the banner of errors groups the repositories that share one error, and the
audit of accesses rotates and appends under the lock of the operating system."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.integrations import ghactions  # noqa: E402
from github_actions_monitor.security import auth  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
CONFIG = {"github_actions": {"enabled": True, "allowed": ["rerun_failed", "cancel"], "require_reason": False, "preflight": False, "writer_lock": False}}


class ContextualErrors(unittest.TestCase):
    def refuse(self, text):
        def run_gh(args, timeout=40):
            if args[:2] == ["api", "-i"]:
                return 0, "HTTP/2 200\n\n{}", ""
            return 1, "", text
        plan, _ = ghactions.plan(CONFIG, "owner", "cancel", "repo", 5)
        return ghactions.execute(CONFIG, plan["id"], run_gh, Path(tempfile.mkdtemp()) / "log.jsonl")

    def test_each_refusal_has_its_reason(self):
        for code, reason in (("403", "forbidden"), ("404", "not_found"), ("405", "method"), ("409", "conflict"), ("422", "invalid")):
            result = self.refuse(f"gh: Resource not accessible (HTTP {code})")
            self.assertEqual((result["status"], result["reason"]), ("refused", reason), code)

    def test_an_error_without_a_known_code_has_no_reason(self):
        result = self.refuse("gh: could not resolve host")
        self.assertEqual(result["status"], "error")
        self.assertNotIn("reason", result)
        self.assertEqual(ghactions.reason_of("HTTP 4040 and 14030"), "", "a code inside a longer number is not a code")

    def test_the_page_and_the_eight_languages_explain_every_reason(self):
        self.assertIn('T("ui.adv_reason_"+j.reason)', PAGE)
        for reason in ghactions.REASONS.values():
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, "ui.adv_reason_" + reason), "ui.adv_reason_" + reason, (lang, reason))


class GroupedBanner(unittest.TestCase):
    def test_the_same_error_in_many_repositories_is_one_alert(self):
        self.assertIn("const by=new Map()", PAGE)
        self.assertIn('T("ui.a_nodata_group"', PAGE)
        self.assertIn("by.size>3", PAGE)
        for lang in i18n.LANGS:
            self.assertIn("{n}", i18n.tl(lang, "ui.a_nodata_group"), lang)


class AuditUnderTheLock(unittest.TestCase):
    def test_rotation_and_append_happen_inside_the_os_lock(self):
        folder = Path(tempfile.mkdtemp())
        target = folder / "auth_audit.jsonl"
        target.write_text("x" * 2000 + "\n", encoding="utf-8")
        events = []
        real_lock = auth.locks.os_lock
        real_replace = auth.os.replace

        class Spy:
            def __init__(self, path, timeout=10.0):
                self.inner = real_lock(path, timeout)

            def __enter__(self):
                events.append("lock")
                return self.inner.__enter__()

            def __exit__(self, *exc):
                events.append("unlock")
                return self.inner.__exit__(*exc)

        def replace(a, b):
            events.append("replace")
            return real_replace(a, b)

        with mock.patch.object(auth, "AUDIT_FILE", target), mock.patch.object(auth, "AUDIT_MAX_BYTES", 1000), mock.patch.object(auth.locks, "os_lock", Spy), mock.patch.object(auth.os, "replace", replace):
            auth.audit({"audit": True}, "login", "root", "admin", "127.0.0.1", "/api/login", "ok", "")
        self.assertEqual(events, ["lock", "replace", "unlock"])
        self.assertTrue((folder / "auth_audit.jsonl.1").exists())
        self.assertEqual(len(target.read_text(encoding="utf-8").splitlines()), 1)

    def test_a_lock_that_cannot_be_taken_never_stops_the_request(self):
        target = Path(tempfile.mkdtemp()) / "auth_audit.jsonl"
        with mock.patch.object(auth, "AUDIT_FILE", target), mock.patch.object(auth.locks, "os_lock", side_effect=TimeoutError("busy")):
            auth.audit({"audit": True}, "login", "root", "admin", "127.0.0.1", "/api/login", "ok", "")


if __name__ == "__main__":
    unittest.main()
