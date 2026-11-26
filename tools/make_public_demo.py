#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/make_public_demo.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Builds a static copy of the demo monitor (invented data only) and a page that checks a workflow file in the browser.

    python tools/make_public_demo.py OUT_FOLDER [--port 18766] [--pyodide 0.28.3]

It starts tools/demo_monitor.py --rich on 127.0.0.1, reads the page and the GET routes of the frozen contract, and writes them as files. The page then answers every request from those files:
nothing can be changed (every POST is refused), there is no login, and no request leaves for any other address than the ones of the static site. Publishing the folder is a separate step that
a person takes; this tool publishes nothing. It refuses to start when an address that is not on this computer is asked for.

OUT_FOLDER/lint/ runs the workflow linter of the monitor with Pyodide (Python in the browser, loaded from its public CDN): the file typed or chosen stays in the browser."""
import argparse
import io
import json
import re
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PRODUCT = REPO / "monitor"
PYODIDE = "0.28.3"
FORBIDDEN = re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}")

SHIM = """<script>
/* the static demo: requests are answered from the files of this site; nothing can be written */
(function(){
  const base=location.pathname.replace(/[^/]*$/,""),real=window.fetch.bind(window),INDEX=%s;
  const reply=(body,status)=>Promise.resolve(new Response(JSON.stringify(body),{status:status,headers:{"Content-Type":"application/json"}}));
  window.fetch=function(input,init){
    const url=new URL(typeof input==="string"?input:input.url,location.origin);
    if(url.origin!==location.origin)return reply({ok:false,error:"demo"},403);
    if(init&&init.method&&init.method.toUpperCase()!=="GET")return reply({ok:false,error:"demo",status:"demo"},403);
    const at=url.pathname.indexOf("/api/");
    if(at<0)return real(input,init);
    const file=INDEX[url.pathname.slice(at)];
    return file?real(base+file):reply({ok:false,error:"demo"},404);
  };
  window.EventSource=function(){this.close=function(){};this.addEventListener=function(){}};
  if(navigator.serviceWorker)navigator.serviceWorker.register=()=>Promise.reject(new Error("demo"));
})();
</script>"""

LINT_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Workflow check</title>
<style>body{font-family:system-ui,sans-serif;max-width:60rem;margin:0 auto;padding:16px;background:#0d1117;color:#e6edf3}textarea{width:100%%;height:22rem;background:#161b22;color:#e6edf3;font-family:monospace}td,th{border:1px solid #30363d;padding:4px;text-align:left}table{border-collapse:collapse;width:100%%}</style>
</head>
<body>
<h1>Check a GitHub Actions workflow in your browser</h1>
<p>The checks of GitHub Actions Monitor run here with Pyodide. What you paste stays in your browser: nothing is uploaded.</p>
<textarea id="text" aria-label="workflow file" placeholder="Paste a workflow file"></textarea>
<p><button id="go" type="button" disabled>Loading Python...</button></p>
<div id="out" role="status"></div>
<script src="https://cdn.jsdelivr.net/pyodide/v%(version)s/full/pyodide.js"></script>
<script>
(async function(){
  const go=document.getElementById("go"),out=document.getElementById("out");
  const py=await loadPyodide();
  const zip=await (await fetch("monitor.zip")).arrayBuffer();
  py.unpackArchive(zip,"zip",{extractDir:"/home/pyodide/monitor"});
  py.runPython("import sys,json;sys.path.insert(0,'/home/pyodide/monitor/src');from github_actions_monitor.cli import lint_workflows");
  go.disabled=false;go.textContent="Check";
  go.onclick=()=>{
    py.globals.set("WORKFLOW",document.getElementById("text").value);
    const found=JSON.parse(py.runPython("json.dumps(lint_workflows.lint_text(WORKFLOW))"));
    out.textContent="";
    if(!found.length){out.textContent="No findings.";return}
    const t=document.createElement("table");
    [["line","rule","severity","detail"]].concat(found.map(f=>[f.line,f.rule,f.severity,f.detail])).forEach(row=>{const tr=document.createElement("tr");row.forEach(x=>{const td=document.createElement("td");td.textContent=x;tr.append(td)});t.append(tr)});
    out.append(t);
  };
})().catch(e=>{document.getElementById("out").textContent="Could not load: "+e});
</script>
</body>
</html>
"""


