# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The wall screens in a real browser (Edge, Chrome or Chromium in headless mode, against the demo monitor with invented data): the three pages in 1920x1080, 3840x2160 and 1080x1920 and in the eight
languages open without a message in the console, without a scroll bar and without a text that leaves its box; they only ask the monitor for its own data (never GitHub, never another address); a failure
blinks less than twice a second and does not blink at all for who asked for less motion or with ?blink=off; and ?rotate=5 turns through the three pages. Skipped when there is no browser (and on a CI runner unless
MONITOR_BROWSER_TESTS=1)."""
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(TOOLS))
import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402

try:
    import check_overflow  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_overflow = None

KINDS = ("overview", "now", "sentinels")
SIZES = {"1080p": (1920, 1080), "4K": (3840, 2160), "1080p turned": (1080, 1920)}
REDUCED = "--force-prefers-reduced-motion"
REPORT = "screens-report"

# runs before the scripts of the page: it records what the page does with the network and with the console
HEAD = b"""<script>
window.__errs=[];window.__reqs=[];
try{var __p=new URLSearchParams(location.search).get("pref");if(__p)localStorage.setItem("am-lang",__p)}catch(e){}
window.addEventListener("error",e=>window.__errs.push("error: "+e.message));
window.addEventListener("unhandledrejection",e=>window.__errs.push("rejection: "+e.reason));
const __ce=console.error;console.error=function(){window.__errs.push("console.error: "+[].slice.call(arguments).join(" "));__ce.apply(console,arguments)};
const __f=window.fetch;window.fetch=function(u){window.__reqs.push(String(u));return __f.apply(this,arguments)};
for(const n of ["XMLHttpRequest","WebSocket","EventSource"]){const o=window[n];if(o)window[n]=function(){window.__reqs.push(n+" "+arguments[0]);return new o(...arguments)}}
if(navigator.sendBeacon)navigator.sendBeacon=function(u){window.__reqs.push("beacon "+u);return true};
</script>"""

PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const out=document.getElementById("screens-report")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"screens-report"}));
  try{
    const seq=[];const note=()=>{const k=window.__screens&&window.__screens.state.kind;if(k&&seq[seq.length-1]!==k)seq.push(k)};
    const rot=new URLSearchParams(location.search).get("rotate");
    for(let i=0;i<(rot?28:12);i++){note();await wait(rot?500:250)}
    const de=document.documentElement,cut=[];
    const shown=e=>{for(let n=e;n&&n!==de;n=n.parentElement){const s=getComputedStyle(n);if(s.display==="none"||s.visibility==="hidden")return false}return true};
    const where=e=>e.tagName.toLowerCase()+(e.id?"#"+e.id:"")+(e.className&&e.className.baseVal===undefined?"."+String(e.className).split(" ").slice(0,2).join("."):"");
    for(const e of document.querySelectorAll(".card,.sen,.tile,.failrow,.rowbar,.row,.ev,.br,.hn,h2,.chip,.brand,.clock,#banner")){
      if(!shown(e)||e.closest("svg"))continue;
      const s=getComputedStyle(e),ell=s.textOverflow==="ellipsis"&&(e.title||e.querySelector("[title]"));
      if(e.scrollWidth>e.clientWidth+3&&!ell)cut.push(where(e)+" wide "+e.scrollWidth+">"+e.clientWidth+" "+(e.textContent||"").trim().slice(0,40));
      if(e.scrollHeight>e.clientHeight+3&&!e.matches(".list,.ticker,.heat"))cut.push(where(e)+" tall "+e.scrollHeight+">"+e.clientHeight+" "+(e.textContent||"").trim().slice(0,40));
    }
    const fails=[...document.querySelectorAll(".fail")].filter(shown).map(e=>{const s=getComputedStyle(e);return{name:s.animationName,dur:s.animationDuration,calm:e.classList.contains("calm"),at:where(e)}});
    const title=document.getElementById("h-title").textContent;
    out.textContent=JSON.stringify({ok:true,errors:window.__errs,reqs:window.__reqs,scroll:{w:[de.scrollWidth,de.clientWidth],h:[de.scrollHeight,de.clientHeight]},cut:cut,fails:fails,seq:seq,
      reduced:matchMedia("(prefers-reduced-motion: reduce)").matches,title:title,search:location.search,text:document.body.innerText,cards:document.querySelectorAll(".card:not([hidden]),.sen").length,kind:window.__screens.state.kind,lang:document.documentElement.lang});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e)})}
  document.title="screens-done";
})();
</script>
"""


