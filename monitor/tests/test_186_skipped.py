# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A job that did not run because of a condition or a path filter is not a failure: the page shows it with its own words and its own dashed look, apart from the red.
Runs in a headless browser; skipped when there is none (and on a CI runner unless MONITOR_BROWSER_TESTS=1)."""
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

PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out=document.getElementById("overflow-report")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"overflow-report"}));
  try{
    await wait(1200);
    const r={};
    const holder=document.createElement("div");
    holder.innerHTML=badge({status:"completed",conclusion:"skipped"})+badge({status:"completed",conclusion:"failure"})+badge({status:"completed",conclusion:"cancelled"});
    const spans=[...holder.querySelectorAll(".badge")];
    r.badges=spans.map(e=>[e.className,e.textContent,e.getAttribute("title")||""]);
    const run={repo:"repo-a",name:"build",status:"in_progress",event:"push",branch:"main",sha:"abc1234",actor:"x",seconds:60,url:"https://github.com/o/repo-a/actions/runs/1",jobs:[
      {name:"unit",status:"completed",conclusion:"success",steps_done:3,steps_total:3,seconds:10},
      {name:"docs",status:"completed",conclusion:"skipped",steps_done:0,steps_total:0,seconds:0},
      {name:"lint",status:"completed",conclusion:"failure",steps_done:1,steps_total:3,seconds:5}]};
    const box=document.createElement("div");box.innerHTML=nowRun(run,true);
    r.bars=[...box.querySelectorAll(".job .bar i")].map(e=>e.className);
    r.job_words=[...box.querySelectorAll(".job .mut:first-of-type")].map(e=>e.textContent);
    out.textContent=JSON.stringify({ok:true,found:r});
  }catch(e){out.textContent=JSON.stringify({ok:false,error:String(e),found:{}})}
})();
</script>
"""


def _port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@unittest.skipUnless(check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
@unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
class SkippedIsNotRed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _port()
        cls.demo = subprocess.Popen([sys.executable, "-I", str(TOOLS / "demo_monitor.py"), str(cls.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
        for _ in range(80):
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("the demo monitor did not start")
        cls.saved = check_overflow.PROBE
        check_overflow.PROBE = PROBE
        cls.relay = check_overflow.relay(cls.port)
        cls.base = f"http://127.0.0.1:{cls.relay.server_address[1]}/"

    @classmethod
    def tearDownClass(cls):
        check_overflow.PROBE = cls.saved
        cls.relay.shutdown()
        cls.demo.terminate()

    def test_a_skipped_badge_has_its_own_class_words_and_hint(self):
        found = check_overflow.measure(check_overflow.edge(), f"{self.base}?lang=en&nowizard=1", check_overflow.SIZES["desktop"])
        skipped, failure, cancelled = found["badges"]
        self.assertIn("b-skipped", skipped[0])
        self.assertEqual(skipped[1], "skipped (path filter)")
        self.assertIn("Not a failure", skipped[2])
        self.assertIn("b-failure", failure[0])
        self.assertEqual(failure[1], "failure")
        self.assertEqual(cancelled[1], "cancelled")
        self.assertEqual(found["bars"], ["done", "skip", "fail"], "the job that did not run is neither green nor red")
        self.assertEqual(found["job_words"][1], "skipped (path filter)")


class TheTextsExist(unittest.TestCase):
    def test_the_words_are_in_the_eight_languages_and_differ_from_a_failure(self):
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ui.concl_skipped", "ui.concl_cancelled", "ui.skipped_hint"):
                self.assertTrue(catalogue.get(key), (lang, key))

    def test_the_red_rule_ignores_a_skipped_run(self):
        from github_actions_monitor.data_pipeline import redrule
        self.assertIn("skipped", redrule.IGNORED)

    def test_the_page_gives_skipped_a_look_of_its_own(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn(".b-skipped{background:transparent", page)
        self.assertNotIn(".b-cancelled,.b-skipped{", page)


if __name__ == "__main__":
    unittest.main()
