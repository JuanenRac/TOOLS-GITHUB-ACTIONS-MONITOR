# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The version of the tool is shown in the title and the heading of the web panel and in the start-up line of the server."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import actions_monitor  # noqa: E402
from tool_version import TOOL_VERSION  # noqa: E402


class VersionShown(unittest.TestCase):
    def test_the_page_shows_the_version_and_no_placeholder_is_left(self):
        page = actions_monitor.render_page()
        self.assertIn(f'"version": "{TOOL_VERSION}"', page)
        self.assertIn('id="ver"', page)

    def test_the_start_up_line_prints_the_version(self):
        text = (HERE / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn('i18n.t("mon.version", version=TOOL_VERSION)', text)


if __name__ == "__main__":
    unittest.main()