def _port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@unittest.skipUnless(check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
@unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
class TheScreensInABrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _port()
        cls.demo = subprocess.Popen([sys.executable, "-I", str(TOOLS / "demo_monitor.py"), str(cls.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
        for _ in range(80):
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("the demo monitor did not start")
        cls.relay = check_overflow.relay(cls.port, probe=PROBE, head=HEAD)
        cls.base = f"http://127.0.0.1:{cls.relay.server_address[1]}"
        cls.browser = check_overflow.edge()

    @classmethod
    def tearDownClass(cls):
        cls.relay.shutdown()
        cls.demo.terminate()

    def open(self, path, size=(1920, 1080), flags=()):
        return check_overflow.measure(self.browser, self.base + path, size, report=REPORT, flags=flags)

    def clean(self, report, label):
        self.assertTrue(report["ok"], (label, report))
        self.assertEqual(report["errors"], [], label)
        self.assertEqual(report["cut"], [], label)
        self.assertLessEqual(report["scroll"]["w"][0], report["scroll"]["w"][1] + 1, (label, "sideways scroll"))
        self.assertLessEqual(report["scroll"]["h"][0], report["scroll"]["h"][1] + 1, (label, "vertical scroll"))
        for url in report["reqs"]:
            self.assertTrue(url.startswith("/api/screens/data?screen=") or url == "/api/version", (label, "the page asked for something else", url))      # the data, and the version of the monitor (screens.version_check_seconds)
        self.assertTrue(report["reqs"], label)
        self.assertGreater(report["cards"], 1, label)

    def many(self, jobs):
        """Opens several pages three at a time (a normal computer is not busy with more): jobs are (path, size, flags); the answers come back in the same order."""
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as pool:
            return list(pool.map(lambda job: self.open(job[0], job[1] if len(job) > 1 else (1920, 1080), job[2] if len(job) > 2 else ()), jobs))

    def test_every_screen_in_every_size_is_clean_and_only_asks_the_monitor(self):
        jobs = [(f"/screen/{kind}?lang=en", size) for kind in KINDS for size in SIZES.values()]
        for (path, size), report in zip(jobs, self.many(jobs)):
            self.clean(report, (path, size))
            self.assertEqual(report["kind"], path.split("/")[2].split("?")[0])

    def test_every_language_fits_in_every_size(self):
        """All 72 combinations of language, size and screen (8 x 3 x 3): German in 4K or Japanese turned are not left to chance."""
        jobs = [(f"/screen/{kind}?lang={lang}", size) for lang in i18n.LANGS for size in SIZES.values() for kind in KINDS]
        self.assertEqual(len(jobs), 72)
        for (path, size), report in zip(jobs, self.many(jobs)):
            lang, kind = path.split("lang=")[1], path.split("/")[2].split("?")[0]
            self.clean(report, (kind, lang, size))
            with i18n.use_language(lang):
                self.assertEqual(report["title"], i18n.t("ui.scr_title_" + kind), (kind, lang))
            self.assertEqual(report["lang"], i18n.HTML_LANG[lang])

    def test_the_language_chosen_on_the_main_page_decides_when_the_address_has_none_in_the_eight_languages(self):
        jobs = [(f"/screen/{kind}?pref={lang}", (1920, 1080)) for lang in i18n.LANGS for kind in KINDS]
        for (path, size), report in zip(jobs, self.many(jobs)):
            lang, kind = path.split("pref=")[1], path.split("/")[2].split("?")[0]
            self.clean(report, (kind, lang))
            with i18n.use_language(lang):
                self.assertEqual(report["title"], i18n.t("ui.scr_title_" + kind), (kind, lang))
            self.assertEqual(report["lang"], i18n.HTML_LANG[lang], (kind, lang))
            if lang != "en":      # the monitor of the test speaks English: a saved English needs no reload, any other language reloads the page once with the language in the address
                self.assertIn("lang=" + lang, report["search"], (kind, lang))
            else:
                self.assertNotIn("lang=", report["search"], (kind, lang))
            self.assertIn("pref=" + lang, report["search"], (kind, lang))      # and kept the rest of the parameters
            if lang != "en":
                self.assert_no_english_left(report["text"], lang, kind)

    def assert_no_english_left(self, text, lang, kind):
        """No phrase of the English catalogue that the language translates differently is on the screen (the product name and the words that are the same in both are not counted)."""
        shown = text.lower()
        english, own = {}, {}
        for key in (k for k in i18n.catalogue_keys() if k.startswith(("ui.scr_", "ui.lv_"))):
            with i18n.use_language("en"):
                english[key] = i18n.t(key)
            with i18n.use_language(lang):
                own[key] = i18n.t(key)
        DATA_WORDS = {"release"}      # a workflow of the demo is called so: it is data on the screen, not text of the interface
        leaked = [english[k] for k in english if english[k].lower() not in DATA_WORDS and "{" not in english[k] and len(english[k]) >= 6 and english[k].lower() != own[k].lower() and english[k].lower() in shown and english[k].lower() not in own[k].lower()]
        self.assertEqual(leaked, [], (kind, lang, "English text on a screen in another language"))

    def test_the_address_wins_over_the_language_saved_by_the_main_page(self):
        jobs = [(f"/screen/{kind}?pref=es&lang=de", (1920, 1080)) for kind in KINDS]
        for (path, size), report in zip(jobs, self.many(jobs)):
            kind = path.split("/")[2].split("?")[0]
            self.clean(report, kind)
            with i18n.use_language("de"):
                self.assertEqual(report["title"], i18n.t("ui.scr_title_" + kind), kind)
            self.assertEqual(report["lang"], "de")
            self.assertNotIn("lang=es", report["search"])

    def test_a_saved_language_keeps_the_rotation_going(self):
        report = self.open("/screen/overview?pref=ja&rotate=5")
        self.assertTrue(report["ok"], report)
        self.assertIn("rotate=5", report["search"])
        self.assertIn("lang=ja", report["search"])
        self.assertEqual(report["lang"], "ja")
        self.assertGreaterEqual(len(report["seq"]), 2, report["seq"])

    def test_the_light_and_the_high_contrast_themes_and_the_large_type_fit_too(self):
        jobs = [(f"/screen/{kind}?lang=en&{query}",) for query in ("theme=light", "theme=contrast", "density=large") for kind in KINDS]
        for job, report in zip(jobs, self.many(jobs)):
            self.clean(report, job[0])

    def test_a_failure_blinks_softly_and_not_at_all_for_who_asked_for_less_motion(self):
        jobs = [(f"/screen/{kind}?lang=en",) for kind in KINDS] + [(f"/screen/{kind}?lang=en", (1920, 1080), (REDUCED,)) for kind in KINDS] + [(f"/screen/{kind}?lang=en&blink=off",) for kind in KINDS]
        answers = self.many(jobs)
        for kind, fails in zip(KINDS, answers[:3]):
            self.assertTrue(fails["fails"], f"{kind}: the demo has failures and the page shows them")
            for f in fails["fails"]:
                if f["calm"]:
                    self.assertEqual(f["name"], "none", f)
                    continue
                self.assertNotEqual(f["name"], "none", f)
                self.assertGreaterEqual(float(f["dur"].rstrip("s")), 0.5, "never faster than twice a second: " + json.dumps(f))
        for reduced in answers[3:6]:
            self.assertTrue(reduced["reduced"])
            self.assertTrue(reduced["fails"], "a failure is still shown (a fixed glow)")
            self.assertEqual({f["name"] for f in reduced["fails"]}, {"none"}, "less motion: nothing blinks")
        for off in answers[6:]:
            self.assertEqual({f["name"] for f in off["fails"]}, {"none"}, "?blink=off: nothing blinks")

    def test_rotation_turns_through_the_pages_in_order(self):
        report, still = self.many([("/screen/overview?lang=en&rotate=5",), ("/screen/now?lang=en&rotate=2",)])
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["seq"][:3], ["overview", "fleet", "now"], report["seq"])
        for url in report["reqs"]:
            self.assertTrue(url.startswith("/api/screens/data?screen=") or url == "/api/version", url)
        self.assertEqual(set(still["seq"]), {"now"}, "a turn faster than five seconds is no turn")


if __name__ == "__main__":
    unittest.main()
