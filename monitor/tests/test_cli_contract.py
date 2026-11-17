# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The contract of the command line: the table of exit codes of the guides equals the code, the document of --json of the commands that existed is the one they always printed, every option and
command of the operator is in --help and in the guides of the eight languages, and the `jq` examples of the guide run (when jq is installed)."""
import io
import json
import re
import shlex
import shutil
import subprocess
import sys
import threading
import unittest
from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_190_cli as base  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.cli import monitor_cli  # noqa: E402

DOCS = HERE / "docs"
SUFFIXES = ("", "_spa", "_fra", "_ita", "_deu", "_jpn", "_zho", "_por")
HEALTH = {"version": "9.9.9", "uptime_seconds": 120, "account": "alpha", "lite": False}
DATA = {"data": {"repos": [{"full_name": "a/x"}], "figures": {"active": 1, "queued": 0, "fail24": 2, "ok24": 8, "red": 1}, "rate": {"remaining": 4000, "limit": 5000, "reset": 1},
                 "updated": "2026-01-01T00:00:00Z", "offline": {}}, "error": None}
ALERTS = {"alerts": [{"sentinel": "ci", "level": "critical", "code": "ci.red", "repo": "a/x", "title": "Red"}, {"sentinel": "collab", "level": "warning", "code": "collab.pr", "repo": "a/y", "title": "PR"}]}
TEAM = {"all": 2, "shown": 2, "totals": {"bad": 1, "warn": 1, "ok": 0, "unknown": 0}, "ranking": [{"repo": "a/x", "state": "bad", "risk": 55, "alerts": 1, "red_workflows": 1}, {"repo": "a/y", "state": "warn", "risk": 3, "alerts": 1, "red_workflows": 0}]}


def codes_of(path):
    return {int(m.group(1)) for m in re.finditer(r"^\| (\d) \|", path.read_text(encoding="utf-8"), re.M)}


class Table(unittest.TestCase):
    def test_the_guide_lists_exactly_the_exit_codes_of_the_code(self):
        in_code = {monitor_cli.EXIT_OK, monitor_cli.EXIT_USAGE, monitor_cli.EXIT_DOWN, monitor_cli.EXIT_AUTH, monitor_cli.EXIT_DEGRADED, monitor_cli.EXIT_ALERTS, monitor_cli.EXIT_CHANGED}
        self.assertEqual(in_code, set(range(7)))
        for suffix in SUFFIXES:
            self.assertEqual(codes_of(DOCS / f"CLI_OPERATOR{suffix}.md") & in_code, in_code, suffix)
            self.assertEqual(codes_of(DOCS / f"CLI{suffix}.md"), in_code, suffix)

    def test_six_is_only_for_watch_on_change(self):
        text = (HERE / "src" / "github_actions_monitor" / "cli" / "monitor_cli.py").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"EXIT_CHANGED", text)), 2)      # defined once, never returned by another command
        self.assertEqual(monitor_cli.EXIT_CHANGED, 6)
        for lang in i18n.LANGS:
            i18n.set_language(lang)
            self.assertIn("6", i18n.t("cli.epilog"), lang)
        i18n.set_language("en")


class Help(unittest.TestCase):
    OPTIONS = ("--format", "--interval", "--once", "--exit-on-change", "--no-clear")
    COMMANDS = ("watch", "completions", "kiosk")

    def test_every_new_option_and_command_is_in_help_and_in_the_guides_of_the_eight_languages(self):
        out = io.StringIO()
        with redirect_stdout(out):
            monitor_cli.main(["--help", "--lang", "en"])
        helptext = out.getvalue()
        for name in self.OPTIONS:
            self.assertIn(name, helptext, name)
        for suffix in SUFFIXES:
            guide = (DOCS / f"CLI_OPERATOR{suffix}.md").read_text(encoding="utf-8")
            for name in self.OPTIONS + self.COMMANDS:
                self.assertIn(name, guide, (suffix, name))
            index = (DOCS / f"CLI{suffix}.md").read_text(encoding="utf-8")
            for name in self.COMMANDS:
                self.assertIn(f"`{name}`", index, (suffix, name))

    def test_the_epilog_and_the_help_of_the_commands_say_the_new_ones(self):
        for lang in i18n.LANGS:
            i18n.set_language(lang)
            self.assertIn("watch", i18n.t("cli.help_command"), lang)
            self.assertIn("kiosk", i18n.t("cli.help_ai_action"), lang)
        i18n.set_language("en")


class Golden(unittest.TestCase):
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
        base.ANSWERS.update({"/api/health": HEALTH, "/api/data": DATA, "/api/alerts": ALERTS, "/api/team/health": TEAM})

    def ask(self, *argv):
        return base.run(*argv, "--url", self.url, "--lang", "en")

    def test_status_json_is_the_document_it_always_was(self):
        code, out, _ = self.ask("status", "--json")
        doc = json.loads(out)
        self.assertEqual((code, doc["ok"], doc["exit"]), (0, True, 0))
        self.assertEqual(sorted(doc["data"]), sorted(["version", "edition", "account", "uptime_seconds", "repos", "active", "queued", "failures_24h", "successes_24h", "red_workflows", "updated",
                                                       "updated_local", "offline", "allowance", "error", "listening", "credential"]))
        self.assertEqual((doc["data"]["version"], doc["data"]["repos"], doc["data"]["failures_24h"]), ("9.9.9", 1, 2))
        self.assertEqual(out, json.dumps(doc, ensure_ascii=False, indent=1) + "\n")

    def test_alerts_and_team_json_carry_the_answer_of_the_monitor_untouched(self):
        _, out, _ = self.ask("alerts", "--json")
        self.assertEqual(json.loads(out), {"ok": True, "exit": 0, "data": ALERTS})
        _, out, _ = self.ask("team", "--json")
        self.assertEqual(json.loads(out)["data"], TEAM)

    def test_the_exit_codes_of_the_old_commands_do_not_move(self):
        self.assertEqual(self.ask("alerts", "--fail-on", "error")[0], 5)
        self.assertEqual(self.ask("alerts", "--fail-on", "critical")[0], 5)
        self.assertEqual(self.ask("alerts")[0], 0)
        self.assertEqual(base.run("status", "--url", "http://127.0.0.1:1", "--lang", "en")[0], 2)
        base.ANSWERS.pop("/api/alerts")
        self.assertEqual(self.ask("alerts")[0], 4)

    def test_the_old_commands_are_the_same_with_format_text(self):
        for command in ("status", "alerts", "team"):
            self.assertEqual(self.ask(command)[1], self.ask(command, "--format", "text")[1], command)

    def test_the_lite_edition_still_answers_only_its_three_commands(self):
        self.assertEqual(monitor_cli.LITE_COMMANDS, ("status", "doctor", "health", "check"))
        for command in ("watch", "completions", "kiosk"):
            self.assertEqual(base.run(command, "status", "--lite", "--lang", "en")[0], 1, command)

    def test_no_new_command_is_imported_by_the_lite_module(self):
        lite = (HERE / "src" / "github_actions_monitor" / "lite.py").read_text(encoding="utf-8")
        for name in ("cli.watch", "cli.formats", "cli.completions", "surfaces"):
            self.assertNotIn(name, lite)


@unittest.skipUnless(shutil.which("jq"), "jq is not installed")
class Jq(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), base.Fake)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_every_example_of_the_guide_runs_against_a_fake_monitor(self):
        base.ANSWERS.clear()
        base.ANSWERS.update({"/api/health": HEALTH, "/api/data": DATA, "/api/alerts": ALERTS, "/api/team/health": TEAM})
        text = (DOCS / "CLI_OPERATOR.md").read_text(encoding="utf-8")
        examples = re.findall(r"^monitor_cli\.py (.+?) \| jq (.+)$", text, re.M)
        self.assertGreaterEqual(len(examples), 4)
        for arguments, program in examples:
            code, out, _ = base.run(*arguments.split(), "--url", self.url, "--lang", "en")
            self.assertIn(code, (0, 5), arguments)
            result = subprocess.run(["jq", *shlex.split(program)], input=out, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(result.returncode, 0, (arguments, result.stderr))
            self.assertTrue(result.stdout.strip(), arguments)


if __name__ == "__main__":
    unittest.main()
