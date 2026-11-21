# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The library of more than fifty sounds: one source (soundlib.py) copied into the page and the wall screens by a tool, every sound short and different, a kind of event may sound as another one of the
library (the page, the wall screens and the beep of this computer), the ambience and the tick are off by default and follow the same switches, and the eight guides name every sound."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE.parent / "tools"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import screens, settings_api  # noqa: E402
from github_actions_monitor.integrations import soundalert, soundlib  # noqa: E402
import test_650_sound_kinds as base  # noqa: E402


class Library(unittest.TestCase):
    def test_there_are_at_least_fifty_short_and_different_sounds(self):
        self.assertGreaterEqual(len(soundlib.LIBRARY), 50)
        seen = set()
        for name, (wave, notes) in soundlib.LIBRARY.items():
            self.assertIn(wave, soundlib.WAVES, name)
            self.assertLess(max(n[1] + n[2] for n in notes), 1.0, name)
            signature = json.dumps([[n[0], n[1], n[2], n[3] if len(n) > 3 else 0] for n in notes])
            self.assertNotIn(signature, seen, name)
            seen.add(signature)
        self.assertEqual(len(soundlib.free_names()), len(soundlib.LIBRARY) - len(soundlib.PAGE_KEY))

    def test_the_page_and_the_wall_carry_the_generated_copy(self):
        if not (HERE.parent / "tools" / "make_sound_library.py").is_file():
            raise unittest.SkipTest("the tools live in the repository, not in the zip of the monitor")
        import make_sound_library
        self.assertEqual(make_sound_library.main(["--check"]), 0, "run: python tools/make_sound_library.py")
        for text in (base.PAGE, base.WALL):
            self.assertEqual(base.block(text, "SND-LIBRARY").replace("\r\n", "\n"), soundlib.js_block().split("/*SND-LIBRARY-END*/")[0])

    def test_every_sound_is_named_in_the_eight_guides(self):
        for suffix in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho"):
            text = (HERE / "docs" / f"SOUNDS{suffix}.md").read_text(encoding="utf-8")
            for name in soundlib.free_names():
                self.assertIn("`%s`" % name, text, (suffix, name))
            for key in ("sound.voices", "sound.ambient", "sound.tick", "screens.sound_voices"):
                self.assertIn(key, text, (suffix, key))


class Voices(unittest.TestCase):
    def test_a_text_of_pairs_is_read_and_what_is_wrong_is_left_out(self):
        self.assertEqual(soundlib.parse_voices("new_red=coin, warning=drop"), {"new_red": "coin", "warning": "drop"})
        self.assertEqual(soundlib.parse_voices("red=coin"), {"new_red": "coin"})      # the page name of the kind is understood too
        self.assertEqual(soundlib.parse_voices("new_red=nothing,bogus=coin,info"), {})
        self.assertEqual(soundlib.parse_voices({"info": "bell", "info2": "bell"}), {"info": "bell"})
        self.assertEqual(soundlib.parse_voices(None), {})
        self.assertEqual(soundlib.merged("new_red=coin,info=bell", {"new_red": "siren"}), {"new_red": "siren", "info": "bell"})
        self.assertTrue(soundlib.valid_text(""))
        self.assertTrue(soundlib.valid_text("new_red=coin,warning=drop"))
        self.assertFalse(soundlib.valid_text("new_red=nothing"))
        self.assertFalse(soundlib.valid_text("new_red=coin,"))
        self.assertFalse(soundlib.valid_text("x" * 500))

    def test_the_settings_page_accepts_only_valid_voices(self):
        for key in ("sound.voices", "screens.sound_voices"):
            self.assertIn(key, settings_api.META)
            kind, bounds = next((row[2], row[3]) for row in settings_api.SCHEMA if row[1] == key)
            self.assertEqual(kind, "text")
            self.assertTrue(bounds.match(""))
            self.assertTrue(bounds.match("new_red=coin,warning=drop"))
            self.assertTrue(bounds.match(",".join("%s=bell" % k for k in soundlib.PAGE_KEY)))
            self.assertFalse(bounds.match("new_red=nothing"))
            self.assertFalse(bounds.match("new_red=coin,"))
            self.assertFalse(bounds.match("new_red=coin;rm"))

    def test_the_settings_of_sound_have_the_voices_and_the_two_backgrounds_off(self):
        cfg = soundalert.settings({"sound": {"voices": "new_red=coin,warning=bogus", "ambient_volume": 500, "tick_seconds": 0}})
        self.assertEqual(cfg["voices"], {"new_red": "coin"})
        self.assertFalse(cfg["ambient"])
        self.assertFalse(cfg["tick"])
        self.assertEqual((cfg["ambient_volume"], cfg["tick_seconds"]), (10, 1))      # a value out of range is the default
        on = soundalert.settings({"sound": {"ambient": True, "ambient_volume": 20, "tick": True, "tick_seconds": 5}})
        self.assertEqual((on["ambient"], on["ambient_volume"], on["tick"], on["tick_seconds"]), (True, 20, True, 5))

    def test_the_wall_screens_have_their_own_voices_and_volume(self):
        cfg = screens.settings({"screens": {"sound_voices": "new_red=siren,bad=bell,info=bogus", "sound_volume": 250}})
        self.assertEqual(cfg["sound_voices"], "new_red=siren")
        self.assertEqual(cfg["sound_volume"], 100)
        self.assertEqual(screens.settings({})["sound_volume"], 0)
        self.assertEqual(screens.settings({})["sound_voices"], "")

    def test_the_beep_of_this_computer_uses_the_voice_of_the_kind(self):
        self.assertEqual(soundalert.tones_of("new_red"), soundalert.TONES["new_red"])
        tones = soundalert.tones_of("new_red", {"new_red": "coin"})
        self.assertEqual(tones, soundlib.server_tones("coin"))
        self.assertTrue(all(37 <= hz <= 32767 and 20 <= ms <= 1200 for hz, ms in tones))
        played = []
        config = {"sound": {"enabled": True, "server_beep": True, "voices": "new_red=coin"}}
        soundalert.reset()
        with mock.patch.object(soundalert, "_play", side_effect=lambda runner=None, kinds=(), voices=None: played.append((list(kinds), voices))):
            soundalert.beep_kinds(config, ["new_red"], now=1000, wait=True)
        self.assertEqual(played, [(["new_red"], {"new_red": "coin"})])
        soundalert.reset()


