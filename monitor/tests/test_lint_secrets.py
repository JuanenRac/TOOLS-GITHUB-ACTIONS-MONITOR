# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The secrets rule of the workflow linter: a readable filler is only information, what looks real is serious, a comment or an ignore pattern silences a finding and the value is never kept."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.cli import lint_workflows  # noqa: E402
from github_actions_monitor.app import settings_api as sa  # noqa: E402

BASE = "name: CI\non: [push]\npermissions:\n  contents: read\njobs:\n  t:\n    runs-on: ubuntu-latest\n    env:\n"
REAL = "q9Zr7LmV3xTb2WkP8sYd4NcA6hGj"


def found(lines):
    return [f for f in lint_workflows.lint_text(BASE + lines, "ci.yml") if f["rule"] == "secrets_in_clear"]


class Secrets(unittest.TestCase):
    def test_the_reported_false_positives_are_information_not_serious(self):
        cases = ("      DEMO_SERVICE_TOKEN: placeholder-for-compose-config   # placeholders: nothing here is a real secret\n",
                 "      DEMO_API_SECRET: ci-dummy-value\n      DEMO_ADMIN_PASSWORD: changeme-in-ci\n",
                 "      DEMO_SIGNING_TOKEN: xxxxxxxxxxxx\n",
                 "      DEMO_REGISTRY_TOKEN: not-a-real-token-for-ci\n")
        for text in cases:
            result = found(text)
            self.assertTrue(result, text)
            for finding in result:
                self.assertEqual((finding["severity"], finding["kind"]), ("info", "filler"), text)

    def test_references_and_empty_values_are_not_findings(self):
        for text in ("      DEMO_TOKEN: ${{ secrets.DEMO_TOKEN }}\n", "      DEMO_TOKEN: ${DEMO_TOKEN}\n", "      DEMO_TOKEN: $DEMO_TOKEN\n", "      DEMO_TOKEN:\n", "      DEMO_TOKEN: ''\n"):
            self.assertEqual(found(text), [], text)

    def test_what_looks_real_is_serious_and_an_odd_value_is_a_warning(self):
        real = found(f"      DEMO_API_KEY: {REAL}\n")
        self.assertEqual((real[0]["severity"], real[0]["kind"], real[0]["detail"]), ("bad", "high_entropy", "DEMO_API_KEY"))
        known = found("      NOTE: ghp_" + "A1b2C3d4" * 5 + "\n")
        self.assertEqual((known[0]["severity"], known[0]["kind"], known[0]["detail"]), ("bad", "known_pattern", "github_token"))
        odd = found("      DEMO_TOKEN: Plainwordsonlyhereforsure\n")
        self.assertEqual((odd[0]["severity"], odd[0]["kind"]), ("warn", "unknown_value"))

    def test_the_value_is_never_in_the_finding_or_the_summary(self):
        finding = found(f"      DEMO_API_KEY: {REAL}\n")[0]
        self.assertNotIn(REAL, json.dumps(finding))
        self.assertNotIn(REAL, json.dumps(lint_workflows.summarize({"demo": [finding]})))

    def test_a_comment_silences_the_line_or_the_next_one(self):
        same = found(f"      DEMO_API_KEY: {REAL}   # monitor-lint: ignore secrets_in_clear a filler for compose config\n")
        before = found(f"      # monitor-lint: ignore secrets_in_clear filler\n      DEMO_API_KEY: {REAL}\n")
        every = found(f"      # monitor-lint: ignore all\n      DEMO_API_KEY: {REAL}\n")
        other = found(f"      # monitor-lint: ignore permissions\n      DEMO_API_KEY: {REAL}\n")
        self.assertEqual((same, before, every), ([], [], []))
        self.assertEqual(len(other), 1)

    def test_the_ignore_list_of_the_configuration(self):
        root = Path(tempfile.mkdtemp())
        flows = root / "demo-one" / ".github" / "workflows"
        flows.mkdir(parents=True)
        (flows / "ci.yml").write_text(BASE + f"      DEMO_API_KEY: {REAL}\n", encoding="utf-8")
        self.assertEqual(len(lint_workflows.scan_clones(root, ["demo-one"])["demo-one"]), 1)
        for pattern in ("demo-one:ci.yml:secrets_in_clear", "demo-*:*:secrets_in_clear", "*:ci.yml:*"):
            self.assertEqual(lint_workflows.scan_clones(root, ["demo-one"], ignore=[pattern]), {}, pattern)
        self.assertEqual(len(lint_workflows.scan_clones(root, ["demo-one"], ignore=["other:ci.yml:secrets_in_clear"])["demo-one"]), 1)
        cfg = lint_workflows.settings({"lint": {"ignore": ["demo-one:ci.yml:secrets_in_clear", "bad pattern with spaces", 5]}})
        self.assertEqual(cfg["ignore"], ["demo-one:ci.yml:secrets_in_clear"])
        self.assertTrue(sa.check_value("lint.ignore", ["demo-*:ci.yml:secrets_in_clear"])[0])
        self.assertFalse(sa.check_value("lint.ignore", ["../x"])[0])

    def test_only_real_findings_turn_the_headline_red(self):
        from test_report_lines import snapshot
        baseline = snapshot()["parte"][0]["level"]
        weak = {"demo": [{"file": "ci.yml", "line": 1, "rule": "secrets_in_clear", "severity": "info", "detail": "DEMO_TOKEN", "kind": "filler"}]}
        s = snapshot(lint={"by_repo": weak, "summary": lint_workflows.summarize(weak), "in_report": True})
        self.assertEqual(s["parte"][0]["level"], baseline)      # information does not change the headline
        self.assertNotIn("workflow_lint", [line.get("code") for line in s["parte"]])
        real = {"demo": [{"file": "ci.yml", "line": 1, "rule": "secrets_in_clear", "severity": "bad", "detail": "github_token", "kind": "known_pattern"}]}
        s = snapshot(lint={"by_repo": real, "summary": lint_workflows.summarize(real), "in_report": True})
        self.assertEqual(s["parte"][0]["level"], "bad")


if __name__ == "__main__":
    unittest.main()
