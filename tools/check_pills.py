#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/check_pills.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Measures the status labels (the lamp pills) inside the headings of the detail panels of the Sentinel tab: a label must stay on one line, never taller than it is wide.

    python tools/check_pills.py [--lang en de ...] [--size desktop mobile] [--json]

The demo monitor is started on a free port, a small relay adds the measuring script to the page and Microsoft Edge (or Chrome or Chromium) in headless mode opens it once per language and
window size. The script opens every panel of "Detail by layer" and, for every `summary > .sem`, checks that the label is not taller than wide and has the height of a single line (it was
split into one letter per line when the flex heading squeezed it). Exit code 0 when all is well (or when there is no browser: it says so and skips), 1 otherwise.
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
  const out=document.createElement("pre");out.id="pills-report";document.body.appendChild(out);
  try{
    await wait(1200);
    for(let i=0;i<60;i++){      /* wait for the condition (the data of the sentinel has arrived), not for a fixed time */
      try{OPEN.add("a2");renderSent();showTab("sci")}catch(e){}
      await wait(250);
      if(document.querySelectorAll("#s-details summary>.sem").length)break;
    }
    document.querySelectorAll("details[data-k]").forEach(d=>{d.open=true});
    await wait(400);
    const pills=[...document.querySelectorAll("summary>.sem")].filter(p=>p.getClientRects().length);
    if(!pills.length)found.push({kind:"no_pills",at:"summary>.sem",detail:"no status label was found to measure (in the page: "+document.querySelectorAll("summary>.sem").length+", panel shown: "+(document.getElementById("t-sci")||{classList:{contains:()=>"none"}}).classList.contains("on")+", sentinel data: "+(typeof SENT!=="undefined"&&!!SENT)+")"});
    for(const p of pills){
      const r=p.getBoundingClientRect(),s=getComputedStyle(p),line=parseFloat(s.lineHeight)||parseFloat(s.fontSize)*1.3;
      const name="summary>.sem '"+(p.textContent||"").trim().slice(0,24)+"'";
      if(r.height>r.width)found.push({kind:"taller_than_wide",at:name,detail:Math.round(r.width)+"x"+Math.round(r.height)});
      else if(r.height>line*2)found.push({kind:"several_lines",at:name,detail:Math.round(r.width)+"x"+Math.round(r.height)+" for a line of "+Math.round(line)});
      if(document.documentElement.scrollWidth>document.documentElement.clientWidth+1)found.push({kind:"page_wider_than_window",at:name,detail:document.documentElement.scrollWidth+">"+document.documentElement.clientWidth});
    }
    out.textContent=JSON.stringify({ok:true,found:found,count:pills.length});
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
        jobs = [(lang, size) for lang in langs for size in sizes]

        def one(job):
            lang, size = job
            doc = co.measure(browser, f"{base}?lang={lang}&nowizard=1", co.SIZES[size], report="pills-report")
            if not doc.get("ok"):
                raise RuntimeError("the measuring script failed: " + str(doc.get("error")))
            if not quiet:
                print(lang, size, doc.get("count"), "labels,", len(doc["found"]), "problems", flush=True)
            return job, doc["found"]
        with ThreadPoolExecutor(max_workers=3) as pool:
            for key, found in pool.map(one, jobs):
                results[key] = found
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
