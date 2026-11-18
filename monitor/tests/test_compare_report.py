# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The optional section "against the period before" of the scheduled report: absent unless `compare.include_in_report` asked for it (the report is then exactly the one it was), present in both
formats and the eight languages, escaped like the rest, and written by the service from the fourth thing the gatherer returns."""
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.reporting import report_builder as builder, report_render as render, report_service as service  # noqa: E402
from test_193_digest import SNAP, TEAM, alert, local  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
ANSWER = {"enabled": True, "state": "compared", "windows": {"days": 7.0}, "data_quality": {"reasons": []},
          "metrics": {"red_rate": {"now": 0.25, "base": 0.1, "direction": "worse", "state": "ok"}, "duration_p50": {"now": 60.0, "base": 120.0, "direction": "better", "state": "ok"},
                      "resolution": {"now": None, "base": 3600.0, "direction": "unknown", "state": "insufficient_data"}, "score_mean": {"now": 80.0, "base": None, "direction": "unknown", "state": "baseline_unavailable"}}}


class Section(unittest.TestCase):
    def test_without_the_setting_the_report_is_the_same_as_before(self):
        doc = builder.build("main", SNAP, [alert("a")], TEAM, 1_800_000_000)
        self.assertNotIn("compare", doc)
        self.assertNotIn("Against the period before", render.markdown(doc, "en"))
        self.assertNotIn("Against the period before", render.page(doc, "en"))
        self.assertNotIn("compare", builder.build("main", SNAP, [], TEAM, 1_800_000_000, compare={"enabled": False, "state": "off"}))

    def test_the_section_has_one_line_per_figure_in_both_formats(self):
        doc = builder.build("main", SNAP, [], TEAM, 1_800_000_000, compare=ANSWER)
        for text in (render.markdown(doc, "en").replace("\\", ""), render.page(doc, "en")):      # the Markdown escapes its marks
            self.assertIn("Against the period before", text)
            self.assertIn("Share of failed runs: 25.0% (before 10.0%, worse)", text)
            self.assertIn("Median duration: 1 min (before 2 min, better)", text)
            self.assertIn("Time to resolve alerts: not enough data", text)
            self.assertIn("Mean score: no baseline", text)

    def test_when_nothing_can_be_compared_the_reason_is_said(self):
        short = {"enabled": True, "state": "baseline_unavailable", "data_quality": {"reasons": ["history_too_short"]}, "metrics": {}}
        text = render.markdown(builder.build("main", SNAP, [], TEAM, 1_800_000_000, compare=short), "en").replace("\\", "")
        self.assertIn("No comparison this time: the history is shorter than compare.min_days_of_history.", text)

    def test_eight_languages_show_no_key(self):
        doc = builder.build("main", SNAP, [], TEAM, 1_800_000_000, compare=ANSWER)
        for lang in LANGS:
            for text in (render.markdown(doc, lang), render.page(doc, lang)):
                self.assertNotRegex(text, r"(report|ui)\.[a-z_0-9]+", lang)

    def test_a_hostile_name_cannot_make_markup(self):
        hostile = {**ANSWER, "metrics": {"<script>x</script>": {"now": 1, "base": 1, "direction": "same", "state": "ok"}}}
        doc = builder.build("main", SNAP, [], TEAM, 1_800_000_000, compare=hostile)
        self.assertNotIn("<script>x", render.page(doc, "en"))
        self.assertIn("\\<script\\>", render.markdown(doc, "en"))


class Service(unittest.TestCase):
    CFG = {"report_schedule": {"enabled": True, "cron": "0 8 * * 1", "formats": "markdown"}}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def written(self):
        at = local(2026, 11, 16, 8, 0)
        service.tick(self.CFG, "main", self.gather, now=at - 3600, base=self.tmp.name)
        result = service.tick(self.CFG, "main", self.gather, now=at + 30, base=self.tmp.name)
        data, _ = service.read_file("main", result["files"][0], self.tmp.name)
        return data.decode("utf-8")

    def test_the_fourth_thing_the_gatherer_returns_is_written(self):
        self.gather = lambda: (SNAP, [], TEAM, ANSWER)
        self.assertIn("Against the period before", self.written())

    def test_a_gatherer_with_three_things_still_works(self):
        self.gather = lambda: (SNAP, [], TEAM)
        self.assertNotIn("Against the period before", self.written())
        self.assertGreater(time.time(), 0)


if __name__ == "__main__":
    unittest.main()
