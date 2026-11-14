# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The order of the product folder: next to the launchers there is nothing but the folders; the data, configuration, logs and AI files live in data/, config/, logs/ and ai/. Covers the table of places,
the folders that can be moved, the migration of an installation of 1.7.x and of 1.8.0 (moves, never deletes, can be undone), the map for the AIs (ai/INDEX.json, /api/paths) and the places the gate script finds."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.cli import doctor  # noqa: E402
from github_actions_monitor.data_pipeline import ci_red  # noqa: E402
from github_actions_monitor.integrations import ai_hook, ai_index  # noqa: E402
from github_actions_monitor.util import paths, rootmigrate  # noqa: E402

LAUNCHERS = ("MONITOR_GITHUB_ACTIONS.bat", "MONITOR_GITHUB_ACTIONS.sh", "MONITOR_GITHUB_ACTIONS.command", "BATCH_GITHUB_ACTIONS.bat", "MONITOR_LITE_GITHUB_ACTIONS.sh", "LICENSE", "NOTICE", "AUTHORS", "README.txt")
FOLDERS_OF_THE_PRODUCT = ("src", "assets", "docs", "bin", "tools", "tests", "deploy")
#: what an installation of 1.7.x / 1.8.0 keeps next to the launchers: file -> (folder it must end in)
OLD_FILES = {
    "actions_monitor.json": "config", "actions_monitor_lite.json": "config", "targets.json": "config", "ecosystems.json": "config", "profiles.json": "config", "quotas.json": "config",
    "etag_cache.json": "data", "etag_cache_lite.json": "data", "events_monitor.jsonl": "data", "events_state.json": "data", "eventos_monitor.jsonl": "data", "analytics_history.json": "data",
    "sentinel_cache.json": "data", "sentinel_history.json": "data", "sentinel_ai_cache.json": "data", "collab_state.json": "data", "alert_mutes.json": "data", "update_check.json": "data",
    "update_check_lite.json": "data", "welcome_state.json": "data", "orgs_state.json": "data", "degraded.json": "data", "degraded_lite.json": "data", "storage.sqlite3": "data",
    "actions_monitor_log.txt": "logs", "actions_monitor_log_lite.txt": "logs", "ai_actions_log.jsonl": "logs", "github_actions_log.jsonl": "logs", "auth_audit.jsonl": "logs",
    "ALERTS_BRIEF.md": "ai", "ai_alerts.jsonl": "ai", "ai_alerts_state.json": "ai", "ai_heartbeat.json": "ai", "ai_hook_state.json": "ai", "ci_red.json": "ai",
}


def make_old_install(root, flavour="1.8.0"):
    """A product folder as 1.7.x (code flat is not needed here) or 1.8.0 left it: launchers, the data next to them, the accounts folder, the backups of the configuration."""
    root = Path(root)
    for name in LAUNCHERS:
        (root / name).write_text("launcher " + name, encoding="utf-8")
    for folder in FOLDERS_OF_THE_PRODUCT:
        (root / folder).mkdir(exist_ok=True)
    for name in OLD_FILES:
        if flavour == "1.7.x" and name in ("ai_alerts_state.json", "ai_heartbeat.json", "ai_hook_state.json", "storage.sqlite3", "auth_audit.jsonl", "degraded.json", "degraded_lite.json"):
            continue                       # these did not exist yet
        (root / name).write_text("content of " + name, encoding="utf-8")
    (root / "accounts" / "personal" / "events").mkdir(parents=True)
    (root / "accounts" / "personal" / "actions_monitor.json").write_text('{"github_owner": "me"}', encoding="utf-8")
    (root / "accounts" / "personal" / "events" / "events_monitor.jsonl").write_text("line\n", encoding="utf-8")
    (root / "config_backups").mkdir()
    (root / "config_backups" / "actions_monitor-20260101-000000.json").write_text("{}", encoding="utf-8")
    return root


def listing(root):
    return sorted(p.relative_to(root).as_posix() for p in Path(root).rglob("*") if p.is_file())


