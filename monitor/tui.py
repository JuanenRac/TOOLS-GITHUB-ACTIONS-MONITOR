#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A live terminal view of the running monitor (OPTIONAL: it needs the `rich` package; nothing else of the monitor does).

  py -3 tui.py [--port 8765] [--refresh 5] [--once] [--theme dark|light] [--lang CODE]

It reads the local monitor on 127.0.0.1 (`/api/data` and `/api/sentinel`: no GitHub quota is used) and draws a grid that refreshes by itself: what is running, the red workflows, what waits for a
signature and the report of the sentinel. It is read-only: there is no key that re-runs, closes or writes anything. Quit with Ctrl+C.

If `rich` is not installed it says how to install it and exits with code 3; the rest of the monitor and its tests never import this file's dependency.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # works also under `py -3 -I`
import i18n  # noqa: E402
import platform_compat  # noqa: E402

INSTALL_HINT = "pip install rich"


def rich_available():
    try:
        import rich  # noqa: F401
        return True
    except ImportError:
        return False


def default_port(lite=False):
    """8766 for the lite edition (--lite or MONITOR_MODE=lite), 8765 for the complete one."""
    return 8766 if (lite or os.environ.get("MONITOR_MODE", "").strip().lower() == "lite") else 8765


def fetch(port, timeout=6):
    """(monitor data, sentinel snapshot) read from the local monitor; either may be None."""
    out = []
    for path in ("/api/data", "/api/sentinel"):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}?lang={i18n.language()}", timeout=timeout) as answer:
                out.append((json.load(answer) or {}).get("data"))
        except (OSError, ValueError):
            out.append(None)
    return out[0], out[1]


def hours(seconds):
    return f"{int(seconds // 60)}m" if seconds < 5400 else f"{seconds / 3600:.1f}h"


def build(data, snap, theme="dark", lite=False):
    """The Rich renderable of one picture. Needs rich; pure otherwise (it only reads its arguments)."""
    from rich import box
    from rich.console import Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    t = i18n.t
    good, bad, warn, dim = ("bright_green", "bright_red", "bright_yellow", "grey62") if theme == "dark" else ("dark_green", "dark_red", "dark_orange3", "grey37")
    data, snap = data or {}, snap or {}
    head = Text()
    head.append("GitHub Actions " + ("LITE " if lite else "COMPLETE "), style="bold")
    head.append(f"{len(data.get('repos') or [])} {t('tui.repos')}  ", style=dim)
    head.append(f"{len(data.get('active') or [])} {t('tui.running')}  ", style=good if data.get("active") else dim)
    head.append(f"{len((snap.get('a2') or {}).get('red') or [])} {t('tui.red')}  ", style=bad if (snap.get("a2") or {}).get("red") else dim)
    head.append(f"{len((snap.get('a5') or {}).get('pending_sign') or [])} {t('tui.unsigned')}", style=warn)
    rate = data.get("rate") or {}
    if rate:
        head.append(f"   {t('tui.allowance')} {rate.get('remaining')}/{rate.get('limit')}", style=dim)
    running = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
    for column in ("tui.col_repo", "tui.col_workflow", "tui.col_status", "tui.col_time"):
        running.add_column(t(column), overflow="ellipsis", no_wrap=True)
    for run in (data.get("active") or [])[:12]:
        status = t("tui.stuck") if run.get("stuck") else (t("tui.queued") if run.get("status") == "queued" else t("tui.in_progress"))
        running.add_row(str(run.get("repo")), str(run.get("name")), Text(status, style=bad if run.get("stuck") else warn if run.get("status") == "queued" else good), hours(run.get("seconds") or 0))
    reds = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
    for column in ("tui.col_repo", "tui.col_workflow", "tui.col_streak"):
        reds.add_column(t(column), overflow="ellipsis", no_wrap=True)
    for row in ((snap.get("a2") or {}).get("red") or [])[:12]:
        reds.add_row(str(row.get("repo")), str(row.get("workflow")), Text(str(row.get("streak")), style=bad))
    queue = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
    for column in ("tui.col_repo", "tui.col_hours", "tui.col_trust"):
        queue.add_column(t(column), no_wrap=True)
    for row in ((snap.get("a5") or {}).get("sign_queue") or [])[:12]:
        trust = row.get("trust") or "unknown"
        queue.add_row(str(row.get("name")), f"{row.get('hours', 0):.0f}", Text(t("ui.trust_" + trust), style={"verified": good, "failed": bad}.get(trust, dim)))
    report = Text()
    for line in (snap.get("parte") or [])[:10]:
        report.append(f"[{line.get('level')}] ", style={"bad": bad, "warn": warn, "ok": good}.get(line.get("level"), dim))
        report.append(f"{line.get('text')}\n")
    if not report.plain:
        report.append(t("tui.no_data"), style=dim)
    return Group(Panel(head, box=box.ROUNDED), Panel(running, title=t("tui.t_running"), box=box.ROUNDED), Panel(reds, title=t("tui.t_red"), box=box.ROUNDED),
                 Panel(queue, title=t("tui.t_queue"), box=box.ROUNDED), Panel(report, title=t("tui.t_report"), box=box.ROUNDED))


def main(argv=None):
    i18n.cli_language()
    platform_compat.console_utf8()
    ap = argparse.ArgumentParser(description=i18n.t("tui.description"))
    ap.add_argument("--lite", action="store_true", help=i18n.t("tui.help_lite"))
    ap.add_argument("--port", type=int, default=None, help=i18n.t("lp.help_port"))
    ap.add_argument("--refresh", type=int, default=5, help=i18n.t("tui.help_refresh"))
    ap.add_argument("--once", action="store_true", help=i18n.t("tui.help_once"))
    ap.add_argument("--theme", choices=("dark", "light"), default="dark", help=i18n.t("tui.help_theme"))
    ap.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    ap.add_argument("--about", action="store_true", help=i18n.t("mon.help_about"))
    ap.add_argument("--help-topics", nargs="*", metavar="TOPIC", help=i18n.t("mon.help_topics"))
    args = ap.parse_args(argv)
    if args.lang:
        i18n.set_language(args.lang)
    if args.about:
        import about
        print(about.console_text(about.lone(lite=args.lite), i18n.t), end="")
        return 0
    if args.help_topics is not None:
        import helpdocs
        code, text = helpdocs.console(args.help_topics, i18n.language(), i18n.t)
        print(text, end="")
        return code
    if args.port is None:
        args.port = default_port(args.lite)
    if not rich_available():
        print(i18n.t("tui.need_rich", cmd=INSTALL_HINT))
        return 3
    from rich.console import Console
    from rich.live import Live
    console = Console()
    data, snap = fetch(args.port)
    if data is None and snap is None:
        print(i18n.t("lp.not_running", port=args.port))
        return 2
    if args.once:
        console.print(build(data, snap, args.theme, args.lite or args.port == 8766))
        return 0
    try:
        with Live(build(data, snap, args.theme, args.lite or args.port == 8766), console=console, refresh_per_second=2, screen=False) as live:
            while True:
                time.sleep(max(2, args.refresh))
                data, snap = fetch(args.port)
                live.update(build(data, snap, args.theme, args.lite or args.port == 8766))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
