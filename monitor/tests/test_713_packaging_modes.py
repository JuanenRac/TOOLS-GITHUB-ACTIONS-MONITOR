# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The shell launchers are versioned with the executable bit (the README tells a person who clones the repository to run them), and the zip carries the same bytes whatever the line endings of the
machine that builds it."""
import os
import shutil
import subprocess
import unittest
from pathlib import Path

import _testenv  # noqa: F401
import make_release

HERE = Path(__file__).resolve().parent.parent
LAUNCHERS = ("BATCH_GITHUB_ACTIONS", "MONITOR_GITHUB_ACTIONS", "MONITOR_LITE_GITHUB_ACTIONS")


def staged_modes():
    """{path: mode} of the launchers in the index of git, or None when this is not a checkout (the zip extracted, no git)."""
    if not shutil.which("git") or not (HERE.parent / ".git").exists():
        return None
    names = [f"monitor/{n}{ext}" for n in LAUNCHERS for ext in (".sh", ".command")]
    flags = 0x08000000 if os.name == "nt" else 0
    done = subprocess.run(["git", "-C", str(HERE.parent), "ls-files", "-s", "--", *names], capture_output=True, text=True, timeout=60, creationflags=flags)
    if done.returncode != 0:
        return None
    return {line.split("\t", 1)[1]: line.split()[0] for line in done.stdout.splitlines() if "\t" in line}


class ExecutableBit(unittest.TestCase):
    def test_every_shell_launcher_is_versioned_as_executable(self):
        modes = staged_modes()
        if modes is None:
            self.skipTest("not a git checkout")
        self.assertEqual(len(modes), 6, modes)
        self.assertEqual({m for m in modes.values()}, {"100755"}, modes)


class LineEndings(unittest.TestCase):
    def test_text_travels_with_lf_whatever_the_builder_checked_out(self):
        for name in ("a.py", "a.md", "a.json", "a.txt", "a.html", "a.sh", "a.command"):
            with self.subTest(name=name):
                self.assertEqual(make_release.line_endings_for_zip(name, b"x\r\ny\r\n"), b"x\ny\n")
                self.assertEqual(make_release.line_endings_for_zip(name, b"x\ny\n"), b"x\ny\n")

    def test_windows_launchers_travel_with_crlf_from_either_checkout(self):
        for data in (b"@echo off\nexit\n", b"@echo off\r\nexit\r\n"):
            self.assertEqual(make_release.line_endings_for_zip("run.bat", data), b"@echo off\r\nexit\r\n")

    def test_what_is_not_text_is_left_alone(self):
        png = b"\x89PNG\r\n\x1a\n\x00\x00"
        self.assertEqual(make_release.line_endings_for_zip("a.png", png), png)
        self.assertEqual(make_release.line_endings_for_zip("a.json", b"a\r\n\x00b\r\n"), b"a\r\n\x00b\r\n")


if __name__ == "__main__":
    unittest.main()
