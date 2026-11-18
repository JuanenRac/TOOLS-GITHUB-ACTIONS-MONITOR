#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/check_unfolded.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Measures that the one unfolded panel of each Sentinel tab reaches the bottom of its box.

    python tools/check_unfolded.py [--lang en de ...] [--size desktop mobile] [--json]

The demo monitor is started on a free port, a small relay adds the measuring script to the page and Microsoft Edge (or Chrome or Chromium) in headless mode opens it once per language and
window size. In the three Sentinel tabs (layers, collaboration, security) the script unfolds a single panel and checks that the end of its body reaches the bottom of the box of the tab
(a few pixels of padding are allowed) and that the body scrolls inside when its content is taller. Exit code 0 when all is well (or when there is no browser: it says so and skips), 1 otherwise.
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
LANGS = co.LANGS
TOLERANCE = 10          # pixels between the end of the unfolded body and the end of the box (the margin of the panel and its border)

PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),found=[],seen=[];
  const out=document.createElement("pre");out.id="unfolded-report";document.body.appendChild(out);
  try{
    await wait(1200);
    for(let i=0;i<60;i++){      /* wait for the condition (the data of the sentinels has arrived), not for a fixed time */
      await wait(250);
      if(typeof SENT!=="undefined"&&SENT&&typeof COLLAB!=="undefined"&&COLLAB&&typeof SECUR!=="undefined"&&SECUR&&typeof SDEL!=="undefined"&&SDEL&&typeof SSUP!=="undefined"&&SSUP)break;
    }
    const cases=[["sci","a1","s-details"],["scol","collab","s-details-collab"],["ssec","security","s-details-sec"],["sdel","delivery","s-details-del"],["ssup","supply","s-details-sup"]];
    for(const [tab,key,box] of cases){
      OPEN.clear();OPEN.add(key);
      try{renderSent();showTab(tab)}catch(e){}
      await wait(500);
      const holder=document.getElementById(box),d=holder&&holder.querySelector('details[data-k="'+key+'"]');
      if(!d||!d.open){found.push({kind:"no_panel",at:tab,detail:"the unfolded panel '"+key+"' was not found"});continue}
      const body=d.querySelector(".dbody"),h=holder.getBoundingClientRect(),cs=getComputedStyle(holder),last=holder.lastElementChild.getBoundingClientRect();
      const floor=h.bottom-parseFloat(cs.paddingBottom||0),scrolls=holder.scrollHeight>holder.clientHeight+1;
      seen.push(tab);
      /* the unfolded panel takes what the folded ones leave: the last thing in the box ends at the end of the box, or the box scrolls because there is more than fits */
      if(!scrolls&&floor-last.bottom>%(tol)d)found.push({kind:"short_of_the_bottom",at:tab,detail:"the content ends "+Math.round(floor-last.bottom)+"px above the end of the box"});
      if(!scrolls&&body.getBoundingClientRect().height<1)found.push({kind:"empty_body",at:tab,detail:"the unfolded body has no height"});
      if(document.documentElement.scrollWidth>document.documentElement.clientWidth+1)found.push({kind:"page_wider_than_window",at:tab,detail:document.documentElement.scrollWidth+">"+document.documentElement.clientWidth});
    }
    /* the daily trend has its own tab and every curve and figure fits the width of its frame */
    try{showTab("strend")}catch(e){}
    await wait(500);
    {const box=document.querySelector("#t-strend .body"),b=box&&box.getBoundingClientRect(),rows=[...document.querySelectorAll("#s-trend .spk")];
     if(!rows.length)found.push({kind:"no_trend",at:"strend",detail:"the daily trend has no rows in its tab"});
     else seen.push("strend");
     if(box&&box.scrollWidth>box.clientWidth+1)found.push({kind:"trend_overflows",at:"strend",detail:box.scrollWidth+">"+box.clientWidth});
     for(const r of rows){const q=r.getBoundingClientRect();if(b&&(q.right>b.right+1||q.left<b.left-1))found.push({kind:"trend_row_outside",at:"strend",detail:Math.round(q.right-b.right)+"px"});
       const v=r.querySelector("svg");if(v){const w=v.getBoundingClientRect().width;if(w<40)found.push({kind:"trend_curve_squeezed",at:"strend",detail:Math.round(w)+"px wide"})}}
     if(document.querySelector("#t-sent #s-trend"))found.push({kind:"trend_still_in_summary",at:"sent",detail:"the summary still holds the daily trend"})}
    out.textContent=JSON.stringify({ok:true,found:found,count:seen.length});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e),found:found})}
})();
</script>
""" % {"tol": TOLERANCE}


def run(langs=LANGS, sizes=("desktop", "mobile"), quiet=False):
    """{(lang, size): [problem, ...]}; None when there is no browser."""
    browser = co.edge()
    if not browser:
        return None
    port = co.free_port()
    demo = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_monitor.py"), str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
    server, results = None, {}
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
        base = f"http://127.0.0.1:{server.server_address[1]}/"
        for lang in langs:          # one window at a time
            for size in sizes:
                doc = co.measure(browser, f"{base}?lang={lang}&nowizard=1", co.SIZES[size], report="unfolded-report")
                if not doc.get("ok"):
                    raise RuntimeError("the measuring script failed: " + str(doc.get("error")))
                if not quiet:
                    print(lang, size, doc.get("count"), "tabs,", len(doc["found"]), "problems", flush=True)
                results[(lang, size)] = doc["found"]
    finally:
        if server:
            server.shutdown()
        demo.terminate()
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lang", nargs="*", default=list(LANGS))
    ap.add_argument("--size", nargs="*", default=["desktop", "mobile"], choices=list(co.SIZES))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    results = run(args.lang, args.size, quiet=args.json)
    if results is None:
        print("SKIP no browser (Edge, Chrome or Chromium) found")
        return 0
    problems = [(key, f) for key, found in sorted(results.items()) for f in found]
    if args.json:
        print(json.dumps({f"{lang}/{size}": found for (lang, size), found in sorted(results.items())}, ensure_ascii=False, indent=1))
    else:
        for (lang, size), f in problems:
            print(f"{lang} {size}: {f['kind']} at {f['at']}: {f['detail']}")
        print("PASS" if not problems else "FAIL", len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
