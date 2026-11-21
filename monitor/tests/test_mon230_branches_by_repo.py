# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Branches to watch for ONE repository (ci.branches_by_repo, `owner/repo=pattern`) and the count of the failures on branches that nobody asked to watch. Synthetic runs only."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import redrule  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400


def stamp(days_ago, hour=0):
    import datetime
    return datetime.datetime.fromtimestamp(NOW - days_ago * DAY + hour * 3600, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(n, conclusion="failure", branch="main", event="push", path="ci.yml", days=1, repo="acme/api"):
    return {"repo": repo, "id": n, "name": path, "path": path, "branch": branch, "event": event, "fork": False, "status": "completed", "conclusion": conclusion,
            "started": stamp(days, n % 20), "url": f"https://example.invalid/runs/{n}", "sha": "abc1234"}


class BranchesByRepository(unittest.TestCase):
    def setUp(self):
        redrule.configure({})

    def tearDown(self):
        redrule.configure({})

    def rows(self, runs_by_repo):
        return redrule.red_workflows(runs_by_repo, {r: "main" for r in runs_by_repo}, now=NOW)[0]

    def test_a_pattern_of_one_repository_does_not_watch_the_others(self):
        redrule.configure({"ci": {"branches_by_repo": ["acme/api=release-*"]}})
        rows = self.rows({"acme/api": [run(1, branch="release-2")], "acme/web": [run(2, branch="release-2", repo="acme/web")]})
        self.assertEqual([(r["repo"], r["origin"]) for r in rows], [("acme/api", "maintenance")])

    def test_the_repository_is_matched_without_regard_to_case_and_adds_to_the_global_patterns(self):
        redrule.configure({"ci": {"extra_branches": ["lts-*"], "branches_by_repo": ["Acme/API=release-*"]}})
        rows = self.rows({"acme/api": [run(1, branch="release-2"), run(2, branch="lts-1", path="b.yml")]})
        self.assertEqual(sorted(r["branch"] for r in rows), ["lts-1", "release-2"])

    def test_bad_entries_are_ignored_and_nothing_is_watched_by_default(self):
        redrule.configure({"ci": {"branches_by_repo": ["no-equals", "=x", "acme/api=", 7, None]}})
        self.assertEqual(redrule.POLICY["repo_branches"], {})
        redrule.configure({"ci": {"branches_by_repo": "acme/api=release-*"}})
        self.assertEqual(redrule.POLICY["repo_branches"], {})
        redrule.configure({})
        self.assertEqual(self.rows({"acme/api": [run(1, branch="release-2")]}), [])


class WhatIsLeftOut(unittest.TestCase):
    def setUp(self):
        redrule.configure({})

    tearDown = setUp

    def states(self, runs):
        return redrule.states({"acme/api": runs}, {"acme/api": "main"}, now=NOW)

    def test_a_failure_on_an_unwatched_branch_is_counted_not_red(self):
        runs = [run(1, branch="release-2"), run(2, branch="main", conclusion="success")]
        self.assertEqual(self.rows_red(runs), [])
        ignored = self.states(runs)["ignored"]
        self.assertEqual([(r["repo"], r["branch"]) for r in ignored], [("acme/api", "release-2")])

    def rows_red(self, runs):
        return redrule.red_workflows({"acme/api": runs}, {"acme/api": "main"}, now=NOW)[0]

    def test_a_watched_branch_is_not_counted_as_left_out(self):
        redrule.configure({"ci": {"branches_by_repo": ["acme/api=release-*"]}})
        self.assertEqual(self.states([run(1, branch="release-2")])["ignored"], [])

    def test_pull_requests_and_green_runs_and_old_failures_do_not_count(self):
        runs = [run(1, branch="feature", event="pull_request"), run(2, branch="feature-b", conclusion="success"), run(3, branch="old", days=200, path="c.yml"), run(4, branch="cancelled", conclusion="cancelled")]
        redrule.configure({"ci": {"inactive_days": 90}})
        self.assertEqual(self.states(runs)["ignored"], [])

    def test_a_branch_that_went_green_again_is_not_counted(self):
        runs = [run(1, branch="release-2", days=3), run(2, branch="release-2", conclusion="success", days=1)]
        self.assertEqual(self.states(runs)["ignored"], [])


class TheSettingIsKnown(unittest.TestCase):
    def test_the_schema_accepts_owner_repo_equals_pattern_and_refuses_the_rest(self):
        self.assertIn("ci.branches_by_repo", settings_api.META)
        self.assertTrue(settings_api.BYREPO_BRANCH_RE.match("my-org/api=release-*"))
        for bad in ("api=release-*", "my-org/api", "my-org/api=", "my-org/api=a b", "x/y=../z "):
            self.assertFalse(settings_api.BYREPO_BRANCH_RE.match(bad), bad)

    def test_texts_in_eight_languages(self):
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("cfg.f.ci.branches_by_repo", "cfg.h.ci.branches_by_repo", "ui.n_ignored"):
                self.assertTrue(texts.get(key), (lang, key))
            self.assertIn("{n}", texts["ui.n_ignored"], lang)


if __name__ == "__main__":
    unittest.main()
