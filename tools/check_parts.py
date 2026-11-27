#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/check_parts.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
"""The boxes of the optional parts in a real browser: extensions, proposals and chat, collaboration and the choice of an environment, roles and groups, the screen of a group (/g/), posture,
compliance, external CI sources and the window of a newer version.

    python tools/check_parts.py [--lang en de ...] [--size phone desktop wall wall4k] [--shots DIR] [--json]

The demo monitor with the optional parts (tools/demo_monitor.py --parts, invented data) is opened through the DevTools protocol at the exact size of a phone, a computer and two wall displays.
Every box is opened with everything unfolded and measured: nothing leaves it or the window, no text is cut, no control covers another, on a phone every control is at least 44 x 44 px, no text key
or placeholder shows, and the browser reports no error. What would write something is answered by a script of the page, so nothing is changed anywhere.
Needs Edge, Chrome or Chromium and the package `websockets`; without them it says so and exits 0. Exit code 1 when something fails."""
import argparse
import asyncio
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_overflow as co  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LANGS = co.LANGS
SIZES = {"phone": (360, 780), "desktop": (1400, 900), "wall": (1920, 1080), "wall4k": (3840, 2160)}
GROUP = "group"
STEPS = ("extensions", "extensions_install", "proposals", "chat", "repo_report", "collaboration", "environment", "environment_confirm", "roles_groups", "posture", "compliance",
         "external_ci", "external_ci_test", "update_notice")

#: before any script of the page: it records the errors and answers, with invented data, what would write or needs a model or another server
HEAD = r"""
window.__parts={errors:[]};
window.addEventListener("error",function(e){window.__parts.errors.push("error: "+String(e.message||"").slice(0,200)+" ("+String(e.filename||"").split("/").pop()+":"+e.lineno+")")});
window.addEventListener("unhandledrejection",function(e){var r=e.reason;window.__parts.errors.push("unhandledrejection: "+String(r&&r.message||r).slice(0,200))});
(function(){
  var original=window.fetch;
  function json(o){return Promise.resolve(new Response(JSON.stringify(o),{status:200,headers:{"Content-Type":"application/json"}}))}
  var LONG="demo-alpha-app has Release build red on main since yesterday: three runs in a row end in the build step (npm: missing script build) https://github.com/demo-owner/demo-alpha-app/actions/runs/104/attempts/1?check_suite_focus=true";
  window.fetch=function(u,o){
    var url=String(u&&u.url||u),post=o&&String(o.method).toUpperCase()==="POST",body={};
    try{body=o&&o.body?JSON.parse(o.body):{}}catch(e){}
    if(url.indexOf("/api/actions/plan")===0)return json(body.action==="approve_deployment"&&!body.environment?{ok:false,status:"choose_environment",environments:["production","staging","preview-of-the-documentation-site-europe-west"]}:
      {ok:true,plan:{id:"demo",method:"POST",endpoint:"repos/demo-owner/demo-gamma-ui/actions/runs/701/pending_deployments",fields:{environment_ids:[1234567890],state:"approved"},environments:[body.environment||"production"]}});
    if(url.indexOf("/api/actions/fork-facts")===0)return json({ok:true,author:"demo-contributor-with-a-long-name",account_age_days:12,merged_before:0,workflow_files:[".github/workflows/continuous-integration-matrix.yml"]});
    if(url.indexOf("/api/actions/dispatch-form")===0)return json({ok:true,ref:"main",inputs:[{name:"target_environment",type:"choice",options:["staging","production"],default:"staging",required:true,description:"where"},{name:"dry_run",type:"boolean",default:"true",description:""},{name:"notes",type:"string",default:"",description:""}]});
    if(url.indexOf("/api/assistant/chat")===0)return json({ok:true,text:LONG,sources:[{tool:"list_alerts",repo:""},{tool:"repo_runs",repo:"demo-alpha-app"}],proposals:[]});
    if(url.indexOf("/api/assistant/repo-report")===0)return json({ok:true,markdown:"# demo-alpha-app\n\n"+LONG,triage:LONG});
    if(url.indexOf("/api/external-ci/log")===0)return json({ok:true,cut:true,text:"npm ERR! missing script: build\n"+LONG.replace(/ /g,"_")});
    if(url.indexOf("/api/external-ci/probe")===0)return json({ok:true,workflows:3,builds:25,red:1});
    if(url.indexOf("/api/plugins/inspect")===0)return json({ok:true,fingerprint:"9f2c41d7a0b35e68c1d4f7a92b60e3c85d1a4f7096b2e8c31a5d70f4b92c6e18",manifest:{name:"demo-badges",version:"0.3.0",author:"Demo Author",permissions:["contents:read"],get_paths:["repos/{owner}/{repo}/readme"]}});
    if(post)return json({ok:true});
    return original.apply(this,arguments);
  };
})();
"""

