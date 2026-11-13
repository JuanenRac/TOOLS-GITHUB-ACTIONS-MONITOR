# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The page knows when it is out of step with the monitor (age of the last answer, retry, watchdog, old data) and the "bing bing" survives a reload and a gap; the real functions of the page run in node."""
import json
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
from github_actions_monitor import i18n  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
NODE = shutil.which("node")
NEW_KEYS = ("ui.fresh", "ui.fresh_late", "ui.fresh_retry", "ui.fresh_t", "ui.fresh_late_t", "ui.snd_locked", "ui.snd_locked_t")


def block(name):
    return PAGE[PAGE.index(f"/*{name}-BEGIN*/"):PAGE.index(f"/*{name}-END*/")]


def run_js(body):
    """Runs the sound and freshness blocks of the page with a fake clock and a fake storage; the script prints a JSON result."""
    prelude = ("let NOW=1000000;const nowMs=()=>NOW;let TONES=0;const playTones=()=>{TONES++};const MEM={};"
               "const store={get:k=>(k in MEM?MEM[k]:null),set:(k,v)=>{MEM[k]=v}};"
               "const I18N={sound:{enabled:true,on_new_red:true,on_connection_lost:true,cooldown_seconds:30,volume:40}};"
               "const red=(...k)=>({failing:k.map(x=>({repo:x,name:'ci'})),offline:{offline:false}});")
    code = prelude + block("SOUND") + block("FRESH") + body
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.js"
        path.write_text(code, encoding="utf-8")
        out = subprocess.run([NODE, str(path)], capture_output=True, text=True, timeout=60, check=False)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


class Texts(unittest.TestCase):
    def test_the_new_texts_exist_in_the_eight_languages_and_the_page_uses_them(self):
        for key in NEW_KEYS:
            self.assertIn(key, PAGE, key)
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))
        for lang in i18n.LANGS:
            text = i18n.tl(lang, "cfg.h.sound.server_beep")
            self.assertGreater(len(text), 120, lang)      # the help says what the page cannot do and what this switch adds

    def test_the_page_has_the_banner_the_watchdog_and_the_reload_on_return(self):
        for needle in ('id="snd-lock"', "function soundUnlock(", "function freshWatch(", "setInterval(freshDog", "visibilitychange", "AbortController", "tick(true)"):
            self.assertIn(needle, PAGE, needle)


