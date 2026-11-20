#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/check_mobile.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The audit of the page on a phone, with a real browser: a window of 375 px, the compact view, every tab.

    python tools/check_mobile.py [--lang en es ...] [--json]

What it measures in every tab:
  * the page never scrolls sideways (the document is not wider than the window);
  * every control a finger has to press (buttons, selects, text fields, the tabs of the menu, the summaries) is at least 44 x 44 px, the size the guidelines of the platforms ask for;
  * the menu is a row at the top that scrolls sideways by itself (it is not a column that covers the page), and the tables scroll inside their own box;
  * the dialogs follow the height the on-screen keyboard leaves free (the variable --vvh is set from the visual viewport).
The demo monitor (tools/demo_monitor.py, invented data) is started on a free port with the same small relay as tools/check_overflow.py. Exit code 0 when nothing fails (or when there is no browser:
it says so and skips), 1 otherwise.
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

ROOT = Path(__file__).resolve().parent.parent
REPORT = "mobile-report"
WINDOW = (375, 812)
TARGET = 44
PROBE = r"""<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const out={ok:true,tabs:{},small:[],wide:[],compact:false,menu:null,errors:[]};
  const shown=e=>{for(let n=e;n&&n!==document.documentElement;n=n.parentElement){const s=getComputedStyle(n);if(s.display==="none"||s.visibility==="hidden")return false}const r=e.getBoundingClientRect();return r.width>0&&r.height>0};
  const inline=e=>e.tagName==="A"&&e.closest("p,li,dd,td,.help,.mut")!==null;
  function audit(tab){
    const wide=document.documentElement.scrollWidth-window.innerWidth;
    if(wide>1)out.wide.push({tab,by:wide});
    const sel="button,select,input:not([type=hidden]):not([type=checkbox]):not([type=radio]),summary,[role=tab],a.btn";
    document.querySelectorAll(sel).forEach(e=>{
      if(!shown(e)||inline(e)||e.closest("[hidden],.vh,.sr-only,#snd-lock"))return;
      const r=e.getBoundingClientRect();
      if(r.right<0||r.left>window.innerWidth)return;      /* part of a row that scrolls sideways: it is measured where it is drawn */
      if(r.height<${TARGET}-0.5||r.width<${TARGET}-0.5)out.small.push({tab,el:e.tagName.toLowerCase()+(e.id?"#"+e.id:"")+(e.className&&typeof e.className==="string"?"."+e.className.split(" ")[0]:""),w:Math.round(r.width),h:Math.round(r.height),text:(e.textContent||e.value||"").trim().slice(0,24)});
    });
  }
  try{
    await wait(2500);
    out.compact=document.documentElement.classList.contains("compact");
    const nav=document.querySelector("nav");if(nav){const s=getComputedStyle(nav);out.menu={direction:s.flexDirection,scrolls:/(auto|scroll)/.test(s.overflowX)}}
    out.vvh=getComputedStyle(document.documentElement).getPropertyValue("--vvh").trim();
    for(const t of TABS){try{showTab(t);await wait(500);audit(t);out.tabs[t]=true}catch(e){out.errors.push(t+": "+e)}}
  }catch(e){out.ok=false;out.errors.push(String(e))}
  const pre=document.createElement("pre");pre.id="mobile-report";pre.textContent=JSON.stringify(out);document.body.appendChild(pre);
})();
</script>""".replace("${TARGET}", str(TARGET))


def audit(lang="en", quiet=True):
    """The report of the probe for one language, or None when there is no browser."""
    browser = co.edge()
    if not browser:
        return None
    port = co.free_port()
    demo = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_monitor.py"), str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
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
        server = co.relay(port, probe=PROBE)
        url = f"http://127.0.0.1:{server.server_address[1]}/?lang={lang}&compact=1&nowizard=1"
        return co.measure(browser, url, WINDOW, report=REPORT)
    finally:
        if server:
            server.shutdown()
        demo.terminate()


def problems(report):
    found = []
    if not report.get("ok"):
        found.append("the probe failed: " + "; ".join(report.get("errors", [])))
    if not report.get("compact"):
        found.append("the compact view is not on in a window of %d px" % WINDOW[0])
    menu = report.get("menu") or {}
    if menu and (menu.get("direction") != "row" or not menu.get("scrolls")):
        found.append("the menu is not a row that scrolls sideways: %s" % menu)
    if not report.get("vvh"):
        found.append("--vvh (the height the on-screen keyboard leaves) is not set")
    found += [f"{w['tab']}: the page scrolls sideways by {w['by']} px" for w in report.get("wide", [])]
    found += [f"{s['tab']}: {s['el']} \"{s['text']}\" is {s['w']}x{s['h']} px, under {TARGET}" for s in report.get("small", [])]
    found += report.get("errors", [])[:5] if report.get("ok") else []
    return found


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", nargs="*", default=["en"], choices=list(co.LANGS))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    code = 0
    for lang in args.lang:
        report = audit(lang)
        if report is None:
            print("MOBILE=SKIP no browser (Edge, Chrome or Chromium) found")
            return 0
        found = problems(report)
        if args.json:
            print(json.dumps({"lang": lang, "report": report, "problems": found}, ensure_ascii=False))
        for line in found[:60]:
            print(f"MOBILE={lang} {line}")
        print(f"MOBILE={lang} {'PASS' if not found else 'FAIL %d' % len(found)}  tabs: {len(report.get('tabs', {}))}")
        code = code or (1 if found else 0)
    return code


if __name__ == "__main__":
    sys.exit(main())
