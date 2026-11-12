# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The "bing bing": the server side (off by default, cooldown, never fails) and the page side (only a NEW red or a lost connection, the mute chip, the cooldown)."""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import i18n  # noqa: E402
import settings_api  # noqa: E402
import soundalert  # noqa: E402

PAGE = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
KEYS = ("sound.enabled", "sound.on_new_red", "sound.on_connection_lost", "sound.cooldown_seconds", "sound.volume", "sound.server_beep")


class ServerSide(unittest.TestCase):
    def setUp(self):
        soundalert.reset()

    def test_it_is_off_by_default_and_a_wrong_value_falls_back(self):
        self.assertFalse(soundalert.settings({})["server_beep"])
        self.assertTrue(soundalert.settings({})["enabled"])
        cfg = soundalert.settings({"sound": {"cooldown_seconds": -5, "volume": 500, "server_beep": "yes", "enabled": 0}})
        self.assertEqual((cfg["cooldown_seconds"], cfg["volume"], cfg["server_beep"], cfg["enabled"]), (30, 40, False, True))
        with mock.patch.object(soundalert, "_play") as play:
            self.assertFalse(soundalert.beep({}, "new_red"))
            play.assert_not_called()

    def test_it_sounds_for_a_new_red_and_for_a_lost_connection_and_keeps_the_cooldown(self):
        config = {"sound": {"server_beep": True, "cooldown_seconds": 30}}
        with mock.patch.object(soundalert, "_play") as play:
            self.assertTrue(soundalert.beep(config, "new_red", now=1000, wait=True))
            self.assertFalse(soundalert.beep(config, "new_red", now=1010, wait=True), "inside the cooldown")
            self.assertFalse(soundalert.beep(config, "connection_lost", now=1020, wait=True))
            self.assertTrue(soundalert.beep(config, "connection_lost", now=1031, wait=True))
            self.assertEqual(play.call_count, 2)

    def test_each_reason_has_its_own_switch_and_the_main_one_silences_all(self):
        with mock.patch.object(soundalert, "_play") as play:
            self.assertFalse(soundalert.beep({"sound": {"server_beep": True, "on_new_red": False}}, "new_red", now=1, wait=True))
            self.assertFalse(soundalert.beep({"sound": {"server_beep": True, "on_connection_lost": False}}, "connection_lost", now=100, wait=True))
            self.assertFalse(soundalert.beep({"sound": {"server_beep": True, "enabled": False}}, "new_red", now=200, wait=True))
            play.assert_not_called()

    def test_a_computer_without_the_program_does_not_fail_and_no_shell_is_used(self):
        calls = []
        with mock.patch.object(soundalert.sys, "platform", "linux"), mock.patch.object(soundalert.shutil, "which", return_value=None), mock.patch.object(soundalert.sys, "stdout", mock.Mock(isatty=lambda: False)):
            self.assertEqual(soundalert._play(lambda args: calls.append(args)), "")
        with mock.patch.object(soundalert.sys, "platform", "linux"), mock.patch.object(soundalert.shutil, "which", return_value="/usr/bin/canberra-gtk-play"):
            self.assertEqual(soundalert._play(lambda args: calls.append(args)), "canberra")
        self.assertEqual(calls, [["canberra-gtk-play", "-i", "bell"]])      # a fixed list of arguments
        with mock.patch.object(soundalert.sys, "platform", "darwin"), mock.patch.object(soundalert.shutil, "which", return_value="/usr/bin/afplay"):
            self.assertEqual(soundalert._play(lambda args: calls.append(args)), "afplay")
        self.assertEqual(calls[-1], ["afplay", "/System/Library/Sounds/Glass.aiff"])
        with mock.patch.object(soundalert.sys, "platform", "linux"), mock.patch.object(soundalert.shutil, "which", return_value="/x"):
            self.assertEqual(soundalert._play(mock.Mock(side_effect=OSError("gone"))), "")      # a program that breaks is not a failure of the monitor
        source = (HERE / "soundalert.py").read_text(encoding="utf-8")
        self.assertNotIn("shell=True", source)
        self.assertNotIn("urllib", source)