#: the measures of one region of the page, and the steps that open each box (window.__run(step) -> report)
LIB = r"""
(function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const until=async(fn,ms)=>{const end=Date.now()+(ms||12000);for(;;){let v=null;try{v=fn()}catch(e){}if(v)return v;if(Date.now()>end)return null;await wait(100)}};
  const $id=i=>document.getElementById(i);
  const css=e=>getComputedStyle(e);
  const shown=e=>{for(let n=e;n&&n!==document.documentElement;n=n.parentElement){const s=css(n);if(s.display==="none"||s.visibility==="hidden")return false}
    if(e.closest(".vh,.sr-only,[hidden]"))return false;const d=e.closest("details:not([open])");if(d&&!e.closest("summary"))return false;const r=e.getBoundingClientRect();return r.width>0&&r.height>0};
  const name=e=>{const p=[];for(let n=e;n&&n!==document.body&&p.length<4;n=n.parentElement)p.push(n.tagName.toLowerCase()+(n.id?"#"+n.id:"")+(typeof n.className==="string"&&n.className?"."+n.className.trim().split(/\s+/)[0]:""));return p.join("<")};
  const scroller=(e,stop)=>{for(let n=e.parentElement;n&&n!==stop.parentElement;n=n.parentElement)if(/(auto|scroll)/.test(css(n).overflowX))return n;return null};
  const canvas=document.createElement("canvas").getContext("2d");
  const width=(e,text)=>{const s=css(e);canvas.font=s.fontStyle+" "+s.fontWeight+" "+s.fontSize+" "+s.fontFamily;return canvas.measureText(text).width};
  function measure(region,phone){
    const found=[],seen=new Set(),vw=document.documentElement.clientWidth;
    const add=(kind,e,detail)=>{const key=kind+"|"+name(e);if(seen.has(key))return;seen.add(key);found.push({kind,at:name(e),text:(e.value||e.textContent||"").trim().slice(0,60),detail:String(detail||"")})};
    if(document.documentElement.scrollWidth>vw+1)add("page-scrolls-sideways",document.documentElement,document.documentElement.scrollWidth+">"+vw);
    const tab=region.closest(".tab");
    if(tab&&tab.scrollWidth>tab.clientWidth+1)add("tab-scrolls-sideways",region,tab.scrollWidth+">"+tab.clientWidth);
    const box=region.getBoundingClientRect();
    if(box.right>vw+1.5||box.left<-1.5)add("box-leaves-window",region,Math.round(box.left)+".."+Math.round(box.right)+" of "+vw);
    const all=[region,...region.querySelectorAll("*")].filter(e=>!e.closest("svg")&&shown(e));
    for(const e of all){
      const r=e.getBoundingClientRect(),s=css(e),inScroll=scroller(e,region);
      if(!inScroll&&(r.right>Math.min(box.right,vw)+1.5||r.left<Math.max(box.left,0)-1.5))add("leaves-box",e,Math.round(r.left)+".."+Math.round(r.right)+" of "+Math.round(box.left)+".."+Math.round(box.right));
      if(s.display!=="inline"&&e.clientWidth>0&&e.scrollWidth>e.clientWidth+1&&!/^(INPUT|TEXTAREA|SELECT)$/.test(e.tagName)){
        if(/(auto|scroll)/.test(s.overflowX)){const own=e.tagName==="PRE"||(phone&&e.tagName==="TABLE")||(e.children.length===1&&e.firstElementChild.tagName==="TABLE");if(!own&&e!==tab)add("needs-sideways-scroll",e,e.scrollWidth+">"+e.clientWidth)}
        else if(s.overflowX!=="visible"){if(!(s.textOverflow==="ellipsis"&&(e.title||e.getAttribute("aria-label"))))add("cut",e,e.scrollWidth+">"+e.clientWidth)}
        else if(!inScroll)add("wider-than-itself",e,e.scrollWidth+">"+e.clientWidth);
      }
      if(e.tagName==="INPUT"&&e.placeholder&&!e.value){const room=e.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight);if(width(e,e.placeholder)>room+2&&!e.title)add("placeholder-cut",e,Math.round(width(e,e.placeholder))+">"+Math.round(room)+" "+e.placeholder)}
    }
    for(const e of all)if(e.matches("section>.body")&&e.clientHeight<Math.min(160,e.scrollHeight)-1)add("squeezed",e,e.clientHeight+"px of "+e.scrollHeight);
    const walker=document.createTreeWalker(region,NodeFilter.SHOW_TEXT);
    for(let t=walker.nextNode();t;t=walker.nextNode()){
      const el=t.parentElement;if(!t.nodeValue.trim()||!el||el.closest("svg,script,style,option,textarea")||!shown(el))continue;
      if(scroller(el,region)||/(auto|scroll)/.test(css(el).overflowX))continue;
      const range=document.createRange();range.selectNodeContents(t);const rr=[...range.getClientRects()].filter(r=>r.width>0);if(!rr.length)continue;
      const left=Math.min(...rr.map(r=>r.left)),right=Math.max(...rr.map(r=>r.right));
      if(right>Math.min(box.right,vw)+1.5||left<Math.max(box.left,0)-1.5)add("text-leaves-box",el,Math.round(left)+".."+Math.round(right)+" of "+Math.round(box.left)+".."+Math.round(box.right));
    }
    const controls=all.filter(e=>/^(BUTTON|SELECT|INPUT|TEXTAREA|SUMMARY)$/.test(e.tagName)&&!/^(checkbox|radio|hidden|range)$/.test(e.type||""));
    if(phone)for(const e of controls){const r=e.getBoundingClientRect();if(r.width<43.5||r.height<43.5)add("under-44px",e,Math.round(r.width)+"x"+Math.round(r.height))}
    for(let i=0;i<controls.length;i++)for(let j=i+1;j<controls.length;j++){
      const a=controls[i],b=controls[j];if(a.contains(b)||b.contains(a)||scroller(a,region)!==scroller(b,region))continue;
      const p=a.getBoundingClientRect(),q=b.getBoundingClientRect();
      if(Math.min(p.right,q.right)-Math.max(p.left,q.left)>2&&Math.min(p.bottom,q.bottom)-Math.max(p.top,q.top)>2)add("controls-overlap",a,"with "+name(b));
    }
    const words=region.innerText||"";
    const raw=words.match(/(?:^|\s)(?:ui|cfg|egress|cli)\.[a-z0-9_]+[._][a-z0-9_.]+/);
    if(raw)add("text-key-shown",region,raw[0].trim());
    const hole=words.match(/\{(?!owner\}|repo\})[a-z_]+\}/);
    if(hole)add("placeholder-shown",region,hole[0]);
    if(words.trim().length<10)add("empty",region,words.trim().length+" characters");
    return {found,chars:words.trim().length,controls:controls.length,width:vw};
  }
  const open=box=>box.querySelectorAll("details").forEach(d=>{d.open=true});
  const button=(host,key)=>[...host.querySelectorAll("button")].find(b=>b.textContent===T(key));
  async function tab(t){showTab(t);await wait(250)}
  async function sub(id){showTab("cfg");await until(()=>CFG.groups.length&&$id("cfp-"+id));cfgShowTab(id);await wait(250)}
  const dialog=()=>[...document.querySelectorAll(".dlg:not([hidden]) .dlg-box")].pop();
  const steps={
    async extensions(){await sub("plugins");return until(()=>$id("plugins-catalog")&&$id("plugins-catalog").querySelector("li")&&$id("plugins-catalog"))},
    async extensions_install(){await sub("plugins");const box=await until(()=>$id("plugins-catalog")&&$id("plugins-catalog").querySelector(".plugins-install")&&$id("plugins-catalog"));if(!box)return null;
      box.querySelector(".plugins-install input").value="C:\\Users\\demo\\Downloads\\demo-badges-0.3.0.plugin.zip";button(box,"ui.plugins.inspect").click();return until(dialog)},
    async proposals(){await tab("al");return until(()=>$id("assistant-proposals")&&$id("assistant-proposals").querySelector("li")&&$id("assistant-proposals"))},
    async chat(){await tab("al");const box=await until(()=>$id("assistant-chat")&&$id("assistant-chat").querySelector("input")&&$id("assistant-chat"));if(!box)return null;
      const input=box.querySelector("input");input.value="What is red right now?";input.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true}));await until(()=>box.querySelector("#assistant-log small"));return box},
    async repo_report(){await tab("al");const box=await until(()=>$id("assistant-report")&&$id("assistant-report").querySelector("input")&&$id("assistant-report"),4000);if(!box)return null;
      box.querySelector("input").value="demo-alpha-app";button(box,"ui.assistant.copy_report").click();await until(()=>!box.querySelector("textarea").hidden);return box},
    async collaboration(){await tab("scol");const box=await until(()=>$id("actions-box")&&$id("actions-box").querySelector("details")&&$id("actions-box"));if(!box)return null;
      open(box);const facts=button(box,"ui.actions.facts");if(facts)facts.click();const read=button(box,"ui.actions.read_inputs");if(read)read.click();await wait(600);open(box);return box},
    async environment(){await tab("scol");const box=await until(()=>$id("actions-box")&&$id("actions-box").querySelector("details")&&$id("actions-box"));if(!box)return null;
      open(box);const approve=button(box,"ui.actions.approve");if(!approve)return null;approve.click();
      if(!await until(()=>$id("actions-msg")&&$id("actions-msg").querySelectorAll("button").length>=3))return null;$id("actions-msg").scrollIntoView({block:"center"});return $id("actions-msg")},
    async environment_confirm(){const msg=await steps.environment();if(!msg)return null;msg.querySelector("button:last-of-type").click();return until(dialog)},
    async roles_groups(){await tab("fleet");const box=await until(()=>$id("fleet-columns")&&$id("fleet-columns").querySelector("li")&&$id("fleet-columns"));if(box)open(box);return box},
    async posture(){await tab("ssec");const box=await until(()=>$id("posture-box")&&$id("posture-box").querySelector("table")&&$id("posture-box"));if(box)open(box);return box},
    async compliance(){await tab("ssec");const box=await until(()=>$id("compliance-box")&&$id("compliance-box").querySelector("button")&&$id("compliance-box"));if(!box)return null;
      box.querySelector("button").click();await until(()=>box.querySelector("li"));return box},
    async external_ci(){await tab("sci");const box=await until(()=>$id("extci-box")&&$id("extci-box").querySelector("li")&&$id("extci-box"));if(!box)return null;
      const log=button(box,"ui.extci.log");if(log){log.click();await until(()=>box.querySelector(".extci-log").textContent)}return box},
    async external_ci_test(){await sub("extci");const box=await until(()=>$id("extci-test"));if(!box)return null;
      box.querySelector("input").value="gitlab;repo=demo-alpha-app;url=https://gitlab.example.org;project=demo-group/alpha";box.querySelector("button").click();await until(()=>box.querySelector("[role=status]").textContent.length>4);return box},
    async update_notice(){await tab("now");if(!window.supplyNotice)return null;
      window.supplyNotice.show({version:"9.9.9",current:"2.2.0",notes:window.__notes||"",changelog:"https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/blob/main/monitor/CHANGELOG.md"});return until(dialog)},
    async group(){return until(()=>document.querySelector("#list li")&&document.body)}
  };
  window.__run=async function(step,phone){
    const out={step,found:[]};
    try{
      if(step!=="group")await until(()=>typeof TABS!=="undefined"&&typeof DATA!=="undefined"&&DATA&&window.FAM);
      document.querySelectorAll(".dlg:not([hidden])").forEach(d=>{const no=d.querySelector("#ask-no,#updn-later,.ib");if(no)no.click()});
      await wait(150);
      const region=await steps[step]();
      if(!region){out.missing=true;return out}
      region.scrollIntoView({block:"start"});await wait(350);
      Object.assign(out,measure(region,phone));
    }catch(e){out.found.push({kind:"script",at:step,text:"",detail:String(e&&e.stack||e).slice(0,300)})}
    return out;
  };
})();
"""


