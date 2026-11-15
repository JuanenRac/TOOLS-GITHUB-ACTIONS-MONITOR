# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The alert of a score that has dropped: when it is seen, how serious it is, that it shows in the panel and only goes out when asked, and that it appears once."""
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
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.integrations import notifiers  # noqa: E402
from github_actions_monitor.scoring import drop, engine, ledger  # noqa: E402
from github_actions_monitor.storage import file_storage  # noqa: E402

CFG = engine.settings({})
NOW = 1_800_000_000.0


def snap(score, delta, letter=None, state="scored", at=NOW):
    return {"state": state, "score": score, "letter": letter or engine.letter(score, CFG["grades"]), "trend": {"direction": "down", "delta": delta}, "at": at}


class Detect(unittest.TestCase):
    def test_ten_points_is_a_drop_and_nine_is_not(self):
        self.assertEqual(drop.detect(snap(90, -10), CFG)["reasons"], ["points"])      # 100 (A) -> 90 (A)
        self.assertIsNone(drop.detect(snap(90, -9.9), CFG))

    def test_a_lower_letter_is_a_drop_even_with_few_points(self):
        found = drop.detect(snap(89, -3), CFG)      # 92 (A) -> 89 (B)
        self.assertEqual((found["reasons"], found["from_letter"], found["to_letter"]), (["letter"], "A", "B"))

    def test_both_reasons_can_come_together(self):
        self.assertEqual(drop.detect(snap(78, -14), CFG)["reasons"], ["points", "letter"])      # 92 A -> 78 C
        self.assertEqual(drop.detect(snap(75, -10), CFG)["reasons"], ["points", "letter"])      # 85 B -> 75 C

    def test_a_better_score_or_the_same_letter_is_not_a_drop(self):
        self.assertIsNone(drop.detect(snap(95, 5), CFG))
        self.assertIsNone(drop.detect(snap(85, -4), CFG))      # 89 B -> 85 B

    def test_warning_and_critical_when_it_falls_to_E(self):
        self.assertEqual(drop.detect(snap(90, -10), CFG)["level"], "warning")
        self.assertEqual(drop.detect(snap(40, -20), CFG)["level"], "critical")

    def test_without_a_number_there_is_no_alert(self):
        for s in (snap(None, None, "A"), snap(70, -20, state="calibrating"), snap(70, -20, state="insufficient_data"), {}, None):
            self.assertIsNone(drop.detect(s, CFG))
        self.assertIsNone(drop.detect({"state": "scored", "score": 70, "letter": "C", "trend": {"direction": "unknown", "delta": None}}, CFG))

    def test_the_alert_can_be_switched_off_and_the_threshold_moved(self):
        self.assertIsNone(drop.detect(snap(75, -10), engine.settings({"score": {"alert": {"enabled": False}}})))
        self.assertIsNone(drop.detect(snap(90, -10), engine.settings({"score": {"alert": {"drop_points": 15}}})))
        self.assertIsNotNone(drop.detect(snap(90, -5), engine.settings({"score": {"alert": {"drop_points": 5}}})))


class Shapes(unittest.TestCase):
    def test_the_alert_has_the_shape_of_the_alerts_of_the_panel(self):
        snapshot = snap(75, -10)
        found = drop.detect(snapshot, CFG)
        a = drop.alert(snapshot, found, "alpha")
        for key in ("id", "code", "level", "sentinel", "account_id", "repo", "title", "details", "created_at"):
            self.assertIn(key, a)
        self.assertEqual((a["id"], a["code"], a["sentinel"], a["level"], a["account_id"]), ("score.dropped:alpha", "score.dropped", "system", "warning", "alpha"))
        self.assertIn("85", a["title"])
        self.assertTrue(a["created_at"].endswith("Z"))

    def test_the_event_is_the_one_the_channels_know(self):
        e = drop.event(drop.detect(snap(40, -20), CFG))
        self.assertEqual((e["kind"], e["code"], e["level"], e["owner"]), ("score_dropped", "score.dropped", "bad", "main"))
        self.assertIn("score_dropped", notifiers.KNOWN_EVENTS)
        schema = json.loads((HERE / "docs" / "schemas" / "notification_event.schema.json").read_text(encoding="utf-8"))
        self.assertIn("score_dropped", schema["properties"]["kind"]["enum"])

    def test_the_texts_exist_in_the_eight_languages_and_fill_in(self):
        for lang in i18n.LANGS:
            for key in ("score.alert_title", "evt.score_dropped"):
                text = i18n.tl(lang, key)
                self.assertNotEqual(text, key, (lang, key))
                filled = text.format(frm=1, to=2, from_letter="A", to_letter="B")
                self.assertTrue(all(token in filled for token in ("1", "2", "A", "B")), (lang, key))


