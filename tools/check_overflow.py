#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/check_overflow.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Looks for text that leaves its box in the page of the monitor, in every language and in a wide and a narrow window.

    python tools/check_overflow.py [--lang en de ...] [--size desktop mobile] [--lite] [--network] [--json]

The demo monitor (tools/demo_monitor.py, invented data) is started on a free port, a small relay in front of it adds a measuring script to the page, and Microsoft Edge (or Chrome or
Chromium) in headless mode opens it once per language and window size. The script goes through every section and every tab of the settings and, for each text, checks that it stays
inside every box that has a border or a background (and inside the window): a box whose content is wider than the box, a text cut without an ellipsis, a text pushed out of the
window. A text cut with an ellipsis that has a full-text `title` is accepted. Exit code 0 when nothing overflows (or when there is no browser: it says so and skips), 1 otherwise.
"""
import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
DARK = ("de", "ja", "pt")      # a few languages are measured with the dark theme so both themes are covered
SIZES = {"desktop": (1400, 900), "mobile": (390, 800)}
EDGES = (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe",
         r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
         "/usr/bin/microsoft-edge", "/usr/bin/chromium", "/usr/bin/google-chrome")

# The measuring script: it runs inside the page, after the page's own scripts. Its answer is written into <pre id="overflow-report"> as JSON.
PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),found=[],seen=new Set();
  const css=(e)=>getComputedStyle(e);
  const boxed=(s)=>{const bw=parseFloat(s.borderLeftWidth)+parseFloat(s.borderRightWidth);const bg=s.backgroundColor;return bw>0.5||(bg&&bg!=="rgba(0, 0, 0, 0)"&&bg!=="transparent")};
  const where=(e)=>{let p=[];for(let n=e;n&&n!==document.body&&p.length<4;n=n.parentElement){p.push(n.tagName.toLowerCase()+(n.id?"#"+n.id:"")+(n.classList.length?"."+[...n.classList].slice(0,2).join("."):""))}return p.join("<")};
  const shown=(e)=>{for(let n=e;n&&n!==document.documentElement;n=n.parentElement){const s=css(n);if(s.display==="none"||s.visibility==="hidden")return false}const r=e.getBoundingClientRect();if(e.closest(".vh,.sr-only"))return false;return r.width>0&&r.height>0};
  const scrolls=(s)=>/(auto|scroll)/.test(s.overflowX);
  function add(kind,e,detail,ctx){const key=kind+"|"+where(e);if(seen.has(key))return;seen.add(key);found.push({kind,at:where(e),text:(e.textContent||"").trim().slice(0,70),detail,section:ctx.section})}
  function scan(ctx){
    const vw=document.documentElement.clientWidth;
    if(document.documentElement.scrollWidth>vw+1)found.push({kind:"page",at:"html",text:"",detail:document.documentElement.scrollWidth+">"+vw,section:ctx.section});
    // 1. a box whose content is wider than the box
    for(const e of document.body.querySelectorAll("*")){
      if(["SCRIPT","STYLE","SVG","svg","path","use","defs"].includes(e.tagName)||e.closest("svg")||!shown(e))continue;
      const s=css(e);if(s.display==="inline"||scrolls(s)||e.closest("[data-scroll]"))continue;
      if(e.scrollWidth>e.clientWidth+1&&e.clientWidth>0){
        const sa=(()=>{for(let n=e.parentElement;n;n=n.parentElement)if(scrolls(css(n)))return n;return null})();
        if(sa&&e.clientWidth>=sa.clientWidth-40)continue;      /* wider than itself but inside a box that scrolls sideways: reachable */
        const clipped=s.overflowX!=="visible";
        const ell=s.textOverflow==="ellipsis"&&(e.title||e.getAttribute("aria-label"));
        if(clipped&&ell)continue;
        {const er=e.getBoundingClientRect(),w=[...e.querySelectorAll("*")].find(c=>c.getBoundingClientRect().right>er.right+1);add(clipped?"cut":"wide",e,e.scrollWidth+">"+e.clientWidth+(w?" by "+where(w):""),ctx)}}}
    // 2. a text that leaves a box with border or background, or the window
    const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
    for(let t=walker.nextNode();t;t=walker.nextNode()){
      if(!t.nodeValue.trim())continue;const el=t.parentElement;if(!el||el.closest("svg,script,style")||!shown(el))continue;
      const range=document.createRange();range.selectNodeContents(t);const rr=[...range.getClientRects()].filter(r=>r.width>0);if(!rr.length)continue;
      const left=Math.min(...rr.map(r=>r.left)),right=Math.max(...rr.map(r=>r.right));
      let stop=false;
      for(let a=el;a&&a!==document.documentElement&&!stop;a=a.parentElement){
        const s=css(a);if(scrolls(s)||a.hasAttribute("data-scroll")){stop=true;break}
        if(s.position==="fixed"&&a!==el&&false)break;
        const r=a.getBoundingClientRect();
        if(a===document.body)break;
        if(r.width<=0)continue;
        if(boxed(s)||s.overflowX!=="visible"){
          if(right>r.right+1.5||left<r.left-1.5){const ell=s.textOverflow==="ellipsis"&&(a.title||a.getAttribute("aria-label")||el.title);if(!ell)add("text",a,Math.round(left)+".."+Math.round(right)+" vs "+Math.round(r.left)+".."+Math.round(r.right),ctx)}}}
      if(!stop&&(right>vw+1.5||left<-1.5)&&!el.closest("[aria-hidden=true],.sr-only,.skip"))add("window",el,Math.round(left)+".."+Math.round(right)+" vs "+vw,ctx)}
  }
  const out=document.getElementById("overflow-report")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"overflow-report"}));
  try{
    await wait(900);
    const ctx={section:"start"};scan(ctx);
    for(const t of TABS){showTab(t);await wait(150);ctx.section=t;scan(ctx);
      if(t==="cfg"&&CFG.groups.length)for(const id of cfgTabIds()){cfgShowTab(id);await wait(100);ctx.section="cfg:"+id;scan(ctx)}}
    for(const [name,fn] of [["about",()=>openAbout()],["help",()=>openHelp("cfg",null)],["notes",()=>openNotes()]]){
      try{showTab("now");await fn();await wait(300);ctx.section="dlg:"+name;scan(ctx);const x=document.querySelector(".dlg:not([hidden]) .ib");if(x)x.click();await wait(200)}catch(e){}}
    out.textContent=JSON.stringify({ok:true,found:found});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e),found:found})}
  document.title="overflow-done";
})();
</script>
"""