@unittest.skipUnless(base.NODE, "node is needed to run the page")
class InTheBrowser(unittest.TestCase):
    def test_a_voice_changes_the_notes_and_a_wrong_one_changes_nothing(self):
        out = base.run_js("""
reset();const r={};
r.set=setVoices({new_red:"coin",warning:"nothing",bogus:"bell",live_recovered:"harp_up"});
playTones(.4,["red"],"classic");r.coin=OSC.map(o=>o.f);OSC.length=0;
playTones(.4,["warning"],"classic");r.warn=OSC.map(o=>o.f);OSC.length=0;
playTones(.4,["live"],"classic");r.live=OSC.map(o=>o.f);OSC.length=0;
setVoices({});playTones(.4,["red"],"classic");r.back=OSC.map(o=>o.f);
r.names=Object.keys(SND_PATTERNS).length;
console.log(JSON.stringify(r));""")
        self.assertEqual(out["set"], {"red": "coin", "live": "harp_up"})
        self.assertEqual(out["coin"], [988, 1319])
        self.assertEqual(out["warn"], [660, 660])
        self.assertEqual(out["live"], [392, 494, 587, 784, 988, 1175])
        self.assertEqual(out["back"], [880, 1175])
        self.assertGreaterEqual(out["names"], 50)

    def test_the_ambience_starts_only_when_asked_and_gets_rougher_with_a_red(self):
        out = base.run_js("""
reset();const r={};
r.off=ambientSet(false,.1,false);r.offOsc=OSC.length;
r.on=ambientSet(true,.1,false);r.onOsc=OSC.length;
ambientSet(true,.1,false);r.again=OSC.length;
ambientSet(true,.1,true);r.tense=AMB.tense;
r.stopped=(ambientSet(false,.1,false),AMB===null);
GESTURE=false;AUDIO=null;r.blocked=ambientSet(true,.1,false);
console.log(JSON.stringify(r));""")
        self.assertFalse(out["off"])
        self.assertEqual(out["offOsc"], 0)
        self.assertTrue(out["on"])
        self.assertEqual(out["onOsc"], 2)
        self.assertEqual(out["again"], 2)      # one pair of oscillators, never more
        self.assertTrue(out["tense"])
        self.assertTrue(out["stopped"])
        self.assertFalse(out["blocked"])

    def test_the_tick_keeps_its_pace_and_is_dry_and_short(self):
        out = base.run_js("""
reset();const r={};
r.due=[1000,1500,2000,2500,3000,6000].map(t=>sndTickDue(1,t));
SND_TICKAT=0;r.slow=[5000,7000,10000,14000,15000].map(t=>sndTickDue(5,t));
r.bad=sndTickDue(0,99999);
r.tick=playTick(.4);r.osc=OSC.map(o=>[o.type,o.f]);
console.log(JSON.stringify(r));""")
        self.assertEqual(out["due"], [True, False, True, False, True, True])
        self.assertEqual(out["slow"], [True, False, True, False, True])
        self.assertFalse(out["bad"])
        self.assertTrue(out["tick"])
        self.assertEqual(out["osc"], [["square", 1900]])

    def test_the_page_follows_the_switches_for_the_ambience_and_the_tick(self):
        out = base.run_js("""
reset();const r={};
I18N.sound={enabled:true,cooldown_seconds:30,volume:40,ambient:true,tick:true,tick_seconds:1,voices:{new_red:"coin"}};
r.cfg=soundCfg();r.amb=soundAmbience();r.tick=soundTicks();
SOUND.muted=true;r.ambMuted=soundAmbience();r.ambStopped=AMB===null;NOW+=5000;r.tickMuted=soundTicks();
SOUND.muted=false;I18N.sound={enabled:true,volume:40};r.defaultAmb=soundAmbience();NOW+=5000;r.defaultTick=soundTicks();
console.log(JSON.stringify(r));""")
        self.assertTrue(out["cfg"]["ambient"])
        self.assertTrue(out["amb"])
        self.assertTrue(out["tick"])
        self.assertFalse(out["ambMuted"])
        self.assertTrue(out["ambStopped"])
        self.assertFalse(out["tickMuted"])
        self.assertFalse(out["defaultAmb"])      # off by default
        self.assertFalse(out["defaultTick"])


if __name__ == "__main__":
    unittest.main()
