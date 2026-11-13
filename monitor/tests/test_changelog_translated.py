# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The history of changes is translated, entry by entry, in the seven other languages: no long line of a translation is the English line of the source, whatever the version."""
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


class Translated(unittest.TestCase):
    def test_no_entry_of_any_version_stays_in_english_in_a_translation(self):
        source = (HERE / "CHANGELOG.md").read_text(encoding="utf-8").replace("\r\n", "\n")
        english = {line for line in source.split("\n") if line.startswith("- ") and re.search(r"[a-z]{4,} [a-z]{3,} [a-z]{3,}", line)}      # a bullet with English words in it
        for tail in ("spa", "deu", "fra", "ita", "jpn", "zho", "por"):
            path = HERE / "docs" / f"CHANGELOG_{tail}.md"
            if not path.is_file():
                self.skipTest("the translations travel with the docs folder")
            text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
            same = [line[:70] for line in text.split("\n") if line in english]
            self.assertEqual(same, [], tail)
            self.assertEqual(re.findall(r"^## \[(\d+\.\d+\.\d+)\]", text, re.M)[-1], "1.0.0", tail)


if __name__ == "__main__":
    unittest.main()
