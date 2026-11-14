# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The time limits of the release gate can be changed with documented variables, have a realistic default, and are read when they are used."""
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import make_release  # noqa: E402


class Limits(unittest.TestCase):
    def test_the_defaults_are_realistic_for_a_loaded_computer(self):
        self.assertGreaterEqual(make_release.TEST_TIMEOUT, 3600)
        self.assertGreaterEqual(make_release.CLEAN_INSTALL_TIMEOUT, 3600)
        self.assertEqual(make_release.test_timeout({}), make_release.TEST_TIMEOUT)
        self.assertEqual(make_release.clean_install_timeout({}), make_release.CLEAN_INSTALL_TIMEOUT)

    def test_the_variables_change_them_and_nonsense_is_ignored(self):
        self.assertEqual(make_release.test_timeout({"MONITOR_RELEASE_TEST_TIMEOUT": "7200"}), 7200)
        self.assertEqual(make_release.clean_install_timeout({"MONITOR_RELEASE_CLEAN_TIMEOUT": "5400"}), 5400)
        for bad in ("", "abc", "-5", "10", "999999", "1.5"):
            self.assertEqual(make_release.test_timeout({"MONITOR_RELEASE_TEST_TIMEOUT": bad}), make_release.TEST_TIMEOUT, bad)

    def test_run_tests_reads_the_value_when_it_is_called(self):
        seen = []

        def fake(*args, **kwargs):
            seen.append(kwargs["timeout"])
            return subprocess.CompletedProcess(args, 0, stdout="OK\n", stderr="OK\n")
        with mock.patch.object(make_release.subprocess, "run", fake):
            with mock.patch.dict(os.environ, {"MONITOR_RELEASE_TEST_TIMEOUT": "4321"}):
                make_release.run_tests()
            make_release.run_tests(timeout=99)
        self.assertEqual(seen, [4321, 99])

    def test_the_variables_are_documented(self):
        for suffix in ("", "_deu", "_fra", "_ita", "_jpn", "_por", "_spa", "_zho"):
            text = (HERE / "docs" / f"DEPLOYMENT{suffix}.md").read_text(encoding="utf-8")
            self.assertIn("MONITOR_RELEASE_TEST_TIMEOUT", text, suffix)
            self.assertIn("MONITOR_RELEASE_CLEAN_TIMEOUT", text, suffix)


if __name__ == "__main__":
    unittest.main()
