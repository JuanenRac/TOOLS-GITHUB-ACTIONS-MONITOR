#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The interactive terminal application (OPTIONAL: it needs the package `textual`; nothing else of the monitor does).

  py -3 bin/tui_textual.py [--lite] [--port N] [--lang CODE] [--theme dark|light]

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

from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.util import platform_compat  # noqa: E402
from github_actions_monitor.ui import tui  # noqa: E402
from github_actions_monitor.security import netguard

INSTALL_HINT = "pip install textual"
BASIC_SWITCHES = ("open_browser", "updates.check", "airgapped", "discovery.events", "discovery.suggest_groups", "discovery.auto_frequency")
EDIT_GROUPS = ("basic", "general", "polling", "cache", "analytics", "lint", "console")     # the groups the terminal can edit; the options of security (secure) are changed in the page, with its confirmation
EDIT_TYPES = ("bool", "int", "float", "enum", "text", "names", "patterns", "acts", "intmap")      # lists (names, patterns, acts: separated by commas) and maps (intmap: name=number, name=number) too


def textual_available():
    try:
        import textual  # noqa: F401
        return True
    except ImportError:
        return False


def get(port, path, timeout=6):
    try:
        with netguard.local_open(f"http://127.0.0.1:{port}{path}{'&' if '?' in path else '?'}lang={i18n.language()}", timeout=timeout) as answer:
            return json.load(answer)
    except (OSError, ValueError):
        return None


def post(port, path, body):
    """A checked write with the one-use token the page uses too."""
    token = (get(port, "/api/session-token") or {}).get("token", "")
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode("utf-8"), method="POST", headers={"Content-Type": "application/json", "X-Monitor-Token": token})
    try:
        with netguard.local_open(request, timeout=8) as answer:
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


def editable_fields(settings):
    """[(group, field)] of the settings the terminal application may edit: simple types, in the common groups, never the ones marked secure."""
    out = []
    for group in (settings or {}).get("groups") or []:
        if group.get("id") not in EDIT_GROUPS:
            continue
        for field in group.get("fields") or []:
            if field.get("type") in EDIT_TYPES and not field.get("secure"):
                out.append((group["id"], field))
    return out


LIST_TYPES = ("names", "patterns", "acts")


def format_value(field):
    """The text shown in the box of a field: a list as `a, b, c`, a map as `name=1, other=2`, anything else as it is."""
    value = field.get("value")
    if field.get("type") in LIST_TYPES and isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if field.get("type") == "intmap" and isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    return str(value if value is not None else "")


def parse_value(field, text):
    """The value typed for a field, or (None, reason) when it does not fit; the server checks it again."""
    kind = field.get("type")
    if kind in LIST_TYPES:
        items = [part.strip() for part in str(text).split(",") if part.strip()]
        return (items, None) if len(set(items)) == len(items) else (None, "names")
    if kind == "intmap":
        out = {}
        for part in (p.strip() for p in str(text).split(",") if p.strip()):
            name, sep, number = part.partition("=")
            try:
                if not sep or not name.strip() or name.strip() in out:
                    return None, "map"
                out[name.strip()] = int(number.strip())
            except ValueError:
                return None, "map"
        return out, None
    try:
        if kind == "int":
            return int(str(text).strip()), None
        if kind == "float":
            return float(str(text).strip()), None
    except ValueError:
        return None, "type"
    return str(text).strip(), None


def ai_text(info):
    """The lines of the AI panel from the answer of /api/ai/actions: provider, model, calls today, availability; and what the page would say when the assistant is off."""
    t = i18n.t
    ai = (info or {}).get("ai")
    if not ai:
        return t("ui.tui_ai_off")
    lines = [f"{ai.get('label', '')}", f"{ai.get('provider')} / {ai.get('model') or '-'}   {ai.get('used_today', 0)}/{ai.get('daily_limit', 0)}", str(ai.get("message") or "")]
    state = (info or {}).get("state") or {}
    lines.append(f"actions: {'on' if state.get('enabled') else 'off'}")
    for entry in ((info or {}).get("log") or [])[-8:]:
        lines.append(f"  {entry.get('at', '')} {entry.get('status', '')} {entry.get('action', '')}")
    return "\n".join(lines)