def edge():
    import os
    chosen = os.environ.get("MONITOR_BROWSER", "")
    if chosen and Path(chosen).is_file():
        return chosen
    for path in EDGES:
        if Path(path).is_file():
            return path
    return shutil.which("msedge") or shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def relay(target_port, probe=None, head=None, change=None):
    """A relay in front of the demo: the page of the monitor comes back with the measuring script before </body>; everything else is passed through. `head` (bytes) is put right after <head>, so
    that it runs before any script of the page; `probe` replaces the measuring script; `change(bytes) -> bytes` edits the page first (the smoke test uses it to break the page on purpose)."""
    tail = (probe if probe is not None else PROBE).encode("utf-8")
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            try:
                with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{target_port}{self.path}"), timeout=30) as reply:
                    body, kind, code = reply.read(), reply.headers.get("Content-Type", "text/html"), reply.status
            except urllib.error.HTTPError as err:
                body, kind, code = err.read(), err.headers.get("Content-Type", "text/plain"), err.code
            if "text/html" in kind and b"</body>" in body:
                if change is not None:
                    body = change(body)
                if head:
                    body = body.replace(b"<head>", b"<head>" + head, 1)
                body = body.replace(b"</body>", tail + b"</body>", 1)
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def measure(browser, url, size, tries=3, report="overflow-report", flags=()):
    """Opens the page and returns the overflows; a browser that answers nothing (a busy computer) is asked again."""
    for attempt in range(tries):
        try:
            return measure_once(browser, url, size, report, flags)
        except RuntimeError:
            if attempt == tries - 1:
                raise
            time.sleep(2)


def measure_once(browser, url, size, report="overflow-report", flags=()):
    """Opens the page once and returns the list of overflows the script found (or raises when the browser gave no answer). With another `report` it returns the whole document the script wrote."""
    profile = tempfile.mkdtemp(prefix="ghamon_ovf_")
    try:
        child = subprocess.Popen([browser, "--headless=new", f"--user-data-dir={profile}", "--disable-gpu", *(["--no-sandbox", "--disable-dev-shm-usage"] if sys.platform.startswith("linux") else []), "--hide-scrollbars", *flags, "--virtual-time-budget=20000", f"--window-size={size[0]},{size[1]}",
                                  "--dump-dom", url], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        try:
            dom = child.communicate(timeout=120)[0].decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            child.kill()
            dom = child.communicate()[0].decode("utf-8", "replace")
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    hit = re.search(r'<pre id="%s"[^>]*>(.*?)</pre>' % re.escape(report), dom, re.S)
    if not hit:
        raise RuntimeError("the browser gave no measurement for " + url)
    import html
    result = json.loads(html.unescape(hit.group(1)))
    if report != "overflow-report":
        return result
    if not result.get("ok"):
        raise RuntimeError("the measuring script failed: " + str(result.get("error")))
    return result["found"]


def run(langs=LANGS, sizes=("desktop", "mobile"), flavor=(), quiet=False):
    """{(lang, size): [overflow, ...]} for every combination; None when there is no browser."""
    browser = edge()
    if not browser:
        return None
    port = free_port()
    demo = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_monitor.py"), str(port), *flavor], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})      # a zone with a long short name (CET) like the one people see
    results = {}
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
        server = relay(port)
        base = f"http://127.0.0.1:{server.server_address[1]}/"
        from concurrent.futures import ThreadPoolExecutor
        jobs = [(lang, size) for lang in langs for size in sizes]

        def one(job):
            lang, size = job
            found = measure(browser, f"{base}?lang={lang}&theme={'dark' if lang in DARK else 'light'}&nowizard=1&open=a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12,a13", SIZES[size])
            if not quiet:
                print(lang, size, len(found), "overflows", flush=True)
            return job, found
        with ThreadPoolExecutor(max_workers=3) as pool:      # three browsers at a time: light enough for a normal computer
            results = dict(pool.map(one, jobs))
    finally:
        if server:
            server.shutdown()
        demo.terminate()
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", nargs="*", default=list(LANGS))
    ap.add_argument("--size", nargs="*", default=["desktop", "mobile"], choices=list(SIZES))
    ap.add_argument("--lite", action="store_true")
    ap.add_argument("--network", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    results = run(args.lang, args.size, flavor=[f for f, on in (("--lite", args.lite), ("--network", args.network)) if on])
    if results is None:
        print("No browser found (Edge, Chrome or Chromium): nothing was measured.")
        return 0
    bad = {k: v for k, v in results.items() if v}
    if args.json:
        print(json.dumps({f"{k[0]}/{k[1]}": v for k, v in results.items()}, indent=1, ensure_ascii=False))
    else:
        for (lang, size), items in bad.items():
            for item in items:
                print(f"[{lang}/{size}] {item['section']}: {item['kind']} {item['at']} ({item['detail']}) {item['text']!r}")
    print("OVERFLOW" if bad else "PASS", sum(len(v) for v in results.values()))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
