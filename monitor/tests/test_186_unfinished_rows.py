# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Runs read through GraphQL (network.graphql_checks) carry no duration, no queue time and no attempt, as the runs of a webhook that has not finished: the Sentinel, its panels and the
daily report must take them as they come instead of raising a TypeError every cycle (the failures were swallowed on purpose and counted in `degraded`)."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import _testenv  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.data_pipeline import graphql_checks, report_history  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402
from github_actions_monitor.sentinels import sentinel_panels  # noqa: E402

NOW = datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc)
NODE = {"defaultBranchRef": {"name": "main", "target": {"oid": "abcdef0123456", "checkSuites": {"nodes": [
    {"status": "COMPLETED", "conclusion": "FAILURE", "createdAt": "2026-11-04T09:00:00Z", "workflowRun": {"databaseId": 7, "runNumber": 3, "event": "PUSH", "url": "https://github.com/o/R/actions/runs/7",
                                                                                                          "workflow": {"name": "CI", "resourcePath": "/o/R/actions/workflows/ci.yml"}}},
    {"status": "IN_PROGRESS", "conclusion": None, "createdAt": "2026-11-04T11:00:00Z", "workflowRun": {"databaseId": 8, "runNumber": 4, "event": "PUSH", "url": "https://github.com/o/R/actions/runs/8",
                                                                                                         "workflow": {"name": "Build", "resourcePath": "/o/R/actions/workflows/b.yml"}}}]}}}}


def snapshot(runs, rate):
    info = {"R": {"branch": "main", "pushed": "2026-11-04T10:00:00Z", "release": None, "vuln_total": 0, "vuln_sev": {}, "prs": [], "rulesets": [], "label_dependencies": True, "files": {}}}
    return sl.compute_snapshot({"now": NOW, "today": "2026-11-04", "cfg": sl.DEFAULTS, "repos": ["R"], "eco": {"R": "armor"}, "repo_info": info, "alerts": {"R": {"at": 1, "codeql": [], "secret": 0}},
                                "perms": {}, "runs": {"R": runs}, "data": {"active": [], "issues": [], "rate": rate, "rate_sources": {}}, "history": {"days": {}}, "unreleased": {}, "targets": {},
                                "errors": {}, "loading": "", "audits": None})


class RowsWithoutADuration(unittest.TestCase):
    def setUp(self):
        self.runs = graphql_checks._runs("R", NODE)

    def test_the_rows_of_graphql_really_have_no_duration(self):
        self.assertEqual(len(self.runs), 2)
        self.assertTrue(all(r["seconds"] is None and r["queued"] is None and r["attempt"] is None for r in self.runs))

    def test_the_minutes_count_a_run_without_duration_as_zero(self):
        rows = sl.minutes({"R": self.runs + [dict(self.runs[0], id=9, seconds=120)]}, NOW)
        self.assertEqual(rows["R"]["min24"], 2)
        self.assertEqual(sl.minutes({"R": self.runs}, NOW), {})

    def test_the_snapshot_the_panels_and_the_daily_report_are_made(self):
        pooled = {"remaining": 14000, "limit": 15600, "reset": "2026-11-04T13:00:00Z"}      # two sources added up
        snap = snapshot(self.runs, pooled)
        self.assertEqual(snap["totals"]["red"], 1)
        panels = sentinel_panels.panels(snap, lambda key, **values: i18n.tl("en", key, **values), analytics=None, collab=None, owner="o")
        self.assertTrue(panels)
        json.dumps(snap)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(report_history.AutoSaver().maybe(Path(tmp), snap, 30))

    def test_the_page_stuck_test_survives_a_run_without_duration(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn('run["stuck"] = (run.get("seconds") or 0) >', source)
        self.assertNotIn('run["stuck"] = run["seconds"] >', source)


if __name__ == "__main__":
    unittest.main()
