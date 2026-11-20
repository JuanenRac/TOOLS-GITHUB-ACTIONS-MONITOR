#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/check_screens.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Measures the wall screens (/screen/overview, /screen/now, /screen/sentinels) in every language, window size and kind of data, and reports what does not fit.

    python tools/check_screens.py [--lang en de ...] [--size 1080p 4K ...] [--data rich long ...] [--kind overview ...] [--safe PERCENT] [--inset PERCENT] [--report FILE] [--list]

The demo monitor (tools/demo_monitor.py --rich, invented data) is started on a free port, a small relay adds the measuring script to the page and Edge, Chrome or Chromium in headless mode
opens the page once per language and size. Inside the page the script feeds every screen with each kind of data (the invented demo as it is, repository names that are very long, the most rows
the server can send, figures of six and seven digits, no data at all, a single datum, an old reading) and measures with the DOM what the eye would see wrong:

    page          the page scrolls (a scroll bar on a screen nobody touches)
    outside       a text or a box beyond the edge of the window, or beyond the safe margin (`--inset`, the part of the edge a television may cut)
    clipped       a box whose content is bigger than the box (cut without a trace)
    cut           a label that ends in "..." (only the names of repositories and workflows may, and they carry their full text in `title`)
    overlap       two texts that cover each other
    small         a type below the smallest that can be read from a few metres (a part of the short side of the window)
    silent        rows of a list hidden without the "+N more" line that says so
    scroll        a panel that scrolls inside (nobody can scroll a wall; the wall screens have none, the page of the kiosk has several)

Exit code 0 when nothing is found (or when there is no browser: it says so), 1 otherwise. `--report FILE` writes every finding as JSON (screen, language, size, data, selector, kind, detail).
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("MONITOR_VT_BUDGET", "90000")      # the browser lives on virtual time: 24 looks of 0.7 s each need more than the usual 20 s
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_overflow  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
KINDS = ("overview", "now", "sentinels")
SIZES = {"1080p": (1920, 1080), "1440p": (2560, 1440), "4K": (3840, 2160), "ultrawide": (3440, 1440), "superwide": (5120, 1440), "portrait": (1080, 1920), "portrait4K": (2160, 3840)}
DATA = ("rich", "long", "many", "huge", "zero", "one", "old", "worst")
#: a part of the short side of the window: the smallest type that is read from about three metres on a wall screen (12 px in a 1080 p window)
MIN_FONT = 0.0105
#: the sizes and the data the normal suite measures (the whole matrix is measured with MONITOR_SCREENS_MATRIX=1, on the CI)
QUICK_SIZES = ("1080p", "portrait", "superwide")
QUICK_DATA = ("rich", "worst", "zero")
REDUCED = "--force-prefers-reduced-motion"

HEAD = """<script>
window.__errs=[];window.__ofetch=window.fetch.bind(window);
window.addEventListener("error",e=>window.__errs.push("error: "+e.message));
window.addEventListener("unhandledrejection",e=>window.__errs.push("rejection: "+e.reason));
const __ce=console.error;console.error=function(){window.__errs.push("console.error: "+[].slice.call(arguments).join(" "));__ce.apply(console,arguments)};
</script>"""

