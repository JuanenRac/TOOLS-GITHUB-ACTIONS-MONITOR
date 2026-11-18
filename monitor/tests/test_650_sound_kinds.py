# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""One sound for each kind of event: the patterns differ, every kind is forced in the real functions of the page (run in node with a fake AudioContext), what the browser blocks is kept and played later,
a burst is limited and ordered, a kind keeps its pause, the switches and the quiet hours silence, and the wall screens carry the same sounds."""
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
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.integrations import soundalert  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
WALL = (HERE / "assets" / "static" / "screens.html").read_text(encoding="utf-8")
NODE = shutil.which("node")
KINDS = ["red", "sentinel", "stuck", "score", "conn", "warning", "resolved", "report", "lesson", "info", "live"]
SWITCH = {"red": "new_red", "conn": "connection_lost", "score": "score_drop", "live": "live_recovered"}


def block(text, name):
    return text[text.index(f"/*{name}-BEGIN*/"):text.index(f"/*{name}-END*/")]


PRELUDE = """
let NOW=Date.UTC(2026,0,5,12,0,0);const nowMs=()=>NOW;const MEM={};
const store={get:k=>(k in MEM?MEM[k]:null),set:(k,v)=>{MEM[k]=v}};
const I18N={sound:{enabled:true,cooldown_seconds:30,volume:40}};
let GESTURE=false;const OSC=[];
class FakeCtx{constructor(){this.state="suspended";this.currentTime=0;this.destination={}}
  resume(){if(GESTURE)this.state="running";return Promise.resolve()}
  createOscillator(){const o={type:"",frequency:{setValueAtTime(f){o.f=f},linearRampToValueAtTime(f){o.to=f}},connect(){},start(){OSC.push(o)},stop(){}};return o}
  createGain(){return {gain:{setValueAtTime(){},exponentialRampToValueAtTime(){}},connect(){}}}}
const window={AudioContext:FakeCtx};
"""
HARNESS = """
const PLAYS=[];const realPlay=playTones;playTones=function(v,k,t){const n=OSC.length,r=realPlay(v,k,t);PLAYS.push({k:[].concat(k),ok:r,theme:t,freqs:OSC.slice(n).map(o=>o.f)});return r};
function reset(){Object.assign(SOUND,{first:true,known:new Set(),lastAt:0,kindAt:{},queue:[],conn:null,lost:false,al:null,rep:null,les:null,muted:false});
  Object.keys(MEM).forEach(k=>delete MEM[k]);PLAYS.length=0;OSC.length=0;GESTURE=true;AUDIO=null;NOW=Date.UTC(2026,0,5,12,0,0);I18N.sound={enabled:true,cooldown_seconds:30,volume:40}}
