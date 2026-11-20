# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The audit of dependencies is a gate of the CI: a vulnerability nobody suppressed fails, a suppression carries a reason and an expiry date, an expired one fails, a dead one (the vulnerability is gone)
fails, and the CI has a job that runs the suite with no network and a job that runs the audit."""
import datetime
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "tools"))

try:
    import audit_dependencies as ad
except ImportError:      # the tools of the repository do not travel with the zip of the product
    ad = None

TODAY = datetime.date(2026, 11, 20)
ANSWER = {"dependencies": [{"name": "rich", "version": "1.0", "vulns": []},
                           {"name": "textual", "version": "0.1", "vulns": [{"id": "PYSEC-1", "aliases": ["CVE-2026-1", "GHSA-aaaa"], "fix_versions": ["0.2"]}]}]}


@unittest.skipIf(ad is None, "the tools of the repository are not in this folder")
class Gate(unittest.TestCase):
    def sup(self, **over):
        return [dict({"id": "CVE-2026-1", "reason": "the vulnerable function is never called", "expires": "2026-12-31"}, **over)]

    def test_a_vulnerability_nobody_suppressed_fails_and_a_clean_answer_passes(self):
        problems, _ = ad.evaluate(ANSWER, [], TODAY)
        self.assertEqual(len(problems), 1)
        self.assertIn("textual 0.1", problems[0])
        self.assertIn("fixed in 0.2", problems[0])
        self.assertEqual(ad.evaluate({"dependencies": [{"name": "rich", "version": "1", "vulns": []}]}, [], TODAY), ([], []))

    def test_a_suppression_by_any_alias_covers_it_and_is_told_in_the_notes(self):
        for name in ("PYSEC-1", "CVE-2026-1", "GHSA-aaaa"):
            problems, notes = ad.evaluate(ANSWER, self.sup(id=name), TODAY)
            self.assertEqual(problems, [], name)
            self.assertIn("never called", notes[0])

    def test_an_expired_suppression_fails(self):
        problems, _ = ad.evaluate(ANSWER, self.sup(expires="2026-11-19"), TODAY)
        self.assertTrue(any("expired" in p for p in problems), problems)
        self.assertTrue(any("textual 0.1" in p for p in problems), "and the vulnerability is no longer covered")
        self.assertEqual(ad.evaluate(ANSWER, self.sup(expires="2026-11-20"), TODAY)[0], [])      # the last day still counts

    def test_a_dead_suppression_fails(self):
        problems, _ = ad.evaluate({"dependencies": [{"name": "rich", "version": "1", "vulns": []}]}, self.sup(), TODAY)
        self.assertEqual(len(problems), 1)
        self.assertIn("dead", problems[0])

    def test_a_suppression_too_far_away_is_refused(self):
        problems, _ = ad.evaluate(ANSWER, self.sup(expires="2027-12-31"), TODAY)
        self.assertTrue(any("days away" in p for p in problems), problems)

    def test_the_file_needs_id_reason_and_a_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            path.write_text(json.dumps([{"id": "X"}, {"id": "Y", "reason": "r", "expires": "tomorrow"}, {"id": "Z", "reason": "r", "expires": "2026-12-01"}]), encoding="utf-8")
            good, bad = ad.load_suppressions(path)
            self.assertEqual([g["id"] for g in good], ["Z"])
            self.assertEqual(len(bad), 2)
            path.write_text("{not json", encoding="utf-8")
            self.assertTrue(ad.load_suppressions(path)[1])
            self.assertEqual(ad.load_suppressions(Path(tmp) / "none.json"), ([], []))

    def test_the_command_judges_a_saved_answer_and_an_audit_that_did_not_run_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            answer, sup = Path(tmp) / "a.json", Path(tmp) / "s.json"
            answer.write_text(json.dumps(ANSWER), encoding="utf-8")
            sup.write_text("[]", encoding="utf-8")
            self.assertEqual(ad.main(["--check-file", str(answer), "--suppressions", str(sup)]), 1)
            answer.write_text(json.dumps({"dependencies": []}), encoding="utf-8")
            self.assertEqual(ad.main(["--check-file", str(answer), "--suppressions", str(sup)]), 0)
            self.assertEqual(ad.main(["--check-file", str(Path(tmp) / "missing.json"), "--suppressions", str(sup)]), 2)

    def test_the_real_file_of_suppressions_is_valid(self):
        good, bad = ad.load_suppressions(ROOT / ".github" / "audit-suppressions.json")
        self.assertEqual(bad, [])


class Workflow(unittest.TestCase):
    def setUp(self):
        path = ROOT / ".github" / "workflows" / "ci.yml"
        if not path.is_file():
            self.skipTest("the workflows are not part of the package")
        self.text = path.read_text(encoding="utf-8").replace("\r\n", "\n")

    def test_the_suite_also_runs_with_no_network_at_all(self):
        block = self.text.split("\n  offline:\n")[1].split("\n  pictures:\n")[0]
        self.assertIn("run_offline_tests.sh", block)
        script = (ROOT / "tools" / "run_offline_tests.sh").read_text(encoding="utf-8")
        self.assertIn("unshare --net", script)
        self.assertIn("ip link set lo up", script)
        self.assertIn("discover -s monitor/tests", block)
        self.assertIn("timeout-minutes:", block)

    def test_the_audit_of_dependencies_is_a_job_that_uses_the_tool_and_installs_nothing_it_does_not_pin(self):
        block = self.text.split("\n  dependencies:\n")[1].split("\n  pictures:\n")[0].split("\n  offline:\n")[0]
        self.assertIn("tools/audit_dependencies.py", block)
        self.assertRegex(block, r"pip-audit==\d+\.\d+\.\d+")
        self.assertNotIn("cache:", block, "no package cache in the workflow that also runs on tags")
        self.assertNotRegex(self.text.split("\n  dependencies:\n")[1], r"(?m)^\s+uses: (?!actions/)")


if __name__ == "__main__":
    unittest.main()
