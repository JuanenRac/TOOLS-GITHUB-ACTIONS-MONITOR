# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The scheduled reports: the cron expression and when a run is owed, the content (no number the score would not show, what changed), the two renderings (every text escaped, no script, eight languages), the service (once per scheduled minute, the first run waits, a failure never stops the monitor, retention, only the files it wrote can be read) and the settings that agree with the example file and the page."""
import inspect
import json
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor, degraded, settings_api  # noqa: E402
from github_actions_monitor.reporting import builder, render, schedule, service  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
SNAP = {"state": "scored", "score": 82.5, "letter": "B", "trend": {"direction": "up", "delta": 3.0}, "coverage": 0.9, "missing_parts": [], "parts": [{"part": "speed", "score": 70, "weight": 15}]}
TEAM = {"all": 2, "totals": {"bad": 1, "warn": 0, "ok": 1, "unknown": 0}, "ranking": [{"repo": "a/x", "state": "bad", "risk": 55, "alerts": 2, "red_workflows": 1}, {"repo": "a/y", "state": "ok", "risk": 0, "alerts": 0, "red_workflows": 0}]}


def alert(id_, level="warning", title="t", muted=None):
    return {"id": id_, "level": level, "sentinel": "ci", "repo": "a/x", "title": title, **({"muted_until": muted} if muted else {})}


def local(y, mo, d, h, mi):
    return time.mktime((y, mo, d, h, mi, 0, 0, 0, -1))


class Cron(unittest.TestCase):
    def test_valid_and_invalid_expressions(self):
        for good in ("0 8 * * 1", "*/15 * * * *", "0 9-17/2 * * 1-5", "30 6 1,15 * *", "0 0 * * 7"):
            self.assertIsNotNone(schedule.parse(good), good)
        for bad in ("", "0 8 * *", "60 8 * * *", "0 24 * * *", "0 8 32 * *", "0 8 * 13 *", "a b c d e", "*/0 * * * *", "5-1 * * * *", "0 8 * * * *", None):
            self.assertIsNone(schedule.parse(bad), bad)

    def test_a_monday_at_eight(self):
        parsed = schedule.parse("0 8 * * 1")
        self.assertTrue(schedule.matches(parsed, time.localtime(local(2026, 11, 16, 8, 0))))
        self.assertFalse(schedule.matches(parsed, time.localtime(local(2026, 11, 17, 8, 0))))
        self.assertFalse(schedule.matches(parsed, time.localtime(local(2026, 11, 16, 8, 1))))

    def test_sunday_is_zero_and_seven(self):
        sunday = time.localtime(local(2026, 11, 15, 12, 0))
        self.assertTrue(schedule.matches(schedule.parse("0 12 * * 0"), sunday))
        self.assertTrue(schedule.matches(schedule.parse("0 12 * * 7"), sunday))

    def test_day_of_month_or_day_of_week_when_both_are_restricted(self):
        parsed = schedule.parse("0 8 1 * 1")
        self.assertTrue(schedule.matches(parsed, time.localtime(local(2026, 12, 1, 8, 0))))       # the 1st (a Tuesday)
        self.assertTrue(schedule.matches(parsed, time.localtime(local(2026, 11, 16, 8, 0))))      # a Monday that is not the 1st

    def test_due_once_after_the_named_minute(self):
        at = local(2026, 11, 16, 8, 0)
        self.assertTrue(schedule.due("0 8 * * 1", at + 30, at - 3600))
        self.assertFalse(schedule.due("0 8 * * 1", at + 3600, at + 5))      # it ran in that minute: nothing is owed until the next Monday

    def test_a_long_stop_produces_one_run_and_not_a_pile(self):
        now = local(2026, 11, 16, 9, 0)
        self.assertTrue(schedule.due("* * * * *", now, now - 40 * 86400))
        self.assertGreaterEqual(schedule.last_due(schedule.parse("* * * * *"), now, now - 40 * 86400), now - 120)

    def test_an_invalid_expression_is_never_due(self):
        self.assertFalse(schedule.due("nonsense", time.time(), 0))


