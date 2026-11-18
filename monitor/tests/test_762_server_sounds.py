# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The beep of this computer has the kinds of event of the page, each with its own pattern, and the sound of the live view that is back exists in the page, in the wall screens and on this computer, with its
switch (on by default, inside the beep that is off by default) and the quiet hours."""
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_650_sound_kinds as page_sounds  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.integrations import soundalert  # noqa: E402

ON = {"sound": {"server_beep": True, "cooldown_seconds": 0}}
PAGE = page_sounds.PAGE
WALL = page_sounds.WALL


class TheKinds(unittest.TestCase):
    def test_every_kind_of_the_page_has_one_of_this_computer_and_each_sounds_different(self):
        self.assertEqual(sorted(soundalert.KINDS), sorted(page_sounds.SWITCH.get(k, k) for k in page_sounds.KINDS))
        for table in (soundalert.TONES, soundalert.MAC_SOUNDS, soundalert.LINUX_SOUNDS):
            self.assertEqual(sorted(table), sorted(soundalert.KINDS))
        self.assertEqual(sorted(soundalert.PRIORITY), sorted(soundalert.KINDS))
        self.assertEqual(len({tuple(v) for v in soundalert.TONES.values()}), len(soundalert.KINDS), "two kinds sound the same")
        self.assertEqual(len(set(soundalert.MAC_SOUNDS.values())), len(soundalert.MAC_SOUNDS))
        for kind, tones in soundalert.TONES.items():
            self.assertLess(sum(length for _hz, length in tones), 1000, kind)      # short: nothing sounds for a second
            self.assertTrue(all(37 <= hz <= 32767 for hz, _length in tones), kind)      # winsound.Beep accepts 37..32767 Hz

    def test_the_sound_of_the_live_view_back_is_the_one_new_kind_and_it_rises(self):
        self.assertIn("live_recovered", soundalert.KINDS)
        notes = [hz for hz, _length in soundalert.TONES["live_recovered"]]
        self.assertEqual(notes, sorted(notes))
        self.assertTrue(soundalert.settings({})["on_live_recovered"], "on by default, inside the beep that is off by default")
        self.assertFalse(soundalert.settings({})["server_beep"])
        self.assertFalse(soundalert.settings({"sound": {"on_live_recovered": False}})["on_live_recovered"])

    def test_the_kind_of_an_alert_is_the_same_as_the_kind_the_page_gives_it(self):
        cases = [("ci.red", "error", "new_red"), ("score.dropped", "critical", "score_drop"), ("ci.stuck", "error", "stuck"), ("ci.ghost_queue", "info", "stuck"), ("runner.queue", "warning", "stuck"),
                 ("runner.selfhosted_down", "error", "stuck"), ("security.secret", "warning", "sentinel"), ("system.credential_blind", "critical", "sentinel"), ("collab.issue.critical", "error", "sentinel"),
                 ("collab.pr.conflict", "warning", "warning"), ("ci.pending_sign", "warning", "warning"), ("ci.dependabot_failed", "warning", "warning"), ("ci.upstream_red", "info", "info"),
                 ("ci.copilot_activity", "info", "info"), ("x.y", "", "info")]
        for code, level, kind in cases:
            self.assertEqual(soundalert.kind_of(code, level), kind, code)


class TheSwitches(unittest.TestCase):
    def setUp(self):
        soundalert.reset()

    def test_a_kind_sounds_only_by_its_own_switch_and_only_with_the_beep_on(self):
        for kind in soundalert.KINDS:
            self.assertTrue(soundalert.allowed(soundalert.settings(ON), kind, now=1000 + 100 * soundalert.KINDS.index(kind)), kind)
            self.assertFalse(soundalert.allowed(soundalert.settings({"sound": {"server_beep": True, f"on_{kind}": False}}), kind, now=1), kind)
            self.assertFalse(soundalert.allowed(soundalert.settings({"sound": {f"on_{kind}": True}}), kind, now=1), "the beep of this computer is off by default")
        self.assertFalse(soundalert.allowed(soundalert.settings(ON), "nothing", now=1))
        self.assertFalse(soundalert.allowed(soundalert.settings({"sound": {"server_beep": True, "enabled": False}}), "info", now=1))

    def test_the_quiet_hours_silence_this_computer_too_and_may_cross_midnight(self):
        now = time.time()
        hour = time.localtime(now).tm_hour
        inside = {"sound": {**ON["sound"], "quiet_enabled": True, "quiet_from_hour": hour, "quiet_to_hour": (hour + 1) % 24}}
        across = {"sound": {**ON["sound"], "quiet_enabled": True, "quiet_from_hour": (hour + 23) % 24, "quiet_to_hour": (hour + 2) % 24}}
        outside = {"sound": {**ON["sound"], "quiet_enabled": True, "quiet_from_hour": (hour + 1) % 24, "quiet_to_hour": (hour + 2) % 24}}
        same = {"sound": {**ON["sound"], "quiet_enabled": True, "quiet_from_hour": 5, "quiet_to_hour": 5}}
        self.assertFalse(soundalert.allowed(soundalert.settings(inside), "new_red", now=now))
        self.assertFalse(soundalert.allowed(soundalert.settings(across), "new_red", now=now))
        self.assertTrue(soundalert.allowed(soundalert.settings(outside), "new_red", now=now))
        self.assertTrue(soundalert.allowed(soundalert.settings(same), "new_red", now=now + 400))

    def test_a_burst_has_the_most_serious_first_at_most_three_and_one_cooldown(self):
        played = []
        with mock.patch.object(soundalert, "_play", side_effect=lambda runner=None, kinds=(): played.append(list(kinds))):
            sounded = soundalert.beep_kinds(ON, ["info", "live_recovered", "warning", "new_red", "stuck"], now=10, wait=True)
            self.assertEqual(sounded, ["new_red", "stuck", "warning"])
            self.assertEqual(played, [["new_red", "stuck", "warning"]])
            soundalert.reset()
            config = {"sound": {"server_beep": True, "cooldown_seconds": 30, "on_new_red": False}}
            self.assertEqual(soundalert.beep_kinds(config, ["new_red"], now=1000, wait=True), [], "a kind that is switched off never sounds")
            self.assertEqual(soundalert.beep_kinds(config, ["info"], now=1000, wait=True), ["info"])
            self.assertEqual(soundalert.beep_kinds(config, ["info"], now=1001, wait=True), [], "inside the cooldown")
            self.assertEqual(soundalert.beep_kinds(config, ["live_recovered"], now=1040, wait=True), ["live_recovered"])
        self.assertEqual(soundalert.beep_kinds({}, ["new_red"], now=1000, wait=True), [], "off by default")

    def test_the_old_calls_still_work(self):
        with mock.patch.object(soundalert, "_play") as play:
            self.assertTrue(soundalert.beep(ON, "new_red", now=5, wait=True))
            self.assertTrue(soundalert.beep(ON, "connection_lost", now=6, wait=True))
            self.assertFalse(soundalert.beep(ON, "bogus", now=7, wait=True))
            self.assertEqual(play.call_count, 2)


class TheTones(unittest.TestCase):
    def test_each_kind_asks_for_its_own_system_sound(self):
        for system, which, table, expected in (("darwin", "/usr/bin/afplay", soundalert.MAC_SOUNDS, lambda v: f"/System/Library/Sounds/{v}.aiff"), ("linux", "/usr/bin/canberra-gtk-play", soundalert.LINUX_SOUNDS, lambda v: v)):
            seen = []
            with mock.patch.object(soundalert.sys, "platform", system), mock.patch.object(soundalert.shutil, "which", return_value=which):
                for kind in soundalert.KINDS:
                    soundalert._play(lambda args: seen.append(args), (kind,))
            self.assertEqual([a[-1] for a in seen], [expected(table[k]) for k in soundalert.KINDS], system)
            self.assertEqual(len({tuple(a) for a in seen}), len(soundalert.KINDS), f"{system}: each kind a different call")

    def test_a_burst_plays_its_kinds_one_after_the_other(self):
        seen = []
        with mock.patch.object(soundalert.sys, "platform", "linux"), mock.patch.object(soundalert.shutil, "which", return_value="/x"):
            self.assertEqual(soundalert._play(lambda args: seen.append(args), ("new_red", "info")), "canberra")
        self.assertEqual([a[-1] for a in seen], [soundalert.LINUX_SOUNDS["new_red"], soundalert.LINUX_SOUNDS["info"]])

    def test_windows_plays_the_tones_of_the_kind(self):
        beeps = []
        fake = mock.Mock(Beep=lambda hz, ms: beeps.append((hz, ms)), MessageBeep=lambda: None)
        with mock.patch.object(soundalert.sys, "platform", "win32"), mock.patch.dict(sys.modules, {"winsound": fake}), mock.patch.object(soundalert.time, "sleep"):
            self.assertEqual(soundalert._play(None, ("live_recovered",)), "winsound")
        self.assertEqual(beeps, list(soundalert.TONES["live_recovered"]))

    def test_an_unknown_kind_falls_back_to_the_classic_one(self):
        seen = []
        with mock.patch.object(soundalert.sys, "platform", "linux"), mock.patch.object(soundalert.shutil, "which", return_value="/x"):
            soundalert._play(lambda args: seen.append(args), ("nonsense",))
        self.assertEqual(seen[0][-1], soundalert.LINUX_SOUNDS["new_red"])


class TheWatch(unittest.TestCase):
    def alert(self, id, code, level, muted=None):
        return {"id": id, "code": code, "level": level, "muted_until": muted}

    def test_the_first_look_only_remembers_and_a_new_alert_sounds_as_its_kind(self):
        watch = soundalert.Watch()
        self.assertEqual(watch.look([self.alert("a", "ci.pending_sign", "warning")]), [])
        self.assertEqual(watch.look([self.alert("a", "ci.pending_sign", "warning"), self.alert("b", "security.secret", "error"), self.alert("c", "ci.upstream_release", "info")]), ["sentinel", "info"])
        self.assertEqual(watch.look([self.alert("a", "ci.pending_sign", "warning"), self.alert("b", "security.secret", "error"), self.alert("c", "ci.upstream_release", "info")]), [])

    def test_a_silenced_alert_and_the_reds_of_the_ci_never_sound_and_a_serious_one_that_is_gone_is_solved(self):
        watch = soundalert.Watch()
        watch.look([self.alert("s", "ci.stuck", "error"), self.alert("w", "ci.pending_sign", "warning")])
        self.assertEqual(watch.look([self.alert("w", "ci.pending_sign", "warning"), self.alert("m", "security.secret", "error", "2099-01-01"), self.alert("r", "ci.red", "error")]), ["resolved"])
        self.assertEqual(watch.look([]), [], "a warning that goes away is not announced")
        self.assertEqual(watch.look(None), [])


class TheReportsAndLessons(unittest.TestCase):
    def test_the_keys_are_the_ones_the_page_builds_and_only_what_is_on_counts(self):
        reports = {"workflow_hygiene": {"enabled": True, "repos": [{"repo": "r", "findings": [{"rule": "x"}, {"rule": "y"}]}]}, "release_view": {"enabled": True, "repos": [{"repo": "a", "state": "blocked"}, {"repo": "b", "state": "ready"}]},
                   "supply_chain": {"enabled": True, "repos": [{"repo": "c", "tag": "v1", "sbom": True, "signature": False}, {"repo": "d", "tag": "v2", "sbom": True, "signature": True}]},
                   "queue": {"enabled": True, "groups": {"linux": {}}}}
        self.assertEqual(soundalert.report_keys(reports), {"h|r|x", "h|r|y", "r|a", "s|c|v1", "q|linux"})
        off = {name: {**part, "enabled": False} for name, part in reports.items()}
        self.assertEqual(soundalert.report_keys(off), set())
        self.assertEqual(soundalert.report_keys(None), set())
        lessons = {"enabled": True, "categories": [{"category": "lint", "recurring": True}, {"category": "ci", "recurring": False}], "apply_now": [{"category": "lint"}]}
        self.assertEqual(soundalert.lesson_keys(lessons), {"lint|r", "ci|n", "now|lint"})
        self.assertEqual(soundalert.lesson_keys({**lessons, "enabled": False}), set())
        self.assertEqual(soundalert.lesson_keys("bad"), set())

    def test_the_first_look_only_remembers_and_a_new_key_is_one_sound_of_its_kind(self):
        watch = soundalert.KeyWatch("report")
        self.assertEqual(watch.look({"a"}), [])
        self.assertEqual(watch.look({"a"}), [])
        self.assertEqual(watch.look({"a", "b"}), ["report"])
        self.assertEqual(watch.look({"b"}), [], "something that goes away is not news")
        self.assertEqual(watch.look({"b", "c", "d"}), ["report"], "several new keys are still one sound")


class TheCycle(unittest.TestCase):
    def setUp(self):
        self.addCleanup(actions_monitor.CONNECTION_WAS.update, lost=False)
        actions_monitor.CONNECTION_WAS["lost"] = False

    def cycle(self, offline, config=ON):
        with mock.patch.object(actions_monitor, "quota_watch"), mock.patch.object(actions_monitor, "digest_tick"), mock.patch.object(actions_monitor, "maintain_extras"), \
                mock.patch.object(actions_monitor, "retention_tick"), mock.patch.object(actions_monitor, "score_tick"), mock.patch.object(actions_monitor, "report_tick"), \
                mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=config), mock.patch.object(actions_monitor, "alerts_payload", return_value={"alerts": []}), \
                mock.patch.object(soundalert, "beep_kinds") as beep:
            try:
                actions_monitor.maintain(config, {"offline": {"offline": offline}})
            except Exception:   # noqa: BLE001 - what comes after the sound is not what is tested
                pass
            return [c.args[1] for c in beep.call_args_list]

    def test_the_connection_that_goes_down_and_comes_back_sound_once_each(self):
        self.assertEqual(self.cycle(False), [])
        self.assertEqual(self.cycle(True), [["connection_lost"]])
        self.assertEqual(self.cycle(True), [], "a connection that stays down is not announced again")
        self.assertEqual(self.cycle(False), [["live_recovered"]])
        self.assertEqual(self.cycle(False), [])


class ThePages(unittest.TestCase):
    def test_the_page_and_the_wall_have_the_sound_of_the_live_view_back(self):
        for text in (PAGE, WALL):
            self.assertIn("live:{w:\"sine\"", text)
        self.assertEqual(page_sounds.block(PAGE, "SOUNDS").replace("\r\n", "\n"), page_sounds.block(WALL, "SOUNDS").replace("\r\n", "\n"))
        self.assertIn('beep(["live"])', WALL)
        self.assertIn('live:on("live_recovered")', PAGE)
        self.assertIn('live:"live_recovered"', WALL)

    def test_the_settings_and_the_texts_of_the_new_kind_exist_in_eight_languages(self):
        self.assertIn("sound.on_live_recovered", settings_api.FIELDS)
        self.assertIs(actions_monitor.DEFAULTS["sound"]["on_live_recovered"], True)
        for lang in i18n.LANGS:
            for key in ("cfg.f.sound.on_live_recovered", "cfg.h.sound.on_live_recovered", "ui.snd_k_live", "cfg.h.sound.server_beep"):
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))

    def test_the_wall_plays_it_when_the_connection_returns(self):
        body = WALL[WALL.index("async function load()"):WALL.index("const JUMP_KINDS")]
        self.assertIn("const wasOff=STATE.offSound", body)
        self.assertLess(body.index("const wasOff"), body.index("STATE.offSound=false"))


@unittest.skipUnless(page_sounds.NODE, "no node on this computer")
class TheBehaviourOfThePage(unittest.TestCase):
    def test_the_connection_with_the_monitor_that_is_found_again_sounds_once(self):
        out = page_sounds.run_js("""
