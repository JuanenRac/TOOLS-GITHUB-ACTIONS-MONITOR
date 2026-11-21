#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/check_page.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Smoke test of the page of the monitor in a real browser: it must open, draw every tab and every sub-tab of Settings with a minimum of fields and raise no error.

    python tools/check_page.py [--lang en ...] [--size desktop mobile] [--json]

The demo monitor (tools/demo_monitor.py, invented data) is started on a free port and a small relay in front of it adds two scripts to the page: one right after <head>, so that it runs before
any script of the page and records every `error` event, every unhandled promise rejection, every `console.error` and every answer of the monitor with a 5xx status; one before </body> that goes through every tab, every sub-tab of
Settings and the three windows, and counts what each one drew. Edge, Chrome or Chromium opens it in headless mode. Exit code 0 when everything is drawn and nothing failed; 1 otherwise; 0 with
a message when there is no browser (the CI has one and the test that wraps this script fails there if it is missing).
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

os.environ.setdefault("MONITOR_VT_BUDGET", "45000")      # the walk through every tab, every sub-tab of Settings and the live checks takes virtual time
ROOT = Path(__file__).resolve().parent.parent
REPORT = "smoke-report"
#: the least fields a sub-tab of Settings must draw (the demo draws about twice as many; a sub-tab that loses half of its fields is broken). A sub-tab that is not listed needs at least one.
MIN_FIELDS = {"interface": 3, "basic": 9, "general": 11, "polling": 7, "cache": 2, "quota": 11, "sentinel": 26, "surface": 28, "readiness": 9, "paths": 6, "outputs": 3, "ai": 26, "webhook": 4,
              "notify": 15, "analytics": 5, "lint": 9, "advanced": 22, "console": 2}      # "interface" is kept in the browser: its controls are counted, not the fields of the file
MIN_TOTAL = 200
MIN_TEXT = 40      # characters a tab must show once it is open
MIN_TEXT_COMPACT = 15      # the same in Japanese and Chinese, where a line says in a third of the characters what a line of the other languages says
COMPACT = ("ja", "zh")

HEAD = r"""<script>
window.__smoke={errors:[]};
window.addEventListener("error",function(e){window.__smoke.errors.push("error: "+String(e.message||"").slice(0,200)+" ("+String(e.filename||"").split("/").pop()+":"+e.lineno+")")});
window.addEventListener("unhandledrejection",function(e){var r=e.reason;window.__smoke.errors.push("unhandledrejection: "+String(r&&r.message||r).slice(0,200))});
(function(){var original=window.fetch;if(!original)return;window.fetch=function(){var args=arguments;return original.apply(this,args).then(function(reply){if(reply.status>=500)window.__smoke.errors.push("http "+reply.status+": "+String(args[0]&&args[0].url||args[0]).split("?")[0].slice(0,120));return reply})}})();
(function(){var original=console.error;console.error=function(){window.__smoke.errors.push("console.error: "+Array.prototype.map.call(arguments,String).join(" ").slice(0,200));return original.apply(console,arguments)}})();
</script>"""

DRIVER = r"""<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const report={ok:true,tabs:{},cfg:{},windows:{},total_fields:0,errors:[]};
  try{
    await wait(1500);
    for(const t of TABS){
      showTab(t);await wait(300);
      const el=document.getElementById("t-"+t);
      report.tabs[t]={on:!!(el&&el.classList.contains("on")),text:el?(el.innerText||"").trim().length:0};
    }
    showTab("cfg");await wait(2500);
    for(const id of cfgTabIds()){
      cfgShowTab(id);await wait(150);
      const panel=document.getElementById("cfp-"+id);
      const fields=panel?panel.querySelectorAll(id==="interface"?"input,select,textarea,button":".cfg-f").length:-1;
      report.cfg[id]={fields:fields,shown:!!panel&&!panel.hidden};
      report.total_fields+=Math.max(0,fields);
    }
    for(const [name,fn] of [["about",()=>openAbout()],["help",()=>openHelp("cfg",null)],["notes",()=>openNotes()]]){
      try{showTab("now");await fn();await wait(300);
        const dlg=document.querySelector(".dlg:not([hidden])");report.windows[name]={open:!!dlg,text:dlg?(dlg.innerText||"").trim().length:0};
        const x=document.querySelector(".dlg:not([hidden]) .ib");if(x)x.click();await wait(200)}
      catch(e){report.windows[name]={open:false,error:String(e).slice(0,160)}}
    }
    showTab("now");await wait(1800);
    const lives=[...document.querySelectorAll("[data-live]")],before=lives.map(e=>e.textContent);
    await wait(2500);
    report.live={n:lives.length,changed:lives.filter((e,i)=>e.isConnected&&e.textContent!==before[i]).length,gone:lives.filter(e=>!e.isConnected).length};
    showTab("charts");await wait(300);
    const host=document.getElementById("t-charts"),probe=document.createElement("span");probe.className="mut";probe.id="es-probe";probe.textContent=T("ui.no_data");host.appendChild(probe);
    await wait(2600);
    report.next={asked:true,added:!!probe.querySelector(".es-next button")};
    probe.remove();
    await wait(500);
  }catch(e){report.ok=false;report.error=String(e).slice(0,300)}
  report.errors=window.__smoke.errors.slice(0,20);
  const out=document.createElement("pre");out.id="smoke-report";out.textContent=JSON.stringify(report);document.body.appendChild(out);
})();
</script>"""