LIB = r"""
  const found=[],seen=new Set(),Q=new URLSearchParams(location.search),wait=ms=>new Promise(r=>setTimeout(r,ms));
  const inset=parseFloat(Q.get("inset")||Q.get("safe")||"0")||0,MINF=parseFloat(Q.get("minfont")||"0.0105");
  const css=e=>getComputedStyle(e);
  const where=e=>{const p=[];for(let n=e;n&&n!==document.body&&p.length<3;n=n.parentElement){p.push(n.tagName.toLowerCase()+(n.id?"#"+n.id:"")+(n.classList.length&&!n.id?"."+[...n.classList].slice(0,2).join("."):""))}return p.join("<")};
  const shown=e=>{if(e.closest(".vh,.sr-only"))return false;for(let n=e;n&&n!==document.documentElement;n=n.parentElement){const s=css(n);if(s.display==="none"||s.visibility==="hidden")return false}const r=e.getBoundingClientRect();return r.width>0&&r.height>0};
  /* ---- the measure ---- */
  function add(ctx,kind,e,detail){const key=ctx.screen+"|"+ctx.data+"|"+kind+"|"+where(e)+"|"+detail.slice(0,24);if(seen.has(key))return;seen.add(key);found.push({kind,at:where(e),text:(e.textContent||"").trim().slice(0,60),detail,screen:ctx.screen,data:ctx.data})}
  const NAMES=".nm,.hn,.gn";
  function clipRect(r,el){      /* the part of the rectangle that is not cut by a box that clips (overflow other than visible), up to the frame of the window itself (#wrap, the body) */
    let x1=r.left,x2=r.right,y1=r.top,y2=r.bottom;
    for(let a=el;a&&a!==document.documentElement;a=a.parentElement){
      if(a===document.body||a.id==="wrap")break;
      const st=css(a),cx=st.overflowX!=="visible",cy=st.overflowY!=="visible";if(!cx&&!cy)continue;
      const b=a.getBoundingClientRect();
      if(cx){x1=Math.max(x1,b.left);x2=Math.min(x2,b.right)}
      if(cy){y1=Math.max(y1,b.top);y2=Math.min(y2,b.bottom)}
    }
    return {left:x1,right:x2,top:y1,bottom:y2};
  }

  function measure(ctx,ROOT){ROOT=ROOT||(()=>document.getElementById("stage"));
    const vw=innerWidth,vh=innerHeight,ix=vw*inset/100,iy=vh*inset/100,de=document.documentElement,minFont=MINF*Math.min(vw,vh);
    if(de.scrollWidth>vw+1||de.scrollHeight>vh+1)found.push({kind:"page",at:"html",text:"",detail:de.scrollWidth+"x"+de.scrollHeight+" > "+vw+"x"+vh,screen:ctx.screen,data:ctx.data});
    const stage=ROOT();const zoom=(parseFloat(document.body.style.zoom)||1)*(parseFloat(css(document.documentElement).zoom)||1);      /* the zoom of the kiosk and the one the page gives to a big window */
    const all=[...stage.querySelectorAll("*")].filter(e=>!e.closest("svg")&&!["SCRIPT","STYLE"].includes(e.tagName)&&shown(e));
    /* boxes: clipped content, labels cut with dots, boxes outside */
    for(const e of all){
      const s=css(e),cx=s.overflowX!=="visible",cy=s.overflowY!=="visible";
      if(cx&&e.scrollWidth>e.clientWidth+1&&e.clientWidth>0){
        const dots=s.textOverflow==="ellipsis";
        if(dots){if(!e.matches(NAMES)||!(e.title||e.querySelector("[title]")))add(ctx,"cut",e,e.scrollWidth+">"+e.clientWidth)}
        else if(!e.matches("#wrap"))add(ctx,"clipped",e,"x "+e.scrollWidth+">"+e.clientWidth);
      }
      if(cy&&e.scrollHeight>e.clientHeight+1&&e.clientHeight>0&&!e.matches("#wrap,#stage")&&!(e.matches(".mini,.ring")))add(ctx,(s.overflowY==="auto"||s.overflowY==="scroll")?"scroll":"clipped",e,"y "+e.scrollHeight+">"+e.clientHeight);      /* scroll: a panel that scrolls inside, which nobody can do on a wall */
      if(e.matches(".card,.sen,.tile,header,.foot,#banner")){const q=e.getBoundingClientRect(),r=clipRect({left:q.left,right:q.right,top:q.top,bottom:q.bottom},e.parentElement||e);if(r.right>r.left&&r.bottom>r.top&&(r.left<ix-1.5||r.right>vw-ix+1.5||r.top<iy-1.5||r.bottom>vh-iy+1.5))add(ctx,"outside",e,"box "+[r.left,r.top,r.right,r.bottom].map(Math.round).join(","))}      /* a box inside a panel that scrolls is judged by the panel (kind scroll) */
    }
    /* texts: where they are, how big, whether two cover each other */
    const items=[],walker=document.createTreeWalker(stage,NodeFilter.SHOW_TEXT);
    for(let t=walker.nextNode();t;t=walker.nextNode()){
      if(!t.nodeValue.trim())continue;const el=t.parentElement;if(!el||el.closest("svg,script,style")||!shown(el))continue;
      const range=document.createRange();range.selectNodeContents(t);const rr=[...range.getClientRects()].filter(r=>r.width>0.5&&r.height>0.5);if(!rr.length)continue;
      const fs=parseFloat(css(el).fontSize);
      if(fs*zoom<minFont-0.01)add(ctx,"small",el,(fs*zoom).toFixed(1)+"px < "+minFont.toFixed(1)+"px");
      for(const line of rr){      /* one rectangle for each line of the text: the box around a text of several lines would cover its neighbours */
        const r=clipRect({left:line.left,right:line.right,top:line.top,bottom:line.bottom},el);      /* what can be seen of it: a box that clips cuts it, and the box tests above report that */
        if(r.right<=r.left||r.bottom<=r.top)continue;
        if(r.left<ix-1.5||r.right>vw-ix+1.5||r.top<iy-1.5||r.bottom>vh-iy+1.5)add(ctx,"outside",el,"text "+[r.left,r.top,r.right,r.bottom].map(Math.round).join(","));
        /* a text that leaves the row, tile or card that holds it */
        for(let a=el.parentElement;a&&a!==stage;a=a.parentElement){if(a.matches(".rowbar,.failrow,.tile")){const q=a.getBoundingClientRect();const tol=Math.max(1.5,fs*0.2);if(r.right>q.right+tol||r.left<q.left-tol||r.bottom>q.bottom+tol||r.top<q.top-tol)add(ctx,"outside",el,"leaves "+where(a)+" text "+[r.left,r.top,r.right,r.bottom].map(Math.round).join(",")+" box "+[q.left,q.top,q.right,q.bottom].map(Math.round).join(","));break}}
        items.push({el,r});
      }
    }
    for(let i=0;i<items.length;i++)for(let j=i+1;j<items.length;j++){
      const a=items[i],b=items[j];if(a.el===b.el)continue;
      const w=Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left),h=Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top);
      if(w>2&&h>0.35*Math.min(a.r.bottom-a.r.top,b.r.bottom-b.r.top))add(ctx,"overlap",a.el,"with "+where(b.el)+" ("+Math.round(w)+"x"+Math.round(h)+")");
    }
    /* lists that hid rows must say so */
    for(const l of stage.querySelectorAll(".list,.ticker,.gmap")){if(!shown(l))continue;const hid=[...l.children].filter(c=>c.hidden).length;if(hid&&!l.querySelector(":scope>.more"))add(ctx,"silent",l,hid+" rows hidden")}
  }
"""

