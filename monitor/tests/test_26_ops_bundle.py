# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The backup package of the operation (format 2): what travels and what never does, the checksums of every member, the compatibility with the plain backup, the restore (refused while a monitor runs
or into a storage that holds accounts, one account alone, into a folder), the sealing with a key from the environment (refused, never faked, without the library) and the scheduled copy."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.cli import monitor_cli  # noqa: E402
from github_actions_monitor.ops import bundle, opsconf, restore, schedule, sealing  # noqa: E402
from github_actions_monitor.storage import backup, installation  # noqa: E402
from github_actions_monitor.storage.file_storage import FileStorage  # noqa: E402

# values that look like secrets are built when the test runs, so no file of the repository holds one
LOGIN = "gh" + "p_" + "A" * 36
HOOK = "webhook-" + "B" * 20
PROVIDER = "provider-" + "C" * 20
KEY_NAME = "GHAMON_TEST_KEY"
KEY_VALUE = "k" * 8 + "-pass-" + "x" * 6
OLD, NEW = "2026-01-01T00:00:00Z", "2026-06-01T12:00:00Z"


def account_config(name):
    return {"github_owner": name, "retention": {"events_days": 30}, "webhook": {"secret": HOOK}, "github_token": {"enabled": True, "store": "file", "value": LOGIN},
            "ai": {"api_key": PROVIDER, "api_key_env": "SOME_VARIABLE"}, "an_unknown_setting": "kept only in the original"}


def fill(root, names=("alpha", "beta")):
    files = FileStorage(root, "accounts")
    for name in names:
        files.save_config(name, account_config(name))
        files.save_doc(name, "alert_mutes", {"active": [], "history": []})
        files.append_events(name, [{"at": OLD, "kind": "a"}, {"at": NEW, "kind": "b"}])
    files.put_record("users", "ana", {"role": "admin"})
    files.put_record("sessions", "s1", {"user": "ana", "csrf": LOGIN}, expires=99.0)
    return files


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "data" / "accounts"
        fill(self.root)
        (self.base / "config").mkdir(parents=True)
        (self.base / "config" / "targets.json").write_text(json.dumps({"repos": ["x/y"], "token": LOGIN}), encoding="utf-8")
        self.config = {"github_owner": "alpha", "ops": {"backup": {"keep": 2}}, "webhook": {"secret": HOOK}, "a_key_nobody_lists": 1}
        self.inst = installation.open_installation("file", self.root)
        self.addCleanup(self.inst.close)

    def members_text(self, path):
        with zipfile.ZipFile(path) as package:
            return {name: package.read(name).decode("utf-8") for name in package.namelist()}

    def make(self, name="one.zip", **options):
        return bundle.create(self.inst, self.base / name, config=self.config, folder=self.base, **options)


