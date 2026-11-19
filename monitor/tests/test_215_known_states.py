# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A status or a conclusion the monitor does not know breaks nothing: it is counted, shown as it came and never read as red or as green."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.data_pipeline import knownstates, signals  # noqa: E402


def run(number, status="completed", conclusion="success"):
    return {"id": number, "name": "ci", "status": status, "conclusion": conclusion, "created_at": "2026-01-02T03:04:05Z", "run_started_at": "2026-01-02T03:04:05Z", "updated_at": "2026-01-02T03:05:05Z",
            "event": "push", "head_branch": "main", "head_sha": "abcdef1234", "path": ".github/workflows/ci.yml", "html_url": "https://example.test/r", "run_attempt": 1}


class UnknownValues(unittest.TestCase):
    def setUp(self):
        knownstates.reset()

    def test_the_known_values_leave_no_trace(self):
        for status, conclusion in (("completed", "success"), ("in_progress", None), ("queued", ""), ("completed", "startup_failure"), ("waiting", None)):
            self.assertFalse(knownstates.observe(run(1, status, conclusion)))
        self.assertTrue(knownstates.is_empty(knownstates.drift()))

    def test_an_unknown_value_is_counted_by_name(self):
        knownstates.observe(run(1, "completed", "brand_new_result"))
        knownstates.observe(run(2, "completed", "brand_new_result"))
        knownstates.observe(run(3, "hibernating", None))
        self.assertEqual(knownstates.drift()["conclusion"], {"brand_new_result": 2})
        self.assertEqual(knownstates.drift()["status"], {"hibernating": 1})

    def test_the_memory_is_bounded_in_values_and_in_length(self):
        for n in range(200):
            knownstates.observe(run(n, "completed", f"odd_{n}" + "x" * 500))
        seen = knownstates.drift()["conclusion"]
        self.assertEqual(len(seen), knownstates.MAX_VALUES)
        self.assertTrue(all(len(k) <= knownstates.MAX_TEXT for k in seen))

    def test_a_list_with_odd_runs_is_read_and_the_good_runs_stay(self):
        data = {"workflow_runs": [run(1), run(2, "completed", "never_seen"), None, "text", {"name": "no number"}, {"id": True}, run(3, "far_future", None)]}
        runs = am.parse_runs("repo", data)
        self.assertEqual([r["id"] for r in runs], [1, 2, 3])
        self.assertEqual(runs[1]["conclusion"], "never_seen")
        self.assertEqual(knownstates.drift()["malformed"], 4)

    def test_the_brief_names_the_drift_and_says_nothing_without_it(self):
        found = [x for x in signals.inventory({"errors": {}, "rate": {}, "offline": {}, "etag": {}, "drift": {"status": {}, "conclusion": {"brand_new_result": 2}, "malformed": 1}}) if x["id"] == "schema.drift"]
        self.assertEqual(len(found), 1)
        self.assertIn("brand_new_result", found[0]["summary"])
        self.assertEqual(found[0]["level"], "info")
        quiet = [x for x in signals.inventory({"errors": {}, "rate": {}, "offline": {}, "etag": {}, "drift": {"status": {}, "conclusion": {}, "malformed": 0}}) if x["id"] == "schema.drift"]
        self.assertEqual(quiet, [])


if __name__ == "__main__":
    unittest.main()