WALL_BODY = r"""
  const out=document.getElementById("screens-measure")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"screens-measure"}));
  const KINDS=(Q.get("kinds")||"overview,now,sentinels").split(","),DS=(Q.get("data")||"rich").split(",");
  const clone=o=>JSON.parse(JSON.stringify(o));
  /* ---- the kinds of data: the answer of the demo, changed ---- */
  const L1="demo-organization-with-an-extremely-long-repository-name-that-keeps-going-on-and-on-and-on",L2="Donaudampfschifffahrtsgesellschaftskapitaensmuetzenabzeichenverwaltungsrepositorium-Kontinuierliche",
        L3="非常に長いリポジトリ名を持つデモプロジェクトの継続的インテグレーションとリリース署名検証ワークフロー名前",W1="Continuous integration, release packaging and signature verification of every package",
        W2="Kontinuierlicheintegrationsundveroeffentlichungspruefungsarbeitsablauf",W3="継続的インテグレーションとリリース署名検証ワークフローの長い名前をここに書きます";
  const LONGS=[L1,L2,L3],LONGW=[W1,W2,W3];
  const lr=i=>LONGS[i%3],lw=i=>LONGW[i%3];
  function rows(list,n,make){const o=[];for(let i=0;i<n;i++)o.push(make(list&&list.length?clone(list[i%list.length]):{},i));return o}
  function mutate(name,kind,d){
    d=clone(d);const long=name==="long"||name==="worst",many=name==="many"||name==="worst",huge=name==="huge"||name==="worst";
    const bigN=huge?1234567:null;
    if(name==="old"){d.meta.age_seconds=900000;d.meta.have_data=true}
    if(name==="zero"||name==="one"){
      const keep=name==="one"?1:0;
      const cut=a=>Array.isArray(a)?a.slice(0,keep):a;
      for(const k of ["trend24","trend7d","heat","top_red","events","running","queued","approval","failures","merges","next_releases","pending_sign","timeline"])if(k in d)d[k]=cut(d[k]);
      if(d.groups)d.groups.groups=cut(d.groups.groups);
      if(name==="zero"){
        if(d.fleet)d.fleet={total:0,red:0,stuck:0,waiting:0,green:0,idle:0};if(d.queue)d.queue={running:0,queued:0,approval:0,minutes24:0,minutes7d:0};
        if(d.score)d.score={state:"off",value:null,letter:null,trend:null};if(d.alerts)d.alerts={total:0,by_level:{critical:0,error:0,warning:0,info:0},by_sentinel:{}};
        if(d.totals)d.totals={running:0,queued:0,approval:0,failures:0};
        if(d.cards)d.cards=d.cards.map(c=>({id:c.id,level:"unknown",open:null,readable:false}));
        if(d.meta)d.meta.api={remaining:null,limit:null,reset_seconds:null,low:false};
        if(kind==="sentinels"){d.enabled=false}
      }
      return d;
    }
    if(kind==="overview"){
      if(many){
        d.heat=rows(d.heat,12,(r,i)=>({repo:r.repo||"repo-"+i,red:i<3,cells:Array.from({length:24},(_,j)=>(i+j)%4)}));
        d.top_red=rows(d.top_red,8,(r,i)=>({repo:r.repo||"r"+i,workflow:r.workflow||"CI",seconds:3600*i+5,streak:i+1}));
        d.events=rows(d.events,10,(r,i)=>({ago:r.ago||60*i,kind:["ok","bad","skip","run"][i%4],repo:r.repo||"r"+i,workflow:r.workflow||"CI",seconds:100+i}));
        d.groups={by:"ecosystem",groups:Array.from({length:12},(_,i)=>({key:"g"+i,label:"Group "+i,repos:30+i,bad:i%3,warn:i%4,ok:20,unknown:1})),more:7};
      }
      if(long){
        d.heat.forEach((r,i)=>{r.repo=lr(i)});d.top_red.forEach((r,i)=>{r.repo=lr(i);r.workflow=lw(i)});d.events.forEach((r,i)=>{r.repo=lr(i);r.workflow=lw(i)});
        if(d.groups)d.groups.groups.forEach((g,i)=>{g.label=(lr(i)).slice(0,40)});
      }
      if(huge){
        d.fleet={total:bigN,red:bigN,stuck:bigN,waiting:bigN,green:bigN,idle:0};d.queue={running:bigN,queued:bigN,approval:bigN,minutes24:9999999,minutes7d:9999999};
        d.alerts={total:bigN,by_level:{critical:bigN,error:bigN,warning:bigN,info:bigN}};d.meta.api={remaining:9999999,limit:9999999,reset_seconds:86400*3,low:false};
        d.score={state:"scored",value:100,letter:"A+",trend:-123};
        d.events.forEach(e=>{e.ago=86400*400});d.top_red.forEach(e=>{e.seconds=86400*400});
      }
    }else if(kind==="now"){
      const rn=(list,n,f)=>rows(list,n,f);
      if(many){
        d.running=rn(d.running,12,(r,i)=>({...r,repo:r.repo||"r"+i,workflow:r.workflow||"Release build",event:"workflow_dispatch",seconds:60*i+7,progress:i%2?(i/12):null,stuck:i%5===0,jobs:2}));
        d.queued=rn(d.queued,12,(r,i)=>({...r,repo:r.repo||"q"+i,workflow:r.workflow||"CI",seconds:30+i,progress:null}));
        d.approval=rn([{repo:"a",ago:60}],12,(r,i)=>({repo:"approval-"+i,ago:600*i}));
        d.failures=rn(d.failures,8,(r,i)=>({repo:r.repo||"f"+i,workflow:r.workflow||"CI",ago:300*i+9,attempt:i%3+1}));
        d.merges=rn([{repo:"m",release:false,ago:5}],6,(r,i)=>({repo:"merged-"+i,release:i%2===0,ago:900*i}));
        d.next_releases=rn([{repo:"n",entries:3,age_days:2}],6,(r,i)=>({repo:"next-"+i,entries:3+i,age_days:i}));
        d.pending_sign=rn([{repo:"p",hours:5}],6,(r,i)=>({repo:"sign-"+i,hours:5+i}));
        d.timeline=rn(d.timeline,24,(r,i)=>({ago:300*i,kind:["ok","bad","run","wait","skip"][i%5],repo:"t"+i,workflow:"CI"}));
      }
      if(long){
        for(const k of ["running","queued","failures","merges","next_releases","pending_sign","approval"])(d[k]||[]).forEach((r,i)=>{r.repo=lr(i);if("workflow" in r)r.workflow=lw(i)});
        (d.timeline||[]).forEach((r,i)=>{r.repo=lr(i);r.workflow=lw(i)});
      }
      if(huge){
        d.totals={running:bigN,queued:bigN,approval:bigN,failures:bigN};
        (d.running||[]).forEach(r=>{r.seconds=86400*400;r.progress=0.99});(d.queued||[]).forEach(r=>{r.seconds=86400*400});(d.failures||[]).forEach(r=>{r.ago=86400*400;r.attempt=99});
        (d.merges||[]).forEach(r=>{r.ago=86400*400});(d.next_releases||[]).forEach(r=>{r.entries=9999});(d.pending_sign||[]).forEach(r=>{r.hours=99999});(d.approval||[]).forEach(r=>{r.ago=86400*400});
      }
    }else{
      if(many||huge||long){
        d.cards=d.cards.map((c,i)=>({id:c.id,level:["bad","warn","ok","info","unknown"][i%5],open:huge?bigN:(many?99+i:c.open),readable:i%3!==0}));
        d.alerts={total:huge?bigN:999,by_level:{critical:huge?bigN:50,error:huge?bigN:60,warning:huge?bigN:70,info:huge?bigN:80},by_sentinel:{}};
        d.sweep={age_seconds:huge?86400*400:100,cycle_seconds:120,progress:.5};
      }
    }
    return d;
  }

  try{
    await wait(1200);
    const S=window.__screens;clearTimeout(S.state.timer);S.state.moving=true;
    const base={};
    for(const k of ["overview","now","sentinels"])base[k]=await (await window.__ofetch("/api/screens/data?screen="+k+"&lang="+encodeURIComponent(document.documentElement.getAttribute("data-l")||Q.get("lang")||"en"))).json();
    const rowsDone=[];
    for(const ds of DS)for(const kind of KINDS){
      S.state.moving=false;S.show(kind);S.state.moving=true;S.paint(mutate(ds,kind,base[kind]));await wait(450);
      measure({screen:kind,data:ds});rowsDone.push(kind+"/"+ds);
    }
    out.textContent=JSON.stringify({ok:true,found:found,done:rowsDone,errors:window.__errs,lang:document.documentElement.lang,w:innerWidth,h:innerHeight});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e&&e.stack||e),found:found,errors:window.__errs})}
  document.title="screens-measured";

"""

