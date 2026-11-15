# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The badge with the number of tests at the top of the README and its seven translations: the dashboard of the profile reads `Tests-<number>` there, and the number is the measured count that the table
of the same README gives, kept by tools/make_glance.py (the check of the counts of the CI fails when one goes out of date)."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE / "src"))
try:
    import make_glance
except ImportError:      # the tools folder does not travel in the zip of a release
    make_glance = None

SUFFIXES = ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por")


@unittest.skipUnless(make_glance is not None and (ROOT / "README.md").is_file(), "the repository is not here (the zip of a release has no README at the top)")
class TheTestsBadge(unittest.TestCase):
    def test_every_readme_has_the_badge_with_the_measured_count(self):
        count = make_glance.facts()["tests"]
        for tail in SUFFIXES:
            text = (ROOT / f"README{tail}.md").read_text(encoding="utf-8")
            found = re.findall(r"Tests-([\d,.]+)", text)
            self.assertEqual(found, [str(count)], tail)

    def test_the_generator_adds_a_missing_badge_and_updates_an_old_one(self):
        facts = {"tests": 1234}
        bare = '  <img src="https://img.shields.io/badge/Languages-8-FFB300.svg" alt="8 languages">\n  <p>x</p>\n'
        once = make_glance.with_badge(bare, facts)
        self.assertIn("Tests-1234_passing", once)
        self.assertEqual(once.count("Tests-"), 1)
        self.assertEqual(make_glance.with_badge(once, {"tests": 99}).count("Tests-99_passing"), 1)
        self.assertEqual(make_glance.with_badge(once, facts), once, "a second pass changes nothing")


if __name__ == "__main__":
    unittest.main()
