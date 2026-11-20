# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The daily trend gets the series the history did not have (how long the runs last and wait, the flaky workflows, the minutes of each repository, the size of the artifacts, the alerts of every
severity), the days a release was published as marks, the lines of the chart as settings with their tooltip, a bar view, and a copy of the chart as an image. All of it from what the cycle already
holds: no call to GitHub. A day without a figure is a gap, never a zero."""
import json
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.app import settings_api
from github_actions_monitor.data_pipeline import briefs, signals, trend_day
from github_actions_monitor.sentinels import sentinel_local as sl

HERE = Path(__file__).resolve().parent.parent
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
NOW = datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc)


def run(repo, name, sha, conclusion, seconds, hours_ago=2, queued=None, attempt=1, status="completed"):
    started = datetime.fromtimestamp(NOW.timestamp() - hours_ago * 3600, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"repo": repo, "name": name, "sha": sha, "conclusion": conclusion, "seconds": seconds, "started": started, "queued": queued, "attempt": attempt, "status": status}


class Figures(unittest.TestCase):
    def test_duration_queue_and_flaky_of_the_last_day(self):
        runs = {"a": [run("a", "ci", "1", "success", 600, queued=10), run("a", "ci", "2", "success", 1200, queued=30),
                      run("a", "ci", "3", "failure", 60, hours_ago=5), run("a", "ci", "3", "success", 100, hours_ago=4)],
                "b": [run("b", "ci", "9", "success", 3600, hours_ago=40, queued=500)]}      # older than a day: not counted
        got = trend_day.run_figures(trend_day.runs_of_the_day(runs, NOW))
        self.assertEqual(got["dur_avg"], round((600 + 1200 + 100) / 3 / 60, 1))
        self.assertEqual(got["dur_p95"], 20.0)
        self.assertEqual(got["queue_avg"], 20.0)
        self.assertEqual(got["flaky"], 1)      # the commit 3 failed and then passed

    def test_no_run_in_the_last_day_is_a_gap_and_never_a_zero(self):
        got = trend_day.run_figures(trend_day.runs_of_the_day({"a": [run("a", "ci", "1", "success", 600, hours_ago=80)]}, NOW))
        self.assertEqual(got, {"dur_avg": None, "dur_p95": None, "queue_avg": None, "flaky": None})

    def test_runs_in_progress_do_not_count_as_durations(self):
        got = trend_day.run_figures([run("a", "ci", "1", "success", 600, status="in_progress")])
        self.assertIsNone(got["dur_avg"])

    def test_artifacts_in_megabytes_and_none_when_nothing_was_read(self):
        self.assertEqual(trend_day.artifact_megabytes({"a": {"artifacts": {"bytes": 3 * 1048576}}, "b": {"artifacts": {"bytes": 1048576}}, "c": {}}), 4.0)
        self.assertIsNone(trend_day.artifact_megabytes({"a": {}, "b": {"artifacts": None}}))
        self.assertIsNone(trend_day.artifact_megabytes(None))

    def test_all_the_severities_are_counted_and_moderate_is_medium(self):
        totals = {"a": {"sev": {"critical": 1, "high": 2, "moderate": 3, "low": 4}}, "b": {"sev": {"medium": 1}}, "c": {}}
        self.assertEqual(trend_day.severities(totals), {"critical": 1, "high": 2, "medium": 4, "low": 4})

    def test_the_minutes_of_each_repository_are_none_while_no_run_has_been_read(self):
        mins = {"a": {"min24": 30, "min7d": 90}}
        self.assertEqual(trend_day.build({"a": []}, NOW, {}, {}, mins)["min_repo"], None)
        self.assertEqual(trend_day.build({"a": [run("a", "ci", "1", "success", 60)]}, NOW, {}, {}, mins)["min_repo"], {"a": 30})

    def test_the_figures_of_the_day_reach_the_history_and_a_missing_one_is_none(self):
        snap = {"a7": {"total24": 5, "day": {"dur_avg": 2.5, "dur_p95": 4.0, "queue_avg": None, "flaky": 0, "artifact_mb": 12.5, "min_repo": {"a": 3}}},
                "a3": {"severity_all": {"critical": 0, "high": 1, "medium": 2, "low": 3}}}
        got = sl.daily_extras(snap)
        self.assertEqual((got["dur_avg"], got["dur_p95"], got["queue_avg"], got["flaky"], got["artifact_mb"]), (2.5, 4.0, None, 0, 12.5))
        self.assertEqual((got["sev_medium"], got["sev_low"]), (2, 3))
        self.assertEqual(got["min_repo"], {"a": 3})
        empty = sl.daily_extras({})
        for key in ("dur_avg", "dur_p95", "queue_avg", "flaky", "artifact_mb", "sev_medium", "sev_low", "min_repo"):
            self.assertIsNone(empty[key], key)

    def test_the_minutes_per_repository_are_series_with_gaps_for_the_old_days(self):
        history = {"days": {"2026-01-01": {"red": 1}, "2026-01-02": {"min_repo": {"a": 10, "b": 5}}, "2026-01-03": {"min_repo": {"a": 20}}}}
        got = trend_day.repo_series(history, top=1)
        self.assertEqual(got["dates"], ["2026-01-01", "2026-01-02", "2026-01-03"])
        self.assertEqual(got["repos"], {"a": [None, 10, 20]})
        self.assertEqual(trend_day.repo_series(history)["repos"]["b"], [None, 5, 0])      # a repository that did not run that day: zero minutes, but not before the figure existed

    def test_the_days_of_a_release_are_marks_and_never_invent_a_day(self):
        found = trend_day.release_days({"a": {"publishedAt": "2026-01-02T10:00:00Z", "tagName": "v1"}, "b": {"publishedAt": "2026-01-02T11:00:00Z", "tagName": "v2"}, "c": {"publishedAt": "2025-12-01T00:00:00Z", "tagName": "v0"}, "d": {}})
        self.assertEqual(found, {"2026-01-02": ["a v1", "b v2"], "2025-12-01": ["c v0"]})
        days = {"2026-01-02": {"red": 0}, "2026-01-03": {"red": 0}}
        trend_day.merge_releases(days, found)
        trend_day.merge_releases(days, found)      # the second cycle does not repeat the names
        self.assertEqual(days["2026-01-02"]["releases"], ["a v1", "b v2"])
        self.assertNotIn("2025-12-01", days)
        self.assertEqual(trend_day.release_marks({"days": days}), {"2026-01-02": ["a v1", "b v2"]})

    def test_the_series_are_in_the_trend_of_the_sentinel(self):
        for key in ("dur_avg", "dur_p95", "queue_avg", "flaky", "artifact_mb", "sev_medium", "sev_low"):
            self.assertIn(key, sl.EXTRA_SERIES)
        self.assertEqual(sorted(trend_day.SEVERITIES), ["critical", "high", "low", "medium"])

    def test_nothing_in_the_module_asks_github(self):
        text = (HERE / "src" / "github_actions_monitor" / "data_pipeline" / "trend_day.py").read_text(encoding="utf-8")
        for needle in ("subprocess", "gh_read", "urllib", "requests", "http"):
            self.assertNotIn(needle, text.replace("GPL-3.0-or-later - see LICENSE", ""))


class Settings(unittest.TestCase):
    KEYS = ("sentinel.trend_green_pct", "sentinel.trend_health", "sentinel.trend_quota_pct")

    def test_the_thresholds_are_settings_with_the_old_values_as_defaults_and_a_tooltip_in_every_language(self):
        defaults = sl.sentinel_config({})
        self.assertEqual((defaults["trend_green_pct"], defaults["trend_health"], defaults["trend_quota_pct"]), (90, 70, 80))
        self.assertEqual(sl.sentinel_config({"sentinel": {"trend_health": 55}})["trend_health"], 55)
        for key in self.KEYS:
            self.assertIn(key, settings_api.META, key)
            for lang in LANGS:
                cat = json.loads((HERE / "assets" / "locales" / (lang + ".json")).read_text(encoding="utf-8"))
                self.assertTrue(cat.get("cfg.f." + key), (lang, key))
                self.assertTrue(cat.get("cfg.h." + key), (lang, key))
        for lang in LANGS:
            self.assertTrue(json.loads((HERE / "assets" / "locales" / (lang + ".json")).read_text(encoding="utf-8")).get("ui.cfg_b_trend"), lang)

    def test_the_template_and_the_guide_carry_them(self):
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))["sentinel"]
        self.assertEqual((example["trend_green_pct"], example["trend_health"], example["trend_quota_pct"]), (90, 70, 80))
        for name in ("SETTINGS.md", "SETTINGS_spa.md", "SETTINGS_deu.md", "SETTINGS_fra.md", "SETTINGS_ita.md", "SETTINGS_jpn.md", "SETTINGS_zho.md", "SETTINGS_por.md"):
            text = (HERE / "docs" / name).read_text(encoding="utf-8")
            for key in self.KEYS:
                self.assertIn("`" + key + "`", text, (name, key))


class Page(unittest.TestCase):
    def block(self):
        return PAGE[PAGE.index("const TRS="):PAGE.index("function section(")]

    def test_the_page_reads_the_thresholds_and_the_marks_and_has_the_new_controls(self):
        block = self.block()
        for needle in ("trThr", "thresholds", "tr.releases", "ui.tr_ev_release", "tr-view", "data-trcopy", "trCopy", "trPng", "ClipboardItem", "mr:", "min_repo", "trbar1", "release"):
            self.assertIn(needle, block, needle)

    def test_every_new_text_exists_in_the_eight_languages(self):
        keys = set(re.findall(r'"(ui\.tr_[a-z_0-9]+)"', self.block()))
        self.assertTrue({"ui.tr_view", "ui.tr_view_bars", "ui.tr_view_line", "ui.tr_copy", "ui.tr_copy_ok", "ui.tr_copy_save", "ui.tr_min_repo", "ui.tr_ev_release"} <= keys, keys)
        for lang in LANGS:
            cat = json.loads((HERE / "assets" / "locales" / (lang + ".json")).read_text(encoding="utf-8"))
            self.assertEqual(sorted(k for k in keys if not cat.get(k)), [], lang)

    def test_the_copy_does_not_ask_anything_to_the_network(self):
        block = self.block()
        copy = block[block.index("function trPng("):block.index("function trCursor(")]
        self.assertNotIn("fetch(", copy)
        self.assertNotIn("XMLHttpRequest", copy)


class BriefAndPrint(unittest.TestCase):
    TREND = {"red": {"dates": ["a", "b", "c"], "values": [1, 2, 4]}, "dur_avg": {"dates": ["a", "b", "c"], "values": [None, None, 3.5]},
             "min_repo": {"dates": ["a", "b", "c"], "repos": {"r1": [None, 5, 7]}}, "releases": {"b": ["r1 v1"]}, "thresholds": {"health": 70}, "versions": [None, None, None]}

    def test_the_trend_is_one_signal_that_asks_nothing_and_tells_the_gaps(self):
        sig = signals.trend_signal(self.TREND)
        self.assertEqual((sig["id"], sig["level"]), ("trend.daily", "info"))
        rows = {r["text"].split(":")[0]: r["text"] for r in sig["rows"]}
        self.assertIn("change against yesterday 2, against 7 days ago unknown", rows["red"])
        self.assertIn("2 day(s) without figure", rows["dur_avg"])
        self.assertIn("r1", [r["repo"] for r in sig["rows"]])
        self.assertIn("releases published on 1 day(s)", sig["summary"])

    def test_the_brief_of_the_tab_carries_the_signal_and_the_state_builds_it_only_when_given_a_trend(self):
        state = signals.state({}, [], "complete", {}, version="9", trend=self.TREND)
        self.assertIn("trend.daily", [s["id"] for s in state["signals"]])
        self.assertNotIn("trend.daily", [s["id"] for s in signals.state({}, [], "complete", {}, version="9")["signals"]])
        brief = briefs.brief("strend", state)
        self.assertIn("trend.daily", [s["id"] for s in brief["signals"]])
        self.assertIn("trend.daily", briefs.CATALOG["strend"]["prefixes"])

    def test_printing_shows_the_whole_tab_without_the_controls(self):
        css = PAGE[PAGE.index("@media print{.tab{"):]
        css = css[:css.index(chr(10))]
        for needle in ("overflow:visible", ".trbar{display:none", "break-inside:avoid"):
            self.assertIn(needle, css, needle)

    @unittest.skipUnless((HERE.parent / "tools" / "demo_monitor.py").is_file(), "needs the repository root (tools/demo_monitor.py), not part of the installed zip")
    def test_the_demo_with_data_fills_the_new_series_with_gaps_at_the_start(self):
        text = (HERE.parent / "tools" / "demo_monitor.py").read_text(encoding="utf-8")
        for key in ("dur_avg", "dur_p95", "queue_avg", "flaky", "artifact_mb", "sev_medium", "sev_low", "min_repo", "releases", "thresholds"):
            self.assertIn('"' + key + '"', text, key)


if __name__ == "__main__":
    unittest.main()
