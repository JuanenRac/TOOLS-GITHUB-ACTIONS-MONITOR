# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`completions bash|zsh|fish|powershell`: the script is written from the real parser, so what it offers is exactly what the command accepts (a new option cannot be forgotten), and the command
only prints: it needs no monitor and writes no file."""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_190_cli as base  # noqa: E402
from github_actions_monitor.cli import completions, monitor_cli  # noqa: E402


def parser_facts():
    parser = monitor_cli.build_parser()
    options, choices, commands = set(), {}, []
    for action in parser._actions:
        for name in action.option_strings:
            if name.startswith("--"):
                options.add(name)
                if action.choices:
                    choices[name] = [str(c) for c in action.choices]
        if action.dest == "command":
            commands = list(action.choices)
    return options, choices, commands


class Parity(unittest.TestCase):
    def test_every_option_of_the_parser_is_in_every_script(self):
        options, _, _ = parser_facts()
        for shell in completions.SHELLS:
            text = completions.script(shell, monitor_cli.build_parser(), monitor_cli.WORDS_BY_COMMAND)
            found = set(re.findall(r"--[a-z][a-z-]*", text)) if shell != "fish" else {"--" + m for m in re.findall(r"-l ([a-z-]+)", text)}
            self.assertEqual(found & options, options, (shell, sorted(options - found)))
            self.assertEqual(found - options, set(), (shell, sorted(found - options)))

    def test_every_command_and_every_choice_is_offered(self):
        _, choices, commands = parser_facts()
        for shell in completions.SHELLS:
            text = completions.script(shell, monitor_cli.build_parser(), monitor_cli.WORDS_BY_COMMAND)
            for command in commands:
                self.assertRegex(text, r"(?<![\w-])" + re.escape(command) + r"(?![\w-])", (shell, command))
            for name, values in choices.items():
                for value in values:
                    self.assertIn(value, text, (shell, name, value))

    def test_the_words_of_each_command_are_the_ones_the_parser_accepts(self):
        accepted = set(next(a for a in monitor_cli.build_parser()._actions if a.dest == "action").choices)
        for command, words in monitor_cli.WORDS_BY_COMMAND.items():
            self.assertIn(command, monitor_cli.COMMANDS)
            self.assertTrue(set(words) <= accepted, (command, set(words) - accepted))

    def test_the_new_options_are_there(self):
        options, _, commands = parser_facts()
        for name in ("--format", "--interval", "--once", "--exit-on-change", "--no-clear"):
            self.assertIn(name, options)
        for command in ("watch", "completions", "kiosk"):
            self.assertIn(command, commands)

    def test_the_output_is_stable(self):
        for shell in completions.SHELLS:
            first = completions.script(shell, monitor_cli.build_parser(), monitor_cli.WORDS_BY_COMMAND)
            second = completions.script(shell, monitor_cli.build_parser(), monitor_cli.WORDS_BY_COMMAND)
            self.assertEqual(first, second)
            self.assertTrue(first.endswith("\n"))


class Command(unittest.TestCase):
    def test_it_prints_the_script_and_needs_no_monitor(self):
        for shell in completions.SHELLS:
            code, out, err = base.run("completions", shell, "--url", "http://127.0.0.1:1", "--lang", "en")
            self.assertEqual((code, err), (0, ""), shell)
            self.assertIn("monitor_cli", out)

    def test_json_carries_the_script(self):
        code, out, _ = base.run("completions", "bash", "--json", "--lang", "en")
        self.assertEqual(code, 0)
        self.assertIn("complete -F", json.loads(out)["data"]["script"])

    def test_it_writes_nothing_in_the_home_or_the_working_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            before, here = set(os.listdir(folder)), os.getcwd()
            os.chdir(folder)
            try:
                base.run("completions", "zsh", "--lang", "en")
            finally:
                os.chdir(here)
            self.assertEqual(set(os.listdir(folder)), before)

    def test_a_shell_that_does_not_exist_is_a_usage_error(self):
        code, _, err = base.run("completions", "--lang", "en")
        self.assertEqual(code, 1)
        self.assertTrue(err.strip())

    def test_there_is_no_install_option(self):
        options, _, _ = parser_facts()
        self.assertNotIn("--install", options)      # the command prints; it never edits the files of a user


if __name__ == "__main__":
    unittest.main()
