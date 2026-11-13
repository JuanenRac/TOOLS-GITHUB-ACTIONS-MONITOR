# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Retention and rotation: the settings are clamped, the purge removes only old events and old analytics days (never the configuration, the state of the sentinels or the documents), the
archive mode writes a .gz first, every pass leaves an audit line, the tick of maintenance runs it when due, the doctor warns about size and about a service without retention, and the
feed that is appended while the purge rewrites it loses no line."""
import gzip
import json
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am, settings_api  # noqa: E402
from github_actions_monitor.cli import doctor  # noqa: E402
from github_actions_monitor.data_pipeline import events  # noqa: E402
from github_actions_monitor.storage import file_storage, retention, runtime, sqlite_storage, state_io  # noqa: E402

NOW = time.mktime(time.strptime("2026-06-01 12:00:00", "%Y-%m-%d %H:%M:%S")) - time.timezone      # 2026-06-01T12:00:00Z whatever the zone of the machine
DAY = 86400


def stamp(days_ago):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - days_ago * DAY))


def day(days_ago):
    return time.strftime("%Y-%m-%d", time.gmtime(NOW - days_ago * DAY))


class Settings(unittest.TestCase):
    def test_the_defaults_are_the_conservative_ones(self):
        self.assertEqual(retention.settings({}), {"enabled": True, "events_days": 90, "analytics_days": 180, "mode": "delete", "events_max_kb": 512, "interval_hours": 24, "warn_events_mb": 20})
        self.assertFalse(retention.configured({}))
        self.assertTrue(retention.configured({"retention": {"events_days": 30}}))

    def test_a_bad_value_reads_as_the_default_and_a_bool_is_not_a_number(self):
        cfg = retention.settings({"retention": {"enabled": "yes", "events_days": True, "analytics_days": 0, "mode": "burn", "events_max_kb": "512", "interval_hours": 100000, "warn_events_mb": -1}})
        self.assertEqual(cfg, retention.settings({}))
        self.assertEqual(retention.settings({"retention": {"events_days": 30, "mode": "archive", "enabled": False}})["events_days"], 30)
        self.assertEqual(retention.settings({"retention": 5}), retention.settings({}))

    def test_the_cutoffs(self):
        cfg = retention.settings({"retention": {"events_days": 10, "analytics_days": 20}})
        self.assertEqual(retention.cutoffs(cfg, NOW), (stamp(10), day(20)))

    def test_service_mode(self):
        env = {}
        self.assertFalse(retention.service_mode({}, env) and not Path("/.dockerenv").exists())
        self.assertTrue(retention.service_mode({"listen": {"network": True}}, env))
        self.assertTrue(retention.service_mode({"open_browser": False}, env))
        self.assertTrue(retention.service_mode({}, {"MONITOR_SERVICE": "1"}))
        self.assertFalse(retention.service_mode({"listen": {"network": False}}, {"MONITOR_SERVICE": "0"}) and not Path("/.dockerenv").exists())


class Backends:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.storage = self.make()
        self.addCleanup(self.storage.close)
        s = self.storage
        s.save_config("alpha", {"github_owner": "me"})
        s.save_sentinel_state("alpha", "sentinel_cache", {"keep": 1})
        s.save_sentinel_state("alpha", "sentinel_history", {"days": {day(400): {"x": 1}}})      # old, but it is state of a sentinel: not ours to purge
        s.save_doc("alpha", "alert_mutes", {"active": [{"x": 1}], "history": []})
        s.save_doc("alpha", "events_state", {"reds": {}})
        s.save_analytics("alpha", {"seen": [1], "daily": {day(300): {"a": 1}, day(200): {"a": 2}, day(100): {"a": 3}, day(1): {"a": 4}}})
        s.append_events("alpha", [{"at": stamp(200), "kind": "ancient"}, {"at": stamp(100), "kind": "old"}, {"at": stamp(10), "kind": "recent"}, {"at": stamp(0), "kind": "now"}])

    def kinds(self):
        return [e["kind"] for e in self.storage.load_events("alpha", None, None)]

    def test_a_pass_removes_only_old_events_and_old_analytics_days(self):
        line = retention.run(self.storage, "alpha", retention.settings({}), NOW)
        self.assertEqual((line["events_removed"], line["events_kept"], line["analytics_removed"], line["error"], line["mode"]), (2, 2, 2, "", "delete"))
        self.assertEqual(self.kinds(), ["recent", "now"])
        self.assertEqual(set(self.storage.load_analytics("alpha")["daily"]), {day(100), day(1)})
        self.assertEqual(self.storage.load_config("alpha"), {"github_owner": "me"})
        self.assertEqual(self.storage.load_sentinel_state("alpha", "sentinel_cache"), {"keep": 1})
        self.assertEqual(list(self.storage.load_sentinel_state("alpha", "sentinel_history")["days"]), [day(400)])
        self.assertEqual(self.storage.load_doc("alpha", "alert_mutes"), {"active": [{"x": 1}], "history": []})
        self.assertEqual(self.storage.load_doc("alpha", "events_state"), {"reds": {}})

    def test_the_limits_come_from_the_settings(self):
        retention.run(self.storage, "alpha", retention.settings({"retention": {"events_days": 5}}), NOW)
        self.assertEqual(self.kinds(), ["now"])
        retention.run(self.storage, "alpha", retention.settings({"retention": {"events_days": 5, "analytics_days": 50}}), NOW)
        self.assertEqual(set(self.storage.load_analytics("alpha")["daily"]), {day(1)})

    def test_archive_mode_writes_the_old_events_first(self):
        line = retention.run(self.storage, "alpha", retention.settings({"retention": {"mode": "archive"}}), NOW)
        self.assertEqual((line["events_removed"], line["mode"], line["error"]), (2, "archive", ""))
        archives = list(Path(self.storage.archive_dir("alpha")).glob("events-*.jsonl.gz"))
        self.assertEqual([a.name for a in archives], [line["archived"]])
        rows = [json.loads(x) for x in gzip.open(archives[0], "rt", encoding="utf-8").read().splitlines()]
        self.assertEqual([r["kind"] for r in rows], ["ancient", "old"])
        self.assertEqual(self.kinds(), ["recent", "now"])

    def test_a_pass_that_finds_nothing_old_removes_nothing_and_archives_nothing(self):
        retention.run(self.storage, "alpha", retention.settings({"retention": {"mode": "archive"}}), NOW)
        line = retention.run(self.storage, "alpha", retention.settings({"retention": {"mode": "archive"}}), NOW + 60)
        self.assertEqual((line["events_removed"], line["archived"], line["analytics_removed"]), (0, "", 0))
        self.assertEqual(len(list(Path(self.storage.archive_dir("alpha")).glob("*.gz"))), 1)

    def test_every_pass_leaves_an_audit_line_and_only_the_last_fifty_are_kept(self):
        for i in range(55):
            retention.run(self.storage, "alpha", retention.settings({}), NOW + i)
        doc = retention.audit(self.storage, "alpha")
        self.assertEqual(len(doc["runs"]), retention.AUDIT_KEEP)
        self.assertEqual(doc["last_run_epoch"], NOW + 54)
        self.assertEqual(set(doc["runs"][0]), {"at", "mode", "events_removed", "events_kept", "archived", "analytics_removed", "error"})

    def test_a_failing_purge_is_recorded_not_raised_and_removes_nothing(self):
        with mock.patch.object(self.storage, "purge_events", side_effect=OSError("disk full")):
            line = retention.run(self.storage, "alpha", retention.settings({}), NOW)
        self.assertIn("OSError", line["error"])
        self.assertEqual(self.kinds(), ["ancient", "old", "recent", "now"])
        self.assertIn("OSError", retention.audit(self.storage, "alpha")["runs"][-1]["error"])

    def test_the_tick_runs_when_due_only(self):
        config = {"retention": {"interval_hours": 2}}
        self.assertIsNotNone(retention.tick(self.storage, "alpha", config, NOW))
        self.assertIsNone(retention.tick(self.storage, "alpha", config, NOW + 3600))
        self.assertIsNotNone(retention.tick(self.storage, "alpha", config, NOW + 2 * 3600 + 1))

    def test_switched_off_it_never_runs(self):
        self.assertIsNone(retention.tick(self.storage, "alpha", {"retention": {"enabled": False}}, NOW))
        self.assertEqual(len(self.kinds()), 4)

    def test_the_report_for_the_doctor_and_the_page(self):
        retention.run(self.storage, "alpha", retention.settings({}), NOW)
        info = retention.report(self.storage, "alpha", {})
        self.assertEqual((info["events"]["count"], info["last"]["events_removed"], info["configured"]), (2, 2, False))


class FileRetention(Backends, unittest.TestCase):
    def make(self):
        return file_storage.FileStorage(Path(self.tmp.name) / "accounts", "accounts")


class SqliteRetention(Backends, unittest.TestCase):
    def make(self):
        return sqlite_storage.SqliteStorage(Path(self.tmp.name) / "accounts" / "alpha" / "storage.sqlite3")


class TheFeedWhileItIsPurged(unittest.TestCase):
    def test_lines_appended_by_the_monitor_while_the_purge_rewrites_the_file_are_not_lost(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = file_storage.FileStorage(Path(tmp), "accounts")
            storage.save_config("alpha", {})
            storage.events_path("alpha").parent.mkdir(parents=True)      # the monitor creates the folder of the account before it starts
            feed = events.Feed(storage.events_path("alpha"), storage.events_path("alpha").with_name("events_state.json"))
            errors, stop = [], threading.Event()

            def feeding():
                try:
                    for i in range(120):
                        feed.emit([{"kind": "fresh", "n": i, "text": "t"}])
                        storage.append_events("alpha", [{"at": stamp(500), "kind": "stale", "n": i}])      # old lines keep arriving, so every purge has something to rewrite
                except Exception as error:  # noqa: BLE001
                    errors.append(error)
                finally:
                    stop.set()

            def purging():
                try:
                    while not stop.is_set():
                        retention.run(storage, "alpha", retention.settings({}), time.time())
                except Exception as error:  # noqa: BLE001
                    errors.append(error)

            threads = [threading.Thread(target=feeding), threading.Thread(target=purging)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(errors, [])
            fresh = sorted(e["n"] for e in storage.load_events("alpha", None, None) if e["kind"] == "fresh")
            self.assertEqual(fresh, list(range(120)))


class Tick(unittest.TestCase):
    def test_the_maintenance_tick_purges_through_the_storage_of_the_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = file_storage.FileStorage(Path(tmp), "accounts")
            storage.save_config("alpha", {})
            storage.append_events("alpha", [{"at": "2020-01-01T00:00:00Z", "kind": "ancient"}, {"kind": "now"}])
            with mock.patch.object(runtime, "process_storage", return_value=(storage, "alpha")), mock.patch.dict(am.LITE, {"on": False}):
                am.retention_tick({})
            self.assertEqual([e["kind"] for e in storage.load_events("alpha", None, None)], ["now"])
            self.assertEqual(retention.audit(storage, "alpha")["runs"][-1]["events_removed"], 1)

    def test_the_lite_edition_has_no_such_job(self):
        with mock.patch.object(runtime, "process_storage", side_effect=AssertionError("must not be asked")), mock.patch.dict(am.LITE, {"on": True}):
            am.retention_tick({})

    def test_a_failure_of_the_job_never_stops_the_cycle(self):
        with mock.patch.object(runtime, "process_storage", side_effect=RuntimeError("boom")), mock.patch.dict(am.LITE, {"on": False}):
            am.retention_tick({})

    def test_the_file_storage_of_a_process_follows_its_layout(self):
        state_io.unbind()
        with tempfile.TemporaryDirectory() as tmp:
            storage, account = runtime.process_storage(None, Path(tmp))
            self.assertEqual((storage.backend, storage.layout, account), ("file", "flat", "default"))

    def test_the_ceiling_of_the_feed_file_comes_from_the_settings_and_lite_keeps_its_own(self):
        keep = events.MAX_BYTES
        self.addCleanup(setattr, events, "MAX_BYTES", keep)
        runtime.bind({"retention": {"events_max_kb": 100}})
        self.assertEqual(events.MAX_BYTES, 100 * 1024)
        runtime.bind({}, lite=True)
        self.assertEqual(events.MAX_BYTES, 100 * 1024)      # lite does not touch it
        runtime.bind({})
        self.assertEqual(events.MAX_BYTES, 512 * 1024)


class TheDoctor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def test_files_are_ok(self):
        self.assertEqual(doctor.storage_check({}, self.folder), ("ok", "file"))

    def test_a_database_that_does_not_exist_yet_is_a_warning_and_is_not_created(self):
        status, detail = doctor.storage_check({"storage": {"backend": "sqlite"}}, self.folder)
        self.assertEqual(status, "warn")
        self.assertIn("no database yet", detail)
        self.assertEqual(list(self.folder.glob("*.sqlite3*")), [])

    def test_a_sound_database_is_ok_and_a_damaged_or_newer_one_is_not(self):
        s = sqlite_storage.SqliteStorage(self.folder / "storage.sqlite3")
        s.save_config("default", {"a": 1})
        s.close()
        self.assertEqual(doctor.storage_check({"storage": {"backend": "sqlite"}}, self.folder), ("ok", "sqlite"))
        con = sqlite3.connect(str(self.folder / "storage.sqlite3"))
        con.execute("UPDATE meta SET value = '99' WHERE key = 'schema_version'")
        con.commit()
        con.close()
        status, detail = doctor.storage_check({"storage": {"backend": "sqlite"}}, self.folder)
        self.assertEqual(status, "warn")
        self.assertIn("newer", detail)
        (self.folder / "storage.sqlite3").write_bytes(b"this is not a database at all" * 50)
        self.assertEqual(doctor.storage_check({"storage": {"backend": "sqlite"}}, self.folder)[0], "warn")

    def test_each_account_is_looked_at(self):
        from github_actions_monitor.accounts import accounts
        with mock.patch.dict("os.environ", {"MONITOR_ACCOUNTS_DIR": str(self.folder / "accounts")}):
            accounts.create_account("alpha", "a")
            path = accounts.config_path("alpha")
            cfg = json.loads(path.read_text(encoding="utf-8"))
            cfg["storage"] = {"backend": "sqlite"}
            path.write_text(json.dumps(cfg), encoding="utf-8")
            status, detail = doctor.storage_check({}, self.folder)
        self.assertEqual(status, "warn")
        self.assertIn("alpha: no database yet", detail)

    def test_a_small_feed_on_a_desktop_is_ok(self):
        (self.folder / "events_monitor.jsonl").write_text("x\n" * 100, encoding="utf-8")
        status, _detail = doctor.retention_check({}, self.folder, {})
        self.assertEqual(status, "ok")

    def test_a_big_feed_warns(self):
        (self.folder / "events_monitor.jsonl").write_bytes(b"x" * (3 * 1024 * 1024))
        status, detail = doctor.retention_check({"retention": {"warn_events_mb": 1}}, self.folder, {})
        self.assertEqual(status, "warn")
        self.assertIn("3 MB > 1 MB", detail)

    def test_a_service_without_a_retention_block_warns_and_one_with_it_does_not(self):
        if Path("/.dockerenv").exists():
            self.skipTest("inside a container every monitor is a service")
        env = {"MONITOR_SERVICE": "1"}
        status, detail = doctor.retention_check({}, self.folder, env)
        self.assertEqual(status, "warn")
        self.assertIn("not configured", detail)
        self.assertEqual(doctor.retention_check({"retention": {"events_days": 60}}, self.folder, env)[0], "ok")
        self.assertEqual(doctor.retention_check({"retention": {"enabled": False}}, self.folder, env)[0], "warn")

    def test_the_checks_are_in_the_list_and_have_their_texts_in_the_eight_languages(self):
        from github_actions_monitor import i18n
        self.assertIn("storage", doctor.ORDER)
        self.assertIn("retention", doctor.ORDER)
        for lang in i18n.LANGS:
            for key in ("doctor.t.storage", "doctor.f.storage", "doctor.t.retention", "doctor.f.retention"):
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))


class TheSettingsPage(unittest.TestCase):
    def test_the_retention_settings_are_in_the_schema_with_their_limits(self):
        for key in ("retention.enabled", "retention.events_days", "retention.analytics_days", "retention.mode", "retention.events_max_kb", "retention.interval_hours", "retention.warn_events_mb"):
            self.assertIn(key, settings_api.FIELDS)
        clean, errors = settings_api.validate({"retention.events_days": 30, "retention.mode": "archive", "retention.enabled": False})
        self.assertEqual((clean, errors), ({"retention.events_days": 30, "retention.mode": "archive", "retention.enabled": False}, {}))
        _clean, errors = settings_api.validate({"retention.events_days": 0, "retention.mode": "burn", "retention.analytics_days": "x"})
        self.assertEqual(set(errors), {"retention.events_days", "retention.mode", "retention.analytics_days"})

    def test_the_lite_page_has_none_of_them_and_cannot_change_them(self):
        self.assertFalse([k for k in settings_api.LITE_KEYS if k.startswith(("retention.", "storage."))])
        _clean, errors = settings_api.validate({"retention.events_days": 30}, lite=True)
        self.assertIn("retention.events_days", errors)


if __name__ == "__main__":
    unittest.main()