def problems(report, min_text=MIN_TEXT):
    """The list of what is wrong in the document the page wrote (empty = the page is fine)."""
    found = []
    if not report.get("ok"):
        found.append("the driver failed: " + str(report.get("error")))
    for tab, info in sorted((report.get("tabs") or {}).items()):
        if not info.get("on"):
            found.append(f"the tab {tab} did not open")
        elif info.get("text", 0) < min_text:
            found.append(f"the tab {tab} drew almost nothing ({info.get('text')} characters)")
    if not report.get("cfg"):
        found.append("Settings drew no sub-tab")
    for sub, info in sorted((report.get("cfg") or {}).items()):
        least = MIN_FIELDS.get(sub, 1)
        if not info.get("shown"):
            found.append(f"the sub-tab {sub} of Settings did not open")
        if info.get("fields", -1) < least:
            found.append(f"the sub-tab {sub} of Settings drew {info.get('fields')} fields (at least {least})")
    if report.get("total_fields", 0) < MIN_TOTAL:
        found.append(f"Settings drew {report.get('total_fields')} fields in all (at least {MIN_TOTAL})")
    for name, info in sorted((report.get("windows") or {}).items()):
        if not info.get("open") or info.get("text", 0) < 20:
            found.append(f"the window {name} did not open or is empty" + (": " + info["error"] if info.get("error") else ""))
    live = report.get("live") or {}
    if live.get("n", 0) and not live.get("changed", 0) and not live.get("gone", 0):
        found.append("the duration of the runs in progress does not count up on the page")
    if report.get("next") and not report["next"].get("added"):
        found.append("an empty list does not say what to do next (no button after \"No data.\")")
    found.extend(report.get("errors") or [])
    return found


def run(langs=("en",), change=None, quiet=True, sizes=("desktop",), fail=()):
    """{lang: [problem, ...]} for the page of the demo monitor (possibly edited by `change(bytes) -> bytes`); None when there is no browser. With more than one size the key is `lang@size` for the sizes after
    the first (so that the answer for one size keeps its shape)."""
    browser = co.edge()
    if not browser:
        return None
    port = co.free_port()
    demo = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_monitor.py"), str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
    server = None
    results = {}
    try:
        for _ in range(80):
            try:
                socket.create_connection(("127.0.0.1", port), 0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("the demo monitor did not start")
        server = co.relay(port, probe=DRIVER, head=HEAD.encode("utf-8"), change=change, fail=fail)
        base = f"http://127.0.0.1:{server.server_address[1]}/"
        for lang in langs:
            for index, size in enumerate(sizes):
                report = co.measure(browser, f"{base}?lang={lang}&nowizard=1", co.SIZES[size], report=REPORT)
                key = lang if index == 0 else f"{lang}@{size}"
                results[key] = problems(report, MIN_TEXT_COMPACT if lang in COMPACT else MIN_TEXT)
                if not quiet:
                    print(key, "fields:", report.get("total_fields"), "problems:", len(results[key]), flush=True)
    finally:
        if server:
            server.shutdown()
            server.server_close()
        demo.terminate()
        try:
            demo.wait(timeout=15)
        except subprocess.TimeoutExpired:
            demo.kill()
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", nargs="*", default=["en"])
    ap.add_argument("--size", nargs="*", default=["desktop"], choices=list(co.SIZES))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    results = run(args.lang, quiet=False, sizes=tuple(args.size))
    if results is None:
        print("No browser found (Edge, Chrome or Chromium): nothing was checked.")
        return 0
    bad = {k: v for k, v in results.items() if v}
    if args.json:
        print(json.dumps(results, indent=1, ensure_ascii=False))
    else:
        for lang, items in bad.items():
            for item in items:
                print(f"[{lang}] {item}")
    print("PAGE=FAIL" if bad else "PAGE=PASS", sum(len(v) for v in results.values()))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
