# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The folder layout: the code is a package in src/, the page, the examples and the languages are in assets/, the data of the person who runs the monitor never goes into either, no flat
module is left next to the launchers, the entry points of the product folder are tiny, `python -m github_actions_monitor[.lite]` starts, and tools/migrate_layout.py moves an old flat
installation out of the way without touching any data."""
import json
import os
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
from github_actions_monitor.app import toolconfig  # noqa: E402
from github_actions_monitor.cli import doctor  # noqa: E402
from github_actions_monitor.util import layout, paths, rootmigrate  # noqa: E402
import make_release as mr  # noqa: E402
import migrate_layout  # noqa: E402

ENTRY_POINTS = {"actions_monitor", "account_child", "gha_dispatch_all", "launcher_msg", "lint_workflows", "migrate_state", "monitor_cli", "read_report", "release_candidates", "release_notes",
                "ai_hook", "mcp_server", "tui", "tui_textual"}


def package_modules():
    return [p for p in (HERE / "src" / "github_actions_monitor").rglob("*.py") if "__pycache__" not in p.parts]


class TheTree(unittest.TestCase):
    def test_paths_point_at_the_product_folder(self):
        self.assertEqual(paths.ROOT.resolve(), HERE.resolve())
        self.assertTrue((paths.SRC / "github_actions_monitor" / "__init__.py").is_file())
        for folder in (paths.EXAMPLES, paths.STATIC, paths.LOCALES, paths.DOCS):
            self.assertTrue(folder.is_dir(), folder)

    def test_no_module_of_logic_is_left_flat_next_to_the_launchers(self):
        """The only .py files of the product folder are the entry points: tiny, with no function and no class, and they do nothing when they are imported."""
        self.assertEqual(list(HERE.glob("*.py")), [], "the root holds no .py file")
        flat = {p.stem: p for p in (HERE / "bin").glob("*.py")}
        self.assertEqual(set(flat), ENTRY_POINTS)
        for name, path in flat.items():
            text = path.read_text(encoding="utf-8")
            self.assertIn("runpy.run_module", text, name)
            self.assertIn('if __name__ == "__main__":', text, name)
            self.assertNotRegex(text, r"(?m)^\s*(def|class)\s", name)
            self.assertLess(len(text.splitlines()), 14, name)

    def test_a_module_name_exists_once_in_the_package(self):
        stems = [p.stem for p in package_modules() if p.stem not in ("__init__", "__main__")]
        self.assertEqual(sorted(stems), sorted(set(stems)), "two modules with the same name (a flat duplicate)")
        self.assertFalse(list(HERE.glob("*.example.json")) + list(HERE.glob("*.html")) + list(HERE.glob("quotas.json")), "examples and the page live in assets/")
        self.assertFalse((HERE / "locales").exists(), "the languages live in assets/locales")
        self.assertFalse(list((HERE / "assets").rglob("*.py")), "assets/ holds no code")

    def test_every_entry_point_has_its_module_in_the_package(self):
        stems = {p.stem for p in package_modules()}
        self.assertLessEqual(ENTRY_POINTS, stems)

    def test_the_data_of_the_person_never_goes_into_src_or_assets(self):
        names = set(mr.FORBIDDEN_NAMES)
        for base in (HERE / "src", HERE / "assets"):
            found = [p for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts and (p.name in names or p.suffix in (".jsonl", ".log", ".tmp"))]
            self.assertEqual(found, [], base.name)

    def test_the_zip_lists_the_new_layout_and_the_launchers_stay_in_the_root(self):
        names = {p.relative_to(HERE).as_posix() for p in mr.members()}
        for needed in ("MONITOR_GITHUB_ACTIONS.sh", "MONITOR_LITE_GITHUB_ACTIONS.bat", "BATCH_GITHUB_ACTIONS.command", "bin/read_report.py", "src/github_actions_monitor/__main__.py", "src/github_actions_monitor/lite.py",
                       "assets/static/actions_monitor.html", "assets/examples/quotas.json", "assets/locales/pt.json", "tools/make_release.py", "tools/migrate_layout.py"):
            self.assertIn(needed, names)
        self.assertFalse([n for n in names if n.endswith(".py") and "/" not in n])
        self.assertEqual({n[4:-3] for n in names if n.startswith("bin/")}, ENTRY_POINTS)
        self.assertEqual(mr.check_entries(["github_actions_monitor/" + n for n in sorted(names)]), [])

    def test_the_launchers_start_the_package_with_src_on_the_path(self):
        for name in ("MONITOR_GITHUB_ACTIONS", "MONITOR_LITE_GITHUB_ACTIONS", "BATCH_GITHUB_ACTIONS"):
            for ext in (".bat", ".sh"):
                text = (HERE / (name + ext)).read_text(encoding="utf-8", errors="replace")
                self.assertIn("PYTHONPATH", text, name + ext)
                self.assertIn("src", text, name + ext)
                self.assertIn("-m github_actions_monitor", text, name + ext)
                self.assertNotRegex(text, r"(?m)^\s*(py -3|\"\$PY\") (actions_monitor|launcher_msg|gha_dispatch_all)\.py", name + ext)


class TheNeutralExamples(unittest.TestCase):
    def test_a_first_start_without_any_file_reads_the_examples_of_assets(self):
        """The template of the configuration names `targets.example.json` without a folder: it is found in assets/examples/, and the files of the person are looked for next to the launchers."""
        env = {k: v for k, v in os.environ.items() if k not in ("MONITOR_TARGETS_FILE", "MONITOR_ECOSYSTEMS_FILE", "MONITOR_PROFILES_FILE")}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, env, clear=True), mock.patch.object(toolconfig, "CONFIG_FILE", Path(tmp) / "none.json"), mock.patch.object(toolconfig, "HERE", Path(tmp)):
            toolconfig.forget()
            try:
                for found in (toolconfig.targets_path(), toolconfig.profiles_path()):
                    self.assertEqual(found.parent, paths.EXAMPLES)
                    self.assertTrue(found.is_file())
                self.assertTrue(toolconfig.ecosystems())
            finally:
                toolconfig.forget()

    def test_quotas_json_of_your_own_next_to_the_launchers_wins(self):
        from github_actions_monitor.data_pipeline import quota
        self.assertEqual(quota.QUOTAS_FILE.parent, paths.EXAMPLES)


class TheEntryPoints(unittest.TestCase):
    def run_python(self, *args):
        env = dict(os.environ, PYTHONPATH=str(HERE / "src"), PYTHONDONTWRITEBYTECODE="1", MONITOR_NO_NESTED="1")
        return subprocess.run([sys.executable, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=str(HERE), timeout=60)

    def test_python_dash_m_starts_the_complete_monitor_and_the_lite_one(self):
        _testenv.guard(self)      # the first start writes the template of the configuration next to the launchers: removed afterwards
        for module, extra in (("github_actions_monitor", []), ("github_actions_monitor.lite", [])):
            done = self.run_python("-m", module, "--help", *extra)
            self.assertEqual(done.returncode, 0, module + done.stderr[-400:])
            self.assertIn("--port", done.stdout, module)

    def test_lite_through_dash_m_turns_the_lite_switch_on(self):
        done = self.run_python("-c", "import sys; sys.argv = ['x']; from github_actions_monitor import lite; from github_actions_monitor.app import actions_monitor as am; "
                                     "am.main = lambda: print('lite', am.lite_requested()) or 0; lite.main([]); print(sys.argv[1:])")
        self.assertEqual(done.stdout.split(), ["lite", "True", "['--lite']"], done.stderr)

    def test_the_old_commands_still_work_through_the_entry_points(self):
        done = subprocess.run([sys.executable, "-I", str(HERE / "bin" / "read_report.py"), "--version"], capture_output=True, text=True, encoding="utf-8", timeout=60, cwd=str(HERE))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("github_actions_monitor", done.stdout)

    def test_importing_an_entry_point_by_its_old_name_starts_nothing(self):
        done = subprocess.run([sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {str(HERE / "bin")!r}); import actions_monitor, read_report; print('quiet')"], capture_output=True, text=True, timeout=30)
        self.assertEqual(done.stdout.strip(), "quiet", done.stderr)


def make_old_install(root):
    """A folder as 1.7.x left it, with the new layout unzipped over it."""
    (root / "src" / "github_actions_monitor").mkdir(parents=True)
    (root / "assets" / "locales").mkdir(parents=True)
    (root / "assets" / "static").mkdir()
    (root / "read_report.py").write_text("# old\ndef main():\n    return 0\n", encoding="utf-8")                         # an old module: the new entry point carries runpy
    (root / "monitor_cli.py").write_text("import runpy\nrunpy.run_module('x')\n", encoding="utf-8")                      # the new entry point: stays
    (root / "i18n.py").write_text("# old i18n\n", encoding="utf-8")
    (root / "actions_monitor.html").write_text("<html></html>", encoding="utf-8")
    (root / "targets.example.json").write_text("{}", encoding="utf-8")
    (root / "locales").mkdir()
    (root / "locales" / "en.json").write_text("{}", encoding="utf-8")
    for name, body in (("actions_monitor.json", '{"x": 1}'), ("targets.json", "{}"), ("quotas.json", "{}"), ("events_monitor.jsonl", "{}\n"), ("etag_cache.json", "{}")):
        (root / name).write_text(body, encoding="utf-8")
    (root / "accounts" / "a").mkdir(parents=True)
    (root / "accounts" / "a" / "actions_monitor.json").write_text("{}", encoding="utf-8")


class MigratingAnOldInstallation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_old_install(self.root)
        self.addCleanup(self.tmp.cleanup)

    def listing(self):
        return sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file())

    def test_it_finds_the_old_files_and_not_the_data_or_the_new_entry_points(self):
        found = sorted(p.as_posix() for p in layout.stale(self.root))
        self.assertEqual(found, ["actions_monitor.html", "i18n.py", "locales", "read_report.py", "targets.example.json"])

    def test_nothing_is_found_without_the_new_layout(self):
        (self.root / "src" / "github_actions_monitor").rmdir()
        self.assertEqual(layout.stale(self.root), [])

    def test_a_dry_run_changes_nothing(self):
        before = self.listing()
        self.assertEqual(migrate_layout.main([str(self.root)]), 0)
        self.assertEqual(self.listing(), before)

    def test_apply_copies_the_configuration_moves_the_old_code_and_keeps_every_datum(self):
        before = self.listing()
        data = {n: (self.root / n).read_bytes() for n in ("actions_monitor.json", "targets.json", "quotas.json", "events_monitor.jsonl", "etag_cache.json")}
        backup, moved, copied = migrate_layout.apply(self.root, stamp="t1")
        self.assertEqual(backup.name, "layout_backup_t1")
        self.assertEqual(sorted(moved), ["actions_monitor.html", "i18n.py", "locales", "read_report.py", "targets.example.json"])
        self.assertEqual(sorted(copied), ["actions_monitor.json", "quotas.json", "targets.json"])
        for name, content in data.items():
            self.assertEqual((self.root / name).read_bytes(), content, name)
        self.assertTrue((self.root / "accounts" / "a" / "actions_monitor.json").is_file())
        self.assertTrue((self.root / "monitor_cli.py").is_file())
        self.assertEqual((backup / "old_code" / "locales" / "en.json").read_text(encoding="utf-8"), "{}")
        self.assertEqual((backup / "old_code" / "read_report.py").read_text(encoding="utf-8").splitlines()[0], "# old")
        self.assertEqual((backup / "config" / "actions_monitor.json").read_text(encoding="utf-8"), '{"x": 1}')
        gone = [n for n in before if not (self.root / n).exists()]
        self.assertTrue(all((backup / "old_code" / n).exists() for n in gone), "everything that left is in the backup (nothing was deleted)")

    def test_running_it_twice_finds_nothing_the_second_time(self):
        self.assertEqual(migrate_layout.main([str(self.root), "--apply"]), 0)
        self.assertEqual(layout.stale(self.root), [])
        before = self.listing()
        self.assertEqual(migrate_layout.main([str(self.root), "--apply"]), 0)
        self.assertEqual(self.listing(), before)

    def test_an_existing_backup_folder_is_never_overwritten(self):
        (self.root / "layout_backup_t2").mkdir()
        with self.assertRaises(SystemExit):
            migrate_layout.apply(self.root, stamp="t2")
        self.assertTrue((self.root / "read_report.py").is_file())

    def test_the_doctor_warns_while_old_files_are_left_and_is_quiet_after(self):
        status, detail = doctor.layout_check(self.root)
        self.assertEqual(status, "warn")
        self.assertIn("read_report.py", detail)
        migrate_layout.apply(self.root, stamp="t3")
        self.assertEqual(doctor.layout_check(self.root)[0], "warn", "the data of 1.8.1 and older is still next to the launchers")
        rootmigrate.apply(self.root, stamp="t3")
        self.assertEqual(doctor.layout_check(self.root)[0], "ok")
        self.assertIn("layout", doctor.ORDER)

    def test_the_real_product_folder_has_nothing_left_over(self):
        self.assertEqual(layout.stale(HERE), [])
        self.assertEqual(doctor.layout_check(HERE)[0], "ok")

    def test_the_texts_exist_in_the_eight_languages(self):
        from github_actions_monitor import i18n
        for key in ("ml.help_apply", "ml.nothing", "ml.found", "ml.dry_run", "ml.done", "doctor.t.layout", "doctor.f.layout"):
            for lang in i18n.LANGS:
                data = json.loads((paths.LOCALES / f"{lang}.json").read_text(encoding="utf-8"))
                self.assertTrue(data.get(key, "").strip(), f"{lang}:{key}")


if __name__ == "__main__":
    unittest.main()
