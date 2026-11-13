# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The storage layer: one contract that every backend must keep (`Contract`, run once per backend), plus what is specific to the file backend (the layout of accounts/<id>/ is the
one the monitor has always written, a write is atomic, a feed written by several threads loses no line) and the factory."""
import gzip
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.storage import backup as backup_module  # noqa: E402
from github_actions_monitor.storage import base, factory, file_storage  # noqa: E402
from github_actions_monitor.data_pipeline import events  # noqa: E402

OLD, NEW = "2026-01-01T00:00:00Z", "2026-06-01T12:00:00Z"


class Contract:
    """What every backend must do. A subclass sets `make()` (a new empty storage) and `reopen()` (a second storage over the same data, as another process would see it)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.storage = self.make()
        self.addCleanup(self.storage.close)

    def make(self):
        raise NotImplementedError

    def add_account(self, account_id="alpha"):
        self.storage.save_config(account_id, {"github_owner": account_id})

    def test_configuration_round_trip_and_empty_when_missing(self):
        self.assertEqual(self.storage.load_config("alpha"), {})
        self.storage.save_config("alpha", {"github_owner": "me", "repos": ["a", "b"], "ñ": "日本"})
        self.assertEqual(self.storage.load_config("alpha"), {"github_owner": "me", "repos": ["a", "b"], "ñ": "日本"})
        self.assertEqual(self.storage.load_config("beta"), {})

    def test_sentinel_state_and_documents_are_separate_names(self):
        self.storage.save_sentinel_state("alpha", "sentinel_cache", {"x": 1})
        self.storage.save_sentinel_state("alpha", "collab_state", {"y": 2})
        self.storage.save_doc("alpha", "alert_mutes", {"active": [], "history": []})
        self.storage.save_doc("alpha", "events_state", {"reds": {}})
        self.assertEqual(self.storage.load_sentinel_state("alpha", "sentinel_cache"), {"x": 1})
        self.assertEqual(self.storage.load_sentinel_state("alpha", "collab_state"), {"y": 2})
        self.assertEqual(self.storage.load_sentinel_state("alpha", "nothing"), {})
        self.assertEqual(self.storage.load_doc("alpha", "alert_mutes"), {"active": [], "history": []})
        self.assertEqual(self.storage.load_doc("alpha", "events_state"), {"reds": {}})
        self.assertIsNone(self.storage.load_doc("alpha", "missing"))
        self.assertEqual(self.storage.load_doc("alpha", "missing", {"d": 1}), {"d": 1})
        self.storage.save_doc("alpha", "custom_thing", {"z": 3})
        self.assertEqual(self.storage.load_doc("alpha", "custom_thing"), {"z": 3})

    def test_accounts_do_not_see_each_other(self):
        for name in ("alpha", "beta"):
            self.add_account(name)
            self.storage.save_sentinel_state(name, "sentinel_cache", {"who": name})
            self.storage.append_event(name, {"kind": "red_new", "text": name})
        self.assertEqual(self.storage.load_sentinel_state("alpha", "sentinel_cache"), {"who": "alpha"})
        self.assertEqual([e["text"] for e in self.storage.load_events("beta", None, 10)], ["beta"])
        self.assertEqual(self.storage.list_accounts(), ["alpha", "beta"])

    def test_events_come_back_in_time_order_with_since_and_limit(self):
        self.add_account()
        rows = [{"at": "2026-03-01T00:00:00Z", "kind": "b"}, {"at": "2026-01-01T00:00:00Z", "kind": "a"}, {"at": "2026-05-01T00:00:00Z", "kind": "c"}]
        self.storage.append_events("alpha", rows)
        self.assertEqual([e["kind"] for e in self.storage.load_events("alpha", None, 10)], ["a", "b", "c"])
        self.assertEqual([e["kind"] for e in self.storage.load_events("alpha", None, 2)], ["b", "c"])
        self.assertEqual([e["kind"] for e in self.storage.load_events("alpha", "2026-03-01T00:00:00Z", 10)], ["b", "c"])
        self.assertEqual(self.storage.load_events("alpha", None, 0), [])
        self.assertEqual(len(self.storage.load_events("alpha", None, None)), 3)
        self.assertEqual(self.storage.load_events("beta", None, 10), [])

    def test_an_event_without_a_time_gets_the_time_of_now(self):
        self.add_account()
        self.storage.append_event("alpha", {"kind": "x", "text": "t"})
        (event,) = self.storage.load_events("alpha", None, 10)
        self.assertRegex(event["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(event["text"], "t")

    def test_the_same_data_is_seen_by_a_second_storage_over_it(self):
        self.add_account()
        self.storage.append_event("alpha", {"at": NEW, "kind": "k"})
        self.storage.save_sentinel_state("alpha", "sentinel_cache", {"x": 1})
        other = self.reopen()
        self.addCleanup(other.close)
        self.assertEqual(other.load_events("alpha", None, 10)[0]["kind"], "k")
        self.assertEqual(other.load_sentinel_state("alpha", "sentinel_cache"), {"x": 1})

    def test_unsafe_names_are_refused(self):
        for bad in ("../x", "a/b", "A", "", "x" * 80, ".hidden", "a b"):
            with self.assertRaises(base.StorageError, msg=repr(bad)):
                self.storage.load_sentinel_state("alpha", bad)
            with self.assertRaises(base.StorageError, msg=repr(bad)):
                self.storage.save_doc("alpha", bad, {})
        for bad in ("../a", "Alpha", "", "a" * 50, "_global"):
            with self.assertRaises(base.StorageError, msg=repr(bad)):
                self.storage.load_config(bad)
        with self.assertRaises(base.StorageError):
            self.storage.put_record("passwords", "k", {})
        with self.assertRaises(base.StorageError):
            self.storage.put_record("users", "../k", {})

    def test_records_users_and_sessions(self):
        self.storage.put_record("users", "ana", {"role": "admin"})
        self.storage.put_record("users", "bob", {"role": "viewer"})
        self.storage.put_record("user_accounts", "ana:alpha", {"user": "ana", "account": "alpha"})
        self.storage.put_record("sessions", "s1", {"user": "ana"}, expires=100.0)
        self.storage.put_record("sessions", "s2", {"user": "bob"}, expires=900.0)
        self.storage.put_record("sessions", "s3", {"user": "bob"})
        self.assertEqual(self.storage.get_record("users", "ana"), {"role": "admin"})
        self.assertIsNone(self.storage.get_record("users", "nobody"))
        self.assertEqual(set(self.storage.list_records("users")), {"ana", "bob"})
        self.storage.put_record("users", "ana", {"role": "maintainer"})
        self.assertEqual(self.storage.get_record("users", "ana"), {"role": "maintainer"})
        self.assertEqual(self.storage.purge_records("sessions", 500.0), 1)
        self.assertEqual(set(self.storage.list_records("sessions")), {"s2", "s3"})
        self.assertTrue(self.storage.delete_record("users", "bob"))
        self.assertFalse(self.storage.delete_record("users", "bob"))
        self.assertEqual(self.storage.list_records("users"), {"ana": {"role": "maintainer"}})

    def test_purging_events_removes_only_old_events_and_never_touches_the_state(self):
        self.add_account()
        self.storage.save_sentinel_state("alpha", "sentinel_cache", {"keep": True})
        self.storage.save_doc("alpha", "alert_mutes", {"active": [1], "history": []})
        self.storage.save_analytics("alpha", {"seen": [], "daily": {"2026-01-01": {"a": 1}, "2026-06-01": {"a": 2}}})
        self.storage.append_events("alpha", [{"at": OLD, "kind": "old"}, {"at": NEW, "kind": "new"}])
        result = self.storage.purge_events("alpha", "2026-03-01T00:00:00Z")
        self.assertEqual((result["removed"], result["kept"], result["archived"]), (1, 1, ""))
        self.assertEqual([e["kind"] for e in self.storage.load_events("alpha", None, 10)], ["new"])
        self.assertEqual(self.storage.load_config("alpha"), {"github_owner": "alpha"})
        self.assertEqual(self.storage.load_sentinel_state("alpha", "sentinel_cache"), {"keep": True})
        self.assertEqual(self.storage.load_doc("alpha", "alert_mutes"), {"active": [1], "history": []})
        self.assertEqual(self.storage.purge_analytics("alpha", "2026-03-01"), {"removed": 1})
        self.assertEqual(set(self.storage.load_analytics("alpha")["daily"]), {"2026-06-01"})
        self.assertEqual(self.storage.purge_analytics("alpha", "2026-03-01"), {"removed": 0})
        self.assertEqual(self.storage.purge_events("alpha", "2026-03-01T00:00:00Z")["removed"], 0)

    def test_archiving_writes_the_old_events_to_a_gz_before_removing_them(self):
        self.add_account()
        self.storage.append_events("alpha", [{"at": OLD, "kind": "old", "text": "日本"}, {"at": NEW, "kind": "new"}])
        archive = Path(self.tmp.name) / "archive"
        result = self.storage.purge_events("alpha", "2026-03-01T00:00:00Z", archive_dir=archive)
        self.assertEqual(result["removed"], 1)
        files = list(archive.glob("*.jsonl.gz"))
        self.assertEqual([str(f) for f in files], [result["archived"]])
        rows = [json.loads(line) for line in gzip.open(files[0], "rt", encoding="utf-8").read().splitlines()]
        self.assertEqual([r["kind"] for r in rows], ["old"])
        self.assertEqual(rows[0]["text"], "日本")
        self.assertEqual([e["kind"] for e in self.storage.load_events("alpha", None, 10)], ["new"])

    def test_events_without_a_time_are_never_purged(self):
        self.add_account()
        self.storage.import_account("alpha", {"events": [{"kind": "no_time"}, {"at": OLD, "kind": "old"}]})
        self.storage.purge_events("alpha", "2026-03-01T00:00:00Z")
        self.assertEqual([e["kind"] for e in self.storage.load_events("alpha", None, 10)], ["no_time"])

    def test_event_stats(self):
        self.add_account()
        self.assertEqual(self.storage.event_stats("alpha")["count"], 0)
        self.storage.append_events("alpha", [{"at": NEW, "kind": "n"}, {"at": OLD, "kind": "o"}])
        stats = self.storage.event_stats("alpha")
        self.assertEqual((stats["count"], stats["oldest"], stats["newest"]), (2, OLD, NEW))
        self.assertGreater(stats["bytes"], 0)

    def fill(self):
        self.add_account("alpha")
        self.add_account("beta")
        for name in ("alpha", "beta"):
            self.storage.save_sentinel_state(name, "sentinel_cache", {"who": name})
            self.storage.save_doc(name, "alert_mutes", {"active": [], "history": []})
            self.storage.save_analytics(name, {"seen": [1, 2], "daily": {"2026-06-01": {"k": 1}}})
            self.storage.append_events(name, [{"at": OLD, "kind": "a", "args": {"n": 1}}, {"at": NEW, "kind": "b"}])
        self.storage.put_record("users", "ana", {"role": "admin"})
        self.storage.put_record("sessions", "s", {"user": "ana"}, expires=5.0)

    def test_export_and_import_reproduce_an_account(self):
        self.fill()
        payload = self.storage.export_account("alpha")
        self.assertEqual(payload["sentinels"], {"sentinel_cache": {"who": "alpha"}})
        self.assertEqual(payload["docs"], {"alert_mutes": {"active": [], "history": []}})
        self.assertEqual(len(payload["events"]), 2)
        second = self.make()
        self.addCleanup(second.close)
        second.import_account("alpha", payload)
        second.import_account("alpha", payload)       # idempotent
        self.assertEqual(second.export_account("alpha"), payload)

    def test_backup_verify_and_restore_into_an_empty_storage(self):
        self.fill()
        zip_path = Path(self.tmp.name) / "backup.zip"
        manifest = self.storage.backup(zip_path)
        self.assertEqual((manifest["accounts"], manifest["events"], manifest["backend"]), (2, 4, self.storage.backend))
        self.assertEqual(backup_module.verify_backup(zip_path), [])
        target = self.make()
        self.addCleanup(target.close)
        self.assertEqual(backup_module.restore_backup(zip_path, target), {"accounts": 2, "events": 4})
        self.assertEqual(target.list_accounts(), ["alpha", "beta"])
        for name in ("alpha", "beta"):
            self.assertEqual(target.export_account(name), self.storage.export_account(name))
        self.assertEqual(target.export_records(), self.storage.export_records())
        with self.assertRaises(base.StorageError):      # not over data that is already there
            backup_module.restore_backup(zip_path, target)
        backup_module.restore_backup(zip_path, target, force=True)
        self.assertEqual(target.verify(), [])

    def test_a_damaged_backup_is_detected_and_not_restored(self):
        import zipfile
        self.fill()
        good = Path(self.tmp.name) / "good.zip"
        self.storage.backup(good)
        bad = Path(self.tmp.name) / "bad.zip"
        with zipfile.ZipFile(good) as source, zipfile.ZipFile(bad, "w") as out:
            for name in source.namelist():
                data = source.read(name)
                if name == backup_module.DUMP:
                    data = data.replace(b'"kind": "a"', b'"kind": "z"', 1)
                out.writestr(name, data)
        self.assertTrue(any("checksum" in p for p in backup_module.verify_backup(bad)))
        junk = Path(self.tmp.name) / "junk.zip"
        junk.write_bytes(b"not a zip")
        self.assertTrue(backup_module.verify_backup(junk))
        self.assertTrue(backup_module.verify_backup(Path(self.tmp.name) / "none.zip"))
        target = self.make()
        self.addCleanup(target.close)
        with self.assertRaises(base.StorageError):
            backup_module.restore_backup(bad, target)
        self.assertEqual(target.list_accounts(), [])

    def test_verify_of_sound_data_is_empty(self):
        self.fill()
        self.assertEqual(self.storage.verify(), [])


class FileContract(Contract, unittest.TestCase):
    def make(self):
        return file_storage.FileStorage(Path(self.tmp.name) / ("accounts" + str(len(os.listdir(self.tmp.name)))), "accounts")

    def reopen(self):
        return file_storage.FileStorage(self.storage.root, "accounts")


class FileLayout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_the_files_are_where_the_monitor_has_always_put_them(self):
        s = file_storage.FileStorage(self.root, "accounts")
        s.save_config("alpha", {"github_owner": "x"})
        s.save_sentinel_state("alpha", "sentinel_cache", {"a": 1})
        s.save_sentinel_state("alpha", "collab_state", {"a": 1})
        s.save_doc("alpha", "events_state", {"a": 1})
        s.save_doc("alpha", "alert_mutes", {"a": 1})
        s.save_doc("alpha", "update_check", {"a": 1})
        s.save_analytics("alpha", {"daily": {}})
        s.append_event("alpha", {"kind": "k"})
        found = {p.relative_to(self.root / "alpha").as_posix() for p in (self.root / "alpha").rglob("*") if p.is_file()}
        self.assertEqual(found, {"actions_monitor.json", "sentinel_state/sentinel_cache.json", "sentinel_state/collab_state.json", "events/events_state.json", "alert_mutes.json",
                                 "update_check.json", "analytics/analytics_history.json", "events/events_monitor.jsonl"})

    def test_the_flat_installation_keeps_the_names_next_to_the_launchers(self):
        s = file_storage.FileStorage(self.root, "flat")
        s.save_config("default", {"github_owner": "x"})
        s.save_sentinel_state("default", "sentinel_cache", {"a": 1})
        s.save_sentinel_state("default", "collab_state", {"a": 1})
        s.save_doc("default", "events_state", {"a": 1})
        s.save_doc("default", "alert_mutes", {"a": 1})
        s.save_analytics("default", {"daily": {}})
        s.append_event("default", {"kind": "k"})
        found = {p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(found, {"actions_monitor.json", "sentinel_cache.json", "collab_state.json", "events_state.json", "alert_mutes.json", "analytics_history.json", "events_monitor.jsonl"})
        self.assertEqual(s.list_accounts(), ["default"])
        self.assertEqual(s.verify(), [])

    def test_it_reads_the_feed_that_the_monitor_itself_wrote(self):
        s = file_storage.FileStorage(self.root, "accounts")
        folder = self.root / "alpha" / "events"
        folder.mkdir(parents=True)
        feed = events.Feed(folder / "events_monitor.jsonl", folder / "events_state.json")
        feed.emit([{"kind": "red_new", "code": "red_new", "text": "r", "repo": "x", "level": "bad", "url": None, "args": {}}])
        (event,) = s.load_events("alpha", None, 10)
        self.assertEqual((event["kind"], event["text"]), ("red_new", "r"))
        self.assertRegex(event["at"], r"^\d{4}-")

    def test_a_damaged_line_of_the_feed_is_skipped_and_reported_and_never_purged(self):
        s = file_storage.FileStorage(self.root, "accounts")
        s.save_config("alpha", {})
        s.append_event("alpha", {"at": OLD, "kind": "old"})
        with open(s.events_path("alpha"), "a", encoding="utf-8") as handle:
            handle.write('{"at": "2026-0\n[1, 2]\n')
        self.assertEqual([e["kind"] for e in s.load_events("alpha", None, 10)], ["old"])
        self.assertTrue(any("damaged" in p for p in s.verify()))
        s.purge_events("alpha", "2026-03-01T00:00:00Z")
        self.assertIn('{"at": "2026-0', s.events_path("alpha").read_text(encoding="utf-8"))

    def test_a_damaged_json_file_reads_as_empty(self):
        s = file_storage.FileStorage(self.root, "accounts")
        s.save_config("alpha", {"a": 1})
        (self.root / "alpha" / "actions_monitor.json").write_text("{broken", encoding="utf-8")
        (self.root / "alpha" / "alert_mutes.json").write_text("[1]", encoding="utf-8")
        self.assertEqual(s.load_config("alpha"), {})
        self.assertIsNone(s.load_doc("alpha", "alert_mutes"))
        self.assertTrue(any("actions_monitor.json" in p for p in s.verify()))

    def test_a_write_that_fails_leaves_the_old_content_and_no_temporary_file(self):
        s = file_storage.FileStorage(self.root, "accounts")
        s.save_config("alpha", {"v": 1})
        with mock.patch.object(file_storage.os, "replace", side_effect=OSError("disk")):
            with self.assertRaises(OSError):
                s.save_config("alpha", {"v": 2})
        self.assertEqual(s.load_config("alpha"), {"v": 1})
        self.assertEqual([p.name for p in (self.root / "alpha").iterdir()], ["actions_monitor.json"])

    def test_a_write_that_dies_before_the_replace_leaves_the_old_content(self):
        s = file_storage.FileStorage(self.root, "accounts")
        s.save_config("alpha", {"v": 1})
        with mock.patch.object(file_storage.os, "fsync", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                s.save_config("alpha", {"v": 2})
        self.assertEqual(s.load_config("alpha"), {"v": 1})
        self.assertEqual([p.name for p in (self.root / "alpha").iterdir()], ["actions_monitor.json"])

    def test_several_threads_appending_and_purging_lose_no_line(self):
        s = file_storage.FileStorage(self.root, "accounts")
        s.save_config("alpha", {})
        errors = []

        def writer(n):
            try:
                for i in range(40):
                    s.append_event("alpha", {"at": NEW, "kind": "w", "n": n, "i": i})
            except Exception as error:  # noqa: BLE001
                errors.append(error)

        def purger():
            try:
                for _ in range(20):
                    s.purge_events("alpha", "2026-03-01T00:00:00Z")
            except Exception as error:  # noqa: BLE001
                errors.append(error)

        threads = [threading.Thread(target=writer, args=(n,)) for n in range(4)] + [threading.Thread(target=purger)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        got = s.load_events("alpha", None, None)
        self.assertEqual(len(got), 160)
        self.assertEqual({(e["n"], e["i"]) for e in got}, {(n, i) for n in range(4) for i in range(40)})

    def test_the_global_records_have_their_own_folder_that_is_not_an_account(self):
        s = file_storage.FileStorage(self.root, "accounts")
        s.save_config("alpha", {})
        s.put_record("users", "ana", {"role": "admin"})
        self.assertTrue((self.root / "_global" / "users.json").is_file())
        self.assertEqual(s.list_accounts(), ["alpha"])
        self.assertFalse(list((self.root / "_global").glob("*.lock")))


class Factory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_without_an_accounts_folder_it_is_the_flat_installation(self):
        s = factory.create_storage(None, base_dir=self.root)
        self.assertEqual((s.backend, s.layout, s.root), ("file", "flat", self.root))

    def test_with_accounts_it_is_the_layout_of_accounts(self):
        (self.root / "accounts" / "alpha").mkdir(parents=True)
        (self.root / "accounts" / "alpha" / "actions_monitor.json").write_text("{}", encoding="utf-8")
        s = factory.create_storage({"backend": "file"}, "alpha", base_dir=self.root)
        self.assertEqual((s.layout, s.root), ("accounts", self.root / "accounts"))

    def test_a_path_sets_the_folder_of_the_accounts(self):
        s = factory.create_storage({"backend": "file", "path": str(self.root / "elsewhere")}, "alpha", base_dir=self.root)
        self.assertEqual((s.layout, s.root), ("accounts", self.root / "elsewhere"))

    def test_nonsense_reads_as_the_file_backend(self):
        for block in (None, "x", 5, {"backend": 3}, {"backend": "mongo"}, {"path": 7}):
            self.assertEqual(factory.settings(block)["backend"], "file")
            self.assertEqual(factory.create_storage(block, base_dir=self.root).backend, "file")

    def test_lite_is_always_the_file_backend_and_ignores_the_block(self):
        s = factory.create_storage({"backend": "sqlite", "path": str(self.root / "x.db")}, lite=True, base_dir=self.root)
        self.assertEqual((s.backend, s.layout), ("file", "flat"))
        self.assertFalse(any(self.root.glob("*.sqlite*")))


if __name__ == "__main__":
    unittest.main()
