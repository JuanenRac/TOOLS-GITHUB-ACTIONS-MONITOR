# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The About panel shows the logo of the monitor and, when `ui.about_org_logo` is on, the logo of the organization: with a translated alternative text, a size that follows the width of the panel without
deforming the picture, and a note (never a broken page) when the organization has no logo or the file cannot be read. The drawing code of the page runs in a headless browser (when there is one)."""
import base64
import html as html_lib
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
KEYS = ("ui.about_org_logo_alt", "ui.about_org_logo_none", "ui.logo_aria", "cfg.f.ui.about_org_logo", "cfg.h.ui.about_org_logo")
EDGES = (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def browser():
    for path in EDGES:
        if Path(path).is_file():
            return path
    return shutil.which("msedge") or shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")


def catalogues():
    return {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}


def png(width, height):
    """A valid grey PNG of the given size (no library)."""
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    rows = b"".join(b"\x00" + b"\x90" * width for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


class Setting(unittest.TestCase):
    def test_the_setting_is_a_switch_that_starts_off_and_is_in_the_example_file(self):
        row = settings_api.FIELDS["ui.about_org_logo"]
        self.assertEqual(row[2], "bool")
        self.assertIs(actions_monitor.DEFAULTS["ui"]["about_org_logo"], False)
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertIs(example["ui"]["about_org_logo"], False)

    def test_its_words_exist_in_the_eight_languages(self):
        cats = catalogues()
        for lang in LANGS:
            for key in KEYS:
                self.assertTrue(cats[lang].get(key), (lang, key))
        for lang in LANGS[1:]:
            for key in KEYS[:2] + KEYS[3:]:
                self.assertNotEqual(cats[lang][key], cats["en"][key], (lang, key))


class Payload(unittest.TestCase):
    def logo(self, ui, info=None, error=None):
        config = {"ui": ui}
        fake = mock.Mock(side_effect=error) if error else mock.Mock(return_value=info or {"present": False, "tag": ""})
        with mock.patch.object(actions_monitor, "LIVE_CONFIG", config), mock.patch.object(actions_monitor.orglogo, "info", fake):
            return actions_monitor.about_logo(), fake

    def test_off_by_default_and_the_folder_is_not_even_read(self):
        out, fake = self.logo({})
        self.assertEqual(out, {"org": {"enabled": False, "present": False, "url": ""}})
        fake.assert_not_called()

    def test_on_with_a_logo_gives_the_address_with_the_tag_of_the_file(self):
        out, _ = self.logo({"about_org_logo": True}, {"present": True, "tag": "abcdef0123456789xx"})
        self.assertEqual(out["org"], {"enabled": True, "present": True, "url": "/api/screens/logo?v=abcdef0123456789"})

    def test_on_without_a_logo_says_so(self):
        out, _ = self.logo({"about_org_logo": True})
        self.assertEqual(out["org"], {"enabled": True, "present": False, "url": ""})

    def test_a_folder_that_cannot_be_read_is_a_missing_logo_and_not_an_error(self):
        out, _ = self.logo({"about_org_logo": True}, error=OSError("denied"))
        self.assertEqual(out["org"], {"enabled": True, "present": False, "url": ""})

    def test_only_true_switches_it_on(self):
        for odd in ("true", 1, "yes"):
            self.assertFalse(self.logo({"about_org_logo": odd})[0]["org"]["enabled"], odd)

    def test_the_about_answer_carries_it_and_no_path(self):
        with mock.patch.object(actions_monitor, "LIVE_CONFIG", {"ui": {"about_org_logo": True}}), mock.patch.object(actions_monitor.orglogo, "info", return_value={"present": True, "tag": "t" * 16}):
            data = actions_monitor.about_payload()
        self.assertIn("logo", data)
        self.assertNotIn(str(HERE), json.dumps(data["logo"]))


def code_of_the_logos():
    start = PAGE.index("function aboutLogos(l){")
    return PAGE[start:PAGE.index("\n}", PAGE.index("function aboutLogosWire(l){")) + 2]


def css_of_the_logos():
    rules = [m.group(0) for m in re.finditer(r"(?:\.about-logos[^{}]*|\.logo|\.lg-[a-z]+)\{[^{}]*\}", PAGE)]
    return "\n".join(rules)


class Page(unittest.TestCase):
    def test_the_panel_draws_them_before_the_list_and_after_loading(self):
        self.assertIn("let html=aboutLogos(a.logo)+dl(", PAGE)
        self.assertIn("body.innerHTML=html;aboutLogosWire(a.logo);opsWire();", PAGE)

    def test_no_new_image_travels_with_the_monitor_and_nothing_is_loaded_for_its_own_logo(self):
        code = code_of_the_logos()
        self.assertIn('document.querySelector(".brand .logo")', code)      # the drawing of the side panel, drawn again
        self.assertNotIn("data:image", code)

    def test_the_sizes_follow_the_width_and_never_deform(self):
        css = css_of_the_logos()
        self.assertIn("clamp(56px,14vw,96px)", css)
        self.assertIn("object-fit:contain", css)
        self.assertIn("aspect-ratio:1/1", css)
        self.assertIn("max-width:min(100%", css)


@unittest.skipUnless(browser(), "no Edge or Chrome on this computer")
class InTheBrowser(unittest.TestCase):
    """Both themes, three widths, the eight languages and the four cases (monitor only, with the logo of the organization, without it, and with a file that cannot be read)."""

    @classmethod
    def setUpClass(cls):
        cats = catalogues()
        brand = re.search(r'<svg class="logo".*?</svg>', PAGE, re.S).group(0)
        wide = "data:image/png;base64," + base64.b64encode(png(400, 100)).decode()
        script = ("const CATS=" + json.dumps({lang: {k: cats[lang][k] for k in KEYS[:3]} for lang in LANGS}, ensure_ascii=False) + ";let LANGNOW='en';const T=k=>CATS[LANGNOW][k]||k,$=id=>document.getElementById(id);\n"
                  "const esc=s=>String(s).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));\n"
                  + code_of_the_logos() + "\n"
                  "const WIDE=" + json.dumps(wide) + ";\n"
                  "const CASES={mon:{org:{enabled:false,present:false,url:''}},org:{org:{enabled:true,present:true,url:WIDE}},none:{org:{enabled:true,present:false,url:''}},broken:{org:{enabled:true,present:true,url:'missing-logo.png'}}};\n"
                  "const out=[];const wait=ms=>new Promise(r=>setTimeout(r,ms));\n"
                  "(async()=>{for(const theme of ['light','dark']){document.documentElement.dataset.theme=theme;for(const w of [300,640,1200]){for(const lang of Object.keys(CATS)){LANGNOW=lang;for(const name of Object.keys(CASES)){\n"
                  "  const host=document.createElement('div');host.id='about-body';host.style.cssText='width:'+w+'px;padding:0 14px;box-sizing:border-box;position:relative';document.body.appendChild(host);\n"
                  "  host.innerHTML=aboutLogos(CASES[name]);aboutLogosWire(CASES[name]);\n"
                  "  for(let i=0;i<40&&!(name==='broken'?$('about-logo-org')&&!$('about-logo-img'):(name==='org'?$('about-logo-img')&&$('about-logo-img').complete:true));i++)await wait(25);\n"
                  "  const box=host.getBoundingClientRect(),inner=host.querySelector('.about-logos'),svg=host.querySelector('svg.logo'),img=host.querySelector('img'),note=host.querySelector('#about-logo-org .mut');\n"
                  "  const figs=[...host.querySelectorAll('figure')].map(f=>f.getBoundingClientRect());\n"
                  "  out.push({theme,w,lang,name,fits:inner.scrollWidth<=inner.clientWidth+1&&figs.every(r=>r.left>=box.left-1&&r.right<=box.right+1),svg:!!svg,aria:svg&&svg.getAttribute('aria-label'),svgw:svg&&Math.round(svg.getBoundingClientRect().width),svgh:svg&&Math.round(svg.getBoundingClientRect().height),\n"
                  "    alt:img&&img.getAttribute('alt'),ratio:img&&img.complete&&img.naturalWidth?(img.getBoundingClientRect().width/img.getBoundingClientRect().height)/(img.naturalWidth/img.naturalHeight):null,\n"
                  "    imgw:img&&Math.round(img.getBoundingClientRect().width),note:note&&note.textContent,wrap:host.scrollWidth<=host.clientWidth+1});\n"
                  "  host.remove()}}}}document.getElementById('res').textContent=JSON.stringify(out)})();\n")
        css = (":root{--bg:#fff;--text:#111;--acc:#0a5;--ok:#0a0;--mut:#666}:root[data-theme=dark]{--bg:#111;--text:#eee;--acc:#6d9;--ok:#4c4;--mut:#aaa}body{margin:0;font:14px sans-serif;background:var(--bg);color:var(--text)}.mut{color:var(--mut)}\n"
               + css_of_the_logos())
        page_html = "<!doctype html><meta charset=utf-8><style>" + css + '</style><div class="brand" hidden>' + brand + "</div><pre id=res></pre><script>" + script.replace("</", "<\\/") + "</script>"
        cls.tmp = tempfile.TemporaryDirectory()
        page = Path(cls.tmp.name) / "logos.html"
        page.write_text(page_html, encoding="utf-8")
        run = subprocess.run([browser(), "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={Path(cls.tmp.name) / 'profile'}", "--virtual-time-budget=60000", "--dump-dom", page.as_uri()],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240, creationflags=0x08000000 if sys.platform == "win32" else 0)
        found = re.search(r'<pre id="res">(.*?)</pre>', run.stdout, re.S)
        cls.rows = json.loads(html_lib.unescape(found.group(1))) if found else None
        cls.cats = cats

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_stand_in_page_ran_every_case(self):
        self.assertIsNotNone(self.rows, "the stand-in page did not answer")
        self.assertEqual(len(self.rows), 2 * 3 * 8 * 4)

    def test_the_monitor_logo_is_always_there_with_its_translated_name_and_never_deformed(self):
        for row in self.rows:
            self.assertTrue(row["svg"], row)
            self.assertEqual(row["aria"], self.cats[row["lang"]]["ui.logo_aria"], row)
            self.assertLessEqual(abs(row["svgw"] - row["svgh"]), 1, row)
            self.assertGreaterEqual(row["svgw"], 56, row)

    def test_nothing_leaves_the_panel_at_any_width_language_or_theme(self):
        for row in self.rows:
            self.assertTrue(row["fits"] and row["wrap"], row)

    def test_the_organization_logo_has_a_translated_alternative_text_and_keeps_its_proportion(self):
        shown = [r for r in self.rows if r["name"] == "org"]
        self.assertTrue(shown)
        for row in shown:
            self.assertEqual(row["alt"], self.cats[row["lang"]]["ui.about_org_logo_alt"], row)
            self.assertIsNotNone(row["ratio"], row)
            self.assertAlmostEqual(row["ratio"], 1.0, delta=0.03, msg=row)

    def test_without_the_setting_there_is_only_the_logo_of_the_monitor(self):
        for row in (r for r in self.rows if r["name"] == "mon"):
            self.assertIsNone(row["alt"], row)
            self.assertIsNone(row["note"], row)

    def test_a_missing_or_unreadable_file_leaves_a_translated_note_and_no_broken_image(self):
        for row in (r for r in self.rows if r["name"] in ("none", "broken")):
            self.assertEqual(row["note"], self.cats[row["lang"]]["ui.about_org_logo_none"], row)
            self.assertIsNone(row["alt"], row)


if __name__ == "__main__":
    unittest.main()