def browser_here():
    """The browser, or None when it or the package for its protocol is not there."""
    try:
        import websockets  # noqa: F401
    except ImportError:
        return None
    return co.edge()


def problems(report):
    """The lines of what is wrong in the report of one step (empty = fine)."""
    step = report.get("step")
    if report.get("missing"):
        return [f"{step}: the box did not appear"]
    lines = [f"{step}: {f['kind']} {f['at']} ({f['detail']}) {f['text']!r}" for f in report.get("found", [])]
    return lines + [f"{step}: {e}" for e in report.get("errors", [])]


class Session:
    """One headless browser and one tab, driven through the DevTools protocol."""

    def __init__(self, browser):
        self.port = co.free_port()
        self.profile = tempfile.mkdtemp(prefix="ghamon_parts_")
        self.child = subprocess.Popen([browser, "--headless=new", f"--user-data-dir={self.profile}", f"--remote-debugging-port={self.port}", "--remote-allow-origins=*", "--disable-gpu", "--hide-scrollbars",
                                       *(["--no-sandbox", "--disable-dev-shm-usage"] if sys.platform.startswith("linux") else []), "about:blank"],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        self.errors, self.counter, self.ws = [], 0, None

    async def start(self):
        import websockets
        url = ""
        for _ in range(120):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=2) as reply:
                    pages = [t for t in json.loads(reply.read()) if t.get("type") == "page"]
                if pages:
                    url = pages[0]["webSocketDebuggerUrl"]
                    break
            except OSError:
                pass
            await asyncio.sleep(0.5)
        if not url:
            raise RuntimeError("the browser did not start")
        self.ws = await websockets.connect(url, max_size=None)
        for domain in ("Page", "Runtime", "Log"):
            await self.call(domain + ".enable")
        await self.call("Page.addScriptToEvaluateOnNewDocument", source=HEAD)

    def note(self, method, params):
        if method == "Runtime.exceptionThrown":
            detail = params.get("exceptionDetails", {})
            self.errors.append("exception: " + str((detail.get("exception") or {}).get("description") or detail.get("text", ""))[:200])
        elif method == "Runtime.consoleAPICalled" and params.get("type") in ("error", "assert"):
            self.errors.append("console.error: " + " ".join(str(a.get("value", a.get("description", ""))) for a in params.get("args", []))[:200])
        elif method == "Log.entryAdded" and params.get("entry", {}).get("level") == "error":
            entry = params["entry"]
            self.errors.append(f"console: {entry.get('text', '')[:160]} {entry.get('url', '')[:120]}")

    async def call(self, method, **params):
        self.counter += 1
        wanted = self.counter
        await self.ws.send(json.dumps({"id": wanted, "method": method, "params": params}))
        while True:
            reply = json.loads(await asyncio.wait_for(self.ws.recv(), 90))
            if reply.get("id") == wanted:
                if "error" in reply:
                    raise RuntimeError(f"{method}: {reply['error']}")
                return reply.get("result", {})
            self.note(reply.get("method", ""), reply.get("params", {}))

    async def evaluate(self, expression):
        answer = await self.call("Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in answer:
            raise RuntimeError("the measuring script failed: " + str(answer["exceptionDetails"])[:400])
        return answer.get("result", {}).get("value")

    async def size(self, width, height):
        await self.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)

    async def open(self, url, notes):
        self.errors.clear()
        await self.call("Page.navigate", url=url)
        for _ in range(150):
            await asyncio.sleep(0.2)
            try:
                if await self.evaluate(f"document.readyState==='complete'&&location.href!=='about:blank'&&!window.__old"):
                    break
            except RuntimeError:
                pass
        await self.evaluate("window.__old=1;window.__notes=" + json.dumps(notes))
        await self.evaluate(LIB)

    async def step(self, step, phone):
        report = await self.evaluate(f"window.__run({json.dumps(step)},{json.dumps(phone)})")
        page = await self.evaluate("(window.__parts||{errors:[]}).errors.splice(0)")
        report["errors"] = list(dict.fromkeys(self.errors + page))
        self.errors.clear()
        return report

    async def picture(self, target):
        data = await self.call("Page.captureScreenshot", format="png")
        Path(target).write_bytes(base64.b64decode(data.get("data", "")))

    async def close(self):
        if self.ws is not None:
            await self.ws.close()
        self.child.terminate()
        try:
            self.child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.child.kill()
        shutil.rmtree(self.profile, ignore_errors=True)


