# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The panels of the Sentinel tab as data: the same levels as the page, the rows somebody has to act on, the brief, the feed and the endpoint all in agreement."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import ai_alerts  # noqa: E402
import i18n  # noqa: E402
import sentinel_panels  # noqa: E402

OWNER = "demo-owner"


def snapshot():
    """A snapshot with the case of the owner: two high CodeQL alerts in one repository and one high Dependabot alert in another."""
    return {
        "enabled": True,
        "a1": {"level": "ok", "stuck": [], "issues": []},
        "a2": {"level": "bad", "red": [{"repo": "demo-alpha-app", "workflow": "CI", "conclusion": "failure", "streak": 2, "url": "https://github.com/demo-owner/demo-alpha-app/actions/runs/9", "since": "2026-01-01T00:00:00Z"}], "workflows_checked": 5},
        "a3": {"level": "bad", "codeql_total": 2, "dependabot_total": 1, "secret_total": 0,
               "rows": [{"repo": "demo-beta-fw", "codeql": 2, "dependabot": 0, "secret": 0, "sev": {"high": 2}}, {"repo": "demo-owner", "codeql": 0, "dependabot": 1, "secret": 0, "sev": {"high": 1}},
                        {"repo": "demo-gamma-ui", "codeql": 0, "dependabot": 0, "secret": 0, "sev": {}}],
               "codeql": [{"repo": "demo-beta-fw", "severity": "high", "rule": "py/sql-injection", "file": "src/db.py", "url": "u1"}, {"repo": "demo-beta-fw", "severity": "high", "rule": "py/path-injection", "file": "src/io.py", "url": "u2"}]},
        "a4": {"level": "warn", "dependabot": [{"repo": "demo-alpha-core", "number": 7, "title": "Bump x", "url": "u", "major": True, "conflict": False}, {"repo": "demo-alpha-core", "number": 8, "title": "Bump y", "url": "u", "major": False, "conflict": False}]},
        "a5": {"level": "warn", "candidates": [{"repo": "demo-alpha-app", "entries": 6}], "pending_sign": [], "green_unreleased": []},
        "a6": {"level": "ok", "rows": []}, "a7": {"level": "ok", "budget": [], "total24": 12}, "a8": {"level": "info", "audits": {}}, "a9": {"level": "unknown", "boards": []},
        "a10": {"level": "warn", "sections": [{"key": "dead_schedule", "title": "Schedules with no runs", "level": "warn", "count": 1, "rows": [["demo-gamma-ui", "ci.yml"]]}]},
        "a11": {"level": "ok", "ready": 1, "behind": 0, "low_health": []},
        "lint": {"enabled": True, "summary": {"bad": 0, "warn": 1, "findings": 1, "repos": 1}, "rows": [{"repo": "demo-alpha-app", "file": "ci.yml", "line": 3, "rule": "unpinned_uses", "severity": "warn"}]},
    }


