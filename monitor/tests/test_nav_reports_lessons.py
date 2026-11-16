# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Alerts, Reports and Lessons are three entries of the menu on the left, each with its own panel and its own address (#reports, #lessons). Nothing is lost or repeated, the old addresses still
open the right panel, every entry has its badge and its words in the eight languages, and Lite does not show them."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


class Structure(unittest.TestCase):
    def tabs(self):
        found = re.search(r"const TABS=LITE\?(\[[^\]]*\]):(\[[^\]]*\])", PAGE)
        return json.loads(found.group(1)), json.loads(found.group(2))

    def test_every_tab_has_its_button_and_its_panel_and_no_panel_is_left_over(self):
        lite, complete = self.tabs()
        self.assertEqual(complete[:4], ["now", "al", "rep", "les"])
        buttons = re.findall(r'<button role="tab" id="n-([a-z]+)" data-tab="([a-z]+)"', PAGE)
        panels = re.findall(r'<div class="tab(?: on)?" id="t-([a-z]+)" role="tabpanel" aria-labelledby="n-([a-z]+)"', PAGE)
        self.assertEqual(sorted(t for t, _ in buttons), sorted(complete))
        self.assertTrue(all(i == t for i, t in buttons))
        self.assertEqual(sorted(p for p, _ in panels), sorted(complete))
        self.assertTrue(all(p == b for p, b in panels), "each panel is labelled by the button of the same tab")
        for tab in ("rep", "les"):
            self.assertNotIn(tab, lite)
            self.assertIn(f".lite #n-{tab},.lite #t-{tab}", PAGE)
            self.assertIn(f'id="d-{tab}"', PAGE, "each entry has its badge")

    def test_the_sections_moved_without_being_lost_or_repeated(self):
        for ident, panel in (("rep-box", "t-rep"), ("rep-list", "t-rep"), ("les-box", "t-les"), ("les-list", "t-les"), ("al-list", "t-al")):
            self.assertEqual(PAGE.count(f'id="{ident}"'), 1, ident)
            start = PAGE.index(f'id="{panel}"')
            end = PAGE.index('<div class="tab" id=', start + 10)
            self.assertIn(f'id="{ident}"', PAGE[start:end], (ident, panel))
        self.assertNotIn('id="rep-box" hidden', PAGE, "the panel is always there: it says when no report is on")

    def test_the_badges_are_written_by_the_code_that_draws_each_panel(self):
        self.assertIn('$("d-rep")', PAGE)
        self.assertIn('$("d-les")', PAGE)
        self.assertIn('$("d-al")', PAGE)
        self.assertRegex(PAGE, r"d-al.*level===\"error\"")

    def test_each_address_and_the_old_ones(self):
        self.assertIn('TABHASH={rep:"reports",les:"lessons"}', PAGE)
        self.assertIn('reports:"rep",lessons:"les"', PAGE, "?view=reports and ?view=lessons")
        self.assertIn('window.addEventListener("hashchange"', PAGE)

    def test_the_help_button_of_each_entry_opens_its_own_topic(self):
        from github_actions_monitor.ui import helpdocs
        index = json.loads((HERE / "docs" / "help_index.json").read_text(encoding="utf-8"))
        topics = {t.get("id") for t in index["topics"] if isinstance(t, dict)}
        self.assertEqual((helpdocs.TAB_TOPICS["rep"], helpdocs.TAB_TOPICS["les"]), ("extras", "lessons"))
        for tab in ("al", "rep", "les"):
            self.assertIn(helpdocs.TAB_TOPICS[tab], topics, tab)
        self.assertEqual((helpdocs.tab_topic("rep"), helpdocs.tab_topic("les")), ("extras", "lessons"))
        self.assertEqual(len({helpdocs.TAB_TOPICS[t] for t in ("al", "rep", "les")}), 3, "three entries, three different topics")
        text = (HERE / "docs" / "EXTRAS.md").read_text(encoding="utf-8") + (HERE / "docs" / "LESSONS.md").read_text(encoding="utf-8")
        self.assertIn("`#reports`", text)
        self.assertIn("`#lessons`", text)

    def test_the_words_exist_in_the_eight_languages(self):
        for lang in LANGS:
            keys = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ui.tab_al", "ui.tab_rep", "ui.tab_les", "ui.rep_title", "ui.les_title", "ui.rep_all_off"):
                self.assertTrue(str(keys.get(key, "")).strip(), (lang, key))
            self.assertNotEqual(keys["ui.tab_rep"], keys["ui.tab_les"], lang)
            for n in (1, 2, 3):
                self.assertIn("rep, les", keys[f"cfg.h.ui.screen{n}_tabs"], (lang, n))


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class OldAddressesRedirect(unittest.TestCase):
    def test_tab_of(self):
        source = PAGE[PAGE.index("const TABHASH="):]
        source = source[:source.index("function tabOf") + source[source.index("function tabOf"):].index("\n")]
        script = source + """
const cases = {"": "", "#alerts": "al", "al": "al", "#reports": "rep", "#lessons": "les", "#alerts/reports": "rep", "#al/lessons": "les", "#alerts/lessons/": "les", "#alerts/something": "al",
               "#rep-box": "rep", "#les-box": "les", "#sent": "sent", "#Reports": "rep"};
const bad = Object.entries(cases).filter(([k, v]) => tabOf(k) !== v).map(([k, v]) => k + " -> " + tabOf(k) + " (wanted " + v + ")");
console.log(JSON.stringify(bad));
"""
        done = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60, creationflags=0x08000000)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout.strip()), [])


if __name__ == "__main__":
    unittest.main()
