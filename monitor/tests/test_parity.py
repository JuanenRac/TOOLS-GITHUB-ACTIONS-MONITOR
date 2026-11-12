# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The header of the complete and of the lite edition must say the same thing about the same repositories: one rule for "red on main", one window and one reading depth for the figures."""
import subprocess
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import actions_monitor as am  # noqa: E402
import redrule  # noqa: E402
import sentinel_local  # noqa: E402

NOW = datetime.now(timezone.utc)


def stamp(hours):
    return (NOW - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(i, repo, name, conclusion, hours, branch="main", status="completed", seconds=60):
    return {"id": i, "repo": repo, "name": name, "path": ".github/workflows/%s.yml" % name, "status": status, "conclusion": conclusion, "branch": branch,
            "started": stamp(hours), "seconds": seconds, "url": "u%d" % i, "sha": "s%d" % i, "event": "push"}


RUNS = [
    run(1, "a", "ci", "failure", 1), run(2, "a", "ci", "success", 5),                      # red
    run(3, "a", "docs", "success", 2), run(4, "a", "docs", "failure", 9),                   # an old failure fixed: green
    run(5, "b", "ci", "failure", 3), run(6, "b", "ci", "cancelled", 1),                     # a cancelled run does not hide the failure: red
    run(7, "c", "ci", "failure", 2, branch="feature"), run(8, "c", "ci", "success", 6),     # red only on a branch: not red on main
    run(9, "d", "ci", "success", 30, seconds=600), run(10, "d", "ci", "success", 4, seconds=120),
]
BY_REPO = {}
for item in RUNS:
    BY_REPO.setdefault(item["repo"], []).append(item)


class OneRuleForRed(unittest.TestCase):
    def test_the_sentinel_and_the_lite_edition_name_the_same_workflows(self):
        full = sentinel_local.red_workflows(BY_REPO, {r: "main" for r in BY_REPO})
        lite, approx = redrule.red_workflows(BY_REPO, None, True)
        self.assertEqual([(r["repo"], r["workflow"]) for r in full], [("a", "ci"), ("b", "ci")])
        self.assertEqual([(r["repo"], r["workflow"]) for r in lite], [(r["repo"], r["workflow"]) for r in full])
        self.assertTrue(approx)             # the branch was guessed

    def test_a_sample_that_is_full_is_flagged_as_approximate(self):
        self.assertTrue(redrule.red_workflows(BY_REPO, {r: "main" for r in BY_REPO}, False, 2)[1])
        self.assertFalse(redrule.red_workflows(BY_REPO, {r: "main" for r in BY_REPO}, False, 50)[1])

    def test_the_branch_is_guessed_as_main_then_master_then_the_busiest(self):
        self.assertEqual(redrule.guess_default_branch([{"branch": "x"}, {"branch": "master"}]), "master")
        self.assertEqual(redrule.guess_default_branch([{"branch": "x"}, {"branch": "x"}, {"branch": "y"}]), "x")
        self.assertIsNone(redrule.guess_default_branch([]))

    def test_the_lite_edition_does_not_load_the_sentinel_for_it(self):
        code = "import sys; sys.path.insert(0, %r); import actions_monitor, redrule; sys.exit(1 if 'sentinel_local' in sys.modules else 0)" % str(HERE)
        done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)


class SameFigures(unittest.TestCase):
    def setUp(self):
        self.saved = (am.LITE["on"], dict(am.RUN_CACHE), list(am.ISSUE_CACHE["items"]), am.ISSUE_CACHE["at"])
        am.RUN_CACHE.clear()
        for repo, items in BY_REPO.items():
            am.RUN_CACHE[repo] = {"runs": [dict(x) for x in items], "at": time.time(), "error": None}
        am.ISSUE_CACHE.update({"items": [], "at": time.time()})

    def tearDown(self):
        am.LITE["on"] = self.saved[0]
        am.RUN_CACHE.clear()
        am.RUN_CACHE.update(self.saved[1])
        am.ISSUE_CACHE.update({"items": self.saved[2], "at": self.saved[3]})

    def build(self, lite, loading=False):
        am.LITE["on"] = lite
        rate = {"resources": {"core": {"remaining": 4439, "limit": 5000, "reset": int(time.time()) + 3000}}}
        with mock.patch.object(am, "gh", return_value=rate):
            return am.build({**am.DEFAULTS, "mode": "full"}, sorted(BY_REPO), time.time(), 0, loading, "3/9" if loading else "")

    def test_both_editions_give_the_same_header_figures(self):
        complete, lite = self.build(False)["figures"], self.build(True)["figures"]
        for key in ("active", "queued", "fail24", "ok24", "issues", "min24"):
            self.assertEqual(complete[key], lite[key], key)
        self.assertEqual((complete["fail24"], complete["ok24"]), (4, 4))
        self.assertEqual(complete["min24"], 10)         # the 30 hours old run is out of the 24 h window: 8 runs of 60 s and one of 120 s
        self.assertEqual(lite["red"], 2)
        self.assertTrue(lite["red_approx"])
        self.assertEqual(complete["red"], lite["red"])     # both editions report the same keys: the complete one takes the figure from the sentinel when it runs, else from the same small rule
        self.assertFalse(complete["red_approx"])

    def test_a_run_listed_twice_is_counted_once(self):
        am.RUN_CACHE["a"]["runs"].append(dict(BY_REPO["a"][0]))
        figures = self.build(False)["figures"]
        self.assertEqual(figures["fail24"], 4)

    def test_the_allowance_is_read_while_the_repositories_are_still_loading(self):
        for lite in (False, True):
            data = self.build(lite, loading=True)
            self.assertEqual((data["rate"]["remaining"], data["rate"]["limit"]), (4439, 5000))

    def test_the_lite_edition_reads_as_deep_as_the_complete_one_and_hides_the_signing_tile(self):
        saved = (am.LITE["on"], am.CONFIG_FILE)
        text = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn('config["mode"] = "full"', text)
        for key in ("runs_per_repo", "cold_runs_per_repo", "hot_hours", "stuck_minutes"):
            self.assertIn('"%s"' % key, text.split("LITE_INHERIT = ")[1].split("\n")[0])
        page = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('$("kp-sign").hidden=true', page)
        self.assertIn("d.figures", page)
        self.assertEqual(saved, (am.LITE["on"], am.CONFIG_FILE))


if __name__ == "__main__":
    unittest.main()