@unittest.skipUnless(NODE, "no node on this computer")
class Freshness(unittest.TestCase):
    def test_a_stopped_server_turns_the_page_late_after_a_minute_and_the_retry_backs_off(self):
        out = run_js("""
const r=[];FRESH.okAt=NOW;
NOW+=30000;r.push(freshInfo(NOW).late);               // 30 s: not late yet
NOW+=31000;r.push(freshInfo(NOW).late);               // 61 s: late
r.push(freshFail(NOW),freshFail(NOW),freshFail(NOW),freshFail(NOW));      // 3000, 6000, 9000, stays at 9000
r.push(freshInfo(NOW).retry);
console.log(JSON.stringify(r));""")
        self.assertEqual(out, [False, True, 3000, 6000, 9000, 9000, 9])

    def test_a_slow_answer_is_aborted_and_a_late_page_with_nothing_on_the_way_asks_again(self):
        out = run_js("""
const r=[];FRESH.okAt=NOW;
FRESH.busy=true;FRESH.start=NOW;NOW+=10000;r.push(freshWatch(NOW));      // still waiting: leave it
NOW+=11000;r.push(freshWatch(NOW));                                      // 21 s: abort
FRESH.busy=false;FRESH.start=NOW;r.push(freshWatch(NOW));                // on time: nothing
NOW+=61000;r.push(freshWatch(NOW));                                      // 61 s without an answer: ask again
FRESH.start=NOW;NOW+=2000;r.push(freshWatch(NOW));                       // just asked: wait
console.log(JSON.stringify(r));""")
        self.assertEqual(out, ["", "abort", "", "tick", ""])

    def test_data_that_stop_changing_are_old_unless_the_monitor_is_loading_or_paused(self):
        out = run_js("""
const r=[],d={updated:'T1',refresh_seconds:20};
freshOk(NOW,d);
for(let i=0;i<6;i++){NOW+=10000;freshOk(NOW,d)}      // answers every 10 s with the same stamp for 60 s
r.push(freshInfo(NOW,20).old);                       // under two minutes: fine
for(let i=0;i<7;i++){NOW+=10000;freshOk(NOW,d)}
r.push(freshInfo(NOW,20).old,freshInfo(NOW,20).late);   // 130 s: old, so late
freshOk(NOW,{updated:'T1',refresh_seconds:20,paused_quota:true});
r.push(freshInfo(NOW,20).old);                       // paused on quota: not old
for(let i=0;i<14;i++){NOW+=10000;freshOk(NOW,{updated:'T1',loading:3})}
r.push(freshInfo(NOW,20).old);                       // loading: not old
const slow={updated:'T2',refresh_seconds:1800};freshOk(NOW,slow);NOW+=300000;freshOk(NOW,slow);r.push(freshInfo(NOW,1800).old);      // a slow refresh in low mode is no alarm
console.log(JSON.stringify(r));""")
        self.assertEqual(out, [False, True, True, False, False, False])

    def test_coming_back_after_a_gap_says_so_once(self):
        out = run_js("""
const r=[];freshOk(NOW,{updated:'A'});
NOW+=90000;r.push(freshOk(NOW,{updated:'B'}));      // was late: true
NOW+=10000;r.push(freshOk(NOW,{updated:'C'}));      // normal: false
console.log(JSON.stringify(r));""")
        self.assertEqual(out, [True, False])


@unittest.skipUnless(NODE, "no node on this computer")
class SoundAcrossReloadsAndGaps(unittest.TestCase):
    def test_a_red_that_came_while_the_page_was_closed_sounds_and_one_already_known_does_not(self):
        out = run_js("""
const r=[];
soundWatch(red('a'));r.push(TONES);                  // very first look ever: nothing
SOUND.first=true;SOUND.known=new Set();SOUND.lastAt=0;      // the page is reloaded: same storage
NOW+=600000;soundWatch(red('a'));r.push(TONES);      // the same red as before the reload: silent
SOUND.first=true;SOUND.known=new Set();SOUND.lastAt=0;
NOW+=600000;soundWatch(red('a','b'));r.push(TONES);  // a new red while closed: sounds
console.log(JSON.stringify(r));""")
        self.assertEqual(out, [0, 0, 1])

    def test_an_old_baseline_is_not_trusted(self):
        out = run_js("""
const r=[];soundWatch(red('a'));
SOUND.first=true;SOUND.known=new Set();NOW+=7*3600*1000;
soundWatch(red('a','b'));r.push(TONES);              // seven hours later: first look again, silent
console.log(JSON.stringify(r));""")
        self.assertEqual(out, [0])

    def test_the_cooldown_does_not_hide_a_new_red_when_the_page_comes_back_from_a_gap(self):
        out = run_js("""
const r=[];soundWatch(red('a'));
NOW+=1000;soundWatch(red('a','b'));r.push(TONES);    // sounds
NOW+=5000;soundWatch(red('a','b','c'));r.push(TONES);      // inside the cooldown: silent
soundResync();NOW+=1000;soundWatch(red('a','b','c','d'));r.push(TONES);      // back from a gap: sounds again
console.log(JSON.stringify(r));""")
        self.assertEqual(out, [1, 1, 2])

    def test_a_broken_storage_does_not_stop_the_sound(self):
        out = run_js("""
store.get=()=>{throw new Error('blocked')};store.set=()=>{throw new Error('blocked')};
const r=[];soundWatch(red('a'));NOW+=1000;soundWatch(red('a','b'));r.push(TONES);
console.log(JSON.stringify(r));""")
        self.assertEqual(out, [1])


if __name__ == "__main__":
    unittest.main()