class Edge(unittest.TestCase):
    def run_tick(self, storage, when, runs):
        return ledger.tick(storage, "alpha", {"score": {"min_runs": 5, "calibrating_hours": 0}}, runs, [], now=when, force=True)

    def test_the_drop_is_new_only_the_first_time_and_again_after_it_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = file_storage.FileStorage(Path(tmp))
            day = 86400.0
            t0 = NOW
            # a good week, then a bad one
            good = [{"id": i, "repo": "a/x", "name": f"w{i % 3}", "status": "completed", "conclusion": "success", "seconds": 100, "started": t0 - 10 * day + i * 600} for i in range(1, 30)]
            self.run_tick(storage, t0 - 5 * day, good)
            bad = [{"id": 100 + i, "repo": "a/x", "name": f"w{i % 3}", "status": "completed", "conclusion": "failure" if i % 6 else "success", "seconds": 100, "started": t0 + i * 600} for i in range(1, 40)]
            first = self.run_tick(storage, t0 + 3 * day, bad)
            self.assertTrue(first["drop"], first)
            self.assertTrue(first["drop_new"])
            second = self.run_tick(storage, t0 + 3 * day + 4000, [])
            self.assertTrue(second["drop"])
            self.assertFalse(second["drop_new"])
            self.assertTrue(storage.load_doc("alpha", ledger.LEDGER_DOC)["drop_open"])


class Panel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.storage = file_storage.FileStorage(Path(self.tmp.name))
        for patch in (mock.patch("github_actions_monitor.storage.runtime.process_storage", return_value=(self.storage, "alpha")),
                      mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value={})):
            patch.start()
            self.addCleanup(patch.stop)
        self.old = actions_monitor.LITE["on"]
        self.addCleanup(lambda: actions_monitor.LITE.update(on=self.old))
        actions_monitor.LITE["on"] = False

    def save(self, age, found):
        import time
        at = time.time() - age
        snapshot = {"schema": 1, "at": at, "state": "scored", "score": 75.0, "letter": "C", "trend": {"direction": "down", "delta": -10.0}, "drop": found}
        self.storage.save_score_snapshot("alpha", time.strftime("%Y-%m-%dT%H", time.gmtime(at)), snapshot)

    def test_a_fresh_drop_is_in_the_list_and_is_read_by_the_alerts_endpoint(self):
        self.save(60, drop.detect(snap(75, -10), CFG))
        found = actions_monitor.score_alerts()
        self.assertEqual([a["code"] for a in found], ["score.dropped"])
        self.assertIn("score_alerts()", __import__("inspect").getsource(actions_monitor.alerts_payload))

    def test_an_old_snapshot_or_no_drop_says_nothing(self):
        self.save(6 * 3600, drop.detect(snap(75, -10), CFG))
        self.assertEqual(actions_monitor.score_alerts(), [])
        self.save(60, None)
        self.assertEqual(actions_monitor.score_alerts(), [])

    def test_lite_never_has_it(self):
        self.save(60, drop.detect(snap(75, -10), CFG))
        actions_monitor.LITE["on"] = True
        self.assertEqual(actions_monitor.score_alerts(), [])

    def test_the_silence_of_the_system_alerts_covers_it(self):
        from github_actions_monitor.sentinels import alert_center
        self.save(60, drop.detect(snap(75, -10), CFG))
        a = actions_monitor.score_alerts()[0]
        live = [{"scope": "code", "value": "score.dropped", "until": NOW * 2, "at": NOW}]
        self.assertTrue(alert_center.muted_until(a, live))


class External(unittest.TestCase):
    def test_a_drop_goes_out_when_the_channels_are_on_without_being_listed_in_the_events(self):
        config = {"notify": {"enabled": True, "events": ["red_new"], "channels": {"http_local": {"enabled": True, "url": "http://127.0.0.1:9/x"}}}}
        sent = []
        with mock.patch.object(notifiers, "send_channel", side_effect=lambda n, c, e, *a, **k: sent.append(e["kind"]) or {"channel": n, "ok": True}):
            notifiers.notify(config, drop.event(drop.detect(snap(75, -10), CFG)))
            notifiers.notify(config, {"kind": "red_fixed", "owner": "main", "repo": "a", "text": "x", "url": None})
        self.assertEqual(sent, ["score_dropped"])

    def test_the_panel_only_default_does_not_emit(self):
        self.assertFalse(CFG["alert"]["notify_external"])
        source = __import__("inspect").getsource(actions_monitor.score_tick)
        self.assertIn('["alert"]["notify_external"]', source)


if __name__ == "__main__":
    unittest.main()
