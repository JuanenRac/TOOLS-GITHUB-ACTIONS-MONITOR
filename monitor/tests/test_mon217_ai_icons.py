# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The two AI indicators of the bar are icons, not words: a button with a drawing whose shape (check, slash, triangle) says the state, a name and a tooltip in the language of the page with the exact state, and a
click that opens the AI settings. The drawing code of the page is run in a headless browser (when there is one) against a small stand-in page; the words and the layout rules are checked in the files."""
import html as html_lib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
KEYS = ("ui.bar_on", "ui.bar_off", "ui.bar_ai_err", "ui.bar_ai_go_int", "ui.bar_ai_go_ext", "ui.bar_ai_int", "ui.bar_ai_ext", "ui.bar_ai_int_t", "ui.bar_ai_int_err_t", "ui.bar_ai_ext_t")
EDGES = (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def browser():
    for path in EDGES:
        if Path(path).is_file():
            return path
    return shutil.which("msedge") or shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")


def catalogues():
    return {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}


def code_of_the_icons():
    start = PAGE.index("function aiIcon(kind,state){")
    return PAGE[start:PAGE.index("function agoText(s){", start)]


class Words(unittest.TestCase):
    def test_every_word_exists_in_the_eight_languages_and_differs_from_english(self):
        cats = catalogues()
        for lang in LANGS:
            for key in KEYS:
                self.assertTrue(cats[lang].get(key), (lang, key))
        for lang in LANGS[1:]:
            for key in ("ui.bar_ai_err", "ui.bar_ai_go_int", "ui.bar_ai_go_ext", "ui.bar_ai_int_err_t"):
                self.assertNotEqual(cats[lang][key], cats["en"][key], (lang, key))


class Markup(unittest.TestCase):
    def test_the_indicators_are_real_buttons_with_no_text_inside(self):
        for ident, kind in (("bar-ai-int", "int"), ("bar-ai-ext", "ext")):
            self.assertRegex(PAGE, rf'<button type="button" class="ib ai-ind" id="{ident}" data-kind="{kind}" data-state="off"></button>')
        self.assertNotRegex(PAGE, r'<span[^>]*id="bar-ai-(int|ext)"')

    def test_the_state_is_told_by_the_shape_and_not_only_by_the_colour(self):
        code = code_of_the_icons()
        self.assertIn('M15.6 18l1.6 1.7 3.1-3.4', code)      # the check of the active state
        self.assertIn('M14.5 21.5l7-7', code)                # the slash of the inactive one
        self.assertIn('M18 12.4l5.6 9.8H12.4z', code)        # the triangle of the one with an error
        self.assertIn('stroke-dasharray="2.2 1.8"', code)     # an inactive drawing is dashed

    def test_the_icon_fits_the_bar_and_has_a_visible_focus(self):
        self.assertRegex(PAGE, r"\.sb-bar \.ai-ind \.ico\{width:22px;height:22px")
        self.assertIn(".sb-bar .ai-ind:focus-visible{outline:2px solid var(--acc)", PAGE)
        self.assertIn(".sb-bar .ai-ind[data-state=err]{color:var(--bad)}", PAGE)

    def test_the_click_goes_to_the_ai_section_of_the_settings_and_each_icon_to_its_own_group(self):
        code = code_of_the_icons()
        self.assertIn('CFG.tab="ai"', code)
        self.assertIn('return kind==="int"?"ai.provider":"ai_alerts.enabled"', code)
        self.assertIn('T("ui.bar_ai_go_"+kind)', code)

    def test_the_two_targets_are_real_settings_of_different_groups(self):
        text = (HERE / "src" / "github_actions_monitor" / "app" / "settings_api.py").read_text(encoding="utf-8")
        self.assertRegex(text, r'_f\(_T_AI, "provider", "ai\.provider"')
        self.assertRegex(text, r'_f\(_T_AI, "alerts", "ai_alerts\.enabled"')


@unittest.skipUnless(browser(), "no Edge or Chrome on this computer")
class InTheBrowser(unittest.TestCase):
    """State, tooltip, name for screen readers, click and focus, in the eight languages, with the real drawing code of the page."""

    @classmethod
    def setUpClass(cls):
        cats = catalogues()
        script = ("const CATS=" + json.dumps({lang: {k: cats[lang][k] for k in KEYS} for lang in LANGS}, ensure_ascii=False) + ";\n"
                  "let LANGNOW='en';const T=k=>CATS[LANGNOW][k]||k,$=id=>document.getElementById(id);const store={set(){}};const CFG={tab:'',groups:[1]};let opened=[];\n"
                  "function showTab(t){opened.push('tab:'+t)}function cfgShowTab(t){opened.push('cfg:'+t)}\n"
                  + code_of_the_icons() + "\n"
                  "const out=[];for(const lang of Object.keys(CATS)){LANGNOW=lang;\n"
                  "  for(const [kind,id] of [['int','bar-ai-int'],['ext','bar-ai-ext']]){for(const st of ['on','off','err']){\n"
                  "    aiPaint(id,kind,T('ui.bar_ai_'+kind),st,T('ui.bar_ai_'+kind+'_t'));const e=$(id);\n"
                  "    out.push({lang,id,st,label:e.getAttribute('aria-label'),title:e.title,state:e.dataset.state,svg:e.innerHTML.length,tag:e.tagName,tab:e.tabIndex,\n"
                  "      check:e.innerHTML.includes('M15.6 18l'),slash:e.innerHTML.includes('M14.5 21.5l'),tri:e.innerHTML.includes('M18 12.4l'),w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height})}}}\n"
                  "opened=[];$('bar-ai-int').click();const a=opened.slice();opened=[];$('bar-ai-ext').click();const b=opened.slice();\n"
                  "setTimeout(()=>{const r={};$('bar-ai-ext').click();\n"
                  "  setTimeout(()=>{r.ext=document.activeElement.id;$('bar-ai-int').click();\n"
                  "    setTimeout(()=>{r.int=document.activeElement.id;const h=document.querySelector('.cfg-hit');r.hit=h&&h.id;\n"
                  "      document.getElementById('res').textContent=JSON.stringify({out,a,b,tab:CFG.tab,focus:r})},200)},200)},50);\n")
        html = ("<!doctype html><meta charset=utf-8><style>.ib{width:28px;height:28px;padding:0;display:inline-grid;place-items:center}.ico{width:22px;height:22px;fill:none;stroke:currentColor}</style>"
                '<div class="sb-bar"><button type="button" class="ib ai-ind" id="bar-ai-int" data-kind="int" data-state="off"></button><button type="button" class="ib ai-ind" id="bar-ai-ext" data-kind="ext" data-state="off"></button></div>'
                '<div id="cfp-ai"><div class="cfg-group" id="g-int"><div class="cfg-f" data-key="ai.provider"><select id="f-int"></select></div></div><div class="cfg-group" id="g-ext"><div class="cfg-f" data-key="ai_alerts.enabled"><input id="f-ext" type="checkbox"></div></div></div>'
                "<pre id=res></pre><script>" + script.replace("</", "<\\/") + "</script>")
        cls.tmp = tempfile.TemporaryDirectory()
        page = Path(cls.tmp.name) / "icons.html"
        page.write_text(html, encoding="utf-8")
        run = subprocess.run([browser(), "--headless=new", "--disable-gpu", "--no-first-run", *(["--no-sandbox", "--disable-dev-shm-usage"] if sys.platform.startswith("linux") else []), f"--user-data-dir={Path(cls.tmp.name) / 'profile'}", "--virtual-time-budget=4000", "--dump-dom", page.as_uri()],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, creationflags=0x08000000 if sys.platform == "win32" else 0)
        found = re.search(r'<pre id="res">(.*?)</pre>', run.stdout, re.S)
        cls.result = json.loads(html_lib.unescape(found.group(1))) if found else None
        cls.cats = cats

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_drawing_code_ran(self):
        self.assertIsNotNone(self.result, "the stand-in page did not answer")

    def test_each_state_has_its_own_shape_its_name_and_the_exact_state_in_the_tooltip(self):
        for row in self.result["out"]:
            cat = self.cats[row["lang"]]
            word = cat["ui.bar_on"] if row["st"] == "on" else cat["ui.bar_ai_err"] if row["st"] == "err" else cat["ui.bar_off"]
            name = cat["ui.bar_ai_int"] if row["id"].endswith("int") else cat["ui.bar_ai_ext"]
            self.assertEqual(row["label"], f"{name}: {word}", row)
            self.assertTrue(row["title"].startswith(f"{name}: {word}. "), row)
            self.assertTrue(row["title"].endswith(cat["ui.bar_ai_go_int" if row["id"].endswith("int") else "ui.bar_ai_go_ext"]), row)
            self.assertNotEqual(cat["ui.bar_ai_go_int"], cat["ui.bar_ai_go_ext"], row)
            self.assertEqual((row["check"], row["slash"], row["tri"]), (row["st"] == "on", row["st"] == "off", row["st"] == "err"), row)
            self.assertEqual(row["state"], row["st"])

    def test_they_are_focusable_buttons_of_the_size_of_the_bar(self):
        for row in self.result["out"]:
            self.assertEqual(row["tag"], "BUTTON")
            self.assertGreaterEqual(row["tab"], 0)
            self.assertEqual((round(row["w"]), round(row["h"])), (28, 28), row)

    def test_the_click_opens_the_settings_on_the_ai_tab(self):
        self.assertEqual(self.result["a"], ["tab:cfg", "cfg:ai"])
        self.assertEqual(self.result["b"], ["tab:cfg", "cfg:ai"])
        self.assertEqual(self.result["tab"], "ai")

    def test_each_icon_focuses_the_first_control_of_its_own_group_and_flashes_the_group(self):
        self.assertEqual(self.result["focus"]["ext"], "f-ext")
        self.assertEqual(self.result["focus"]["int"], "f-int")
        self.assertEqual(self.result["focus"]["hit"], "g-int")


if __name__ == "__main__":
    unittest.main()
