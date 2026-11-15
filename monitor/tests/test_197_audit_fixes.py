# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Four hardening fixes of the folder migration, the backup, the log of a step and the first administrator of a container.

1. The migration of the product folder writes what it is about to move BEFORE it moves it (paths relative to the folder), so a run that is cut half way can still be undone, and --undo deletes the journal
   only when everything it lists is back (a folder renamed after the migration still undoes).
2. A symbolic link next to the launchers is never moved (it would break): it stays and is reported.
3. The backup does not carry the sessions and restoring one does not bring back a revoked session.
4. The id of a run for the log of a step is plain ASCII digits (a superscript two is refused, not an error).
5. A container started in the team mode without an administrator says the exact command that creates the first one, and the deployment guide, the example file and the container test say it too."""
import json
import os
import shutil
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
from github_actions_monitor.integrations import steplog  # noqa: E402
from github_actions_monitor.security import auth  # noqa: E402
from github_actions_monitor.storage import backup, factory  # noqa: E402
from github_actions_monitor.util import rootmigrate  # noqa: E402

PW = "a long enough passphrase 1"


def old_install(tmp):
    root = Path(tmp) / "monitor"
    root.mkdir()
    for name, text in (("actions_monitor.json", '{"github_owner": "o"}'), ("alert_mutes.json", '{"active": []}'), ("events_monitor.jsonl", "e\n"),
                       ("ai_alerts.jsonl", "a\n"), ("actions_monitor_log.txt", "log\n"), ("targets.json", "{}")):
        (root / name).write_text(text, encoding="utf-8")
    return root


def files(root):
    return sorted(p.relative_to(root).as_posix() for p in Path(root).rglob("*") if (p.is_file() or p.is_symlink()) and "config_backups" not in p.parts)


class TheJournal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_control_apply_then_undo_puts_everything_back_and_the_journal_goes(self):
        root = old_install(self.tmp.name)
        before = files(root)
        rootmigrate.apply(root)
        self.assertEqual(len(rootmigrate.undo(root)), 6)
        self.assertEqual(files(root), before)

    def test_a_run_cut_half_way_can_still_be_undone(self):
        root = old_install(self.tmp.name)
        before = files(root)
        real, calls = shutil.move, []

        def flaky(source, destination):
            calls.append(source)
            if len(calls) == 4:
                raise KeyboardInterrupt("cut at the fourth move")
            return real(source, destination)
        with mock.patch.object(rootmigrate.shutil, "move", flaky):
            with self.assertRaises(KeyboardInterrupt):
                rootmigrate.apply(root)
        journal = root / "data" / ".layout_moves.json"
        self.assertTrue(journal.is_file(), "the journal was written before the moves")
        lines = json.loads(journal.read_text(encoding="utf-8"))["runs"][0]["moves"]
        self.assertEqual(len(lines), 4, "three done and the one that was cut: the intention is on disk before the move")
        self.assertEqual(len(rootmigrate.undo(root)), 3)
        self.assertEqual(files(root), before)

    def test_the_journal_holds_paths_relative_to_the_folder_and_a_renamed_folder_still_undoes(self):
        root = old_install(self.tmp.name)
        rootmigrate.apply(root)
        for run in json.loads((root / "data" / ".layout_moves.json").read_text(encoding="utf-8"))["runs"]:
            for old, new in run["moves"]:
                self.assertFalse(Path(old).is_absolute() or Path(new).is_absolute(), (old, new))
        renamed = root.with_name("monitor_renamed")
        root.rename(renamed)
        self.assertEqual(len(rootmigrate.undo(renamed)), 6)
        self.assertFalse((renamed / "data" / ".layout_moves.json").exists())

    def test_the_journal_stays_with_what_could_not_be_put_back(self):
        root = old_install(self.tmp.name)
        rootmigrate.apply(root)
        (root / "targets.json").write_text("{}", encoding="utf-8")      # the old place of one file is taken again
        back = rootmigrate.undo(root)
        self.assertEqual(len(back), 5)
        journal = root / "data" / ".layout_moves.json"
        self.assertTrue(journal.is_file())
        left = [m for run in json.loads(journal.read_text(encoding="utf-8"))["runs"] for m in run["moves"]]
        self.assertEqual(len(left), 1)
        self.assertTrue(left[0][0].endswith("targets.json"))
        (root / "targets.json").unlink()
        self.assertEqual(len(rootmigrate.undo(root)), 1)
        self.assertFalse(journal.exists(), "everything is back: now it goes")


@unittest.skipUnless(hasattr(os, "symlink"), "no symbolic links")
class TheLinks(unittest.TestCase):
    def test_a_symbolic_link_is_not_moved_and_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "monitor"
            root.mkdir()
            shared = Path(tmp) / "dotfiles"
            shared.mkdir()
            (shared / "monitor.json").write_text('{"github_owner": "o"}', encoding="utf-8")
            try:
                os.symlink(os.path.join("..", "dotfiles", "monitor.json"), root / "actions_monitor.json")
            except OSError:
                self.skipTest("this account cannot make symbolic links")
            (root / "ai_alerts.jsonl").write_text("a\n", encoding="utf-8")
            self.assertEqual([p.name for p in rootmigrate.links(root)], ["actions_monitor.json"])
            self.assertEqual([s.name for s, _d in rootmigrate.plan(root)], ["ai_alerts.jsonl"])
            out = rootmigrate.apply(root)
            self.assertTrue((root / "actions_monitor.json").is_symlink(), "the link stays where it is")
            self.assertEqual(json.loads((root / "actions_monitor.json").read_text(encoding="utf-8"))["github_owner"], "o", "and still reads")
            self.assertFalse((root / "config" / "actions_monitor.json").exists())
            self.assertEqual([p.name for p in out["links"]], ["actions_monitor.json"])
            self.assertEqual(len(out["moved"]), 1)


class TheBackup(unittest.TestCase):
    def test_a_backup_has_no_sessions_and_restoring_does_not_bring_back_a_revoked_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = factory.create_storage({"backend": "file", "path": tmp + "/data"})
            self.addCleanup(store.close)
            cfg = auth.settings({"auth": {"enabled": True}})
            auth.bootstrap_admin(store, "root", PW)
            session, _code = auth.login(store, "root", PW, cfg)
            backup.make_backup(store, tmp + "/copy.zip")
            dump = zipfile.ZipFile(tmp + "/copy.zip").read("dump.jsonl").decode()
            self.assertNotIn(session["csrf"], dump)
            self.assertNotIn('"sessions": {"', dump)
            self.assertIn('"users": {"root"', dump, "the users are still in the backup")
            auth.revoke_sessions(store, "root")
            backup.restore_backup(tmp + "/copy.zip", store, force=True)
            self.assertIsNone(auth.find_session(store, session["token"]))

    def test_a_dump_that_carries_sessions_restores_everything_but_them(self):
        records = {"users": {"root": {"data": {"x": 1}, "expires": None}}, "sessions": {"abc": {"data": {"user": "root"}, "expires": None}}}
        self.assertEqual(list(backup._without_sessions(records)), ["users"])
        self.assertEqual(backup._without_sessions(None), {})


class TheStepLog(unittest.TestCase):
    def test_a_run_id_must_be_plain_digits(self):
        config = {"logs": {"failed_step": {"enabled": True}}}
        for bad in ("²", "٣٤", "12 ", "-1", "1e3", "", "1" * 15, "0"):
            self.assertEqual(steplog.read(config, "o", "repo", bad, ["repo"]), {"ok": False, "error": "request"}, repr(bad))


class TheFirstAdministrator(unittest.TestCase):
    def test_the_message_of_the_service_says_the_exact_command_and_the_guides_say_it_too(self):
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            text = catalogue["mon.network_needs_admin_service"]
            self.assertIn("docker compose run --rm --entrypoint python monitor -m github_actions_monitor.security.auth_cli create-admin", text, lang)
            self.assertIn("MONITOR_ADMIN_PASSWORD_FILE", text, lang)
            for key in ("service.admin_created", "service.admin_refused", "service.admin_unreadable"):
                self.assertTrue(catalogue.get(key), (lang, key))
        for tail in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por"):
            guide = (HERE / "docs" / f"DEPLOYMENT{tail}.md").read_text(encoding="utf-8")
            self.assertIn("docker compose run --rm --entrypoint python monitor -m github_actions_monitor.security.auth_cli create-admin", guide, tail)
            self.assertIn("MONITOR_ADMIN_PASSWORD_FILE", guide, tail)

    def test_the_example_file_and_the_container_test_have_the_steps(self):
        deploy = HERE.parent / "deploy"
        if not deploy.is_dir():
            self.skipTest("the deploy folder does not travel in the zip of a release")
        example = (deploy / ".env.example").read_text(encoding="utf-8")
        self.assertIn("auth_cli create-admin", example)
        self.assertIn("MONITOR_ADMIN_PASSWORD_FILE", example)
        script = (deploy / "test" / "container_test.sh").read_text(encoding="utf-8")
        self.assertIn("MONITOR_TEAM_MODE=1", script)
        self.assertIn("auth_cli create-admin", script)


class TheServiceCreatesTheFirstAdministrator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.config = {"auth": {"enabled": True}, "storage": {"backend": "file", "path": str(self.dir / "data")}}

    def run_prepare(self, env, config=None):
        from github_actions_monitor import service
        said = []
        with mock.patch.object(auth, "get_storage", lambda _c: self.storage):
            return service.prepare_admin(self.config if config is None else config, env, said.append), said

    def test_with_the_user_and_the_password_file_the_first_administrator_is_made_once_and_nothing_is_printed(self):
        self.storage = factory.create_storage({"backend": "file", "path": str(self.dir / "data")})
        self.addCleanup(self.storage.close)
        pw = self.dir / "pw"
        pw.write_text(PW + "\n", encoding="utf-8")
        env = {"MONITOR_ADMIN_USER": "ops", "MONITOR_ADMIN_PASSWORD_FILE": str(pw)}
        made, said = self.run_prepare(env)
        self.assertEqual(made, "ops")
        self.assertNotIn(PW, " ".join(said))
        self.assertTrue(auth.users_exist(self.storage))
        again, _said = self.run_prepare(env)
        self.assertEqual(again, "", "a second start does not touch the users")

    def test_nothing_happens_without_both_variables_without_the_team_mode_or_with_a_bad_file(self):
        self.storage = factory.create_storage({"backend": "file", "path": str(self.dir / "data")})
        self.addCleanup(self.storage.close)
        pw = self.dir / "pw"
        pw.write_text(PW, encoding="utf-8")
        self.assertEqual(self.run_prepare({"MONITOR_ADMIN_USER": "ops"})[0], "")
        self.assertEqual(self.run_prepare({"MONITOR_ADMIN_PASSWORD_FILE": str(pw)})[0], "")
        self.assertEqual(self.run_prepare({"MONITOR_ADMIN_USER": "ops", "MONITOR_ADMIN_PASSWORD_FILE": str(pw)}, {"auth": {"enabled": False}})[0], "")
        made, said = self.run_prepare({"MONITOR_ADMIN_USER": "ops", "MONITOR_ADMIN_PASSWORD_FILE": str(self.dir / "missing")})
        self.assertEqual(made, "")
        self.assertEqual(len(said), 1)
        pw.write_text("short", encoding="utf-8")
        made, said = self.run_prepare({"MONITOR_ADMIN_USER": "ops", "MONITOR_ADMIN_PASSWORD_FILE": str(pw)})
        self.assertEqual(made, "")
        self.assertFalse(auth.users_exist(self.storage))


if __name__ == "__main__":
    unittest.main()

