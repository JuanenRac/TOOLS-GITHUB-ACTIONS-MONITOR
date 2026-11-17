# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The button "Help of this tab" opens the topic of the tab that is open. The map from tab to topic is ONE table (`TAB_TOPICS` of helpdocs.py); a tab that is not in it used to open the first topic
of the Help ("GitHub Actions Monitor"). Two layers: parity (every tab of the page has a topic that exists and is not the first one) and the page in a real browser (every tab, one click on the
button, the topic that opens is the one of the table). A new tab, or a tab split in two, is added to the table; this test fails until it is."""
import json
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE.parent / "tools"))
import _testenv  # noqa: F401,E402
from github_actions_monitor.ui import helpdocs  # noqa: E402

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
FIRST = "readme"


def tabs_of_the_page():
    found = re.search(r"const TABS=LITE\?(\[[^\]]*\]):(\[[^\]]*\])", PAGE)
    assert found, "the list of tabs of the page"
    return sorted(set(json.loads(found.group(1))) | set(json.loads(found.group(2))))


class TheTable(unittest.TestCase):
    def test_every_tab_of_the_page_has_a_topic_and_it_is_not_the_first_one(self):
        topics = {t["id"] for t in json.loads((HERE / "docs" / "help_index.json").read_text(encoding="utf-8"))["topics"]}
        missing = [t for t in tabs_of_the_page() if t not in helpdocs.TAB_TOPICS]
        self.assertEqual(missing, [], "a tab without an entry in TAB_TOPICS opens the first topic of the Help")
        for tab in tabs_of_the_page():
            self.assertIn(helpdocs.TAB_TOPICS[tab], topics, tab)
            self.assertNotEqual(helpdocs.tab_topic(tab), FIRST, tab)

    def test_the_topic_of_every_entry_exists(self):
        topics = {t["id"] for t in json.loads((HERE / "docs" / "help_index.json").read_text(encoding="utf-8"))["topics"]}
        self.assertEqual([k for k, v in helpdocs.TAB_TOPICS.items() if v not in topics], [])

    def test_a_tab_that_is_not_in_the_table_falls_back_to_the_first_topic_and_to_nothing_else(self):
        self.assertEqual(helpdocs.tab_topic("no-such-tab"), FIRST)


PROBE = r"""<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out={tabs:{}};
  try{
    await wait(1500);
    for(const t of TABS){
      showTab(t);await wait(150);
      document.getElementById("help-tab").click();await wait(700);
      const h=document.querySelector("#help-body h2"),cur=document.querySelector("#help-list a[aria-current]");
      out.tabs[t]={cur:HELP.cur,list:cur?cur.dataset.topic:null,title:h?h.textContent:"",open:!document.getElementById("help-dlg").hidden};
      dlgClose("help");await wait(100);
    }
  }catch(e){out.error=String(e&&e.stack||e).slice(0,400)}
  out.errors=(window.__smoke&&window.__smoke.errors||[]).slice(0,10);
  const pre=document.createElement("pre");pre.id="help-report";pre.textContent=JSON.stringify(out);document.body.appendChild(pre);
})();
</script>"""


class TheButtonInABrowser(unittest.TestCase):
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
            cls.report = co.measure(co.edge(), f"http://127.0.0.1:{server.server_address[1]}/?lang=en&nowizard=1", co.SIZES["desktop"], report="help-report")
        finally:
            if server:
                server.shutdown()
                server.server_close()
            demo.terminate()
            try:
                demo.wait(timeout=15)
            except subprocess.TimeoutExpired:
                demo.kill()

    def test_every_tab_opens_the_topic_of_the_table_and_not_the_first_one(self):
        if self.report is None:
            if NEEDS_BROWSER:
                self.fail("there is no Edge, Chrome or Chromium on this computer and MONITOR_REQUIRE_BROWSER is set")
            self.skipTest("no Edge, Chrome or Chromium on this computer, or the tools folder is not there")
        self.assertNotIn("error", self.report)
        self.assertEqual(self.report["errors"], [])
        self.assertTrue(self.report["tabs"])
        for tab, got in self.report["tabs"].items():
            self.assertTrue(got["open"], tab)
            self.assertEqual(got["cur"], helpdocs.TAB_TOPICS[tab], tab)
            self.assertEqual(got["list"], got["cur"], tab)      # the list of topics marks the one that is shown
            self.assertNotEqual(got["cur"], FIRST, tab)
            self.assertTrue(got["title"].strip(), tab)
            self.assertNotEqual(got["title"], "GitHub Actions Monitor", tab)


if __name__ == "__main__":
    unittest.main()
