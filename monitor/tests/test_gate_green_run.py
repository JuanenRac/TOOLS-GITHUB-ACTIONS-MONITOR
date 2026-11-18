# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The release gate names the tests that fail and keeps the whole output, and it may accept a complete green run of the very commit instead of repeating the suite."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import make_release  # noqa: E402

REPORT = """..F.E
======================================================================
FAIL: test_one (test_a.Alpha.test_one)
----------------------------------------------------------------------
Traceback (most recent call last):
AssertionError: 1 != 2
======================================================================
ERROR: test_two (test_b.Beta.test_two)
----------------------------------------------------------------------
Ran 5 tests in 1.0s

FAILED (failures=1, errors=1)
"""
SHA = "6dbc07c9f3f804694bdca9d61e3d49098ca5aa24"


def record(**changes):
    base = {"total": 10, "done": 10, "ok": 9, "skipped": 1, "fail": 0, "error": 0, "finished": True, "exit_code": 0, "sha": SHA}
    base.update(changes)
    return base


class NamesAndLog(unittest.TestCase):
    def test_the_failing_tests_are_read_from_the_report(self):
        self.assertEqual(make_release.failing_tests(REPORT), ["test_a.Alpha.test_one", "test_b.Beta.test_two"])
        self.assertEqual(make_release.failing_tests("OK\n"), [])

    def test_the_message_names_them_and_the_whole_output_is_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.CompletedProcess([], 1, stdout="out line\n", stderr=REPORT + "x" * 4000)
            text = make_release.suite_failure("suite", result, env={"MONITOR_RELEASE_LOG_DIR": folder})
            self.assertIn("test_a.Alpha.test_one; test_b.Beta.test_two", text)
            saved = Path(folder) / "make_release_suite.log"
            self.assertIn(str(saved), text)
            self.assertIn("AssertionError: 1 != 2", saved.read_text(encoding="utf-8"))

    def test_an_output_without_names_says_so_instead_of_guessing(self):
        with tempfile.TemporaryDirectory() as folder:
            text = make_release.suite_failure("clean", subprocess.CompletedProcess([], 1, stdout="", stderr="boom"), env={"MONITOR_RELEASE_LOG_DIR": folder})
            self.assertIn("no failing test is named", text)


class SuiteProgress(unittest.TestCase):
    def suite(self, folder, count):
        (Path(folder) / "tests").mkdir()
        body = "import unittest" + chr(10) + "class T(unittest.TestCase):" + chr(10) + "".join(f"    def test_{i}(self):" + chr(10) + "        pass" + chr(10) for i in range(count))
        (Path(folder) / "tests" / "test_many.py").write_text(body, encoding="utf-8")
        return [sys.executable, "-I", "-m", "unittest", "discover", "-s", "tests"]

    def test_without_progress_it_is_a_plain_run(self):
        with tempfile.TemporaryDirectory() as folder:
            result = make_release.run_suite("x", self.suite(folder, 3), folder, dict(), 120)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Ran 3 tests", result.stderr)

    def test_with_progress_a_line_says_how_far_it_is_and_the_result_is_the_same(self):
        import contextlib
        import io
        old = (make_release.SHOW_PROGRESS, make_release.PROGRESS_EVERY)
        make_release.SHOW_PROGRESS, make_release.PROGRESS_EVERY = True, 2
        self.addCleanup(lambda: setattr(make_release, "SHOW_PROGRESS", old[0]) or setattr(make_release, "PROGRESS_EVERY", old[1]))
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()) as shown:
            result = make_release.run_suite("suite", self.suite(folder, 5), folder, dict(), 120)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Ran 5 tests", result.stderr)
        self.assertIn("gate: suite: 2 tests run", shown.getvalue())
        self.assertIn("gate: suite: 4 tests run", shown.getvalue())

    def test_the_flag_is_in_the_help(self):
        result = subprocess.run([sys.executable, "-I", str(HERE / "tools" / "make_release.py"), "--help"], capture_output=True, text=True, timeout=120)
        self.assertIn("--progress", result.stdout)


class AcceptedGreenRun(unittest.TestCase):
    def write(self, data):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "run.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def refused(self, data, commit=SHA):
        with self.assertRaises(make_release.GateError):
            make_release.green_run(self.write(data), commit)

    def test_a_complete_clean_run_of_the_same_commit_is_accepted(self):
        text = make_release.green_run(self.write(record()), SHA)
        self.assertIn("9 ok", text)
        self.assertIn(SHA[:12], text)
        self.assertIn("accepted", make_release.green_run(self.write(record()), SHA[:9]))

    def test_another_commit_is_refused(self):
        self.refused(record(sha="aaaaaaaaaaaa" + SHA[12:]))
        self.refused(record(sha=""))
        self.refused(record(), commit="")
        self.refused(record(), commit="abc")

    def test_an_unfinished_or_dirty_run_is_refused(self):
        for change in ({"finished": False}, {"exit_code": 1}, {"fail": 1}, {"error": 2}, {"total": 0}, {"done": 9}):
            self.refused(record(**change))

    def test_the_count_unittest_gave_wins_over_the_lines_that_were_read(self):
        text = make_release.green_run(self.write(record(total=10, done=7, ran=10)), SHA)
        self.assertIn("of 10", text)
        self.refused(record(total=10, done=10, ran=9))
        self.refused(record(total=10, done=10, ran=0, finished=False))
        self.assertIn("accepted", make_release.green_run(self.write(record(total=10, done=10, ran=0)), SHA))

    def test_a_file_that_is_not_a_record_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / "bad.json"
            bad.write_text("not json", encoding="utf-8")
            with self.assertRaises(make_release.GateError):
                make_release.green_run(str(bad), SHA)
            with self.assertRaises(make_release.GateError):
                make_release.green_run(str(Path(folder) / "missing.json"), SHA)

    def test_skipping_the_suite_of_the_zip_needs_an_accepted_run(self):
        result = subprocess.run([sys.executable, "-I", str(HERE / "tools" / "make_release.py"), "--skip-clean-suite"], capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--accept-green-suite", result.stderr)


if __name__ == "__main__":
    unittest.main()