class Content(unittest.TestCase):
    def test_no_number_unless_the_score_is_scored(self):
        for state in ("calibrating", "insufficient_data", "off"):
            part = builder.score_part({"state": state, "score": 99, "letter": "A", "parts": [{"part": "speed"}]})
            self.assertEqual((part["score"], part["letter"], part["parts"]), (None, None, []), state)
        self.assertEqual(builder.score_part(SNAP)["score"], 82.5)
        self.assertEqual(builder.score_part(None)["state"], "off")

    def test_silenced_alerts_are_not_open_and_the_worst_come_first(self):
        part = builder.alerts_part([alert("a", "info"), alert("b", "critical"), alert("c", "warning", muted="2999"), alert("d", "error")], 2)
        self.assertEqual((part["total"], [a["id"] for a in part["items"]]), (3, ["b", "d"]))

    def test_a_text_is_cut_so_nothing_long_can_hide_in_a_report(self):
        part = builder.alerts_part([alert("a", title="x" * 5000)], 5)
        self.assertEqual(len(part["items"][0]["title"]), builder.CUT)

    def test_the_first_report_has_nothing_to_compare_and_the_next_one_does(self):
        first = builder.build("main", SNAP, [alert("a")], TEAM, 1_800_000_000)
        self.assertTrue(first["changes"]["first"])
        memory = builder.memory(first, [alert("a")])
        second = builder.build("main", {**SNAP, "score": 80.0}, [alert("a"), alert("b")], TEAM, 1_800_003_600, memory)
        self.assertEqual((second["changes"]["first"], second["changes"]["score_delta"], second["changes"]["new_alerts"], second["changes"]["gone_alerts"]), (False, -2.5, ["b"], 0))

    def test_the_document_holds_no_key_that_looks_like_a_secret(self):
        doc = builder.build("main", SNAP, [alert("a")], TEAM, 1_800_000_000)
        self.assertNotRegex(json.dumps(doc).lower(), r"token|password|secret|authorization")


class Rendering(unittest.TestCase):
    def doc(self):
        hostile = '<script>alert(1)</script> | **x** [l](http://e) `c`'
        return builder.build('acc"<b>', SNAP, [alert("a", "critical", title=hostile)], {**TEAM, "ranking": [{**TEAM["ranking"][0], "repo": hostile}]}, 1_800_000_000)

    def test_the_html_escapes_every_text_and_has_no_script_or_outside_address(self):
        page = render.page(self.doc(), "en")
        self.assertNotIn("<script", page.lower())
        self.assertIn("&lt;script&gt;", page)
        self.assertNotRegex(page, r"(?i)(src|href)=\"https?://")
        self.assertIn("@media print", page)

    def test_the_markdown_does_not_let_the_data_make_formatting_or_links(self):
        text = render.markdown(self.doc(), "en")
        self.assertIn("\\<script\\>", text)
        self.assertIn("\\[l\\]", text)
        self.assertNotIn("](http", text)
        self.assertIn("\\|", text)

    def test_eight_languages_have_every_text_and_none_shows_a_key(self):
        doc = builder.build("main", SNAP, [alert("a")], TEAM, 1_800_000_000)
        calibrating = builder.build("main", {"state": "calibrating"}, [], {"all": 0, "totals": {}, "ranking": []}, 1_800_000_000)
        for lang in LANGS:
            for text in (render.markdown(doc, lang), render.page(doc, lang), render.markdown(calibrating, lang)):
                self.assertNotRegex(text, r"report\.[a-z_]+", lang)

    def test_the_two_renderings_say_the_same_number(self):
        doc = builder.build("main", SNAP, [], TEAM, 1_800_000_000)
        self.assertIn("82.5", render.markdown(doc, "en"))
        self.assertIn("82.5", render.page(doc, "en"))


