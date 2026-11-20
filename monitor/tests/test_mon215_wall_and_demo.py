# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Two shared mechanisms that every tab of the page answers to. (1) The decision of the wall screens, tab by tab: `screens.TAB_DECISIONS` says, for each tab, on which wall screen it is shown (and in which field of
the answer of /api/screens/data) or why it is not; the guide of the screens (eight languages) lists the same table. (2) The demo with data for each tab: `tools/demo_monitor.py --rich` fills every tab that the plain demo
leaves empty, and `TAB_DEMO` names, for every tab, what it puts there; the test starts the demo and reads each of those tabs through its own endpoint."""
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(HERE / "src"))

from github_actions_monitor.app import screens  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
TABS = tuple(t.strip('"') for t in re.search(r"const TABS=LITE\?\[[^\]]*\]:\[([^\]]*)\]", PAGE).group(1).split(","))
TAILS = ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho")
DEMO_FILE = TOOLS / "demo_monitor.py"


def demo_table():
    """TAB_DEMO of the demo, read from its source (importing the demo would load the whole monitor for nothing)."""
    import ast
    tree = ast.parse(DEMO_FILE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "TAB_DEMO" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("TAB_DEMO is not in the demo")


class TheWallScreensDecideTabByTab(unittest.TestCase):
    def test_every_tab_has_a_decision_and_nothing_else_is_there(self):
        self.assertEqual(sorted(screens.TAB_DECISIONS), sorted(TABS))
        self.assertEqual(sorted(screens.tab_decisions()), sorted(TABS))

    def test_a_decision_names_a_real_screen_and_a_real_field_or_a_known_reason(self):
        data = {kind: screens.build(kind, {}, {}, {}, None, screens.settings({})) for kind in screens.KINDS}
        for tab, decision in screens.tab_decisions().items():
            if decision["screen"]:
                self.assertIn(decision["screen"], screens.KINDS, tab)
                self.assertIn(decision["field"], data[decision["screen"]], f"{tab}: the field is not in the answer of the screen")
                self.assertEqual(decision["reason"], "", tab)
            else:
                self.assertIn(decision["reason"], screens.NO_SCREEN_REASONS, tab)
                self.assertEqual(decision["field"], "", tab)

    def test_every_screen_and_every_reason_is_used(self):
        used = screens.tab_decisions().values()
        self.assertEqual({d["screen"] for d in used if d["screen"]}, set(screens.KINDS))
        self.assertEqual({d["reason"] for d in used if d["reason"]}, set(screens.NO_SCREEN_REASONS))

    def test_a_tab_that_names_people_is_never_on_a_wall_screen(self):
        self.assertIsNone(screens.TAB_DECISIONS["team"]["screen"])
        self.assertEqual(screens.TAB_DECISIONS["team"]["reason"], "people")

    def test_the_guide_of_the_screens_lists_the_decision_of_every_tab_in_the_eight_languages(self):
        decisions = screens.tab_decisions()
        for tail in TAILS:
            text = (HERE / "docs" / f"SCREENS{tail}.md").read_text(encoding="utf-8")
            for tab, decision in decisions.items():
                row = re.search(rf"^\| `{tab}` \|(.*)\|\s*$", text, re.M)
                self.assertIsNotNone(row, f"SCREENS{tail}.md has no row for the tab {tab}")
                self.assertIn(f"`/screen/{decision['screen']}`" if decision["screen"] else f"`{decision['reason']}`", row.group(1), (tail, tab))


@unittest.skipUnless(DEMO_FILE.is_file(), "needs the repository root (tools/demo_monitor.py), not part of the installed zip")
class TheDemoHasDataForEveryTab(unittest.TestCase):
    def test_every_tab_says_what_the_demo_puts_in_it(self):
        table = demo_table()
        self.assertEqual(sorted(table), sorted(TABS))
        for tab, (mode, what) in table.items():
            self.assertIn(mode, ("plain", "rich"), tab)
            self.assertTrue(what.strip(), tab)
        self.assertGreaterEqual(sum(1 for mode, _ in table.values() if mode == "rich"), 8)


def _port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@unittest.skipUnless(DEMO_FILE.is_file(), "needs the repository root (tools/demo_monitor.py), not part of the installed zip")
class TheRichDemoFillsTheTabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _port()
        cls.demo = subprocess.Popen([sys.executable, "-I", str(DEMO_FILE), str(cls.port), "--rich"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, "PYTHONUTF8": "1"})
        for _ in range(120):
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            cls.demo.terminate()
            raise RuntimeError("the demo monitor did not start")

    @classmethod
    def tearDownClass(cls):
        cls.demo.terminate()
        cls.demo.wait(10)

    def get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=20) as answer:
            return json.loads(answer.read().decode("utf-8"))

    def test_the_sentinel_tabs_of_security_delivery_and_supply_chain_have_findings(self):
        for name, prefix in (("security", "security."), ("delivery", "release."), ("supply", "actions.supply.")):
            alerts = self.get(f"/api/sentinel/{name}")["data"]["alerts"]
            self.assertGreaterEqual(len([a for a in alerts if a["code"].startswith(prefix)]), 3, name)

    def test_the_trend_tab_has_fourteen_days(self):
        trend = self.get("/api/sentinel")["data"]["a3"]["trend"]
        self.assertEqual(len(trend["ci_green_pct"]["dates"]), 14)

    def test_the_yesterday_against_today_tab_has_a_base_day_with_changes(self):
        answer = self.get("/api/sentinel/historial")["data"]
        self.assertTrue(answer["available"])
        self.assertTrue(answer["red"]["appeared"] and answer["red"]["disappeared"])

    def test_the_reports_tab_has_the_four_reports_on_and_filled(self):
        answer = self.get("/api/reports")
        for kind, key in (("workflow_hygiene", "repos"), ("queue", "groups"), ("release_view", "repos"), ("supply_chain", "repos")):
            self.assertTrue(answer[kind]["enabled"], kind)
            self.assertTrue(answer[kind][key], kind)

    def test_the_scheduled_reports_tab_has_a_report(self):
        self.assertTrue(self.get("/api/report-files")["reports"])

    def test_the_lessons_tab_has_the_book_of_failures(self):
        self.assertGreaterEqual(len(self.get("/api/ai/lessons")["categories"]), 2)


if __name__ == "__main__":
    unittest.main()
