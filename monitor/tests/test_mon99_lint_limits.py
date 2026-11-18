# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The workflow linter (and with it the sentinels of the supply chain and of the delivery) under a hostile file: an endless line, a million lines, anchors and aliases that would expand in a YAML parser, a huge
file on the disk. The linter reads text and never parses YAML, so nothing expands; the limits keep the time and the memory small and the findings of the normal part of the file intact."""
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.cli import lint_workflows as lw  # noqa: E402

GOOD = "name: x\non: push\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n"


class Limits(unittest.TestCase):
    def test_a_normal_file_is_read_as_before(self):
        found = lw.lint_text(GOOD, "w.yml")
        self.assertTrue(any(f["rule"] == "unpinned_uses" for f in found))

    def test_an_endless_line_is_cut(self):
        text = GOOD + "      - uses: " + "a" * 5_000_000 + "@v1\n"
        start = time.monotonic()
        found = lw.lint_text(text, "w.yml")
        self.assertLess(time.monotonic() - start, 5)
        self.assertTrue(all(len(str(f.get("detail") or "")) <= lw.MAX_LINE for f in found))

    def test_a_million_lines_are_cut(self):
        text = GOOD + "x: 1\n" * 1_000_000
        start = time.monotonic()
        lw.lint_text(text, "w.yml")
        self.assertLess(time.monotonic() - start, 10)
        self.assertLessEqual(len(lw.bounded(text)), lw.MAX_LINES)

    def test_anchors_and_aliases_are_plain_text(self):
        bomb = "a: &a [x,x,x,x,x,x,x,x,x]\n" + "".join(f"{chr(98 + i)}: &{chr(98 + i)} [*{chr(97 + i)},*{chr(97 + i)},*{chr(97 + i)}]\n" for i in range(20))
        start = time.monotonic()
        found = lw.lint_text(GOOD + bomb, "w.yml")
        self.assertLess(time.monotonic() - start, 2)
        self.assertTrue(any(f["rule"] == "unpinned_uses" for f in found))

    def test_a_huge_file_on_the_disk_is_read_only_up_to_the_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / ".github" / "workflows"
            folder.mkdir(parents=True)
            (folder / "big.yml").write_text(GOOD + "# " + "z" * (lw.MAX_TEXT * 2) + "\n", encoding="utf-8")
            start = time.monotonic()
            found = lw.lint_path(tmp)
            self.assertLess(time.monotonic() - start, 5)
            self.assertTrue(any(f["rule"] == "unpinned_uses" for f in found))

    def test_the_limits_are_sane(self):
        self.assertGreaterEqual(lw.MAX_TEXT, 262144)
        self.assertGreaterEqual(lw.MAX_LINE, 1000)


if __name__ == "__main__":
    unittest.main()