PROBE = "<script>" + chr(10) + "(async function(){" + LIB + WALL_BODY + "})();" + chr(10) + "</script>"



KIOSK_BODY = r"""
  const out=document.getElementById("screens-measure")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"screens-measure"}));
  try{
    await wait(2500);
    const tabs=(Q.get("tabs")||"now").split(","),done=[];
    for(const t of tabs){showTab(t);await wait(800);measure({screen:"kiosk:"+t,data:"rich"},()=>document.body);done.push(t)}
    out.textContent=JSON.stringify({ok:true,found:found,done:done,errors:window.__errs,lang:document.documentElement.lang,w:innerWidth,h:innerHeight,zoom:document.body.style.zoom});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e&&e.stack||e),found:found,errors:window.__errs})}
  document.title="screens-measured";
"""

KIOSK_PROBE = "<script>" + chr(10) + "(async function(){" + LIB + KIOSK_BODY + "})();" + chr(10) + "</script>"
PRESETS = {"ops": "now,al,charts", "team": "al,team", "release": "now,repos,rep", "quiet": "al"}


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def start_demo():
    """The demo monitor with its richest data on a free port; returns (process, port), or raises when it does not start."""
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_monitor.py"), str(port), "--rich", "--kiosk"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                            env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
    for _ in range(120):
        try:
            socket.create_connection(("127.0.0.1", port), 0.5).close()
        except OSError:
            time.sleep(0.5)
            continue
        for _ in range(40):      # the monitor keeps the configuration for a few seconds: ask until the page says that the kiosk profile is on
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/?lang=en", timeout=10) as page:
                    if b'"kiosk": {"enabled": true' in page.read():
                        return proc, port
            except OSError:
                pass
            time.sleep(1)
        break
    proc.terminate()
    raise RuntimeError("the demo monitor did not start")


