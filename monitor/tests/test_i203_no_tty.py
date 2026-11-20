# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A clean output without a terminal: NO_COLOR and a missing terminal give no escape sequence, the width is COLUMNS or 80, `--color` decides, text that came from GitHub is cleaned of escape
sequences, and a reader that closes early ends the command without a traceback."""
import io
import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_190_cli as base  # noqa: E402
from github_actions_monitor.cli import terminal  # noqa: E402

ALERTS = {"alerts": [{"sentinel": "ci", "level": "error", "code": "ci.red", "repo": "a/x", "title": "\x1b[31mRed\x1b[0m workflow \x1b]0;pwned\x07here\x07\x00"}]}


class Tty(io.StringIO):
    def isatty(self):
        return True


class Terminal(unittest.TestCase):
    def test_colour_follows_the_mode_then_no_color_then_the_terminal(self):
        tty, pipe = Tty(), io.StringIO()
        self.assertTrue(terminal.use_color("auto", tty, {}))
        self.assertFalse(terminal.use_color("auto", pipe, {}))
        self.assertFalse(terminal.use_color("auto", tty, {"NO_COLOR": "1"}))
        self.assertFalse(terminal.use_color("auto", tty, {"TERM": "dumb"}))
        self.assertTrue(terminal.use_color("auto", tty, {"NO_COLOR": ""}))      # an empty NO_COLOR does not count (the convention)
        self.assertTrue(terminal.use_color("always", pipe, {"NO_COLOR": "1"}))
        self.assertFalse(terminal.use_color("never", tty, {}))
        self.assertFalse(terminal.use_color("nonsense", pipe, {}))      # an unknown mode is auto

    def test_the_width_without_a_terminal_is_columns_or_80(self):
        pipe = io.StringIO()
        self.assertEqual(terminal.width(pipe, {}), 80)
        self.assertEqual(terminal.width(pipe, {"COLUMNS": "132"}), 132)
        self.assertEqual(terminal.width(pipe, {"COLUMNS": "abc"}), 80)
        self.assertEqual(terminal.width(pipe, {"COLUMNS": "5"}), 80)

    def test_clean_removes_escape_sequences_and_control_characters_but_keeps_tab_and_line_break(self):
        self.assertEqual(terminal.clean("\x1b[31mred\x1b[0m\ttab\nline\x00\x07 \x1b]0;title\x07end"), "red\ttab\nline end")
        self.assertIn("\x1b[1m", terminal.bold("x", True))
        self.assertEqual(terminal.bold("x", False), "x")

    def test_a_reader_that_closes_early_is_not_an_error(self):
        class Gone:
            def write(self, text):
                raise BrokenPipeError

            def flush(self):
                pass

        self.assertFalse(terminal.emit("x", Gone()))
        out = io.StringIO()
        self.assertTrue(terminal.emit("x", out))
        self.assertEqual(out.getvalue(), "x\n")

    def test_head_closing_the_pipe_gives_no_traceback(self):
        code = ("import sys; sys.path.insert(0, %r)\nfrom github_actions_monitor.cli import terminal\n"
                "for i in range(20000):\n    if not terminal.emit('line %%d' %% i):\n        break\nsys.exit(0)\n") % str(HERE / "src")
        proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.stdout.read(10)
        proc.stdout.close()
        _, err = proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, 0, err)
        self.assertNotIn(b"Traceback", err)


class Command(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), base.Fake)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        base.ANSWERS.clear()
        base.SEEN.clear()
        base.ANSWERS["/api/alerts"] = ALERTS
        self._old = os.environ.pop("NO_COLOR", None)

    def tearDown(self):
        os.environ.pop("NO_COLOR", None)
        if self._old is not None:
            os.environ["NO_COLOR"] = self._old

    def ask(self, *argv):
        return base.run(*argv, "--url", self.url, "--lang", "en")

    def test_redirected_output_has_no_escape_sequence_in_any_text_format(self):
        for fmt in ("text", "table", "plain"):
            code, out, _ = self.ask("alerts", "--format", fmt)
            self.assertEqual(code, 0, fmt)
            self.assertNotIn("\x1b", out, fmt)
            self.assertNotIn("\x00", out, fmt)
            self.assertNotIn("pwned", out, fmt)
            self.assertIn("Red workflow", out, fmt)
        code, out, _ = self.ask("alerts", "--format", "table", "--color", "never")
        self.assertNotIn("\x1b", out)

    def test_json_stays_what_it_was(self):
        code, out, _ = self.ask("alerts", "--json")
        self.assertEqual(json.loads(out)["data"]["alerts"][0]["code"], "ci.red")

    def test_colour_is_written_only_when_asked_for_and_only_in_the_header(self):
        code, out, _ = self.ask("alerts", "--format", "table", "--color", "always")
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("\x1b[1m"), lines[0])
        self.assertNotIn("\x1b", "\n".join(lines[1:]))

    def test_the_option_is_in_the_help_and_the_completions(self):
        from github_actions_monitor.cli import monitor_cli
        text = monitor_cli.build_parser().format_help()
        self.assertIn("--color", text)


if __name__ == "__main__":
    unittest.main()