class TheTableOfPlaces(unittest.TestCase):
    def test_every_known_file_has_one_folder(self):
        for name, folder in OLD_FILES.items():
            self.assertEqual(paths.kind_of(name), folder, name)
        self.assertEqual(paths.kind_of("accounts"), "data")
        self.assertEqual(paths.kind_of("config_backups"), "config")
        self.assertIsNone(paths.kind_of("README.txt"))
        self.assertIsNone(paths.kind_of("MONITOR_GITHUB_ACTIONS.sh"))

    def test_the_lite_and_demo_variants_follow_the_file_they_vary(self):
        self.assertEqual(paths.kind_of("etag_cache_demo.json"), "data")
        self.assertEqual(paths.kind_of("actions_monitor_log_lite.txt"), "logs")
        self.assertEqual(paths.kind_of("config_backups_lite"), "config")

    def test_place_gives_the_path_inside_the_folder_of_its_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(paths.place("etag_cache.json", tmp), Path(tmp) / "data" / "etag_cache.json")
            self.assertEqual(paths.place("ALERTS_BRIEF.md", tmp), Path(tmp) / "ai" / "ALERTS_BRIEF.md")
            self.assertEqual(paths.place("actions_monitor.json", tmp), Path(tmp) / "config" / "actions_monitor.json")
            self.assertEqual(paths.place("a-file-of-nobody.bin", tmp), Path(tmp) / "data" / "a-file-of-nobody.bin")

    def test_a_folder_can_be_moved_by_the_environment_or_by_the_file_of_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with mock.patch.dict(os.environ, {"MONITOR_DATA_DIR": str(tmp / "vol-data")}, clear=False):
                self.assertEqual(paths.folder("data"), tmp / "vol-data")
                self.assertEqual(paths.folder("logs"), tmp / "vol-data" / "logs", "with the data volume alone, logs and ai follow it")
                self.assertEqual(paths.folder("ai"), tmp / "vol-data" / "ai")
                self.assertEqual(paths.folder("config"), paths.ROOT / "config", "the configuration has its own variable")
            with mock.patch.dict(os.environ, {"MONITOR_DATA_DIR": str(tmp / "vol-data"), "MONITOR_LOGS_DIR": str(tmp / "elsewhere")}):
                self.assertEqual(paths.folder("logs"), tmp / "elsewhere")
            (tmp / "p.json").write_text(json.dumps({"ai": str(tmp / "for-the-ais"), "data": "relative-data", "nonsense": "x", "logs": 5}), encoding="utf-8")
            with mock.patch.dict(os.environ, {"MONITOR_PATHS_FILE": str(tmp / "p.json")}):
                self.assertEqual(paths.folder("ai"), tmp / "for-the-ais")
                self.assertEqual(paths.folder("data"), paths.ROOT / "relative-data", "a relative path starts at the product folder")
                self.assertEqual(paths.folder("logs"), paths.ROOT / "logs", "a value that is not text is ignored")

    def test_a_damaged_file_of_paths_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "p.json").write_text("{not json", encoding="utf-8")
            with mock.patch.dict(os.environ, {"MONITOR_PATHS_FILE": str(Path(tmp) / "p.json")}):
                self.assertEqual(paths.folder("data"), paths.ROOT / "data")

    def test_ensure_makes_the_four_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            made = paths.ensure(tmp)
            self.assertEqual({p.name for p in made}, {"config", "data", "logs", "ai"})
            self.assertTrue(all(p.is_dir() for p in made))

    def test_the_repository_itself_has_no_data_file_next_to_the_launchers(self):
        self.assertEqual([p.name for p in paths.ROOT.iterdir() if p.is_file() and paths.kind_of(p.name)], [])


class TheWritersMakeTheFoldersOfTheMonitor(unittest.TestCase):
    def test_a_file_of_the_monitor_can_be_written_before_its_folder_exists_and_any_other_cannot(self):
        from github_actions_monitor.security import private_io
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with mock.patch.dict(os.environ, {"MONITOR_DATA_DIR": str(tmp / "vol")}):
                private_io.write_private(paths.place("etag_cache.json"), "{}")
                self.assertTrue((tmp / "vol" / "etag_cache.json").is_file())
                with private_io.open_append(paths.place("ai_actions_log.jsonl")) as log:
                    log.write("x\n")
                self.assertTrue((tmp / "vol" / "logs" / "ai_actions_log.jsonl").is_file())
                self.assertTrue(paths.is_own(tmp / "vol" / "data" / "x"))
                self.assertFalse(paths.is_own(tmp / "elsewhere" / "x"))
            with self.assertRaises(OSError):
                private_io.write_private(tmp / "elsewhere" / "x.json", "{}")


