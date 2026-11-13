# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The version of the tool is shown in the title and the heading of the web panel and in the start-up line of the server."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.tool_version import TOOL_VERSION  # noqa: E402


class VersionShown(unittest.TestCase):
    def test_the_page_shows_the_version_and_no_placeholder_is_left(self):
        page = actions_monitor.render_page()
        self.assertIn(f'"version": "{TOOL_VERSION}"', page)
        self.assertIn('id="ver"', page)

    def test_the_start_up_output_names_the_version_once(self):
        """One banner line carries the name and the version; the line of authorship and the licence repeats neither (every language, both editions)."""
        from github_actions_monitor.util import banner
        from github_actions_monitor import i18n
        text = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertNotIn('i18n.t("mon.version"', text)
        for lang in i18n.LANGS:
            i18n.set_language(lang)
            for lite in (False, True):
                shown = chr(10).join([banner.line(lite, 8765, "actions_monitor.json", i18n.t, "http://127.0.0.1:8765/"), i18n.about_line(), i18n.t("mon.started", url="http://127.0.0.1:8765/")])
                self.assertEqual(shown.count(TOOL_VERSION), 1, (lang, lite, shown))
        i18n.set_language("en")


if __name__ == "__main__":
    unittest.main()