class Service(unittest.TestCase):
    CFG = {"report_schedule": {"enabled": True, "cron": "0 8 * * 1"}}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = self.tmp.name
        self.calls = []

    def gather(self):
        self.calls.append(1)
        return SNAP, [alert("a")], TEAM

    def test_everything_is_off_by_default_and_a_bad_value_falls_back(self):
        self.assertFalse(service.settings({})["enabled"])
        got = service.settings({"report_schedule": {"enabled": "yes", "cron": "x", "formats": "pdf", "keep": 0, "top": 999}})
        self.assertEqual(got, service.DEFAULTS)
        self.assertIsNone(service.tick({}, "main", self.gather, now=time.time(), base=self.base))
        self.assertEqual(self.calls, [])

    def test_the_first_tick_only_starts_the_clock(self):
        at = local(2026, 11, 16, 8, 0)
        self.assertIsNone(service.tick(self.CFG, "main", self.gather, now=at + 5, base=self.base))
        self.assertEqual(self.calls, [])
        self.assertEqual(service.listing("main", self.base), [])

    def test_a_report_is_written_once_for_the_scheduled_minute(self):
        at = local(2026, 11, 16, 8, 0)
        service.tick(self.CFG, "main", self.gather, now=at - 3600, base=self.base)
        done = service.tick(self.CFG, "main", self.gather, now=at + 20, base=self.base)
        self.assertEqual(len(done["files"]), 2)
        self.assertIsNone(service.tick(self.CFG, "main", self.gather, now=at + 50, base=self.base))
        self.assertIsNone(service.tick(self.CFG, "main", self.gather, now=at + 3600, base=self.base))
        self.assertEqual(len(self.calls), 1)

    def test_the_formats_setting_chooses_the_files(self):
        for formats, count in (("html", 1), ("markdown", 1), ("both", 2)):
            with tempfile.TemporaryDirectory() as tmp:
                done = service.run({"report_schedule": {"formats": formats}}, "main", SNAP, [], TEAM, now=1_800_000_000, base=tmp)
                self.assertEqual(len(done["files"]), count, formats)

    def test_a_failure_is_noted_and_the_slot_is_used(self):
        at = local(2026, 11, 16, 8, 0)
        service.tick(self.CFG, "main", self.gather, now=at - 3600, base=self.base)

        def broken():
            raise RuntimeError("no data")
        with mock.patch.object(degraded, "note") as note:
            self.assertIsNone(service.tick(self.CFG, "main", broken, now=at + 5, base=self.base))
            self.assertIsNone(service.tick(self.CFG, "main", broken, now=at + 30, base=self.base))
        self.assertEqual(note.call_count, 1)

    def test_the_oldest_runs_go_when_there_are_more_than_keep(self):
        cfg = {"report_schedule": {"keep": 2, "formats": "markdown"}}
        for i in range(4):
            service.run(cfg, "main", SNAP, [], TEAM, now=1_800_000_000 + i * 100, base=self.base)
        names = [r["name"] for r in service.listing("main", self.base)]
        self.assertEqual(len(names), 2)
        self.assertTrue(names[0] > names[1])

    def test_listing_and_reading_belong_to_the_account_and_to_the_files_the_service_wrote(self):
        service.run({}, "alpha", SNAP, [], TEAM, now=1_800_000_000, base=self.base)
        service.run({}, "beta", SNAP, [], TEAM, now=1_800_000_000, base=self.base)
        mine = service.listing("alpha", self.base)
        self.assertEqual({r["kind"] for r in mine}, {"html", "markdown"})
        name = mine[0]["name"]
        self.assertIsNotNone(service.read_file("alpha", name, self.base))
        self.assertIsNone(service.read_file("beta", name, self.base))
        for bad in ("../x", "..\\x", "report_alpha_20260101-000000.html/../..", "_state.json", "report_alpha_1.html", "", None, "/etc/passwd"):
            self.assertIsNone(service.read_file("alpha", bad, self.base), bad)

    def test_the_memory_file_is_not_a_report_and_holds_no_text_of_an_alert(self):
        service.run({}, "main", SNAP, [alert("a", title="secret title")], TEAM, now=1_800_000_000, base=self.base)
        self.assertNotIn("_state.json", [r["name"] for r in service.listing("main", self.base)])
        state = next(Path(self.base).rglob("_state.json")).read_text(encoding="utf-8")
        self.assertNotIn("secret title", state)


class Wiring(unittest.TestCase):
    def test_the_routes_exist_and_lite_is_refused(self):
        source = inspect.getsource(actions_monitor)
        for needle in ('"/api/report-files"', '"/api/report-files/file"', '"/api/report-files/run"', "report_tick(", "def report_gather"):
            self.assertIn(needle, source, needle)
        self.assertIn("/api/report-files", actions_monitor.LITE_PATHS)

    def test_the_run_is_not_a_maintainer_route(self):
        from github_actions_monitor.security import auth
        self.assertNotIn("/api/report-files/run", auth.MAINTAINER_POST)

    def test_the_settings_of_the_page_the_service_and_the_example_agree(self):
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["report_schedule"], service.DEFAULTS)
        keys = sorted(k for k in settings_api.FIELDS if k.startswith("report_schedule."))
        self.assertEqual(keys, ["report_schedule.cron", "report_schedule.enabled", "report_schedule.formats", "report_schedule.keep", "report_schedule.top"])
        for key in keys:
            ok, clean = settings_api.check_value(key, service.DEFAULTS[key.split(".")[1]])
            self.assertTrue(ok, (key, clean))
        self.assertFalse(settings_api.check_value("report_schedule.cron", "61 8 * * 1")[0])
        self.assertFalse(settings_api.check_value("report_schedule.cron", "0 8 * *")[0])

    def test_every_text_of_the_page_and_of_the_settings_is_in_the_eight_languages(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        used = set(re.findall(r'"(ui\.rep_[a-z_]+)"', page)) | set(re.findall(r'data-i18n="(ui\.rep_[a-z_]+)"', page)) | {"ui.rs_kind_html", "ui.rs_kind_markdown", "ui.cfg_b_report_schedule"}
        used = {k for k in used if not k.endswith("_")}
        used |= {f"cfg.{p}.report_schedule.{n}" for p in "fh" for n in ("enabled", "cron", "formats", "keep", "top")}
        for lang in LANGS:
            keys = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(k for k in used if k not in keys), [], lang)


if __name__ == "__main__":
    unittest.main()
