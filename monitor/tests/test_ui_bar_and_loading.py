# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The bottom bar and the loading box, in a headless browser: the bar is ONE line at every width and says nothing the boxes at the top already say, and the
"loading repositories" box is gone once the load is finished.

Skipped when there is no Edge, Chrome or Chromium on this computer (and on the runners of the CI unless MONITOR_BROWSER_TESTS=1)."""
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
try:
    import check_overflow  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_overflow = None

PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out=document.getElementById("overflow-report")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"overflow-report"}));
  const shown=id=>{const e=document.getElementById(id);return !!e&&getComputedStyle(e).display!=="none"&&e.getBoundingClientRect().height>0};
  try{
    await wait(1500);
    const r={};
    const bar=document.getElementById("statusbar"),kids=[...bar.querySelectorAll(".sb-left,.sb-right,.sb-item,.sb-text")].filter(e=>e.getBoundingClientRect().height>0);
    const tops=kids.map(e=>{const b=e.getBoundingClientRect();return Math.round(b.top+b.height/2)});
    r.centres=[...new Set(tops)].length;                 /* every piece of the bar is centred on the same horizontal line */
    r.height=Math.round(bar.getBoundingClientRect().height);
    r.wide=bar.scrollWidth>bar.clientWidth+1;
    r.repeated=["sb-conn","sb-quota","sb-runs","sb-refresh","sb-repos"].filter(id=>document.getElementById(id));
    r.loaded_hidden=!shown("kt-loading");               /* the demo has finished loading */
    const d=Object.assign({},DATA);
    paintTiles(Object.assign({},d,{loading:"3 / 10"}));await wait(50);r.loading_shown=shown("kt-loading");
    paintTiles(Object.assign({},d,{loading:""}));await wait(50);r.loading_gone=!shown("kt-loading");
    out.textContent=JSON.stringify({ok:true,found:r});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e),found:{}})}
})();
</script>
"""


def _port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@unittest.skipUnless(check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
@unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
class BarAndLoadingInABrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _port()
        cls.demo = subprocess.Popen([sys.executable, "-I", str(TOOLS / "demo_monitor.py"), str(cls.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
        for _ in range(80):
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("the demo monitor did not start")
        cls.saved = check_overflow.PROBE
        check_overflow.PROBE = PROBE
        cls.relay = check_overflow.relay(cls.port)
        cls.base = f"http://127.0.0.1:{cls.relay.server_address[1]}/"

    @classmethod
    def tearDownClass(cls):
        check_overflow.PROBE = cls.saved
        cls.relay.shutdown()
        cls.demo.terminate()

    def look(self, lang, size):
        return check_overflow.measure(check_overflow.edge(), f"{self.base}?lang={lang}&nowizard=1", check_overflow.SIZES[size])

    def test_the_bar_is_one_line_wide_and_narrow_and_repeats_nothing(self):
        for lang in ("en", "de", "ja"):
            for size in ("desktop", "mobile"):
                found = self.look(lang, size)
                self.assertEqual(found["repeated"], [], (lang, size))
                self.assertEqual(found["centres"], 1, (lang, size, found))
                self.assertFalse(found["wide"], (lang, size))
                self.assertLessEqual(found["height"], 64, (lang, size, found))

    def test_the_loading_box_is_gone_when_the_load_is_finished(self):
        found = self.look("en", "desktop")
        self.assertTrue(found["loaded_hidden"], found)
        self.assertTrue(found["loading_shown"], found)      # while repositories load it is there
        self.assertTrue(found["loading_gone"], found)       # and it leaves with the last one
        self.assertTrue(json.dumps(found))


if __name__ == "__main__":
    unittest.main()