async def _run(browser, base, jobs, shots, quiet):
    summaries = json.loads((ROOT / "monitor" / "assets" / "release_summaries" / "2.2.0.json").read_text(encoding="utf-8"))
    results = {}
    session = Session(browser)
    try:
        await session.start()
        for lang, size in jobs:
            width, height = SIZES[size]
            phone = size == "phone"
            await session.size(width, height)
            theme = "dark" if lang in co.DARK else "light"
            for url, steps in ((f"{base}/?lang={lang}&theme={theme}&nowizard=1", STEPS), (f"{base}/g/alpha", (GROUP,))):
                if steps == (GROUP,) and lang != jobs[0][0]:
                    continue      # the screen of a group has no translated text: one language is enough for each size
                await session.open(url, summaries.get(lang, summaries["en"]))
                for name in steps:
                    report = await session.step(name, phone)
                    found = problems(report)
                    if name != GROUP and report.get("width") not in (None, width):
                        found.append(f"{name}: the window is {report.get('width')} px wide, not {width}")
                    results[(lang, size, name)] = found
                    if shots and not report.get("missing"):
                        await session.picture(Path(shots) / f"{name}_{lang}_{size}.png")
            if not quiet:
                print(lang, size, sum(len(v) for k, v in results.items() if k[:2] == (lang, size)), "problems", flush=True)
    finally:
        await session.close()
    return results


