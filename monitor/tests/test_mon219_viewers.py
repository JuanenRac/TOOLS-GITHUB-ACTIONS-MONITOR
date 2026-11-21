# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Polling that knows whether anybody is looking (`modes.idle_minutes`, off by default): a page, a wall screen or a live stream asking for data is a look; after that many minutes without one the cycle stretches to
the cold interval, but never while an alert can leave the computer; the start counts as a look; a hidden tab or window stops asking; /api/health says what is going on."""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am, settings_api, viewers  # noqa: E402

T0 = 1_000_000.0
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
WALL = (HERE / "assets" / "static" / "screens.html").read_text(encoding="utf-8")


class Fresh(unittest.TestCase):
    def setUp(self):
        viewers.reset()


class TheSetting(Fresh):
    def test_it_is_off_by_default_and_a_wrong_value_is_the_default(self):
        self.assertEqual(viewers.settings({}), {"idle_minutes": 0})
        for bad in (-1, 1441, "ten", True, 1.5, None):
            self.assertEqual(viewers.settings({"modes": {"idle_minutes": bad}}), {"idle_minutes": 0}, bad)
        self.assertEqual(viewers.settings({"modes": {"idle_minutes": 10}}), {"idle_minutes": 10})
        self.assertEqual(am.DEFAULTS["modes"]["idle_minutes"], 0)
        kind, bounds = next((row[2], row[3]) for row in settings_api.SCHEMA if row[1] == "modes.idle_minutes")
        self.assertEqual((kind, tuple(bounds)), ("int", (0, 1440)))
        for lang in i18n.LANGS:
            self.assertNotEqual(i18n.tl(lang, "cfg.f.modes.idle_minutes"), "cfg.f.modes.idle_minutes", lang)
            self.assertNotEqual(i18n.tl(lang, "cfg.h.modes.idle_minutes"), "cfg.h.modes.idle_minutes", lang)


class TheLooks(Fresh):
    def test_only_what_a_page_a_screen_or_a_stream_asks_for_is_a_look(self):
        viewers.touch("/api/health", T0)
        viewers.touch("/api/alerts", T0)
        viewers.touch("/metrics", T0)
        self.assertEqual(viewers.idle_seconds(T0 + 100), 0, "the start counts as a look, and nothing else touched")
        for path in ("/api/data", "/api/data?account=x", "/api/screens/data?screen=fleet", "/api/live-events/stream"):
            viewers.reset()
            viewers.idle_seconds(T0)
            viewers.touch(path, T0 + 50)
            self.assertEqual(viewers.idle_seconds(T0 + 80), 30, path)

    def test_the_start_of_the_monitor_is_a_look(self):
        self.assertEqual(viewers.idle_seconds(T0), 0)
        self.assertEqual(viewers.idle_seconds(T0 + 90), 90)


class TheColdPace(Fresh):
    ON = {"modes": {"idle_minutes": 10}}

    def test_nothing_changes_while_the_setting_is_off(self):
        viewers.idle_seconds(T0)
        self.assertFalse(viewers.cold({}, T0 + 10 ** 6))
        self.assertEqual(viewers.stretch({}, 45, 600, T0 + 10 ** 6), 45)

    def test_after_the_minutes_without_a_look_the_cycle_stretches_and_a_look_brings_it_back(self):
        viewers.idle_seconds(T0)
        self.assertFalse(viewers.cold(self.ON, T0 + 599))
        self.assertTrue(viewers.cold(self.ON, T0 + 600))
        self.assertEqual(viewers.stretch(self.ON, 45, 600, T0 + 900), 600)
        self.assertEqual(viewers.stretch(self.ON, 45, 600, T0 + 100), 45)
        viewers.touch("/api/data", T0 + 1000)
        self.assertFalse(viewers.cold(self.ON, T0 + 1100))
        self.assertEqual(viewers.stretch(self.ON, 45, 600, T0 + 1100), 45)

    def test_it_never_stretches_a_pause_that_is_already_longer_or_with_a_wrong_cold_value(self):
        viewers.idle_seconds(T0)
        self.assertEqual(viewers.stretch(self.ON, 900, 600, T0 + 10 ** 5), 900)
        self.assertEqual(viewers.stretch(self.ON, 45, None, T0 + 10 ** 5), 45)
        self.assertEqual(viewers.stretch(self.ON, 45, True, T0 + 10 ** 5), 45)

    def test_nothing_that_guards_the_fleet_goes_cold(self):
        viewers.idle_seconds(T0)
        cases = {"webhook": {"webhook": {"enabled": True}}, "ai_alerts": {"ai_alerts": {"enabled": True}}, "chatops": {"chatops": {"enabled": True}},
                 "server_beep": {"sound": {"enabled": True, "server_beep": True}}, "notify": {"notify": {"enabled": True}}}
        for name, extra in cases.items():
            config = {**self.ON, **extra}
            self.assertIn(name, viewers.exceptions(config), name)
            self.assertFalse(viewers.cold(config, T0 + 10 ** 6), name)
            self.assertEqual(viewers.stretch(config, 45, 600, T0 + 10 ** 6), 45, name)
        self.assertEqual(viewers.exceptions({"sound": {"enabled": False, "server_beep": True}}), [], "the beep is off with the sounds")
        self.assertEqual(viewers.exceptions(am.DEFAULTS), [], "by default nothing keeps it awake")

    def test_a_check_that_fails_never_stops_the_cycle(self):
        viewers.idle_seconds(T0)
        self.assertEqual(viewers.stretch("not a config", 45, 600, T0 + 10 ** 6), 45)
        self.assertEqual(viewers.exceptions("not a config"), [])


class TheHealthAndThePages(Fresh):
    def test_health_says_what_is_going_on(self):
        document = am.health_payload()
        self.assertEqual(sorted(document["viewers"]), ["aware", "cold", "idle_minutes", "idle_seconds", "kept_by"])
        self.assertFalse(document["viewers"]["aware"])
        self.assertFalse(document["viewers"]["cold"])
        public = viewers.public({"modes": {"idle_minutes": 5}, "webhook": {"enabled": True}}, T0)
        self.assertEqual((public["aware"], public["idle_minutes"], public["kept_by"], public["cold"]), (True, 5, ["webhook"], False))
        json.dumps(public)

    def test_the_pages_know_whether_to_stop_asking_when_hidden(self):
        self.assertIn("I18N.viewer_aware&&document.hidden", PAGE)
        self.assertRegex(WALL, r"if\(D\.viewer_aware&&document\.hidden\)\{STATE\.timer=setTimeout\(load,30000\);return\}")
        self.assertIn('document.addEventListener("visibilitychange",()=>{if(!document.hidden&&D.viewer_aware', WALL)
        self.assertRegex(PAGE, r'visibilitychange",\(\)=>\{if\(!document\.hidden\)tick\(true\)\}', "and the main page asks at once when it comes back")
        text = Path(am.__file__).read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r'data\["viewer_aware"\] = bool\(viewers\.settings\(', text)), 2, "the page and the wall screens both receive the flag")
        self.assertIn("viewers.touch(self.path)", text)
        self.assertIn("viewers.stretch(config", text)


if __name__ == "__main__":
    unittest.main()
