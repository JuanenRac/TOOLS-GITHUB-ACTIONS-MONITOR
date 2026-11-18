# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The AIs read everything the monitor shows through one catalogued brief per tab and a master index. Parity: a tab of the page without a brief fails here, a brief for a tab that does not exist fails here, the
index lists every brief, the lite edition says which tabs it does not have, no secret travels in a brief, and the record of who read what is off by default and carries neither signals nor secrets.
Nothing here reaches GitHub."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.data_pipeline import briefs, signals  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
TABS = tuple(t.strip('"') for t in re.search(r"const TABS=LITE\?\[[^\]]*\]:\[([^\]]*)\]", PAGE).group(1).split(","))
LITE = tuple(t.strip('"') for t in re.search(r"const TABS=LITE\?\[([^\]]*)\]", PAGE).group(1).split(","))


def a_state(edition="complete"):
    data = {"updated": None, "figures": {"active": 1, "queued": 0, "fail24": 2, "ok24": 5}, "repos": []}
    return signals.state(data, [{"id": "a3", "title": "Trend", "summary": "up", "level": "warn", "rows": []}], edition, {"age_seconds": 3}, version="9.9.9")


class Parity(unittest.TestCase):
    def test_every_tab_of_the_page_has_a_brief_and_every_brief_a_tab(self):
        self.assertEqual(sorted(briefs.tabs()), sorted(TABS))

    def test_the_lite_tabs_of_the_module_are_the_ones_of_the_page(self):
        self.assertEqual(sorted(briefs.LITE_TABS), sorted(LITE))

    def test_the_index_lists_every_tab_with_a_route_that_answers(self):
        doc = briefs.index(a_state(), "en", i18n.tl)
        self.assertEqual(doc["kind"], "ai-index")
        self.assertEqual([e["tab"] for e in doc["briefs"]], list(briefs.tabs()))
        for entry in doc["briefs"]:
            self.assertEqual(entry["brief"], f"/api/ai/briefs?tab={entry['tab']}")
            self.assertTrue(entry["title"])
            self.assertIsNotNone(briefs.brief(entry["tab"], a_state(), "en", i18n.tl))
        for route in doc["channels"]:
            self.assertTrue(route.startswith("/api/"))

    def test_the_title_comes_in_every_language_of_the_page(self):
        for lang in i18n.LANGS:
            for tab in briefs.tabs():
                self.assertNotEqual(briefs.index(a_state(), lang, i18n.tl)["briefs"][list(briefs.tabs()).index(tab)]["title"], "ui.tab_" + tab, (lang, tab))

    def test_the_sources_are_routes_of_the_monitor(self):
        text = Path(actions_monitor.__file__).read_text(encoding="utf-8")
        for tab, info in briefs.CATALOG.items():
            for route in info["sources"]:
                self.assertIn(route, text + "/api/data", (tab, route))

    def test_the_skills_name_every_brief_route(self):
        for kind in ("external", "internal"):
            api = (HERE / "skills" / kind / "references" / "api.md").read_text(encoding="utf-8")
            self.assertIn("/api/ai/index", api)
            self.assertIn("/api/ai/briefs", api)

    def test_both_routes_exist_in_the_lite_edition_too(self):
        self.assertIn("/api/ai/index", actions_monitor.LITE_SHARED)
        self.assertIn("/api/ai/briefs", actions_monitor.LITE_SHARED)


class Content(unittest.TestCase):
    def test_a_brief_carries_only_the_signals_of_its_tab(self):
        doc = briefs.brief("hist", a_state(), "en", i18n.tl)
        self.assertEqual([s["id"] for s in doc["signals"]], ["now.fail24"])
        self.assertEqual(doc["tab"], "hist")
        self.assertEqual(briefs.brief("strend", a_state(), "en", i18n.tl)["signals"][0]["id"], "sentinel.a3")

    def test_an_unknown_tab_has_no_brief(self):
        self.assertIsNone(briefs.brief("nope", a_state(), "en", i18n.tl))
        document, status = actions_monitor.briefs_get("/api/ai/briefs", "tab=nope")
        self.assertEqual((status, document["error"]), (404, "tab"))

    def test_without_a_tab_every_brief_comes_in_one_document(self):
        document, status = actions_monitor.briefs_get("/api/ai/briefs", "")
        self.assertEqual(status, 200)
        self.assertEqual([b["tab"] for b in document["briefs"]], list(briefs.tabs()))
        self.assertEqual(document["count"], len(briefs.tabs()))
        self.assertEqual(actions_monitor.briefs_get("/api/ai/briefs", "tab=all")[0]["count"], document["count"])

    def test_the_lite_edition_says_which_tabs_do_not_exist_instead_of_looking_empty(self):
        doc = briefs.brief("ssup", a_state("lite"), "en", i18n.tl)
        self.assertFalse(doc["available"])
        self.assertEqual(doc["signals"], [])
        self.assertTrue(doc["note"])
        self.assertTrue(briefs.brief("now", a_state("lite"), "en", i18n.tl)["available"])
        self.assertFalse([e for e in briefs.index(a_state("lite"), "en", i18n.tl)["briefs"] if e["tab"] == "sent"][0]["available"])

    def test_a_secret_in_a_signal_does_not_leave_through_the_route(self):
        secret = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
        state = a_state()
        state["signals"].append({"id": "now.runs", "panel": "now", "level": "info", "summary": "token " + secret, "rows": [], "transient": False})
        original = actions_monitor.ai_state
        actions_monitor.ai_state = lambda lang=None, *a, **k: state
        self.addCleanup(lambda: setattr(actions_monitor, "ai_state", original))
        document, status = actions_monitor.briefs_get("/api/ai/briefs", "tab=now")
        self.assertEqual(status, 200)
        self.assertNotIn(secret, json.dumps(document))
        self.assertNotIn(secret, json.dumps(actions_monitor.briefs_get("/api/ai/index", "")[0]))


class AccessRecord(unittest.TestCase):
    def test_the_record_is_off_by_default_and_never_holds_signals(self):
        self.assertIs(actions_monitor.DEFAULTS["ai_alerts"]["briefs"]["access_log"], False)
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(briefs.note_access(folder, "now", "agent/1.0 ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8", now=100))
            lines = briefs.read_access(folder)
            self.assertEqual([(x["tab"], x["at"]) for x in lines], [("now", 100)])
            self.assertNotIn("ghp_A1b2", json.dumps(lines))
            self.assertEqual(set(lines[0]), {"at", "tab", "client"})

    def test_the_record_stays_small(self):
        with tempfile.TemporaryDirectory() as folder:
            for i in range(9000):
                briefs.note_access(folder, "now", "client-" + "x" * 40, now=i)
            size = (Path(folder) / briefs.ACCESS_FILE).stat().st_size
            self.assertLess(size, briefs.ACCESS_MAX_BYTES + 200)
            self.assertEqual(briefs.read_access(folder, 1)[0]["at"], 8999)

    def test_an_unreadable_record_is_an_empty_list(self):
        self.assertEqual(briefs.read_access("/nonexistent/folder/for/briefs"), [])


if __name__ == "__main__":
    unittest.main()