def run(langs=LANGS, sizes=tuple(SIZES), shots=None, quiet=True):
    """{(lang, size, step): [problem, ...]}; None when there is no browser or no `websockets`."""
    browser = browser_here()
    if not browser:
        return None
    if shots:
        Path(shots).mkdir(parents=True, exist_ok=True)
    port = co.free_port()
    demo = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_monitor.py"), str(port), "--parts"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
    try:
        for _ in range(80):
            try:
                socket.create_connection(("127.0.0.1", port), 0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("the demo monitor did not start")
        return asyncio.run(_run(browser, f"http://127.0.0.1:{port}", [(lang, size) for lang in langs for size in sizes], shots, quiet))
    finally:
        demo.terminate()
        try:
            demo.wait(timeout=15)
        except subprocess.TimeoutExpired:
            demo.kill()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", nargs="*", default=list(LANGS), choices=list(LANGS))
    ap.add_argument("--size", nargs="*", default=list(SIZES), choices=list(SIZES))
    ap.add_argument("--shots", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    results = run(args.lang, args.size, shots=args.shots or None, quiet=False)
    if results is None:
        print("PARTS=SKIP no browser (Edge, Chrome or Chromium) or no websockets package")
        return 0
    bad = {k: v for k, v in results.items() if v}
    if args.json:
        print(json.dumps({"/".join(k): v for k, v in bad.items()}, indent=1, ensure_ascii=False))
    else:
        for (lang, size, _step), lines in bad.items():
            for line in lines:
                print(f"[{lang}/{size}] {line}")
    print(("PARTS=FAIL" if bad else "PARTS=PASS"), sum(len(v) for v in results.values()), "problems in", len(results), "views")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
