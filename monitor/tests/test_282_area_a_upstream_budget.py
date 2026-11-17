# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The requests of the hour of the upstream follow-up survive a restart (a restart does not give back the allowance) and the panel says when one pass over the forks takes longer than the time between
two readings."""
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
import test_250_upstream as t250  # noqa: E402
import test_275_area_a_sentinel_quota as t275  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.data_pipeline import upstream  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402

NOW = 1_800_000_000.0


class TheRequestsOfTheHourSurviveARestart(unittest.TestCase):
    def test_the_requests_made_before_a_restart_still_count_after_it(self):
        account = t275.Account(self, 2, lambda *a: {})
        first = account.sentinel
        recent = [time.time() - 600, time.time() - 60]
        first.upstream_calls = recent + [time.time() - 7200]
        first._persist()
        again = sl.Sentinel(first.ctx, dict(first.config))
        self.assertEqual(sorted(again.upstream_calls), sorted(recent), "the two of the last hour, not the old one")
        self.assertEqual(again._upstream_requests(), 2)

    def test_a_damaged_list_is_an_empty_one(self):
        account = t275.Account(self, 1, lambda *a: {})
        s = account.sentinel
        for bad in ("x", [True, "a", None, 10 ** 12, -5], {"a": 1}):
            s._save(sl.CACHE_FILE, {"saved": time.time(), "upstream_calls": bad})
            self.assertEqual(sl.Sentinel(s.ctx, dict(s.config)).upstream_calls, [], repr(bad))


class ThePanelSaysHowLongAPassTakes(unittest.TestCase):
    def test_a_pass_longer_than_the_time_between_readings_is_continuous(self):
        forks = ["f%03d" % n for n in range(727)]
        cfg = t250.on()      # 12 h between readings, 6 requests an hour, 8 forks a request
        picture = upstream.build({}, forks, cfg, NOW)
        self.assertEqual((picture["followed"], picture["round_hours"], picture["continuous"], picture["refresh_hours"]), (727, 15.2, True, 12))
        small = upstream.build({}, forks[:48], cfg, NOW)
        self.assertEqual((small["round_hours"], small["continuous"]), (1.0, False))

    def test_the_text_exists_in_eight_languages_and_the_page_shows_it_only_when_continuous(self):
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                text = i18n.t("ui.upstream_round", n=727, hours=15.2, refresh=12)
                self.assertNotEqual(text, "ui.upstream_round", lang)
                self.assertTrue("727" in text and "15.2" in text and "12" in text, lang)
        html = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("u.continuous?", html)
        self.assertTrue(mock)


if __name__ == "__main__":
    unittest.main()
