# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The guides have the same structure in the eight languages: the same headings (by level and number), the same fenced blocks of code (the commands are not translated), so a section, a warning box or a step cannot exist in one language and be missing in another."""
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DOCS = HERE / "docs"
TAILS = ("spa", "deu", "fra", "ita", "jpn", "zho", "por")
SKIP = {"CHANGELOG", "help_index"}      # the history and the index have their own checks


def facts(text):
    text = text.replace("\r\n", "\n")
    body = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    fenced = re.findall(r"^```", body, re.M)
    plain = re.sub(r"```.*?```", "", body, flags=re.S)
    return {
        "headings": [len(m) for m in re.findall(r"^(#{1,6})\s", plain, re.M)],
        "fences": len(fenced),
    }


class Parity(unittest.TestCase):
    def test_every_guide_has_the_same_structure_in_the_eight_languages(self):
        problems = []
        for source in sorted(DOCS.glob("*.md")):
            name = source.stem
            if "_" in name and name.rsplit("_", 1)[1] in TAILS or name.split("_")[0] in SKIP:
                continue
            base = facts(source.read_text(encoding="utf-8"))
            for tail in TAILS:
                other = DOCS / f"{name}_{tail}.md"
                if not other.is_file():
                    continue
                got = facts(other.read_text(encoding="utf-8"))
                for key in base:
                    if got[key] != base[key]:
                        problems.append(f"{other.name}: {key}")
        self.assertEqual(problems, [], "\n".join(problems[:40]))


if __name__ == "__main__":
    unittest.main()
