# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What a person folds stays folded: the sections of the CI sentinel, the cards of the other sentinels and the folding lists of the first tab are drawn again at every refresh, and a refresh must not
open again what was folded (or fold what was unfolded). Runs in a headless browser; skipped when there is none (and on the runners of the CI unless MONITOR_BROWSER_TESTS=1)."""
import json
import os
import re
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

try:
    import check_overflow  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_overflow = None

PROBE = r"""
<script>
(async function(){
  const wait=ms=>new Promise(r=>setTimeout(r,ms)),out=document.getElementById("overflow-report")||document.body.appendChild(Object.assign(document.createElement("pre"),{id:"overflow-report"}));
  try{
    await wait(2500);
    const r={};
    const det=k=>document.querySelector('#s-details details[data-k="'+k+'"]');
    const click=async el=>{el.querySelector("summary").click();await wait(150)};
    showTab("sci");await wait(200);
    r.start={a1:!!det("a1")&&det("a1").open,a4:!!det("a4")&&det("a4").open};
    await click(det("a1"));await click(det("a4"));      // a person folds the first section and unfolds the fourth
    r.after_click={a1:det("a1").open,a4:det("a4").open};
    for(let i=0;i<3;i++){await sentTick();await wait(150)}      // three refreshes of the data: the sections are drawn again each time
    r.after_refresh={a1:det("a1").open,a4:det("a4").open,a2:det("a2").open};
    r.saved=store.get("am-fold")||"";
    // a card of another sentinel and a folding list of the first tab
    showTab("ssec");await wait(150);
    const cards=[...document.querySelectorAll('#s-details-sec details[data-sp]')];
    r.cards=cards.length;
    if(cards.length){const k=cards[cards.length-1].dataset.k;const before=cards[cards.length-1].open;await click(cards[cards.length-1]);
      renderSentOthers();await wait(100);r.card_flip=[before,document.querySelector('details[data-k="'+k+'"]').open]}
    const errors={};for(let i=0;i<5;i++)errors["repo-"+i]="reason number "+i;
    const d=Object.assign({},DATA,{errors:errors});
    showTab("now");await wait(100);alerts(d);await wait(100);
    const many=document.querySelector('#alerts details[data-fold="al-many"]');
    r.many_start=many?many.open:null;
    if(many){await click(many);alerts(d);await wait(100);alerts(d);await wait(100);r.many_after=document.querySelector('#alerts details[data-fold="al-many"]').open}
    // the setting off: nothing is written to this browser, the memory of the page still holds
    I18N.screens=Object.assign({},I18N.screens,{remember_folds:false});
    store.set("am-fold","");
    showTab("sci");await wait(100);
    await click(det("a2"));await sentTick();await wait(150);
    r.off_memory=det("a2").open;r.off_saved=store.get("am-fold")||"";
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
class FoldsSurviveARefresh(unittest.TestCase):
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
        cls.found = {}

    @classmethod
    def tearDownClass(cls):
        check_overflow.PROBE = cls.saved
        cls.relay.shutdown()
        cls.demo.terminate()

    def look(self, lang):
        if lang not in self.found:
            self.found[lang] = check_overflow.measure(check_overflow.edge(), f"{self.base}?lang={lang}&nowizard=1", check_overflow.SIZES["desktop"])
        return self.found[lang]

    def test_a_section_folded_by_hand_is_still_folded_after_the_data_are_drawn_again(self):
        found = self.look("en")
        self.assertTrue(found["start"]["a1"], found)      # the first sections start unfolded
        self.assertFalse(found["start"]["a4"], found)
        self.assertEqual(found["after_click"], {"a1": False, "a4": True}, found)
        self.assertEqual(found["after_refresh"], {"a1": False, "a4": True, "a2": True}, found)      # folded stays folded, unfolded stays unfolded, the rest is not touched

    def test_the_choice_is_kept_in_this_browser_by_a_stable_id(self):
        saved = json.loads(self.look("en")["saved"])
        self.assertIn(["a1", 0], saved)
        self.assertIn(["a4", 1], saved)

    def test_a_card_of_another_sentinel_and_a_folding_list_keep_their_state(self):
        found = self.look("en")
        if found.get("cards"):
            before, after = found["card_flip"]
            self.assertNotEqual(before, after, found)      # the click flipped it and the repaint did not flip it back
        self.assertEqual(found.get("many_start"), False, found)
        self.assertEqual(found.get("many_after"), True, found)

    def test_with_the_setting_off_nothing_is_written_but_the_page_still_remembers(self):
        found = self.look("en")
        self.assertFalse(found["off_memory"], found)
        self.assertEqual(found["off_saved"], "", found)

    def test_it_holds_in_other_languages_too(self):
        for lang in ("es", "ja"):
            found = self.look(lang)
            self.assertEqual(found["after_refresh"]["a1"], False, (lang, found))
            self.assertEqual(found["after_refresh"]["a4"], True, (lang, found))


class TheSourceKeepsTheContract(unittest.TestCase):
    """Without a browser: every folding block drawn by the page carries a stable id, and the listeners that only looked at some containers are gone."""
    PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")

    def test_every_details_the_page_draws_has_a_fold_id(self):
        drawn = re.findall(r"<details\b[^>]*>", self.PAGE)
        self.assertGreaterEqual(len(drawn), 8)
        # the column picker of a table keeps its own state (tb.open) and the repositories of the first tab have their own sets
        bare = [d for d in drawn if "FOLD.attr" not in d and "data-now-details" not in d and "colsel" not in d]
        self.assertEqual(bare, [], "a folding block with no id in the fold memory is drawn open or shut at every refresh")

    def test_the_old_listeners_that_missed_the_sentinel_sections_are_gone(self):
        self.assertNotIn('$("t-sent").addEventListener("toggle"', self.PAGE)
        self.assertNotIn("SPTOUCH", self.PAGE)

    def test_the_setting_exists_with_a_conservative_default(self):
        from github_actions_monitor.app import actions_monitor
        self.assertIs(actions_monitor.DEFAULTS["ui"]["remember_folds"], True)
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertIs(example["ui"]["remember_folds"], True)


if __name__ == "__main__":
    unittest.main()
