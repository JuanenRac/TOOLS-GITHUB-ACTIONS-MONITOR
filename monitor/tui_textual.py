#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The interactive terminal application (OPTIONAL: it needs the package `textual`; nothing else of the monitor does).

  py -3 tui_textual.py [--lite] [--port N] [--lang CODE] [--theme dark|light]

It reads the same local API as the web page (`/api/data`, `/api/sentinel`, `/api/analytics`, `/api/settings`): no GitHub quota is used. Tabs: Summary, Repositories, Builds, Performance,
Scripts (the workflow linter, with level filters) and Settings (the basic switches). Keys: r refresh, o open the web page, f filter, 1 2 3 lint levels, a About, ? Help, q quit. The data are
read-only; the basic switches of Settings are saved through the same checked API as the page (with its one-use token). The simple Rich view (`tui.py`, with --once) stays as it is.
Without `textual` it says how to install it and exits with code 3.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n  # noqa: E402
import platform_compat  # noqa: E402
import tui  # noqa: E402

INSTALL_HINT = "pip install textual"
BASIC_SWITCHES = ("open_browser", "updates.check", "airgapped", "discovery.events", "discovery.suggest_groups", "discovery.auto_frequency")


def textual_available():
    try:
        import textual  # noqa: F401
        return True
    except ImportError:
        return False


def get(port, path, timeout=6):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}{'&' if '?' in path else '?'}lang={i18n.language()}", timeout=timeout) as answer:
            return json.load(answer)
    except (OSError, ValueError):
        return None


def post(port, path, body):
    """A checked write with the one-use token the page uses too."""
    token = (get(port, "/api/session-token") or {}).get("token", "")
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode("utf-8"), method="POST", headers={"Content-Type": "application/json", "X-Monitor-Token": token})
    try:
        with urllib.request.urlopen(request, timeout=8) as answer:
            return json.load(answer)
    except urllib.error.HTTPError as error:
        try:
            return json.load(error)
        except ValueError:
            return {"ok": False}
    except (OSError, ValueError):
        return {"ok": False}


# --- pure helpers (tested without Textual) ------------------------------------------------------------------------------------------------------------------------------------------------
def repo_rows(data, query=""):
    """[(repo, last workflow, result, hours ago)] for the table of repositories, filtered by a text."""
    rows = []
    for repo in (data or {}).get("repos") or []:
        if query and query.lower() not in repo.lower():
            continue
        runs = [r for r in (data.get("runs") or []) if r.get("repo") == repo]
        last = runs[0] if runs else None
        rows.append((repo, (last or {}).get("name") or "–", (last or {}).get("conclusion") or (last or {}).get("status") or "–", tui.hours((last or {}).get("seconds") or 0) if last else "–"))
    return rows


def build_rows(data, query=""):
    runs = list((data or {}).get("active") or []) + [r for r in ((data or {}).get("runs") or []) if r.get("status") == "completed"][:40]
    return [(r.get("repo"), r.get("name"), r.get("status") if r.get("status") != "completed" else r.get("conclusion"), r.get("branch") or "", tui.hours(r.get("seconds") or 0))
            for r in runs if not query or query.lower() in (str(r.get("repo")) + str(r.get("name"))).lower()]


def perf_rows(analytics):
    return [(r.get("repo"), r.get("workflow"), r.get("n"), r.get("p50"), r.get("p95")) for r in ((analytics or {}).get("duration") or [])][:60]


def lint_rows(snapshot, levels=("info", "warn", "bad")):
    return [(r.get("repo"), r.get("file"), r.get("line"), r.get("rule"), r.get("severity")) for r in (((snapshot or {}).get("lint") or {}).get("rows") or []) if r.get("severity") in levels]


def summary_text(data, snapshot):
    t = i18n.t
    data, snapshot = data or {}, snapshot or {}
    fig = data.get("figures") or {}
    rate = data.get("rate") or {}
    lines = [f"{t('tui.running')}: {fig.get('active', 0)}   {t('tui.queued')}: {fig.get('queued', 0)}   {t('tui.red')}: {fig.get('red', len((snapshot.get('a2') or {}).get('red') or []))}",
             f"24 h: {fig.get('ok24', 0)} ok / {fig.get('fail24', 0)} fail / {fig.get('min24', 0)} min",
             f"{t('tui.repos')}: {len(data.get('repos') or [])}   {t('tui.allowance')}: {rate.get('remaining', '–')}/{rate.get('limit', '–')}"]
    for line in (snapshot.get("parte") or [])[:8]:
        lines.append(f"[{line.get('level')}] {line.get('text')}")
    return "\n".join(lines)


