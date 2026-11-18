# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The comparison of periods end to end on a ledger and some snapshots made by hand (the figures are worked out in the test): exact figures, the calendar filter against the bias it removes, the
honest states (too little data, no baseline, calibrating, off), the resolution time of alerts, the list of changes, the exports, the cache, the isolation between accounts and old documents."""
import json
import sys
import tempfile
import unittest
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.compare import changes, config, metrics, resolution, windows  # noqa
from github_actions_monitor.compare import compare_service as service  # noqa: E402
from github_actions_monitor.scoring import ledger as score_ledger  # noqa: E402
from github_actions_monitor.storage import file_storage  # noqa: E402

DAY = 86400.0
NOW = datetime(2027, 1, 15, 8, tzinfo=timezone.utc).timestamp()      # Friday; the window of 7 days starts on Friday 8 January
ON = {"compare": {"enabled": True, "min_runs_per_window": 5}}


def utc(*parts):
    return datetime(*parts, tzinfo=timezone.utc).timestamp()


def runs_at(moment, good, bad, repo="a/x", workflow="CI", seconds=60.0):
    """{key: row} of the ledger: `good` successes and `bad` failures that started at that moment."""
    rows = {}
    for i in range(good):
        rows[f"{repo}:{workflow}:{moment}:g{i}"] = [moment + i, "success", seconds, repo, workflow]
    for i in range(bad):
        rows[f"{repo}:{workflow}:{moment}:b{i}"] = [moment + 100 + i, "failure", seconds, repo, workflow]
    return rows


def make_ledger(first_seen=NOW - 40 * DAY):
    runs = {}
    runs.update(runs_at(utc(2027, 1, 9, 12), 0, 10))                       # Saturday of the window now: ten failures
    runs.update(runs_at(utc(2027, 1, 12, 12), 30, 0, seconds=60.0))        # Tuesday of the window now: thirty successes
    runs.update(runs_at(utc(2027, 1, 5, 12), 36, 4, seconds=120.0))        # Tuesday of the window before: forty runs, four failures
    return {"first_seen": first_seen, "last_tick": NOW, "runs": runs, "collab": {}, "drop_open": False}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.s = file_storage.FileStorage(Path(self.tmp.name))
        service.clear_cache()
        self.addCleanup(service.clear_cache)

    def put(self, ledger, account="alpha"):
        self.s.save_doc(account, score_ledger.LEDGER_DOC, ledger)

    def ask(self, ask=None, cfg=None, account="alpha"):
        return service.build(self.s, account, cfg or ON, ask or {}, now=NOW, zone="utc")


class Figures(Base):
    def test_the_share_of_failed_runs_is_exact(self):
        self.put(make_ledger())
        m = self.ask()["metrics"]["red_rate"]
        self.assertEqual((m["now"], m["base"], m["delta"], m["state"], m["direction"]), (0.25, 0.1, 0.15, "ok", "worse"))      # 10 of 40 against 4 of 40
        self.assertEqual((m["samples_now"]["runs"], m["samples_base"]["runs"]), (40, 40))

    def test_the_median_duration_uses_the_successful_runs(self):
        self.put(make_ledger())
        m = self.ask()["metrics"]["duration_p50"]
        self.assertEqual((m["now"], m["base"], m["delta"], m["direction"]), (60.0, 120.0, -60.0, "better"))

    def test_workdays_and_weekend_give_what_the_mixed_data_hides(self):
        self.put(make_ledger())
        everyday = self.ask({"days": "all"})["metrics"]["red_rate"]["now"]
        workdays = self.ask({"days": "workdays"})["metrics"]["red_rate"]
        weekend = self.ask({"days": "weekend"})["metrics"]["red_rate"]
        self.assertEqual(everyday, 0.25)
        self.assertEqual((workdays["now"], workdays["base"], workdays["direction"]), (0.0, 0.1, "better"))      # all the failures of the week were on Saturday
        self.assertEqual((weekend["now"], weekend["state"]), (1.0, "insufficient_data"))      # nothing ran on the weekend before: that side has no figure
        self.assertEqual(weekend["missing"], [{"window": "base", "reason": "few_runs"}])
        self.assertEqual(self.ask({"days": "workdays"})["workdays"], [1, 2, 3, 4, 5])

    def test_a_window_with_few_runs_is_insufficient_never_zero(self):
        self.put(make_ledger())
        answer = self.ask(cfg={"compare": {"enabled": True, "min_runs_per_window": 41}})
        m = answer["metrics"]["red_rate"]
        self.assertEqual((m["now"], m["base"], m["state"], m["delta"]), (None, None, "insufficient_data", None))
        self.assertEqual(answer["coverage"], 0.0)
        self.assertEqual(answer["state"], "compared")

    def test_the_resolution_time_of_alerts(self):
        ledger = make_ledger()
        a = utc(2027, 1, 9, 6)      # opened in the window now and closed one, one and two days later
        ledger["collab"] = {"n1": [a, a + DAY], "n2": [a, a + DAY], "n3": [a, a + 2 * DAY], "o1": [a, None],
                            "b1": [utc(2027, 1, 2), utc(2027, 1, 2) + 3600], "b2": [utc(2027, 1, 3), utc(2027, 1, 3) + 3600], "b3": [utc(2027, 1, 4), utc(2027, 1, 4) + 3600]}
        self.put(ledger)
        answer = self.ask()
        m = answer["metrics"]["resolution"]
        self.assertEqual((m["now"], m["base"], m["direction"]), (DAY, 3600.0, "worse"))
        self.assertEqual(answer["alerts"], {"opened_now": 4, "open_at_end_now": 1, "opened_base": 3, "open_at_end_base": 0})

    def test_resolution_edges_open_across_the_border_and_reopened(self):
        edge = utc(2027, 1, 8, 8)      # the start of the window now
        collab = {"crosses_start": [edge - 3600, edge + 3600],      # opened before, closed inside: counted where it closed
                  "crosses_end": [NOW - 3600, NOW + 3600],      # closes after the end: still open at the end
                  "never": [edge + 10, None], "reopened": [edge + 20, edge + 3620]}
        r = resolution.summarize(collab, (edge, NOW), "all", [1, 2, 3, 4, 5], "utc")
        self.assertEqual((r["resolved"], r["median_seconds"], r["opened"], r["open_at_end"]), (2, 3600.0, 3, 2))      # spans of 7200 and 3600 s: the median is the lower middle one (nearest rank)

    def test_the_mean_score_comes_from_the_hourly_snapshots(self):
        self.put(make_ledger())
        for h in range(12):
            for start, score in ((NOW - 3 * DAY, 80.0), (NOW - 10 * DAY, 70.0)):
                moment = start + h * 3600
                self.s.save_score_snapshot("alpha", score_ledger.hour_key(moment), {"at": moment, "state": "scored", "score": score, "coverage": 0.8})
        answer = self.ask()
        self.assertEqual((answer["metrics"]["score_mean"]["now"], answer["metrics"]["score_mean"]["base"], answer["metrics"]["score_mean"]["direction"]), (80.0, 70.0, "better"))
        self.assertEqual(answer["metrics"]["score_coverage"]["now"], 0.8)
        self.assertEqual(answer["metrics"]["score_coverage"]["direction"], "same")

    def test_snapshots_without_a_number_do_not_count(self):
        self.put(make_ledger())
        for h in range(12):
            moment = NOW - 3 * DAY + h * 3600
            self.s.save_score_snapshot("alpha", score_ledger.hour_key(moment), {"at": moment, "state": "calibrating", "score": None})
        self.assertEqual(self.ask()["metrics"]["score_mean"]["state"], "insufficient_data")


class Honesty(Base):
    def test_off_by_default(self):
        self.put(make_ledger())
        answer = self.ask(cfg={"compare": {}})
        self.assertEqual((answer["state"], answer["enabled"], answer["metrics"]), ("off", False, {}))

    def test_nothing_kept_yet_is_calibrating(self):
        answer = self.ask()
        self.assertEqual((answer["state"], answer["data_quality"]["reasons"]), ("calibrating", ["no_history"]))

    def test_a_monitor_that_is_calibrating_does_not_compare(self):
        self.put(make_ledger(first_seen=NOW - 3600))
        answer = self.ask()
        self.assertEqual((answer["state"], answer["data_quality"]["reasons"]), ("calibrating", ["watched_briefly"]))
        self.assertEqual(answer["metrics"], {})

    def test_a_short_history_leaves_the_baseline_unavailable_and_nothing_is_filled(self):
        ledger = make_ledger(first_seen=NOW - 10 * DAY)
        ledger["runs"] = {k: v for k, v in ledger["runs"].items() if v[0] > NOW - 10 * DAY}      # the monitor really started 10 days ago
        self.put(ledger)
        answer = self.ask()
        self.assertEqual(answer["state"], "baseline_unavailable")
        self.assertEqual(answer["baseline_unavailable"], {"reason": "history_too_short"})
        m = answer["metrics"]["red_rate"]
        self.assertEqual((m["state"], m["base"], m["delta"], m["direction"]), ("baseline_unavailable", None, None, "unknown"))
        self.assertIsNotNone(m["now"])      # what exists is still shown
        self.assertEqual(answer["changes"]["reason"], "history_too_short")

    def test_a_baseline_older_than_the_data_is_not_made_up(self):
        self.put(make_ledger())
        answer = self.ask({"baseline": "year_ago"})
        self.assertEqual((answer["state"], answer["baseline_unavailable"]), ("baseline_unavailable", {"reason": "before_history"}))

    def test_a_ledger_that_dropped_runs_is_said_to_be_incomplete(self):
        ledger = make_ledger()
        ledger["truncated_at"] = utc(2027, 1, 3)
        self.put(ledger)
        self.assertTrue(self.ask()["data_quality"]["truncated"])
        self.assertIn("truncated", self.ask()["data_quality"]["reasons"])

    def test_a_bad_request_raises_with_a_code(self):
        self.put(make_ledger())
        with self.assertRaises(windows.WindowError) as caught:
            self.ask({"window": "200"})
        self.assertEqual(caught.exception.code, "bad_window")

    def test_old_and_damaged_documents_are_read_without_failing(self):
        self.put({"first_seen": NOW - 40 * DAY, "runs": {"a": "x", "b": [1, 2], "c": [utc(2027, 1, 12), "success", None, "a/x", "CI"]}, "collab": {"z": "bad", "y": [1]}})
        self.s.save_score_snapshot("alpha", "2027-01-12T10", {"state": "scored", "score": 50})      # no `at`, no coverage: the hour tells the moment
        answer = self.ask()
        self.assertEqual(answer["state"], "compared")
        self.assertIsNone(answer["metrics"]["red_rate"]["now"])

    def test_nothing_is_asked_of_github(self):
        self.put(make_ledger())
        with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("network")), mock.patch("subprocess.Popen", side_effect=AssertionError("process")):
            self.assertEqual(self.ask()["state"], "compared")


class Changes(Base):
    def test_who_got_worse_who_improved_and_what_started_or_stopped_failing(self):
        runs = {}
        runs.update(runs_at(utc(2027, 1, 12, 12), 2, 2, "a/worse", "CI"))      # now 50 % red
        runs.update(runs_at(utc(2027, 1, 5, 12), 3, 1, "a/worse", "CI"))      # before 25 %
        runs.update(runs_at(utc(2027, 1, 12, 13), 4, 0, "a/better", "CI"))      # now 0 %
        runs.update(runs_at(utc(2027, 1, 5, 13), 2, 2, "a/better", "CI"))      # before 50 %
        runs.update(runs_at(utc(2027, 1, 12, 14), 1, 3, "a/new", "Deploy"))      # fails now, never before
        runs.update(runs_at(utc(2027, 1, 5, 14), 4, 0, "a/new", "Deploy"))
        runs.update(runs_at(utc(2027, 1, 12, 15), 4, 0, "a/gone", "Lint"))      # did fail before, not now
        runs.update(runs_at(utc(2027, 1, 5, 15), 1, 3, "a/gone", "Lint"))
        runs.update(runs_at(utc(2027, 1, 12, 16), 1, 0, "a/tiny", "CI"))      # too few runs to be ranked
        runs.update(runs_at(utc(2027, 1, 5, 16), 0, 1, "a/tiny", "CI"))
        ledger = make_ledger()
        ledger["runs"] = runs
        self.put(ledger)
        c = self.ask(cfg={"compare": {"enabled": True, "min_runs_per_window": 5}})["changes"]
        self.assertEqual([r["repo"] for r in c["worse"]], ["a/new", "a/worse"])      # +0.75 and +0.25
        self.assertEqual([r["repo"] for r in c["better"]], ["a/gone", "a/better"])      # -0.75 and -0.5
        self.assertEqual(c["worse"][1], {"repo": "a/worse", "red_rate_now": 0.5, "red_rate_base": 0.25, "delta": 0.25, "runs_now": 4, "runs_base": 4})
        self.assertEqual([(r["repo"], r["workflow"], r["failures"]) for r in c["new_failures"]], [("a/new", "Deploy", 3)])
        self.assertEqual([(r["repo"], r["workflow"], r["failures_before"]) for r in c["resolved_failures"]], [("a/gone", "Lint", 3), ("a/better", "CI", 2), ("a/tiny", "CI", 1)])      # the list of workflows is not held back by the minimum of runs of the ranking
        self.assertNotIn("a/tiny", [r["repo"] for r in c["worse"] + c["better"]])
        self.assertIsNone(c["reason"])

    def test_ties_are_ordered_by_name_and_the_list_is_cut_at_the_setting(self):
        runs = {}
        for name in ("a/c", "a/a", "a/b", "a/d"):
            runs.update(runs_at(utc(2027, 1, 12, 12), 2, 2, name))
            runs.update(runs_at(utc(2027, 1, 5, 12), 4, 0, name))
        ledger = make_ledger()
        ledger["runs"] = runs
        self.put(ledger)
        c = self.ask(cfg={"compare": {"enabled": True, "min_runs_per_window": 5, "top_changes": 3}})["changes"]
        self.assertEqual([r["repo"] for r in c["worse"]], ["a/a", "a/b", "a/c"])

    def test_without_runs_the_lists_are_empty_with_a_reason(self):
        ledger = make_ledger()
        ledger["runs"] = {}
        self.put(ledger)
        c = self.ask()["changes"]
        self.assertEqual((c["worse"], c["better"], c["new_failures"], c["resolved_failures"], c["reason"]), ([], [], [], [], "no_data"))

    def test_the_direction_of_every_figure(self):
        self.assertEqual([metrics.direction("red_rate", 0.1, 0.2), metrics.direction("score_mean", 80, 70), metrics.direction("resolution", 10, 10.0001), metrics.direction("red_rate", None, 1)],
                         ["better", "better", "same", "unknown"])
        self.assertEqual(changes.build.__name__, "build")


class Surface(Base):
    def test_ndjson_and_csv_carry_one_row_per_figure(self):
        self.put(make_ledger())
        answer = self.ask()
        kind, text = service.render(answer, "ndjson")
        rows = [json.loads(line) for line in text.splitlines()]
        self.assertEqual((kind, [r["metric"] for r in rows]), ("application/x-ndjson", list(metrics.METRICS)))
        self.assertEqual(rows[0], {"metric": "red_rate", "now": 0.25, "base": 0.1, "delta": 0.15, "direction": "worse", "state": "ok"})
        kind, text = service.render(answer, "csv")
        lines = text.splitlines()
        self.assertEqual((kind, lines[0], lines[1]), ("text/csv", "metric,now,base,delta,direction,state", "red_rate,0.25,0.1,0.15,worse,ok"))
        self.assertIn("score_mean,,,,unknown,insufficient_data", lines)      # a missing figure is an empty cell, never a zero

    def test_the_answer_is_cached_for_the_time_of_the_setting_and_not_when_the_clock_is_given(self):
        self.put(make_ledger())
        cfg = {"compare": {"enabled": True, "min_runs_per_window": 5, "cache_seconds": 60}}
        with mock.patch.object(self.s, "load_doc", wraps=self.s.load_doc) as reads, mock.patch("time.time", return_value=NOW):
            first = service.build(self.s, "alpha", cfg, {})
            second = service.build(self.s, "alpha", cfg, {})
            self.assertEqual(reads.call_count, 1)
            self.assertEqual(first["metrics"]["red_rate"]["now"], 0.25)
            self.assertEqual(first, second)
            second["metrics"].clear()      # the caller cannot damage what is kept
            self.assertTrue(service.build(self.s, "alpha", cfg, {})["metrics"])
            service.build(self.s, "alpha", cfg, {"days": "workdays"})
            self.assertEqual(reads.call_count, 2)
            service.build(self.s, "alpha", {"compare": {**cfg["compare"], "cache_seconds": 0}}, {})
            service.build(self.s, "alpha", {"compare": {**cfg["compare"], "cache_seconds": 0}}, {})
            self.assertEqual(reads.call_count, 4)

    def test_an_account_does_not_see_the_data_of_another(self):
        self.put(make_ledger(), "alpha")
        self.assertEqual(self.ask(account="alpha")["state"], "compared")
        beta = self.ask(account="beta")
        self.assertEqual((beta["state"], beta["account"], beta["metrics"]), ("calibrating", "beta", {}))
        self.assertEqual(beta["changes"]["worse"], [])

    def test_the_default_filter_and_window_come_from_the_settings(self):
        self.put(make_ledger())
        cfg = {"compare": {"enabled": True, "min_runs_per_window": 5, "default_days_filter": "workdays"}}
        self.assertEqual(self.ask(cfg=cfg)["days"], "workdays")
        self.assertEqual(self.ask({"days": "all"}, cfg=cfg)["days"], "all")


class Wiring(unittest.TestCase):
    def test_the_route_the_setting_and_the_lite_edition(self):
        from github_actions_monitor.app import actions_monitor, settings_api
        source = Path(actions_monitor.__file__).read_text(encoding="utf-8")
        self.assertIn('elif path == "/api/compare":', source)
        self.assertTrue(any("/api/compare".startswith(p) for p in actions_monitor.LITE_PATHS))
        self.assertEqual(actions_monitor.DEFAULTS["compare"]["enabled"], False)
        self.assertEqual(config.settings(actions_monitor.DEFAULTS), config.DEFAULTS)
        for key in ("enabled", "default_window_days", "default_days_filter", "workdays", "min_runs_per_window", "min_days_of_history", "min_resolved", "min_snapshots", "min_repo_runs", "top_changes", "include_in_report", "cache_seconds"):
            self.assertIn("compare." + key, settings_api.META)
        self.assertTrue(settings_api.check_value("compare.workdays", ["1", "2"])[0])
        self.assertFalse(settings_api.check_value("compare.workdays", ["8"])[0])
        self.assertFalse(settings_api.check_value("compare.default_days_filter", "sometimes")[0])
        self.assertFalse(settings_api.check_value("compare.top_changes", 2)[0])

    def test_the_ledger_keeps_two_windows_while_the_comparison_is_on(self):
        from github_actions_monitor.app import actions_monitor
        self.assertEqual(actions_monitor.compare_keep_days({}), 0)
        self.assertEqual(actions_monitor.compare_keep_days({"compare": {"enabled": True}}), 15)
        self.assertEqual(actions_monitor.compare_keep_days({"compare": {"enabled": True, "default_window_days": 30}}), 61)
        s = file_storage.FileStorage(Path(tempfile.mkdtemp()))
        old = NOW - 20 * DAY
        score_ledger.tick(s, "alpha", {"score": {"window_days": 7}}, [{"id": 1, "status": "completed", "conclusion": "success", "started": old, "repo": "a/x", "name": "CI", "seconds": 5}], [], now=NOW, force=True)
        self.assertEqual(len(s.load_doc("alpha", score_ledger.LEDGER_DOC)["runs"]), 0)      # 20 days old: gone with the usual 15
        score_ledger.tick(s, "alpha", {"score": {"window_days": 7}}, [{"id": 1, "status": "completed", "conclusion": "success", "started": old, "repo": "a/x", "name": "CI", "seconds": 5}], [], now=NOW, force=True, keep_days_min=61)
        self.assertEqual(len(s.load_doc("alpha", score_ledger.LEDGER_DOC)["runs"]), 1)


if __name__ == "__main__":
    unittest.main()