def routes():
    """The GET routes that the page may ask for: the frozen contract and the parts."""
    sys.path.insert(0, str(PRODUCT / "src"))
    from github_actions_monitor import families
    contract = json.loads((PRODUCT / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8"))
    found = [row["path"] for row in contract["endpoints"]] + [row["path"] for row in contract.get("unfrozen", []) if not row["path"].endswith("/")]
    found += [route.path for route in families.routes() if route.method == "GET"]
    return sorted({path.split("?")[0] for path in found if "{" not in path and "stream" not in path})


def check_local(url):
    if not re.fullmatch(r"http://127\.0\.0\.1:\d{2,5}(/.*)?", url):
        raise SystemExit("make_public_demo: only the demo on this computer is read, not " + url)
    return url


def read(url, timeout=30):
    with urllib.request.urlopen(check_local(url), timeout=timeout) as answer:      # noqa: S310 - checked above: loopback http only
        return answer.headers.get("Content-Type", ""), answer.read()


def static_page(page, index):
    shim = SHIM % json.dumps(index, sort_keys=True)
    return page.replace("<head>", "<head>\n" + shim, 1)


def lint_site(target, version):
    target.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder in (PRODUCT / "src" / "github_actions_monitor", PRODUCT / "assets" / "locales"):
            for path in sorted(folder.rglob("*")):
                if path.is_file() and path.suffix in (".py", ".json"):
                    archive.write(path, path.relative_to(PRODUCT).as_posix())
    (target / "monitor.zip").write_bytes(buffer.getvalue())
    (target / "index.html").write_text(LINT_PAGE % {"version": version}, encoding="utf-8", newline="\n")


def build(out, port, version=PYODIDE, wait=90):
    out = Path(out)
    (out / "data").mkdir(parents=True, exist_ok=True)
    base = f"http://127.0.0.1:{int(port)}"
    demo = subprocess.Popen([sys.executable, str(REPO / "tools" / "demo_monitor.py"), str(int(port)), "--rich"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        limit = time.time() + wait
        while True:
            try:
                _kind, page = read(base + "/", 5)
                break
            except OSError:
                if time.time() > limit or demo.poll() is not None:
                    raise SystemExit("make_public_demo: the demo did not start")
                time.sleep(1)
        time.sleep(3)
        index = {}
        for path in routes():
            try:
                kind, body = read(base + path)
            except OSError:
                continue
            if not kind.startswith("application/json"):
                continue
            name = "data/" + re.sub(r"[^a-z0-9]+", "_", path[5:].lower()).strip("_") + ".json"
            (out / name).write_bytes(body)
            index[path] = name
        (out / "index.html").write_text(static_page(page.decode("utf-8"), index), encoding="utf-8", newline="\n")
    finally:
        demo.terminate()
        demo.wait(timeout=20)
    lint_site(out / "lint", version)
    (out / ".nojekyll").write_text("", encoding="utf-8")
    for path in out.rglob("*"):
        if path.is_file() and path.suffix in (".json", ".html") and FORBIDDEN.search(path.read_text(encoding="utf-8", errors="replace")):
            raise SystemExit("make_public_demo: something that looks like a token is in " + path.name)
    return index


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out")
    parser.add_argument("--port", type=int, default=18766)
    parser.add_argument("--pyodide", default=PYODIDE)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.pyodide):
        raise SystemExit("make_public_demo: the version of Pyodide is X.Y.Z")
    index = build(args.out, args.port, args.pyodide)
    print(f"DEMO_SITE=WRITTEN {args.out} ({len(index)} answers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
