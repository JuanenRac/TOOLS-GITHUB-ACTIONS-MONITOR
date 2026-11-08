#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/make_screenshots.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Photographs the monitor with invented data (tools/demo_monitor.py), in the light and the dark theme, for docs/screenshots/.

    python tools/make_screenshots.py [--only NAME ...] [--console] [--web]

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
EDGES = (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", "/usr/bin/microsoft-edge", "/usr/bin/chromium", "/usr/bin/google-chrome")
TABS = ("interface", "basic", "general", "polling", "cache", "sentinel", "surface", "readiness", "paths", "outputs", "ai", "webhook", "notify", "analytics", "lint", "console")
WEB = [("about", "tab=now&dlg=about", (1400, 900)), ("help", "tab=cfg&dlg=help&topic=sentinel", (1400, 900)), ("now", "tab=now", (1400, 820)), ("sentinel", "tab=sent&open=a2", (1400, 1000)), ("sentinel_queue", "tab=sent&open=a5", (1400, 900)), ("sentinel_analytics", "tab=sent&open=a12,a13", (1400, 1200)),
       ("charts", "tab=charts", (1400, 820)), ("repositories", "tab=repos", (1400, 820)), ("history", "tab=hist", (1400, 820))] + [(f"settings_{t}", f"tab=cfg&cfgtab={t}", (1400, 820)) for t in TABS]


LITE_WEB = [("lite_about", "tab=now&dlg=about", (1400, 900)), ("lite_basic", "tab=cfg&cfgtab=basic", (1400, 900)), ("lite_now", "tab=now", (1400, 820)), ("lite_charts", "tab=charts", (1400, 820)), ("lite_history", "tab=hist", (1400, 820)), ("lite_settings", "tab=cfg&cfgtab=general", (1400, 700))]


def edge():
    for path in EDGES:
        if Path(path).is_file():
            return path
    found = shutil.which("msedge") or shutil.which("chromium") or shutil.which("google-chrome")
    if found:
        return found
    raise SystemExit("Microsoft Edge (or Chromium) was not found")


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def shot(url, target, size, tries=3):
    """One headless screenshot with its own temporary profile; tried again when Edge leaves no file (it sometimes does right after another run)."""
    for attempt in range(tries):
        profile = tempfile.mkdtemp(prefix="ghamon_edge_")
        Path(target).unlink(missing_ok=True)
        try:
            subprocess.run([edge(), "--headless=new", f"--user-data-dir={profile}", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=9000", f"--window-size={size[0]},{size[1]}",
                            f"--screenshot={target}", url], capture_output=True, timeout=120)
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
    return False


def clean(text):
    """No local path in a picture: the folder of the repository becomes ~/github_actions_monitor."""
    for variant in {str(ROOT), str(ROOT).replace("\\", "/"), str(MON), str(MON).replace("\\", "/")}:
        text = text.replace(variant, "~/github_actions_monitor" + ("/monitor" if variant.endswith("monitor") else ""))
    return re.sub(r"[A-Za-z]:\\Users\\[^\\\s]+", "~", text)


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
    out["read_report"] = ("read_report.py", "py -3 read_report.py --lang en", run(py + [str(MON / "read_report.py"), "--port", str(port), "--lang", "en"]))
    legacy = Path(work) / "legacy"
    shutil.copytree(MON, legacy, ignore=shutil.ignore_patterns("tests", "__pycache__", "docs", "*.json", "actions_monitor_log.txt"))
    shutil.copytree(MON / "locales", legacy / "locales", dirs_exist_ok=True)
    for name in ("eventos_monitor.jsonl", "eventos_estado.json", "PARTE_CENTINELA_DIA_2000-01-01.txt"):
        (legacy / name).write_text("{}\n", encoding="utf-8")
    out["about"] = ("tui.py --about", "py -3 tui.py --about --lang en", run(py + [str(MON / "tui.py"), "--about", "--lang", "en"]))
    out["help_topics"] = ("tui.py --help-topics", "py -3 tui.py --help-topics --lang en", run(py + [str(MON / "tui.py"), "--help-topics", "--lang", "en"]))
    out["doctor"] = ("--doctor", "py -3 actions_monitor.py --doctor --lang en", run(py + ["-c", "import sys; sys.path.insert(0, sys.argv[1]); import doctor, i18n; i18n.set_language('en'); print(doctor.text(doctor.run(), i18n.t, 'lite'))", str(MON)]))
    out["migrate_state"] = ("migrate_state.py", "py -3 migrate_state.py --lang en", run(py + [str(legacy / "migrate_state.py"), "--lang", "en"], cwd=legacy))
    catalog = Path(work) / "catalog"
    catalog.mkdir()
    (catalog / "ecosystems.json").write_text(json.dumps({"ecosystems": {"alpha": {"label": "Alpha", "prefixes": ["demo-alpha-"], "tool": "demo_fetch_and_sign.py"}, "beta": {"label": "Beta", "prefixes": ["demo-beta-"], "tool": "demo_fetch_and_sign.py"}}}), encoding="utf-8")
    (catalog / "targets.json").write_text(json.dumps({"demo-beta-fw": {"workflow": "firmware-build.yml", "tool": "demo_fetch_and_sign.py", "extra": []},
                                                      "demo-alpha-app": {"workflow": "package-build.yml", "tool": "demo_fetch_and_sign.py", "extra": []}}), encoding="utf-8")
    (catalog / "profiles.json").write_text(json.dumps({"min_rate_remaining": 1500, "canary_wait_seconds": 1800, "profiles": {"release": {"description": "Every signed target of the demo ecosystems.", "workflows": ["firmware-build.yml", "package-build.yml"],
                                                                                                                                       "ecosystems": ["alpha", "beta"], "canary": True}}}), encoding="utf-8")
    env = {"MONITOR_ECOSYSTEMS_FILE": str(catalog / "ecosystems.json"), "MONITOR_TARGETS_FILE": str(catalog / "targets.json"), "MONITOR_PROFILES_FILE": str(catalog / "profiles.json")}
    out["plan"] = ("gha_dispatch_all.py plan", "py -3 gha_dispatch_all.py --lang en plan --profile release", run(py + [str(MON / "gha_dispatch_all.py"), "--lang", "en", "plan", "--profile", "release"], env=env))
    repo = Path(work) / "demo-alpha-app" / ".github" / "workflows"
    repo.mkdir(parents=True)
    (repo / "ci.yml").write_text("name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n      - run: echo \"${{ github.event.issue.title }}\"\n", encoding="utf-8")
    out["lint"] = ("lint_workflows.py", "py -3 lint_workflows.py demo-alpha-app --lang en", run(py + [str(MON / "lint_workflows.py"), str(repo.parent.parent), "--lang", "en"]).replace(str(Path(work)), "."))
    return out


def tui_html(port, theme):
    """The terminal view drawn by Rich itself and exported as HTML (needs rich in the interpreter that runs this script)."""
    sys.path.insert(0, str(MON))
    import io
    import tui
    from rich.console import Console
    data, snap = tui.fetch(port)
    console = Console(record=True, width=100, file=io.StringIO(), force_terminal=True, color_system="truecolor")
    console.print(tui.build(data, snap, theme))
    page = console.export_html(inline_styles=True, code_format="<pre>{code}</pre>")
    return re.search(r"<pre>(.*)</pre>", page, re.S).group(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="names of the pictures to redo (web_<name> or console_<name>)")
    ap.add_argument("--web", action="store_true")
    ap.add_argument("--console", action="store_true")
    args = ap.parse_args()
    both = not (args.web or args.console)
    OUT.mkdir(parents=True, exist_ok=True)
    port = free_port()
    demo = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_monitor.py"), str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    work = tempfile.mkdtemp(prefix="ghamon_shots_")
    lite_port = free_port()
    lite = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "demo_monitor.py"), str(lite_port), "--lite"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                socket.create_connection(("127.0.0.1", port), 0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        wanted = lambda name: not args.only or name in args.only   # noqa: E731
        if args.web or both:
            for name, query, size in WEB:
                for theme in ("light", "dark"):
                    if wanted(f"web_{name}"):
                        shot(f"http://127.0.0.1:{port}/?{query}&theme={theme}&lang=en&nowizard=1", str(OUT / f"web_{name}_{theme}.png"), size)
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
        if args.console or both:
            texts = console_texts(port, work)
            for name, (title, command, text) in texts.items():
                for theme in ("light", "dark"):
                    if wanted(f"console_{name}"):
                        page = Path(work) / f"{name}_{theme}.html"
                        page.write_text(console_page(title, command, text, theme), encoding="utf-8")
                        shot(page.as_uri(), str(OUT / f"console_{name}_{theme}.png"), (1100, 40 + 22 * (len(text.splitlines()) + 4)))
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
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
