# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The webhook remembers its deliveries after a restart (a bounded private file that a damaged file does not break), can refuse events whose own time is old, and its allowance of good requests is a setting."""
import hashlib
import json
import os
import stat
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am, settings_api  # noqa: E402
from github_actions_monitor.security import localguard, webhook  # noqa: E402

SECRET = "m" * 40


def stamp(seconds_ago):
    return datetime.fromtimestamp(time.time() - seconds_ago, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def deliver(config, n=0, ago=0, event="workflow_run", address=None, delivery_id=None):
    inner = {"id": n + 1, "updated_at": stamp(ago), "status": "completed", "name": "CI"}
    raw = json.dumps({"repository": {"name": "R", "full_name": "JuanenRac/R"}, "workflow_run" if event == "workflow_run" else "workflow_job": inner}).encode()
    headers = {"X-GitHub-Event": event, "X-Hub-Signature-256": webhook.sign(SECRET, raw), "X-GitHub-Delivery": delivery_id or f"{n:08d}-aaaa-bbbb"}
    return webhook.handle(config, raw, headers, ["R"], address)


class Base(unittest.TestCase):
    def setUp(self):
        webhook.reset()
        localguard.reset_limits()
        self.addCleanup(localguard.reset_limits)
        self.addCleanup(webhook._store.update, path=None, dirty=False, saved=0.0)
        self.addCleanup(webhook.reset)
        patch = mock.patch.dict(os.environ, {webhook.SECRET_ENV: SECRET})
        patch.start()
        self.addCleanup(patch.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "deliveries.json"


class TheMemorySurvivesARestart(Base):
    CONFIG = {"webhook": {"enabled": True}}

    def test_a_delivery_accepted_before_a_restart_is_a_duplicate_after_it(self):
        webhook.load_memory(self.file)
        self.assertEqual(deliver(self.CONFIG, 1)[0], 200)
        webhook.save_memory(force=True)
        self.assertTrue(self.file.is_file())
        webhook.reset()      # the process ends
        self.assertEqual(webhook.load_memory(self.file), 2, "the id and the hash of the body")
        code, answer, _ = deliver(self.CONFIG, 1)
        self.assertEqual((code, answer.get("duplicate")), (202, True))
        self.assertEqual(deliver(self.CONFIG, 2)[0], 200, "another delivery is new")

    def test_the_file_is_private_bounded_and_written_at_most_every_few_seconds(self):
        webhook.load_memory(self.file)
        deliver(self.CONFIG, 1)
        self.assertTrue(self.file.is_file(), "the first delivery is written at once")
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(self.file.stat().st_mode), 0o600)
        self.assertFalse(webhook.save_memory(now=time.time() + 11), "nothing changed: nothing written")
        deliver(self.CONFIG, 2)
        self.assertEqual(len(json.loads(self.file.read_text(encoding="utf-8"))), 2, "written a moment ago: the second waits")
        self.assertTrue(webhook.save_memory(now=webhook._store["saved"] + 3))
        self.assertEqual(len(json.loads(self.file.read_text(encoding="utf-8"))), 4)
        many = {f"k{i}": time.time() - i for i in range(webhook.MAX_DELIVERIES + 500)}
        self.file.write_text(json.dumps(many), encoding="utf-8")
        webhook.reset()
        self.assertEqual(webhook.load_memory(self.file), webhook.MAX_DELIVERIES)

    def test_a_damaged_or_hand_edited_file_is_an_empty_memory(self):
        for text in ("{not json", "[]", "null", json.dumps({"a": "x", "b": True, "c": -5, "d": 10 ** 12, "e" * 200: 5}), b"\xff\xfe\x00".decode("latin-1")):
            self.file.write_text(text, encoding="utf-8")
            webhook.reset()
            self.assertEqual(webhook.load_memory(self.file), 0, text[:20])
        self.assertEqual(deliver(self.CONFIG, 3)[0], 200, "the receiver works with an empty memory")
        self.assertEqual(webhook.load_memory(Path(self.tmp.name) / "missing.json"), 0)

    def test_old_entries_are_not_loaded(self):
        self.file.write_text(json.dumps({"old": time.time() - 3 * 86400, "new": time.time() - 5}), encoding="utf-8")
        self.assertEqual(webhook.load_memory(self.file), 1)

    def test_it_can_be_switched_off_and_without_a_file_nothing_is_written(self):
        config = {"webhook": {"enabled": True, "persist_deliveries": False}}
        webhook.load_memory(self.file)
        deliver(config, 1)
        self.assertFalse(self.file.exists())
        webhook._store["path"] = None
        deliver(self.CONFIG, 5)
        self.assertFalse(webhook.save_memory(force=True))
        self.assertTrue(webhook.guard_settings({})["persist_deliveries"])


class OldEventsCanBeRefused(Base):
    def test_off_by_default_so_an_old_event_is_accepted(self):
        self.assertEqual(deliver({"webhook": {"enabled": True}}, 1, ago=10 * 3600)[0], 200)

    def test_on_an_event_older_than_the_window_is_answered_and_not_acted_on(self):
        config = {"webhook": {"enabled": True, "reject_stale": True, "replay_seconds": 600}}
        code, answer, repo = deliver(config, 1, ago=3600)
        self.assertEqual((code, answer.get("stale"), repo), (202, True, None))
        self.assertEqual(deliver(config, 2, ago=30)[0], 200)
        self.assertEqual(deliver(config, 3, ago=3600, event="ping")[0], 200, "only workflow events carry a time that is judged")

    def test_what_cannot_be_read_is_not_stale(self):
        self.assertFalse(webhook.event_is_stale("workflow_run", b"{not json", 60))
        self.assertFalse(webhook.event_is_stale("workflow_run", b'{"workflow_run": {"updated_at": "9999-99-99T99:99:99Z"}}', 60))
        self.assertFalse(webhook.event_is_stale("push", b"{}", 60))
        self.assertTrue(webhook.event_is_stale("workflow_job", json.dumps({"workflow_job": {"completed_at": stamp(5000)}}).encode(), 60))


class TheAllowanceOfGoodRequestsIsASetting(Base):
    def test_the_setting_decides_how_many_good_requests_an_address_may_send(self):
        config = {"webhook": {"enabled": True, "max_verified_per_minute": 3}}
        codes = [deliver(config, n, event="ping", address="tunnel")[0] for n in range(5)]
        self.assertEqual(codes, [200, 200, 200, 429, 429])
        self.assertEqual(webhook.guard_settings({})["max_verified_per_minute"], webhook.MAX_VERIFIED_PER_MINUTE)
        self.assertEqual(webhook.guard_settings({"webhook": {"max_verified_per_minute": 0}})["max_verified_per_minute"], webhook.MAX_VERIFIED_PER_MINUTE)

    def test_the_three_settings_have_a_row_a_default_and_texts_in_eight_languages(self):
        from github_actions_monitor import i18n
        for name in ("max_verified_per_minute", "reject_stale", "persist_deliveries"):
            self.assertIn("webhook." + name, settings_api.FIELDS)
            self.assertIn(name, am.DEFAULTS["webhook"])
            for lang in i18n.LANGS:
                with i18n.use_language(lang):
                    for prefix in ("cfg.f.webhook.", "cfg.h.webhook."):
                        self.assertNotEqual(i18n.t(prefix + name), prefix + name, (lang, prefix + name))
        self.assertFalse(am.DEFAULTS["webhook"]["reject_stale"])
        self.assertTrue(hashlib)


if __name__ == "__main__":
    unittest.main()
