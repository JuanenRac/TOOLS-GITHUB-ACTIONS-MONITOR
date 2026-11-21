# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Corrections of the page, the guides and the command line: the Fleet screen says how many tiles the server left out, the kiosk follows screens.show_repo_names, the guides count four screens,
the command line refuses a format it cannot write, lists every command it has, and the panels of the Sentinel grow when they carry information."""
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
SCREENS = HERE / "assets" / "static" / "screens.html"


class TheFleetScreenCountsWhatTheServerLeftOut(unittest.TestCase):
    def setUp(self):
        self.html = SCREENS.read_text(encoding="utf-8")

    def test_fit_takes_the_rows_the_server_left_out(self):
        self.assertRegex(self.html, r"function fit\(list,keep,extra\)")
        self.assertIn('T("ui.scr_more",{n:hid+left})', self.html)
        self.assertRegex(self.html, r"if\(hid>0\|\|left>0\)")

    def test_the_fleet_gives_the_hidden_number_of_each_group(self):
        self.assertRegex(self.html, r'querySelectorAll\("\.tiles"\)\.forEach\(\(l,i\)=>fit\(l,0,num\(gs\[i\]&&gs\[i\]\.hidden\)\)\)')


if __name__ == "__main__":
    unittest.main()
