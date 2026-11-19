# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A path that does not exist, or a workflow file that cannot be read, is never a clean bill of health: the checker says so, checks the rest and exits with 2."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.cli import lint_workflows as lw

CLEAN = "name: x\non: push\npermissions: {}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n"


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = lw.main(argv)
    return code, out.getvalue(), err.getvalue()


class NotThereIsNotClean(unittest.TestCase):
    def test_a_path_that_does_not_exist_exits_with_two_and_says_so(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            code, out, err = run([str(Path(tmp) / "nowhere")])
            self.assertEqual(code, lw.EXIT_NOT_READ)
            self.assertIn("nowhere", err)
            self.assertIn("0 finding", out)

    def test_a_path_that_does_not_exist_next_to_a_good_one_still_exits_with_two(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            good = Path(tmp) / "ok.yml"
            good.write_text(CLEAN, encoding="utf-8")
            code, _, err = run([str(good), str(Path(tmp) / "nowhere")])
            self.assertEqual(code, 2)
            self.assertIn("nowhere", err)

    def test_a_readable_folder_without_findings_is_clean(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            (Path(tmp) / "ok.yml").write_text(CLEAN, encoding="utf-8")
            code, _, err = run([tmp])
            self.assertEqual((code, err), (0, ""))

    def test_a_finding_that_reaches_the_limit_still_exits_with_one(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            (Path(tmp) / "bad.yml").write_text("on: push\njobs:\n  a:\n    runs-on: x\n    steps:\n      - run: echo ghp_" + "a" * 36 + "\n", encoding="utf-8")
            code, _, _ = run([tmp])
            self.assertEqual(code, 1)


class OneBadFileDoesNotStopTheOthers(unittest.TestCase):
    def test_an_unreadable_file_is_named_the_others_are_checked_and_it_is_not_clean(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            folder = Path(tmp) / ".github" / "workflows"
            folder.mkdir(parents=True)
            (folder / "a.yml").write_text(CLEAN, encoding="utf-8")
            (folder / "b.yml").write_text("on: push\njobs:\n  a:\n    runs-on: x\n    steps:\n      - run: echo ghp_" + "b" * 36 + "\n", encoding="utf-8")
            real_open = open

            def picky(file, *args, **kwargs):
                if str(file).endswith("a.yml"):
                    raise PermissionError("denied")
                return real_open(file, *args, **kwargs)

            with mock.patch("builtins.open", picky):
                found, problems = lw.lint_path_status(tmp)
            self.assertTrue(any(f["file"] == "b.yml" for f in found))
            self.assertEqual([(Path(name).name, reason) for name, reason in problems], [("a.yml", "PermissionError")])

    def test_the_json_output_is_still_a_list_of_findings(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            code, out, _ = run(["--json", str(Path(tmp) / "nowhere")])
            self.assertEqual((code, json.loads(out)), (2, []))


class Texts(unittest.TestCase):
    def test_the_message_exists_in_every_language_with_its_placeholders(self):
        root = Path(__file__).resolve().parents[1] / "assets" / "locales"
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            text = json.loads((root / f"{lang}.json").read_text(encoding="utf-8"))["lint.path_unread"]
            self.assertIn("{name}", text, lang)
            self.assertIn("{reason}", text, lang)


if __name__ == "__main__":
    unittest.main()
