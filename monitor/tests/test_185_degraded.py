# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A failure that the monitor swallows on purpose leaves a line in its log: the kind of error, where it happened and a cleaned message, never a token."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import degraded  # noqa: E402

TOKEN = "ghp_" + "A1b2C3d4E5" * 3


def fails():
    raise KeyError("rate " + TOKEN)


class Lines(unittest.TestCase):
    def setUp(self):
        degraded.reset()
        self.lines = []
        degraded.set_writer(self.lines.append)
        self.addCleanup(degraded.set_writer, None)
        self.addCleanup(degraded.reset)

    def caught(self):
        try:
            fails()
        except KeyError as error:
            return error

    def test_the_line_says_what_failed_where_and_with_which_text(self):
        degraded.note("ai_alerts.panels", self.caught())
        self.assertEqual(len(self.lines), 1)
        line = self.lines[0]
        self.assertIn("origin=ai_alerts.panels", line)
        self.assertIn("kind=KeyError", line)
        self.assertIn("test_185_degraded.py", line)
        self.assertIn("in fails", line)
        self.assertNotIn(TOKEN, line)
        self.assertIn("***", line)

    def test_the_recent_list_keeps_the_place_too(self):
        degraded.note("loop.extra", self.caught())
        self.assertIn("in fails", degraded.snapshot()["recent"][0]["where"])

    def test_a_failure_that_repeats_does_not_fill_the_log(self):
        error = self.caught()
        for _ in range(degraded.LINE_FULL + degraded.LINE_EVERY * 2):
            degraded.note("loop.extra", error)
        self.assertEqual(len(self.lines), degraded.LINE_FULL + 2)
        self.assertEqual(degraded.snapshot()["origins"]["loop.extra"], degraded.LINE_FULL + degraded.LINE_EVERY * 2, "the counter counts all of them")

    def test_a_text_without_an_exception_and_a_writer_that_breaks_are_harmless(self):
        degraded.note("loop.extra", "just a note")
        self.assertIn("kind=just a note", self.lines[0])
        degraded.set_writer(mock.Mock(side_effect=OSError("disk full")))
        degraded.note("loop.extra", self.caught())
        self.assertEqual(degraded.snapshot()["origins"]["loop.extra"], 2)


class InTheLogFile(unittest.TestCase):
    def test_the_monitor_appends_the_line_to_its_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "actions_monitor_log.txt"
            with mock.patch.object(am, "LOG_FILE", log):
                am.degraded_line("degraded origin=x kind=KeyError where=a.py:1 in f text=boom count=1")
                am.degraded_line("degraded origin=y kind=OSError where=- text=- count=1")
            lines = log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].endswith("text=boom count=1"))
        self.assertRegex(lines[0], r"^\d{4}-\d\d-\d\d ")

    def test_a_log_that_cannot_be_written_is_not_one_more_failure(self):
        with mock.patch.object(am, "LOG_FILE", Path("/nonexistent-folder/definitely/not/here.txt")):
            am.degraded_line("degraded origin=x")
