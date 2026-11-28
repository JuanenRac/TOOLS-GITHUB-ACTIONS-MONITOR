# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The window of a newer version in a real browser: it opens over the demo when the server says so, shows the summary as text, takes the focus, closes with Escape and does not come back in that
session, and stays away from a wall screen. Skipped without a browser or without the tools of the repository."""
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(TOOLS))

import _testenv  # noqa: F401,E402

try:
    import check_overflow as co  # noqa: E402
    import check_page  # noqa: E402
except ImportError:
    co = check_page = None

ANSWER = r"""<script>
(function(){const original=window.fetch;window.fetch=function(u){if(String(u).indexOf("/api/supply/update-notice")===0)
  return Promise.resolve(new Response(JSON.stringify({show:true,version:"9.9.9",current:"2.2.0",notes:"Line one\n<b>not html</b>",changelog:"https://github.com/x/y",url:"",command:""})));
  return original.apply(this,arguments)}})();
</script>"""
PROBE = r"""<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out={};
  const box=()=>document.getElementById("updn-dlg");
  try{
    for(let i=0;i<40&&!(box()&&!box().hidden);i++)await wait(250);
    out.open=!!box()&&!box().hidden;
    if(out.open){
      out.focus=document.activeElement&&document.activeElement.id;
      out.title=document.getElementById("updn-title").textContent;
      out.notes=document.getElementById("updn-notes").textContent;
      out.markup=!!document.querySelector("#updn-notes b");
      out.buttons=[...box().querySelectorAll("button")].map(b=>b.id);
      document.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true,cancelable:true}));
      await wait(50);
      out.closed=box().hidden;
      out.remembered=sessionStorage.getItem("am-upd-later");
    }
  }catch(e){out.error=String(e&&e.stack||e).slice(0,300)}
  const pre=document.createElement("pre");pre.id="notice-report";pre.textContent=JSON.stringify(out);document.body.appendChild(pre);
})();
</script>"""


class TheNoticeInABrowser(unittest.TestCase):
    report = None

    @classmethod
    def setUpClass(cls):
        if co is None or check_page is None or not co.edge():
            return
        port = co.free_port()
        demo = subprocess.Popen([sys.executable, "-I", str(TOOLS / "demo_monitor.py"), str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
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
            server = co.relay(port, probe=PROBE, head=check_page.HEAD.encode("utf-8") + ANSWER.encode("utf-8"))
            cls.report = co.measure(co.edge(), f"http://127.0.0.1:{server.server_address[1]}/?lang=en&nowizard=1", co.SIZES["desktop"], report="notice-report")
        finally:
            if server:
                server.shutdown()
                server.server_close()
            demo.terminate()
            demo.wait(timeout=20)

    def test_it_opens_takes_the_focus_shows_text_and_closes_with_escape(self):
        if self.report is None:
            self.skipTest("no browser or no tools of the repository here")
        report = self.report
        self.assertNotIn("error", report, report)
        self.assertTrue(report["open"], report)
        self.assertEqual(report["focus"], "updn-go")
        self.assertIn("9.9.9", report["title"])
        self.assertEqual((report["notes"], report["markup"]), ("Line one\n<b>not html</b>", False))
        self.assertEqual(report["buttons"], ["updn-go", "updn-later", "updn-never"])
        self.assertEqual((report["closed"], report["remembered"]), (True, "9.9.9"))


if __name__ == "__main__":
    unittest.main()
