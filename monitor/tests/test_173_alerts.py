# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.7.3, second part: one list of alerts for every sentinel, the local silences with an end (an alert, a rule or a whole sentinel), the label that makes Collab ignore an item, the
events endpoint, and that the page has the tab. The silences go to a temporary folder (never next to the code) and nothing reaches GitHub."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.sentinels import alert_center as ac  # noqa: E402
from github_actions_monitor.sentinels import sentinel_collab as sc  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402

NOW = 1_800_000_000


def alert(id_, code="ci.red", sentinel="ci", level="error", repo="o/r"):
    return {"id": id_, "code": code, "sentinel": sentinel, "level": level, "repo": repo, "title": id_, "details": {}, "created_at": "2026-01-01T00:00:00Z"}


class FakeRegistry:
    def __init__(self, alerts, broken=False):
        self._alerts, self.broken = alerts, broken

    def alerts(self):
        if self.broken:
            raise RuntimeError("a sentinel failed")
        return list(self._alerts)

    def names(self):
        return ["ci", "collab"]


class Silences(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(ac, "STATE_FILE", Path(self.tmp.name) / "alert_mutes.json")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_an_alert_a_rule_and_a_sentinel_can_each_be_silenced_and_only_what_they_cover(self):
        ac.mute("alert", "ci.red:o/r:build", 2, now=NOW)
        ac.mute("code", "collab.pr.draft_old", 3, now=NOW)
        ac.mute("sentinel", "ci", 1, now=NOW + 10)
        live = ac.active(NOW + 20)
        self.assertEqual(len(live), 3)
        self.assertTrue(ac.muted_until(alert("ci.red:o/r:build"), live))
        self.assertTrue(ac.muted_until(alert("x", code="collab.pr.draft_old", sentinel="collab"), live))
        self.assertTrue(ac.muted_until(alert("y", code="ci.stuck"), live))                       # the whole CI sentinel
        self.assertIsNone(ac.muted_until(alert("z", code="collab.issue.stale", sentinel="collab"), live))

    def test_a_silence_ends_by_itself_and_stays_in_the_history(self):
        ac.mute("alert", "a1", 1, now=NOW)
        self.assertEqual(len(ac.active(NOW + 3599)), 1)
        self.assertEqual(ac.active(NOW + 3601), [])
        self.assertEqual([h["value"] for h in ac.history()], ["a1"])

    def test_the_length_comes_from_the_settings_and_is_kept_in_bounds(self):
        self.assertEqual(ac.hours_setting({}), 24)
        self.assertEqual(ac.hours_setting({"alerts": {"mute_hours": 6}}), 6)
        for bad in (0, 721, "6", True, None, 2.5):
            self.assertEqual(ac.hours_setting({"alerts": {"mute_hours": bad}}), 24, bad)
        self.assertEqual(ac.mute("alert", "a", None, {"alerts": {"mute_hours": 5}}, now=NOW)["hours"], 5)
        self.assertEqual(ac.mute("alert", "b", 99999, None, now=NOW)["hours"], 24)             # out of range: the default, never an endless silence

    def test_a_silence_can_be_lifted_and_the_history_says_when(self):
        ac.mute("code", "ci.red", 5, now=NOW)
        self.assertTrue(ac.unmute("code", "ci.red", now=NOW + 60))
        self.assertFalse(ac.unmute("code", "ci.red", now=NOW + 61))
        self.assertEqual(ac.active(NOW + 62), [])
        self.assertTrue(ac.history()[0]["ended"])

    def test_a_scope_or_a_value_that_is_not_valid_is_refused(self):
        self.assertIsNone(ac.mute("everything", "x", 1))
        self.assertIsNone(ac.mute("alert", "   ", 1))
        self.assertEqual(ac.active(NOW), [])

    def test_the_same_silence_twice_is_one_entry_and_the_history_is_capped(self):
        ac.mute("alert", "a", 1, now=NOW)
        ac.mute("alert", "a", 2, now=NOW)
        self.assertEqual(len(ac.active(NOW)), 1)
        for i in range(ac.HISTORY + 20):
            ac.mute("alert", f"n{i}", 1, now=NOW)
        self.assertLessEqual(len(json.loads(ac.STATE_FILE.read_text(encoding="utf-8"))["history"]), ac.HISTORY)

    def test_a_damaged_file_is_an_empty_state(self):
        ac.STATE_FILE.write_text("{not json", encoding="utf-8")
        self.assertEqual(ac.active(NOW), [])
        self.assertTrue(ac.mute("alert", "a", 1, now=NOW))


class OneList(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(ac, "STATE_FILE", Path(self.tmp.name) / "alert_mutes.json")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def sample(self):
        return [alert("ci.red:1"), alert("ci.stuck:2", code="ci.stuck", level="warning"), alert("collab.pr.conflict:o/r:3", code="collab.pr.conflict", sentinel="collab", level="warning"),
                alert("collab.issue.critical:o/r:4", code="collab.issue.critical", sentinel="collab", level="error")]

    def test_the_two_sentinels_come_in_one_list_with_their_origin_and_the_filters_work(self):
        everything = ac.collect(FakeRegistry(self.sample()))
        self.assertEqual(len(everything), 4)
        self.assertEqual({a["sentinel"] for a in ac.select(everything)}, {"ci", "collab"})
        self.assertEqual({a["sentinel"] for a in ac.select(everything, sentinel="collab")}, {"collab"})
        self.assertEqual([a["level"] for a in ac.select(everything, level="warning")], ["warning", "warning"])
        self.assertEqual(ac.select(everything)[0]["level"], "error")                              # errors first

    def test_the_silenced_ones_are_shown_hidden_or_listed_alone(self):
        ac.mute("sentinel", "collab", 1, now=NOW)
        everything = ac.collect(FakeRegistry(self.sample()), now=NOW + 5)
        self.assertEqual(len(ac.select(everything, muted="show")), 4)
        self.assertEqual(len(ac.select(everything, muted="hide")), 2)
        self.assertEqual({a["sentinel"] for a in ac.select(everything, muted="only")}, {"collab"})
        summary = ac.summary(everything)
        self.assertEqual((summary["total"], summary["muted"]), (2, 2))
        self.assertEqual(summary["by_sentinel"], {"ci": 2})

    def test_a_sentinel_that_fails_does_not_blank_the_list_and_no_registry_is_an_empty_list(self):
        self.assertEqual(ac.collect(FakeRegistry(self.sample(), broken=True)), [])
        self.assertEqual(ac.collect(None), [])

    def test_the_endpoint_answers_with_the_list_the_counts_and_the_silences(self):
        from github_actions_monitor.app import actions_monitor as am
        ac.mute("alert", "ci.red:1", 3, now=NOW)
        with mock.patch.dict(am.SENTINEL, {"registry": FakeRegistry(self.sample())}):
            body = am.alerts_payload({"sentinel": "ci"})
            self.assertEqual({a["id"] for a in body["alerts"]}, {"ci.red:1", "ci.stuck:2"})
            self.assertEqual(body["sentinels"], ["ci", "collab"])
            self.assertIn("mutes", body)
            self.assertEqual(am.alerts_payload({"muted": "nonsense"})["alerts"].__len__(), 4)   # an unknown value is the default

    def test_the_posts_need_this_computer_and_a_token_and_the_page_goes_through_the_one_use_token(self):
        text = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        group = text.split('"/api/gh-action/plan", "/api/gh-action/confirm"', 1)[1].split("):", 1)[0]
        self.assertIn("/api/alerts/mute", group)
        self.assertIn("/api/alerts/unmute", group)
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("alerts\\/(mute|unmute)", page)
        lite = text.split("LITE_PATHS = (", 1)[1].split(")", 1)[0]
        self.assertIn("/api/alerts", lite)         # the lite product has no sentinel and answers none of them
        self.assertIn("/api/events", lite)

    def test_the_events_are_read_newest_first_filtered_and_a_bad_line_is_skipped(self):
        path = Path(self.tmp.name) / "events.jsonl"
        rows = [{"at": "2026-01-01T00:00:00Z", "kind": "red_new"}, {"at": "2026-01-02T00:00:00Z", "kind": "collab_new", "sentinel": "collab"}, {"at": "2026-01-03T00:00:00Z", "kind": "red_fixed"}]
        path.write_text("\n".join([json.dumps(rows[0]), "not json", json.dumps(rows[1]), json.dumps(rows[2])]) + "\n", encoding="utf-8")
        self.assertEqual([e["kind"] for e in ac.read_events(path)], ["red_fixed", "collab_new", "red_new"])
        self.assertEqual([e["kind"] for e in ac.read_events(path, sentinel="collab")], ["collab_new"])
        self.assertEqual([e["kind"] for e in ac.read_events(path, sentinel="ci")], ["red_fixed", "red_new"])
        self.assertEqual([e["kind"] for e in ac.read_events(path, since="2026-01-02T00:00:00Z")], ["red_fixed", "collab_new"])
        self.assertEqual(ac.read_events(Path(self.tmp.name) / "missing.jsonl"), [])


class IgnoreLabel(unittest.TestCase):
    def rules(self, **extra):
        rules = json.loads(json.dumps(sc.DEFAULTS["rules"]))
        rules.update(extra)
        return rules

    def test_an_issue_or_a_pull_request_with_the_label_raises_nothing(self):
        old = sc.stamp(NOW - 100 * 86400)
        issues = [{"number": 1, "title": "t", "url": "u", "created": old, "updated": old, "labels": ["Monitor:Ignore"], "bot": False}, {"number": 2, "title": "t", "url": "u", "created": old, "updated": old, "labels": [], "bot": False}]
        pulls = [{"number": 3, "title": "t", "url": "u", "created": old, "updated": old, "draft": True, "labels": ["monitor:ignore"], "review_requested": False, "bot": False},
                 {"number": 4, "title": "t", "url": "u", "created": old, "updated": old, "draft": True, "labels": [], "review_requested": False, "bot": False}]
        found = sc.evaluate("r", issues, pulls, self.rules(), NOW)
        self.assertEqual(sorted(a["number"] for a in found.values()), [2, 4])
        self.assertEqual(len(sc.evaluate("r", issues, pulls, self.rules(ignore_labels=[]), NOW)), 4)

    def test_the_setting_is_read_and_a_bad_value_keeps_the_default(self):
        self.assertEqual(sc.settings({})["rules"]["ignore_labels"], ["monitor:ignore"])
        self.assertEqual(sc.settings({"sentinels": {"collab": {"rules": {"ignore_labels": ["skip"]}}}})["rules"]["ignore_labels"], ["skip"])
        self.assertEqual(sc.settings({"sentinels": {"collab": {"rules": {"ignore_labels": "skip"}}}})["rules"]["ignore_labels"], ["monitor:ignore"])

    def test_the_labels_of_a_pull_request_are_kept(self):
        self.assertEqual(sc.slim_pull({"number": 1, "labels": [{"name": "monitor:ignore"}]})["labels"], ["monitor:ignore"])


class Wiring(unittest.TestCase):
    def test_the_silences_follow_the_account_and_are_never_published(self):
        from github_actions_monitor.accounts import accounts
        from github_actions_monitor.app import demo_mode
        import make_release
        self.assertIn(("github_actions_monitor.sentinels.alert_center", "STATE_FILE", "alert_mutes.json"), accounts.STATE_FILES)
        self.assertIn("alert_mutes.json", [name for name, _ in accounts.LEGACY])
        self.assertIn(("github_actions_monitor.sentinels.alert_center", "STATE_FILE", "alert_mutes_demo.json"), demo_mode.STATE_FILES)
        self.assertIn("alert_mutes.json", make_release.FORBIDDEN_NAMES)
        if (HERE.parent / ".gitignore").is_file():         # the zip of the package carries no .gitignore
            ignored = (HERE.parent / ".gitignore").read_text(encoding="utf-8").splitlines()
            for name in ("monitor/alert_mutes.json", "monitor/ai_alerts_state.json", "monitor/ALERTS_BRIEF.md"):
                self.assertIn(name, ignored)

    def test_the_page_has_the_alerts_tab_the_filters_and_the_live_checklist(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        for needle in ('id="t-al"', 'id="n-al"', "function renderAlerts", "/api/alerts", "alertMute", 'id="live-check"', 'const TABS=LITE?["now","charts","repos","hist","cfg"]:["now","al","sent"', ".lite #n-al"):
            self.assertIn(needle, page, needle)

    def test_the_new_settings_exist_with_their_texts_in_the_eight_languages(self):
        keys = ("sentinels.collab.rules.ignore_labels", "alerts.mute_hours")
        for key in keys:
            self.assertIn(key, settings_api.META, key)
        texts = {}
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            texts[lang] = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in keys:
                self.assertTrue(texts[lang].get("cfg.f." + key) and texts[lang].get("cfg.h." + key), (lang, key))
            for key in [k for k in texts["en"] if k.startswith(("ui.al_", "ui.live_ck_", "ui.tab_al"))]:
                self.assertTrue(texts[lang].get(key), (lang, key))


if __name__ == "__main__":
    unittest.main()
