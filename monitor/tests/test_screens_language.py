# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The language of a wall screen. ?lang= wins; then the language the person chose on the main page of the same browser (the key `am-lang`); then the one of the monitor. Light checks: the page reads the
same key as the main page and reloads once with ?lang= before it draws, the link of Settings carries the language, every text a screen uses exists (and is not empty) in the eight languages, nothing
visible is fixed in English in the page, the locale of every language is the one for time, date and numbers, and the font of ja and zh is a family that has those characters. The pages in a browser are in
test_207_wall_screens_browser.py."""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import screens  # noqa: E402

SCREENS = (HERE / "assets" / "static" / "screens.html").read_text(encoding="utf-8")
MAIN = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


class TheDecision(unittest.TestCase):
    def test_the_screen_reads_the_key_of_the_main_page_and_reloads_once_before_drawing(self):
        key = re.search(r'store\.set\("(am-lang)",LANG\)', MAIN)
        self.assertIsNotNone(key, "the main page saves the language under this key")
        self.assertIn('localStorage.getItem("am-lang")', SCREENS)
        self.assertIn('if(!q.has("lang"))', SCREENS)      # an address with ?lang= is never rewritten: it wins, and there is no loop
        self.assertIn("location.replace(", SCREENS)
        self.assertLess(SCREENS.index("LANG_RELOAD=true"), SCREENS.index("if(LANG_RELOAD)return;"))
        self.assertLess(SCREENS.index("if(LANG_RELOAD)return;"), SCREENS.index("document.documentElement.lang=D.html_lang"), "before anything is drawn")
        self.assertIn("q.set(\"lang\",l)", SCREENS)      # the other parameters (rotate, theme...) are kept: the query is the one of the address

    def test_the_link_of_settings_carries_the_language_of_the_page(self):
        self.assertIn('href="/screen/${k}?lang=${encodeURIComponent(LANG)}"', MAIN)

    def test_a_language_of_the_address_is_the_language_of_the_page_data(self):
        cfg = screens.settings({})
        prm = screens.params({}, cfg)
        for lang in LANGS:
            with i18n.use_language(lang):
                data = screens.page_data("overview", cfg, prm)
                expected = i18n.t("ui.scr_title_overview")
            self.assertEqual(data["lang"], lang)
            self.assertEqual(data["html_lang"], i18n.HTML_LANG[lang])
            self.assertEqual(data["locale"], i18n.BROWSER_LOCALE[lang])
            self.assertEqual(data["texts"]["ui.scr_title_overview"], expected)

    def test_the_locales_and_the_attribute_of_the_page(self):
        self.assertEqual(i18n.BROWSER_LOCALE, {"en": "en-GB", "es": "es-ES", "de": "de-DE", "fr": "fr-FR", "it": "it-IT", "ja": "ja-JP", "zh": "zh-CN", "pt": "pt-PT"})
        self.assertEqual(i18n.HTML_LANG["pt"], "pt-PT")
        self.assertIn('dir="ltr"', SCREENS.split("<head>")[0])
        for call in re.findall(r"to(?:Locale\w*String)\(([^)]{0,40})", SCREENS):
            self.assertTrue(call.startswith("D.locale"), "times, dates and numbers are written with the locale of the language: " + call)

    def test_japanese_and_chinese_have_a_font_that_draws_them(self):
        self.assertRegex(SCREENS, r':lang\(ja\) body\{font-family:[^}]*(Yu Gothic|Meiryo|Hiragino|Noto Sans CJK JP)')
        self.assertRegex(SCREENS, r':lang\(zh\) body\{font-family:[^}]*(Microsoft YaHei|PingFang|Noto Sans CJK SC)')


class TheTexts(unittest.TestCase):
    def test_every_text_a_screen_uses_exists_in_the_eight_languages(self):
        keys = screens.page_keys()
        self.assertGreater(len(keys), 60)
        catalogues = {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}
        for lang, words in catalogues.items():
            self.assertEqual([k for k in keys if not str(words.get(k, "")).strip()], [], lang)
        for key in sorted(k for k in set(re.findall(r'T\("(ui\.[a-z0-9_]+)"', SCREENS)) if not k.endswith("_")):
            self.assertIn(key, catalogues["en"], key)

    def test_a_translation_that_is_the_english_text_is_a_word_that_is_the_same_in_both_languages(self):
        catalogues = {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}
        same_ok = {"ui.scr_monitor", "ui.scr_sen_radar", "ui.scr_sev_info", "ui.scr_sev_error", "ui.scr_u_m", "ui.scr_score", "ui.scr_trend", "ui.scr_merge", "ui.scr_release", "ui.scr_min24",
                   "ui.scr_version", "ui.lv_warn"}
        for key in screens.page_keys():
            for lang in LANGS[1:]:
                english, own = catalogues["en"][key], catalogues[lang][key]
                if own == english and re.search(r"[A-Za-z]{4,}", english) and key not in same_ok and not re.fullmatch(r"ui\.a\d+", key):
                    self.fail(f"{lang} {key} is the English text: {english!r}")

    def test_no_visible_text_is_fixed_in_english_in_the_screen(self):
        body = SCREENS.split("<body", 1)[1]
        visible = re.sub(r"<script.*?</script[^>]*>|<style.*?</style[^>]*>|<svg.*?</svg[^>]*>", "", body, flags=re.S | re.I)
        words = [w for w in re.findall(r">([^<>{}]*[A-Za-z]{3,}[^<>{}]*)<", visible) if w.strip()]
        self.assertEqual(words, [], "text between tags in the static part of the page: it must come from the catalogue")
        for fixed in re.findall(r'textContent\s*=\s*"([A-Za-z][^"]{3,})"', SCREENS):
            self.assertEqual(fixed.strip(), "GitHub Actions Monitor", "the name of the product is the only fixed text")


if __name__ == "__main__":
    unittest.main()
