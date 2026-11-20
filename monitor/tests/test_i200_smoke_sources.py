# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The smoke of external sources: each format is judged by a pure function that these tests feed with samples (so the format is tested offline), the list of endpoints agrees with the code, a source that
cannot be reached is named, and the weekly workflow exists with nothing but a read of the repository."""
import re
import sys
import unittest
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE / "src"))

try:
    import smoke_sources as sm
except ImportError:      # the tools of the repository do not travel with the zip of the product
    sm = None

STATUS = {"status": {"indicator": "none", "description": "All Systems Operational"}, "components": [{"name": "Actions", "status": "operational"}], "incidents": []}
ADV = [{"ghsa_id": "GHSA-abcd-1234-wxyz", "severity": "high", "vulnerabilities": []}]


@unittest.skipIf(sm is None, "the tools of the repository are not in this folder")
class Formats(unittest.TestCase):
    def test_the_status_page(self):
        self.assertEqual(sm.check_status(STATUS), [])
        self.assertTrue(sm.check_status({"status": {"indicator": "purple", "description": "x"}, "components": [], "incidents": []}))
        self.assertTrue(sm.check_status({"components": [{"name": "A"}], "incidents": {}}))
        self.assertTrue(sm.check_status([]))

    def test_the_advisories(self):
        self.assertEqual(sm.check_advisories(ADV), [])
        self.assertTrue(sm.check_advisories([]))
        self.assertTrue(sm.check_advisories([{"id": 1}]))
        self.assertTrue(sm.check_advisories([{"ghsa_id": "GHSA-abcd-1234-wxyz", "severity": "spicy"}]))

    def test_the_description_of_the_api_must_have_every_endpoint_the_monitor_calls(self):
        paths = {}
        for method, path in sm.ENDPOINTS:
            paths.setdefault(path, {})[method] = {}
        self.assertEqual(sm.check_openapi({"paths": paths}), [])
        del paths["/rate_limit"]
        problems = sm.check_openapi({"paths": paths})
        self.assertEqual(len(problems), 1)
        self.assertIn("/rate_limit", problems[0])
        self.assertTrue(sm.check_openapi({}))

    def test_the_release_goes_through_the_function_of_the_update_notice(self):
        good = {"tag_name": "v2.1.7", "html_url": "https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases/tag/v2.1.7", "published_at": "2026-11-20T10:00:00Z"}
        self.assertEqual(sm.check_release(good), [])
        self.assertTrue(sm.check_release(dict(good, draft=True)))
        self.assertTrue(sm.check_release({"name": "no tag"}))

    def test_a_source_that_cannot_be_read_is_a_failure_with_its_name_and_the_rest_are_still_judged(self):
        def getter(url, timeout):
            if "githubstatus" in url:
                raise urllib.error.URLError("no route")
            return ADV
        out = sm.run(["status", "advisories"], 5, getter)
        self.assertIn("cannot read", out["status"][0])
        self.assertEqual(out["advisories"], [])

    def test_the_command_exits_1_on_a_failure_and_2_without_a_source(self):
        self.assertEqual(sm.main(["--only", "nothing"]), 2)


@unittest.skipIf(sm is None, "the tools of the repository are not in this folder")
class TheListAgreesWithTheCode(unittest.TestCase):
    def test_every_endpoint_of_the_list_is_still_named_in_the_code(self):
        code = "\n".join(p.read_text(encoding="utf-8") for p in (HERE / "src").rglob("*.py"))
        for method, path in sm.ENDPOINTS:
            if path.startswith("/repos/"):
                needle = path.replace("/repos/{owner}/{repo}/", "").replace("{run_id}", "").replace("{path}", "")
                stem = [s for s in needle.split("/") if s][0:2]
                self.assertIn("/".join(stem), code, path)
            else:
                self.assertIn(path.strip("/"), code, path)

    def test_the_actions_runs_the_monitor_writes_are_all_in_the_list(self):
        code = "\n".join(p.read_text(encoding="utf-8") for p in (HERE / "src").rglob("*.py"))
        written = set(re.findall(r"actions/runs/\{id\}/(rerun-failed-jobs|rerun|cancel)", code))
        listed = {path.rsplit("/", 1)[1] for method, path in sm.ENDPOINTS if method == "post"}
        self.assertEqual(written - listed, set())


class Workflow(unittest.TestCase):
    def test_it_runs_weekly_by_hand_too_and_reads_only_the_repository(self):
        path = ROOT / ".github" / "workflows" / "sources-smoke.yml"
        if not path.is_file():
            self.skipTest("the workflows are not part of the package")
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        self.assertRegex(text, r'cron: "\d+ \d+ \* \* 1"')
        self.assertIn("workflow_dispatch:", text)
        self.assertRegex(text, r"(?m)^permissions: \{\}$")
        self.assertEqual(re.findall(r"^\s+([a-z-]+): (read|write)", text.split("    permissions:\n")[1], re.M), [("contents", "read")])
        self.assertIn("python tools/smoke_sources.py", text)
        self.assertNotIn("secrets.", text)
        for item in re.findall(r"uses:\s*(\S+)", text):
            self.assertRegex(item, r"^actions/[a-z-]+@[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
