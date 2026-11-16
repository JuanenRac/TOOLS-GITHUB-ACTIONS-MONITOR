# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The ring "Result of the last 24 h": the server counts every finished run of the 24 hours (ok24, fail24 and done24), and the page draws the ring and the number in its centre from those
three figures, never from the (shorter) list of runs it receives; so "cancelled or other" cannot go negative and the legend always adds up to the centre. Two layers: the figures of the server,
and the page in a real browser with a list of 593 runs against 3196 + 127 of the server."""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE.parent / "tools"))
import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402

try:
    import check_overflow as co  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    co = None

NOW = datetime.now(timezone.utc)
NEEDS_BROWSER = bool(os.environ.get("MONITOR_REQUIRE_BROWSER"))


def run(i, hours, status="completed", conclusion="success"):
    return {"id": i, "repo": "r", "name": "ci", "status": status, "conclusion": conclusion, "started": (NOW - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ"), "seconds": 60}


class TheFiguresOfTheServer(unittest.TestCase):
    def test_done24_counts_every_finished_run_of_the_24_hours_and_the_rest_is_never_negative(self):
        runs = [run(1, 1), run(2, 2), run(3, 3, conclusion="failure"), run(4, 4, conclusion="cancelled"), run(5, 5, conclusion="skipped"), run(6, 1, status="in_progress", conclusion=None),
                run(7, 40), run(2, 2)]      # one still running, one older than a day, one listed twice
        figures = am.header_figures(runs, [], [], now=NOW.timestamp())
        self.assertEqual((figures["ok24"], figures["fail24"], figures["done24"]), (2, 1, 5))
        self.assertEqual(figures["done24"] - figures["ok24"] - figures["fail24"], 2)

    def test_no_runs_and_one_kind_of_run(self):
        none = am.header_figures([], [], [], now=NOW.timestamp())
        self.assertEqual((none["ok24"], none["fail24"], none["done24"]), (0, 0, 0))
        only = am.header_figures([run(i, 1) for i in range(1, 4)], [], [], now=NOW.timestamp())
        self.assertEqual((only["ok24"], only["fail24"], only["done24"]), (3, 0, 3))


#: the page receives 593 runs; the server counts 3196 + 127 + 77 of the last 24 hours (the shape of the figure the owner saw)
PROBE = r"""<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out={cases:{}};
  try{
    await wait(1500);
    const base=JSON.parse(JSON.stringify(DATA)),runs=[];base.figures=base.figures||{};base.runs=base.runs&&base.runs.length?base.runs:[{repo:"r",name:"ci",id:1}];
    for(let i=0;i<593;i++)runs.push({...base.runs[0],id:900000+i,status:"completed",conclusion:i%9?"success":"failure",started:new Date(Date.now()-i*60000).toISOString(),seconds:60});
    const cases={
      server:{runs:runs,runs_total:3400,figures:{...base.figures,ok24:3196,fail24:127,done24:3400}},
      oldserver:{runs:runs,runs_total:3400,figures:(({done24,...f})=>({...f,ok24:3196,fail24:127}))(base.figures)},
      inconsistent:{runs:runs,runs_total:593,figures:{...base.figures,ok24:3196,fail24:127,done24:100}},
      garbage:{runs:runs,runs_total:593,figures:{...base.figures,ok24:-5,fail24:"x",done24:null}},
      nothing:{runs:[],runs_total:0,figures:{...base.figures,ok24:0,fail24:0,done24:0}},
      single:{runs:runs,runs_total:593,figures:{...base.figures,ok24:50,fail24:0,done24:50}},
      zerofail:{runs:runs,runs_total:593,figures:{...base.figures,ok24:40,fail24:0,done24:50}},
    };
    for(const [name,patch] of Object.entries(cases)){
      render({...base,...patch});await wait(100);
      const el=document.getElementById("donut"),svg=el.querySelector("svg"),centre=svg&&svg.querySelector("[data-inside]");
      const legend=svg?[...svg.querySelectorAll("text:not([data-inside]) tspan")].map(t=>+t.textContent):[];
      out.cases[name]={text:el.innerText,centre:centre?+centre.textContent:null,legend:legend,paths:svg?svg.querySelectorAll("path,circle").length:0,sample:!!el.querySelector("[data-sample]"),
        outside:svg?[...svg.querySelectorAll("text")].some(t=>{const b=t.getBoundingClientRect(),s=svg.getBoundingClientRect();return b.width>0&&(b.right>s.right+1||b.left<s.left-1)}):false};
    }
  }catch(e){out.error=String(e&&e.stack||e).slice(0,400)}
  out.errors=(window.__smoke&&window.__smoke.errors||[]).slice(0,10);
  const pre=document.createElement("pre");pre.id="ring-report";pre.textContent=JSON.stringify(out);document.body.appendChild(pre);
})();
</script>"""


class TheRingInABrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import socket
        import subprocess
        import time
        import check_page
        cls.report = None
        if co is None or not co.edge():
            cls.why = "no browser"
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
            cls.report = co.measure(co.edge(), f"http://127.0.0.1:{server.server_address[1]}/?lang=en&nowizard=1", co.SIZES["desktop"], report="ring-report")
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
        return self.report["cases"]

    def test_a_list_shorter_than_the_server_total_gives_no_negative_figure(self):
        case = self.need()["server"]
        self.assertEqual(case["centre"], 3400)
        self.assertEqual(case["legend"], [3196, 127, 77])
        self.assertEqual(sum(case["legend"]), case["centre"])
        self.assertNotIn("-", case["text"])
        self.assertFalse(case["sample"], "the figures are the ones of the server: nothing to say about a sample")

    def test_a_server_without_the_total_counts_the_three_figures_on_the_list_and_says_so(self):
        case = self.need()["oldserver"]
        self.assertEqual(case["centre"], 593)
        self.assertEqual(sum(case["legend"]), 593)
        self.assertTrue(all(n >= 0 for n in case["legend"]))
        self.assertTrue(case["sample"])

    def test_figures_that_do_not_add_up_or_are_not_numbers_never_draw_a_false_ring(self):
        cases = self.need()
        for name in ("inconsistent", "garbage"):
            case = cases[name]
            self.assertTrue(all(n >= 0 for n in case["legend"]), name)
            self.assertEqual(sum(case["legend"]), case["centre"], name)
            self.assertNotIn("-", case["text"], name)
        self.assertEqual(cases["inconsistent"]["legend"], [3196, 127, 0])

    def test_no_run_one_segment_and_a_missing_segment(self):
        cases = self.need()
        self.assertEqual(cases["nothing"]["paths"], 0)
        self.assertIn("No finished runs", cases["nothing"]["text"])
        self.assertEqual(cases["single"]["legend"], [50, 0, 0])
        self.assertEqual(cases["single"]["paths"], 1)      # one full circle, not an arc of 360 degrees that the browser would not draw
        self.assertEqual(cases["zerofail"]["legend"], [40, 0, 10])
        self.assertEqual(cases["zerofail"]["paths"], 2)

    def test_no_label_leaves_the_card_and_the_console_stays_clean(self):
        report = self.report
        if report is None:
            self.skipTest("no browser")
        self.assertEqual(report.get("errors"), [])
        for name, case in report["cases"].items():
            self.assertFalse(case["outside"], name)


if __name__ == "__main__":
    unittest.main()