class Migration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def check_clean_root(self):
        files = sorted(p.name for p in self.root.iterdir() if p.is_file())
        self.assertEqual(files, sorted(LAUNCHERS), "next to the launchers: the launchers, the legal files and the README, nothing else")
        folders = {p.name for p in self.root.iterdir() if p.is_dir()}
        self.assertEqual(folders - set(FOLDERS_OF_THE_PRODUCT), {"config", "data", "logs", "ai"})

    def test_an_installation_of_1_8_0_ends_with_a_clean_root(self):
        make_old_install(self.root, "1.8.0")
        before = {name: (self.root / name).read_bytes() for name in OLD_FILES}
        result = rootmigrate.apply(self.root, stamp="t1")
        self.assertEqual(result["conflicts"], [])
        self.check_clean_root()
        for name, folder in OLD_FILES.items():
            self.assertEqual((self.root / folder / name).read_bytes(), before[name], name + " moved with its content")
            self.assertFalse((self.root / name).exists(), name)
        self.assertTrue((self.root / "data" / "accounts" / "personal" / "events" / "events_monitor.jsonl").is_file())
        self.assertTrue((self.root / "config" / "config_backups" / "actions_monitor-20260101-000000.json").is_file())

    def test_an_installation_of_1_7_x_ends_the_same_way(self):
        make_old_install(self.root, "1.7.x")
        rootmigrate.apply(self.root, stamp="t1")
        self.check_clean_root()
        self.assertTrue((self.root / "ai" / "ALERTS_BRIEF.md").is_file())
        self.assertTrue((self.root / "logs" / "actions_monitor_log.txt").is_file())

    def test_the_configuration_is_copied_before_anything_moves(self):
        make_old_install(self.root)
        result = rootmigrate.apply(self.root, stamp="t1")
        backup = result["backup"]
        self.assertEqual(backup, self.root / "config" / "config_backups" / "pre_layout_t1")
        for name in ("actions_monitor.json", "targets.json", "quotas.json"):
            self.assertEqual((backup / name).read_text(encoding="utf-8"), "content of " + name)

    def test_the_second_run_finds_nothing_and_changes_nothing(self):
        make_old_install(self.root)
        rootmigrate.apply(self.root, stamp="t1")
        before = listing(self.root)
        again = rootmigrate.apply(self.root, stamp="t2")
        self.assertEqual((again["moved"], again["backup"]), ([], None))
        self.assertEqual(listing(self.root), before)
        self.assertEqual(rootmigrate.plan(self.root), [])

    def test_a_dry_run_touches_nothing(self):
        make_old_install(self.root)
        before = listing(self.root)
        self.assertGreater(len(rootmigrate.plan(self.root)), 20)
        self.assertEqual(rootmigrate.main([str(self.root)]), 0)
        self.assertEqual(listing(self.root), before)

    def test_it_never_overwrites_and_says_what_it_left(self):
        make_old_install(self.root)
        (self.root / "data").mkdir()
        (self.root / "data" / "etag_cache.json").write_text("THE NEW ONE", encoding="utf-8")
        result = rootmigrate.apply(self.root, stamp="t1")
        self.assertEqual((self.root / "data" / "etag_cache.json").read_text(encoding="utf-8"), "THE NEW ONE")
        self.assertEqual((self.root / "etag_cache.json").read_text(encoding="utf-8"), "content of etag_cache.json", "the old one stays where it was: nothing is lost")
        self.assertEqual([s.name for s, _d in result["conflicts"]], ["etag_cache.json"])
        self.assertEqual(doctor.layout_check(self.root)[0], "warn")

    def test_the_old_backups_join_the_new_folder_without_replacing_any(self):
        make_old_install(self.root)
        (self.root / "config" / "config_backups").mkdir(parents=True)
        (self.root / "config" / "config_backups" / "actions_monitor-20260101-000000.json").write_text("KEPT", encoding="utf-8")
        (self.root / "config_backups" / "actions_monitor-20250101-000000.json").write_text("{}", encoding="utf-8")
        rootmigrate.apply(self.root, stamp="t1")
        names = sorted(p.name for p in (self.root / "config" / "config_backups").iterdir())
        self.assertIn("actions_monitor-20250101-000000.json", names)
        self.assertEqual((self.root / "config" / "config_backups" / "actions_monitor-20260101-000000.json").read_text(encoding="utf-8"), "KEPT")

    def test_undo_puts_every_file_back(self):
        make_old_install(self.root)
        before = {n: (self.root / n).read_bytes() for n in OLD_FILES}
        rootmigrate.apply(self.root, stamp="t1")
        restored = rootmigrate.undo(self.root)
        self.assertGreater(len(restored), 20)
        for name in OLD_FILES:
            self.assertEqual((self.root / name).read_bytes(), before[name], name)
        self.assertFalse((self.root / "data" / "etag_cache.json").exists())
        self.assertTrue((self.root / "accounts" / "personal" / "actions_monitor.json").is_file())
        self.assertEqual(rootmigrate.undo(self.root), [], "the journal is gone: a second undo does nothing")

    def test_the_monitor_does_it_by_itself_unless_told_not_to(self):
        make_old_install(self.root)
        with mock.patch.dict(os.environ, {"MONITOR_NO_AUTO_MIGRATION": "1"}):
            self.assertIsNone(rootmigrate.auto(self.root))
        self.assertTrue((self.root / "etag_cache.json").exists())
        with mock.patch("sys.stderr"):
            self.assertTrue(rootmigrate.auto(self.root, {})["moved"])
        self.check_clean_root()

    def test_the_doctor_tells_what_is_left_and_is_quiet_after(self):
        make_old_install(self.root)
        status, detail = doctor.layout_check(self.root)
        self.assertEqual(status, "warn")
        self.assertRegex(detail, r"^\d+: ")
        self.assertIn("etag_cache.json", [source.name for source, _destination in rootmigrate.plan(self.root)])
        rootmigrate.apply(self.root, stamp="t1")
        self.assertEqual(doctor.layout_check(self.root)[0], "ok")

    def test_the_accounts_migration_reads_the_new_and_the_old_places(self):
        from github_actions_monitor.accounts import accounts
        make_old_install(self.root)
        old = {Path(src).name for src, _dst, _kind in accounts.migration_plan(self.root, self.root)}
        rootmigrate.apply(self.root, stamp="t1")
        new = {Path(src).name for src, _dst, _kind in accounts.migration_plan(self.root, self.root)}
        self.assertEqual(new, old)
        self.assertIn("actions_monitor.json", new)


