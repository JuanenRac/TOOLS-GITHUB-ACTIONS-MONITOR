# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.5.2: the signing queue filter, the readiness chips of the header, grouped issue-closing suggestions, the Grafana board validated against /metrics and the contract
of the profile dashboard."""
import json
import re
import sys
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import ci_red  # noqa: E402
import export_status  # noqa: E402
import i18n  # noqa: E402
import outputs  # noqa: E402
import signstate  # noqa: E402
from test_report_lines import codes, snapshot  # noqa: E402
from test_settings_outputs import DATA, NOW, SNAP  # noqa: E402


def queue_row(name, verified, hours=5):
    return {"name": name, "repo": name, "ecosystem": "armor", "hours": hours, "step": "sign", "run_id": 1, "last_build_at": None, "signature_kind": "release",
            "signature_verified": verified, "url": "u", "argv": [], "command": ""}


class SignQueueFilter(unittest.TestCase):
    rows = [queue_row("A", True), queue_row("B", "unknown"), queue_row("C", False), queue_row("D", "unknown")]

    def test_trust_of_a_row(self):
        self.assertEqual([signstate.trust_of(r) for r in self.rows], ["verified", "unknown", "failed", "unknown"])

    def test_filter(self):
        names = lambda trust: [r["name"] for r in signstate.filter_queue(self.rows, trust)]   # noqa: E731
        self.assertEqual(names("verified"), ["A"])
        self.assertEqual(names("unknown"), ["B", "D"])
        self.assertEqual(names("failed"), ["C"])
        self.assertEqual(names("all"), ["A", "B", "C", "D"])
        self.assertEqual(names("nonsense"), ["A", "B", "C", "D"])      # an unknown value filters nothing

    def test_the_queue_built_by_the_tool_carries_the_trust(self):
        state = {"state": "built_on_gha", "name": "t", "repo": "R", "ecosystem": "armor", "hours": 3.0, "run_id": 7, "last_build_at": None,
                 "signature_kind": "none", "signature_verified": False, "url": "u"}
        queue = signstate.sign_queue([state])
        self.assertEqual(queue[0]["trust"], "failed")

    def test_the_export_filters_and_names_the_trust(self):
        snap = {"a5": {"sign_queue": self.rows}}
        self.assertEqual([r["name"] for r in export_status.sign_queue_rows(snap, "failed")], ["C"])
        self.assertEqual({r["trust"] for r in export_status.sign_queue_rows(snap)}, {"verified", "unknown", "failed"})
        self.assertIn("trust", export_status.FIELDS)

    def test_the_page_has_the_filter_and_a_distinct_look_per_trust(self):
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        for needle in ('id="sq-trust"', ".tq-verified", ".tq-unknown", ".tq-failed", 'q.trust'):
            self.assertIn(needle, page)
        for lang in i18n.LANGS:
            cat = i18n.catalogue(lang)
            for key in ("ui.trust_verified", "ui.trust_unknown", "ui.trust_failed", "ui.trust_filter", "ui.trust_all"):
                self.assertIn(key, cat)


class ReadinessChips(unittest.TestCase):
    def test_the_header_has_the_chips_and_the_texts_exist(self):
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('id="k-ready"', page)
        self.assertIn(".rdy-chip.warn", page)
        for lang in i18n.LANGS:
            self.assertIn("ui.ready_title", i18n.catalogue(lang))

    def test_the_snapshot_gives_one_health_row_per_ecosystem(self):
        s = snapshot()
        self.assertTrue(s["a11"]["health"])
        self.assertTrue(all("ecosystem" in h and "score" in h for h in s["a11"]["health"]))


class IssueCloseGrouped(unittest.TestCase):
    def with_close_rows(self, rows):
        import surface
        real = surface.build

        def fake(inp):
            block = real(inp)
            block["sections"] = [dict(sec, rows=rows, count=len(rows)) if sec["key"] == "issue_close" else sec for sec in block["sections"]]
            return block

        with unittest.mock.patch.object(surface, "build", fake):
            return snapshot()

    def test_one_line_grouped_by_repository(self):
        s = self.with_close_rows([["R-ONE", "#1 a", "r", "gh issue close 1"], ["R-ONE", "#2 b", "r", "gh issue close 2"], ["R-TWO", "#3 c", "r", "gh issue close 3"]])
        lines = [l for l in s["parte"] if l.get("code") == "issue_close"]
        self.assertEqual(len(lines), 1)
        self.assertIn("R-ONE (2)", lines[0]["text"])
        self.assertIn("R-TWO (1)", lines[0]["text"])
        self.assertEqual(lines[0]["level"], "info")
        self.assertNotIn("gh issue close", lines[0]["text"])      # the commands stay in the section: the report only counts

    def test_no_suggestion_no_line(self):
        self.assertNotIn("issue_close", codes(self.with_close_rows([])))

    def test_every_language_has_the_text(self):
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                self.assertNotEqual(i18n.t("parte.issue_close", n=2, list="R (2)"), "parte.issue_close")


class GrafanaBoards(unittest.TestCase):
    def names(self, board):
        text = " ".join(t.get("expr", "") for p in board["panels"] for t in p.get("targets", []))
        return set(re.findall(r"ghamon_[a-z0-9_]+", text))

    def test_every_metric_of_every_board_is_served(self):
        served = outputs.metrics_text(SNAP, DATA, now=NOW)
        for name in ("monitor_dashboard.json", "red_by_ecosystem.json"):
            board = json.loads((HERE / "docs" / "grafana" / name).read_text(encoding="utf-8"))
            self.assertTrue(self.names(board), name)
            for metric in self.names(board):
                self.assertRegex(served, rf"(?m)^# TYPE {metric} gauge$", f"{name}: {metric}")

    def test_the_minimal_board_is_red_by_ecosystem_and_uses_one_label(self):
        board = json.loads((HERE / "docs" / "grafana" / "red_by_ecosystem.json").read_text(encoding="utf-8"))
        self.assertEqual(len(board["panels"]), 1)
        target = board["panels"][0]["targets"][0]
        self.assertEqual(target["expr"], "ghamon_ecosystem_red_workflows")
        self.assertEqual(target["legendFormat"], "{{ecosystem}}")
        served = outputs.metrics_text(SNAP, DATA, now=NOW)
        self.assertIn('ghamon_ecosystem_red_workflows{ecosystem="armor"}', served)       # the label the legend uses exists
        self.assertEqual({i["name"] for i in board["__inputs"]}, {"DS_PROMETHEUS"})


class DashboardContract(unittest.TestCase):
    """What the profile dashboard may rely on (documented in CI_RED_SCHEMA.md and CI_RED_BRIDGE.md): the document served at /api/outputs/dashboard.json is the one of ci_red.py."""
    doc = (HERE / "docs" / "CI_RED_SCHEMA.md").read_text(encoding="utf-8")

    def test_the_served_document_is_the_documented_one(self):
        served = outputs.dashboard_json(SNAP)
        self.assertEqual(served, ci_red.build(SNAP))
        for key in ("schema", "generated", "tool_version", "complete", "red_repos", "pending_sign_repos", "pending_sign_hours_threshold", "repos"):
            self.assertIn(key, served)
            self.assertIn(f'"{key}"', self.doc)
        self.assertEqual(served["schema"], 2)
        for repo in served["repos"].values():
            for key in ("ecosystem", "red", "pending_sign_hours", "pending_sign"):
                self.assertIn(key, repo)
            for red in repo["red"]:
                self.assertEqual(set(red), {"workflow", "conclusion", "since", "streak", "url", "ai_hint"})

    def test_the_public_export_never_carries_the_signing_side(self):
        public = json.dumps(export_status.public_status(SNAP))
        self.assertFalse(export_status.contains_sensitive(public))
        self.assertEqual(set(export_status.public_status(SNAP)), {"schema", "generated", "tool_version", "complete", "red_repos", "red"})

    def test_an_incomplete_snapshot_is_marked_so_the_dashboard_keeps_its_last_picture(self):
        self.assertIs(ci_red.build(dict(SNAP, loading="3/10"))["complete"], False)
        self.assertIs(export_status.public_status(dict(SNAP, loading="3/10"))["complete"], False)


if __name__ == "__main__":
    unittest.main()