class Package(Case):
    def test_the_package_lists_every_member_with_its_checksum_and_verifies(self):
        made = self.make()
        manifest = made["manifest"]
        self.assertEqual(manifest["format"], 2)
        self.assertEqual(sorted(manifest["members"]), ["dump.jsonl", "files.json"])
        self.assertEqual({"product_version", "schema_version", "edition", "config_included"} <= set(manifest), True)
        self.assertEqual(bundle.verify(made["path"]), [])
        self.assertEqual(oct(Path(made["path"]).stat().st_mode & 0o777)[-3:] if os.name != "nt" else "600", "600")

    def test_no_member_holds_a_token_a_key_a_secret_or_a_session(self):
        made = self.make()
        for name, text in self.members_text(made["path"]).items():
            for secret in (LOGIN, HOOK, PROVIDER, "csrf"):
                self.assertNotIn(secret, text, f"{secret[:6]} found in {name}")
        files = json.loads(self.members_text(made["path"])["files.json"])
        self.assertEqual(files["config"]["github_owner"], "alpha")
        self.assertNotIn("a_key_nobody_lists", files["config"], "only the white list of the settings travels")
        self.assertEqual(files["lists"]["targets.json"], {"repos": ["x/y"]}, "a key that looks like a secret is dropped from the lists too")

    def test_the_optional_stores_travel_when_present_and_are_skipped_when_not(self):
        without = json.loads(self.members_text(self.make("none.zip")["path"])["files.json"])
        self.assertNotIn("proposals.json", without["files"], "a store that is not there is left out without an error")
        (self.base / "data").mkdir(exist_ok=True); (self.base / "data" / "proposals.json").write_text(json.dumps({"items": [{"id": 1, "token": LOGIN}]}), encoding="utf-8")
        made = self.make("some.zip")
        for name, text in self.members_text(made["path"]).items():
            self.assertNotIn(LOGIN, text, f"a secret found in {name}")
        files = json.loads(self.members_text(made["path"])["files.json"])
        self.assertEqual(files["files"]["proposals.json"], {"items": [{"id": 1}]})

    def test_the_name_of_a_variable_travels_but_not_its_value(self):
        with mock.patch.dict(os.environ, {"SOME_VARIABLE": "value-that-must-not-travel"}):
            made = self.make()
        text = "".join(self.members_text(made["path"]).values())
        self.assertNotIn("value-that-must-not-travel", text)

    def test_the_settings_can_be_left_out_altogether(self):
        made = self.make(include_config=False)
        files = json.loads(self.members_text(made["path"])["files.json"])
        self.assertEqual(files, {"schema": 1, "included": False})
        dump = self.members_text(made["path"])["dump.jsonl"]
        self.assertNotIn("github_owner", dump)

    def test_a_byte_changed_in_the_dump_is_found(self):
        made = self.make()
        path = Path(made["path"])
        members = self.members_text(path)
        members["dump.jsonl"] = members["dump.jsonl"].replace('"kind": "a"', '"kind": "z"')
        with zipfile.ZipFile(path, "w") as package:
            for name, text in members.items():
                package.writestr(name, text)
        problems = bundle.verify(path)
        self.assertTrue(any("checksum" in p for p in problems), problems)

    def test_a_member_taken_out_or_added_is_found(self):
        made = self.make()
        members = self.members_text(made["path"])
        short = self.base / "short.zip"
        with zipfile.ZipFile(short, "w") as package:
            for name, text in members.items():
                if name != "files.json":
                    package.writestr(name, text)
        self.assertTrue(any("members missing" in p for p in bundle.verify(short)), bundle.verify(short))
        extra = self.base / "extra.zip"
        with zipfile.ZipFile(extra, "w") as package:
            for name, text in members.items():
                package.writestr(name, text)
            package.writestr("evil.json", "{}")
        self.assertTrue(any("does not list" in p for p in bundle.verify(extra)), bundle.verify(extra))

    def test_a_changed_files_member_is_found(self):
        made = self.make()
        members = self.members_text(made["path"])
        members["files.json"] = members["files.json"].replace("alpha", "omega")
        changed = self.base / "changed.zip"
        with zipfile.ZipFile(changed, "w") as package:
            for name, text in members.items():
                package.writestr(name, text)
        self.assertTrue(any("checksum of a member" in p for p in bundle.verify(changed)), bundle.verify(changed))

    def test_a_plain_backup_of_the_first_format_still_verifies_and_restores(self):
        old = self.base / "old.zip"
        backup.make_backup(self.inst, old)
        self.assertEqual(bundle.verify(old), [])
        fresh = installation.open_installation("file", self.base / "fresh" / "accounts")
        self.addCleanup(fresh.close)
        done = restore.restore(old, self.config, folder=self.base, inst=fresh, alive=lambda: False)
        self.assertEqual((done["accounts"], done["events"]), (2, 4))
        self.assertEqual(done["files"], {"written": [], "skipped": []})

    def test_deep_verify_restores_into_a_temporary_folder(self):
        made = self.make()
        self.assertEqual(restore.deep_verify(made["path"]), [])


