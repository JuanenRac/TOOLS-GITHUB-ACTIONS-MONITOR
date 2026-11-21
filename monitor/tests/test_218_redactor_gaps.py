# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The cleaner leaves no piece of a secret that was split, hidden among invisible characters, written as a temporary key or cut before it was cleaned."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.integrations import ai_actions  # noqa: E402
from github_actions_monitor.security import redactor  # noqa: E402

TAIL = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
PAT = "github_pat_11ABCDEFG0aBcDeFgHiJk_" + "ZyXwVuTsRqPoNmLkJiHgFeDcBa9876543210"
CASES = {
    "github_pat split in two lines": ("token " + PAT[:30] + "\n" + PAT[30:], PAT[30:]),
    "github_pat split with the second half only 30 long": ("x github_pat_11ABC\n" + "Z" * 30, "Z" * 30),
    "AWS temporary key (ASIA)": ("aws key " + "ASIA" + "IOSFODNN7EXAMPLE in use", "ASIA" + "IOSFODNN7EXAMPLE"),
    "AWS long-term key (AKIA)": ("aws key AKIAIOSFODNN7EXAMPLE in use", "AKIAIOSFODNN7EXAMPLE"),
    "soft hyphen inside ghp_": ("see gh" + "p­_" + TAIL, TAIL),
    "invisible separator inside ghp_": ("see gh⁣p_" + TAIL, TAIL),
    "word joiner function-application inside ghp_": ("see ghp⁡_" + TAIL, TAIL),
    "password of a URL with a slash": ("clone https://bob:hunter2/secretpart@example.com/x", "hunter2"),
    "password of a URL with a slash (second piece)": ("clone https://bob:hunter2/secretpart@example.com/x", "secretpart"),
    "plain ghp_": ("ghp_" + TAIL, TAIL),
    "plain github_pat_": (PAT, PAT[20:]),
}


def survives(clean, secret):
    secret = secret.strip()
    if len(secret) <= 12:
        return secret in clean
    return any(secret[i:i + 12] in clean for i in range(len(secret) - 11))


class Gaps(unittest.TestCase):
    def test_no_piece_of_twelve_characters_of_the_secret_survives(self):
        for name, (text, secret) in CASES.items():
            with self.subTest(name):
                self.assertFalse(survives(redactor.redact(text), secret), redactor.redact(text))

    def test_what_is_not_a_secret_is_left_alone(self):
        for text in ("see https://github.com/o/r/actions/runs/123", "visit http://host:8080/path and mail ana at home", "the AKIA prefix is public"):
            self.assertEqual(redactor.redact(text), text)

    def test_the_output_of_an_action_is_cleaned_before_it_is_cut(self):
        class Done:
            returncode, stderr = 1, ""
            stdout = "ghp_" + TAIL + " " + "x" * 280 + " end"
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            actions = ai_actions.Actions(log_file=Path(tmp) / "log.jsonl")
            config = {"ai": {"actions": {"enabled": True, "execute": True, "require_approval": False}}}
            ident = actions.propose("run gh run rerun 5 --failed", "r", config, {"r"}, lambda repo, n: True, lambda repo, n: True, "o")[0]
            command = actions.listing(config)[0]["command"]
            actions.run(ident["id"], command, config, runner=lambda argv, **kw: Done())
            written = (Path(tmp) / "log.jsonl").read_text(encoding="utf-8")
        self.assertNotIn(TAIL[:12], written)
        self.assertNotIn(TAIL[-12:], written)


if __name__ == "__main__":
    unittest.main()