const played=()=>PLAYS.filter(p=>p.ok!==false).map(p=>p.k.join("+"));
const alertsOf=(...a)=>({alerts:a.map(([id,code,level,muted])=>({id:id,code:code,level:level,muted_until:muted||null}))});
"""


def run_js(body):
    code = PRELUDE + block(PAGE, "SOUNDS") + block(PAGE, "SOUND") + HARNESS + body
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.js"
        path.write_text(code, encoding="utf-8")
        out = subprocess.run([NODE, str(path)], capture_output=True, text=True, timeout=60, check=False)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


class Static(unittest.TestCase):
    def test_every_kind_has_a_pattern_and_the_patterns_are_all_different(self):
        shared = block(PAGE, "SOUNDS")
        names = re.findall(r"^\s{2}(\w+):\{w:", shared, re.M)
        self.assertEqual(sorted(names), sorted(KINDS))
        notes = {}
        for name in names:
            body = re.search(r"^\s{2}" + name + r":\{w:\"\w+\",n:(\[\[.*?\]\])\}", shared, re.M).group(1)
            notes[name] = json.loads(re.sub(r"(?<![\d])\.(\d)", r"0.\1", body))
        signatures = {json.dumps([[n[0], n[1], n[2], n[3] if len(n) > 3 else 0] for n in v]) for v in notes.values()}
        self.assertEqual(len(signatures), len(KINDS), "two kinds sound the same")
        # the ear tells them apart by the number of notes, the pitch and the rhythm: no two kinds share both the count and the first pitch
        self.assertEqual(len({(len(v), v[0][0]) for v in notes.values()}), len(KINDS))
        for name, v in notes.items():
            self.assertLess(max(n[1] + n[2] for n in v), 1.0, name)      # short: nothing sounds for a second or more

    def test_the_wall_screens_carry_the_same_block_of_sounds(self):
        self.assertEqual(block(PAGE, "SOUNDS").replace("\r\n", "\n"), block(WALL, "SOUNDS").replace("\r\n", "\n"))
        for needle in ("playTones(", "SND_PATTERNS", "beep([\"resolved\"])", "beep([\"conn\"])", "alertSound(", "D.sound"):
            self.assertIn(needle, WALL, needle)

    def test_the_settings_have_a_switch_per_kind_a_theme_and_quiet_hours_in_eight_languages(self):
        keys = [f"sound.on_{SWITCH.get(k, k)}" for k in KINDS] + ["sound.theme", "sound.quiet_enabled", "sound.quiet_from_hour", "sound.quiet_to_hour"]
        for key in keys:
            self.assertIn(key, settings_api.FIELDS, key)
            for lang in i18n.LANGS:
                for prefix in ("cfg.f.", "cfg.h."):
                    self.assertNotEqual(i18n.tl(lang, prefix + key), prefix + key, (lang, key))
        for lang in i18n.LANGS:
            for kind in KINDS:
                self.assertNotEqual(i18n.tl(lang, "ui.snd_k_" + kind), "ui.snd_k_" + kind, (lang, kind))
            self.assertNotEqual(i18n.tl(lang, "ui.snd_tests"), "ui.snd_tests", lang)
        self.assertEqual(sorted(k for k in soundalert.KINDS), sorted(SWITCH.get(k, k) for k in KINDS))

    def test_the_defaults_are_the_conservative_ones_and_wrong_values_fall_back(self):
        cfg = soundalert.settings({})
        self.assertEqual((cfg["theme"], cfg["quiet_enabled"], cfg["quiet_from_hour"], cfg["quiet_to_hour"], cfg["server_beep"]), ("classic", False, 22, 7, False))
        bad = soundalert.settings({"sound": {"theme": "loud", "quiet_from_hour": 99, "quiet_to_hour": "x", "quiet_enabled": "yes", "on_report": 1}})
        self.assertEqual((bad["theme"], bad["quiet_from_hour"], bad["quiet_to_hour"], bad["quiet_enabled"], bad["on_report"]), ("classic", 22, 7, False, True))
        good = soundalert.settings({"sound": {"theme": "soft", "quiet_enabled": True, "quiet_from_hour": 0, "quiet_to_hour": 23, "on_lesson": False}})
        self.assertEqual((good["theme"], good["quiet_enabled"], good["quiet_from_hour"], good["quiet_to_hour"], good["on_lesson"]), ("soft", True, 0, 23, False))

    def test_the_page_gets_the_settings_and_has_a_button_to_test_each_kind(self):
        for needle in ('id="snd-kinds"', "function soundTest(", "function soundKindsPaint(", "SND_PRI.forEach", "soundAlerts(ALERTS)", "soundReports(REP)", "soundLessons(LESS)", "visibilitychange", '"touchend"'):
            self.assertIn(needle, PAGE, needle)


@unittest.skipUnless(NODE, "no node on this computer")
class Behaviour(unittest.TestCase):
    def test_every_kind_is_forced_by_its_own_event_and_asks_for_its_own_sound(self):
        out = run_js("""
const res={};
const first=(f)=>{reset();f(0);NOW+=60000;f(1);return played()};
res.red=first(i=>soundWatch({failing:i?[{repo:'a',name:'ci'}]:[],offline:{offline:false}}));
res.resolved=first(i=>soundWatch({failing:i?[]:[{repo:'a',name:'ci'}],offline:{offline:false}}));
res.conn=first(i=>soundWatch({failing:[],offline:{offline:!!i}}));
res.live=first(i=>soundWatch({failing:[],offline:{offline:!i}}));
res.sentinel=first(i=>soundAlerts(alertsOf(...(i?[['s1','security.secret','error']]:[]))));
res.stuck=first(i=>soundAlerts(alertsOf(...(i?[['t1','ci.stuck','error']]:[]))));
res.score=first(i=>soundAlerts(alertsOf(...(i?[['sc','score.dropped','warning']]:[]))));
res.warning=first(i=>soundAlerts(alertsOf(...(i?[['w1','ci.pending_sign','warning']]:[]))));
res.info=first(i=>soundAlerts(alertsOf(...(i?[['i1','ci.upstream_release','info']]:[]))));
res.report=first(i=>soundReports({workflow_hygiene:{enabled:true,repos:i?[{repo:'r',findings:[{rule:'x'}]}]:[]}}));
res.lesson=first(i=>soundLessons({enabled:true,categories:i?[{category:'lint',recurring:false}]:[],apply_now:[]}));
console.log(JSON.stringify(res));""")
        for kind in KINDS:
            self.assertEqual(out[kind], [kind], kind)

    def test_each_kind_plays_its_own_notes_and_the_soft_theme_keeps_the_rhythm(self):
        out = run_js("""
