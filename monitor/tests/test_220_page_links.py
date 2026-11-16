# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Every link of the page that is built from data goes through the URL filter, so a value that is not an https address of the host never becomes a clickable javascript: link."""
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401

PAGE = (Path(__file__).resolve().parent.parent / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")


class PageLinks(unittest.TestCase):
    def test_interpolated_hrefs_are_filtered(self):
        bad = []
        for m in re.finditer(r'href="\$\{([^"]*)\}', PAGE):
            expr = m.group(1)
            if "safeUrl(" in expr or expr.startswith("GH}") or (expr == "esc(url(a))" and "const url=a=>safeUrl(" in PAGE):
                continue
            bad.append(expr)
        self.assertEqual(bad, [], "href built from data without the URL filter")

    def test_filter_accepts_the_configured_host(self):
        self.assertIn("u.startsWith(GH)", PAGE)


if __name__ == "__main__":
    unittest.main()
