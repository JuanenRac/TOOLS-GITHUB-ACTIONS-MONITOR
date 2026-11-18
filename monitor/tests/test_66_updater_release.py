# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The updater as a product: the loose copy that is published next to the zip (with the registry inside), the entry `monitor_cli update` and the documentation of the eight languages."""
import io
import json
import re
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import make_release  # noqa: E402

LANGS = ("deu", "fra", "ita", "jpn", "por", "spa", "zho")


class LooseCopy(unittest.TestCase):
    def load(self):
        text = make_release.standalone_updater()
        namespace = {"__name__": "monitor_updater_loose"}
        exec(compile(text, "monitor_updater_loose.py", "exec"), namespace)      # noqa: S102 - our own file, read from this tree
        return text, namespace

    def test_the_loose_copy_carries_every_version_and_the_launchers(self):
        text, ns = self.load()
        registry = ns["Registry"].embedded()
        self.assertEqual(registry.versions()[0], "1.8.1")
        self.assertIn("2.0.8", registry.versions())
        self.assertTrue(registry.launchers.get("files"))
        self.assertEqual(registry.check(), [])
        self.assertNotIn("\r", text)

    def test_the_loose_copy_is_the_same_file_with_only_the_registry_added(self):
        text, _ = self.load()
        source = (HERE / "tools" / "monitor_updater.py").read_text(encoding="utf-8").replace("\r\n", "\n")
        head, tail = source.split("EMBEDDED_REGISTRY = None", 1)
        self.assertTrue(text.startswith(head))
        self.assertTrue(text.endswith(tail))

    def test_the_registry_and_the_updater_travel_in_the_zip(self):
        names = {p.relative_to(HERE).as_posix() for p in make_release.members()}
        self.assertIn("tools/monitor_updater.py", names)
        self.assertIn("assets/migrations/2.0.8.json", names)
        self.assertIn("assets/migrations/launchers.json", names)


class CommandLine(unittest.TestCase):
    def run_cli(self, *args):
        from github_actions_monitor.cli import monitor_cli
        out = io.StringIO()
        with redirect_stdout(out):
            code = monitor_cli.main(["update", *args])
        return code, out.getvalue()

    def test_update_history_goes_to_the_updater_and_returns_its_code(self):
        code, text = self.run_cli("history", "--dir", str(HERE), "--json")
        self.assertEqual(code, 0)
        self.assertIsInstance(json.loads(text), list)

    def test_update_help_is_the_help_of_the_updater(self):
        code, text = self.run_cli("--help")
        self.assertEqual(code, 0)
        self.assertIn("--dry-run", text)

    def test_update_is_a_command_of_the_cli(self):
        from github_actions_monitor.cli import monitor_cli
        self.assertIn("update", monitor_cli.COMMANDS)


class Docs(unittest.TestCase):
    def test_the_guide_exists_in_the_eight_languages_with_the_same_commands(self):
        base = (HERE / "docs" / "UPDATE.md").read_text(encoding="utf-8")
        commands = sorted(set(re.findall(r"`(--[a-z-]+)`", base)))
        self.assertTrue(commands)
        for lang in LANGS:
            path = HERE / "docs" / f"UPDATE_{lang}.md"
            self.assertTrue(path.is_file(), path.name)
            text = path.read_text(encoding="utf-8")
            for flag in commands:
                self.assertIn(flag, text, f"{path.name} lacks {flag}")

    def test_every_option_of_the_updater_is_in_the_guide(self):
        import monitor_updater
        parser = monitor_updater.build_parser()
        flags = {o for a in parser._actions for o in a.option_strings if o.startswith("--") and o != "--help"}
        guide = (HERE / "docs" / "UPDATE.md").read_text(encoding="utf-8")
        self.assertEqual(sorted(f for f in flags if f not in guide), [])


if __name__ == "__main__":
    unittest.main()
