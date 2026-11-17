# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`/favicon.ico` was the only 404 of the page and of the wall screens (a kiosk asks for it at every start): it answers 204 in both editions."""
import unittest

import _testenv  # noqa: F401
from test_200_contract import Served


class Favicon(unittest.TestCase):
    def test_it_answers_no_content_in_both_editions(self):
        for lite in (False, True):
            with self.subTest(lite=lite):
                served = Served(self, lite=lite)
                status, body, answer = served.raw("GET", "/favicon.ico")
                self.assertEqual((status, body), (204, b""))
                self.assertIn("max-age", answer.getheader("Cache-Control") or "")


if __name__ == "__main__":
    unittest.main()
