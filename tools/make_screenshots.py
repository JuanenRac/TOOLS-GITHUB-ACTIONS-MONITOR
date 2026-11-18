#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/make_screenshots.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Photographs the monitor with invented data (tools/demo_monitor.py), in the light and the dark theme, for docs/screenshots/.

    python tools/make_screenshots.py [--only NAME ...] [--console] [--web] [--viewport 1920x1080]

The page: Microsoft Edge in headless mode with a temporary profile (it never touches a browser that is open). The console tools (read_report.py, migrate_state.py,
gha_dispatch_all.py plan, lint_workflows.py, tui.py) run against the demo with the invented catalogue and their text is drawn as a terminal page, also in two themes. Local paths are
replaced by `~/github_actions_monitor` before anything is drawn. tui.py needs the optional package rich.

Output: docs/screenshots/web_<name>_<light|dark>.png and docs/screenshots/console_<name>_<light|dark>.png
"""
import argparse
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MON = ROOT / "monitor"
OUT = ROOT / "docs" / "screenshots"
EDGES = (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe",
         r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
         "/usr/bin/microsoft-edge", "/usr/bin/chromium", "/usr/bin/google-chrome")
VIEWPORT = [1920, 1080]      # the window of every picture of a page that is not a device size (1080p; --viewport WxH changes it): the size entries below keep their own
V = None      # in the lists: "the viewport"
TABS = ("interface", "basic", "general", "polling", "cache", "quota", "sentinel", "surface", "readiness", "paths", "outputs", "ai", "webhook", "notify", "analytics", "lint", "advanced", "console")
WEB = [("about", "tab=now&dlg=about", V), ("help", "tab=cfg&dlg=help&topic=sentinel", V), ("now", "tab=now", V), ("alerts", "tab=al", V), ("sentinel", "tab=sci&open=a2", V), ("sentinel_queue", "tab=sci&open=a5", V), ("sentinel_analytics", "tab=sci&open=a12,a13", V),
       ("size_4k", "tab=now", (3840, 2160)), ("size_ultrawide", "tab=now", (3440, 1440)), ("size_portrait", "tab=now", (1080, 1920)), ("size_phone", "tab=now", (390, 844)),
       ("charts", "tab=charts", V), ("repositories", "tab=repos", V), ("team", "tab=team", V), ("history", "tab=hist", V),
       ("menu_groups", "tab=sent", V), ("sentinel_ci", "tab=sci", V), ("sentinel_collab", "tab=scol", V), ("fleet", "tab=fleet", V), ("reports", "tab=rep", V)] + [(f"settings_{t}", f"tab=cfg&cfgtab={t}", V) for t in TABS]


FOLD = 'NAV_CLOSED=["watch","sentinels","team","learn"];applyGroups()'      # the menu with only the System group open (Updates, Settings): at 1080p the long menu hides it
SCROLL_CMP = ('document.querySelectorAll("#t-charts>section").forEach(function(s){if(s.id!=="cmp-sec")s.hidden=true})')      # the section is at the foot of Charts, below the first screen: the other charts step aside so that it fills the picture
RICH_WEB = [("sentinel_delivery", "tab=sdel&open=delivery", V, ""), ("sentinel_supply", "tab=ssup&open=supply", V, ""), ("sentinel_trend", "tab=strend", V, ""),
            ("compare", "tab=charts", V, SCROLL_CMP), ("updates", "tab=upd", V, FOLD)]      # the newest tabs, against tools/demo_monitor.py --rich; a little script scrolls or folds the page


LITE_WEB = [("lite_about", "tab=now&dlg=about", V), ("lite_basic", "tab=cfg&cfgtab=basic", V), ("lite_now", "tab=now", V), ("lite_charts", "tab=charts", V), ("lite_history", "tab=hist", V), ("lite_settings", "tab=cfg&cfgtab=general", V)]


NETWORK_WEB = [("network_now", "tab=now", V), ("network_notices", "tab=now&dlg=notes", V), ("network_settings", "tab=cfg&cfgtab=advanced", V)]      # the page of the network mode: the red bar and the warning for every interface


ACCOUNTS_WEB = [("accounts_all", "account=all", V), ("accounts_one", "account=org-acme", V), ("accounts_live", "view=live&chrome=0", V)]      # the complete edition with several accounts (tools/demo_accounts.py)


SCREEN_WEB = [(f"screen_{kind}_{tag}", f"/screen/{kind}?lang=en&theme=dark&monitor=1", size) for kind in ("overview", "now", "sentinels") for tag, size in (("1080p", (1920, 1080)), ("4k", (3840, 2160)), ("portrait", (1080, 1920)))]      # the wall screens (docs/SCREENS.md): dark only, one picture per resolution


THEME_WEB = [("theme_midnight", "tab=now&theme=Midnight", V)]      # the whole product wears the theme of Settings


SCREEN_EXTRA = [("screen_overview_light", "/screen/overview?lang=en&theme=light&monitor=1", (1920, 1080)), ("screen_overview_midnight", "/screen/overview?lang=en&theme=Midnight&monitor=1", (1920, 1080)), ("screen_sentinels_contrast", "/screen/sentinels?lang=en&theme=contrast&monitor=1", (1920, 1080)),
                ("screen_rotate", "/screen/overview?lang=en&theme=dark&monitor=1&rotate=20", (1920, 1080))]      # the 2.1 wall screens: other themes and the window that turns by itself


LOGO_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 64"><rect x="2" y="12" width="40" height="40" rx="8" fill="#2563eb"/><path d="M12 38l8-10 8 6 8-12" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/><text x="50" y="42" font-family="Arial,sans-serif" font-size="18" font-weight="700" fill="#e2e8f0">Acme Corp</text></svg>'      # an invented organization: the logo of the wall screens


FAILED = []      # the pictures that were not made: the exit code says so


def edge():
    """The browser: --browser / MONITOR_BROWSER first, then Edge, Chrome or Chromium in their usual places and on the PATH."""
    chosen = os.environ.get("MONITOR_BROWSER", "")
    if chosen and Path(chosen).is_file():
        return chosen
    for path in EDGES:
        if Path(path).is_file():
            return path
    found = shutil.which("msedge") or shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")
    if found:
        return found
    raise SystemExit("No browser was found: install Microsoft Edge, Chrome or Chromium, or set MONITOR_BROWSER to the full path of its program")


def updater_shot(target, size=V):
    """The page of the updater (monitor_updater.py web) over this very folder. Its first card holds the folders of this computer, so the picture is cut: the header and the list of versions of GitHub."""
    from PIL import Image
    port = free_port()
    child = subprocess.Popen([sys.executable, "-u", "-I", str(MON / "tools" / "monitor_updater.py"), "web", "--no-browser", "--port", str(port), "--dir", str(MON), "--lang", "en", "--no-gh"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    full = Path(tempfile.mkdtemp(prefix="ghamon_upd_")) / "full.png"
    try:
        found = re.search(r"http://\S+", child.stdout.readline() or "")
        if not found:
            print("the updater did not print its address", flush=True)
            FAILED.append(str(target))
            return False
        time.sleep(3)      # the list of the versions is read from GitHub: a moment to arrive
        if not shot(found.group(0), str(full), size):
            return False
        picture = Image.open(full).convert("RGB")
        top, cut = picture.crop((0, 0, picture.width, 66)), 370      # the header, then the card of the versions
        out = Image.new("RGB", (picture.width, 66 + picture.height - cut), (228, 231, 236))
        out.paste(top, (0, 0))
        out.paste(picture.crop((0, cut, picture.width, picture.height)), (0, 66))
        out.crop((0, 0, out.width, min(out.height, 1126))).save(target, optimize=True)      # ends on the line of a version, not in the middle of one
        return True
    finally:
        child.terminate()
        shutil.rmtree(full.parent, ignore_errors=True)


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def shot(url, target, size, tries=3, flags=()):
    """One headless screenshot with its own temporary profile; tried again when Edge leaves no file (it sometimes does right after another run). size None = the viewport (1920x1080)."""
    size = tuple(size or VIEWPORT)
    for attempt in range(tries):
        profile = tempfile.mkdtemp(prefix="ghamon_edge_")
        Path(target).unlink(missing_ok=True)
        try:
            # Popen with its output sent to the null device and an explicit kill on timeout: with capture_output a browser that leaves a helper process alive keeps the pipe open and
            # subprocess.run waited for ever (or raised after the time limit, which ended the whole script without a word).
            child = subprocess.Popen([edge(), "--headless=new", f"--user-data-dir={profile}", "--disable-gpu", "--hide-scrollbars", "--autoplay-policy=no-user-gesture-required", *flags, "--virtual-time-budget=9000", f"--window-size={size[0]},{size[1]}",
                                      f"--screenshot={target}", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            try:
                child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                child.kill()
                print("(the browser took more than 60 s: ended; the picture is looked for anyway)", flush=True)
        finally:
            shutil.rmtree(profile, ignore_errors=True)
        for _ in range(30):      # Edge may return before the file is complete: wait until it is there and stops growing
            time.sleep(0.5)
            if Path(target).is_file() and Path(target).stat().st_size > 2000:
                size_now = Path(target).stat().st_size
                time.sleep(0.5)
                if Path(target).stat().st_size == size_now:
                    return True
    print("FAILED:", target, flush=True)
    FAILED.append(str(target))
    return False


def cdp_shot(url, target, size, script="", wait=10.0):
    """A screenshot through the DevTools protocol (the optional package `websockets`): the page is loaded at exactly `size`, a small script runs (scroll to a section, fold the menu) and the picture is taken.
    Only the browser started here is ended."""
    import asyncio
    import base64
    import urllib.request
    import websockets
    size = tuple(size or VIEWPORT)
    port = free_port()
    profile = tempfile.mkdtemp(prefix="ghamon_edge_")
    child = subprocess.Popen([edge(), "--headless=new", f"--user-data-dir={profile}", f"--remote-debugging-port={port}", "--remote-allow-origins=*", "--disable-gpu", "--hide-scrollbars", "--autoplay-policy=no-user-gesture-required",
                              f"--window-size={size[0]},{size[1]}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)

    async def go(ws_url):
        async with websockets.connect(ws_url, max_size=None) as ws:
            counter = [0]

            async def call(method, **params):
                counter[0] += 1
                await ws.send(json.dumps({"id": counter[0], "method": method, "params": params}))
                while True:
                    reply = json.loads(await ws.recv())
                    if reply.get("id") == counter[0]:
                        return reply.get("result", {})
            await call("Emulation.setDeviceMetricsOverride", width=size[0], height=size[1], deviceScaleFactor=1, mobile=False)
            await call("Page.navigate", url=url)
            await asyncio.sleep(wait)
            if script:
                await call("Runtime.evaluate", expression=script)
                await asyncio.sleep(3.0)
            return base64.b64decode((await call("Page.captureScreenshot", format="png")).get("data", ""))
    try:
        ws_url = ""
        for _ in range(60):
            try:
                pages = [t for t in json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2).read()) if t.get("type") == "page"]
                if pages:
                    ws_url = pages[0]["webSocketDebuggerUrl"]
                    break
            except OSError:
                pass
            time.sleep(0.5)
        data = asyncio.run(go(ws_url)) if ws_url else b""
        if len(data) > 2000:
            Path(target).write_bytes(data)
            return True
        print("FAILED:", target, flush=True)
        FAILED.append(str(target))
        return False
    finally:
        child.kill()
        shutil.rmtree(profile, ignore_errors=True)


def paletize():
    """docs/screenshots stays small: every picture is saved with 256 colours (Pillow); without Pillow they are left as taken."""
    try:
        from PIL import Image
    except ImportError:
        return
    for path in OUT.glob("*.png"):
        picture = Image.open(path)
        if picture.mode != "P":
            picture.convert("RGB").quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)


def clean(text):
    """No local path in a picture: the folder of the repository becomes ~/github_actions_monitor."""
    for variant in {str(ROOT), str(ROOT).replace("\\", "/"), str(ROOT).replace("\\", "\\\\"), str(MON), str(MON).replace("\\", "/"), str(MON).replace("\\", "\\\\")}:
        text = text.replace(variant, "~/github_actions_monitor" + ("/monitor" if variant.endswith("monitor") else ""))
    return re.sub(r"[A-Za-z]:(?:\\){1,2}Users(?:\\){1,2}[^\\\s']+", "~", text)      # also the form with doubled bars that an error message writes


TERMINAL = """<!doctype html><meta charset="utf-8"><style>
body{{margin:0;background:{bg};font:14px/1.45 Consolas,"Cascadia Mono","DejaVu Sans Mono",monospace}}
.win{{margin:14px;border-radius:10px;overflow:hidden;box-shadow:0 6px 24px rgba(0,0,0,.35);background:{panel};border:1px solid {line}}}
.bar{{padding:8px 14px;background:{bar};color:{mut};font-size:12px}} pre{{margin:0;padding:14px 16px;color:{fg};white-space:pre-wrap;word-break:break-word}}
.p{{color:{ok}}}</style><div class="win"><div class="bar">{title}</div><pre>{body}</pre></div>"""
THEMES = {"dark": dict(bg="#0a0b10", panel="#14161f", line="#2e3444", bar="#202430", mut="#94a3b8", fg="#e2e8f0", ok="#22c55e"),
          "light": dict(bg="#e4e7ec", panel="#f8fafc", line="#c7ccd6", bar="#e9ecf1", mut="#4b5563", fg="#16202c", ok="#15803d")}


def console_page(title, command, text, theme, raw_html=None):
    body = raw_html if raw_html is not None else html.escape(clean(text))
    prompt = f'<span class="p">$</span> {html.escape(command)}\n\n'
    return TERMINAL.format(title=html.escape(title), body=prompt + body, **THEMES[theme])


def run(args, env=None, cwd=None, timeout=90):
    done = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})}, cwd=cwd, timeout=timeout)
    return (done.stdout or "") + (done.stderr or "")


def console_texts(port, work):
    """{name: (title, command, text)} produced by the real tools against the demo."""
    py = [sys.executable, "-I"]
    out = {}
    out["read_report"] = ("read_report.py", "py -3 read_report.py --lang en", run(py + [str(MON / "bin" / "read_report.py"), "--port", str(port), "--lang", "en"]))
    legacy = Path(work) / "legacy"
    shutil.copytree(MON, legacy, ignore=shutil.ignore_patterns("tests", "__pycache__", "docs", "*.json", "actions_monitor_log.txt"))
    shutil.copytree(MON / "assets" / "locales", legacy / "assets" / "locales", dirs_exist_ok=True)
    for name in ("eventos_monitor.jsonl", "eventos_estado.json", "PARTE_CENTINELA_DIA_2000-01-01.txt"):
        (legacy / name).write_text("{}\n", encoding="utf-8")
    out["about"] = ("tui.py --about", "py -3 tui.py --about --lang en", run(py + [str(MON / "bin" / "tui.py"), "--about", "--lang", "en"]))
    out["help_topics"] = ("tui.py --help-topics", "py -3 tui.py --help-topics --lang en", run(py + [str(MON / "bin" / "tui.py"), "--help-topics", "--lang", "en"]))
    out["migrate_state"] = ("migrate_state.py", "py -3 migrate_state.py --lang en", run(py + [str(legacy / "bin" / "migrate_state.py"), "--lang", "en"], cwd=legacy))
    catalog = Path(work) / "catalog"
    catalog.mkdir()
    (catalog / "ecosystems.json").write_text(json.dumps({"ecosystems": {"alpha": {"label": "Alpha", "prefixes": ["demo-alpha-"], "tool": "demo_fetch_and_sign.py"}, "beta": {"label": "Beta", "prefixes": ["demo-beta-"], "tool": "demo_fetch_and_sign.py"}}}), encoding="utf-8")
    (catalog / "targets.json").write_text(json.dumps({"demo-beta-fw": {"workflow": "firmware-build.yml", "tool": "demo_fetch_and_sign.py", "extra": []},
                                                      "demo-alpha-app": {"workflow": "package-build.yml", "tool": "demo_fetch_and_sign.py", "extra": []}}), encoding="utf-8")
    (catalog / "profiles.json").write_text(json.dumps({"min_rate_remaining": 1500, "canary_wait_seconds": 1800, "profiles": {"release": {"description": "Every signed target of the demo ecosystems.", "workflows": ["firmware-build.yml", "package-build.yml"],
                                                                                                                                       "ecosystems": ["alpha", "beta"], "canary": True}}}), encoding="utf-8")
    env = {"MONITOR_ECOSYSTEMS_FILE": str(catalog / "ecosystems.json"), "MONITOR_TARGETS_FILE": str(catalog / "targets.json"), "MONITOR_PROFILES_FILE": str(catalog / "profiles.json"), "MONITOR_ROOT": str(work)}
    out["plan"] = ("gha_dispatch_all.py plan", "py -3 gha_dispatch_all.py --lang en plan --profile release", run(py + [str(MON / "bin" / "gha_dispatch_all.py"), "--lang", "en", "plan", "--profile", "release"], env=env))
    repo = Path(work) / "demo-alpha-app" / ".github" / "workflows"
    repo.mkdir(parents=True)
    (repo / "ci.yml").write_text("name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n      - run: echo \"${{ github.event.issue.title }}\"\n", encoding="utf-8")
    out["lint"] = ("lint_workflows.py", "py -3 lint_workflows.py demo-alpha-app --lang en", run(py + [str(MON / "bin" / "lint_workflows.py"), str(repo.parent.parent), "--lang", "en"]).replace(str(Path(work)), "."))
    return out


def tui_html(port, theme):
    """The terminal view drawn by Rich itself and exported as HTML (needs rich in the interpreter that runs this script)."""
    sys.path.insert(0, str(MON / "src"))
    import io
    from github_actions_monitor.ui import tui
    from rich.console import Console
    data, snap = tui.fetch(port)
    console = Console(record=True, width=100, file=io.StringIO(), force_terminal=True, color_system="truecolor")
    console.print(tui.build(data, snap, theme))
    page = console.export_html(inline_styles=True, code_format="<pre>{code}</pre>")
    return re.search(r"<pre>(.*)</pre>", page, re.S).group(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="names of the pictures to redo (web_<name> or console_<name>)")
    ap.add_argument("--viewport", default="1920x1080", help="the window of the pictures of a page, WIDTHxHEIGHT (default 1920x1080 = 1080p); the device sizes (4K, ultrawide, portrait, phone, wall screens) keep their own")
    ap.add_argument("--web", action="store_true")
    ap.add_argument("--console", action="store_true")
    args = ap.parse_args()
    both = not (args.web or args.console)
    try:
        VIEWPORT[:] = [int(n) for n in args.viewport.lower().split("x")]
        assert len(VIEWPORT) == 2 and min(VIEWPORT) > 0
    except (ValueError, AssertionError):
        raise SystemExit("--viewport wants WIDTHxHEIGHT, for example 1920x1080")
    OUT.mkdir(parents=True, exist_ok=True)
    FAILED.clear()
    print("browser:", edge(), "| output:", OUT, flush=True)
    os.environ["MONITOR_DATA_DIR"] = tempfile.mkdtemp(prefix="ghamon_data_")      # the logo, the backups and the rest of the demo live here and nowhere else
    port = free_port()
    demo = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_monitor.py"), str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    work = tempfile.mkdtemp(prefix="ghamon_shots_")
    lite_port = free_port()
    lite = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_monitor.py"), str(lite_port), "--lite"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    net_port = free_port()
    net = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_monitor.py"), str(net_port), "--network"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rich_port = free_port()
    rich = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_monitor.py"), str(rich_port), "--rich"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    acc_port = free_port()
    acc = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_accounts.py"), str(acc_port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                socket.create_connection(("127.0.0.1", port), 0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            print("The demo monitor did not start on port %d (run `python tools/demo_monitor.py %d` by hand to see why)." % (port, port), flush=True)
            return 1
        wanted = lambda name: not args.only or name in args.only   # noqa: E731
        if args.web or both:
            import urllib.request
            try:
                urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/api/screens/logo", data=LOGO_SVG, method="POST", headers={"Content-Type": "image/svg+xml"}), timeout=10).read()
            except OSError as error:
                print("the logo of the demo organization was not uploaded:", error, flush=True)
        if args.web or both:
            for name, query, size in WEB:
                for theme in ("light", "dark"):
                    if wanted(f"web_{name}"):
                        shot(f"http://127.0.0.1:{port}/?{query}&theme={theme}&lang=en&nowizard=1", str(OUT / f"web_{name}_{theme}.png"), size)
                        print("web", name, theme, flush=True)
        if args.web or both:
            if wanted("web_updater"):
                updater_shot(OUT / "web_updater.png")
                print("web updater", flush=True)
            for name, query, size in THEME_WEB:
                if wanted(f"web_{name}"):
                    shot(f"http://127.0.0.1:{port}/?{query}&lang=en&nowizard=1", str(OUT / f"web_{name}.png"), size)
                    print("web", name, flush=True)
            for name, path, size in SCREEN_EXTRA:
                if wanted(f"web_{name}"):
                    shot(f"http://127.0.0.1:{port}{path}", str(OUT / f"web_{name}.png"), size, flags=("--force-prefers-reduced-motion",))
                    print("web", name, flush=True)
            for name, path, size in SCREEN_WEB:
                if wanted(f"web_{name}"):
                    shot(f"http://127.0.0.1:{port}{path}", str(OUT / f"web_{name}.png"), size, flags=("--force-prefers-reduced-motion",))      # the entrance of the cards is an animation: the picture is taken with the page at rest
                    print("web", name, flush=True)
        if args.web or both:
            for _ in range(60):
                try:
                    socket.create_connection(("127.0.0.1", rich_port), 0.5).close()
                    break
                except OSError:
                    time.sleep(0.5)
            for name, query, size, script in RICH_WEB:
                for theme in ("light", "dark"):
                    if wanted(f"web_{name}"):
                        cdp_shot(f"http://127.0.0.1:{rich_port}/?{query}&theme={theme}&lang=en&nowizard=1", str(OUT / f"web_{name}_{theme}.png"), size, script)
                        print("web", name, theme, flush=True)
        if args.web or both:
            for _ in range(60):
                try:
                    socket.create_connection(("127.0.0.1", lite_port), 0.5).close()
                    break
                except OSError:
                    time.sleep(0.5)
            for name, query, size in LITE_WEB:
                for theme in ("light", "dark"):
                    if wanted(f"web_{name}"):
                        shot(f"http://127.0.0.1:{lite_port}/?{query}&theme={theme}&lang=en&nowizard=1", str(OUT / f"web_{name}_{theme}.png"), size)
                        print("web", name, theme, flush=True)
        if args.web or both:
            for _ in range(60):
                try:
                    socket.create_connection(("127.0.0.1", net_port), 0.5).close()
                    break
                except OSError:
                    time.sleep(0.5)
            for name, query, size in NETWORK_WEB:
                for theme in ("light", "dark"):
                    if wanted(f"web_{name}"):
                        shot(f"http://127.0.0.1:{net_port}/?{query}&theme={theme}&lang=en&nowizard=1", str(OUT / f"web_{name}_{theme}.png"), size)
                        print("web", name, theme, flush=True)
        if args.web or both:
            for _ in range(120):
                try:
                    socket.create_connection(("127.0.0.1", acc_port), 0.5).close()
                    break
                except OSError:
                    time.sleep(0.5)
            time.sleep(6)       # the supervisor starts its three monitors before the page can be served
            for name, query, size in ACCOUNTS_WEB:
                for theme in ("light", "dark"):
                    if wanted(f"web_{name}"):
                        shot(f"http://127.0.0.1:{acc_port}/?{query}&theme={theme}&lang=en&nowizard=1", str(OUT / f"web_{name}_{theme}.png"), size)
                        print("web", name, theme, flush=True)
        if args.console or both:
            texts = console_texts(port, work)
            for name, (title, command, text) in texts.items():
                for theme in ("light", "dark"):
                    if wanted(f"console_{name}"):
                        page = Path(work) / f"{name}_{theme}.html"
                        page.write_text(console_page(title, command, text, theme), encoding="utf-8")
                        shot(page.as_uri(), str(OUT / f"console_{name}_{theme}.png"), (1100, 40 + 22 * (sum(1 + len(line) // 118 for line in clean(text).splitlines()) + 4)))      # a long line wraps: it takes more than one row
                        print("console", name, theme, flush=True)
            try:
                for theme in ("light", "dark"):
                    if wanted("console_tui"):
                        page = Path(work) / f"tui_{theme}.html"
                        page.write_text(console_page("tui.py", "py -3 tui.py --once", "", theme, raw_html=tui_html(port, theme)), encoding="utf-8")
                        shot(page.as_uri(), str(OUT / f"console_tui_{theme}.png"), (1000, 1050))
                        print("console tui", theme, flush=True)
            except ImportError:
                print("rich is not installed: the picture of tui.py was skipped (pip install rich)")
    finally:
        demo.terminate()
        lite.terminate()
        net.terminate()
        rich.terminate()
        if sys.platform == "win32":      # the supervisor started three monitors of its own: its whole tree ends, and only that tree
            subprocess.run(["taskkill", "/PID", str(acc.pid), "/T", "/F"], capture_output=True)
        else:
            acc.terminate()
        shutil.rmtree(work, ignore_errors=True)
        paletize()
    if FAILED:
        print("%d picture(s) were not made; take them by hand (see docs/CONTRIBUTING: start --demo, open the page, save one capture per tab)." % len(FAILED), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
