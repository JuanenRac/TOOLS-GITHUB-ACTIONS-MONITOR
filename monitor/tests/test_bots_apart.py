# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Bots apart from people: the kind of account is what GitHub says (type Bot), never a guess from the name. Synthetic pull requests and runs, no network."""
import unittest
from datetime import datetime, timezone

import _testenv  # noqa: F401
from github_actions_monitor.app import settings_api as sa  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402

NOW = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)


def pr(login, typename, number, title="Change"):
    return {"number": number, "title": title, "url": f"https://x/{number}", "author": {"login": login, "__typename": typename}, "createdAt": "2026-11-01T00:00:00Z",
            "isDraft": False, "mergeable": "MERGEABLE", "files": {"nodes": [{"path": "src/a.py"}]}}


PRS = [pr("octocat", "User", 1), pr("release-helper", "Bot", 2), pr("dependabot[bot]", "Bot", 3, "Bump x from 1 to 2"), pr("bot-lover", "User", 4)]


def snapshot(**cfg):
    info = {"R": {"branch": "main", "pushed": None, "release": None, "vuln_total": 0, "vuln_sev": {}, "rulesets": [], "label_dependencies": True, "files": {}, "prs": PRS}}
    inp = {"now": NOW, "today": "2026-11-20", "cfg": {**sl.DEFAULTS, **cfg}, "repos": ["R"], "eco": {"R": "main"}, "repo_info": info, "alerts": {}, "perms": {}, "runs": {"R": []},
           "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}}, "history": {"days": {}}, "unreleased": {}, "targets": {}, "errors": {}, "loading": "", "audits": None}
    return sl.compute_snapshot(inp)


class BotsApart(unittest.TestCase):
    def test_the_kind_comes_from_github(self):
        prs = {p["number"]: sl.classify_pr("R", p, NOW)["bot"] for p in PRS}
        self.assertEqual(prs, {1: False, 2: True, 3: True, 4: False})      # "bot-lover" is a person and "release-helper" is a bot, whatever their names say
        self.assertFalse(sl.classify_pr("R", {"number": 9, "title": "t", "author": {"login": "x"}}, NOW)["bot"])      # an answer without the kind is not a bot

    def test_the_default_changes_nothing(self):
        a4 = snapshot()["a4"]
        self.assertEqual((a4["other"], a4["other_bots"], [p["number"] for p in a4["dependabot"]]), (3, 1, [3]))
        self.assertFalse(sl.DEFAULTS["bots_apart"])

    def test_bots_apart_counts_them_apart(self):
        a4 = snapshot(bots_apart=True)["a4"]
        self.assertEqual((a4["other"], a4["other_bots"]), (2, 1))

    def test_old_pull_requests_waiting_for_a_person(self):
        def rows(**cfg):
            sections = {s["key"]: s["rows"] for s in snapshot(**cfg)["a10"]["sections"]}
            return sorted(r[1] for r in sections["pr_human"])
        self.assertEqual(rows(), ["#1", "#2", "#4"])
        self.assertEqual(rows(bots_apart=True), ["#1", "#4"])

    def test_the_graphql_question_asks_for_the_kind_of_account(self):
        self.assertIn("author{login __typename}", sl.repo_query(["README.md"]))

    def test_the_setting_is_on_the_page(self):
        self.assertEqual(sa.FIELDS["sentinel.bots_apart"][0], "sentinel")
        self.assertTrue(sa.check_value("sentinel.bots_apart", True)[0])
        self.assertFalse(sa.check_value("sentinel.bots_apart", "yes")[0])


if __name__ == "__main__":
    unittest.main()
