# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The last test of the suite (its name sorts after all the others): the suite leaves no file next to the code. A test that starts a process of the monitor gives it folders of its own
(`_testenv.isolated_env`) and a test that writes in the folders of the product removes what it created (`_testenv.guard`); a file left behind makes the next run start from a different state, which is
how the tests of the lite edition (their output is compared word for word) failed in a place where the folder already held the settings of an earlier run."""
import unittest

import _testenv


class TheSuiteLeavesTheTreeAsItFoundIt(unittest.TestCase):
    def test_no_file_was_added_next_to_the_code_while_the_suite_ran(self):
        added = sorted(_testenv.files_next_to_the_code() - _testenv.FILES_AT_START)
        self.assertEqual(added, [], "the suite left files in the folder of the product:\n" + "\n".join(added[:30]))

    def test_the_helper_sees_a_file_that_appears(self):
        from pathlib import Path
        probe = Path(_testenv.PRODUCT) / "state" / "probe_left_by_a_test.txt"
        existed = (Path(_testenv.PRODUCT) / "state").exists()
        probe.parent.mkdir(parents=True, exist_ok=True)
        try:
            probe.write_text("x", encoding="utf-8")
            self.assertIn(str(Path("state") / "probe_left_by_a_test.txt"), _testenv.files_next_to_the_code() - _testenv.FILES_AT_START)
        finally:
            probe.unlink()
            if not existed:
                probe.parent.rmdir()


if __name__ == "__main__":
    unittest.main()