def make_app(port, lite=False, theme="dark"):
    """The Textual application (imports Textual here so the helpers above need nothing)."""
    from textual.app import App, ComposeResult
    from textual.containers import VerticalScroll
    from textual.screen import ModalScreen
    from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Select, Static, Switch, TabbedContent, TabPane

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
            from github_actions_monitor.ui import helpdocs
            code, text = helpdocs.console([name] if name else [], i18n.language(), t)
            self.query_one("#help-text", Static).update(text)

        def on_input_submitted(self, event):
            from github_actions_monitor.ui import helpdocs
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
            self.ai_info = None
            self.fields = {}
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
                if not lite:
                    with TabPane(t("ui.tui_ai"), id="ai"):
                        yield Static("", id="ai-text", markup=False)
                        yield Button(t("ui.tui_ai_explain"), id="ai-explain")
                        yield Static("", id="ai-answer", markup=False)
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
            self.ai_info = get(self.port, "/api/ai/actions") if not self.lite else None
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
            if not self.lite:
                self.query_one("#ai-text", Static).update(ai_text(self.ai_info))
            self.paint_settings(settings)

        def paint_settings(self, settings):
            box = self.query_one("#settings-box")
            if box.children and len(box.children) > 1:
                return
            for group_id, field in editable_fields(settings):
                widget_id = "f-" + field["key"].replace(".", "__")
                self.fields[widget_id] = field
                box.mount(Label(f"{t('ui.cfg_g_' + group_id)} - {t('cfg.f.' + field['key'])}" + (" *" if field.get("restart") else "")))
                if field["type"] == "bool":
                    box.mount(Switch(value=bool(field["value"]), id=widget_id))
                elif field["type"] == "enum":
                    box.mount(Select([(v if v else "-", v) for v in field.get("enum") or []], value=field["value"], allow_blank=False, id=widget_id))
                else:
                    box.mount(Input(value=format_value(field), id=widget_id))

        def save(self, widget_id, value):
            field = self.fields.get(widget_id)
            if field is None or value == field.get("value"):
                return
            result = post(self.port, "/api/settings", {"changes": {field["key"]: value}})
            if result.get("ok"):
                field["value"] = value
            self.notify(t("ui.cfg_saved", n=len(result.get("changed", []))) if result.get("ok") else t("ui.cfg_not_saved", why=str(result.get("errors", ""))), timeout=3)

        def on_switch_changed(self, event):
            self.save(event.switch.id, bool(event.value))

        def on_select_changed(self, event):
            self.save(event.select.id, event.value)

        def on_button_pressed(self, event):
            if event.button.id == "ai-explain":
                self.run_worker(self.explain, thread=True, exclusive=True)

        def explain(self):
            """Asks the assistant to explain the daily report of the sentinel (only if the assistant is on); the answer is labelled as written by an AI."""
            answer = post(self.port, "/api/sentinel/ai", {"kind": "report"})
            text = answer.get("text") if answer.get("ok") else (answer.get("error") or t("ai.is_off"))
            self.call_from_thread(lambda: self.query_one("#ai-answer", Static).update(str(text)[:3000]))

        def on_input_changed(self, event):
            if event.input.id == "filter":
                self.query = event.value
                self.paint(None)

        def on_input_submitted(self, event):
            field = self.fields.get(event.input.id or "")
            if field is not None:
                value, why = parse_value(field, event.value)
                if why:
                    self.notify(t("ui.cfg_not_saved", why=why), timeout=3)
                else:
                    self.save(event.input.id, value)

        def action_focus_filter(self):
            self.query_one("#filter", Input).focus()

        def action_open_web(self):
            webbrowser.open(f"http://127.0.0.1:{self.port}/")

        def action_level(self, name):
            self.levels ^= {name}
            self.paint(None)

        def action_about(self):
            from github_actions_monitor.ui import about
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
