# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""tools/migrate_storage.py and tools/backup_storage.py: a dry run writes nothing, the source is never touched, every account is copied whole or not at all, an interrupted run resumes,
the verification catches a difference, the backup of either backend restores into either."""
import contextlib
import hashlib
import io
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import backup_storage  # noqa: E402
import migrate_storage  # noqa: E402
from github_actions_monitor.storage import backup, installation, migrate  # noqa: E402
from github_actions_monitor.storage.file_storage import FileStorage  # noqa: E402

OLD, NEW = "2026-01-01T00:00:00Z", "2026-06-01T12:00:00Z"


def snapshot(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(folder).rglob("*")) if p.is_file()}


def fill(root, accounts=("alpha", "beta")):
    files = FileStorage(root, "accounts")
    for name in accounts:
        files.save_config(name, {"github_owner": name, "repos": ["a", "b"]})
        files.save_sentinel_state(name, "sentinel_cache", {"who": name, "n": [1, 2, 3]})
        files.save_sentinel_state(name, "collab_state", {"alerts": {}, "per_repo": {}, "last_full_scan": None})
        files.save_doc(name, "alert_mutes", {"active": [], "history": []})
        files.save_doc(name, "events_state", {"reds": {"x": 1}})
        files.save_analytics(name, {"seen": [1], "queue": {}, "steps": {}, "daily": {"2026-06-01": {"k": 1.5}}})
        files.append_events(name, [{"at": OLD, "kind": "a", "text": "日本語", "args": {"n": 1}}, {"at": NEW, "kind": "b"}, {"at": NEW, "kind": "c"}])
    files.put_record("users", "ana", {"role": "admin"})
    files.put_record("sessions", "s1", {"user": "ana"}, expires=99.0)
    return files


def run_cli(module, argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = module.main(argv)
    return code, out.getvalue()


class Migration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "accounts"
        self.files = fill(self.root)

    def test_a_dry_run_writes_nothing_and_says_what_it_would_copy(self):
        before = snapshot(self.root)
        code, text = run_cli(migrate_storage, ["--from", "file", "--to", "sqlite", "--accounts-dir", str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn("alpha", text)
        self.assertIn("3 events", text)
        self.assertIn("Dry run", text)
        self.assertEqual(snapshot(self.root), before)
        self.assertEqual(list(self.root.rglob("*.sqlite3*")), [])

    def test_apply_copies_every_account_verifies_it_and_leaves_the_files_alone(self):
        before = snapshot(self.root)
        code, text = run_cli(migrate_storage, ["--from", "file", "--to", "sqlite", "--accounts-dir", str(self.root), "--apply"])
        self.assertEqual(code, 0, text)
        self.assertIn("2 account(s) copied and verified", text)
        after = snapshot(self.root)
        self.assertEqual({k: v for k, v in after.items() if not k.endswith((".sqlite3", ".sqlite3-wal", ".sqlite3-shm"))}, before, "the source files are untouched")
        sql = installation.open_installation("sqlite", self.root)
        self.addCleanup(sql.close)
        self.assertEqual(sql.list_accounts(), ["alpha", "beta"])
        for name in ("alpha", "beta"):
            self.assertEqual(sql.export_account(name)["events"], self.files.export_account(name)["events"])
        self.assertEqual(sql.export_records(), self.files.export_records())
        self.assertEqual(sql.verify(), [])
        self.assertTrue((self.root / "alpha" / "storage.sqlite3").is_file())

    def test_running_it_again_skips_what_is_already_identical(self):
        argv = ["--from", "file", "--to", "sqlite", "--accounts-dir", str(self.root), "--apply"]
        self.assertEqual(run_cli(migrate_storage, argv)[0], 0)
        code, text = run_cli(migrate_storage, argv)
        self.assertEqual(code, 0)
        self.assertIn("0 account(s) copied", text)
        self.assertIn("2 already identical", text)

    def test_one_account_only(self):
        code, _text = run_cli(migrate_storage, ["--from", "file", "--to", "sqlite", "--accounts-dir", str(self.root), "--account", "beta", "--apply"])
        self.assertEqual(code, 0)
        self.assertFalse((self.root / "alpha" / "storage.sqlite3").exists())
        self.assertTrue((self.root / "beta" / "storage.sqlite3").is_file())

    def test_the_shared_database_of_model_b(self):
        db = Path(self.tmp.name) / "all.sqlite3"
        code, _ = run_cli(migrate_storage, ["--from", "file", "--to", "sqlite", "--accounts-dir", str(self.root), "--db", str(db), "--apply"])
        self.assertEqual(code, 0)
        shared = installation.open_installation("sqlite", self.root, db)
        self.addCleanup(shared.close)
        self.assertEqual(shared.list_accounts(), ["alpha", "beta"])
        self.assertEqual(shared.export_records()["users"], {"ana": {"data": {"role": "admin"}, "expires": None}})

    def test_and_back_to_files_for_a_fresh_folder(self):
        self.assertEqual(run_cli(migrate_storage, ["--from", "file", "--to", "sqlite", "--accounts-dir", str(self.root), "--apply"])[0], 0)
        other = Path(self.tmp.name) / "restored" / "accounts"
        other.mkdir(parents=True)
        for name in ("alpha", "beta"):
            (other / name).mkdir()
            (other / name / "storage.sqlite3").write_bytes((self.root / name / "storage.sqlite3").read_bytes())
        code, _ = run_cli(migrate_storage, ["--from", "sqlite", "--to", "file", "--accounts-dir", str(other), "--apply"])
        self.assertEqual(code, 0)
        back = FileStorage(other, "accounts")
        self.assertEqual(back.export_account("alpha"), self.files.export_account("alpha"))

    def test_the_flat_installation(self):
        flat = Path(self.tmp.name) / "flat"
        FileStorage(flat, "flat").save_config("default", {"github_owner": "me"})
        FileStorage(flat, "flat").append_event("default", {"at": NEW, "kind": "k"})
        code, _ = run_cli(migrate_storage, ["--from", "file", "--to", "sqlite", "--accounts-dir", str(flat), "--flat", "--apply"])
        self.assertEqual(code, 0)
        self.assertTrue((flat / "data" / "storage.sqlite3").is_file())

    def test_the_same_backend_on_both_sides_is_refused(self):
        self.assertEqual(run_cli(migrate_storage, ["--from", "file", "--to", "file", "--accounts-dir", str(self.root)])[0], 2)

    def test_an_empty_folder_has_nothing_to_migrate(self):
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        code, text = run_cli(migrate_storage, ["--from", "file", "--to", "sqlite", "--accounts-dir", str(empty), "--apply"])
        self.assertEqual(code, 0)
        self.assertIn("Nothing to migrate", text)

    def test_an_interrupted_run_leaves_each_account_whole_or_untouched_and_resumes(self):
        source = installation.open_installation("file", self.root)
        target = installation.open_installation("sqlite", self.root)
        self.addCleanup(target.close)
        real = target.import_account

        def failing(account_id, payload):
            if account_id == "beta":
                raise OSError("disk full")
            return real(account_id, payload)

        with mock.patch.object(target, "import_account", side_effect=failing):
            result = migrate.migrate(source, target, apply=True)
        self.assertFalse(result["verified"])
        self.assertTrue(any("beta" in p for p in result["problems"]))
        self.assertEqual(target.list_accounts(), ["alpha"])      # alpha is whole, beta never started
        self.assertEqual(migrate.verify(source, target, ["alpha"], records=False), [])
        again = migrate.migrate(source, target, apply=True)      # the same command resumes
        self.assertTrue(again["verified"], again["problems"])
        self.assertEqual((again["copied"], again["skipped"]), (1, 1))

    def test_a_process_killed_in_the_middle_of_an_account_leaves_no_half_account(self):
        code = textwrap.dedent("""
            import os, sys
            sys.path.insert(0, sys.argv[1])
            from github_actions_monitor.storage import installation, migrate, sqlite_storage
            source = installation.open_installation("file", sys.argv[2])
            target = installation.open_installation("sqlite", sys.argv[2])
            state = {"in_beta": False, "calls": 0}
            real_import, real_dumps = sqlite_storage.SqliteStorage.import_account, sqlite_storage._dumps
            def import_account(self, account_id, payload):
                state["in_beta"] = account_id == "beta"
                return real_import(self, account_id, payload)
            def dumps(value):
                if state["in_beta"]:
                    state["calls"] += 1
                    if state["calls"] > 8:      # after the configuration, the states and some events of the second account, inside its transaction
                        os._exit(9)
                return real_dumps(value)
            sqlite_storage.SqliteStorage.import_account = import_account
            sqlite_storage._dumps = dumps
            migrate.migrate(source, target, apply=True)
        """)
        done = subprocess.run([sys.executable, "-I", "-c", code, str(HERE / "src"), str(self.root)], capture_output=True, timeout=120)
        self.assertEqual(done.returncode, 9, done.stderr)
        target = installation.open_installation("sqlite", self.root)
        self.addCleanup(target.close)
        source = installation.open_installation("file", self.root)
        self.assertEqual(target.verify(), [])      # whatever is there is sound
        for account in target.list_accounts():
            self.assertEqual(migrate.verify(source, target, [account], records=False), [], account)      # every account that exists is complete
        result = migrate.migrate(source, target, apply=True)      # and the next run finishes the job
        self.assertTrue(result["verified"], result["problems"])
        self.assertEqual(target.list_accounts(), ["alpha", "beta"])

    def test_the_verification_catches_a_difference(self):
        source = installation.open_installation("file", self.root)
        target = installation.open_installation("sqlite", self.root)
        self.addCleanup(target.close)
        self.assertTrue(migrate.migrate(source, target, apply=True)["verified"])
        target.account_storage("alpha").append_event("alpha", {"at": NEW, "kind": "extra"})
        self.assertTrue(any("alpha" in p for p in migrate.verify(source, target)))
        target.account_storage("beta")._conn().execute("UPDATE configs SET data = 'oops'")
        self.assertTrue(any("beta" in p or "target" in p for p in migrate.verify(source, target)))


class BackupTool(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "accounts"
        self.files = fill(self.root)
        self.zip = str(Path(self.tmp.name) / "b.zip")

    def test_backup_verify_and_restore_files_into_a_fresh_folder(self):
        code, text = run_cli(backup_storage, ["backup", self.zip, "--backend", "file", "--accounts-dir", str(self.root)])
        self.assertEqual(code, 0, text)
        self.assertIn("2 account(s)", text)
        self.assertEqual(run_cli(backup_storage, ["verify", self.zip])[0], 0)
        fresh = Path(self.tmp.name) / "fresh"
        code, text = run_cli(backup_storage, ["restore", self.zip, "--backend", "file", "--accounts-dir", str(fresh)])
        self.assertEqual(code, 0, text)
        self.assertEqual(FileStorage(fresh, "accounts").export_account("beta"), self.files.export_account("beta"))
        code, text = run_cli(backup_storage, ["restore", self.zip, "--backend", "file", "--accounts-dir", str(fresh)])
        self.assertEqual(code, 1)      # not over data that is already there
        self.assertIn("Refused", text)
        self.assertEqual(run_cli(backup_storage, ["restore", self.zip, "--backend", "file", "--accounts-dir", str(fresh), "--force"])[0], 0)

    def test_a_backup_of_files_restores_into_sqlite_and_the_other_way_round(self):
        self.assertEqual(run_cli(backup_storage, ["backup", self.zip, "--backend", "file", "--accounts-dir", str(self.root)])[0], 0)
        sql_root = Path(self.tmp.name) / "sql"
        self.assertEqual(run_cli(backup_storage, ["restore", self.zip, "--backend", "sqlite", "--accounts-dir", str(sql_root)])[0], 0)
        second = str(Path(self.tmp.name) / "c.zip")
        self.assertEqual(run_cli(backup_storage, ["backup", second, "--backend", "sqlite", "--accounts-dir", str(sql_root)])[0], 0)
        back = Path(self.tmp.name) / "back"
        self.assertEqual(run_cli(backup_storage, ["restore", second, "--backend", "file", "--accounts-dir", str(back)])[0], 0)
        self.assertEqual(FileStorage(back, "accounts").export_account("alpha"), self.files.export_account("alpha"))
        kept = {kind: rows for kind, rows in self.files.export_records().items() if kind != "sessions"}
        restored = FileStorage(back, "accounts").export_records()
        self.assertEqual({kind: rows for kind, rows in restored.items() if kind != "sessions"}, kept)
        self.assertEqual(restored["sessions"], {}, "a backup carries no sessions")

    def test_a_damaged_backup_is_not_restored(self):
        self.assertEqual(run_cli(backup_storage, ["backup", self.zip, "--backend", "file", "--accounts-dir", str(self.root)])[0], 0)
        data = bytearray(Path(self.zip).read_bytes())
        data[len(data) // 2] ^= 0xFF
        Path(self.zip).write_bytes(bytes(data))
        self.assertEqual(run_cli(backup_storage, ["verify", self.zip])[0], 1)
        fresh = Path(self.tmp.name) / "fresh"
        self.assertEqual(run_cli(backup_storage, ["restore", self.zip, "--backend", "file", "--accounts-dir", str(fresh)])[0], 1)
        self.assertFalse(fresh.exists() and list(fresh.iterdir()))

    def test_restore_needs_to_know_the_backend(self):
        self.assertEqual(run_cli(backup_storage, ["backup", self.zip, "--backend", "file", "--accounts-dir", str(self.root)])[0], 0)
        self.assertEqual(run_cli(backup_storage, ["restore", self.zip])[0], 2)

    def test_the_backup_file_is_private(self):
        self.assertEqual(run_cli(backup_storage, ["backup", self.zip, "--backend", "file", "--accounts-dir", str(self.root)])[0], 0)
        if sys.platform != "win32":
            self.assertEqual(Path(self.zip).stat().st_mode & 0o077, 0)
        self.assertEqual(backup.verify_backup(self.zip), [])



class RepeatedMigration(unittest.TestCase):
    def test_repeating_the_command_never_replaces_newer_data_of_the_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "accounts"
            fill(root)
            argv = ["--from", "file", "--to", "sqlite", "--accounts-dir", str(root), "--apply"]
            self.assertEqual(run_cli(migrate_storage, argv)[0], 0)
            sql = installation.open_installation("sqlite", root)
            payload = sql.export_account("alpha")
            payload["events"].append({"at": "2026-09-01T00:00:00Z", "kind": "new_after_switch"})
            sql.import_account("alpha", payload)
            sql.close()
            code, text = run_cli(migrate_storage, argv)
            self.assertEqual(code, 1, text)
            self.assertIn("REFUSED", text)
            self.assertIn("alpha", text)
            sql, files = installation.open_installation("sqlite", root), installation.open_installation("file", root)
            try:
                self.assertIn("new_after_switch", [e.get("kind") for e in sql.export_account("alpha")["events"]])
                rows = migrate.plan(files, sql)
                self.assertEqual({r["account"]: r["status"] for r in rows}, {"alpha": "target_newer", "beta": "same"})
            finally:
                sql.close()
                files.close()
            code, text = run_cli(migrate_storage, argv + ["--force"])
            self.assertEqual(code, 0, text)
            sql = installation.open_installation("sqlite", root)
            try:
                self.assertNotIn("new_after_switch", [e.get("kind") for e in sql.export_account("alpha")["events"]])
            finally:
                sql.close()



class HandMadeBackup(unittest.TestCase):
    def test_a_backup_with_an_invalid_account_id_is_refused_before_anything_is_written(self):
        import json
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "accounts"
            fill(root)
            good = Path(tmp) / "good.zip"
            self.assertEqual(run_cli(backup_storage, ["backup", str(good), "--backend", "file", "--accounts-dir", str(root)])[0], 0)
            with zipfile.ZipFile(good) as bundle:
                manifest = json.loads(bundle.read(backup.MANIFEST))
                lines = bundle.read(backup.DUMP).decode("utf-8").splitlines()
            data = [json.loads(line) for line in lines]
            second = next(i for i, d in enumerate(data) if d.get("account") == "beta")
            data[second]["account"] = "../escaped"
            dump = "".join(json.dumps(d) + "\n" for d in data).encode("utf-8")
            import hashlib
            manifest.update(dump_bytes=len(dump), dump_sha256=hashlib.sha256(dump).hexdigest())
            bad = Path(tmp) / "bad.zip"
            with zipfile.ZipFile(bad, "w") as bundle:
                bundle.writestr(backup.DUMP, dump)
                bundle.writestr(backup.MANIFEST, json.dumps(manifest))
            self.assertTrue(backup.verify_backup(bad))
            fresh = Path(tmp) / "fresh"
            code, _text = run_cli(backup_storage, ["restore", str(bad), "--backend", "file", "--accounts-dir", str(fresh)])
            self.assertEqual(code, 1)
            self.assertFalse((fresh / "alpha").exists(), "the first account was not written either")


class DamagedLines(unittest.TestCase):
    def test_the_migration_says_how_many_damaged_lines_of_the_feed_it_does_not_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "accounts"
            files = fill(root, ("alpha",))
            path = files.events_path("alpha")
            path.write_text(path.read_text(encoding="utf-8") + "this is not json\n", encoding="utf-8")
            code, text = run_cli(migrate_storage, ["--from", "file", "--to", "sqlite", "--accounts-dir", str(root)])
            self.assertEqual(code, 0)
            self.assertIn("1 damaged line", text)


if __name__ == "__main__":
    unittest.main()