class Settings(unittest.TestCase):
    def test_the_settings_exist_with_their_texts_in_the_eight_languages(self):
        for key in KEYS:
            self.assertIn(key, settings_api.FIELDS, key)
            for lang in i18n.LANGS:
                for prefix in ("cfg.f.", "cfg.h."):
                    self.assertNotEqual(i18n.tl(lang, prefix + key), prefix + key, (lang, key))
        for lang in i18n.LANGS:
            for key in ("ui.snd_test", "ui.snd_on", "ui.snd_off", "ui.snd_chip_t"):
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))

    def test_the_server_beep_is_a_local_only_setting(self):
        import localguard
        self.assertNotIn("sound.server_beep", localguard.REMOTE_WRITABLE)


class PageSide(unittest.TestCase):
    def test_the_page_makes_two_short_tones_only_for_a_new_red_or_a_lost_connection(self):
        self.assertIn("createOscillator", PAGE)
        self.assertIn("function playTones(", PAGE)
        self.assertIn("function soundWatch(", PAGE)
        self.assertRegex(PAGE, r"SOUND\.known=new Set|SOUND\.known=keys")      # the alerts already there at the first look are remembered, not announced
        self.assertIn("SOUND.first", PAGE)
        self.assertIn("cooldown", PAGE)
        self.assertIn('id="sb-sound"', PAGE)        # the chip of the bar that unlocks the audio and says muted / on
        self.assertIn("am-sound", PAGE)             # remembered by the browser

    def test_the_page_logic_in_a_browser_new_red_only_and_cooldown(self):
        """The real functions run in a headless browser: no sound on the first look, none for an alert that was already there, one for a new one, none inside the cooldown, none when muted."""
        sys.path.insert(0, str(HERE.parent / "tools"))
        import check_overflow
        browser = check_overflow.edge()
        if not browser:
            self.skipTest("no Edge, Chrome or Chromium on this computer")
        import json
        import re
        import tempfile
        start = PAGE.index("/*SOUND-BEGIN*/")
        end = PAGE.index("/*SOUND-END*/")
        logic = PAGE[start:end]
        script = ("<!doctype html><meta charset=utf-8><pre id=overflow-report></pre><script>const store={get:k=>null,set(){}};const I18N={sound:{enabled:true,on_new_red:true,on_connection_lost:true,cooldown_seconds:30,volume:40}};"
                  "let NOW=1000;const nowMs=()=>NOW*1000;let TONES=0;const playTones=()=>{TONES++};" + logic +
                  "const out=[];const red=(...k)=>({failing:k.map(x=>({repo:x,name:'ci'})),offline:{offline:false}});"
                  "soundWatch(red('a'));out.push(TONES);"      # first look: nothing
                  "NOW=2000;soundWatch(red('a'));out.push(TONES);"      # the same alert: nothing
                  "NOW=3000;soundWatch(red('a','b'));out.push(TONES);"      # a new one: sounds
                  "NOW=3010;soundWatch(red('a','b','c'));out.push(TONES);"      # another new one inside the cooldown: silent
                  "NOW=4000;SOUND.muted=true;soundWatch(red('a','b','c','d'));out.push(TONES);"      # muted: silent
                  "NOW=5000;SOUND.muted=false;soundWatch({failing:[],offline:{offline:true}});out.push(TONES);"      # the connection is lost: sounds
                  "document.getElementById('overflow-report').textContent=JSON.stringify({ok:true,found:out})</script>")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sound.html"
            path.write_text(script, encoding="utf-8")
            found = check_overflow.measure(browser, path.as_uri(), (600, 400))
        self.assertEqual(found, [0, 0, 1, 1, 1, 2])
        self.assertTrue(re.search("x", "x") and json.dumps(found))


if __name__ == "__main__":
    unittest.main()
