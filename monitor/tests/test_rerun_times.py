# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Duration and queue time of a run are measured on its latest attempt: a re-run days or months after the first try must not report days of queue or hundreds of days of duration."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.data_pipeline import analytics  # noqa: E402


def api_run(**over):
    base = {"id": 1, "name": "CI", "path": ".github/workflows/ci.yml", "event": "push", "head_branch": "main", "head_sha": "abcdef123456", "status": "completed", "conclusion": "success", "run_attempt": 1,
            "created_at": "2026-01-01T10:00:00Z", "run_started_at": "2026-01-01T10:00:20Z", "updated_at": "2026-01-01T10:05:20Z", "html_url": "https://example.invalid/r/1",
            "head_repository": {"full_name": "owner/demo"}, "repository": {"full_name": "owner/demo"}}
    base.update(over)
    return base


class RunTimes(unittest.TestCase):
    def test_first_attempt_keeps_queue_and_duration(self):
        queued, seconds, started = am.run_times(api_run())
        self.assertEqual((queued, seconds, started), (20, 300, "2026-01-01T10:00:20Z"))

    def test_rerun_months_later_has_no_queue_and_a_real_duration(self):
        rerun = api_run(run_attempt=2, run_started_at="2026-12-10T08:00:00Z", updated_at="2026-12-10T08:04:00Z")
        queued, seconds, started = am.run_times(rerun)
        self.assertIsNone(queued)      # created_at is of the first attempt: 343 days of "queue" would be wrong
        self.assertEqual(seconds, 240)
        self.assertEqual(started, "2026-12-10T08:00:00Z")

    def test_rerun_without_start_of_its_own_has_no_duration(self):
        queued, seconds, _started = am.run_times(api_run(run_attempt=3, run_started_at=None))
        self.assertIsNone(queued)
        self.assertIsNone(seconds)

    def test_a_duration_longer_than_a_run_can_last_is_unknown(self):
        queued, seconds, _s = am.run_times(api_run(updated_at="2027-06-01T10:00:00Z"))
        self.assertIsNone(seconds)
        self.assertEqual(queued, 20)

    def test_running_run_counts_up_to_now(self):
        from datetime import datetime, timedelta, timezone
        begun = (datetime.now(timezone.utc) - timedelta(seconds=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _q, seconds, _s = am.run_times(api_run(status="in_progress", conclusion=None, created_at=begun, run_started_at=begun, updated_at=begun))
        self.assertTrue(85 <= seconds <= 400, seconds)

    def test_fetch_runs_uses_the_attempt_not_the_first_try(self):
        body = {"workflow_runs": [api_run(id=7, run_attempt=2, run_started_at="2026-12-10T08:00:00Z", updated_at="2026-12-10T08:04:00Z"), api_run(id=8)]}
        with mock.patch.object(am, "gh_read", return_value=body):
            runs, error = am.fetch_runs("demo", 20)
        self.assertIsNone(error)
        by_id = {r["id"]: r for r in runs}
        self.assertEqual((by_id[7]["queued"], by_id[7]["seconds"], by_id[7]["attempt"]), (None, 240, 2))
        self.assertEqual((by_id[8]["queued"], by_id[8]["seconds"]), (20, 300))


class RerunTiming(unittest.TestCase):
    def setUp(self):
        am.TIMING["on"], am.TIMING["budget"] = True, 3
        am.TIMING["known"].clear()

    def tearDown(self):
        am.TIMING["on"] = False
        am.TIMING["known"].clear()

    def test_timing_endpoint_is_used_once_and_remembered(self):
        run = api_run(id=9, run_attempt=2)
        with mock.patch.object(am, "gh_read", return_value={"run_duration_ms": 125000}) as read:
            self.assertEqual(am.rerun_seconds("demo", run), 125)
            self.assertEqual(am.rerun_seconds("demo", run), 125)
        self.assertEqual(read.call_count, 1)
        self.assertIn("/actions/runs/9/timing", read.call_args[0][0])

    def test_off_by_default_budget_and_bad_answers(self):
        am.TIMING["on"] = False
        with mock.patch.object(am, "gh_read") as read:
            self.assertIsNone(am.rerun_seconds("demo", api_run(id=10, run_attempt=2)))
        read.assert_not_called()
        am.TIMING["on"], am.TIMING["budget"] = True, 0
        with mock.patch.object(am, "gh_read") as read:
            self.assertIsNone(am.rerun_seconds("demo", api_run(id=11, run_attempt=2)))
        read.assert_not_called()
        am.TIMING["budget"] = 3
        with mock.patch.object(am, "gh_read", return_value={"run_duration_ms": 10 ** 12}):
            self.assertIsNone(am.rerun_seconds("demo", api_run(id=12, run_attempt=2)))
        with mock.patch.object(am, "gh_read", side_effect=RuntimeError("boom")):
            self.assertIsNone(am.rerun_seconds("demo", api_run(id=13, run_attempt=2)))

    def test_setting_exists(self):
        from github_actions_monitor.app import settings_api
        self.assertIn("ci.rerun_timing", settings_api.META)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("cfg.f.ci.rerun_timing", "cfg.h.ci.rerun_timing", "ui.cfg_b_durations"):
                self.assertTrue(texts.get(key), (lang, key))


class FlakyAfterApproval(unittest.TestCase):
    def run_(self, n, conclusion, attempt=1, fork=False, minute=0):
        return {"repo": "demo", "id": n, "name": "CI", "sha": "abc", "status": "completed", "conclusion": conclusion, "attempt": attempt, "fork": fork, "started": f"2026-01-01T10:{minute:02d}:00Z"}

    def test_retry_after_an_approval_is_not_flaky(self):
        runs = [self.run_(1, "action_required", minute=0), self.run_(2, "success", attempt=2, minute=5)] + [self.run_(i, "success", minute=10 + i) for i in range(3, 6)]
        for i, r in enumerate(runs[2:], start=1):
            r["sha"] = f"other{i}"
        self.assertEqual(analytics.flaky_rows(runs), [])

    def test_a_real_retry_is_still_flaky(self):
        runs = [self.run_(1, "failure", minute=0), self.run_(2, "success", attempt=2, minute=5)] + [self.run_(i, "success", minute=10 + i) for i in range(3, 6)]
        for i, r in enumerate(runs[2:], start=1):
            r["sha"] = f"other{i}"
        self.assertEqual(len(analytics.flaky_rows(runs)), 1)

    def test_runs_of_forks_are_not_counted(self):
        runs = [self.run_(1, "failure", fork=True, minute=0), self.run_(2, "success", fork=True, attempt=2, minute=5)] + [self.run_(i, "success", fork=True, minute=10 + i) for i in range(3, 6)]
        self.assertEqual(analytics.flaky_rows(runs), [])


if __name__ == "__main__":
    unittest.main()
