# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The score for other tools: the figures of /metrics, the tool of the MCP server, and the invented answer of --demo that has the same shape as the real one."""
import inspect
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor, demo_mode  # noqa: E402
from github_actions_monitor.integrations import mcp_server, outputs  # noqa: E402
from github_actions_monitor.scoring import api, engine  # noqa: E402


class Metrics(unittest.TestCase):
    def text(self, score):
        return outputs.metrics_text({}, {}, extra={"score": score})

    def test_a_scored_account_gives_the_number_the_coverage_and_a_one(self):
        text = self.text({"state": "scored", "score": 82.5, "coverage": 0.8})
        self.assertIn("ghamon_score 82.5", text)
        self.assertIn("ghamon_score_coverage 0.8", text)
        self.assertIn("ghamon_score_scored 1", text)

    def test_without_a_number_there_is_no_number_in_the_metrics_either(self):
        for state in ("calibrating", "insufficient_data"):
            text = self.text({"state": state, "score": None, "coverage": 0.2})
            self.assertNotIn("\nghamon_score ", text)
            self.assertIn("ghamon_score_scored 0", text)
            self.assertIn("ghamon_score_coverage 0.2", text)

    def test_nothing_about_the_score_when_there_is_none(self):
        self.assertNotIn("ghamon_score", self.text(None))
        self.assertNotIn("ghamon_score", outputs.metrics_text({}, {}, extra={}))

    def test_the_series_have_no_labels(self):
        text = self.text({"state": "scored", "score": 80.0, "coverage": 1.0})
        for line in text.splitlines():
            if line.startswith("ghamon_score"):
                self.assertNotIn("{", line)


class Mcp(unittest.TestCase):
    def test_the_tool_is_listed_and_answers_from_the_api(self):
        self.assertIn("get_score", [t["name"] for t in mcp_server.TOOLS])
        asked = []
        out = mcp_server.call("get_score", {}, {}, getter=lambda path: asked.append(path) or {"state": "scored", "score": 80, "letter": "B"})
        self.assertEqual(asked, ["/api/score"])
        self.assertEqual(json.loads(out)["score"], 80)

    def test_it_takes_no_arguments(self):
        tool = [t for t in mcp_server.TOOLS if t["name"] == "get_score"][0]
        self.assertEqual(tool["inputSchema"]["properties"], {})


class Demo(unittest.TestCase):
    def test_the_demo_answer_has_every_field_of_the_real_one(self):
        real = api.empty("x", engine.settings({}), "r")
        fake = demo_mode.score_answer(1_800_000_000)
        self.assertEqual(sorted(set(real) - set(fake)), [])
        self.assertEqual(fake["state"], "scored")
        self.assertFalse(fake["complete"])
        self.assertEqual(fake["missing_parts"], ["security"])
        self.assertTrue(all(0 <= p["score"] <= 100 for p in fake["parts"] if p["score"] is not None))

    def test_the_demo_history_is_a_line_of_points_in_order(self):
        points = demo_mode.score_history({}, 1_800_000_000)["points"]
        self.assertGreater(len(points), 10)
        ats = [p["at"] for p in points]
        self.assertEqual(ats, sorted(ats))
        self.assertEqual(set(points[0]), set(api.HISTORY_FIELDS))

    def test_the_handler_answers_the_demo_without_touching_a_storage(self):
        self.assertIn("--demo writes nothing: an invented score answers", inspect.getsource(actions_monitor.Handler))


class Handler(unittest.TestCase):
    def test_metrics_extra_carries_the_score_and_survives_a_storage_that_fails(self):
        old = actions_monitor.LITE["on"]
        actions_monitor.LITE["on"] = False
        self.addCleanup(lambda: actions_monitor.LITE.update(on=old))
        with mock.patch("github_actions_monitor.storage.runtime.process_storage", side_effect=RuntimeError("no storage")):
            self.assertIsNone(actions_monitor.score_metrics())
            self.assertIn("score", actions_monitor.metrics_extra())
        actions_monitor.LITE["on"] = True
        self.assertIsNone(actions_monitor.score_metrics())


if __name__ == "__main__":
    unittest.main()