const res={};
for(const k of Object.keys(SND_PATTERNS)){reset();AUDIO=null;const a=playTones(.4,[k],'classic'),n=OSC.length,types=OSC.map(o=>o.type);OSC.length=0;AUDIO=null;const b=playTones(.4,[k],'soft');
  res[k]={ok:[a,b],count:[n,OSC.length],classic:SND_PATTERNS[k].n.map(x=>x[0]),soft:OSC.map(o=>o.f),types:types,softTypes:OSC.map(o=>o.type)};OSC.length=0}
console.log(JSON.stringify(res));""")
        sigs = set()
        for kind, r in out.items():
            self.assertEqual(r["ok"], [True, True], kind)
            self.assertEqual(r["count"][0], r["count"][1], kind)      # the same notes in both themes
            self.assertEqual([round(f * 0.75, 3) for f in r["classic"]], [round(f, 3) for f in r["soft"]], kind)
            self.assertEqual(set(r["softTypes"]), {"sine"}, kind)
            sigs.add(tuple(r["classic"]))
        self.assertEqual(len(sigs), len(KINDS))

    def test_what_the_browser_blocks_is_kept_and_plays_after_the_click_and_a_stale_one_is_dropped(self):
        out = run_js("""
reset();GESTURE=false;const r={};
soundWatch({failing:[],offline:{offline:false}});NOW+=1000;soundWatch({failing:[{repo:'a',name:'ci'}],offline:{offline:false}});
r.blocked=played();r.queued=SOUND.queue.map(q=>q.k);
NOW+=5000;soundDrain();r.stillBlocked=played();
GESTURE=true;NOW+=2000;soundDrain();r.afterClick=played();r.left=SOUND.queue.length;
reset();GESTURE=false;soundSay(['red']);NOW+=11*60000;GESTURE=true;soundDrain();r.stale=played();
console.log(JSON.stringify(r));""")
        self.assertEqual(out["blocked"], [])
        self.assertEqual(out["queued"], ["red"])
        self.assertEqual(out["stillBlocked"], [])
        self.assertEqual(out["afterClick"], ["red"])
        self.assertEqual(out["left"], 0)
        self.assertEqual(out["stale"], [], "old news is not announced")

    def test_a_burst_is_limited_and_ordered_a_kind_keeps_its_pause_and_two_bursts_do_not_overlap(self):
        out = run_js("""
const r={};reset();
soundSay(['info','report','warning','red','stuck','sentinel']);r.burst=played();r.waiting=SOUND.queue.map(q=>q.k);
NOW+=500;soundDrain();r.tooSoon=played().length;
NOW+=4000;soundDrain();r.second=played().slice(1);
reset();soundSay(['red']);NOW+=10000;soundSay(['red']);r.sameKindInPause=played();
NOW+=25000;soundSay(['red']);r.afterPause=played();
reset();soundSay(['red']);NOW+=100;soundSay(['report']);r.gap=played();NOW+=2000;soundDrain();r.gapLater=played();
console.log(JSON.stringify(r));""")
        self.assertEqual(out["burst"], ["red+sentinel+stuck"])
        self.assertEqual(out["waiting"], ["warning", "report", "info"])
        self.assertEqual(out["tooSoon"], 1)
        self.assertEqual(out["second"], ["warning+report+info"])
        self.assertEqual(out["sameKindInPause"], ["red"])
        self.assertEqual(out["afterPause"], ["red", "red"])
        self.assertEqual(out["gap"], ["red"])
        self.assertEqual(out["gapLater"], ["red", "report"])

    def test_switches_the_mute_chip_and_the_quiet_hours_silence_a_kind(self):
        out = run_js("""
