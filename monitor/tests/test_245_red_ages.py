# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A red nobody attends to ages: after `ci.red_age_days` days (30 by default, switch `ci.red_ages`) a failure with nothing newer of the events that decide stops being red and is shown as inactive. The cases
are the ones measured on a fork whose copied nightly job fails every night: 41 of 42 runs and 26 of 27 failed, the last one nearly a year ago, and the owner switched the workflow off afterwards."""
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


def run(n, conclusion="failure", days=1, event="push", path="ci.yml", branch="main", fork=False):
    return {"repo": "demo", "id": n, "name": path, "path": path, "branch": branch, "event": event, "fork": fork, "status": "completed", "conclusion": conclusion, "started": stamp(days, n % 20), "url": f"https://x/{n}", "sha": "abc"}


class Aging(unittest.TestCase):
    def setUp(self):
        redrule.configure({"ci": {"red_age_days": 30}})

    def tearDown(self):
        redrule.configure({})

    def split(self, runs):
        out = redrule.classify(runs, "main", NOW)
        return len(out["red"]), len(out["inactive"]), out

    def test_a_fresh_red_is_red_and_an_old_one_is_history(self):
        self.assertEqual(self.split([run(1, days=29)])[:2], (1, 0))
        self.assertEqual(self.split([run(1, days=31)])[:2], (0, 1))

    def test_the_old_red_is_marked_as_aged_in_its_row(self):
        _red, _inactive, out = self.split([run(1, days=45)])
        row = redrule.row_of("demo", out["inactive"][0])
        self.assertTrue(row["aged"])
        _red, _inactive, fresh = self.split([run(1, days=2)])
        self.assertFalse(redrule.row_of("demo", fresh["red"][0])["aged"])

    def test_a_workflow_that_still_runs_other_events_does_not_keep_an_old_red_alive(self):
        # pull requests keep running (they never decide), but nothing that decides has run for 45 days: the red is not attended to
        runs = [run(1, days=45), run(2, "success", days=1, event="pull_request"), run(3, "failure", days=0, event="pull_request")]
        self.assertEqual(self.split(runs)[:2], (0, 1))

    def test_a_green_run_after_the_failure_clears_it_whatever_its_age(self):
        self.assertEqual(self.split([run(1, days=100), run(2, "success", days=50)])[:2], (0, 0))

    def test_the_copied_nightly_job_of_a_fork_is_history(self):
        # 41 of 42 runs of the schedule failed, the last one 290 days ago
        runs = [run(n, "failure" if n else "success", days=290 + n % 3, event="schedule", path="publish.yaml") for n in range(42)]
        self.assertEqual(self.split(runs)[:2], (0, 1))
        redrule.configure({"ci": {"red_ages": False, "inactive_days": 0}})
        self.assertEqual(self.split(runs)[:2], (1, 0))      # the switch off: the old behaviour, a red stays red

    def test_the_streak_and_the_cause_are_kept_for_the_aged_item(self):
        _red, _inactive, out = self.split([run(1, days=60), run(2, days=59), run(3, days=58)])
        self.assertEqual(out["inactive"][0]["streak"], 3)

    def test_the_states_list_the_aged_reds_with_the_inactive_workflows(self):
        held = redrule.states({"demo": [run(1, days=45, path="old.yml"), run(2, days=1, path="new.yml")]}, {"demo": "main"}, now=NOW)
        self.assertEqual([r["file"] for r in held["inactive"]], ["old.yml"])
        rows, _approx = redrule.red_workflows({"demo": [run(1, days=45, path="old.yml"), run(2, days=1, path="new.yml")]}, {"demo": "main"}, now=NOW)
        self.assertEqual([r["file"] for r in rows], ["new.yml"])


class Configuration(unittest.TestCase):
    def tearDown(self):
        redrule.configure({})

    def test_the_default_is_thirty_days_and_on(self):
        original = redrule.DEFAULT_RED_AGE_DAYS
        redrule.DEFAULT_RED_AGE_DAYS = 30      # the tests of the repository run with the aging off; this one asks for the real default
        try:
            redrule.configure({})
            self.assertEqual(redrule.POLICY["red_age_days"], 30)
            redrule.configure({"ci": {"red_ages": False}})
            self.assertEqual(redrule.POLICY["red_age_days"], 0)
            redrule.configure({"ci": {"red_age_days": 10}})
            self.assertEqual(redrule.POLICY["red_age_days"], 10)
        finally:
            redrule.DEFAULT_RED_AGE_DAYS = original

    def test_a_bad_value_keeps_the_default_of_that_key(self):
        original = redrule.DEFAULT_RED_AGE_DAYS
        redrule.DEFAULT_RED_AGE_DAYS = 30
        try:
            for bad in (0, -5, "10", True, 5000, None, 2.5):
                redrule.configure({"ci": {"red_age_days": bad}})
                self.assertEqual(redrule.POLICY["red_age_days"], 30, bad)
        finally:
            redrule.DEFAULT_RED_AGE_DAYS = original

    def test_the_settings_are_in_the_schema_with_texts_in_eight_languages(self):
        import json
        for key in ("ci.red_ages", "ci.red_age_days"):
            self.assertIn(key, settings_api.META)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ci.red_ages", "ci.red_age_days"):
                self.assertTrue(texts.get("cfg.f." + key) and texts.get("cfg.h." + key), (lang, key))


if __name__ == "__main__":
    unittest.main()
