# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The daily trend has many more series, all of them from the history the sentinel already keeps (no call to GitHub), and a chart of its own drawn in SVG: cards with the change against yesterday and
seven days ago, a range of 7/30/60 days, a threshold, marks of events, a tooltip, a second series to compare, a legend that switches the lines and CSV/JSON export. A day saved before a series existed
has no value (None), never a zero."""
import json
import re
import sys
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.sentinels import sentinel_local as sl

HERE = Path(__file__).resolve().parent.parent
PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
NEWER = {"sev_medium", "sev_low", "dur_avg", "dur_p95", "queue_avg", "flaky", "artifact_mb"}      # the series that came with the figures of the day (test_mon106_trend_series)
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
sys.path.insert(0, str(HERE.parent / "tools"))
try:
    import check_overflow
    import check_unfolded
except ImportError:      # the zip of the package has no tools folder
    check_unfolded = check_overflow = None


def snapshot():
    return {"repos": 10, "rate": {"limit": 5000, "remaining": 4000}, "a1": {"stuck": [{"repo": "a"}], "issues": [{}, {}]},
            "a2": {"workflows_checked": 20, "red": [{"repo": "b"}, {"repo": "a"}]}, "a3": {"severity": {"critical": 1, "high": 3}},
            "a4": {"stale_days": 7, "dependabot": [{"age_days": 9}, {"age_days": 2}, {"age_days": None}]}, "a5": {"pending_sign": [{}]},
            "a7": {"total24": 120}, "a11": {"ready": 2, "health": [{"score": 80}, {"score": 60}, {"score": None}]}}


class Backend(unittest.TestCase):
    def test_the_figures_of_a_day_come_from_the_snapshot(self):
        got = sl.daily_extras(snapshot())
        self.assertEqual({k: got[k] for k in sl.EXTRA_SERIES if k not in NEWER},
                         {"stuck": 1, "ci_green_pct": 90.0, "ci_repos_ok": 8, "issues_open": 2, "prs_old": 1, "unsigned": 1, "health": 70.0, "ready": 2, "quota_used_pct": 20.0, "minutes24": 120, "sev_critical": 1, "sev_high": 3})
        self.assertEqual(got["version"], sl.TOOL_VERSION)

    def test_what_cannot_be_told_is_none_and_never_zero(self):
        got = sl.daily_extras({})
        self.assertIsNone(got["ci_green_pct"])
        self.assertIsNone(got["health"])
        self.assertIsNone(got["quota_used_pct"])
        self.assertIsNone(got["minutes24"])

    def test_a_day_saved_before_a_series_existed_has_a_gap(self):
        history = {"days": {"2026-01-01": {"red": 2}, "2026-01-02": {"red": 1, "health": 80}}}
        self.assertEqual(sl.trend_gaps(history, "health")["values"], [None, 80])
        self.assertEqual(sl.trend(history, "health")["values"], [0, 80])      # the old series keep their zeros

    def test_the_series_of_the_page_are_the_ones_the_snapshot_carries(self):
        keys = re.findall(r'\["([a-z_0-9]+)","ui\.tr_', PAGE[PAGE.index("const TRS="):PAGE.index("let TRR=")])
        self.assertEqual(sorted(set(keys) - {"red", "codeql", "dependabot", "secret", "prs", "candidates"}), sorted(sl.EXTRA_SERIES))


class Page(unittest.TestCase):
    def test_every_series_and_every_text_exists_in_the_eight_languages(self):
        keys = set(re.findall(r'"(ui\.tr_[a-z_0-9]+)"', PAGE[PAGE.index("const TRS="):PAGE.index("function section(")]))
        self.assertGreaterEqual(len(keys), 30)
        for lang in LANGS:
            cat = json.loads((HERE / "assets" / "locales" / (lang + ".json")).read_text(encoding="utf-8"))
            self.assertEqual(sorted(k for k in keys if not cat.get(k)), [], lang)

    def test_the_chart_is_drawn_without_a_library_and_without_asking_github(self):
        block = PAGE[PAGE.index("const TRS="):PAGE.index("function section(")]
        self.assertNotIn("fetch(", block)
        self.assertNotIn("<script src", block)
        for needle in ("stroke-dasharray", "data-trexp", "data-trleg", "tr-range", "tr-cmp", "trCursor", "ArrowLeft", "pointermove", "trthr", "trev"):
            self.assertIn(needle, block, needle)


@unittest.skipUnless(check_unfolded is not None and check_overflow is not None and check_overflow.edge(), "no tools folder or no browser")
class InTheBrowser(unittest.TestCase):
    def test_the_cards_the_rich_trend_and_the_tooltip_of_the_settings_work_wide_and_narrow(self):
        results = check_unfolded.run(["en"], ("desktop", "mobile"), quiet=True)
        self.assertIsNotNone(results)
        bad = [(key, f) for key, found in results.items() for f in found if f["kind"].startswith(("sub_", "trend_", "tip_"))]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
