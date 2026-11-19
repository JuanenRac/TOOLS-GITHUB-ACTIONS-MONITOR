# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The prompt that sets the monitor up with an AI says the same thing in the eight languages: the seven rules (R1 to R7) are all there, in the same order, and each one names the same keys, commands and
files as the English one (a translation that loses `ai.actions.enabled` from the rule that keeps the actions off is a rule that changed); the steps and the questions are the same in number and the list
of keys the AI may write is identical. The words are the work of the translation; the identifiers are not."""
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DOCS = HERE / "docs"
TAILS = ("spa", "deu", "fra", "ita", "jpn", "zho", "por")
#: a dotted key (`ai.actions.enabled`), a command or file (`gh auth token`, `config/actions_monitor.json`, `SHA256SUMS`) or a variable
IDENT = re.compile(r"(?<![\w/.-])(?:[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+|[A-Za-z_]+/[A-Za-z0-9_./-]+|[A-Z][A-Z0-9]*\d[A-Z0-9]*|[A-Z]+_[A-Z_]+|[a-z]+_[a-z_]+)(?![\w-])")


def prompt(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return text.split("```text", 1)[1].split("\n```", 1)[0]


def rules(text):
    return {m.group(1): m.group(2) for m in re.finditer(r"^(R[1-7])\.\s(.*)$", text, re.M)}


def keys_of(text):
    """The list between the last [keys] and the last [/keys]: the rules mention both marks in words before it."""
    return text.rsplit("[keys]", 1)[1].rsplit("[/keys]", 1)[0].replace(",", " ").split()


def idents(line):
    return {m for m in IDENT.findall(line) if not m.endswith(".")}


class SetupPrompt(unittest.TestCase):
    def setUp(self):
        self.base = prompt(DOCS / "AI_SETUP_PROMPT.md")

    def other(self, tail):
        return prompt(DOCS / f"AI_SETUP_PROMPT_{tail}.md")

    def test_the_seven_rules_are_in_every_language_in_order(self):
        self.assertEqual(sorted(rules(self.base)), ["R1", "R2", "R3", "R4", "R5", "R6", "R7"])
        for tail in TAILS:
            text = self.other(tail)
            self.assertEqual(sorted(rules(text)), ["R1", "R2", "R3", "R4", "R5", "R6", "R7"], tail)
            order = [m.group(1) for m in re.finditer(r"^(R[1-7])\.\s", text, re.M)]
            self.assertEqual(order, ["R1", "R2", "R3", "R4", "R5", "R6", "R7"], tail)

    def test_each_rule_names_the_same_keys_commands_and_files(self):
        base = rules(self.base)
        problems = []
        for tail in TAILS:
            got = rules(self.other(tail))
            for rule, line in base.items():
                missing = sorted(idents(line) - idents(got[rule]))
                if missing:
                    problems.append(f"{tail} {rule}: {', '.join(missing)}")
        self.assertEqual(problems, [])

    def test_the_rule_that_keeps_the_actions_off_names_every_switch(self):
        for name in ("ai.actions.enabled",):
            for tail in (None,) + TAILS:
                text = self.base if tail is None else self.other(tail)
                self.assertIn(name, rules(text)["R5"], tail)

    def test_the_steps_the_questions_and_the_list_of_keys_are_the_same(self):
        def numbers(text, pattern):
            return re.findall(pattern, text, re.M)
        for tail in TAILS:
            text = self.other(tail)
            self.assertEqual(numbers(text, r"^\S+ ([0-5]) - "), numbers(self.base, r"^\S+ ([0-5]) - "), tail)
            self.assertEqual(numbers(text, r"^[A-Z]{1,3}(\d+)\s"), numbers(self.base, r"^[A-Z]{1,3}(\d+)\s"), tail)
            self.assertEqual(keys_of(text), keys_of(self.base), tail)

    def test_no_secret_is_asked_for_in_any_language(self):
        for tail in (None,) + TAILS:
            text = self.base if tail is None else self.other(tail)
            self.assertIn("gh auth token", rules(text)["R2"], tail)      # the commands that show a secret are named in the rule that forbids them


if __name__ == "__main__":
    unittest.main()
