#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/check_motion.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Checks the life of the page in a real browser: the lamps are animated, every lamp has a shape (not only a colour), a lamp that changes plays one transition, and with the preference of
the user for less motion nothing moves at all.

    python tools/check_motion.py [--reduced]

The demo monitor is started on a free port with a small relay in front of it (the same one of tools/check_page.py); the script of the relay opens the tab of the sentinels, reads the style
the browser computed for every lamp and changes a lamp on purpose. Exit code 0 when everything is as expected; 1 otherwise; 0 with a message when there is no browser.
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_overflow as co  # noqa: E402
import check_page  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REPORT = "motion-report"
REDUCED_FLAG = "--force-prefers-reduced-motion"
#: the least lamps of the sentinels the demo draws
MIN_LAMPS = 5

PROBE = r"""<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const report={ok:true,reduced:matchMedia("(prefers-reduced-motion: reduce)").matches,lamps:[],bar:null,flip:null,errors:[]};
  try{
    await wait(1500);
    showTab("sent");await wait(3000);
    for(const b of document.querySelectorAll("#s-sems .sem")){
      const i=b.querySelector("i"),cs=getComputedStyle(i),after=getComputedStyle(i,"::after").content;
      report.lamps.push({level:[...b.classList].filter(c=>c!=="sem")[0]||"",animation:cs.animationName,glyph:after&&after!=="none"&&after!=='""'&&after!=="normal"?after:"",tip:b.dataset.tip||""});
    }
    const lamp=document.getElementById("sb-lamp");
    if(lamp){const cs=getComputedStyle(lamp);report.bar={animation:cs.animationName,glyph:getComputedStyle(lamp,"::after").content,aria:lamp.getAttribute("aria-hidden")}}
    const probe=document.querySelector("#s-sems .sem i");
    if(probe){
      lampTrack("probe",probe,"ok");lampTrack("probe",probe,"bad");
      report.flip={class:probe.classList.contains("lamp-flip"),animation:getComputedStyle(probe).animationName};
    }
    await wait(300);
  }catch(e){report.ok=false;report.error=String(e).slice(0,300)}
  report.errors=window.__smoke.errors.slice(0,20);
  const out=document.createElement("pre");out.id="motion-report";out.textContent=JSON.stringify(report);document.body.appendChild(out);
})();
</script>"""


def problems(report, reduced=False):
    """The list of what is wrong in the document the page wrote (empty = the life of the page is as expected)."""
    found = []
    if not report.get("ok"):
        found.append("the driver failed: " + str(report.get("error")))
    if bool(report.get("reduced")) != reduced:
        found.append("the browser did not take the preference of motion that was asked for")
    lamps = report.get("lamps") or []
    if len(lamps) < MIN_LAMPS:
        found.append(f"the sentinels drew {len(lamps)} lamps (at least {MIN_LAMPS})")
    for lamp in lamps:
        name = lamp.get("level") or "?"
        if not lamp.get("glyph"):
            found.append(f"a {name} lamp has no shape: its state would depend on the colour alone")
        if not lamp.get("tip"):
            found.append(f"a {name} lamp has no text with its state")
        moving = lamp.get("animation") not in (None, "", "none")
        if reduced and moving:
            found.append(f"a {name} lamp moves although the user asked for less motion ({lamp.get('animation')})")
        if not reduced and not moving and name != "unknown":
            found.append(f"a {name} lamp is not animated")
    bar = report.get("bar")
    if bar is None:
        found.append("the status bar has no lamp")
    else:
        if bar.get("aria") != "true":
            found.append("the lamp of the status bar must be hidden from screen readers (its text says the state)")
        moving = bar.get("animation") not in (None, "", "none")
        if reduced == moving:
            found.append("the lamp of the status bar " + ("moves although the user asked for less motion" if reduced else "is not animated"))
    flip = report.get("flip")
    if flip is None:
        found.append("there was no lamp to change on purpose")
    elif reduced:
        if flip.get("class") or flip.get("animation") not in (None, "", "none"):
            found.append("a lamp that changed played a transition although the user asked for less motion")
    elif not flip.get("class") or flip.get("animation") != "lamp-flip":
        found.append("a lamp that changed did not play its transition")
    found.extend(report.get("errors") or [])
    return found


def run(reduced=False):
    """The list of problems for the page of the demo monitor; None when there is no browser."""
    browser = co.edge()
    if not browser:
        return None
    port = co.free_port()
    demo = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_monitor.py"), str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
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
        url = f"http://127.0.0.1:{server.server_address[1]}/?lang=en&nowizard=1"
        report = co.measure(browser, url, co.SIZES["desktop"], report=REPORT, flags=(REDUCED_FLAG,) if reduced else ())
        return problems(report, reduced), report
    finally:
        if server:
            server.shutdown()
            server.server_close()
        demo.terminate()
        try:
            demo.wait(timeout=15)
        except subprocess.TimeoutExpired:
            demo.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reduced", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    result = run(args.reduced)
    if result is None:
        print("No browser found (Edge, Chrome or Chromium): nothing was checked.")
        return 0
    found, report = result
    if args.json:
        print(json.dumps(report, indent=1))
    for line in found:
        print(line)
    print("MOTION=FAIL" if found else "MOTION=PASS", len(found))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
