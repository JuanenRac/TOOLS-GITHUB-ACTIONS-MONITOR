# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""When the allowance of GitHub runs out: ONE notice with the time of the renewal, no error per repository, no pause-less hammering of the API, nothing red, and it resumes by itself."""
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
REAL = ("gh: API rate limit exceeded for user ID 1234567. If you reach out to GitHub Support for help, please include the request ID ABCD:1234:5678:9ABC:DEF0 and timestamp "
        "2026-11-12 16:30:00 UTC. (HTTP 403)")


class RateLimit(unittest.TestCase):
    def setUp(self):
        am.RUN_CACHE.clear()
        am.RATE_BLOCK.update({"until": 0.0, "unread": 0})
        self.config = {"mode": "full", "cold_runs_per_repo": 5, "runs_per_repo": 20, "cold_refresh_seconds": 600, "refresh_seconds": 120, "max_workers": 4, "hot_hours": 24, "tuning": {}}

    def tearDown(self):
        am.RUN_CACHE.clear()
        am.RATE_BLOCK.update({"until": 0.0, "unread": 0})

    def test_the_real_message_is_cut_to_one_line_and_recognised(self):
        self.assertTrue(am.is_rate_limit(REAL))
        self.assertFalse(am.is_rate_limit("gh: Could not resolve host: api.github.com"))
        short = am.short_error(REAL)
        self.assertEqual(short, "gh: API rate limit exceeded for user ID 1234567")
        self.assertNotIn("request ID", short)
        self.assertNotIn("GitHub Support", short)
        self.assertEqual(am.short_error("line one\nline two"), "line one")

    def test_131_repositories_give_one_pause_and_no_error_and_it_resumes(self):
        repos = [f"repo-{i:03d}" for i in range(131)]
        calls = []

        def fetch(repo, count):
            calls.append(repo)
            return [], REAL
        reset = int(time.time()) + 1800
        with mock.patch.object(am, "fetch_runs", fetch), mock.patch.object(am, "gh", return_value={"resources": {"core": {"reset": reset}}}), mock.patch.object(am, "hot_only_state", return_value={"on": False}):
            am.refresh_runs(repos, self.config)
            first = len(calls)
            self.assertLessEqual(first, 40, "the reading stops after the first chunk that hit the limit")
            self.assertTrue(all((am.RUN_CACHE.get(r) or {}).get("error") is None for r in repos), "a rate limit is not an error of a repository")
            state = am.rate_block_state(None)
            self.assertTrue(state["blocked"])
            self.assertGreater(state["unread"], 100)
            self.assertIn("T", state["until"])
            am.refresh_runs(repos, self.config)      # still blocked: it does not ask GitHub again
            self.assertEqual(len(calls), first)
            am.RATE_BLOCK["until"] = time.time() - 1      # the allowance renewed
            self.assertFalse(am.rate_block_state(None)["blocked"])
            am.refresh_runs(repos, self.config)
            self.assertGreater(len(calls), first, "it resumes by itself")

    def test_nothing_is_red_and_the_feed_does_not_see_it(self):
        runs = []
        self.assertEqual(am.unresolved_failures(runs), [])      # no run, no failure: an error of reading is never a red workflow
        am.RUN_CACHE["repo-x"] = {"runs": [], "at": 0, "error": None, "fails": 0}
        with mock.patch.object(am, "fetch_runs", lambda repo, count: ([], REAL)), mock.patch.object(am, "gh", side_effect=RuntimeError("limited")):
            am.refresh_runs(["repo-x"], {**self.config})
        self.assertIsNone(am.RUN_CACHE["repo-x"]["error"])
        self.assertGreater(am.RATE_BLOCK["until"], time.time() + 500)      # ten minutes when the renewal cannot be read

    def test_other_errors_are_cut_too_and_the_page_groups_many_of_them(self):
        am.note_read("repo-y", [], "gh: Could not resolve host: api.github.com\nsecond line (https://x)")
        am.note_read("repo-y", [], "gh: Could not resolve host: api.github.com\nsecond line (https://x)")
        am.note_read("repo-y", [], "gh: Could not resolve host: api.github.com\nsecond line (https://x)")
        self.assertNotIn("second line", str(am.RUN_CACHE["repo-y"].get("error") or ""))
        self.assertIn('T("ui.a_quota_out"', PAGE)
        self.assertIn('T("ui.a_nodata_many"', PAGE)
        self.assertIn("errs.length>3", PAGE)
        for lang in i18n.LANGS:
            self.assertIn("{time}", i18n.tl(lang, "ui.a_quota_out"), lang)
            self.assertIn("{n}", i18n.tl(lang, "ui.a_quota_out"), lang)
            self.assertIn("{n}", i18n.tl(lang, "ui.a_nodata_many"), lang)


if __name__ == "__main__":
    unittest.main()