const r={};
reset();I18N.sound.on_report=false;soundSay(['report','lesson']);r.kindOff=played();
reset();I18N.sound.enabled=false;soundSay(['red']);r.allOff=played();
reset();SOUND.muted=true;soundSay(['red']);r.muted=played();
const h=new Date(NOW).getHours();
reset();Object.assign(I18N.sound,{quiet_enabled:true,quiet_from_hour:h,quiet_to_hour:(h+1)%24});soundSay(['red']);r.quiet=played();
reset();Object.assign(I18N.sound,{quiet_enabled:true,quiet_from_hour:(h+23)%24,quiet_to_hour:(h+2)%24});soundSay(['red']);r.quietAcrossMidnight=played();
reset();Object.assign(I18N.sound,{quiet_enabled:true,quiet_from_hour:(h+1)%24,quiet_to_hour:(h+2)%24});soundSay(['red']);r.outsideQuiet=played();
reset();Object.assign(I18N.sound,{quiet_enabled:true,quiet_from_hour:5,quiet_to_hour:5});soundSay(['red']);r.sameHours=played();
reset();Object.assign(I18N.sound,{quiet_enabled:false,quiet_from_hour:h,quiet_to_hour:(h+1)%24});soundSay(['red']);r.quietOff=played();
reset();I18N.sound.theme='soft';soundSay(['red']);r.theme=PLAYS[0].theme;
console.log(JSON.stringify(r));""")
        self.assertEqual(out["kindOff"], ["lesson"])
        self.assertEqual(out["allOff"], [])
        self.assertEqual(out["muted"], [])
        self.assertEqual(out["quiet"], [])
        self.assertEqual(out["quietAcrossMidnight"], [])
        self.assertEqual(out["outsideQuiet"], ["red"])
        self.assertEqual(out["sameHours"], ["red"])
        self.assertEqual(out["quietOff"], ["red"])
        self.assertEqual(out["theme"], "soft")

    def test_the_kind_of_an_alert_follows_its_code_and_a_silenced_or_known_alert_is_quiet(self):
        out = run_js("""
const r={};
const kind=(code,level)=>soundKindOf({code:code,level:level});
r.kinds=[['ci.red','error'],['score.dropped','critical'],['ci.stuck','error'],['ci.ghost_queue','info'],['runner.queue','warning'],['runner.selfhosted_down','error'],['security.secret','warning'],['system.credential_blind','critical'],
  ['collab.issue.critical','error'],['collab.pr.conflict','warning'],['ci.pending_sign','warning'],['ci.upstream_red','info'],['x.y','']].map(x=>kind(x[0],x[1]));
reset();soundAlerts(alertsOf());NOW+=60000;soundAlerts(alertsOf(['m','security.secret','error','2099-01-01']));r.muted=played();
reset();soundAlerts(alertsOf(['k','ci.stuck','error']));NOW+=60000;soundAlerts(alertsOf(['k','ci.stuck','error']));r.known=played();
reset();soundAlerts(alertsOf());NOW+=60000;soundAlerts(alertsOf(['r','ci.red','error']));r.ciRedIsNotCountedTwice=played();
reset();soundAlerts(alertsOf(['k','ci.stuck','error'],['w','ci.pending_sign','warning']));NOW+=60000;soundAlerts(alertsOf(['w','ci.pending_sign','warning']));r.gone=played();
reset();soundAlerts(alertsOf(['w','ci.pending_sign','warning']));NOW+=60000;soundAlerts(alertsOf());r.warningGone=played();
reset();soundAlerts(alertsOf(['k','ci.stuck','error']));const saved=Object.assign({},MEM);const keep=SOUND.al;SOUND.al=null;NOW+=60000;soundAlerts(alertsOf(['k','ci.stuck','error'],['n','security.secret','error']));r.reloadKeepsBaseline=played();
console.log(JSON.stringify(r));""")
        self.assertEqual(out["kinds"], ["red", "score", "stuck", "stuck", "stuck", "stuck", "sentinel", "sentinel", "sentinel", "warning", "warning", "info", "info"])
        self.assertEqual(out["muted"], [])
        self.assertEqual(out["known"], [])
        self.assertEqual(out["ciRedIsNotCountedTwice"], [])
        self.assertEqual(out["gone"], ["resolved"])
        self.assertEqual(out["warningGone"], [])
        self.assertEqual(out["reloadKeepsBaseline"], ["sentinel"])


if __name__ == "__main__":
    unittest.main()
