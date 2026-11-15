#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/check_charts.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Measures the geometry of the pictures of the Charts tab in a real browser: nothing of a drawing may leave its box.

    python tools/check_charts.py [--lang en de ...] [--size desktop mobile] [--json]

The demo monitor (tools/demo_monitor.py, invented data) is started on a free port, a small relay adds a measuring script to the page (the same way as check_overflow.py) and Microsoft Edge,
Chrome or Chromium in headless mode opens the Charts tab once per language and size, in the light and the dark theme. For every drawing of the tab (the ring of the result of the last 24 hours,
the bars of the success rate, the bars of the durations, the timeline) it checks that
  - the drawing is inside the box that holds it and the box does not cut it (no scroll, no clipped height);
  - every mark and every label of the drawing is inside the drawing (a bar, an axis label or a legend text that falls outside the picture is a failure);
  - the labels do not lie on top of the marks they explain (the legend of the ring does not touch the ring).
Exit code 0 when everything fits (or when there is no browser: it says so and skips), 1 otherwise.
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

PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),found=[];
  const out=document.createElement("pre");out.id="charts-report";document.body.appendChild(out);
  const R=e=>e.getBoundingClientRect();
  const inside=(a,b,tol)=>a.left>=b.left-tol&&a.right<=b.right+tol&&a.top>=b.top-tol&&a.bottom<=b.bottom+tol;
  const name=e=>{let p=[];for(let n=e;n&&n.id!=="app"&&n!==document.body&&p.length<3;n=n.parentElement)p.push(n.tagName.toLowerCase()+(n.id?"#"+n.id:""));return p.join("<")};
  function add(kind,e,detail){found.push({kind,at:name(e),detail})}
  function check(){
    const tab=document.querySelector("[data-tabpane=charts],#t-charts,#charts")||document.body;
    for(const svg of document.querySelectorAll("#donut svg, #rates svg, #durs svg, #timeline svg, #tl svg, .charts svg, section svg")){
      if(svg.closest(".ico,.tile,button,.hcorner,nav,aside")||svg.classList.contains("ico")||!svg.getClientRects().length)continue;
      const section=svg.closest("section")||svg.parentElement,host=svg.parentElement,sr=R(svg),hr=R(host),sec=R(section);
      if(sr.width<2||sr.height<2)continue;
      if(!inside(sr,hr,1.5)&&getComputedStyle(host).overflow!=="visible")add("picture_cut",svg,Math.round(sr.left)+","+Math.round(sr.top)+","+Math.round(sr.right)+","+Math.round(sr.bottom)+" vs "+Math.round(hr.left)+","+Math.round(hr.top)+","+Math.round(hr.right)+","+Math.round(hr.bottom));
      if(!inside(sr,sec,1.5))add("picture_outside_section",svg,Math.round(sr.bottom)+" vs "+Math.round(sec.bottom)+" / "+Math.round(sr.right)+" vs "+Math.round(sec.right));
      if(host.scrollHeight>host.clientHeight+1.5&&getComputedStyle(host).overflowY!=="visible")add("box_cuts_picture",host,host.scrollHeight+">"+host.clientHeight);
      if(host.scrollWidth>host.clientWidth+1.5&&getComputedStyle(host).overflowX!=="visible")add("box_cuts_picture_wide",host,host.scrollWidth+">"+host.clientWidth);
      const marks=[...svg.querySelectorAll("rect,path,circle,line,polyline,text")];
      for(const m of marks){const r=R(m);if(r.width<=0&&r.height<=0)continue;if(m.closest("defs"))continue;
        if(!inside(r,sr,1.5)){add(m.tagName==="text"?"label_outside":"mark_outside",m,Math.round(r.left)+".."+Math.round(r.right)+" x "+Math.round(r.top)+".."+Math.round(r.bottom)+" vs "+Math.round(sr.left)+".."+Math.round(sr.right)+" x "+Math.round(sr.top)+".."+Math.round(sr.bottom)+(m.textContent&&m.tagName==="text"?" '"+m.textContent.trim().slice(0,24)+"'":""))}}
      const texts=marks.filter(m=>m.tagName==="text"&&m.textContent.trim()),shapes=marks.filter(m=>m.tagName==="path"||m.tagName==="circle");
      for(const t of texts)for(const s of shapes){const a=R(t),b=R(s);if(a.width<=0||b.width<=0)continue;const ox=Math.min(a.right,b.right)-Math.max(a.left,b.left),oy=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top);
        if(s.tagName==="path"&&s.getAttribute("stroke-width")&&ox>6&&oy>6&&!t.hasAttribute("data-inside")&&(t.getAttribute("text-anchor")!=="middle"))add("label_on_mark",t,(t.textContent||"").trim().slice(0,24)+" overlaps a mark by "+Math.round(ox)+"x"+Math.round(oy))}
    }
  }
  try{
    await wait(1200);
    showTab("charts");await wait(700);
    check();
    out.textContent=JSON.stringify({ok:true,found:found});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e),found:found})}
})();
</script>
"""


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
        from concurrent.futures import ThreadPoolExecutor
        jobs = [(lang, size, theme) for lang in langs for size in sizes for theme in ("light", "dark")]

        def one(job):
            lang, size, theme = job
            doc = co.measure(browser, f"{base}?lang={lang}&theme={theme}&nowizard=1", co.SIZES[size], report="charts-report")
            if not doc.get("ok"):
                raise RuntimeError("the measuring script failed: " + str(doc.get("error")))
            if not quiet:
                print(lang, size, theme, len(doc["found"]), "problems", flush=True)
            return job, doc["found"]
        with ThreadPoolExecutor(max_workers=3) as pool:
            for (lang, size, theme), found in pool.map(one, jobs):
                results.setdefault((lang, size), []).extend({**f, "theme": theme} for f in found)
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
            print(f"{lang} {size} {f['theme']}: {f['kind']} at {f['at']}: {f['detail']}")
        print("PASS" if not problems else "FAIL", len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
