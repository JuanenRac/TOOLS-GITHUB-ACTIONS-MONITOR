# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The rotating wall screen in a real browser (Edge, Chrome or Chromium in headless mode, against the demo monitor): the window turns through the three screens, a new red makes it jump to the screen that shows it
('Ahora' for a workflow that failed, 'Centinelas' for a panel in red) and stay there for the hold time or until the red is gone, a red that was already shown does not make it jump again until it changes or comes
back, what is red when the window opens is only the starting point, a second red waits for the first, and the turning goes on after. The page also wears the theme of its screen and shows the logo only where it
should. Skipped when there is no browser (and on a CI runner unless MONITOR_BROWSER_TESTS=1)."""
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

REPORT = "rotation-report"

# before the scripts of the page: what the monitor answers for 'now' and for 'sentinels' can be replaced by the test, so the reds are the ones it says and not the ones of the demo
HEAD = b"""<script>
window.__fake={now:null,sentinels:null};window.__errs=[];window.__reqs=[];
window.addEventListener("error",e=>window.__errs.push("error: "+e.message));
window.addEventListener("unhandledrejection",e=>window.__errs.push("rejection: "+e.reason));
const __o=window.fetch;
window.fetch=async function(u){window.__reqs.push(String(u));const r=await __o.apply(this,arguments);const m=/screen=(\\w+)/.exec(String(u));
  if(m&&window.__fake[m[1]]){const j=await r.clone().json();Object.assign(j,window.__fake[m[1]]);
    if(m[1]==="sentinels"&&j.cards){const bad=window.__fake.sentinels.bad||[];j.cards=j.cards.map(c=>Object.assign({},c,{level:bad.indexOf(c.id)>=0?"bad":"ok"}));}
    return new Response(JSON.stringify(j),{status:200,headers:{"Content-Type":"application/json"}})}
  return r};
</script>"""

PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const out=document.body.appendChild(Object.assign(document.createElement("pre"),{id:"rotation-report"}));
  const log={};
  try{
    const S=window.__screens,P=S.params,kind=()=>S.state.kind,hold=()=>!!S.turn.hold;
    const fail=(...names)=>({failures:names.map(n=>({repo:"r1",workflow:n,ago:60,attempt:1}))});
    const feed=async k=>{const r=await fetch("/api/screens/data?screen="+k+"&lang=en");S.observe(k,await r.json())};
    for(let i=0;i<40&&!S.state.data;i++)await wait(100);
    log.first=kind();
    P.jump=true;P.hold=2;P.rotate=0;
    window.__fake.now=fail("CI");await feed("now");await wait(1000);
    log.baseline=[kind(),hold()];
    window.__fake.now=fail("CI","Deploy");await feed("now");await wait(1500);
    log.jumped=[kind(),hold()];
    await wait(2300);
    log.afterHold=[kind(),hold()];
    await feed("now");
    log.again=[kind(),hold()];
    window.__fake.now=fail("Build2");await feed("now");
    log.changed=hold();
    window.__fake.now=fail();await feed("now");
    log.gone=hold();
    window.__fake.now=fail("Build2");await feed("now");
    log.back=hold();
    window.__fake.now=fail();await feed("now");
    window.__fake.sentinels={bad:[]};await feed("sentinels");
    window.__fake.sentinels={bad:["a2"]};await feed("sentinels");await wait(1500);
    log.sentinels=[kind(),hold(),S.turn.hold&&S.turn.hold.kind];
    window.__fake.now=fail("Z");await feed("now");
    log.queued=[kind(),S.turn.pending.length];
    window.__fake.sentinels={bad:[]};await feed("sentinels");await wait(1500);
    log.next=[kind(),S.turn.hold&&S.turn.hold.kind,S.turn.pending.length];
    window.__fake.now=fail();await feed("now");
    log.released=hold();
    P.rotate=2;S.schedule();
    const seen=[kind()];
    for(let i=0;i<9;i++){await wait(500);if(seen[seen.length-1]!==kind())seen.push(kind())}
    log.turned=seen;
    log.theme=[document.documentElement.dataset.theme,document.documentElement.dataset.studio||""];
    log.logo=[...document.querySelectorAll(".orglogo")].map(e=>[e.id,e.hidden]);
    log.errors=window.__errs;log.reqs=window.__reqs;
    out.textContent=JSON.stringify({ok:true,log:log});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e),log:log})}
})();
</script>
"""


def _port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@unittest.skipUnless(check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
@unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
class TheRotatingScreen(unittest.TestCase):
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
        cls.relay = check_overflow.relay(cls.port, probe=PROBE, head=HEAD)
        cls.base = f"http://127.0.0.1:{cls.relay.server_address[1]}"
        cls.browser = check_overflow.edge()

    @classmethod
    def tearDownClass(cls):
        cls.relay.shutdown()
        cls.demo.terminate()

    def test_a_new_red_jumps_to_its_screen_stays_and_goes_on_turning(self):
        report = check_overflow.measure(self.browser, self.base + "/screen/overview?lang=en&refresh=120&theme=Armor", (1920, 1080), report=REPORT)
        self.assertTrue(report["ok"], report)
        log = report["log"]
        self.assertEqual(log["first"], "overview")
        self.assertEqual(log["baseline"], ["overview", False], "what is red when the window opens is the starting point: no jump")
        self.assertEqual(log["jumped"], ["now", True], "a workflow that failed: the screen that shows it, held")
        self.assertEqual(log["afterHold"], ["now", False], "the hold time is over")
        self.assertEqual(log["again"][1], False, "a red already shown does not make it jump again")
        self.assertTrue(log["changed"], "a red that changed does")
        self.assertFalse(log["gone"], "the red went away: the stay ends before its time")
        self.assertTrue(log["back"], "and one that comes back jumps again")
        self.assertEqual(log["sentinels"], ["sentinels", True, "sentinels"], "a panel in red: the screen of the sentinels")
        self.assertEqual(log["queued"], ["sentinels", 1], "a second red waits for the first")
        self.assertEqual(log["next"], ["now", "now", 0], "the first one is gone: the second takes its turn")
        self.assertFalse(log["released"])
        self.assertGreaterEqual(len(log["turned"]), 2, "after the stay it goes on turning: " + json.dumps(log["turned"]))
        self.assertEqual(log["theme"], ["Armor", "1"], "the theme of the address is worn by every screen of the window")
        self.assertTrue(log["logo"] and all(hidden for _, hidden in log["logo"]), "no logo uploaded: every box stays hidden")
        self.assertEqual(log["errors"], [])
        for url in log["reqs"]:
            self.assertTrue(url.startswith("/api/screens/data?screen="), url)


if __name__ == "__main__":
    unittest.main()
