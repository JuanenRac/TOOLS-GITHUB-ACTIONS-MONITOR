# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A script with a shebang travels in the zip with Unix line endings, even when it was checked out with Windows ones."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import make_release  # noqa: E402


class ShebangLineEndings(unittest.TestCase):
    def test_a_script_with_a_shebang_loses_its_carriage_returns(self):
        self.assertEqual(make_release.lf_for_scripts(b"#!/usr/bin/env python3\r\nprint(1)\r\n"), b"#!/usr/bin/env python3\nprint(1)\n")

    def test_a_file_without_a_shebang_is_not_touched(self):
        self.assertEqual(make_release.lf_for_scripts(b"# text\r\nx\r\n"), b"# text\r\nx\r\n")

    def test_the_entry_points_of_the_product_start_with_a_shebang_and_pass_the_conversion(self):
        scripts = sorted((HERE / "bin").glob("*.py"))
        self.assertTrue(scripts)
        for path in scripts:
            data = make_release.lf_for_scripts(path.read_bytes())
            if data.startswith(b"#!"):
                self.assertNotIn(b"\r", data.split(b"\n", 1)[0], path.name)


if __name__ == "__main__":
    unittest.main()
