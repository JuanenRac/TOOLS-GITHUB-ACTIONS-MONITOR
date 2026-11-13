# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The author and the licence are shown in the web panel (footer) and by the command line tools (--version and the start-up line), in the 8 languages."""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.tool_version import AUTHOR, LICENSE_ID  # noqa: E402


class Authorship(unittest.TestCase):
    def test_the_line_names_the_author_and_the_licence_in_every_language(self):
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                line = i18n.about_line()
            self.assertIn(AUTHOR, line, lang)
            self.assertIn(LICENSE_ID, line, lang)
            self.assertNotIn("{", line, lang)

    def test_the_page_carries_author_and_licence_in_the_about_panel_and_has_no_authorship_footer(self):
        page = actions_monitor.render_page()
        self.assertIn('id="about-dlg"', page)           # since 1.7.4 the line of authorship at the foot is gone: the bar there is the status bar and About has it
        self.assertNotIn('<footer id="about"', page)
        self.assertIn(f'"author": "{AUTHOR}"', page)
        self.assertIn(f'"license": "{LICENSE_ID}"', page)
        self.assertIn('"ui.about"', page)

    def test_version_flag_of_the_reader_prints_the_author(self):
        from github_actions_monitor.cli import read_report
        old = sys.argv
        sys.argv = ["read_report.py", "--version"]
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                read_report.main()
        finally:
            sys.argv = old
        self.assertIn(AUTHOR, buf.getvalue())

    def test_the_batch_tool_has_a_version_flag_with_the_author(self):
        text = (HERE / "src" / "github_actions_monitor" / "cli" / "gha_dispatch_all.py").read_text(encoding="utf-8")
        self.assertIn('action="version"', text)
        self.assertIn("i18n.about_line()", text)

    def test_the_start_up_line_prints_the_author(self):
        text = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn("i18n.about_line()", text)


if __name__ == "__main__":
    unittest.main()
