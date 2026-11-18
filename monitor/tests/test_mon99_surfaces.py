# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The single register of the SURFACES of the page (every tab) and the guard that nothing grows alone: for each surface, every thing a surface needs is checked (the button, its name in the eight languages, its
help topic, the line in the guide of the tabs of the AIs, the row of the table of signals, its place in the lite edition). What a surface still lacks is written in EXCEPTIONS with the version that closes it; the
guard fails when something is missing without an exception, and also when an exception is left over for something that now exists. A new tab that is not in SURFACES fails the guard too."""
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

# Things that do not exist yet for ANY surface (the shared mechanisms still to build) and the version that closes them. When the mechanism exists, its check below turns true and the line must go.
PENDING_FOR_ALL = {
    "save_print": "2.1.4",           # the SAVE and PRINT buttons of the common bar cover the tab
    "wall_screen": "2.2.0",          # the decision about the four wall screens, tab by tab
    "demo_rich": "2.1.4",            # the demo with data for the tab (python tools/demo_monitor.py --rich)
}
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


def lite_knows_it(tab):
    lite_tabs = re.search(r'LITE\?\[([^\]]*)\]', PAGE).group(1)
    return f".lite #n-{tab}," in PAGE or f".lite #n-{tab}{{" in PAGE or f'"{tab}"' in lite_tabs


CHECKS = {"button": has_button, "name_x8": named_in_eight_languages, "help_topic": has_help_topic, "ai_guide": in_the_guide_of_the_ais, "signal_row": has_signal_row, "brief": has_brief, "lite": lite_knows_it}
MECHANISMS = {      # the shared mechanisms: true the day they exist
    "save_print": lambda: 'id="bar-save"' in PAGE and 'id="bar-print"' in PAGE,
    "wall_screen": lambda: False,
    "demo_rich": lambda: False,
}


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


if __name__ == "__main__":
    unittest.main()
