# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The reading of the posture findings against OWASP and CIS, the broad personal access tokens, the original of a fork and the permissions of a GitHub App. Invented names, no real calls."""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.families.posture import posture_catalogue as catalogue, posture_checks as checks, posture_engine as engine  # noqa: E402
from github_actions_monitor.families.posture.posture_checks import Unread  # noqa: E402


def get_from(answers):
    def get(endpoint):
        key = endpoint.partition("?")[0]
        if key not in answers:
            raise Unread("missing")
        if isinstance(answers[key], str):
            raise Unread(answers[key])
        return answers[key]
    return get


class Tokens(unittest.TestCase):
    def test_only_the_broad_tokens_that_still_work_are_listed(self):
        rows = [{"owner": {"login": "a"}, "token_name": "all", "repository_selection": "all", "permissions": {"repository": {"contents": "write"}}},
                {"owner": {"login": "b"}, "token_name": "one", "repository_selection": "subset", "permissions": {"repository": {"contents": "write"}}, "token_expires_at": "2030-01-01"},
                {"owner": {"login": "c"}, "token_name": "old", "repository_selection": "all", "permissions": {"repository": {"contents": "write"}}, "token_expired": True},
                {"owner": {"login": "d"}, "token_name": "org", "repository_selection": "none", "permissions": {"organization": {"members": "write"}}, "token_expires_at": "2030-01-01"}]
        found = checks.pats(get_from({"orgs/acme/personal-access-tokens": rows}), "orgs/acme", {})
        self.assertEqual([f["item"] for f in found], ["a: all", "d: org"])
        self.assertIn("no expiry", found[0]["detail"])

    def test_a_refusal_is_not_checked(self):
        found, unread = engine.read_groups(get_from({"orgs/acme/personal-access-tokens": "forbidden"}), "orgs/acme", {"pats": checks.pats}, {}, {"pats"})
        self.assertEqual((found, unread), ([], {"pats": "forbidden"}))


class Original(unittest.TestCase):
    def test_the_original_of_a_fork_is_looked_at_only_when_asked(self):
        answers = {"repos/me/app": {"fork": True, "parent": {"full_name": "them/app"}}}
        cfg = engine.settings({"posture": {"enabled": True}})
        entry = engine.check_repo(get_from(answers), "me", "app", cfg, {}, 100)
        self.assertEqual((entry["findings"], entry["skipped"]), ([], "fork"))
        entry = engine.check_repo(get_from(answers), "me", "app", dict(cfg, upstream=True), {}, 100)
        self.assertEqual([(f["check"], f["item"]) for f in entry["findings"]], [("upstream.weak", "them/app")])
        self.assertEqual(entry["checked"], ["upstream"])

    def test_a_parent_name_that_is_not_one_is_not_asked(self):
        self.assertEqual(checks.upstream(get_from({}), "repos/me/app", {"repo_info": {"parent": {"full_name": "../x"}}}), [])


class Compliance(unittest.TestCase):
    def test_nothing_read_is_never_without_findings(self):
        out = engine.compliance({"repos": {}, "org": {}})
        self.assertEqual({r["status"] for r in out["owasp"] + out["cis"]}, {"not_checked"})
        self.assertEqual(len(out["owasp"]), 10)

    def test_findings_partly_and_clean_are_told_apart(self):
        data = {"repos": {"app": {"checked": ["hooks", "branch"], "findings": [{"check": "webhook.no_secret", "item": "h"}]}}, "org": {}}
        rows = {r["id"]: r for r in engine.compliance(data)["cis"]}
        self.assertEqual(rows["2.4"]["status"], "findings")
        self.assertEqual(rows["1.1"]["status"], "partly")      # the merged changes were not read
        self.assertEqual(rows["5.1"]["status"], "not_checked")

    def test_the_markdown_has_both_standards_and_the_lesson_of_what_was_found(self):
        data = {"repos": {"app": {"checked": ["hooks"], "findings": [{"check": "webhook.no_secret", "item": "h"}]}}, "org": {}}
        with mock.patch.object(engine, "load", return_value=dict(data, history=[])):
            out = engine.report({"posture": {"enabled": True}})
        text = "\n".join(engine.markdown(out))
        for part in ("OWASP Top 10 CI/CD", "CIS Software Supply Chain", "CICD-SEC-8"):
            self.assertIn(part, text)
        self.assertEqual(len(out["learn"]), 10)

    def test_the_trend_needs_a_week_of_history(self):
        row = lambda day, errors: {"day": day, "error": errors, "warning": 0, "info": 0}
        self.assertEqual(engine.trend([row("2026-01-10", 1)])["direction"], "unknown")
        self.assertEqual(engine.trend([row("2026-01-01", 3), row("2026-01-10", 1)]), {"direction": "better", "since": "2026-01-01", "delta": -2})
        self.assertEqual(engine.trend([row("2026-01-01", 0), row("2026-01-10", 1)])["direction"], "worse")


class Matrix(unittest.TestCase):
    def test_each_group_says_which_permission_of_an_app_unlocks_it(self):
        self.assertEqual(set(catalogue.APP_PERMISSIONS), set(catalogue.PERMISSIONS))
        rows = {r["group"]: r for r in catalogue.matrix((), {"contents": "read", "secrets": "missing"})}
        self.assertEqual((rows["files"]["granted"], rows["stored"]["granted"], rows["pats"]["granted"]), ("read", "missing", "unknown"))
        self.assertEqual({r["granted"] for r in catalogue.matrix()}, {"unknown"})


if __name__ == "__main__":
    unittest.main()