class TheMapForTheAIs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_the_index_and_the_guide_are_written_where_the_ais_look(self):
        with mock.patch.object(paths, "ASSETS", HERE / "assets"):
            written = ai_index.write("complete", self.root)
        self.assertEqual({p.name for p in written}, {"INDEX.json", "README.md"})
        index = json.loads((self.root / "ai" / "INDEX.json").read_text(encoding="utf-8"))
        self.assertEqual((index["schema"], index["edition"]), ("monitor_ai_index/1", "complete"))
        self.assertEqual(index["folders"]["ai"], str((self.root / "ai").resolve()))
        self.assertEqual(set(index["folders"]), {"config", "data", "logs", "ai"})
        names = {f["name"] for f in index["files"]}
        self.assertTrue({"ALERTS_BRIEF.md", "ai_alerts.jsonl", "ci_red.json", "INDEX.json", "README.md"} <= names)
        self.assertIn("/api/paths", {e["path"] for e in index["endpoints"]})
        for row in index["files"]:
            self.assertTrue(row["purpose"] and row["format"] and row["written_by"] and row["changes"], row["name"])
        self.assertEqual((self.root / "ai" / "README.md").read_bytes(), (HERE / "assets" / "ai" / "README.md").read_bytes())

    def test_every_file_the_index_lists_is_in_the_readme(self):
        text = (HERE / "assets" / "ai" / "README.md").read_text(encoding="utf-8")
        for row in ai_index.FILES:
            self.assertIn(row[0], text, row[0])
        for _id, command, _about in ai_index.TOOLS:
            self.assertTrue((HERE / command).is_file(), command)

    def test_writing_twice_changes_nothing_the_second_time(self):
        ai_index.write("complete", self.root)
        self.assertEqual(ai_index.write("complete", self.root), [])

    def test_the_index_follows_a_file_that_appears(self):
        ai_index.write("complete", self.root)
        (self.root / "ai" / "ALERTS_BRIEF.md").write_text("x", encoding="utf-8")
        self.assertEqual([p.name for p in ai_index.write("complete", self.root)], ["INDEX.json"])
        row = next(f for f in json.loads((self.root / "ai" / "INDEX.json").read_text(encoding="utf-8"))["files"] if f["name"] == "ALERTS_BRIEF.md")
        self.assertEqual((row["exists"], row["bytes"]), (True, 1))

    def test_the_answer_of_api_paths_says_where_everything_is_and_what_is_left(self):
        make_old_install(self.root)
        report = ai_index.paths_report("lite", self.root)
        self.assertEqual((report["schema"], report["edition"]), ("monitor_paths/1", "lite"))
        self.assertIn("ALERTS_BRIEF.md", report["leftovers"])
        rootmigrate.apply(self.root, stamp="t1")
        report = ai_index.paths_report("lite", self.root)
        self.assertEqual(report["leftovers"], [])
        by_name = {f["name"]: f for f in report["files"]}
        self.assertTrue(by_name["ALERTS_BRIEF.md"]["exists"])
        self.assertEqual(by_name["ALERTS_BRIEF.md"]["path"], str(self.root / "ai" / "ALERTS_BRIEF.md"))

    def test_the_gate_script_finds_the_same_folders_as_the_monitor(self):
        cases = ({}, {"MONITOR_AI_DIR": "/somewhere/ai"}, {"MONITOR_DATA_DIR": "/vol/data"}, {"MONITOR_CONFIG_DIR": "/vol/config"})
        for env in cases:
            with mock.patch.dict(os.environ, {k: "" for k in ("MONITOR_AI_DIR", "MONITOR_DATA_DIR", "MONITOR_CONFIG_DIR", "MONITOR_PATHS_FILE")}), mock.patch.dict(os.environ, env):
                self.assertEqual(Path(os.path.abspath(ai_hook.own_folder("ai"))), Path(os.path.abspath(paths.folder("ai"))), env)
                self.assertEqual(Path(os.path.abspath(ai_hook.own_folder("config"))), Path(os.path.abspath(paths.folder("config"))), env)

    def test_the_red_workflows_file_goes_to_the_folder_of_the_ais_by_default(self):
        self.assertEqual(ci_red.target_path("", self.root), self.root / "ai" / "ci_red.json")
        self.assertEqual(ci_red.target_path("elsewhere/x.json", self.root), self.root / "elsewhere" / "x.json")
        self.assertIsNone(ci_red.target_path("off", self.root))


class TheEntryPointsLiveInBin(unittest.TestCase):
    def test_the_hook_installer_registers_the_script_of_bin(self):
        from github_actions_monitor.integrations import ai_hook_install
        self.assertEqual(ai_hook_install.SCRIPT, HERE / "bin" / "ai_hook.py")
        self.assertTrue(ai_hook_install.SCRIPT.is_file())

    def test_the_supervisor_starts_its_children_with_the_script_of_bin(self):
        from github_actions_monitor.accounts import accounts_supervisor
        child = accounts_supervisor.Child("a", 9999)
        self.assertIn(str(HERE / "bin" / "account_child.py"), child.command)
        self.assertTrue((HERE / "bin" / "account_child.py").is_file())

    def test_the_docs_x8_tell_the_new_commands(self):
        for text in ((HERE / "docs" / "CLI.md").read_text(encoding="utf-8"), (HERE / "docs" / "AI_ALERTS.md").read_text(encoding="utf-8")):
            self.assertIn("bin/monitor_cli.py", text)
            self.assertNotRegex(text, r"(?<![/\w])monitor_cli\.py")


if __name__ == "__main__":
    unittest.main()