const r={};reset();
soundLost();r.lost=played();NOW+=40000;soundFound();r.found=played();soundFound();NOW+=40000;soundFound();r.again=played();
reset();I18N.sound.on_live_recovered=false;soundLost();NOW+=40000;soundFound();r.off=played();
reset();soundFound();r.neverLost=played();
console.log(JSON.stringify(r));""")
        self.assertEqual(out["lost"], ["conn"])
        self.assertEqual(out["found"], ["conn", "live"])
        self.assertEqual(out["again"], ["conn", "live"], "one sound for the return, not one for each look")
        self.assertEqual(out["off"], ["conn"])
        self.assertEqual(out["neverLost"], [])

    def test_the_connection_to_github_that_returns_sounds_and_the_first_look_does_not(self):
        out = page_sounds.run_js("""
const r={};reset();
soundWatch({failing:[],offline:{offline:true}});r.first=played();NOW+=60000;soundWatch({failing:[],offline:{offline:false}});r.back=played();
reset();soundWatch({failing:[],offline:{offline:false}});NOW+=60000;soundWatch({failing:[],offline:{offline:false}});r.steady=played();
console.log(JSON.stringify(r));""")
        self.assertEqual(out["first"], [])
        self.assertEqual(out["back"], ["live"])
        self.assertEqual(out["steady"], [])


if __name__ == "__main__":
    unittest.main()
