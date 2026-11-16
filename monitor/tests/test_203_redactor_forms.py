# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The forms of a secret that a log really has (a command line, a cookie, a block of a key, an encoding) and the answers of the MCP server that are longer than their limit: a document that
is cut is still a document, says so and keeps the health of the monitor."""
import json
import unittest

import _testenv  # noqa: F401
from github_actions_monitor.integrations import mcp_server
from github_actions_monitor.security import redactor

PGP = "-----BEGIN PGP PRIVATE KEY " + "BLOCK-----\nlQdGBF\n-----END PGP PRIVATE KEY " + "BLOCK-----"
CASES = (
    ("pgp block", PGP, "lQdGBF"),
    ("password with a space", "mysql --password hunter2hunter2 -h db", "hunter2hunter2"),
    ("password glued to -p", "mysql -uroot -phunter2hunter2", "hunter2hunter2"),
    ("cookie", "Cookie: session=abcDEF123456xyz", "abcDEF123456xyz"),
    ("set-cookie", "Set-Cookie: sid=abcDEF123456xyz; HttpOnly", "abcDEF123456xyz"),
    ("ENCRYPTION_KEY", "ENCRYPTION_KEY=abcdef12345", "abcdef12345"),
    ("DSN", "SENTRY_DSN=https://abc123@sentry.example/1", "abc123@sentry"),
    ("CREDS", "AWS_CREDS=zzzzzzzzqq", "zzzzzzzzqq"),
    ("escaped quote", 'password="ab\\"cd SECRETO-FINAL" next', "SECRETO-FINAL"),
    ("phrase", "password: horse battery staple", "battery"),
    ("basic", "Authorization: Basic dTpwYXNz", "dTpwYXNz"),
    ("percent", "password%3Dhunter2hunter2", "hunter2hunter2"),
    ("percent in a token", "gh%70_abcdefghijklmnopqrstuvwxyz0123456789", "abcdefghijklmnopqrstuvwxyz"),
    ("zero width", "pass​word=hunter2hunter2", "hunter2hunter2"),
    ("full width", "ｐａｓｓｗｏｒｄ=hunter2hunter2", "hunter2hunter2"),
    ("ipv6", "link fe80::1ff:fe23:4567:890a up", "fe80::1ff"),
    ("ipv6 in an address", "http://[2001:db8::7]:8080/x", "2001:db8"),
    ("unc", "\\\\servidor\\Users\\victima\\x", "victima"),
    ("root", "cat /root/.ssh/id_rsa", "/root"),
    ("jenkins", "read /var/lib/jenkins/secrets/master.key", "master.key"),
    ("stripe", "sk_live_abcdefghijklmnop1234", "abcdefghijklmnop1234"),
    ("token cut in two lines", "gh" + "p_aBcDeFgH1234567890\nI9j0K1l2M3n4O5p6Q7r8", "I9j0K1l2M3n4O5p6Q7r8"),
)
HARMLESS = ("Error: step Run tests failed with exit code 1", "at 10:00:00 and 12:30 std::vector done", "built in 12.5s: 3 passed", "password: [secret]")


class FormsOfASecret(unittest.TestCase):
    def test_every_form_is_cleaned(self):
        for name, text, forbidden in CASES:
            with self.subTest(name):
                self.assertNotIn(forbidden, redactor.redact(text))

    def test_ordinary_text_is_left_alone(self):
        for text in HARMLESS:
            self.assertEqual(redactor.redact(text), text)

    def test_the_key_of_a_pair_says_it_is_a_secret(self):
        out = redactor.redact_data({"password": "hunter2hunter2", "token": "abcDEF123456", "token_env": "GH_TOKEN", "n": 3, "list": [{"api_key": "kkkkkkkk"}]})
        self.assertEqual(out["password"], "[secret]")
        self.assertEqual(out["token"], "[secret]")
        self.assertEqual(out["token_env"], "GH_TOKEN", "the NAME of a variable is not a secret")
        self.assertEqual(out["list"][0]["api_key"], "[secret]")
        self.assertEqual(out["n"], 3)


class ALongAnswerIsStillADocument(unittest.TestCase):
    @staticmethod
    def big_state(rows=400):
        signals = [{"id": f"alerts.item{i}", "level": "act", "text": "a workflow is red in some repository " + "x" * 80} for i in range(rows)]
        signals.append({"id": "health.refresh", "level": "warn", "text": "data read 900 s ago"})
        return {"edition": "complete", "signals": signals}

    def test_fit_json_trims_rows_keeps_the_health_and_says_so(self):
        text = redactor.fit_json(self.big_state(), 5000, first=mcp_server._health_row)
        document = json.loads(text)
        self.assertLessEqual(len(text), 5000)
        self.assertTrue(document["truncated"])
        self.assertGreater(document["omitted_rows"], 0)
        self.assertIn("health.refresh", [s["id"] for s in document["signals"]])

    def test_a_short_answer_is_not_touched(self):
        document = json.loads(redactor.fit_json({"a": [1, 2, 3]}, 5000))
        self.assertEqual(document, {"a": [1, 2, 3]})

    def test_a_document_that_is_not_an_object_is_wrapped(self):
        document = json.loads(redactor.fit_json(["x" * 100] * 200, 1000))
        self.assertTrue(document["truncated"])
        self.assertLessEqual(len(json.dumps(document)), 1200)

    def test_without_any_list_to_trim_the_answer_is_still_valid(self):
        document = json.loads(redactor.fit_json({"text": "word " * 5000}, 1000))
        self.assertTrue(document["truncated"])

    def test_every_tool_with_a_limit_answers_valid_json_with_the_health_signal(self):
        state = self.big_state(1500)
        for tool, arguments in (("monitor_state", {}), ("signals", {})):
            text = mcp_server.call(tool, arguments, {}, getter=lambda path: state)
            document = json.loads(text)
            self.assertTrue(document["truncated"], tool)
            self.assertIn("health.refresh", [s["id"] for s in document["signals"]], tool)


if __name__ == "__main__":
    unittest.main()