def measure_one(browser, base, lang, size, data=DATA, kinds=KINDS, safe=0, inset=None):
    """One browser window: every kind of data on every screen, in one language and one size. Returns the report of the page ({found, done, errors, ...})."""
    query = f"lang={lang}&kinds={','.join(kinds)}&data={','.join(data)}&density=normal&blink=off"
    if safe:
        query += f"&safe={safe:g}"
    if inset is not None:
        query += f"&inset={inset:g}"
    report = check_overflow.measure(browser, f"{base}/screen/overview?{query}", SIZES[size] if isinstance(size, str) else size, report="screens-measure", flags=(REDUCED,))
    if len(report.get("done", [])) != len(data) * len(kinds):      # the budget of the browser ran out before every look was made: say it, do not pass in silence
        report.setdefault("found", []).append({"kind": "incomplete", "at": "page", "text": "", "detail": "%d of %d looks" % (len(report.get("done", [])), len(data) * len(kinds)), "screen": "-", "data": "-"})
    return report


def run(langs=LANGS, sizes=tuple(SIZES), data=DATA, kinds=KINDS, safe=0, inset=None, quiet=False, surface="wall", presets=tuple(PRESETS), scale=150, fit=True):
    """{(lang, size): report} for every combination (for the kiosk, {(lang, size, preset): report}); None when there is no browser. Each report also carries `found` with the findings."""
    browser = check_overflow.edge()
    if not browser:
        return None
    demo, port = start_demo()
    relay = check_overflow.relay(port, probe=PROBE if surface == "wall" else KIOSK_PROBE, head=HEAD.encode("utf-8"))
    base = f"http://127.0.0.1:{relay.server_address[1]}"
    results = {}
    try:
        for size in sizes:
            for lang in langs:
                if surface == "wall":
                    report = measure_one(browser, base, lang, size, data, kinds, safe, inset)
                    results[(lang, size)] = report
                    if not quiet:
                        print(f"{size:10} {lang}: {len(report.get('found', []))} finding(s)", flush=True)
                    continue
                for preset in presets:
                    report = measure_kiosk(browser, base, lang, size, preset, scale, safe, inset, fit)
                    results[(lang, size, preset)] = report
                    if not quiet:
                        print(f"{size:10} {lang} {preset}: {len(report.get('found', []))} finding(s)", flush=True)
    finally:
        relay.shutdown()
        demo.terminate()
    return results


