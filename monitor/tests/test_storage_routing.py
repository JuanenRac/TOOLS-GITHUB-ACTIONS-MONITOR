# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The modules that keep state reach it through state_io: with no storage bound they read and write their files exactly as they always did; with a SQLite storage bound the feed, what the
feed announced, the analytics, the state of the sentinels, the silences and the update notice live in the database, and the caches and logs stay files."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import updatecheck  # noqa: E402
from github_actions_monitor.data_pipeline import analytics, events, etagcache  # noqa: E402
from github_actions_monitor.sentinels import alert_center, sentinel_ai, sentinel_collab, sentinel_local  # noqa: E402
from github_actions_monitor.storage import runtime, sqlite_storage, state_io  # noqa: E402

RED = {"loading": 0, "enabled": True, "a2": {"red": [{"repo": "r", "workflow": "ci", "url": "u", "streak": 1, "since": "x"}]}}
CLEAN = {"loading": 0, "enabled": True}


class Bound(unittest.TestCase):
    """A SQLite storage for account `alpha`, bound to the paths the modules hold inside a temporary folder."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        names = [(events, "EVENTS_FILE", "events/events_monitor.jsonl"), (events, "STATE_FILE", "events/events_state.json"), (analytics, "HISTORY_FILE", "analytics/analytics_history.json"),
                 (sentinel_local, "CACHE_FILE", "sentinel_state/sentinel_cache.json"), (sentinel_local, "HISTORY_FILE", "sentinel_state/sentinel_history.json"),
                 (sentinel_ai, "CACHE_FILE", "sentinel_state/sentinel_ai_cache.json"), (sentinel_collab, "STATE_FILE", "sentinel_state/collab_state.json"),
                 (alert_center, "STATE_FILE", "alert_mutes.json"), (updatecheck, "STATE_FILE", "update_check.json")]
        for module, attribute, relative in names:
            patcher = mock.patch.object(module, attribute, self.root / "alpha" / relative)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.storage = sqlite_storage.SqliteStorage(self.root / "alpha" / "storage.sqlite3")
        self.addCleanup(self.storage.close)
        state_io.bind(self.storage, "alpha")
        self.addCleanup(state_io.unbind)

    def files(self):
        return sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file() and "storage.sqlite3" not in p.name)

    def test_the_feed_and_what_it_announced_live_in_the_database(self):
        feed = events.Feed(events.EVENTS_FILE, events.STATE_FILE)
        feed.feed(CLEAN)
        written = feed.feed(RED)
        self.assertEqual([e["kind"] for e in written], ["red_new"])
        (stored,) = self.storage.load_events("alpha", None, 10)
        self.assertEqual((stored["kind"], stored["repo"]), ("red_new", "r"))
        self.assertRegex(stored["at"], r"^\d{4}-")
        self.assertIsNotNone(self.storage.load_doc("alpha", "events_state"))
        self.assertEqual(self.files(), [], "nothing was written as a file")
        again = events.Feed(events.EVENTS_FILE, events.STATE_FILE)      # a restart knows what was announced: the same red is not announced twice
        self.assertEqual([e["kind"] for e in again.feed(RED) if e["kind"] != "loaded"], [])
        self.assertEqual([e["kind"] for e in again.feed(CLEAN)], ["red_fixed"])

    def test_emitted_events_of_other_sentinels_land_there_too(self):
        events.Feed(events.EVENTS_FILE, events.STATE_FILE).emit([{"kind": "collab_new", "code": "x", "text": "t", "level": "warn", "repo": "", "owner": "main", "url": None, "args": {}}])
        self.assertEqual([e["kind"] for e in self.storage.load_events("alpha", None, 10)], ["collab_new"])

    def test_analytics_survive_a_restart(self):
        store = analytics.Store(analytics.HISTORY_FILE)
        store.add_jobs("repo", "ci", 7, [], True)
        self.assertTrue(store.save())
        self.assertEqual(self.storage.load_analytics("alpha")["seen"], [7])
        self.assertTrue(analytics.Store(analytics.HISTORY_FILE).seen(7))

    def test_the_state_of_the_sentinels_the_silences_and_the_update_notice(self):
        sentinel_local.Sentinel._save(sentinel_local.CACHE_FILE, {"saved": 1, "repo_info": {"a": 1}})
        self.assertEqual(self.storage.load_sentinel_state("alpha", "sentinel_cache"), {"saved": 1, "repo_info": {"a": 1}})
        self.assertEqual(sentinel_local.Sentinel._load(sentinel_local.CACHE_FILE, {}), {"saved": 1, "repo_info": {"a": 1}})
        self.assertEqual(sentinel_local.Sentinel._load(sentinel_local.HISTORY_FILE, {"days": {}}), {"days": {}})      # nothing stored: the default
        ai = sentinel_ai.Store(sentinel_ai.CACHE_FILE)
        ai.put("k", {"at": "2026", "text": "t"})
        ai.save()
        self.assertEqual(sentinel_ai.Store(sentinel_ai.CACHE_FILE).get("k"), {"at": "2026", "text": "t"})
        self.assertIn("entries", self.storage.load_sentinel_state("alpha", "sentinel_ai_cache"))
        collab = {"alerts": {"a": {"repo": "r"}}, "per_repo": {}, "last_full_scan": None}
        state_io.save_text(sentinel_collab.STATE_FILE, json.dumps(collab))
        self.assertEqual(sentinel_collab.load_state(sentinel_collab.STATE_FILE)["alerts"], {"a": {"repo": "r"}})
        alert_center.mute("alert", "a1", 1, now=1000)
        self.assertEqual([m["value"] for m in alert_center.active(now=1001)], ["a1"])
        self.assertEqual([m["value"] for m in self.storage.load_doc("alpha", "alert_mutes")["active"]], ["a1"])
        updatecheck._save(updatecheck.STATE_FILE, {"checked_at": 5, "release": None})
        self.assertEqual(updatecheck._load(updatecheck.STATE_FILE)["checked_at"], 5)
        self.assertEqual(self.storage.load_doc("alpha", "update_check")["checked_at"], 5)
        self.assertEqual(self.files(), [])

    def test_caches_and_logs_stay_files(self):
        cache = etagcache.EtagCache(self.root / "alpha" / "cache" / "etag_cache.json")
        cache.put("k", "e", {"a": 1}) if hasattr(cache, "put") else None
        self.assertIsNone(state_io.routed(self.root / "alpha" / "cache" / "etag_cache.json"))
        self.assertIsNone(state_io.routed(self.root / "alpha" / "ai_actions_log.jsonl"))
        self.assertEqual(state_io.routed(events.EVENTS_FILE), ("events", None))

    def test_a_missing_item_raises_like_a_missing_file_and_a_broken_database_like_a_failed_write(self):
        with self.assertRaises(FileNotFoundError):
            state_io.load_json(events.STATE_FILE)
        with self.assertRaises(OSError):
            state_io.save_text(events.STATE_FILE, "not json")
        self.storage.close()
        self.storage._local = __import__("threading").local()
        self.storage._ready = True      # a connection that cannot be opened again
        with mock.patch.object(self.storage, "_conn", side_effect=sqlite_storage.sqlite3.OperationalError("disk I/O error")):
            with self.assertRaises(OSError):
                state_io.save_text(events.STATE_FILE, "{}")
            events.Feed(events.EVENTS_FILE, events.STATE_FILE).emit([{"kind": "k"}])      # the feed swallows the error like a failed file write: the monitor goes on


class Unbound(unittest.TestCase):
    def test_without_a_storage_the_files_are_read_and_written_as_before(self):
        state_io.unbind()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.json"
            state_io.save_text(path, '{"a": 1}')
            self.assertEqual(state_io.load_json(path), {"a": 1})
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["x.json"])
            with self.assertRaises(FileNotFoundError):
                state_io.load_json(Path(tmp) / "none.json")
            self.assertFalse(state_io.append_events(path, [{"a": 1}]))


class Runtime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(state_io.unbind)

    def test_the_file_backend_binds_nothing(self):
        for config in ({}, {"storage": {"backend": "file"}}, {"storage": 5}):
            self.assertIsNone(runtime.bind(config, "alpha", Path(self.tmp.name)))
            self.assertEqual(state_io.bound(), (None, None))

    def test_lite_ignores_sqlite_and_creates_no_database(self):
        self.assertIsNone(runtime.bind({"storage": {"backend": "sqlite"}}, None, Path(self.tmp.name), lite=True))
        self.assertEqual(list(Path(self.tmp.name).glob("*.sqlite3*")), [])

    def test_sqlite_binds_one_database_for_the_process(self):
        storage = runtime.bind({"storage": {"backend": "sqlite"}}, None, Path(self.tmp.name))
        self.addCleanup(storage.close)
        self.assertEqual(state_io.bound(), (storage, "default"))
        self.assertEqual(storage.path, Path(self.tmp.name) / "storage.sqlite3")

    def test_a_database_that_cannot_be_opened_stops_the_start(self):
        blocked = Path(self.tmp.name) / "blocker"
        blocked.write_text("a file where the folder of the database should be", encoding="utf-8")
        with self.assertRaises(Exception):
            runtime.bind({"storage": {"backend": "sqlite", "path": str(blocked / "x.db")}}, "alpha", Path(self.tmp.name))
        self.assertEqual(state_io.bound(), (None, None))


class ChildWithSqlite(unittest.TestCase):
    def test_an_account_process_keeps_its_state_in_the_database_of_its_folder(self):
        code = (
            "import json, os, sys, tempfile\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, %r)\n"
            "t = tempfile.mkdtemp()\n"
            "os.environ['MONITOR_ACCOUNTS_DIR'] = str(Path(t) / 'accounts')\n"
            "from github_actions_monitor.accounts import accounts, account_child\n"
            "path = accounts.create_account('alpha', 'a')\n"
            "cfg = json.loads(path.read_text(encoding='utf-8')); cfg['storage'] = {'backend': 'sqlite'}\n"
            "path.write_text(json.dumps(cfg), encoding='utf-8')\n"
            "root = Path(t) / 'accounts' / 'alpha'\n"
            "account_child.redirect('alpha')\n"
            "from github_actions_monitor.data_pipeline import events\n"
            "from github_actions_monitor.storage import state_io\n"
            "feed = events.Feed()\n"
            "feed.emit([{'kind': 'red_new', 'text': 'x'}])\n"
            "storage, account = state_io.bound()\n"
            "print('DB', (root / 'storage.sqlite3').is_file(), 'JSONL', (root / 'events' / 'events_monitor.jsonl').exists(), 'N', len(storage.load_events('alpha', None, 10)), account)\n") % str(HERE / "src")
        done = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=90)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue(done.stdout.strip().endswith("DB True JSONL False N 1 alpha"), done.stdout)


if __name__ == "__main__":
    unittest.main()