class PanelsAsData(unittest.TestCase):
    def setUp(self):
        i18n.set_language("en")
        self.panels = sentinel_panels.panels(snapshot(), i18n.t, analytics={"enabled": True, "slower": [{"repo": "demo-alpha-app", "workflow": "CI"}], "duration": [1], "flaky": []},
                                             collab=[{"id": "c1", "repo": "demo-alpha-core", "title": "Critical issue", "level": "warn", "details": {"url": "u"}}], owner=OWNER)
        self.by_id = {p["id"]: p for p in self.panels}

    def test_every_panel_is_there_with_the_level_the_page_shows(self):
        self.assertEqual([p["id"] for p in self.panels], list(sentinel_panels.ORDER))
        snap = snapshot()
        for key in ("a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10", "a11"):
            self.assertEqual(self.by_id[key]["level"], snap[key]["level"], key)      # the page paints the level the sentinel computed: same word here
        self.assertEqual(self.by_id["a12"]["level"], "warn")
        self.assertEqual(self.by_id["a13"]["level"], "warn")
        self.assertEqual(self.by_id["collab"]["level"], "warn")

    def test_the_security_panel_names_the_repositories_of_the_owner_with_a_link(self):
        rows = self.by_id["a3"]["rows"]
        beta = [r for r in rows if r["repo"] == "demo-beta-fw" and r["key"] == "security"][0]
        self.assertEqual(beta["level"], "bad")
        self.assertIn("CodeQL 2", beta["text"])
        self.assertEqual(beta["url"], "https://github.com/demo-owner/demo-beta-fw/security")
        mine = [r for r in rows if r["repo"] == "demo-owner"][0]
        self.assertIn("Dependabot 1", mine["text"])
        self.assertIn("high 1", mine["text"])
        self.assertFalse([r for r in rows if r["repo"] == "demo-gamma-ui"], "a repository with nothing open is not a row")
        self.assertEqual(len([r for r in rows if r["key"].startswith("codeql:")]), 2)

    def test_only_what_somebody_has_to_do_becomes_an_alert(self):
        alerts = sentinel_panels.alert_rows(self.panels)
        by = {(a["panel"], a["repo"]): a for a in alerts}
        self.assertEqual(by[("a3", "demo-beta-fw")]["level"], "bad")
        self.assertEqual(by[("a3", "demo-owner")]["level"], "bad")
        self.assertEqual(by[("a4", "demo-alpha-core")]["level"], "warn")      # only the major or conflicting pull request
        self.assertEqual(len([a for a in alerts if a["panel"] == "a4"]), 1)
        self.assertFalse([a for a in alerts if a["panel"] in ("a1", "a2", "a6", "a7", "a8", "a9", "a11")])      # panels without findings add nothing
        for alert in alerts:
            self.assertEqual(alert["conclusion"], "panel")

    def test_the_panels_reach_the_brief_and_the_feed_with_the_same_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {"ai_alerts": {"enabled": True, "folder": tmp}}
            red = [{"repo": "demo-alpha-app", "workflow": "CI", "conclusion": "failure", "streak": 2, "since": "2026-01-01T00:00:00Z", "url": "https://github.com/demo-owner/demo-alpha-app/actions/runs/9"}]
            result = ai_alerts.update(config, red, panels=self.panels)
            brief = (Path(tmp) / ai_alerts.BRIEF).read_text(encoding="utf-8")
            real = [a for a in result["alerts"] if a["class"] == "real"]
            watch = [a for a in result["alerts"] if a["class"] == "watch"]
            expected_real = 1 + len([a for a in sentinel_panels.alert_rows(self.panels) if a["level"] == "bad"])
            self.assertEqual(len(real), expected_real)
            self.assertGreaterEqual(len(watch), 1)
            self.assertIn(f"{expected_real} real alert(s) open", brief)      # the counter adds the CI reds and the panels that say "act"
            self.assertIn("## Sentinel panels", brief)
            self.assertIn("A3 ", brief)
            self.assertIn("- [high/real] demo-beta-fw / ", brief)
            self.assertIn("demo-beta-fw", brief)
            self.assertIn("demo-owner", brief)
            self.assertEqual(json.loads((Path(tmp) / ai_alerts.STATE).read_text(encoding="utf-8")).keys(), {a["id"] for a in result["alerts"]})
            # the next refresh with the same data opens nothing new; when the finding goes away the alert is resolved
            again = ai_alerts.update(config, red, panels=self.panels)
            self.assertEqual(again["opened"], [])
            gone = ai_alerts.update(config, red, panels=[])
            self.assertEqual(len(gone["resolved"]), len(result["alerts"]) - 1)

    def test_brief_section_lists_levels_and_rows(self):
        text = sentinel_panels.brief_section(self.panels)
        self.assertIn("- A3 ", text)
        self.assertIn(": bad", text)
        self.assertIn("demo-owner: CodeQL 0 · Dependabot 1", text)

    def test_the_mcp_tool_and_the_endpoint_say_what_the_page_says(self):
        import mcp_server
        self.assertIn("sentinel_panels", [t["name"] for t in mcp_server.TOOLS])
        answer = {"data": {"panels": self.panels, "act": 2, "watch": 3}, "error": None}
        seen = []
        text = mcp_server.call("sentinel_panels", {}, {}, getter=lambda path: seen.append(path) or answer)
        self.assertEqual(seen, ["/api/sentinel/panels"])
        data = json.loads(text)["data"]
        self.assertEqual([p["id"] for p in data["panels"]], list(sentinel_panels.ORDER))
        self.assertTrue([r for p in data["panels"] if p["id"] == "a3" for r in p["rows"] if r["repo"] == "demo-owner"])
        source = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn('path == "/api/sentinel/panels"', source)
        self.assertIn("panels=panels", source)      # the feed takes the same panels

    def test_a_snapshot_that_is_off_or_empty_gives_no_panels(self):
        self.assertEqual(sentinel_panels.panels({"enabled": False}, i18n.t), [])
        self.assertEqual(sentinel_panels.panels(None, i18n.t), [])


if __name__ == "__main__":
    unittest.main()