def measure_kiosk(browser, base, lang, size, preset, scale=150, safe=0, inset=None, fit=True):
    """One browser window with the kiosk profile (the page of the monitor, no header, larger type) on the tabs of a preset."""
    query = f"lang={lang}&screen=1&tabs={PRESETS[preset]}&chrome=0&kiosk=1&scale={scale}&nowizard=1&fit={int(fit)}"
    if safe:
        query += f"&safe={safe:g}"
    if inset is not None:
        query += f"&inset={inset:g}"
    return check_overflow.measure(browser, f"{base}/?{query}", SIZES[size] if isinstance(size, str) else size, report="screens-measure", flags=(REDUCED,))


def flat(results):
    """Every finding as a dictionary with its language and size."""
    rows = []
    for key, report in sorted(results.items()):
        lang, size = key[0], key[1]
        for item in report.get("found", []):
            rows.append({"lang": lang, "size": size, **({"preset": key[2]} if len(key) > 2 else {}), **item})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="Measures the wall screens in every language, size and kind of data.")
    ap.add_argument("--surface", choices=("wall", "kiosk"), default="wall", help="wall: the three pages /screen/*; kiosk: the page of the monitor with the kiosk profile")
    ap.add_argument("--preset", nargs="*", default=list(PRESETS), choices=list(PRESETS), help="the presets of the kiosk")
    ap.add_argument("--scale", type=int, default=150, help="the type size of the kiosk in percent")
    ap.add_argument("--no-fit", action="store_true", help="the kiosk keeps the same type size whatever the window (kiosk.scale_with_window off)")
    ap.add_argument("--lang", nargs="*", default=list(LANGS))
    ap.add_argument("--size", nargs="*", default=list(SIZES), choices=list(SIZES))
    ap.add_argument("--data", nargs="*", default=list(DATA), choices=list(DATA))
    ap.add_argument("--kind", nargs="*", default=list(KINDS), choices=list(KINDS))
    ap.add_argument("--safe", type=float, default=0, help="the safe margin of the window in percent (the setting screens.safe_margin_percent), and the margin the measure demands")
    ap.add_argument("--inset", type=float, default=None, help="only demand that the content stays this many percent inside the edge (without asking the page for a margin)")
    ap.add_argument("--report", default="", help="write every finding as JSON to this file")
    ap.add_argument("--list", action="store_true", help="print the findings one by one")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    results = run(args.lang, args.size, args.data, args.kind, args.safe, args.inset, surface=args.surface, presets=args.preset, scale=args.scale, fit=not args.no_fit)
    if results is None:
        print("SCREENS=SKIP (no Edge, Chrome or Chromium on this computer)")
        return 0
    rows = flat(results)
    by_kind = {}
    for row in rows:
        by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + 1
    if args.report:
        Path(args.report).write_text(json.dumps({"total": len(rows), "by_kind": by_kind, "findings": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.list:
        for row in rows:
            print(f'{row["size"]:10} {row["lang"]} {row["screen"]:9} {row["data"]:6} {row["kind"]:8} {row["at"]}  {row["detail"]}  | {row["text"][:40]}')
    print("SCREENS=" + ("PASS" if not rows else "FAIL"), "findings=%d" % len(rows), json.dumps(by_kind, sort_keys=True))
    return 0 if not rows else 1


if __name__ == "__main__":
    sys.exit(main())
