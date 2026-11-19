# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The command `api` of the command line (`api openapi`, `api me`) against a real monitor: it prints the document and who the monitor takes the client for, and says in one line that the API is closed."""
import contextlib
import io
import json
import unittest
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor import i18n
from github_actions_monitor.app import actions_monitor, api_v1
from github_actions_monitor.cli import monitor_cli as cli
from test_200_contract import Served


def run(url, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(["api", *args, "--url", url, "--lang", "en"])
    return code, out.getvalue(), err.getvalue()


class TheApiCommand(unittest.TestCase):
    def serve(self, service):
        served = Served(self, lite=False)
        patcher = mock.patch.object(actions_monitor, "service_mode", return_value=service)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(i18n.set_language, "en")
        return served

    def test_it_is_a_command_with_its_two_actions_and_texts_in_eight_languages(self):
        self.assertIn("api", cli.COMMANDS)
        self.assertEqual(cli.API_ACTIONS, ("openapi", "me", "contract-check"))
        self.assertNotIn("api", cli.LITE_COMMANDS)      # the lite edition has no prefix
        from pathlib import Path
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            texts = json.loads((Path(__file__).resolve().parent.parent / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("cli.api_action", "cli.api_closed", "cli.api_me", "cli.api_can", "cli.api_no_suite", "cli.api_suite_total"):
                self.assertTrue(texts.get(key), (lang, key))
            self.assertIn("{things}", texts["cli.api_can"], lang)
            self.assertIn("api", texts["cli.help_command"], lang)

    def test_openapi_prints_the_document_of_the_contract(self):
        served = self.serve(True)
        code, out, _ = run(served.url, "openapi")
        self.assertEqual(code, cli.EXIT_OK)
        document = json.loads(out)      # plain output is the document itself: it can be redirected to a file
        self.assertEqual(document["openapi"], "3.0.3")
        self.assertIn("/api/v1/health", document["paths"])
        code, out, _ = run(served.url, "openapi", "--json")
        self.assertEqual(json.loads(out)["data"]["info"]["x-contract-version"], api_v1.CONTRACT_VERSION)

    def test_me_says_who_the_client_is_and_what_it_may_do(self):
        served = self.serve(True)
        code, out, _ = run(served.url, "me")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("mode individual", out)
        self.assertIn("contract " + api_v1.CONTRACT_VERSION, out)
        self.assertIn("the session may: read, write, admin", out)
        code, out, _ = run(served.url, "me", "--json")
        data = json.loads(out)["data"]
        self.assertEqual((data["capabilities"]["v1_write"], data["api_version"]), (False, "1"))

    def test_a_closed_api_is_said_in_one_line_and_is_not_a_crash(self):
        served = self.serve(False)      # "auto" outside the service mode
        for action in ("openapi", "me"):
            code, out, err = run(served.url, action)
            self.assertEqual(code, cli.EXIT_DEGRADED)
            self.assertIn("api.v1_enabled", out + err)

    def test_contract_check_runs_the_suite_against_the_monitor(self):
        import test_api_contract_suite as fixture
        served = fixture.real_monitor(self)
        code, out, _ = run(served.url, "contract-check")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertNotIn("FAIL ", out)
        self.assertRegex(out.strip().splitlines()[-1], r"^(\d+) of (\d+) checks pass$")
        code, out, _ = run(served.url, "contract-check", "--json")
        data = json.loads(out)["data"]
        self.assertEqual((data["ok"], data["failed"]), (True, 0))

    def test_contract_check_fails_with_exit_4_when_the_api_is_closed(self):
        served = self.serve(False)
        code, out, _ = run(served.url, "contract-check")
        self.assertEqual(code, cli.EXIT_DEGRADED)
        self.assertIn("FAIL openapi: served", out)

    def test_a_wrong_action_is_a_usage_error(self):
        served = self.serve(True)
        code, _, _ = run(served.url, "nothing")
        self.assertEqual(code, cli.EXIT_USAGE)


if __name__ == "__main__":
    unittest.main()
