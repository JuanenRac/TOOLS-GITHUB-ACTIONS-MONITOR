# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Fleet screen and the life of the wall screens in a real browser (Edge, Chrome or Chromium in headless mode, against the demo monitor): the fleet screen draws a card for each group with a square for each
healthy repository and a chip for each one that needs a look; "hide what is healthy" leaves only the chips; a figure that changes flashes where it changed, a new red sends a wave and a glance of chips says what
changed for the seconds it was asked to; the change from one screen to the next fades, slides or cuts; a quiet screen rests; and in a small window no text is smaller than the smallest letter asked for. Skipped when
there is no browser (and on a CI runner unless MONITOR_BROWSER_TESTS=1)."""
import json
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
    import check_overflow  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_overflow = None

HEAD = b"""<script>window.__errs=[];window.addEventListener("error",e=>window.__errs.push("error: "+e.message));window.addEventListener("unhandledrejection",e=>window.__errs.push("rejection: "+e.reason));</script>"""

PROBE_LIFE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const out=document.body.appendChild(Object.assign(document.createElement("pre"),{id:"life-report"}));
  const log={};
  try{
    const S=window.__screens,CFG=S.settings;
    for(let i=0;i<40&&!S.state.data;i++)await wait(100);
    clearTimeout(S.state.timer);S.state.moving=true;
    const tiles=(n,st)=>Array.from({length:n},(_,i)=>({name:"r"+i,state:st,running:0,red:0}));
    const fleet=(red,extra)=>Object.assign({schema:1,screen:"fleet",version:"x",epoch:1,names:"all",meta:{have_data:true,age_seconds:5,refresh_seconds:10,api:{remaining:4000,limit:5000,reset_seconds:100,low:false}},
      fleet:{total:30,red:red,stuck:0,waiting:0,green:30-red,idle:0},totals:{bad:red,warn:1,ok:20,unknown:0},alerts:{total:0,by_level:{critical:0,error:0,warning:0,info:0}},by:"ecosystem",more_groups:2,
      groups:[{key:"a",label:"Group A",repos:25,bad:red,warn:1,ok:20,unknown:0,hidden:3,tiles:tiles(20,"ok").concat(tiles(red,"bad"),tiles(1,"warn"))},{key:"b",label:"Group B",repos:5,bad:0,warn:0,ok:5,unknown:0,hidden:0,tiles:tiles(5,"ok")}]},extra||{});
    S.life.prev={};S.state.moving=false;S.show("fleet");S.state.moving=true;
    CFG.hide_healthy=false;CFG.life=true;CFG.glance_seconds=1;
    S.paint(fleet(1));await wait(500);
    log.groups=document.querySelectorAll("#f-groups .fg").length;
    log.squares=document.querySelectorAll("#f-groups .ft").length;
    log.chips=[...document.querySelectorAll("#f-groups .tn")].map(e=>e.className.replace("tn ","")+":"+e.textContent);
    log.more=(document.querySelector("#f-groups>.more")||{}).textContent||"";
    log.title=document.getElementById("h-title").textContent;
    log.glanceFirst=document.getElementById("glance").hidden;
    S.paint(fleet(3));await wait(250);
    log.glance=[document.getElementById("glance").hidden,document.getElementById("glance").textContent];
    log.changed=document.getElementById("ff-red").classList.contains("changed");
    log.wave=document.querySelectorAll(".wavefx").length>0;
    await wait(1400);
    log.glanceGone=document.getElementById("glance").hidden;
    CFG.glance_seconds=0;S.paint(fleet(4));await wait(150);
    log.noGlance=document.getElementById("glance").hidden;
    CFG.hide_healthy=true;S.paint(fleet(4));await wait(150);
    log.hiddenSquares=document.querySelectorAll("#f-groups .ft").length;
    log.hiddenChips=document.querySelectorAll("#f-groups .tn").length;
    await wait(1700);      /* the wave of the last red is gone */
    CFG.hide_healthy=false;CFG.life=false;CFG.glance_seconds=3;
    document.getElementById("ff-green").classList.remove("changed");
    S.paint(fleet(2));await wait(150);
    log.lifeOff=[document.getElementById("ff-green").classList.contains("changed"),document.querySelectorAll(".wavefx").length];
    /* a quiet screen rests, and wakes with the next change */
    CFG.idle_dim_minutes=1;S.life.changedAt=Date.now()-61000;S.state.prevRed=new Set();
    document.dispatchEvent(new Event("x"));
    await wait(1200);
    log.rests=document.body.classList.contains("idle");
    S.state.prevRed=new Set(["x"]);await wait(1200);
    log.restsWithRed=document.body.classList.contains("idle");
    S.state.prevRed=new Set();S.paint(fleet(5));await wait(1200);
    log.wakes=document.body.classList.contains("idle");
    /* the change from one screen to the next */
    const seen={},STATE_KIND=()=>S.state.kind;
    for(const mode of ["fade","slide","none"]){
      CFG.transition=mode;S.state.moving=false;S.show("fleet");S.state.moving=false;
      S.goTo("now");await wait(150);
      seen[mode]=[document.getElementById("s-fleet").classList.contains("out"),document.getElementById("s-fleet").classList.contains("slide"),STATE_KIND()];
      await wait(1200);
      seen[mode].push(STATE_KIND(),document.getElementById("s-now").classList.contains("enter"));
    }
    log.transition=seen;
    log.errors=window.__errs;
    out.textContent=JSON.stringify({ok:true,log:log});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e&&e.stack||e),log:log})}
})();
</script>
"""

