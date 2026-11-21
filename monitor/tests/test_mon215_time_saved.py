# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Time saved: the estimate of the analytics is off by default, says "no data" where the person did not note the time before the monitor, labels an assumption as an assumption, counts the failed runs in view
and never makes a call. Its settings exist, have help and a title in the eight languages, and the example file carries them with the same defaults."""
import json
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.app import settings_api as sa  # noqa: E402
from github_actions_monitor.data_pipeline import timesaved  # noqa: E402
from github_actions_monitor.sentinels import sentinel_panels  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
LOCALES = {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}
EXAMPLE = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
NOW = 1_800_000_000.0


def stamp(days_ago):
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - days_ago * 86400))


def runs(failed_days, ok_days=()):
    return [{"started": stamp(d), "conclusion": "failure"} for d in failed_days] + [{"started": stamp(d), "conclusion": "success"} for d in ok_days]


def cfg(**kw):
    return timesaved.settings({"productivity": dict({"enabled": True}, **kw)})


class Estimate(unittest.TestCase):
    def test_it_is_off_by_default_and_says_so(self):
        self.assertFalse(timesaved.settings({})["enabled"])
        self.assertEqual(timesaved.estimate(runs([1]), timesaved.settings({}), NOW), {"enabled": False})

    def test_without_the_notes_of_the_person_there_is_no_number(self):
        out = timesaved.estimate(runs([1, 2], [3]), cfg(), NOW)
        self.assertTrue(out["enabled"])
        self.assertEqual([t["basis"] for t in out["tasks"]], ["no_data", "no_data"])
        self.assertIsNone(out["saved_minutes_week"])
        self.assertIsNone(out["share_percent"])
        self.assertEqual(out["failed_seen"], 2)

    def test_an_assumption_is_labelled_and_uses_the_percentage(self):
        out = timesaved.estimate(runs([1, 2, 3, 4]), cfg(triage_minutes_before=30), NOW)
        triage = out["tasks"][1]
        self.assertEqual(triage["basis"], "assumed")
        self.assertEqual(triage["times_per_week"], 4.0)
        self.assertEqual(triage["saved_minutes"], 108)      # 4 x 30 x 0.90
        self.assertEqual(out["tasks"][0]["basis"], "no_data")
        self.assertEqual(out["saved_minutes_week"], 108)

    def test_the_minutes_after_make_it_a_measurement_from_the_notes(self):
        out = timesaved.estimate(runs([1, 2]), cfg(window_days=7, triage_minutes_before=40, triage_minutes_after=10, saving_percent=50), NOW)
        triage = out["tasks"][1]
        self.assertEqual(triage["basis"], "measured")
        self.assertEqual(triage["saving_percent"], 75)
        self.assertEqual(triage["saved_minutes"], 60)      # 2 x 40 x 0.75

    def test_the_watching_task_uses_the_notes_only_and_the_share_needs_the_hours(self):
        out = timesaved.estimate([], cfg(watch_times_per_week=10, watch_minutes_before=10, team_hours_per_week=20), NOW)
        self.assertEqual(out["tasks"][0]["saved_minutes"], 90)
        self.assertEqual(out["tasks"][1]["basis"], "no_data")      # no run at all in view: nothing was seen
        self.assertEqual(out["saved_minutes_week"], 90)
        self.assertEqual(out["share_percent"], 7.5)
        self.assertIsNone(timesaved.estimate([], cfg(watch_times_per_week=10, watch_minutes_before=10), NOW)["share_percent"])

    def test_the_example_of_the_run_list_without_failures_saves_nothing_it_does_not_invent(self):
        out = timesaved.estimate(runs([], [1, 2]), cfg(triage_minutes_before=30), NOW)
        self.assertEqual(out["tasks"][1]["saved_minutes"], 0)
        self.assertEqual(out["failed_seen"], 0)

    def test_only_the_failed_runs_inside_the_window_count(self):
        failed, dated = timesaved.failed_in_window(runs([1, 6, 9, 20], [2]) + [{"started": "not a date", "conclusion": "failure"}], 7, NOW)
        self.assertEqual((failed, dated), (2, 5))

    def test_values_out_of_range_or_of_the_wrong_type_keep_the_default(self):
        c = timesaved.settings({"productivity": {"enabled": "yes", "window_days": 0, "saving_percent": 101, "watch_minutes_before": True, "triage_minutes_after": -5, "team_hours_per_week": 40}})
        self.assertFalse(c["enabled"])
        self.assertEqual((c["window_days"], c["saving_percent"], c["watch_minutes_before"], c["triage_minutes_after"], c["team_hours_per_week"]), (7, 90, 0, -1, 40))

    def test_fixing_a_failure_is_declared_not_counted(self):
        self.assertIn("fixing_failures", timesaved.estimate([], cfg(), NOW)["not_quantified"])


class Panel(unittest.TestCase):
    def tr(self, key, **kw):
        return LOCALES["en"][key].format(**kw)

    def test_the_summary_of_the_panel_names_the_estimate_only_when_it_is_on(self):
        base = {"enabled": True, "duration": [], "flaky": []}
        _rows, plain = sentinel_panels._a12(base, "", self.tr)
        _rows, none = sentinel_panels._a12(dict(base, time_saved={"enabled": True, "saved_minutes_week": None}), "", self.tr)
        _rows, some = sentinel_panels._a12(dict(base, time_saved={"enabled": True, "saved_minutes_week": 120}), "", self.tr)
        _rows, off = sentinel_panels._a12(dict(base, time_saved={"enabled": False}), "", self.tr)
        self.assertEqual(plain, off)
        self.assertIn("no data", none)
        self.assertIn("120", some)
        self.assertIn("estimate", some)


class Settings(unittest.TestCase):
    KEYS = ["productivity." + k for k in timesaved.DEFAULTS]

    def test_every_setting_exists_with_its_help_and_title_in_the_eight_languages(self):
        for key in self.KEYS:
            self.assertIn(key, sa.FIELDS)
            for lang in LANGS:
                self.assertTrue(LOCALES[lang].get("cfg.f." + key), (lang, key))
                self.assertTrue(LOCALES[lang].get("cfg.h." + key), (lang, key))
        for lang in LANGS:
            self.assertTrue(LOCALES[lang].get("ui.cfg_b_time_saved"))

    def test_the_example_file_carries_the_defaults_of_the_code(self):
        self.assertEqual(EXAMPLE["productivity"], timesaved.DEFAULTS)

    def test_the_words_of_the_panel_exist_in_the_eight_languages(self):
        words = [k for k in LOCALES["en"] if k.startswith(("ui.ts_", "ui.sc_ts", "ui.a12_h_saved"))]
        self.assertGreaterEqual(len(words), 20)
        for lang in LANGS:
            for key in words:
                self.assertTrue(LOCALES[lang].get(key), (lang, key))
        for task in ("watch", "triage"):
            self.assertIn("ui.ts_task_" + task, LOCALES["en"])
        for basis in ("measured", "assumed", "no_data"):
            self.assertIn("ui.ts_basis_" + basis, LOCALES["en"])


if __name__ == "__main__":
    unittest.main()
