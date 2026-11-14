# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Nothing repeats in the lists of the page: the panel "Right now" has ONE row for each repository with a counter ("3 running") and the runs in a folding list, and the alerts of stuck or failing
workflows are ONE line for each repository. Three runs of one repository give one row with n = 3. Runs in a headless browser; skipped when there is none (and on the runners of the CI unless
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

PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out=document.getElementById("overflow-report")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"overflow-report"}));
  try{
    await wait(1500);
    const r={};
    const mk=(repo,name,status,stuck)=>({repo:repo,name:name,status:status,stuck:!!stuck,event:"push",branch:"main",sha:"abc1234",actor:"x",seconds:600,url:"https://github.com/o/"+repo+"/actions/runs/1",jobs:[]});
    const act=[mk("repo-a","build","in_progress"),mk("repo-a","docs","in_progress"),mk("repo-a","pages","queued"),mk("repo-b","build","in_progress"),mk("repo-c","x","in_progress",true),mk("repo-c","y","in_progress",true)];
    const fail=[{repo:"repo-d",name:"one",conclusion:"failure",started:"2026-01-02T00:00:00Z",url:"https://github.com/o/repo-d/actions/runs/2"},{repo:"repo-d",name:"two",conclusion:"failure",started:"2026-01-01T00:00:00Z",url:"https://github.com/o/repo-d/actions/runs/3"},
      {repo:"repo-e",name:"one",conclusion:"failure",started:"2026-01-01T00:00:00Z",url:"https://github.com/o/repo-e/actions/runs/4"}];
    const d=Object.assign({},DATA,{active:act,failing:fail,issues:[],errors:{},stuck_minutes:120,ecosystems:Object.assign({},DATA.ecosystems,{"repo-a":"t","repo-b":"t","repo-c":"t","repo-d":"t","repo-e":"t"})});
    now_(d);await wait(100);
    const now=document.getElementById("now");
    r.cards=[...now.querySelectorAll("[data-now-repo]")].map(e=>[e.getAttribute("data-now-repo"),+e.getAttribute("data-now-n")]);
    r.names=[...now.querySelectorAll(".rl")].map(e=>e.textContent);
    r.counter=(now.querySelector('[data-now-repo="repo-a"] summary .badge')||{}).textContent||"";
    r.sub_runs=now.querySelectorAll('[data-now-repo="repo-a"] .subrun').length;
    const det=now.querySelector('details[data-now-details="repo-a"]');
    det.open=true;await wait(300);now_(d);await wait(100);
    r.still_open=document.querySelector('details[data-now-details="repo-a"]').open;
    alerts(d);await wait(100);
    r.alerts=[...document.querySelectorAll("#alerts [data-alert-repo]")].map(e=>[e.getAttribute("data-alert-repo"),e.textContent]);
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
class NothingRepeatsInABrowser(unittest.TestCase):
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

    def look(self, lang):
        return check_overflow.measure(check_overflow.edge(), f"{self.base}?lang={lang}&nowizard=1", check_overflow.SIZES["desktop"])

    def test_three_runs_of_one_repository_are_one_row_with_a_counter(self):
        found = self.look("en")
        self.assertEqual(found["cards"], [["repo-a", 3], ["repo-b", 1], ["repo-c", 2]], found)
        self.assertEqual(found["names"], ["repo-a", "repo-b", "repo-c"], "every repository once")
        self.assertEqual(found["counter"], "2 running · 1 queued", found)
        self.assertEqual(found["sub_runs"], 3, "the runs are in the folding list")

    def test_a_refresh_does_not_fold_what_the_person_unfolded(self):
        self.assertTrue(self.look("en")["still_open"])

    def test_the_alerts_say_each_repository_once(self):
        found = self.look("en")
        self.assertEqual([a[0] for a in found["alerts"]], ["repo-c", "repo-d", "repo-e"], found)
        by = dict(found["alerts"])
        self.assertIn("2 runs possibly stuck", by["repo-c"])
        self.assertIn("2 workflows failing (one, two)", by["repo-d"])

    def test_it_reads_in_other_languages_too(self):
        for lang in ("es", "de", "ja"):
            found = self.look(lang)
            self.assertEqual([c[1] for c in found["cards"]], [3, 1, 2], (lang, found))
            self.assertTrue(found["counter"] and "{" not in found["counter"], (lang, found))


class TheTextsExist(unittest.TestCase):
    KEYS = ("ui.n_group_run", "ui.n_group_queued", "ui.a_stuck_many", "ui.a_unresolved_many")

    def test_every_new_text_is_in_the_eight_languages_with_its_fields(self):
        fields = {"ui.n_group_run": {"{n}"}, "ui.n_group_queued": {"{n}"}, "ui.a_stuck_many": {"{repo}", "{n}", "{dur}", "{limit}"}, "ui.a_unresolved_many": {"{repo}", "{n}", "{names}", "{since}"}}
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in self.KEYS:
                self.assertIn(key, catalogue, (lang, key))
                for field in fields[key]:
                    self.assertIn(field, catalogue[key], (lang, key))

    def test_the_page_groups_through_one_function(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertEqual(page.count("function nowGroups("), 1)
        self.assertGreaterEqual(page.count("nowGroups("), 4)      # the panel and the two alert lists use it


if __name__ == "__main__":
    unittest.main()