PROBE_FONT = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const out=document.body.appendChild(Object.assign(document.createElement("pre"),{id:"font-report"}));
  try{
    for(let i=0;i<40&&!window.__screens.state.data;i++)await wait(100);
    await wait(800);
    const small=[];let least=1e9;
    const walker=document.createTreeWalker(document.getElementById("stage"),NodeFilter.SHOW_TEXT);
    for(let t=walker.nextNode();t;t=walker.nextNode()){
      if(!t.nodeValue.trim())continue;const el=t.parentElement;if(!el||el.closest("svg,script,style")||el.offsetParent===null)continue;
      const fs=parseFloat(getComputedStyle(el).fontSize);least=Math.min(least,fs);if(fs<parseFloat(new URLSearchParams(location.search).get("want"))-0.01)small.push(el.tagName+":"+t.nodeValue.trim().slice(0,20)+":"+fs.toFixed(1));
    }
    out.textContent=JSON.stringify({ok:true,least:least,small:small.slice(0,10),root:parseFloat(getComputedStyle(document.documentElement).fontSize),errors:window.__errs});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e&&e.stack||e)})}
})();
</script>
"""


def _port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@unittest.skipUnless(check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
@unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
class TheFleetScreenAndItsLife(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _port()
        cls.demo = subprocess.Popen([sys.executable, "-I", str(TOOLS / "demo_monitor.py"), str(cls.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
        for _ in range(80):
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("the demo monitor did not start")
        cls.life_relay = check_overflow.relay(cls.port, probe=PROBE_LIFE, head=HEAD)
        cls.font_relay = check_overflow.relay(cls.port, probe=PROBE_FONT, head=HEAD)
        cls.browser = check_overflow.edge()

    @classmethod
    def tearDownClass(cls):
        cls.life_relay.shutdown()
        cls.font_relay.shutdown()
        cls.demo.terminate()

    def test_the_fleet_screen_the_life_the_transitions_and_the_rest(self):
        base = f"http://127.0.0.1:{self.life_relay.server_address[1]}"
        report = check_overflow.measure(self.browser, base + "/screen/fleet?lang=en&refresh=120", (1920, 1080), report="life-report")
        self.assertTrue(report["ok"], report)
        log = report["log"]
        self.assertEqual(log["title"], "Fleet")
        self.assertEqual(log["groups"], 2)
        self.assertGreaterEqual(log["squares"], 1, "a square for the healthy repositories")
        self.assertEqual(sorted(c for c in log["chips"] if c.startswith("s-bad")), ["s-bad:r0"])
        self.assertIn("s-warn:r0", log["chips"])
        self.assertIn("2", log["more"], "the groups that did not fit are counted")
        self.assertTrue(log["glanceFirst"], "the first look only remembers: no glance")
        self.assertFalse(log["glance"][0], "something changed: the glance says it")
        self.assertIn("+2", log["glance"][1])
        self.assertTrue(log["changed"], "the figure that changed flashes")
        self.assertTrue(log["wave"], "a new red sends a wave")
        self.assertTrue(log["glanceGone"], "the glance goes after the seconds it was asked for")
        self.assertTrue(log["noGlance"], "0 seconds: no glance")
        self.assertEqual(log["hiddenSquares"], 0, "hide what is healthy: no squares")
        self.assertGreaterEqual(log["hiddenChips"], 2, "and the chips of what needs a look stay")
        self.assertEqual(log["lifeOff"], [False, 0], "life off: nothing flashes and no wave")
        self.assertTrue(log["rests"], "a quiet screen rests")
        self.assertFalse(log["restsWithRed"], "but not while something is red")
        self.assertFalse(log["wakes"], "and the next change wakes it")
        fade, slide, none = log["transition"]["fade"], log["transition"]["slide"], log["transition"]["none"]
        self.assertEqual(fade[:3], [True, False, "fleet"], "fade: the old screen fades out first")
        self.assertEqual(slide[:3], [True, True, "fleet"], "slide: the old screen slides out first")
        self.assertEqual(none[2], "now", "none: a cut, the new screen is already there")
        for mode in (fade, slide, none):
            self.assertEqual(mode[3], "now")
        self.assertEqual(log["errors"], [])

    def test_in_a_small_window_no_text_is_smaller_than_the_smallest_letter(self):
        base = f"http://127.0.0.1:{self.font_relay.server_address[1]}"
        for kind in ("overview", "fleet", "now", "sentinels"):
            report = check_overflow.measure(self.browser, base + f"/screen/{kind}?lang=en&refresh=120&want=11.99", (1280, 720), report="font-report")
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["small"], [], f"{kind}: {report['small']}")
            self.assertGreaterEqual(report["least"], 11.99, kind)
            self.assertEqual(report["errors"], [])


if __name__ == "__main__":
    unittest.main()
