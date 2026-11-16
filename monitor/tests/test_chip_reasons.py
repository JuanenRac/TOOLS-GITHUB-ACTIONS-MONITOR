# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The two chips at the top right of the page that had no explanation: a group of the readiness without a number ("?") and the score of the account that stays "calibrating". A group counts only
the repositories that can have data: one with no workflow at all is not applicable and does not lower the coverage (it is listed apart); a group below the minimum says "not enough data" and why;
the score says how long the calibration lasts and when it ends, why there are not enough data and why a part is not counted. Unit tests of the server and the page in a real browser."""
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE.parent / "tools"))
import _testenv  # noqa: F401,E402
import test_readiness as tr  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import surface  # noqa: E402
from github_actions_monitor.scoring import api as score_api, engine  # noqa: E402
from github_actions_monitor.sentinels import readiness  # noqa: E402

try:
    import check_overflow as co  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    co = None
try:
    import check_page  # noqa: E402
except ImportError:
    check_page = None

NEEDS_BROWSER = bool(os.environ.get("MONITOR_REQUIRE_BROWSER"))
REPOS = ["ARMOR-A", "ARMOR-B", "ARMOR-C", "ARMOR-D", "ARMOR-E"]
SCAN = {"stacks": [], "dependabot_yml": False, "codeql_yml": False, "manifest": None, "changelog_top": None}
EMPTY = {"workflows": [], **SCAN}
CI = {"workflows": [surface.scan_workflow("on: push\n", "ci.yml")], **SCAN}


def armor(**over):
    snap = tr.snapshot(repos=REPOS, **over)
    return next(h for h in snap["a11"]["health"] if h["ecosystem"] == "armor"), snap


def runs_of(*names):
    return {r: ([tr.run(r, "CI", "success", "2026-11-04T09:00:00Z")] if r in names else []) for r in REPOS}


class TheCoverageOfAGroup(unittest.TestCase):
    def test_two_empty_repositories_do_not_lower_the_coverage_and_the_group_gets_a_number(self):
        scans = {"ARMOR-A": CI, "ARMOR-B": CI, "ARMOR-C": CI, "ARMOR-D": EMPTY, "ARMOR-E": EMPTY}
        row, snap = armor(runs=runs_of("ARMOR-A", "ARMOR-B"), scans=scans)      # 2 of 5 had data: 40 %, below the 50 % minimum
        self.assertEqual((row["applicable"], row["covered"], row["coverage"]), (3, 2, 0.67))
        self.assertEqual(row["no_ci"], ["ARMOR-D", "ARMOR-E"])
        self.assertEqual(row["missing"], ["ARMOR-C"])
        self.assertIsInstance(row["score"], int)
        self.assertIn("ARMOR-D", snap["a11"]["sections"][1]["note"])      # the repositories that do not count are named in the table

    def test_the_same_five_repositories_without_a_scan_keep_the_old_answer(self):
        row, _ = armor(runs=runs_of("ARMOR-A", "ARMOR-B"))      # nobody can tell that D and E have no workflow
        self.assertEqual((row["applicable"], row["covered"], row["coverage"]), (5, 2, 0.4))
        self.assertIsNone(row["score"])
        self.assertEqual(row["missing"], ["ARMOR-C", "ARMOR-D", "ARMOR-E"])
        self.assertEqual(row["no_ci"], [])

    def test_three_repositories_with_a_workflow_and_no_run_stay_without_enough_data(self):
        scans = {"ARMOR-A": CI, "ARMOR-B": CI, "ARMOR-C": CI, "ARMOR-D": EMPTY, "ARMOR-E": EMPTY}
        row, _ = armor(runs=runs_of(), scans=scans)
        self.assertEqual((row["applicable"], row["covered"]), (3, 0))
        self.assertIsNone(row["score"])
        self.assertEqual(row["missing"], ["ARMOR-A", "ARMOR-B", "ARMOR-C"])

    def test_a_repository_without_workflow_but_with_runs_is_applicable(self):
        scans = {r: EMPTY for r in REPOS}      # the clone shows no file, but GitHub has runs for it: it has a CI
        row, _ = armor(runs=runs_of("ARMOR-A", "ARMOR-B", "ARMOR-C"), scans=scans)
        self.assertEqual((row["applicable"], row["covered"], row["no_ci"]), (3, 3, ["ARMOR-D", "ARMOR-E"]))

    def test_a_group_where_nothing_is_applicable_has_no_score_and_no_division_by_zero(self):
        row, _ = armor(runs=runs_of(), scans={r: EMPTY for r in REPOS})
        self.assertEqual((row["applicable"], row["coverage"]), (0, 0.0))
        self.assertIsNone(row["score"])

    def test_the_default_minimum_is_not_changed(self):
        self.assertEqual(readiness.DEFAULTS["min_coverage"], 0.5)
        self.assertEqual(engine.DEFAULTS["calibrating_hours"], 24)


class TheScoreAnswer(unittest.TestCase):
    def test_the_answer_says_how_long_the_calibration_lasts(self):
        cfg = engine.settings({})
        quality = engine.compute({"samples": {}}, cfg, watched_hours=22.1)["data_quality"]
        self.assertEqual((quality["watched_hours"], quality["calibrating_hours"]), (22.1, 24))
        self.assertEqual(score_api.empty("acct", cfg, "no_snapshot_yet")["data_quality"]["calibrating_hours"], 24)

    def test_a_part_without_data_says_why(self):
        class Sentinel:
            enabled = True

            def __init__(self, scope, checked):
                self.status = {"repos_in_scope": scope, "repos_checked": checked}

            def get_status(self):
                return self.status

        answer = {"missing_parts": ["security"], "parts": [{"part": "collaboration", "available": False}, {"part": "speed", "available": False}]}
        why = lambda registry: {row["part"]: row for row in am.score_missing_detail(registry, {}, answer)}      # noqa: E731
        self.assertEqual(why({})["security"]["reason"], "sentinel_off")
        found = why({"security": Sentinel(0, 0), "collab": Sentinel(10, 3)})
        self.assertEqual((found["security"]["reason"], found["collaboration"]["reason"]), ("first_sweep", "partial"))
        self.assertEqual((found["collaboration"]["checked"], found["collaboration"]["scope"]), (3, 10))
        self.assertNotIn("speed", found)      # only the parts that depend on a sentinel
        self.assertEqual(why({"security": Sentinel(10, 10), "collab": Sentinel(10, 9)})["security"]["reason"], "next_pass")
        off = Sentinel(5, 5)
        off.enabled = False
        self.assertEqual(why({"security": off})["security"]["reason"], "sentinel_off")


PROBE = r"""<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out={chips:[],score:{}};
  try{
    await wait(1500);
    const mk=(e,score,extra)=>({ecosystem:e,score:score,coverage:0,applicable:0,covered:0,min_coverage:0.5,missing:[],no_ci:[],...extra});
    readyChips({a11:{enabled:true,warn_below:70,health:[
      mk("armor",null,{coverage:0.4,applicable:5,covered:2,missing:["ARMOR-A","ARMOR-B","ARMOR-C"],no_ci:["ARMOR-X","ARMOR-Y"]}),
      mk("urtc",97,{coverage:1,applicable:2,covered:2}),
      mk("hydra",null,{applicable:0,no_ci:["HYDRA-NEW"]}),
      {ecosystem:"eh3d",score:null}]}});
    out.chips=[...document.querySelectorAll("#k-ready .rdy-chip")].map(c=>({text:c.textContent.trim(),title:c.title,cls:c.className,dot:getComputedStyle(c.querySelector("i")).backgroundColor}));
    const q={runs:5,min_runs:20,coverage:0.3,min_coverage:0.5,reasons:[]};
    const chip=a=>{const d=document.createElement("div");d.innerHTML=scoreChip(a,[]);const c=d.firstElementChild;return {text:c.textContent.trim().replace(/\s+/g," "),title:c.title,bar:!!c.querySelector(".scr-bar"),pct:c.querySelector(".scr-bar")?c.querySelector(".scr-bar").getAttribute("aria-valuenow"):null}};
    const detail=[{part:"security",reason:"first_sweep",checked:0,scope:0},{part:"collaboration",reason:"first_sweep",checked:3,scope:9}];
    out.score.calibrating=chip({state:"calibrating",coverage:0.5,window_days:7,missing_parts:["security"],missing_detail:detail,parts:[],data_quality:{...q,watched_hours:22.1,calibrating_hours:24,reasons:["watched_briefly"]}});
    out.score.old=chip({state:"calibrating",coverage:0,window_days:7,missing_parts:[],parts:[],data_quality:{...q,watched_hours:null,reasons:["watched_briefly"]}});
    out.score.insufficient=chip({state:"insufficient_data",coverage:0.3,window_days:7,missing_parts:[],parts:[],data_quality:{...q,watched_hours:100,calibrating_hours:24,reasons:["few_runs","low_coverage"]}});
  }catch(e){out.error=String(e&&e.stack||e).slice(0,400)}
  out.errors=(window.__smoke&&window.__smoke.errors||[]).slice(0,10);
  const pre=document.createElement("pre");pre.id="chip-report";pre.textContent=JSON.stringify(out);document.body.appendChild(pre);
})();
</script>"""


class TheChipsInABrowser(unittest.TestCase):
    report = None

    @classmethod
    def setUpClass(cls):
        import socket
        import subprocess
        import time
        if co is None or check_page is None or not co.edge():
            return
        port = co.free_port()
        demo = subprocess.Popen([sys.executable, "-I", str(HERE.parent / "tools" / "demo_monitor.py"), str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
        server = None
        try:
            for _ in range(80):
                try:
                    socket.create_connection(("127.0.0.1", port), 0.5).close()
                    break
                except OSError:
                    time.sleep(0.5)
            else:
                raise RuntimeError("the demo monitor did not start")
            server = co.relay(port, probe=PROBE, head=check_page.HEAD.encode("utf-8"))
            cls.report = co.measure(co.edge(), f"http://127.0.0.1:{server.server_address[1]}/?lang=en&nowizard=1", co.SIZES["desktop"], report="chip-report")
        finally:
            if server:
                server.shutdown()
                server.server_close()
            demo.terminate()
            try:
                demo.wait(timeout=15)
            except subprocess.TimeoutExpired:
                demo.kill()

    def need(self):
        if self.report is None:
            if NEEDS_BROWSER:
                self.fail("there is no Edge, Chrome or Chromium on this computer and MONITOR_REQUIRE_BROWSER is set")
            self.skipTest("no Edge, Chrome or Chromium on this computer")
        self.assertNotIn("error", self.report)
        return self.report

    def test_a_group_below_the_minimum_says_not_enough_data_with_words_and_the_reason(self):
        chips = self.need()["chips"]
        self.assertEqual(len(chips), 4)
        armor = chips[0]
        self.assertIn("not enough data", armor["text"])
        self.assertNotIn("?", armor["text"])
        self.assertIn("2 of 5 repositories with data (40 %), minimum 50 %: missing ARMOR-A, ARMOR-B, ARMOR-C", armor["title"])
        self.assertIn("ARMOR-X, ARMOR-Y", armor["title"])
        self.assertIn("nodata", armor["cls"])
        self.assertTrue(chips[1]["text"].endswith("97"))
        self.assertNotIn("nodata", chips[1]["cls"])
        self.assertIn("nothing to measure", chips[2]["title"])
        self.assertIn("HYDRA-NEW", chips[2]["title"])
        self.assertIn("not enough data", chips[3]["text"])      # a server that does not send the numbers still says the words

    def test_the_score_says_how_long_the_calibration_is_missing_and_when_it_ends(self):
        calibrating = self.need()["score"]["calibrating"]
        self.assertIn("calibrating: 1 h 54 min left of 24 h", calibrating["text"])
        self.assertTrue(calibrating["bar"])
        self.assertEqual(calibrating["pct"], "92")
        self.assertIn("22.1 h of the 24 h", calibrating["title"])
        self.assertIn("security: waiting for the first sweep of the sentinel.", calibrating["title"])
        self.assertIn("collaboration: waiting for the first sweep of the sentinel (3 of 9 repositories read).", calibrating["title"])

    def test_an_old_snapshot_without_the_hours_still_says_calibrating(self):
        old = self.need()["score"]["old"]
        self.assertIn("calibrating", old["text"])
        self.assertFalse(old["bar"])

    def test_not_enough_data_says_what_is_missing(self):
        insufficient = self.need()["score"]["insufficient"]
        self.assertIn("not enough data", insufficient["text"])
        self.assertIn("Only 5 finished runs in the window; at least 20 are needed.", insufficient["title"])
        self.assertIn("weigh 30 % of the total; at least 50 % is needed.", insufficient["title"])

    def test_the_console_stays_clean(self):
        self.assertEqual(self.need().get("errors"), [])


if __name__ == "__main__":
    unittest.main()
