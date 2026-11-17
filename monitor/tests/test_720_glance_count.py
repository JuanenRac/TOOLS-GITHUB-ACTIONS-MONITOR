# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The number of tests in the README is the number of `test*` methods of every class of the test files (the glance counted only the classes whose base is called TestCase, and left out the ones that
inherit from a base of their own: 2912 in the README against 3314 methods). The run prints a higher number still because each subclass runs the methods it inherits."""
import ast
import sys
import unittest
from pathlib import Path

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent.parent / "tools"


def every_test_method():
    total = 0
    for path in sorted(HERE.glob("test_*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            if isinstance(node, ast.ClassDef):
                total += sum(1 for f in node.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name.startswith("test"))
    return total


class TheCountOfTheReadme(unittest.TestCase):
    def test_the_glance_counts_the_classes_with_a_base_of_their_own_too(self):
        if not (TOOLS / "make_glance.py").is_file():
            self.skipTest("the tools of the repository do not travel in the zip")
        sys.path.insert(0, str(TOOLS))
        try:
            import make_glance
            counted = make_glance.facts()["tests"]
        finally:
            sys.path.remove(str(TOOLS))
        self.assertEqual(counted, every_test_method())
        only_testcase = 0
        for path in sorted(HERE.glob("test_*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
                if isinstance(node, ast.ClassDef) and any((isinstance(b, ast.Attribute) and b.attr == "TestCase") or (isinstance(b, ast.Name) and b.id.endswith("TestCase")) for b in node.bases):
                    only_testcase += sum(1 for f in node.body if isinstance(f, ast.FunctionDef) and f.name.startswith("test"))
        self.assertGreater(counted, only_testcase, "the old way of counting left classes out")


if __name__ == "__main__":
    unittest.main()
