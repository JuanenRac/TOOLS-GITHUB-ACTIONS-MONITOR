# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What the security, delivery, supply and collab sentinels say reaches the AI: a signal per sentinel with a row per (code, repository), the gaps of reading as a signal of their own, one event per
(code, repository) in the stream (never for an alert of level info), no duplicates and no noise when everything is read."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.data_pipeline import signals  # noqa: E402
from github_actions_monitor.integrations import ai_alerts  # noqa: E402


def alert(code, repo, level="warning"):
    return {"id": f"{code}:{repo}", "code": code, "level": level, "repo": repo, "title": f"{repo}: {code}"}


def doc(reports):
    return signals.state({"figures": {}}, [], "complete", sentinels=reports)


class Signals(unittest.TestCase):
    def test_each_sentinel_without_a_panel_has_a_signal_with_a_row_per_code_and_repo_worst_first(self):
        d = doc({"security": {"status": {}, "alerts": [alert("security.workflow_write", "b"), alert("security.secret", "a", "critical"), alert("security.workflow_write", "a")]},
                 "delivery": {"status": {}, "alerts": [alert("release.ecosystem_drift", "x", "info")]}, "supply": {"status": {}, "alerts": []}})
        by = {s["id"]: s for s in d["signals"]}
        self.assertEqual((by["sentinel.security"]["level"], [(r["code"], r["repo"]) for r in by["sentinel.security"]["rows"]]),
                         ("act", [("security.secret", "a"), ("security.workflow_write", "a"), ("security.workflow_write", "b")]))
        self.assertEqual(by["sentinel.delivery"]["level"], "info")
        self.assertEqual((by["sentinel.supply"]["level"], by["sentinel.supply"]["summary"]), ("info", "no alerts"))
        self.assertNotIn("sentinel.collab", by, "collab keeps its panel")

    def test_a_gap_of_reading_is_a_signal_with_its_cause_and_nothing_to_report_when_everything_was_read(self):
        quiet = doc({"security": {"status": {"errors": [], "unchecked": [], "unavailable_why": {"off": {"code_scanning": 46}, "plan": {"secret": 2}}}, "alerts": []}})
        self.assertNotIn("sentinel.security.coverage", {s["id"] for s in quiet["signals"]}, "a feature that is off is not a gap")
        gap = doc({"security": {"status": {"errors": [{"section": "a", "kind": "timeout"}, {"section": "b", "kind": "timeout"}], "unchecked": ["c"], "unavailable_why": {"permission": {"dependabot": 3}}}, "alerts": []},
                   "collab": {"status": {"paused": True}, "alerts": []}})
        by = {s["id"]: s for s in gap["signals"]}
        self.assertEqual(by["sentinel.security.coverage"]["level"], "watch")
        self.assertIn("read timeout 2", by["sentinel.security.coverage"]["summary"])
        self.assertIn("permission dependabot 3", by["sentinel.security.coverage"]["summary"])
        self.assertIn("sentinel.collab.coverage", by)
        self.assertFalse(by["sentinel.security.coverage"]["transient"], "a permission gap does not clear by itself")
        self.assertTrue(by["sentinel.collab.coverage"]["transient"])

    def test_the_brief_names_them(self):
        d = doc({"security": {"status": {}, "alerts": [alert("security.secret", "a", "critical")]}, "delivery": {"status": {"unavailable": {"timeout": 2, "not_found": 4}}, "alerts": [alert("release.tag_without_release", "r")]}})
        text = signals.brief_sections(d)
        self.assertIn("sentinel.security: 1 alert(s) in 1 repositor(ies): security.secret 1", text)
        self.assertIn("sentinel.delivery: 1 alert(s)", text)
        self.assertIn("sentinel.delivery.coverage: delivery: not everything was read - unreadable timeout 2", text)
        self.assertNotIn("not_found", text, "a repository without the file is not a gap")


class Stream(unittest.TestCase):
    def test_one_event_per_code_and_repo_none_for_info_resolved_when_solved_and_no_duplicates(self):
        reports = {"security": {"status": {}, "alerts": [alert("security.secret", "a", "critical"), alert("security.workflow_write", "a"), alert("security.workflow_write", "b")]},
                   "delivery": {"status": {}, "alerts": [alert("release.ecosystem_drift", "x", "info"), alert("release.tag_without_release", "x")]}}
        rows = signals.extra_alert_rows(doc(reports))
        self.assertEqual(sorted((r["repo"], r["workflow"]) for r in rows), [("a", "security.secret"), ("a", "security.workflow_write"), ("b", "security.workflow_write"), ("x", "release.tag_without_release")])
        with tempfile.TemporaryDirectory() as tmp:
            config = {"ai_alerts": {"enabled": True, "folder": tmp}}
            first = ai_alerts.update(config, [], extra_rows=rows)
            self.assertEqual(len(first["opened"]), 4)
            self.assertEqual(ai_alerts.update(config, [], extra_rows=signals.extra_alert_rows(doc(reports)))["opened"], [], "an event only when it appears")
            reports["security"]["alerts"] = reports["security"]["alerts"][:1]
            solved = ai_alerts.update(config, [], extra_rows=signals.extra_alert_rows(doc(reports)))
            self.assertEqual(sorted(a["repo"] for a in solved["resolved"]), ["a", "b"])

    def test_a_gap_of_reading_is_one_event_and_a_flood_is_cut_with_one_more_that_counts(self):
        rows = signals.extra_alert_rows(doc({"supply": {"status": {"unchecked": ["a", "b"]}, "alerts": []}}))
        self.assertEqual([(r["repo"], r["workflow"]) for r in rows], [("monitor", "sentinel.supply.coverage")])
        flood = signals.extra_alert_rows(doc({"security": {"status": {}, "alerts": [alert("security.workflow_write", f"r{i:03d}") for i in range(40)]}}))
        self.assertEqual(len(flood), signals.STREAM_MAX_ROWS + 1)
        self.assertIn("more alert", flood[-1]["detail"])


if __name__ == "__main__":
    unittest.main()
