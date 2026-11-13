# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Low mode: reads less when the allowance is short (chosen, or by itself with a gap between going in and coming out), never loses a red alert, and says that its figures can be old."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import modes  # noqa: E402
from github_actions_monitor.data_pipeline import signals  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
CONFIG = {"refresh_seconds": 45, "cold_refresh_seconds": 600, "runs_per_repo": 20, "hot_hours": 6, "min_rate_remaining": 800}


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class LowMode(unittest.TestCase):
    def test_low_reads_less_never_more_than_you_set(self):
        self.assertIn("low", modes.NAMES)
        self.assertEqual(modes.effective(CONFIG, "refresh_seconds", "low"), 240)
        self.assertEqual(modes.effective(CONFIG, "cold_refresh_seconds", "low"), 1800)
        self.assertEqual(modes.effective(CONFIG, "runs_per_repo", "low"), 10)
        self.assertEqual(modes.effective(CONFIG, "hot_hours", "low"), 2)
        self.assertEqual(modes.effective({**CONFIG, "refresh_seconds": 900}, "refresh_seconds", "low"), 900, "a slower setting of yours stays")
        self.assertEqual(modes.effective({**CONFIG, "runs_per_repo": 5}, "runs_per_repo", "low"), 5)
        est = modes.estimate(CONFIG, 131, 6, 900)
        self.assertLess(est["low"]["calls_per_hour"], est["normal"]["calls_per_hour"] if "normal" in est else 10 ** 9)
        self.assertLess(est["low"]["calls_per_hour"], est["fast"]["calls_per_hour"])

    def test_it_is_configurable_in_the_file_with_safe_values(self):
        cfg = {**CONFIG, "modes": {"low": {"refresh_seconds": 600, "hot_hours": 9999}}}
        self.assertEqual(modes.presets(cfg)["low"]["refresh_seconds"], 600)
        self.assertEqual(modes.presets(cfg)["low"]["hot_hours"], 2)      # out of range: the default
        flat = modes.settings({"modes": {"auto_low_enter": 3000, "auto_low_exit": 2000}})
        self.assertEqual((flat["auto_low_enter"], flat["auto_low_exit"]), (1000, 2500), "going in must be lower than coming out, or it flaps")
        self.assertTrue(modes.settings({})["auto_low"])
        self.assertFalse(modes.settings({"modes": {"auto_low": False}})["auto_low"])

    def test_auto_low_goes_in_under_1000_and_comes_out_over_2500_with_a_gap(self):
        clock = Clock()
        state = modes.State(clock)
        self.assertEqual(state.current(CONFIG, 3000), "normal")
        self.assertEqual(state.current(CONFIG, 999), "low")
        self.assertTrue(state.auto)
        self.assertEqual(state.notice, "auto_low")
        for remaining in (1200, 2000, 2500, 1000):
            self.assertEqual(state.current(CONFIG, remaining), "low", f"{remaining}: inside the gap it stays")
        self.assertEqual(state.current(CONFIG, 2501), "normal")
        self.assertEqual(state.notice, "auto_low_end")
        self.assertFalse(state.auto)
        off = modes.State(clock)
        self.assertEqual(off.current({**CONFIG, "modes": {"auto_low": False}}, 10), "normal")

    def test_a_chosen_low_does_not_leave_by_itself_and_is_always_allowed(self):
        state = modes.State(Clock())
        self.assertEqual(state.set("low", 0, CONFIG, rate_limit=60, remaining=10), (True, "ok"))      # no login, almost no allowance: low is exactly for that
        self.assertFalse(state.auto)
        self.assertEqual(state.current(CONFIG, 5000), "low")
        self.assertEqual(state.set("fast", 5, CONFIG, rate_limit=60), (False, "no_token"))
        fast = modes.State(Clock())
        fast.set("turbo", 0, CONFIG, remaining=4000)
        self.assertEqual(fast.current(CONFIG, 100), "normal")      # the old rule for the fast modes is kept

    def test_the_page_offers_it_and_says_the_figures_can_be_old(self):
        self.assertEqual(PAGE.count('<option value="low"></option>'), 2)
        self.assertIn('["normal","fast","turbo","low"]', PAGE)
        self.assertIn('T("ui.mode_low_t")', PAGE)
        for lang in i18n.LANGS:
            for key in ("mode.low", "ui.mode_low", "ui.mode_auto", "ui.mode_low_t", "mode.back_auto_low", "mode.back_auto_low_end", "ui.mode_back_auto_low_end"):
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))

    def test_the_brief_marks_the_age_of_the_data_in_low(self):
        doc = signals.state({"figures": {}}, [], "lite", {"working_mode": "low", "auto_mode": True, "age_seconds": 700})
        mode = [s for s in doc["signals"] if s["id"] == "health.mode"][0]
        self.assertEqual(mode["level"], "watch")
        self.assertIn("automatic", mode["summary"])
        self.assertIn("700 s ago", mode["summary"])
        self.assertTrue(mode["transient"])
        normal = [s for s in signals.state({"figures": {}}, [], "lite", {"working_mode": "normal"})["signals"] if s["id"] == "health.mode"][0]
        self.assertEqual(normal["level"], "info")

    def test_red_alerts_survive_low(self):
        """Low slows the reading but the alerts of what was already read stay: the failing list comes from the runs in memory and the rule does not look at the mode."""
        from github_actions_monitor.app import actions_monitor as am
        runs = [{"id": 1, "repo": "r", "name": "ci", "path": "ci.yml", "status": "completed", "conclusion": "failure", "event": "push", "branch": "main", "sha": "a", "url": "u", "started": "2026-01-01T10:00:00Z", "seconds": 5}]
        self.assertEqual(len(am.unresolved_failures(runs)), 1)
        import inspect
        self.assertNotIn("MODE", inspect.getsource(am.unresolved_failures))


if __name__ == "__main__":
    unittest.main()
