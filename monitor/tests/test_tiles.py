# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The figures of the header are tiles: structure of the markup, accessibility, texts in the eight languages, narrow screens, last known values and the countdown."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import i18n  # noqa: E402

PAGE = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
HEADER = PAGE[PAGE.index("<header>"):PAGE.index("</header>")]
FIRST_LINE = ("k-active", "k-queued", "k-fail", "k-ok", "k-issues", "k-min", "k-red", "k-sign")
SECOND_LINE = ("tv-repos", "tv-hot", "tv-mode", "tv-etag", "tv-quota", "tv-conn", "tv-upd", "tv-load")


class Tiles(unittest.TestCase):
    def test_every_figure_is_a_tile_with_icon_label_and_tooltip(self):
        tiles = re.findall(r'<div class="tile [^"]*"[^>]*>.*?</div>', HEADER, re.S)
        self.assertGreaterEqual(len(tiles), 15)
        for ident in FIRST_LINE + SECOND_LINE:
            self.assertIn(f'id="{ident}"', HEADER, ident)
        for tile in tiles:
            self.assertIn('<svg class="ico" aria-hidden="true" focusable="false">', tile)
            self.assertIn("<small", tile)
            self.assertIn("data-i18n-title=", tile)
            self.assertIn("data-i18n-aria=", tile)
            self.assertRegex(tile, r'role="(button|group)"')

    def test_both_lines_are_groups_and_the_clickable_tiles_can_be_reached_with_the_keyboard(self):
        for line in ('id="tiles1" role="group"', 'id="tiles2" role="group"'):
            self.assertIn(line, HEADER)
        for tile in re.findall(r'<div class="tile[^"]*"[^>]*>', HEADER):
            if 'role="button"' in tile:
                self.assertIn('tabindex="0"', tile)
        self.assertIn("e.key===\"Enter\"||e.key===\" \"", PAGE)
        for go in ("now", "hist", "sent", "charts", "repos", "cfg:cache", "cfg:general", "cfg:polling"):
            self.assertIn(f'data-go="{go}"', HEADER, go)
        for ident in ("kp-fail", "kp-red", "kp-sign"):
            self.assertIn(f'id="{ident}"', HEADER)      # these three keep their own handlers (the list of reds, the signing queue...)

    def test_the_tiles_have_skeletons_states_and_a_narrow_layout(self):
        for needle in (".tile.skel", ".tile.stale", ".tile.ok", ".tile.warn", ".tile.bad", ".tile.run", "tilepulse", "@media (max-width:640px)", "flex-wrap:wrap", "prefers-reduced-motion"):
            self.assertIn(needle, PAGE, needle)
        self.assertNotRegex(HEADER, r"overflow-x\s*:\s*scroll")
        self.assertEqual(HEADER.count('class="tile skel'), len(re.findall(r'<div class="tile[ "]', HEADER)) - 1)      # all start as skeletons, the loading tile is hidden

    def test_the_last_known_values_are_kept_in_a_guarded_storage_and_shown_at_once(self):
        self.assertIn('const TILE_KEY="am-tiles"', PAGE)
        self.assertIn("JSON.parse(store.get(TILE_KEY)", PAGE)
        self.assertIn("tilesRestore();", PAGE)
        self.assertRegex(PAGE, r"const store=\{get\(k\)\{try\{")
        self.assertIn("function tileSave()", PAGE)

    def test_the_quota_has_a_bar_and_a_live_countdown_and_the_loading_a_progress_bar(self):
        self.assertIn('id="tq-fill"', HEADER)
        self.assertIn('id="tl-fill"', HEADER)
        self.assertIn("setInterval(quotaCount", PAGE)
        self.assertIn("d.rate.remaining<low*2?\"warn\"", PAGE)

    def test_the_rest_of_the_state_keeps_a_text_for_screen_readers(self):
        for ident in ('id="stamp"', 'id="mode"', 'id="rate"'):
            self.assertIn(ident, HEADER)
        self.assertIn('class="vh" role="status"', HEADER)

    def test_every_icon_of_the_tiles_is_in_the_sprite(self):
        defined = set(re.findall(r'<symbol id="(i-[a-z0-9]+)"', PAGE))
        for icon in re.findall(r'<use href="#(i-[a-z0-9]+)"', HEADER):
            self.assertIn(icon, defined, icon)

    def test_every_text_of_the_tiles_exists_in_the_eight_languages(self):
        keys = set(re.findall(r'data-i18n(?:-title|-aria)?="(ui\.[a-z0-9_]+)"', HEADER))
        keys |= {"ui.t_renews", "ui.t_online", "ui.t_offline", "ui.t_offline_since", "ui.t_took", "ui.t_stale"}
        self.assertGreaterEqual(len(keys), 25)
        for lang in i18n.LANGS:
            cat = i18n.catalogue(lang)
            embedded = i18n.ui_catalogues()[lang]
            for key in keys:
                self.assertIn(key, cat, f"{lang} {key}")
                self.assertTrue(cat[key].strip())
                self.assertIn(key, embedded, f"{lang} {key} is not shipped to the page")


if __name__ == "__main__":
    unittest.main()
