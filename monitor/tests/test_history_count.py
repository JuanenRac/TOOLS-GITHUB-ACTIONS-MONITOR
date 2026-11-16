# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The History tab draws "Showing 200 of N" ONCE. The tools of its table (the list of columns and the hint) are drawn again only when the order or the columns change, and the count used to be
appended to them at every refresh, so thousands of copies piled up next to the list of columns. The page is opened in a real browser, the table is drawn many times (refresh, filter, columns,
language) and there must be exactly one count and one hint; the same goes for the tools of the repositories table."""
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE.parent / "tools"))
import _testenv  # noqa: F401,E402

try:
    import check_overflow as co  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    co = None
try:
    import check_page  # noqa: E402
except ImportError:
    check_page = None

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
NEEDS_BROWSER = bool(os.environ.get("MONITOR_REQUIRE_BROWSER"))


class TheSource(unittest.TestCase):
    def test_nothing_appends_the_count_without_replacing_it(self):
        body = PAGE[PAGE.index("function renderHistory()"):PAGE.index('["f-repo","f-res"]')]
        self.assertNotIn("appendChild", body, "the count goes through histCount, which replaces it")
        self.assertIn("histCount(", body)
        self.assertEqual(PAGE.count('n.id="hist-count"'), 1)


PROBE = r"""<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out={steps:[]};
  try{
    await wait(1500);
    const base=JSON.parse(JSON.stringify(DATA)),run=base.runs[0],runs=[];
    for(let i=0;i<600;i++)runs.push({...run,id:700000+i,status:"completed",conclusion:i%7?"success":"failure",started:new Date(Date.now()-i*60000).toISOString()});
    base.runs=runs;base.runs_total=5704;
    const tools=$("hist-tools"),look=label=>{const t=tools.textContent;out.steps.push({label:label,counts:tools.querySelectorAll("#hist-count").length,hints:t.split(T("ui.tbl_sort_hint")).length-1,showing:t.split(T("ui.n_showing",{n:200,total:5704})).length-1,
      showingAny:(t.match(/Showing/g)||[]).length,text:t.length,rows:$("hist").querySelectorAll("tr").length});};
    DATA=base;
    for(let i=0;i<30;i++)renderHistory();look("30 refreshes");
    for(let i=0;i<10;i++){render({...base,runs:runs.slice(0)});}look("10 full renders");
    document.querySelectorAll("#hist-tools input[data-c]:not(:checked):not(:disabled)").forEach(i=>i.click());await wait(50);
    for(let i=0;i<10;i++)renderHistory();look("all columns, 10 renders");
    $("f-res").value="failure";renderHistory();look("filter that shortens the list below 200");
    $("f-res").value="";$("f-q").value="no-run-has-this";renderHistory();look("filter without rows");
    $("f-q").value="";renderHistory();renderHistory();look("filter cleared");
    const th=document.querySelector("#hist-head th");th.click();await wait(50);for(let i=0;i<5;i++)renderHistory();look("one order, 5 renders");
    out.cols=document.querySelectorAll("#hist-tools input[data-c]").length;
    out.repoHints=document.getElementById("repos-tools").textContent.split(T("ui.tbl_sort_hint")).length-1;
  }catch(e){out.error=String(e&&e.stack||e).slice(0,400)}
  out.errors=(window.__smoke&&window.__smoke.errors||[]).slice(0,10);
  const pre=document.createElement("pre");pre.id="count-report";pre.textContent=JSON.stringify(out);document.body.appendChild(pre);
})();
</script>"""


class TheTableInABrowser(unittest.TestCase):
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
            cls.report = co.measure(co.edge(), f"http://127.0.0.1:{server.server_address[1]}/?lang=en&nowizard=1", co.SIZES["desktop"], report="count-report")
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
        return {step["label"]: step for step in self.report["steps"]}

    def test_after_many_renders_there_is_one_count_and_one_hint(self):
        steps = self.need()
        for label in ("30 refreshes", "10 full renders", "all columns, 10 renders"):
            step = steps[label]
            self.assertEqual((step["counts"], step["hints"], step["showing"], step["showingAny"]), (1, 1, 1, 1), label)
            self.assertLess(step["text"], 600, label)      # the list of columns, the hint and the count: not thousands of characters

    def test_the_count_disappears_when_the_list_is_whole_and_comes_back(self):
        steps = self.need()
        self.assertEqual(steps["filter that shortens the list below 200"]["counts"], 0)      # a filtered list that fits in 200 rows says nothing
        self.assertEqual(steps["filter without rows"]["counts"], 0)
        self.assertEqual(steps["filter cleared"]["counts"], 1)
        self.assertEqual(steps["filter cleared"]["showingAny"], 1)

    def test_the_order_changes_the_tools_and_still_leaves_one_count(self):
        step = self.need()["one order, 5 renders"]
        self.assertEqual((step["counts"], step["showingAny"]), (1, 1))
        self.assertEqual(step["hints"], 0)      # with an order the hint becomes "Order: ..."

    def test_the_repositories_table_has_one_hint_and_the_console_is_clean(self):
        self.need()
        self.assertEqual(self.report["repoHints"], 1)
        self.assertEqual(self.report["errors"], [])


if __name__ == "__main__":
    unittest.main()
