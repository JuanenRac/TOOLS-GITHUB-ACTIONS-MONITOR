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
  const errs=[];window.addEventListener("error",e=>errs.push(String(e.message||e).slice(0,120)));window.addEventListener("unhandledrejection",e=>errs.push(String(e.reason).slice(0,120)));
  try{
    await wait(1200);
    for(let i=0;i<60;i++){      /* wait for the condition (the data of the sentinels has arrived), not for a fixed time */
      await wait(250);
      if(typeof SENT!=="undefined"&&SENT&&typeof COLLAB!=="undefined"&&COLLAB&&typeof SECUR!=="undefined"&&SECUR&&typeof SDEL!=="undefined"&&SDEL&&typeof SSUP!=="undefined"&&SSUP)break;
    }
    const cases=[["sci","a1","s-details"],["scol","scol:collab.issue.critical","s-details-collab"],["ssec","ssec:security.secret","s-details-sec"],["sdel","sdel:release.unreleased_pending","s-details-del"],["ssup","ssup:actions.supply.unpinned","s-details-sup"]];
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
    /* panels that are unfolded together, one by one, all at once and by hand (no new render): their boxes never overlap and each body ends inside its panel */
    {const holders=[["sci","s-details"],["scol","s-details-collab"],["ssec","s-details-sec"],["sdel","s-details-del"],["ssup","s-details-sup"]];
     const check=(tab,holder,label)=>{
       const ds=[...holder.querySelectorAll(":scope>details")];
       for(let i=0;i<ds.length;i++){
         const r=ds[i].getBoundingClientRect();
         if(i+1<ds.length){const n=ds[i+1].getBoundingClientRect();if(n.top<r.bottom-1)found.push({kind:"panels_overlap",at:tab,detail:label+": panel "+(ds[i].dataset.k||i)+" ends "+Math.round(r.bottom-n.top)+"px below the start of the next"})}
         const b=ds[i].querySelector(":scope>.dbody");
         if(ds[i].open&&b){const q=b.getBoundingClientRect();if(q.bottom>r.bottom+1)found.push({kind:"body_outside_panel",at:tab,detail:label+": the body of "+(ds[i].dataset.k||i)+" ends "+Math.round(q.bottom-r.bottom)+"px below its panel"});
           if(q.height<1&&b.textContent.trim())found.push({kind:"body_without_height",at:tab,detail:label+": "+(ds[i].dataset.k||i)})}}};
     for(const [tab,box] of holders){
       try{showTab(tab)}catch(e){continue}
       await wait(150);
       const holder=document.getElementById(box);if(!holder)continue;
       const all=[...holder.querySelectorAll(":scope>details")];
       if(!all.length)continue;
       for(const d of all)d.open=false;await wait(30);check(tab,holder,"folded");
       for(const d of all){d.open=true;await wait(15);check(tab,holder,"one more unfolded: "+(d.dataset.k||""))}
       await wait(30);check(tab,holder,"all unfolded");
       for(const d of all){d.open=false;await wait(15);check(tab,holder,"one folded: "+(d.dataset.k||""))}
       for(let i=0;i<all.length;i++){for(const d of all)d.open=false;all[i].open=true;await wait(15);check(tab,holder,"only "+(all[i].dataset.k||""))}
       for(const d of all)d.open=false;
       all.forEach((d,i)=>{if((i&1)===0)d.open=true});await wait(30);check(tab,holder,"alternate");
       seen.push(tab+"-overlap")}}
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
    /* one card per signal in the panels of Collaboration, Security, Delivery and Supply chain; Delivery and Supply chain also have a table by code and filters */
    for(const [tab,box,n,tbl] of [["scol","s-details-collab",6,false],["ssec","s-details-sec",6,false],["sdel","s-details-del",6,true],["ssup","s-details-sup",5,true]]){
      try{showTab(tab)}catch(e){}await wait(200);
      const holder=document.getElementById(box),cards=holder?holder.querySelectorAll(":scope>details[data-sp]"):[];
      if(cards.length!==n)found.push({kind:"sub_cards",at:tab,detail:cards.length+" cards instead of "+n});
      for(const c of cards){if(!c.querySelector(".sphelp")||!c.querySelector("[data-sprepo]"))found.push({kind:"sub_card_parts",at:tab,detail:"a card without help or filter: "+c.dataset.k})}
      if(tbl&&(!holder.querySelector(".sptable")||!holder.querySelector('[data-spk="level"]')))found.push({kind:"sub_table",at:tab,detail:"no table by code or no filter"});
      seen.push(tab+"-cards")}
    /* the rich daily trend: cards, range, compare, legend, tooltip and the export */
    {try{showTab("strend")}catch(e){}await wait(300);
     {const ds=[],tr={versions:[]};for(let i=0;i<12;i++){ds.push("2026-02-"+String(i+1).padStart(2,"0"));tr.versions.push(i<6?"1.0.0":"1.0.1")}
      for(const d of TRS)tr[d[0]]={dates:ds,values:ds.map((x,i)=>d[0]==="red"?(i===3||i===9?2:0):(i<2?null:Math.round(Math.abs(Math.sin(i+d[0].length))*17)))};TRLAST=tr;renderTrend()}
     const q=s=>document.querySelector("#s-trend "+s),fire=(el,v)=>{el.value=v;el.dispatchEvent(new Event("change",{bubbles:true}))};
     if(document.querySelectorAll("#s-trend .trcard").length<16)found.push({kind:"trend_cards",at:"strend",detail:"fewer than 16 cards"});
     const rng=q("#tr-range");
     if(!rng)found.push({kind:"trend_range",at:"strend",detail:"no range selector"});
     else{for(const n of ["7","60","30"]){fire(q("#tr-range"),n);await wait(80);const sv=q(".trsvg");if(!sv||+sv.dataset.n>+n)found.push({kind:"trend_range",at:"strend",detail:"range "+n+" shows "+(sv&&sv.dataset.n)+" points"})}}
     if(q("#tr-cmp")){fire(q("#tr-cmp"),"health");await wait(80);const legs=document.querySelectorAll("#s-trend .trleg");if(legs.length!==2)found.push({kind:"trend_legend",at:"strend",detail:legs.length+" legend entries"});
       else{legs[0].click();await wait(60);if(q(".trleg").getAttribute("aria-pressed")!=="false")found.push({kind:"trend_legend",at:"strend",detail:"the legend does not switch the line"});fire(q("#tr-cmp"),"")}}
     const sv=q(".trsvg");if(sv){trCursor(sv,0);const tip=q(".trtip");if(!tip||tip.hidden||!tip.textContent.trim())found.push({kind:"trend_tooltip",at:"strend",detail:"no tooltip"})}else found.push({kind:"trend_tooltip",at:"strend",detail:"no large chart"});
     const cs=[...document.querySelectorAll("#s-trend .trcard")];if(cs.length>2){cs[2].click();await wait(60);if(!q(".trcard.sel")||q(".trcard.sel").dataset.trs!==cs[2].dataset.trs)found.push({kind:"trend_pick",at:"strend",detail:"a card does not become the large chart"})}
     if(typeof trExport!=="function"||!q('[data-trexp="csv"]')||!q('[data-trexp="json"]'))found.push({kind:"trend_export",at:"strend",detail:"no export"});
     seen.push("strend-rich")}
    /* the help of the settings: pointing at or focusing a control shows the tooltip inside the window, tied to the control, and Escape hides it */
    {try{showTab("cfg")}catch(e){}await wait(700);let tested=0;
     for(const id of ["cfg-sentinel-enabled","cfg-report_history_days"]){
       const el=document.getElementById(id);if(!el)continue;
       const pan=el.closest('[id^="cfp-"]');if(pan){try{cfgShowTab(pan.id.slice(4))}catch(e){}await wait(150)}
       el.focus();await wait(100);const tip=document.getElementById("cfg-tip");
       if(!tip||tip.hidden||tip.textContent.trim().length<10){found.push({kind:"tip_missing",at:id,detail:"no tooltip when the control takes the focus"});continue}
       const r=tip.getBoundingClientRect();
       if(r.left<-1||r.top<-1||r.right>window.innerWidth+1||r.bottom>window.innerHeight+1)found.push({kind:"tip_outside",at:id,detail:"the tooltip leaves the window"});
       if(el.getAttribute("aria-describedby")!=="cfg-tip")found.push({kind:"tip_aria",at:id,detail:"the control is not tied to the tooltip"});
       el.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true}));await wait(40);
       if(!tip.hidden)found.push({kind:"tip_escape",at:id,detail:"Escape does not hide the tooltip"});
       el.blur();tested++}
     if(tested<2)found.push({kind:"tip_untested",at:"cfg",detail:"only "+tested+" of the 2 controls were found"});
     seen.push("cfg-tooltip")}
    /* the counters of the header jump to a tab (some of them with a filter of repositories): back on Now, the list and the alerts are the same as before and no filter is left behind */
    {const count=()=>document.querySelectorAll("#t-now .card,#t-now tr,#t-now .alrow").length;
     for(const id of ["kp-red","kp-sign","kt-active","kt-queued","kt-ok","kt-min","kt-issues","kt-repos","kt-hot"]){
       try{showTab("now")}catch(e){}await wait(250);const n0=count(),el=document.getElementById(id);if(!el){found.push({kind:"no_counter",at:id,detail:"the counter is not in the page"});continue}
       el.click();await wait(300);try{showTab("now")}catch(e){}await wait(300);
       if(typeof FILTER!=="undefined"&&FILTER.list)found.push({kind:"filter_left_behind",at:id,detail:"the filter '"+FILTER.listLabel+"' stays on Now"});
       if(count()!==n0)found.push({kind:"now_lost_rows",at:id,detail:n0+" before, "+count()+" after"})}
     for(const t of TABS){try{showTab(t)}catch(e){errs.push("showTab "+t+": "+e)}await wait(150);const el=document.getElementById("t-"+t);if(!el||!el.textContent.trim())found.push({kind:"blind_tab",at:t,detail:"the tab is empty after the counters were pressed"})}
     try{showTab("now")}catch(e){}
     for(const m of errs)found.push({kind:"js_error",at:"console",detail:m});
     seen.push("counters")}
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
    os.environ.setdefault("MONITOR_VT_BUDGET", "60000")      # the walk through the panels takes virtual time
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
