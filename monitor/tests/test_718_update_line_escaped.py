# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The line of the update notice in the About window is drawn as HTML, so the version it names goes through `esc()` like every other text from outside (there is no real way to make the version hostile:
it passes a tag check first, this keeps it so)."""
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401

PAGE = (Path(__file__).resolve().parent.parent / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")


class UpdateLine(unittest.TestCase):
    def test_the_version_in_the_update_line_is_escaped(self):
        line = next(ln for ln in PAGE.splitlines() if ln.startswith("function updLine("))
        self.assertIn('esc(T("ui.update_available",{version:u.latest}))', line)

    def test_no_text_with_a_value_from_outside_is_joined_to_html_unescaped_in_the_about_window(self):
        start = PAGE.index("function updLine(")
        block = PAGE[start:PAGE.index("async function aboutLoad")]
        for call in re.findall(r'T\("[a-z_.]+",\{[^}]*\}\)', block):
            self.assertTrue(f"esc({call})" in block, call)


if __name__ == "__main__":
    unittest.main()
