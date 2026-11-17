# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""No native dialog in the page. confirm(), alert() and prompt() of the browser are not drawn, or drop the page out of full screen, and they block the thread: the dashboard on a wall screen in full
screen showed nothing when the mode was changed to turbo. The page has ONE dialog of its own, `askConfirm(text, {danger})`, that answers a Promise<boolean>. Static: no file of assets/static calls a
native dialog, and the five questions go through askConfirm with their texts of the catalogue. In a browser: the dialog is in the DOM with the roles of an alert dialog, Accept and Cancel with the mouse,
Esc and Tab with the keyboard, the focus starts on Cancel for a dangerous action and goes back where it was, a second question closes the first one, and changing the mode asks inside the page."""
import json
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE.parent / "tools"))
import _testenv  # noqa: F401,E402

try:
    import check_overflow as co  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    co = None
try:
    import check_page  # noqa: E402
except ImportError:
    check_page = None

STATIC = HERE / "assets" / "static"
PAGE = (STATIC / "actions_monitor.html").read_text(encoding="utf-8")
NEEDS_BROWSER = bool(os.environ.get("MONITOR_REQUIRE_BROWSER"))
NATIVE = re.compile(r"(?<![\w.$])(?:window\.|self\.|globalThis\.)?(?:confirm|alert|prompt)\s*\(")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


class TheSource(unittest.TestCase):
    def test_no_page_calls_a_native_dialog(self):
        for path in sorted(STATIC.glob("*.html")):
            text = path.read_text(encoding="utf-8")
            hits = [(i + 1, line.strip()[:100]) for i, line in enumerate(text.splitlines()) if NATIVE.search(line)]
            self.assertEqual(hits, [], f"{path.name}: a native dialog (use askConfirm)")

    def test_the_five_questions_go_through_askconfirm_with_their_texts(self):
        for key in ("ui.ai_prop_confirm", "ui.mode_confirm", "ui.adv_gh_confirm", "ui.adv_act_confirm", "ui.auth_confirm_delete"):
            self.assertRegex(PAGE, r'await askConfirm\(T\("%s"' % re.escape(key), key)

    def test_the_dialog_is_an_alert_dialog_and_never_a_sentence_of_the_page(self):
        found = re.search(r'<div id="ask-dlg"[^>]*>', PAGE)
        self.assertIsNotNone(found)
        for needle in ('role="alertdialog"', 'aria-modal="true"', 'aria-labelledby="ask-h"', 'aria-describedby="ask-t"', "hidden"):
            self.assertIn(needle, found.group(0))
        for key in ("ui.confirm_title", "ui.confirm_ok", "ui.confirm_cancel"):
            self.assertIn(f'data-i18n="{key}"', PAGE)

    def test_the_words_exist_in_the_eight_languages(self):
        for lang in LANGS:
            words = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ui.confirm_title", "ui.confirm_ok", "ui.confirm_cancel"):
                self.assertTrue(str(words.get(key, "")).strip(), (lang, key))

    def test_the_pattern_sees_what_it_must(self):
        for line in ("if(window.confirm('x'))", "alert('x')", "x=prompt('a')", "if (confirm(T('k')))", ";confirm(1)"):
            self.assertTrue(NATIVE.search(line), line)
        for line in ("await askConfirm(T('k'))", "ui.adv_gh_confirm", "function confirmPlan(x)", "const r=await fetch('/api/ai/actions/confirm')", "obj.confirm(1)"):
            self.assertFalse(NATIVE.search(line), line)


PROBE = r"""<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out={native:0,cases:{}};
  window.confirm=()=>{out.native++;return true};window.alert=()=>{out.native++};window.prompt=()=>{out.native++;return ""};
  const dlg=()=>document.getElementById("ask-dlg"),key=(k)=>document.dispatchEvent(new KeyboardEvent("keydown",{key:k,bubbles:true,cancelable:true}));
  const state=()=>({open:!dlg().hidden,text:document.getElementById("ask-t").textContent,active:document.activeElement&&document.activeElement.id,
    title:document.getElementById("ask-h").textContent,ok:document.getElementById("ask-ok").textContent,no:document.getElementById("ask-no").textContent});
  try{
    await wait(1500);
    const anchor=document.createElement("button");anchor.id="anchor";anchor.textContent="anchor";document.body.appendChild(anchor);
    const c=out.cases;
    anchor.focus();let p=askConfirm("Question one");await wait(30);
    c.open=state();c.attrs={role:dlg().getAttribute("role"),modal:dlg().getAttribute("aria-modal"),by:dlg().getAttribute("aria-labelledby"),desc:dlg().getAttribute("aria-describedby")};
    document.getElementById("ask-ok").click();c.accept=await p;c.afterAccept=state();c.focusBack=document.activeElement.id;
    anchor.focus();p=askConfirm("Question two");await wait(30);document.getElementById("ask-no").click();c.cancel=await p;c.afterCancel=state();
    anchor.focus();p=askConfirm("Question three");await wait(30);key("Escape");c.esc=await p;c.afterEsc=state();c.focusBackEsc=document.activeElement.id;
    anchor.focus();p=askConfirm("Danger",{danger:true});await wait(30);c.dangerFocus=state().active;key("Tab");c.tab1=document.activeElement.id;key("Tab");c.tab2=document.activeElement.id;
    document.getElementById("ask-ok").click();c.dangerAccept=await p;
    p=askConfirm("First");await wait(10);const q=askConfirm("Second");c.superseded=await p;c.second=state().text;document.getElementById("ask-ok").click();c.secondValue=await q;
    p=askConfirm("Line one\nLine two <b>not html</b>");await wait(30);c.multiline={text:document.getElementById("ask-t").textContent,html:document.getElementById("ask-t").innerHTML.includes("<b>")};key("Escape");await p;
    // the mode: a change to turbo asks inside the page
    let posts=0;const realFetch=window.fetch;window.fetch=(u,o)=>{if(String(u).includes("/api/mode")&&o&&o.method==="POST"){posts++;return Promise.resolve({json:async()=>({ok:true})})}return realFetch(u,o)};
    MODEDATA={mode:"normal",allowed:true,default_minutes:30,floor:800,estimate:{turbo:{calls_per_hour:3000,with_cache_per_hour:900,minutes_left:null},fast:{calls_per_hour:1000,with_cache_per_hour:300,minutes_left:null}}};
    const sel=document.getElementById("mode-sel");[...sel.options].forEach(o=>o.disabled=false);
    sel.value="turbo";sel.dispatchEvent(new Event("change"));await wait(80);c.modeOpen=state();c.modePostsBefore=posts;
    document.getElementById("ask-no").click();await wait(80);c.modeCancel={value:sel.value,posts:posts,open:state().open};
    sel.value="turbo";sel.dispatchEvent(new Event("change"));await wait(80);document.getElementById("ask-ok").click();await wait(150);c.modeAccept={value:sel.value,posts:posts,open:state().open};
  }catch(e){out.error=String(e&&e.stack||e).slice(0,400)}
  out.errors=(window.__smoke&&window.__smoke.errors||[]).slice(0,10);
  const pre=document.createElement("pre");pre.id="ask-report";pre.textContent=JSON.stringify(out);document.body.appendChild(pre);
})();
</script>"""


class TheDialogInABrowser(unittest.TestCase):
    report = None

    @classmethod
    def setUpClass(cls):
        import socket
        import subprocess
        import time
        if co is None or check_page is None or not co.edge():
            return
        port = co.free_port()
        demo = subprocess.Popen([sys.executable, "-I", str(HERE.parent / "tools" / "demo_monitor.py"), str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
        server = None
        try:
            for _ in range(80):
                try:
                    socket.create_connection(("127.0.0.1", port), 0.5).close()
                    break
                except OSError:
                    time.sleep(0.5)
            else:
                raise RuntimeError("the demo monitor did not start")
            server = co.relay(port, probe=PROBE, head=check_page.HEAD.encode("utf-8"))
            cls.report = co.measure(co.edge(), f"http://127.0.0.1:{server.server_address[1]}/?lang=en&nowizard=1", co.SIZES["desktop"], report="ask-report")
        finally:
            if server:
                server.shutdown()
                server.server_close()
            demo.terminate()
            try:
                demo.wait(timeout=15)
            except subprocess.TimeoutExpired:
                demo.kill()

    def cases(self):
        if self.report is None:
            if NEEDS_BROWSER:
                self.fail("there is no Edge, Chrome or Chromium on this computer and MONITOR_REQUIRE_BROWSER is set")
            self.skipTest("no Edge, Chrome or Chromium on this computer, or the tools folder is not there")
        self.assertNotIn("error", self.report)
        return self.report["cases"]

    def test_the_dialog_is_in_the_page_with_the_roles_and_the_focus_of_an_alert_dialog(self):
        c = self.cases()
        self.assertEqual(c["open"]["text"], "Question one")
        self.assertTrue(c["open"]["open"])
        self.assertEqual((c["open"]["title"], c["open"]["ok"], c["open"]["no"]), ("Please confirm", "Accept", "Cancel"))
        self.assertEqual(c["attrs"], {"role": "alertdialog", "modal": "true", "by": "ask-h", "desc": "ask-t"})
        self.assertEqual(c["open"]["active"], "ask-ok")      # a harmless question starts on Accept

    def test_accept_and_cancel_with_the_mouse_and_escape_with_the_keyboard(self):
        c = self.cases()
        self.assertIs(c["accept"], True)
        self.assertFalse(c["afterAccept"]["open"])
        self.assertIs(c["cancel"], False)
        self.assertFalse(c["afterCancel"]["open"])
        self.assertIs(c["esc"], False)
        self.assertFalse(c["afterEsc"]["open"])

    def test_the_focus_goes_back_and_the_danger_starts_on_cancel_and_tab_stays_inside(self):
        c = self.cases()
        self.assertEqual((c["focusBack"], c["focusBackEsc"]), ("anchor", "anchor"))
        self.assertEqual(c["dangerFocus"], "ask-no")
        self.assertEqual((c["tab1"], c["tab2"]), ("ask-ok", "ask-no"))
        self.assertIs(c["dangerAccept"], True)

    def test_a_second_question_closes_the_first_and_the_text_is_never_html(self):
        c = self.cases()
        self.assertIs(c["superseded"], False)
        self.assertEqual(c["second"], "Second")
        self.assertIs(c["secondValue"], True)
        self.assertIn("Line two <b>not html</b>", c["multiline"]["text"])
        self.assertFalse(c["multiline"]["html"])

    def test_changing_the_mode_asks_inside_the_page_and_nothing_is_native(self):
        c = self.cases()
        self.assertTrue(c["modeOpen"]["open"])
        self.assertIn("Turbo", c["modeOpen"]["text"])
        self.assertEqual(c["modePostsBefore"], 0)      # nothing is sent while the question is open
        self.assertEqual((c["modeCancel"]["value"], c["modeCancel"]["posts"], c["modeCancel"]["open"]), ("normal", 0, False))
        self.assertEqual((c["modeAccept"]["posts"], c["modeAccept"]["open"]), (1, False))
        self.assertEqual(self.report["native"], 0)
        self.assertEqual(self.report["errors"], [])


if __name__ == "__main__":
    unittest.main()
