# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The menu on the left: every tab is in exactly one group with a title (role=group, labelled by its title, foldable and remembered), Team health, Fleet and Scheduled reports are three entries,
and the Sentinel tab is a summary plus one entry per sentinel that is there only while that sentinel is on (checked with 3, 1 and 0 sentinels on)."""
import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


def tabs():
    return json.loads(re.search(r"const TABS=LITE\?(\[[^\]]*\]):(\[[^\]]*\])", PAGE).group(2))


class Groups(unittest.TestCase):
    def groups(self):
        out = {}
        for match in re.finditer(r'<div class="nav-group" data-group="([a-z]+)" role="group" aria-labelledby="ng-([a-z]+)">(.*?)</div></div>', PAGE, re.S):
            self.assertEqual(match.group(1), match.group(2))
            out[match.group(1)] = re.findall(r'data-tab="([a-z]+)"', match.group(3))
        return out

    def test_every_tab_is_in_one_group_and_every_group_has_a_title(self):
        groups = self.groups()
        self.assertEqual(list(groups), ["watch", "sentinels", "team", "learn", "system"])
        flat = [t for tabs_ in groups.values() for t in tabs_]
        self.assertEqual(sorted(flat), sorted(tabs()))
        self.assertEqual(len(flat), len(set(flat)), "no tab twice")
        self.assertEqual(flat, tabs(), "the keyboard walks the tabs in the order of the menu")
        for group in groups:
            self.assertIn(f'<strong id="ng-{group}" data-i18n="ui.nav_g_{group}">', PAGE)
        self.assertIn("aria-expanded", PAGE)
        self.assertIn('store.set("am-nav-closed"', PAGE, "the folded groups are remembered")

    def test_the_group_titles_and_tab_names_exist_in_the_eight_languages(self):
        for lang in LANGS:
            keys = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for group in self.groups():
                self.assertTrue(keys.get(f"ui.nav_g_{group}", "").strip(), (lang, group))
            for tab in tabs():
                self.assertTrue(keys.get(f"ui.tab_{tab}", "").strip(), (lang, tab))
            for key in ("ui.sentinel_off", "ui.sentinel_off_go"):
                self.assertTrue(keys[key].strip(), (lang, key))

    def test_team_is_three_entries_with_their_content_once(self):
        for ident, panel in (("team-rows", "t-team"), ("fleet-rows", "t-fleet"), ("rs-list", "t-trep"), ("s-details", "t-sci"), ("s-details-collab", "t-scol"), ("s-details-sec", "t-ssec"), ("s-parte", "t-sent")):
            self.assertEqual(PAGE.count(f'id="{ident}"'), 1, ident)
            start = PAGE.index(f'id="{panel}"')
            end = PAGE.index('<div class="tab', start + 10) if '<div class="tab' in PAGE[start + 10:] else len(PAGE)
            self.assertIn(f'id="{ident}"', PAGE[start:end], (ident, panel))

    def test_the_old_addresses_and_views_of_the_team_and_the_sentinel_still_work(self):
        for needle in ('"team-health":"team"', '"team-reports":"trep"', 'sentinel:"sent"', '"sentinel-ci":"sci"', '"sentinel-collab":"scol"', '"sentinel-security":"ssec"', 'repo:"team"'):
            self.assertIn(needle, PAGE, needle)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class SentinelMenus(unittest.TestCase):
    def run_case(self, state):
        start = PAGE.index("function sentIsOn(")
        end = PAGE.index("function sentOff(")
        script = """
const LITE=false, QS=new URLSearchParams(""), I18N={screens:{}}, TABS=%s;
const els={};const mk=id=>els[id]||(els[id]={id,hidden:true});
const $=id=>mk("x"+id);
global.document={documentElement:{dataset:{}},querySelector:()=>mk("group")};
let SENT=%s, COLLAB=%s, SECUR=%s;
%s
sentMenus();
console.log(JSON.stringify(["sent","sci","scol","ssec"].filter(k=>!els["xn-"+k].hidden).concat(els.group.hidden?["GROUP-HIDDEN"]:[])));
""" % (json.dumps(tabs()), *[json.dumps(v) for v in state], PAGE[start:end].replace("$(\"n-\"+k)", "$(\"n-\"+k)"))
        done = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60, **({"creationflags": 0x08000000} if os.name == "nt" else {}))
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout.strip())

    def test_the_menus_present_are_exactly_those_of_the_sentinels_that_are_on(self):
        on, off = {"enabled": True}, {"enabled": False}
        self.assertEqual(self.run_case([on, on, on]), ["sent", "sci", "scol", "ssec"])
        self.assertEqual(self.run_case([off, on, off]), ["sent", "scol"])
        self.assertEqual(self.run_case([off, None, on]), ["sent", "ssec"])
        self.assertEqual(self.run_case([on, off, off]), ["sent", "sci"])
        self.assertEqual(self.run_case([off, off, off]), ["GROUP-HIDDEN"])
        self.assertEqual(self.run_case([None, None, None]), ["GROUP-HIDDEN"])

    def test_an_off_sentinel_says_so_and_points_to_its_switch(self):
        for key in ("sentinel.enabled", "sentinels.collab.enabled", "sentinels.security.enabled"):
            self.assertIn(f'"{key}"', PAGE)
        self.assertIn("data-sent-switch", PAGE)
        self.assertIn("ui.sentinel_off_go", PAGE)

    def test_the_badge_of_each_menu_comes_from_its_own_sentinel(self):
        self.assertIn('$("d-sci")', PAGE)
        body = PAGE[PAGE.index("function renderSentOthers("):]
        body = body[:body.index("sentMenus()")]
        self.assertIn("COLLAB.alerts", body)
        self.assertIn("SECUR.alerts", body)
        self.assertNotIn("SENT.", body)


if __name__ == "__main__":
    unittest.main()
