# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The guides on the command line (`docs list`, `docs show NAME`) and the `help` that every error of the command carries. Nothing here reaches GitHub or needs a running monitor."""
import contextlib
import io
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE.parent / "tools"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.cli import monitor_cli as cli  # noqa: E402


LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
LOCALES = {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}


def command(*args):
    """(exit code, standard output, standard error) of the command line."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(args))
    return code, out.getvalue(), err.getvalue()


class TheGuidesOnTheCommandLine(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("en")

    def test_list_names_every_guide_of_this_version_with_its_title(self):
        code, out, _ = command("docs", "list", "--json")
        answer = json.loads(out)["data"]
        self.assertEqual(code, 0)
        names = [row["name"] for row in answer["docs"]]
        self.assertEqual(answer["count"], len(names))
        for guide in ("CLI", "FIRST_STEPS", "ACCOUNTS", "HEALTH"):
            self.assertIn(guide, names)
        self.assertFalse([n for n in names if re.search(r"_(deu|fra|ita|jpn|por|spa|zho)$", n)], "the translated files are not guides of their own")
        self.assertTrue(all(row["title"] for row in answer["docs"]))
        self.assertEqual(names, sorted(names))

    def test_show_prints_a_guide_in_any_case_and_in_the_language_asked(self):
        code, out, _ = command("docs", "show", "cli", "--json")
        english = json.loads(out)["data"]
        self.assertEqual((code, english["name"], english["lang"]), (0, "CLI", "en"))
        self.assertIn("monitor_cli", english["text"])
        code, out, _ = command("docs", "show", "CLI", "--json", "--lang", "es")
        spanish = json.loads(out)["data"]
        self.assertEqual((code, spanish["lang"]), (0, "es"))
        self.assertNotEqual(spanish["text"], english["text"])

    def test_plain_show_writes_the_text_itself(self):
        code, out, _ = command("docs", "show", "FIRST_STEPS", "--format", "plain")
        self.assertEqual(code, 0)
        self.assertIn("# ", out)

    def test_a_name_that_does_not_exist_is_a_usage_error_that_points_to_the_list(self):
        for name in ("nope", "../../etc/passwd"):
            code, out, _ = command("docs", "show", name, "--json")
            answer = json.loads(out)
            self.assertEqual(code, 1, name)
            self.assertFalse(answer["ok"])
            self.assertIn("docs list", answer["help"])

    def test_show_without_a_name_is_a_usage_error(self):
        code, out, _ = command("docs", "show", "--json")
        self.assertEqual((code, json.loads(out)["exit"]), (1, 1))

    def test_every_error_of_the_command_carries_a_help_that_names_a_guide_that_exists(self):
        guides = {row["name"] for row in json.loads(command("docs", "list", "--json")[1])["data"]["docs"]}
        for code in (1, 2, 3, 4):
            error = cli.CliError(code, "x")
            self.assertTrue(error.help, code)
            for name in re.findall(r"docs show ([A-Z_]+)", error.help):
                self.assertIn(name, guides, (code, name))
        self.assertEqual(cli.CliError(1, "x", "mine").help, "mine")

    def test_the_json_error_of_a_command_has_the_help_field_and_the_text_error_a_line(self):
        code, out, _ = command("status", "--url", "http://127.0.0.1:1", "--json", "--timeout", "1")
        answer = json.loads(out)
        self.assertEqual(code, 2)
        self.assertIn("help", answer)
        self.assertIn("--url", answer["help"])
        _, _, err = command("status", "--url", "http://127.0.0.1:1", "--timeout", "1")
        self.assertIn("help:", err)

    def test_the_texts_exist_in_the_eight_languages(self):
        keys = ["cli.fix_%d" % n for n in (1, 2, 3, 4)] + ["cli.help_line", "cli.docs_action", "cli.docs_head", "cli.docs_name_needed", "cli.docs_unknown", "cli.docs_help_list", "cli.docs_unreadable"]
        for lang in LANGS:
            for key in keys:
                self.assertTrue(LOCALES[lang].get(key), (lang, key))
        for lang in LANGS:
            self.assertIn("{help}", LOCALES[lang]["cli.help_line"], lang)
            self.assertIn("{n}", LOCALES[lang]["cli.docs_head"], lang)
            self.assertIn("{name}", LOCALES[lang]["cli.docs_unknown"], lang)


if __name__ == "__main__":
    unittest.main()
