# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The single register of the SURFACES of the monitor and the guard that nothing grows alone. Two parts. The TABS of the page are checked one by one (EXCEPTIONS and PENDING_FOR_ALL name what is missing and the version
that closes it). The other four kinds - every SETTING, every ROUTE (the audited or exempt writes and the frozen reads), every COMMAND of the command line and every TOOL of the MCP server - are checked from the
code itself, so a new one cannot appear without its help, its guide and its words for the AIs and the skills: what is missing today is in fixtures/surfaces_exceptions.json (kind, check, the version that closes
it, the items); the guard fails for something missing that is not there and for an item that is there now and still listed. Tabs:
For each tab: for each surface, every thing a surface needs is checked (the button, its name in the eight languages, its
help topic, the line in the guide of the tabs of the AIs, the row of the table of signals, its place in the lite edition). What a surface still lacks is written in EXCEPTIONS with the version that closes it; the
guard fails when something is missing without an exception, and also when an exception is left over for something that now exists. A new tab that is not in SURFACES fails the guard too."""
import glob
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
LOCALES = {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}
HELPDOCS = (HERE / "src" / "github_actions_monitor" / "ui" / "helpdocs.py").read_text(encoding="utf-8")
SIGNALS = (HERE / "src" / "github_actions_monitor" / "data_pipeline" / "signals.py").read_text(encoding="utf-8")
BRIEFS = (HERE / "src" / "github_actions_monitor" / "data_pipeline" / "briefs.py").read_text(encoding="utf-8")
TABS_FOR_AI = (HERE / "skills" / "external" / "references" / "tabs.md").read_text(encoding="utf-8")

# The single register: every tab of the page. A tab is registered here when it is created.
SURFACES = ("now", "al", "charts", "sent", "sci", "scol", "ssec", "sdel", "ssup", "strend", "syvt", "team", "fleet", "repos", "rep", "trep", "les", "hist", "upd", "cfg")

# Things that do not exist yet for ANY surface (the shared mechanisms still to build) and the version that closes them. When the mechanism exists, its check below turns true and the line must go. Empty today: the decision of the wall
# screens (screens.TAB_DECISIONS) and the demo with data for each tab (tools/demo_monitor.py --rich, TAB_DEMO) exist, and the two checks below look at every tab.
PENDING_FOR_ALL = {}
# Exceptions of one surface: {surface: {check: version}}. Nothing here is silent: each line names the version that closes it.
EXCEPTIONS = {}


def has_button(tab):
    return re.search(rf'<button role="tab" id="n-{tab}" data-tab="{tab}"', PAGE) is not None


def named_in_eight_languages(tab):
    return all(LOCALES[lang].get(f"ui.tab_{tab}") for lang in LANGS)


def has_help_topic(tab):
    return f'"{tab}":' in HELPDOCS or tab in ("cfg",)


def in_the_guide_of_the_ais(tab):
    return f"- `{tab}`:" in TABS_FOR_AI


def has_signal_row(tab):
    return f'"tab:{tab}"' in SIGNALS


def has_brief(tab):
    """The catalogued brief of the tab (data_pipeline/briefs.py) and its place in the master index of the AIs."""
    return f'"{tab}": {{"prefixes"' in BRIEFS and f"`{tab}`" in TABS_FOR_AI


def covered_by_the_common_bar(tab):
    """The common bar (save, print and the two AI indicators) saves the brief of the tab that is open: the tab must have a brief, and the bar must be in the page."""
    return has_brief(tab) and all(x in PAGE for x in ('id="bar-save"', 'id="bar-print"', 'id="bar-ai-int"', 'id="bar-ai-ext"', "/api/report/tab"))


def wall_screen_decided(tab):
    """The decision of the wall screens for the tab: it is shown on one of them (in a field that its answer has) or it says why not (screens.TAB_DECISIONS)."""
    from github_actions_monitor.app import screens
    decision = screens.TAB_DECISIONS.get(tab)
    if not decision:
        return False
    return decision.get("screen") in screens.KINDS if decision.get("screen") else decision.get("reason") in screens.NO_SCREEN_REASONS


def demo_declared(tab):
    """What `tools/demo_monitor.py --rich` puts in the tab is written in its TAB_DEMO (a package without the tools folder cannot check it and does not fail for it)."""
    import ast
    demo = HERE.parent / "tools" / "demo_monitor.py"
    if not demo.is_file():
        return True
    for node in ast.parse(demo.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(getattr(x, "id", "") == "TAB_DEMO" for x in node.targets):
            row = ast.literal_eval(node.value).get(tab)
            return bool(row) and row[0] in ("plain", "rich") and bool(row[1].strip())
    return False


def lite_knows_it(tab):
    lite_tabs = re.search(r'LITE\?\[([^\]]*)\]', PAGE).group(1)
    return f".lite #n-{tab}," in PAGE or f".lite #n-{tab}{{" in PAGE or f'"{tab}"' in lite_tabs


CHECKS = {"button": has_button, "name_x8": named_in_eight_languages, "help_topic": has_help_topic, "ai_guide": in_the_guide_of_the_ais, "signal_row": has_signal_row, "brief": has_brief, "common_bar": covered_by_the_common_bar, "lite": lite_knows_it, "wall_screen": wall_screen_decided, "demo_rich": demo_declared}
MECHANISMS = {}      # the shared mechanisms still to build, each one true the day it exists (none today)


class Register(unittest.TestCase):
    def test_every_tab_of_the_page_is_registered_and_every_registered_tab_exists(self):
        tabs = re.search(r"const TABS=LITE\?\[[^\]]*\]:\[([^\]]*)\]", PAGE).group(1)
        in_page = tuple(t.strip('"') for t in tabs.split(","))
        self.assertEqual(sorted(in_page), sorted(SURFACES), "a tab was added or removed: register it in SURFACES with what it needs")

    def test_nothing_is_missing_without_an_exception_and_no_exception_is_left_over(self):
        missing, stale = [], []
        for tab in SURFACES:
            for name, check in CHECKS.items():
                ok = check(tab)
                excepted = name in EXCEPTIONS.get(tab, {})
                if not ok and not excepted:
                    missing.append(f"{tab}: {name}")
                if ok and excepted:
                    stale.append(f"{tab}: {name}")
        self.assertEqual(missing, [], "a surface lacks something and no exception names the version that closes it")
        self.assertEqual(stale, [], "an exception is left over: the thing exists now, remove the line")

    def test_the_shared_mechanisms_are_either_built_or_pending_with_a_version(self):
        for name, version in PENDING_FOR_ALL.items():
            self.assertRegex(version, r"^\d+\.\d+\.\d+$", name)
            self.assertFalse(MECHANISMS[name](), f"{name} exists now: remove it from PENDING_FOR_ALL and check it for every surface")
        self.assertEqual(set(MECHANISMS), set(PENDING_FOR_ALL) | {k for k in MECHANISMS if MECHANISMS[k]()})

    def test_every_exception_names_a_version_and_a_known_surface(self):
        for tab, items in EXCEPTIONS.items():
            self.assertIn(tab, SURFACES)
            for name, version in items.items():
                self.assertIn(name, CHECKS)
                self.assertRegex(version, r"^\d+\.\d+\.\d+$")


# ---- the other four kinds: settings, routes, commands of the command line and tools of the MCP server --------------------------------------------------------------------------------------------------------
TAILS = ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho")
EXCEPTIONS_FILE = HERE / "tests" / "fixtures" / "surfaces_exceptions.json"
FED_ITEM = re.compile(r"^/api/repos/\{owner\}/[^/{}]+/health\Z")


def read(path):
    return Path(path).read_text(encoding="utf-8")


def english_docs():
    return "".join(read(f) for f in sorted(glob.glob(str(HERE / "docs" / "*.md"))) if not re.search(r"_(spa|deu|fra|ita|jpn|zho|por)\.md\Z", f))


def documented_patterns(text):
    return re.findall(r"`([a-z0-9_.]+)\.\*`", text)


def settings_items():
    from github_actions_monitor.app import settings_api
    return list(settings_api.META)


def routes_items():
    from github_actions_monitor.security import audited_posts
    contract = json.loads(read(HERE / "docs" / "schemas" / "api_contract.json"))
    frozen = set()
    for row in contract["endpoints"] + contract["fed_endpoints"]:
        path = row["path"].split("?")[0]
        frozen.add("/api/repos/{owner}/{repo}/health" if FED_ITEM.match(path) else path)
    return sorted(set(audited_posts.AUDITED) | set(audited_posts.EXEMPT) | frozen)


def commands_items():
    from github_actions_monitor.cli import monitor_cli
    return list(monitor_cli.COMMANDS)


def tools_items():
    from github_actions_monitor.integrations import mcp_server
    return [t["name"] for t in mcp_server.TOOLS]


def settings_checks():
    from github_actions_monitor.app import settings_api
    docs = [read(HERE / "docs" / f"SETTINGS{tail}.md") for tail in TAILS]
    patterns = [documented_patterns(d) for d in docs]
    skills = {kind: read(HERE / "skills" / kind / "references" / "settings.md") for kind in ("external", "internal")}
    example = json.loads(read(HERE / "assets" / "examples" / "actions_monitor.example.json"))

    def documented(key):
        return all(f"`{key}`" in d or any(key.startswith(p + ".") for p in pats) for d, pats in zip(docs, patterns))

    def in_example(key):
        if key in settings_api.STATUS_KEYS:      # computed and read-only: it is shown, never written in a file
            return True
        node = example
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return True
    return {
        "help_x8": lambda k: all(LOCALES[lang].get(settings_api.help_key(k)) for lang in LANGS),
        "label_x8": lambda k: all(all(LOCALES[lang].get(x) for x in settings_api.label_keys(k)) for lang in LANGS),
        "doc_x8": documented,
        "skill_external": lambda k: f"`{k}`" in skills["external"],
        "skill_internal": lambda k: f"`{k}`" in skills["internal"],
        "example": in_example,
    }


def angle(route):
    """The route as the skills write a path with parts: /api/repos/<owner>/<repo>/health."""
    return route.replace("{owner}", "<owner>").replace("{repo}", "<repo>")


def routes_checks():
    skills = {kind: read(HERE / "skills" / kind / "references" / "api.md") for kind in ("external", "internal")}
    docs = english_docs()
    return {
        "skill_external": lambda r: r in skills["external"] or angle(r) in skills["external"],
        "skill_internal": lambda r: r in skills["internal"] or angle(r) in skills["internal"],
        "doc": lambda r: r in docs or angle(r) in docs,
    }


def commands_checks():
    from github_actions_monitor.cli import monitor_cli
    docs = [read(HERE / "docs" / f"CLI{tail}.md") for tail in TAILS]
    skill = read(HERE / "skills" / "external" / "references" / "cli.md")
    return {
        "handler": lambda c: c in monitor_cli.HANDLERS or c == "update",      # `update` is read before the others and parses its own options
        "help_x8": lambda c: all(re.search(rf"\b{re.escape(c)}\b", LOCALES[lang].get("cli.help_command", "")) for lang in LANGS),
        "doc_x8": lambda c: all(c in d for d in docs),
        "skill_external": lambda c: c in skill,
    }


def tools_checks():
    docs = english_docs() + read(HERE / "assets" / "ai" / "README.md")
    skill = "".join(read(f) for f in glob.glob(str(HERE / "skills" / "external" / "**" / "*.md"), recursive=True))
    return {
        "doc": lambda n: n in docs,
        "skill_external": lambda n: n in skill,
    }


KINDS = {"setting": (settings_items, settings_checks), "route": (routes_items, routes_checks), "command": (commands_items, commands_checks), "tool": (tools_items, tools_checks)}


def what_is_missing():
    """{kind: {check: [items that lack it]}}, only the checks that have something missing."""
    found = {}
    for kind, (items, checks) in KINDS.items():
        names = items()
        for check, test in checks().items():
            lacking = sorted(i for i in names if not test(i))
            if lacking:
                found.setdefault(kind, {})[check] = lacking
    return found


def listed():
    return json.loads(read(EXCEPTIONS_FILE))["exceptions"]


def as_tuple(version):
    return tuple(int(x) for x in version.split("."))


class RegisterOfEverything(unittest.TestCase):
    def test_every_kind_has_its_items(self):
        counts = {kind: len(items()) for kind, (items, _checks) in KINDS.items()}
        self.assertGreater(counts["setting"], 600)
        self.assertGreater(counts["route"], 80)
        self.assertGreater(counts["command"], 15)
        self.assertGreater(counts["tool"], 20)

    def test_what_is_missing_is_exactly_what_the_file_of_exceptions_lists(self):
        missing, written = what_is_missing(), listed()
        new, stale = [], []
        for kind, checks in missing.items():
            for check, items in checks.items():
                owned = set(written.get(kind, {}).get(check, {}).get("items", []))
                new += [f"{kind} {check}: {i}" for i in items if i not in owned]
        for kind, checks in written.items():
            for check, row in checks.items():
                now = set(missing.get(kind, {}).get(check, []))
                stale += [f"{kind} {check}: {i}" for i in row["items"] if i not in now]
        self.assertEqual(new[:20], [], "something has no help, guide, words for the AIs or place in a skill and no exception names the version that closes it (fixtures/surfaces_exceptions.json)")
        self.assertEqual(stale[:20], [], "an exception is left over: the item has it now, remove it from fixtures/surfaces_exceptions.json")

    def test_every_exception_names_a_known_check_and_a_later_version(self):
        from github_actions_monitor.tool_version import TOOL_VERSION
        for kind, checks in listed().items():
            self.assertIn(kind, KINDS)
            known = KINDS[kind][1]()
            for check, row in checks.items():
                self.assertIn(check, known, (kind, check))
                self.assertRegex(row["version"], r"^\d+\.\d+\.\d+$")
                self.assertGreater(as_tuple(row["version"]), as_tuple(TOOL_VERSION), f"{kind} {check} is promised for {row['version']}, which is out: close it or move it")
                self.assertTrue(row["items"] and row["reason"], (kind, check))
                self.assertEqual(row["items"], sorted(set(row["items"])), "keep the list sorted and without repeats")

    def test_the_tab_exceptions_are_for_a_later_version_too(self):
        from github_actions_monitor.tool_version import TOOL_VERSION
        for name, version in PENDING_FOR_ALL.items():
            self.assertGreater(as_tuple(version), as_tuple(TOOL_VERSION), name)
        for tab, items in EXCEPTIONS.items():
            for name, version in items.items():
                self.assertGreater(as_tuple(version), as_tuple(TOOL_VERSION), (tab, name))


if __name__ == "__main__":
    unittest.main()
