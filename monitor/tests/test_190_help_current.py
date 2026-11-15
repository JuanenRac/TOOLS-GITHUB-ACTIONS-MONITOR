# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The help is current with every version: the version of the README of the repository (At a glance) and of its seven translations is the one of tool_version.py, the headings of the READMEs of the
package say it too, no topic of the help talks about another version as if it were the current one, every guide of monitor/docs is listed in the README (in the eight languages), and the
gate of make_release.py refuses a release whose help is behind. Files that do not travel in the zip of a release are skipped."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import tool_version  # noqa: E402

TOOLS = HERE / "tools"
sys.path.insert(0, str(TOOLS))
import make_release as mr  # noqa: E402

TAILS = ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho")
READMES = [ROOT / f"README{t}.md" for t in TAILS]
HAS_REPO = all(p.is_file() for p in READMES)
#: guides that are not topics of the README by design: the history, the plan and the package for the auditors
NOT_LISTED = {"CHANGELOG", "ROADMAP", "AUDIT_PACKAGE_INDEX"}


@unittest.skipUnless(HAS_REPO, "the README of the repository does not travel in the zip of a release")
class TheReadme(unittest.TestCase):
    def test_at_a_glance_says_the_version_of_the_tool_in_the_eight_languages(self):
        for path in READMES:
            found = mr.VERSION_CELL.search(path.read_text(encoding="utf-8"))
            self.assertIsNotNone(found, path.name)
            self.assertEqual(found.group(1), tool_version.TOOL_VERSION, path.name)

    def test_measured_today_says_it_too(self):
        for path in READMES:
            found = re.search(r"\(v(\d+\.\d+\.\d+)\)", path.read_text(encoding="utf-8"))
            self.assertIsNotNone(found, path.name)
            self.assertEqual(found.group(1), tool_version.TOOL_VERSION, path.name)

    def test_the_manifest_says_it(self):
        import json
        manifest = json.loads((ROOT / "electro-hobby-3d.project.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], tool_version.TOOL_VERSION)

    def test_every_guide_is_listed_in_the_readme_of_its_language(self):
        guides = sorted({re.sub(r"_(spa|deu|fra|ita|jpn|zho|por)$", "", p.stem) for p in (HERE / "docs").glob("*.md")} - NOT_LISTED)
        for tail, path in zip(TAILS, READMES):
            text = path.read_text(encoding="utf-8")
            missing = [g for g in guides if f"monitor/docs/{g}{tail}.md" not in text]
            self.assertEqual(missing, [], f"{path.name}: a guide of the help is not listed in the Documentation of the README: add it to the sources of the eight READMEs")

    def test_the_new_commands_and_features_are_in_the_what_it_does_of_every_language(self):
        for path in READMES:
            text = path.read_text(encoding="utf-8")
            for needle in ("monitor/docs/SCORE", "monitor/docs/DEPLOYMENT", "monitor/docs/STORAGE", "`score`"):
                self.assertIn(needle, text, (path.name, needle))

    def test_the_status_table_has_the_rows_of_1_8_and_1_9(self):
        for path in READMES:
            text = path.read_text(encoding="utf-8")
            self.assertGreaterEqual(text.count("| 🟡 |"), 6, path.name)

    def test_the_generator_writes_the_version_so_it_cannot_be_left_behind(self):
        generator = (ROOT / "tools" / "make_glance.py").read_text(encoding="utf-8")
        self.assertIn("def with_version(", generator)
        self.assertIn("with_version(with_badge(text, f), f)", generator)


class TheGate(unittest.TestCase):
    def test_the_help_of_this_version_has_no_problems(self):
        self.assertEqual(mr.help_version_problems(tool_version.TOOL_VERSION), [])

    @unittest.skipUnless(HAS_REPO, "the README of the repository does not travel in the zip of a release")
    def test_a_help_that_says_another_version_is_refused(self):
        problems = mr.help_version_problems("99.0.0")
        self.assertTrue(any("At a glance" in p for p in problems), problems)
        self.assertTrue(any("README.txt" in p or "README_en.txt" in p for p in problems), problems)

    def test_a_package_readme_that_says_the_previous_version_is_refused(self):
        self.assertTrue([p for p in mr.help_version_problems("99.0.0") if "heading" in p])

    def test_the_text_format_of_prometheus_is_not_taken_for_ours(self):
        self.assertIn("0.0.4", mr.HELP_VERSION_OTHER)

    def test_the_gate_calls_the_check(self):
        import inspect
        self.assertIn("help_version_problems(tool_version.TOOL_VERSION)", inspect.getsource(mr.gate_static))


@unittest.skipUnless(HAS_REPO, "CONTRIBUTING does not travel in the zip of a release")
class TheRule(unittest.TestCase):
    def test_every_version_reviews_the_whole_help_in_the_eight_languages(self):
        for tail in TAILS:
            text = (ROOT / f"CONTRIBUTING{tail}.md").read_text(encoding="utf-8")
            self.assertRegex(text, r"(?m)^8\. \*\*", tail)
            self.assertIn("test_190_help_current.py", text, tail)


if __name__ == "__main__":
    unittest.main()
