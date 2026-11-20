# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The id of an alert never depends on the language: the panels of the Sentinel build the same alerts in the eight languages, and a persistent alert makes no new event when the language changes."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.integrations import ai_alerts  # noqa: E402
from github_actions_monitor.sentinels import sentinel_panels  # noqa: E402
from test_177_panels import snapshot  # noqa: E402

TITLES = {"en": "Incomplete published releases", "es": "Releases publicadas incompletas", "de": "Unvollständige Releases", "fr": "Releases incomplètes", "it": "Release incomplete",
          "ja": "不完全なリリース", "zh": "不完整的发布", "pt": "Releases publicadas incompletas"}


def full_snapshot(lang):
    """Every panel with something to say; the titles that come from the data (A10 sections) are written in the language of the moment, as the real sections are."""
    snap = snapshot()
    snap["a1"] = {"level": "bad", "stuck": [{"repo": "demo-alpha-app", "name": "CI", "status": "queued", "seconds": 9000, "url": "u"}], "issues": [{"repo": "demo-alpha-app", "number": 4, "title": "Broken", "url": "u"}]}
    snap["a6"] = {"level": "warn", "rows": [{"repo": "demo-beta-fw", "problems": [{"text": "no license"}]}]}
    snap["a7"] = {"level": "bad", "total24": 9, "budget": [{"ecosystem": "demo-eco", "used": 99, "limit": 10, "period": "day", "level": "over"}]}
    snap["a9"] = {"level": "warn", "boards": [{"name": "Roadmap", "problems": ["stale"], "url": "u"}]}
    snap["a10"] = {"level": "bad", "sections": [{"key": "release_assets", "title": TITLES[lang], "level": "bad", "count": 2, "rows": [["HYDRA-A", "v0.3.1", "assets"], ["HYDRA-B", "v0.2.7", "assets"]]},
                                                 {"key": "dead_schedule", "title": "Schedules " + lang, "level": "warn", "count": 1, "rows": [["demo-gamma-ui", "ci.yml"]]}]}
    snap["a11"] = {"level": "warn", "ready": 1, "behind": 0, "low_health": [{"ecosystem": "demo-eco", "score": 20}]}
    return snap


def panels_in(lang):
    return sentinel_panels.panels(full_snapshot(lang), lambda key, **values: i18n.tl(lang, key, **values), analytics={"enabled": True, "slower": [{"repo": "demo-alpha-app", "workflow": "CI"}], "duration": [1], "flaky": []},
                                  collab=[{"id": "c1", "repo": "demo-alpha-core", "title": "Critical " + lang, "level": "warn", "details": {"url": "u"}}], owner="demo-owner")


def ids_in(lang):
    return {ai_alerts.row_id(row) for row in sentinel_panels.alert_rows(panels_in(lang))}


class IdsDoNotDependOnTheLanguage(unittest.TestCase):
    def test_the_feed_of_every_panel_has_the_same_ids_in_the_eight_languages(self):
        base = ids_in("en")
        self.assertGreaterEqual(len(base), 12, "the sample must make alerts in many panels")
        panels_seen = {row["panel"] for row in sentinel_panels.alert_rows(panels_in("en"))}
        self.assertTrue({"a1", "a3", "a4", "a5", "a6", "a7", "a9", "a10", "a11", "a12", "a13", "collab"} <= panels_seen, panels_seen)
        for lang in i18n.LANGS:
            self.assertEqual(ids_in(lang), base, lang)
        built = [ai_alerts.build_alert(row, [], "") for row in sentinel_panels.alert_rows(panels_in("es"))]
        self.assertEqual({a["id"] for a in built}, base)
        self.assertEqual(len({ai_alerts.row_id(r) for r in sentinel_panels.alert_rows(panels_in("en"))}), len(sentinel_panels.alert_rows(panels_in("en"))), "two different findings never share an id")

    def test_the_titles_really_differ_between_languages(self):
        self.assertNotEqual([r["repo"] for r in sentinel_panels.alert_rows(panels_in("en")) if r["panel"] == "a10"], [r["repo"] for r in sentinel_panels.alert_rows(panels_in("es")) if r["panel"] == "a10"])

    def test_a_persistent_alert_makes_no_event_when_the_language_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {"ai_alerts": {"enabled": True, "folder": tmp}}
            first = ai_alerts.update(config, [], panels=panels_in("en"))
            self.assertTrue(first["opened"])
            feed = Path(tmp) / ai_alerts.FEED
            lines = feed.read_text(encoding="utf-8").splitlines()
            for lang in ("es", "en", "pt", "ja", "en"):
                again = ai_alerts.update(config, [], panels=panels_in(lang))
                self.assertEqual((again["opened"], again["resolved"]), ([], []), lang)
            self.assertEqual(feed.read_text(encoding="utf-8").splitlines(), lines, "no new line in the feed")
            state = json.loads((Path(tmp) / ai_alerts.STATE).read_text(encoding="utf-8"))
            self.assertEqual(len([a for a in state.values() if a["state"] == "open"]), len(first["alerts"]))

    def test_the_old_id_of_a_red_workflow_does_not_change(self):
        self.assertEqual(ai_alerts.row_id({"repo": "repo-a", "workflow": "CI"}), ai_alerts.alert_id("repo-a", "CI"))


if __name__ == "__main__":
    unittest.main()