def make_app(port, lite=False, theme="dark"):
    """The Textual application (imports Textual here so the helpers above need nothing)."""
    from textual.app import App, ComposeResult
    from textual.containers import VerticalScroll
    from textual.screen import ModalScreen
    from textual.widgets import DataTable, Footer, Header, Input, Static, Switch, TabbedContent, TabPane, Label

    t = i18n.t

    class TextScreen(ModalScreen):
        BINDINGS = [("escape", "app.pop_screen", "Esc")]

        def __init__(self, text):
            super().__init__()
            self.text = text

        def compose(self):
            with VerticalScroll():
                yield Static(self.text, markup=False)

    class HelpScreen(ModalScreen):
        BINDINGS = [("escape", "app.pop_screen", "Esc")]

        def __init__(self, topic="readme"):
            super().__init__()
            self.topic = topic

        def compose(self):
            yield Input(placeholder=t("ui.help_search_ph"), id="help-q")
            with VerticalScroll():
                yield Static("", id="help-text", markup=False)

        def on_mount(self):
            self.show(self.topic)

        def show(self, name):
            import helpdocs
            code, text = helpdocs.console([name] if name else [], i18n.language(), t)
            self.query_one("#help-text", Static).update(text)

        def on_input_submitted(self, event):
            import helpdocs
            query = event.value.strip()
            if not query:
                self.show("")
                return
            code, text = helpdocs.console(["--search"] + query.split(), i18n.language(), t)
            self.query_one("#help-text", Static).update(text)

    class MonitorApp(App):
        TITLE = "GitHub Actions"
        BINDINGS = [("r", "refresh", "Refresh"), ("o", "open_web", "Web"), ("f", "focus_filter", "Filter"), ("a", "about", "About"), ("question_mark", "help", "?"), ("q", "quit", "Quit"),
                    ("1", "level('info')", "info"), ("2", "level('warn')", "warn"), ("3", "level('bad')", "error")]

        def __init__(self):
            super().__init__()
            self.port, self.lite = port, lite
            self.data, self.snapshot, self.analytics = None, None, None
            self.levels = {"info", "warn", "bad"}
            self.query = ""
            self.dark = theme == "dark"
            self.title = "GitHub Actions Monitor " + ("LITE" if lite else "COMPLETE")

        def compose(self) -> ComposeResult:
            yield Header()
            yield Input(placeholder=t("ui.f_search_ph"), id="filter")
            with TabbedContent(id="tabs"):
                with TabPane(t("ui.tab_now"), id="summary"):
                    yield Static("", id="summary-text", markup=False)
                with TabPane(t("ui.tab_repos"), id="repos"):
                    yield DataTable(id="repos-table")
                with TabPane(t("ui.th_workflow"), id="builds"):
                    yield DataTable(id="builds-table")
                with TabPane(t("ui.tab_charts"), id="perf"):
                    yield DataTable(id="perf-table")
                if not lite:
                    with TabPane("Scripts", id="scripts"):
                        yield DataTable(id="lint-table")
                with TabPane(t("ui.tab_cfg"), id="settings"):
                    with VerticalScroll(id="settings-box"):
                        yield Label(t("ui.cfg_g_basic"))
            yield Footer()

        def on_mount(self):
            for table, columns in (("repos-table", ("tui.col_repo", "tui.col_workflow", "ui.th_result", "tui.col_time")), ("builds-table", ("tui.col_repo", "tui.col_workflow", "ui.th_result", "ui.th_branch", "tui.col_time"))):
                self.query_one("#" + table, DataTable).add_columns(*[t(c) for c in columns])
            self.query_one("#perf-table", DataTable).add_columns(t("ui.th_repo"), t("ui.th_workflow"), t("ui.th_samples"), t("ui.th_p50"), t("ui.th_p95"))
            if not self.lite:
                self.query_one("#lint-table", DataTable).add_columns(t("ui.th_repo"), t("ui.th_file"), t("ui.th_line"), t("ui.th_rule"), t("ui.th_severity"))
            self.set_interval(5, self.action_refresh)
            self.action_refresh()

        def action_refresh(self):
            self.run_worker(self.load, thread=True, exclusive=True)

        def load(self):
            data = get(self.port, "/api/data")
            self.data = (data or {}).get("data")
            self.snapshot = ((get(self.port, "/api/sentinel") or {}).get("data")) if not self.lite else None
            self.analytics = get(self.port, "/api/analytics") if not self.lite else None
            settings = get(self.port, "/api/settings")
            self.call_from_thread(self.paint, settings)

        def paint(self, settings):
            self.query_one("#summary-text", Static).update(summary_text(self.data, self.snapshot) if self.data else t("lp.not_running", port=self.port))
            for name, rows in (("repos-table", repo_rows(self.data, self.query)), ("builds-table", build_rows(self.data, self.query)), ("perf-table", perf_rows(self.analytics))):
                table = self.query_one("#" + name, DataTable)
                table.clear()
                for row in rows:
                    table.add_row(*[str(c) for c in row])
            if not self.lite:
                table = self.query_one("#lint-table", DataTable)
                table.clear()
                for row in lint_rows(self.snapshot, tuple(self.levels)):
                    table.add_row(*[str(c) for c in row])
            self.paint_settings(settings)

        def paint_settings(self, settings):
            box = self.query_one("#settings-box")
            if box.children and len(box.children) > 1:
                return
            for group in (settings or {}).get("groups") or []:
                if group["id"] != "basic":
                    continue
                for field in group["fields"]:
                    if field["key"] in BASIC_SWITCHES and field["type"] == "bool":
                        box.mount(Label(t("cfg.f." + field["key"])))
                        box.mount(Switch(value=bool(field["value"]), id="sw-" + field["key"].replace(".", "-")))

        def on_switch_changed(self, event):
            key = next((k for k in BASIC_SWITCHES if "sw-" + k.replace(".", "-") == event.switch.id), None)
            if key:
                result = post(self.port, "/api/settings", {"changes": {key: bool(event.value)}})
                self.notify(t("ui.cfg_saved", n=len(result.get("changed", []))) if result.get("ok") else t("ui.cfg_not_saved", why=str(result.get("errors", ""))), timeout=3)

        def on_input_changed(self, event):
            if event.input.id == "filter":
                self.query = event.value
                self.paint(None)

        def action_focus_filter(self):
            self.query_one("#filter", Input).focus()

        def action_open_web(self):
            webbrowser.open(f"http://127.0.0.1:{self.port}/")

        def action_level(self, name):
            self.levels ^= {name}
            self.paint(None)

        def action_about(self):
            import about
            data = about.lone(lite=self.lite)
            self.push_screen(TextScreen(about.console_text(data, t)))

        def action_help(self):
            tab = self.query_one("#tabs", TabbedContent).active
            self.push_screen(HelpScreen({"summary": "readme", "repos": "readme", "perf": "analytics", "scripts": "console_tools", "settings": "settings"}.get(tab, "readme")))

    return MonitorApp()


def main(argv=None):
    i18n.cli_language()
    platform_compat.console_utf8()
    ap = argparse.ArgumentParser(description=i18n.t("tui.description"))
    ap.add_argument("--lite", action="store_true", help=i18n.t("tui.help_lite"))
    ap.add_argument("--port", type=int, default=None, help=i18n.t("lp.help_port"))
    ap.add_argument("--theme", choices=("dark", "light"), default="dark", help=i18n.t("tui.help_theme"))
    ap.add_argument("--lang", metavar="CODE", help=i18n.t("cli.help_lang"))
    args = ap.parse_args(argv)
    if args.lang:
        i18n.set_language(args.lang)
    port = args.port or tui.default_port(args.lite)
    if not textual_available():
        print(i18n.t("tui.need_textual", cmd=INSTALL_HINT))
        return 3
    if get(port, "/api/health") is None:
        print(i18n.t("lp.not_running", port=port))
        return 2
    make_app(port, args.lite or port == 8766, args.theme).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
