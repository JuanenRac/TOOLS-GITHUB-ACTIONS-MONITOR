# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.7.2: the header in an order that reads and a grid that follows the width, the quick controls fixed in the top right corner, About in the side panel, no notice of a new version in
the header, and the proof that the tests leave nothing next to the code (which is what had put the neutral template in place of the settings of a person)."""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import i18n  # noqa: E402

PAGE = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
HEADER = PAGE[PAGE.index("<header>"):PAGE.index("</header>") + 9]
SIDE = PAGE.split('<aside class="sidebar"', 1)[1].split("</aside>", 1)[0]
FIRST_ROW = ("kt-active", "kt-queued", "kp-fail", "kt-ok", "kt-min", "kt-issues", "kp-red", "kp-sign")
SECOND_ROW = ("kt-repos", "kt-hot", "kt-mode", "kt-etag", "kt-quota", "kt-conn", "kt-upd", "kt-loading")


def ids_in(block):
    return [i for i in re.findall(r'<div class="tile[^"]*" id="([^"]+)"', block) if i != "tiles1"]


class HeaderOrder(unittest.TestCase):
    def test_the_first_row_reads_from_what_is_going_on_to_what_needs_attention(self):
        row = HEADER.split('id="tiles1"', 1)[1].split('id="tiles2"', 1)[0]
        self.assertEqual(tuple(ids_in(row)), FIRST_ROW)
        activity, attention = FIRST_ROW[:5], FIRST_ROW[5:]
        self.assertEqual(activity[0], "kt-active")                    # running first, then queued, then the failures and the successes of the day, then the cost
        self.assertEqual(attention, ("kt-issues", "kp-red", "kp-sign"))

    def test_the_second_row_keeps_the_machinery_and_both_rows_are_eight_tiles(self):
        row = HEADER.split('id="tiles2"', 1)[1]
        self.assertEqual(tuple(ids_in(row)), SECOND_ROW)
        self.assertEqual(len(FIRST_ROW), len(SECOND_ROW))

    def test_each_row_is_a_grid_of_eight_four_or_two_columns_by_the_width_of_its_own_block(self):
        self.assertIn("container-type:inline-size", PAGE)
        self.assertRegex(PAGE, r"header \.tiles\{display:grid;grid-template-columns:repeat\(2,minmax\(0,1fr\)\)")
        self.assertIn("@container (min-width:500px){header .tiles{grid-template-columns:repeat(4,minmax(0,1fr))}}", PAGE)
        self.assertIn("@container (min-width:1080px){header .tiles{grid-template-columns:repeat(8,minmax(0,1fr))}}", PAGE)

    def test_a_tile_never_forces_a_width(self):
        self.assertIn("header .tile{min-width:0;", PAGE)
        self.assertIn("header .tile.wide{min-width:0;grid-column:span 2}", PAGE)

    def test_the_header_has_one_grid_with_the_figures_and_the_corner(self):
        self.assertEqual(HEADER.count('class="hgrid"'), 1)
        self.assertLess(HEADER.index('class="hmain"'), HEADER.index('class="hcorner"'))
        self.assertEqual(HEADER.count("<header"), 1)


class Corner(unittest.TestCase):
    def corner(self):
        return HEADER.split('class="hcorner"', 1)[1].split('class="vh"', 1)[0]

    def test_the_hot_only_button_and_the_speed_list_live_in_the_corner_and_nowhere_else(self):
        corner = self.corner()
        for ident in ('id="hotonly"', 'id="mode-sel"', 'id="mode-left"'):
            self.assertIn(ident, corner)
            self.assertEqual(PAGE.count(ident), 1, ident)
        self.assertLess(corner.index('id="hotonly"'), corner.index('id="mode-sel"'))

    def test_the_health_chips_of_the_ecosystems_and_the_badges_are_in_the_corner_too(self):
        corner = self.corner()
        for ident in ('id="k-ready"', 'id="k-budget"', 'id="k-a10"'):
            self.assertIn(ident, corner)

    def test_the_corner_stays_at_the_top_right_and_wraps_inside_its_own_width(self):
        self.assertIn(".hcorner{position:sticky;top:0;", PAGE)
        self.assertIn("grid-template-columns:minmax(0,1fr) var(--corner-w,236px)", PAGE)
        self.assertIn(".hcorner .hbadges{display:flex;flex-wrap:wrap;", PAGE)
        self.assertIn(".rdy-chip{max-width:100%;white-space:nowrap}", PAGE)

    def test_on_a_narrow_window_it_goes_above_the_figures_and_the_page_of_all_accounts_hides_it(self):
        self.assertRegex(PAGE, r"@media \(max-width:1100px\)\{\.hgrid\{grid-template-columns:minmax\(0,1fr\)\}\.hcorner\{position:static;")
        self.assertIn(".allmode header .tiles,.allmode #g-list,.allmode .hcorner{display:none!important}", PAGE)

    def test_it_has_a_name_for_screen_readers_in_the_eight_languages(self):
        self.assertIn('data-i18n-aria="ui.corner_aria"', HEADER)
        for lang in i18n.LANGS:
            self.assertTrue(i18n.catalogue(lang).get("ui.corner_aria", "").strip(), lang)


class PanelAndNotice(unittest.TestCase):
    def test_settings_help_and_about_are_not_in_the_header_any_more(self):
        for ident in ("cfg-open", "help-open", "about-open", "upd-badge"):
            self.assertNotIn(f'id="{ident}"', HEADER, ident)
        self.assertNotIn('$("cfg-open")', PAGE)
        self.assertNotIn('$("help-open")', PAGE)

    def test_about_joins_the_help_at_the_foot_of_the_side_panel(self):
        foot = SIDE.split('class="side-foot"', 1)[1]
        self.assertIn('id="help-tab"', foot)
        self.assertIn('id="about-open"', foot)
        self.assertLess(foot.index('id="help-tab"'), foot.index('id="about-open"'))
        self.assertIn('data-i18n="ui.about_title"', foot)
        self.assertIn('$("about-open").addEventListener("click",openAbout)', PAGE)
        self.assertEqual(PAGE.count('id="about-open"'), 1)

    def test_settings_is_one_of_the_sections_of_the_panel(self):
        self.assertIn('id="n-cfg" data-tab="cfg"', SIDE)

    def test_the_notice_of_a_new_version_is_gone_from_the_header_and_its_code_and_style_with_it(self):
        self.assertNotIn("upd-badge", PAGE)
        self.assertNotIn("paintBadge", PAGE)
        self.assertNotRegex(PAGE, r"(?m)^\.upd[{:]")

    def test_the_about_panel_and_the_console_still_say_it(self):
        self.assertIn("function updLine(", PAGE)
        text = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn("updatecheck.notice(", text)

    def test_the_guide_of_the_settings_says_where_the_gear_is_in_each_language(self):
        for suffix in ("", "_spa", "_deu", "_fra", "_ita", "_por", "_jpn", "_zho"):
            text = (HERE / "docs" / f"SETTINGS{suffix}.md").read_text(encoding="utf-8")
            self.assertNotRegex(text, r"header or in the tab bar|cabecera o en la barra de pesta|Kopfzeile oder in der Reiterleiste|l'en-tête ou dans la barre d'onglets|intestazione o nella barra delle schede|cabeçalho ou na barra de separadores|ヘッダーまたはタブバー|标题栏或选项卡栏", suffix)
            self.assertIn("actions_monitor.json", text, suffix)


class NothingNextToTheCode(unittest.TestCase):
    def test_the_guard_removes_what_a_test_created_and_keeps_what_was_there(self):
        folder = HERE
        watched = _testenv.WATCHED
        existing = [n for n in watched if (folder / n).exists()]
        case = unittest.TestCase()
        remove = _testenv.guard(case)
        created = [n for n in watched if n not in existing][:2]
        for name in created:
            (folder / name).write_text("{}", encoding="utf-8")
        remove()
        for name in created:
            self.assertFalse((folder / name).exists(), name)
        for name in existing:
            self.assertTrue((folder / name).exists(), name)

    def test_a_lite_process_leaves_no_file_next_to_the_code_when_the_test_that_started_it_is_over(self):
        before = {n for n in _testenv.WATCHED if (HERE / n).exists()}
        case = unittest.TestCase()
        remove = _testenv.guard(case)
        script = "import sys; sys.path.insert(0, %r); sys.argv = ['x', '--lite']; import actions_monitor as am; am.enable_lite(); am.load_config(); print('ran')" % str(HERE)
        done = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.stdout.strip(), "ran", done.stderr)
        remove()
        self.assertEqual({n for n in _testenv.WATCHED if (HERE / n).exists()}, before)

    def test_the_modules_that_used_to_leave_files_register_the_guard(self):
        for name, needle in (("test_164.py", "_testenv.guard(self)"), ("test_164.py", "_testenv.guard(unittest.TestCase())"), ("test_170.py", "_testenv.guard(self)")):
            self.assertIn(needle, (HERE / "tests" / name).read_text(encoding="utf-8"), name)


class TheCatalogueOfAPerson(unittest.TestCase):
    """The settings of a person name their own catalogue; the neutral template does not. A monitor started with the template puts every repository in one group (the cause of the corner that read
    'Everything else 54'). These tests pin what the classification does with each."""

    def classify(self, config, repos):
        import os
        from unittest import mock
        import toolconfig
        env = {k: v for k, v in os.environ.items() if k != "MONITOR_ECOSYSTEMS_FILE"}      # _testenv pins a catalogue for the tests: here the one of the configuration decides
        with mock.patch.dict(os.environ, env, clear=True):
            toolconfig.forget()
            try:
                return {r: toolconfig.ecosystem_of(r, config) for r in repos}
            finally:
                toolconfig.forget()

    def test_with_the_own_catalogue_each_repository_goes_to_its_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ecosystems.json"
            path.write_text('{"ecosystems": {"armor": {"label": "A", "prefixes": ["ARMOR-"]}, "urtc": {"label": "U", "prefixes": ["URTC"]}}}', encoding="utf-8")
            got = self.classify({"ecosystems_file": str(path), "ecosystems": "all"}, ["ARMOR-SERVER", "URTC-WEB", "OTHER"])
        self.assertEqual((got["ARMOR-SERVER"], got["URTC-WEB"]), ("armor", "urtc"))
        self.assertNotIn(got["OTHER"], ("armor", "urtc"))

    def test_with_the_neutral_template_everything_falls_into_the_last_group(self):
        template = HERE / "ecosystems.example.json"
        got = self.classify({"ecosystems_file": str(template), "ecosystems": "all"}, ["ARMOR-SERVER", "URTC-WEB", "OTHER"])
        self.assertEqual(len(set(got.values())), 1, got)

    def test_the_settings_of_a_first_start_are_the_template_and_the_package_never_carries_the_catalogue_of_a_person(self):
        import make_release as mr
        for name in ("ecosystems.json", "targets.json", "profiles.json", "actions_monitor.json"):
            self.assertNotIn(name, mr.DATA_JSON)
        self.assertIn("ecosystems.example.json", mr.DATA_JSON)


if __name__ == "__main__":
    unittest.main()