class BackendsAndWriters(Case):
    def test_a_package_made_from_files_restores_into_sqlite_and_back(self):
        made = self.make("files.zip")
        lite = installation.open_installation("sqlite", self.base / "sql" / "accounts")
        self.addCleanup(lite.close)
        done = restore.restore(made["path"], self.config, folder=self.base / "sql", inst=lite, alive=lambda: False)
        self.assertEqual((done["accounts"], done["events"], done["verify"]), (2, 4, []))
        again = bundle.create(lite, self.base / "sql.zip", config=self.config, folder=self.base / "sql")
        back = installation.open_installation("file", self.base / "back" / "accounts")
        self.addCleanup(back.close)
        restore.restore(again["path"], self.config, folder=self.base / "back", inst=back, alive=lambda: False)
        for name in ("alpha", "beta"):
            self.assertEqual([e["kind"] for e in back.account_storage(name).load_events(name, limit=None)], ["a", "b"])
            self.assertEqual(back.account_storage(name).load_config(name)["github_owner"], name)

    def test_a_copy_made_while_another_thread_writes_still_verifies_and_is_consistent(self):
        import threading
        lite = installation.open_installation("sqlite", self.base / "hot" / "accounts")
        self.addCleanup(lite.close)
        lite.import_account("alpha", {"config": {"github_owner": "alpha"}, "events": [{"at": OLD, "kind": "seed"}]})
        stop = threading.Event()
        writer_store = installation.open_installation("sqlite", self.base / "hot" / "accounts")
        self.addCleanup(writer_store.close)

        def write():
            counter = 0
            while not stop.is_set() and counter < 400:
                writer_store.account_storage("alpha").append_events("alpha", [{"at": NEW, "kind": "w", "n": counter}])
                counter += 1
        thread = threading.Thread(target=write, daemon=True)
        thread.start()
        try:
            made = bundle.create(lite, self.base / "hot.zip", config={}, folder=self.base / "hot", include_config=False)
        finally:
            stop.set()
            thread.join(10)
        self.assertEqual(bundle.verify(made["path"]), [])
        self.assertGreaterEqual(made["manifest"]["events"], 1)


