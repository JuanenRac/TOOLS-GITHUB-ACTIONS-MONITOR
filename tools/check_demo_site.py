#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/check_demo_site.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Opens the site made by tools/make_public_demo.py in a real browser and checks that it works.

    python tools/check_demo_site.py SITE_FOLDER [--require]

The folder is served on 127.0.0.1 only. Two pages are opened with a small probe added on the way (the files are not changed): the static demo (it must draw, raise nothing and refuse a write) and the
workflow check (Python must load with Pyodide, which comes from its public CDN, and a workflow with known mistakes must give their rules). The probe sends what it saw back to this server; a request
that would write anything else is counted and fails the check. Without a browser the check passes with a message, unless --require."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_overflow as co  # noqa: E402

#: a workflow with two mistakes the linter knows: an action that is not pinned to a commit and the title of an issue inside a script
WORKFLOW = "name: CI\non: [issues]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: echo \"${{ github.event.issue.title }}\"\n"
EXPECTED_RULES = ("unpinned_uses", "injection")

HEAD = """<script>
window.__seen=[];
window.addEventListener("error",function(e){window.__seen.push("error: "+String(e.message||"").slice(0,200))});
window.addEventListener("unhandledrejection",function(e){window.__seen.push("unhandledrejection: "+String(e.reason&&e.reason.message||e.reason).slice(0,200))});
window.__report=function(name,data){var x=new XMLHttpRequest();x.open("POST","/report/"+name);x.send(JSON.stringify(data))};
</script>"""

DEMO_PROBE = """<script>
setTimeout(async function(){
  var out={errors:window.__seen};
  try{
    var now=document.getElementById("t-now");
    out.text=now?(now.innerText||"").trim().length:0;
    out.shows_demo=document.body.innerText.indexOf("demo-")>=0;
    var answer=await fetch("/api/gh-action/confirm",{method:"POST",body:"{}"});
    out.write=answer.status;
  }catch(e){out.errors.push(String(e).slice(0,200))}
  window.__report("demo",out);
},6000);
</script>"""

LINT_PROBE = """<script>
(function(){
  var started=Date.now(),workflow=%s;
  var timer=setInterval(function(){
    var go=document.getElementById("go"),out=document.getElementById("out");
    if(out.textContent.indexOf("Could not load")===0||Date.now()-started>120000){clearInterval(timer);window.__report("lint",{loaded:false,text:out.textContent.slice(0,400),errors:window.__seen});return}
    if(go.disabled)return;
    clearInterval(timer);
    var data={loaded:true,errors:window.__seen};
    try{
      document.getElementById("text").value=workflow;
      go.click();
      data.rules=[].slice.call(out.querySelectorAll("tr")).slice(1).map(function(row){return row.cells[1].textContent});
      data.text=out.textContent.slice(0,400);
    }catch(e){data.errors.push(String(e).slice(0,200))}
    window.__report("lint",data);
  },500);
})();
</script>"""


class Site(SimpleHTTPRequestHandler):
    reports = {}
    writes = []
    probes = {}

    def log_message(self, *args):
        pass

    def do_GET(self):
        path = self.path.partition("?")[0]
        probe = self.probes.get("index.html" if path in ("/", "/index.html") else path.lstrip("/") + ("index.html" if path.endswith("/") else ""))
        if probe is None:
            return super().do_GET()
        page = Path(self.directory, probe[0]).read_text(encoding="utf-8")
        page = page.replace("<head>", "<head>\n" + HEAD, 1)
        at = page.rfind("</body>")
        body = (page[:at] + probe[1] + page[at:]).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        data = self.rfile.read(min(int(self.headers.get("Content-Length") or 0), 100000))
        if self.path.startswith("/report/"):
            try:
                self.reports[self.path[8:]] = json.loads(data)
            except ValueError:
                self.reports[self.path[8:]] = {"errors": ["the report is not JSON"]}
        else:
            self.writes.append(self.path[:100])
        self.send_response(204)
        self.end_headers()


def judge(reports, writes):
    """The mistakes found in what the two probes saw (an empty list: the site works)."""
    out = []
    demo, lint = reports.get("demo"), reports.get("lint")
    if demo is None:
        out.append("the static demo never answered")
    else:
        if demo.get("errors"):
            out.append("the static demo raised: " + "; ".join(demo["errors"])[:600])
        if not (demo.get("text", 0) > 100 and demo.get("shows_demo")):
            out.append("the static demo drew nothing with the invented data")
        if demo.get("write") != 403:
            out.append(f"a write was not refused by the static demo (status {demo.get('write')})")
    if lint is None:
        out.append("the workflow check never answered")
    elif not lint.get("loaded"):
        out.append("Python did not load in the browser: " + str(lint.get("text"))[:400])
    else:
        missing = [rule for rule in EXPECTED_RULES if rule not in (lint.get("rules") or [])]
        if missing:
            out.append(f"the workflow check did not find {', '.join(missing)} (it said: {str(lint.get('text'))[:300]})")
        if lint.get("errors"):
            out.append("the workflow check raised: " + "; ".join(lint["errors"])[:600])
    if writes:
        out.append("requests that write reached the server: " + ", ".join(writes[:5]))
    return out


def open_page(browser, url, name, wait):
    with tempfile.TemporaryDirectory(prefix="ghamon_site_", ignore_cleanup_errors=True) as profile:
        flags = ["--no-sandbox", "--disable-dev-shm-usage"] if sys.platform.startswith("linux") else []
        child = subprocess.Popen([browser, "--headless=new", f"--user-data-dir={profile}", "--disable-gpu", "--no-first-run", *flags, "--remote-debugging-port=0", url],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        try:
            limit = time.time() + wait
            while name not in Site.reports and time.time() < limit and child.poll() is None:
                time.sleep(0.5)
        finally:
            child.kill()      # only the browser started here
            child.wait(timeout=20)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("site")
    parser.add_argument("--require", action="store_true", help="fail when there is no browser")
    args = parser.parse_args(argv)
    site = Path(args.site).resolve()
    if not (site / "index.html").is_file() or not (site / "lint" / "index.html").is_file():
        print("DEMO_SITE_CHECK=FAIL the folder is not a site made by make_public_demo.py")
        return 1
    browser = os.environ.get("MONITOR_BROWSER") or co.edge()
    if not browser:
        print("DEMO_SITE_CHECK=" + ("FAIL" if args.require else "SKIPPED") + " no browser")
        return 1 if args.require else 0
    Site.reports, Site.writes = {}, []
    Site.probes = {"index.html": ("index.html", DEMO_PROBE), "lint/index.html": ("lint/index.html", LINT_PROBE % json.dumps(WORKFLOW))}
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Site, directory=str(site)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        open_page(browser, base + "/", "demo", 60)
        open_page(browser, base + "/lint/", "lint", 150)
    finally:
        server.shutdown()
        server.server_close()
    mistakes = judge(Site.reports, Site.writes)
    for line in mistakes:
        print("  " + line)
    print("DEMO_SITE_CHECK=" + ("FAIL" if mistakes else "PASS"))
    return 1 if mistakes else 0


if __name__ == "__main__":
    raise SystemExit(main())
