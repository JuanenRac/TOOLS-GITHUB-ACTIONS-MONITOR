# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`--format text|table|plain|json|ndjson`: ndjson is one valid JSON object per line, a table has no colour and fits the width (wide characters count as two cells), plain is separable by tabs, and
--json and the default text output of the commands that already existed are exactly what they were."""
import json
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
from github_actions_monitor.cli import formats  # noqa: E402

ALERTS = {"alerts": [{"sentinel": "ci", "level": "error", "code": "ci.red", "repo": "a/x", "title": "Red workflow"},
                     {"sentinel": "collab", "level": "warning", "code": "collab.pr", "repo": "a/y", "title": "Tab\tand\nline", "muted_until": "2030-01-01"},
                     {"sentinel": "ci", "level": "info", "code": "ci.slow", "repo": "b/日本語の名前", "title": "長いタイトル" * 6}]}


class Formats(unittest.TestCase):
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

    def ask(self, *argv):
        return base.run(*argv, "--url", self.url, "--lang", "en")

    def test_ndjson_is_one_valid_object_per_line(self):
        code, out, _ = self.ask("alerts", "--format", "ndjson")
        lines = out.splitlines()
        self.assertEqual((code, len(lines)), (0, 3), out)
        rows = [json.loads(line) for line in lines]
        self.assertEqual([r["code"] for r in rows], ["ci.red", "collab.pr", "ci.slow"])
        self.assertEqual(rows[1]["title"], "Tab\tand\nline")      # a line break inside a text is escaped: it never splits a record

    def test_ndjson_of_a_command_with_one_answer_is_one_line(self):
        base.ANSWERS["/api/health"] = {"version": "9.9.9", "uptime_seconds": 5, "account": "alpha"}
        base.ANSWERS["/api/data"] = {"data": {"repos": [], "figures": {"red": 0}, "rate": {"remaining": 4000, "limit": 5000}, "updated": "2026-01-01T00:00:00Z"}}
        code, out, _ = self.ask("status", "--format", "ndjson")
        self.assertEqual(len(out.splitlines()), 1, out)
        record = json.loads(out)
        self.assertEqual((record["version"], record["allowance_remaining"]), ("9.9.9", 4000))

    def test_plain_is_tab_separated_without_header(self):
        code, out, _ = self.ask("alerts", "--format", "plain")
        first = out.splitlines()[0].split("\t")
        self.assertEqual((code, first[:4]), (0, ["ci", "error", "ci.red", "a/x"]))
        self.assertEqual(len(out.splitlines()), 3)
        self.assertEqual({len(line.split("\t")) for line in out.splitlines()}, {6})

    def test_table_has_a_header_no_colour_and_fits_the_width(self):
        code, out, _ = self.ask("alerts", "--format", "table")
        self.assertEqual(code, 0)
        self.assertNotIn("\x1b", out)
        self.assertTrue(out.splitlines()[0].startswith("sentinel"))
        limit = formats.terminal_width()
        for line in out.splitlines():
            self.assertLessEqual(formats.width_of(line), limit, line)

    def test_wide_characters_count_as_two_cells_and_a_cut_ends_in_an_ellipsis(self):
        self.assertEqual(formats.width_of("日本"), 4)
        cut = formats.clip("日本語の名前", 7)
        self.assertLessEqual(formats.width_of(cut), 7)
        self.assertTrue(cut.endswith("…"))
        rendered = formats.table(["a", "b"], [{"a": "x" * 60, "b": "日本語" * 30}], width=50)
        for line in rendered.splitlines():
            self.assertLessEqual(formats.width_of(line), 50, line)

    def test_json_and_dash_dash_json_are_the_same_document(self):
        _, a, _ = self.ask("alerts", "--json")
        _, b, _ = self.ask("alerts", "--format", "json")
        self.assertEqual(a, b)
        self.assertEqual(json.loads(a)["data"]["alerts"][0]["code"], "ci.red")

    def test_the_default_text_is_what_it_was(self):
        code, out, _ = self.ask("alerts")
        self.assertEqual(code, 0)
        self.assertIn("[ERR ] ci", out)
        self.assertIn("2030-01-01)", out)

    def test_json_document_is_byte_for_byte_the_old_one(self):
        _, out, _ = self.ask("alerts", "--json")
        expected = json.dumps({"ok": True, "exit": 0, "data": ALERTS}, ensure_ascii=False, indent=1) + "\n"
        self.assertEqual(out, expected)

    def test_an_empty_list_prints_nothing_in_ndjson_and_the_text_in_table(self):
        base.ANSWERS["/api/alerts"] = {"alerts": []}
        _, nd, _ = self.ask("alerts", "--format", "ndjson")
        self.assertEqual(nd.strip(), "")
        _, tb, _ = self.ask("alerts", "--format", "table")
        self.assertIn("0", tb)

    def test_an_error_in_ndjson_is_one_json_line_and_the_same_code(self):
        code, out, _ = base.run("alerts", "--format", "ndjson", "--url", "http://127.0.0.1:1", "--lang", "en")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out)["exit"], 2)

    def test_the_configured_default_format_is_used_only_when_none_is_asked(self):
        self.assertEqual(formats.choose("", False, "ndjson"), "ndjson")
        self.assertEqual(formats.choose("table", True, "ndjson"), "table")
        self.assertEqual(formats.choose("", True, "ndjson"), "json")
        self.assertEqual(formats.choose("", False, None), "text")
        self.assertEqual(formats.configured_format({"cli": {"default_format": "bogus"}}), "text")
        self.assertEqual(formats.configured_format({"cli": {"default_format": "plain"}}), "plain")

    def test_every_existing_command_still_takes_each_format(self):
        base.ANSWERS.update({"/api/accounts": {"accounts": [{"id": "alpha", "state": "ok", "repos": 3}]}, "/api/live-events": {"events": [{"at": "t", "repo": "a/x", "name": "ci"}]},
                             "/api/live-status": {"enabled": True}})
        for command in ("accounts", "live", "alerts"):
            for fmt in ("text", "table", "plain", "json", "ndjson"):
                code, out, err = self.ask(command, "--format", fmt)
                self.assertEqual(code, 0, (command, fmt, err))
                self.assertTrue(out.strip() or fmt == "ndjson", (command, fmt))


if __name__ == "__main__":
    unittest.main()