class OneAccount(Case):
    def test_the_package_holds_that_account_alone_and_no_user(self):
        made = self.make("one-account.zip", account="alpha")
        manifest = made["manifest"]
        self.assertEqual((manifest["scope"], manifest["account"], manifest["accounts"]), ("account", "alpha", 1))
        self.assertEqual(bundle.verify(made["path"]), [])
        dump = self.members_text(made["path"])["dump.jsonl"].splitlines()
        parsed = [json.loads(line) for line in dump]
        self.assertEqual([p["account"] for p in parsed if "account" in p], ["alpha"])
        self.assertEqual([p["records"] for p in parsed if "records" in p], [{}], "no user, no session")
        self.assertEqual(json.loads(self.members_text(made["path"])["files.json"]), {"schema": 1, "included": False, "scope": "account"})
        text = "".join(self.members_text(made["path"]).values())
        for secret in (LOGIN, HOOK, PROVIDER):
            self.assertNotIn(secret, text)

    def test_an_account_that_does_not_exist_is_refused_before_anything_is_written(self):
        for name in ("gamma", "../x"):
            with self.assertRaises(bundle.OpsError) as caught:
                self.make("none.zip", account=name)
            self.assertEqual(caught.exception.code, "no_account")
        self.assertFalse((self.base / "none.zip").exists())

    def test_restoring_it_touches_only_that_account_and_needs_force_only_when_it_exists(self):
        made = self.make("one-account.zip", account="alpha")
        target = installation.open_installation("file", self.base / "t" / "accounts")
        self.addCleanup(target.close)
        target.import_account("beta", {"config": {"github_owner": "mine"}})
        target.put_record("users", "ana", {"role": "admin"}) if hasattr(target, "put_record") else target.global_storage().put_record("users", "ana", {"role": "admin"})

        def go(**options):
            return restore.restore(made["path"], self.config, folder=self.base / "t", inst=target, alive=lambda: False, **options)
        done = go()
        self.assertEqual((done["ids"], done["files"]), (["alpha"], {"written": [], "skipped": []}))
        self.assertEqual(target.account_storage("beta").load_config("beta"), {"github_owner": "mine"})
        self.assertEqual(list(target.export_records()["users"]), ["ana"], "the users of the destination are not touched")
        with self.assertRaises(bundle.OpsError) as caught:
            go()
        self.assertEqual(caught.exception.code, "exists")
        self.assertEqual(go(force=True)["ids"], ["alpha"])
        with self.assertRaises(bundle.OpsError) as caught:
            go(account="beta", force=True)
        self.assertEqual(caught.exception.code, "no_account")

    def test_a_whole_package_that_claims_to_be_of_one_account_does_not_verify(self):
        made = self.make("whole.zip")
        members = self.members_text(made["path"])
        manifest = json.loads(members["manifest.json"])
        manifest.update(scope="account", account="alpha")
        members["manifest.json"] = json.dumps(manifest)
        fake = self.base / "fake.zip"
        with zipfile.ZipFile(fake, "w") as package:
            for name, text in members.items():
                package.writestr(name, text)
        self.assertTrue(any("one account" in p for p in bundle.verify(fake)), bundle.verify(fake))

    def test_the_command_line_makes_it(self):
        patches = [mock.patch("github_actions_monitor.app.toolconfig.raw_config", return_value=self.config),
                   mock.patch.object(bundle, "open_installation", side_effect=lambda *a, **k: installation.open_installation("file", self.root)),
                   mock.patch.object(opsconf.paths, "folder", side_effect=lambda kind, base=None: self.base / kind)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(i18n.set_language, "en")
        out = io.StringIO()
        target = self.base / "cli-one.zip"
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = monitor_cli.main(["backup", "create", str(target), "--account", "alpha", "--lang", "en", "--json"])
        self.assertEqual(code, 0, out.getvalue())
        self.assertEqual(backup.read_manifest(target)["scope"], "account")


class Restoring(Case):
    def setUp(self):
        super().setUp()
        self.made = self.make()["path"]
        self.target_base = self.base / "target"
        self.target = installation.open_installation("file", self.target_base / "accounts")
        self.addCleanup(self.target.close)

    def go(self, **options):
        options.setdefault("alive", lambda: False)
        return restore.restore(self.made, self.config, folder=self.target_base, inst=self.target, **options)

    def test_it_restores_the_accounts_and_the_files_and_leaves_a_checklist(self):
        done = self.go()
        self.assertEqual((done["accounts"], done["ids"]), (2, ["alpha", "beta"]))
        self.assertIn("targets.json", done["files"]["written"])
        self.assertIn("credentials", done["todo"])
        self.assertEqual(done["verify"], [])
        self.assertTrue((self.target_base / "data" / "ops" / "restore_report.json").is_file())
        config = self.target.account_storage("alpha").load_config("alpha")
        self.assertEqual(config["github_owner"], "alpha")
        self.assertNotIn("value", config.get("github_token", {}), "the login did not come back")

    def test_it_refuses_a_storage_that_already_holds_accounts_unless_forced(self):
        self.go()
        with self.assertRaises(bundle.OpsError) as caught:
            self.go()
        self.assertEqual(caught.exception.code, "exists")
        self.assertEqual(self.go(force=True)["accounts"], 2)

    def test_forcing_merges_the_settings_and_never_removes_a_key_of_the_destination(self):
        self.target.import_account("alpha", {"config": {"a_key_of_the_destination": 7, "retention": {"events_days": 5, "mode": "delete"}}})
        done = self.go(force=True)
        self.assertEqual(done["accounts"], 2)
        config = self.target.account_storage("alpha").load_config("alpha")
        self.assertEqual(config["a_key_of_the_destination"], 7)
        self.assertEqual(config["retention"], {"events_days": 30, "mode": "delete"})

    def test_one_account_alone_leaves_the_others_and_the_global_files_alone(self):
        self.target.import_account("beta", {"config": {"github_owner": "mine"}})
        done = self.go(account="alpha")
        self.assertEqual(done["ids"], ["alpha"])
        self.assertEqual(self.target.account_storage("beta").load_config("beta"), {"github_owner": "mine"})
        self.assertEqual(done["files"], {"written": [], "skipped": []})
        with self.assertRaises(bundle.OpsError) as caught:
            self.go(account="alpha")
        self.assertEqual(caught.exception.code, "exists")
        with self.assertRaises(bundle.OpsError) as caught:
            self.go(account="gamma", force=True)
        self.assertEqual(caught.exception.code, "no_account")

    def test_a_running_monitor_stops_the_restore(self):
        with self.assertRaises(bundle.OpsError) as caught:
            self.go(alive=lambda: True)
        self.assertEqual(caught.exception.code, "service_running")
        self.assertEqual(self.target.list_accounts(), [])

    def test_into_a_folder_it_needs_an_empty_one_and_does_not_care_about_the_monitor(self):
        to_dir = self.base / "elsewhere"
        done = restore.restore(self.made, self.config, folder=self.target_base, to_dir=to_dir, alive=lambda: True)
        self.assertEqual(done["accounts"], 2)
        self.assertTrue((to_dir / "accounts" / "alpha").is_dir())
        with self.assertRaises(bundle.OpsError) as caught:
            restore.restore(self.made, self.config, folder=self.target_base, to_dir=to_dir)
        self.assertEqual(caught.exception.code, "dir_not_empty")

    def test_a_package_that_does_not_verify_is_refused_before_anything_is_written(self):
        bad = self.base / "bad.zip"
        bad.write_bytes(b"not a zip")
        with self.assertRaises(bundle.OpsError) as caught:
            restore.restore(bad, self.config, folder=self.target_base, inst=self.target, alive=lambda: False)
        self.assertEqual(caught.exception.code, "verify")
        self.assertEqual(self.target.list_accounts(), [])
        with self.assertRaises(bundle.OpsError) as caught:
            restore.restore(self.base / "nothing.zip", self.config, folder=self.target_base, inst=self.target)
        self.assertEqual(caught.exception.code, "not_found")


class Sealing(Case):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {KEY_NAME: KEY_VALUE})
        env.start()
        self.addCleanup(env.stop)
        fast = mock.patch.object(sealing, "ITERATIONS", 2000)
        fast.start()
        self.addCleanup(fast.stop)

    def test_without_the_library_sealing_is_refused_and_nothing_is_written(self):
        with mock.patch.object(sealing, "_aead", return_value=None):
            with self.assertRaises(bundle.OpsError) as caught:
                self.make("sealed.zip", encrypt=True, key_env=KEY_NAME)
        self.assertEqual(caught.exception.code, "library_missing")
        self.assertEqual(sorted(p.name for p in self.base.glob("sealed*")), [], "no copy in the clear, no half copy")

    @unittest.skipUnless(sealing.available(), "the optional library cryptography is not installed")
    def test_with_the_library_the_copy_is_sealed_verified_and_restored_with_the_key(self):
        made = self.make("sealed.zip", encrypt=True, key_env=KEY_NAME)
        self.assertTrue(made["sealed"] and made["path"].endswith(".enc"))
        raw = Path(made["path"]).read_bytes()
        self.assertTrue(raw.startswith(sealing.MAGIC))
        self.assertNotIn(b"alpha", raw, "the content is not readable")
        self.assertEqual(bundle.verify(made["path"], KEY_NAME), [])
        target = installation.open_installation("file", self.base / "t" / "accounts")
        self.addCleanup(target.close)
        done = restore.restore(made["path"], self.config, folder=self.base / "t", inst=target, key_env=KEY_NAME, alive=lambda: False)
        self.assertEqual(done["accounts"], 2)

    @unittest.skipUnless(sealing.available(), "the optional library cryptography is not installed")
    def test_a_wrong_key_a_missing_key_a_weak_key_and_a_cut_file_are_told_apart(self):
        made = self.make("sealed.zip", encrypt=True, key_env=KEY_NAME)
        with mock.patch.dict(os.environ, {KEY_NAME: "another-key-123"}):
            with self.assertRaises(bundle.OpsError) as caught:
                bundle.verify(made["path"], KEY_NAME)
        self.assertEqual(caught.exception.code, "bad_key")
        with mock.patch.dict(os.environ, {KEY_NAME: ""}):
            with self.assertRaises(bundle.OpsError) as caught:
                bundle.verify(made["path"], KEY_NAME)
        self.assertEqual(caught.exception.code, "key_missing")
        with mock.patch.dict(os.environ, {KEY_NAME: "short"}):
            with self.assertRaises(bundle.OpsError) as caught:
                self.make("weak.zip", encrypt=True, key_env=KEY_NAME)
        self.assertEqual(caught.exception.code, "key_weak")
        cut = Path(made["path"]).read_bytes()
        Path(made["path"]).write_bytes(cut[:len(cut) // 2])
        with self.assertRaises(bundle.OpsError) as caught:
            bundle.verify(made["path"], KEY_NAME)
        self.assertEqual(caught.exception.code, "damaged")

    def test_the_variable_must_exist_and_may_not_be_one_the_monitor_or_github_reads(self):
        with self.assertRaises(bundle.OpsError) as caught:
            self.make("x.zip", encrypt=True, key_env="")
        self.assertIn(caught.exception.code, ("key_missing", "library_missing"))
        self.assertEqual(opsconf.settings({"ops": {"backup": {"key_env": "GH_TOKEN"}}})["backup"]["key_env"], "")
        self.assertEqual(opsconf.settings({"ops": {"backup": {"key_env": "GHAMON_BACKUP_KEY"}}})["backup"]["key_env"], "GHAMON_BACKUP_KEY")


class Settings(unittest.TestCase):
    def test_conservative_defaults_and_clamped_values(self):
        cfg = opsconf.settings({})
        self.assertFalse(cfg["backup"]["enabled"])
        self.assertFalse(cfg["backup"]["encrypt"])
        self.assertFalse(cfg["purge"]["enabled"])
        self.assertEqual(cfg["doctor"]["sqlite_check"], "quick")
        wild = opsconf.settings({"ops": {"backup": {"keep": 0, "interval_hours": True, "dir": "../outside", "compress_level": 99}, "doctor": {"sqlite_check": "never", "min_free_mb": "lots"}}})
        self.assertEqual((wild["backup"]["keep"], wild["backup"]["interval_hours"], wild["backup"]["dir"], wild["backup"]["compress_level"]), (7, 24, "backups", 6))
        self.assertEqual((wild["doctor"]["sqlite_check"], wild["doctor"]["min_free_mb"]), ("quick", 500))
        for bad in ("\\\\server\\share", "D:\\copies", "a\\..\\b"):
            self.assertEqual(opsconf.settings({"ops": {"backup": {"dir": bad}}})["backup"]["dir"], "backups", bad)

    def test_every_setting_of_the_block_is_in_the_page_and_none_can_hold_a_secret(self):
        from github_actions_monitor.app import settings_api
        keys = [k for k in settings_api.FIELDS if k.startswith("ops.")]
        self.assertEqual(len(keys), 17)      # 16 of the operations and ops.verify_release.fetch of the release check
        self.assertEqual(settings_api.check_value("ops.backup.dir", "../x"), (False, "path"))
        self.assertEqual(settings_api.check_value("ops.backup.key_env", "GH_TOKEN"), (False, "text"))
        self.assertEqual(settings_api.check_value("ops.backup.key_env", "MY_BACKUP_KEY"), (True, "MY_BACKUP_KEY"))
        self.assertEqual(settings_api.check_value("ops.backup.keep", 0), (False, "range"))


class Schedule(Case):
    def setUp(self):
        super().setUp()
        self.config = {"ops": {"backup": {"enabled": True, "interval_hours": 1, "keep": 2, "dir": str(self.base / "copies")}}}

    def tick(self, now, **options):
        return schedule.tick(self.config, self.base, now=now, **options)

    def test_it_is_off_by_default_and_does_nothing_when_off(self):
        self.assertIsNone(schedule.tick({}, self.base, now=1000.0))
        self.assertEqual(list((self.base / "data").glob("ops")), [])

    def test_it_copies_on_the_interval_and_keeps_only_the_newest(self):
        with mock.patch.object(bundle, "open_installation", return_value=self.inst), mock.patch.object(self.inst, "close"):
            first = self.tick(1_800_000_000.0)
            self.assertTrue(first["ok"])
            self.assertIsNone(self.tick(1_800_000_000.0 + 600), "not due yet")
            for index in range(1, 4):
                self.assertTrue(self.tick(1_800_000_000.0 + 4000 * index)["ok"])
        names = [row["name"] for row in schedule.list_backups(self.config, self.base)]
        self.assertEqual(len(names), 2, names)
        self.assertEqual(names, sorted(names, reverse=True))
        (self.base / "copies" / "notes.txt").write_text("mine", encoding="utf-8")
        schedule.rotate(self.config, self.base)
        self.assertTrue((self.base / "copies" / "notes.txt").is_file(), "only files with the name of a copy are ever removed")

    def test_a_failure_is_written_down_and_never_raised(self):
        with mock.patch.object(bundle, "open_installation", return_value=self.inst), mock.patch.object(self.inst, "close"):
            with mock.patch.object(bundle.backup, "write_package", side_effect=OSError(28, "No space left on device")):
                state = self.tick(1_800_000_000.0)
        self.assertFalse(state["ok"])
        self.assertEqual((state["error"], state["failures"]), ("failed", 1))
        self.assertEqual(schedule.read_status(self.base)["error"], "failed")
        self.assertIsNone(self.tick(1_800_000_000.0 + 60), "the next try waits for the interval")

    def test_a_sealed_schedule_without_the_library_says_so_and_writes_nothing(self):
        self.config["ops"]["backup"].update(encrypt=True, key_env=KEY_NAME)
        with mock.patch.object(sealing, "_aead", return_value=None), mock.patch.dict(os.environ, {KEY_NAME: KEY_VALUE}):
            with mock.patch.object(bundle, "open_installation", return_value=self.inst), mock.patch.object(self.inst, "close"):
                state = self.tick(1_800_000_000.0)
        self.assertEqual((state["ok"], state["error"]), (False, "library_missing"))
        self.assertEqual(schedule.list_backups(self.config, self.base), [])


class CommandLine(Case):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = monitor_cli.main(list(argv) + ["--lang", "en"])
        return code, out.getvalue(), err.getvalue()

    def setUp(self):
        super().setUp()
        self.addCleanup(i18n.set_language, "en")      # the command pins the language of the process: put it back for the tests that follow
        patches = [mock.patch("github_actions_monitor.app.toolconfig.raw_config", return_value=self.config),
                   mock.patch.object(bundle, "open_installation", side_effect=lambda *a, **k: installation.open_installation("file", self.root)),
                   mock.patch.object(opsconf.paths, "folder", side_effect=lambda kind, base=None: self.base / kind)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_create_verify_status_and_list(self):
        target = self.base / "cli.zip"
        code, out, _ = self.run_cli("backup", "create", str(target), "--json")
        self.assertEqual(code, 0, out)
        self.assertTrue(json.loads(out)["data"]["ok"])
        code, out, _ = self.run_cli("backup", "verify", str(target), "--deep")
        self.assertEqual((code, out.strip()), (0, i18n.t("ops.deep_ok")))
        code, out, _ = self.run_cli("backup", "status", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["data"]["file"], "cli.zip")
        code, out, _ = self.run_cli("backup", "list")
        self.assertEqual(code, 0)
        self.assertIn("backups", out)

    def test_a_package_that_does_not_verify_exits_one_and_a_missing_file_is_a_wrong_use(self):
        bad = self.base / "bad.zip"
        bad.write_bytes(b"nope")
        self.assertEqual(self.run_cli("backup", "verify", str(bad))[0], 1)
        self.assertEqual(self.run_cli("backup", "verify")[0], 1)
        self.assertEqual(self.run_cli("backup", "bogus")[0], 1)

    def test_restore_into_a_folder_from_the_command_line_prints_the_checklist(self):
        target = self.base / "cli.zip"
        self.assertEqual(self.run_cli("backup", "create", str(target))[0], 0)
        code, out, _ = self.run_cli("backup", "restore", str(target), "--to-dir", str(self.base / "out"))
        self.assertEqual(code, 0, out)
        self.assertIn(i18n.t("ops.todo.credentials"), out)


class LiteStaysAlone(unittest.TestCase):
    def test_the_lite_edition_and_its_doctor_never_load_the_operation(self):
        code = ("import sys; sys.path.insert(0, %r); import github_actions_monitor.lite, github_actions_monitor.cli.doctor as d; "
                "d.run(runner=lambda *a, **k: (1, '', ''), config={}, ports=(), edition='lite'); "
                "bad = [m for m in sys.modules if m.startswith('github_actions_monitor.ops')]; print('LOADED', bad); sys.exit(1 if bad else 0)") % str(HERE / "src")
        flags = {"creationflags": 0x08000000} if os.name == "nt" else {}
        done = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=120, **flags)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
