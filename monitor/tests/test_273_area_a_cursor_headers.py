# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A cursor with a letter that is not ASCII is a plain 400 with the envelope, and every answer of the supervisor carries the protection against framing that the answers of an account carry."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_170 as t170  # noqa: E402
import test_251_api_v1 as t251  # noqa: E402
from github_actions_monitor.app import api_v1  # noqa: E402
from github_actions_monitor.security import localguard  # noqa: E402

SECRET = b"s" * 32
HEADERS = [name for name, _ in localguard.SECURITY_HEADERS]


def only_mine(cls):
    for name in dir(cls):
        if name.startswith("test") and name not in cls.__dict__:
            setattr(cls, name, None)
    return cls


class TheCursorIsPlainText(unittest.TestCase):
    def test_a_signature_or_body_with_a_letter_that_is_not_ascii_is_refused_with_the_error_code(self):
        good = api_v1.repos_payload(t251.VIEWS, {"limit": "10"}, secret=SECRET, now=1000, cfg=t251.CFG)["next_cursor"]
        body, mac = good.split(".")
        for cursor in (body + "." + mac[:-1] + "é", "é" + body + "." + mac, body + ".é", body + ".", "." + mac, good + "‮", body + "\u0000." + mac):
            with self.assertRaises(api_v1.ApiError, msg=repr(cursor)) as caught:
                api_v1.read_cursor(SECRET, cursor, api_v1.fingerprint("repos", {}), 1000, 900)
            self.assertEqual((caught.exception.status, caught.exception.code), (400, "api.bad_cursor"))
        self.assertIsNotNone(api_v1.read_cursor(SECRET, good, api_v1.fingerprint("repos", {}), 1000, 900) or True)


@only_mine
class OverHttp(t251.TheServer):
    def test_the_cursor_with_a_non_ascii_letter_gets_the_envelope_not_a_cut_connection(self):
        served = self.serve()
        status, body, _ = self.get(served, "/api/v1/repos?limit=10")
        self.assertEqual(status, 200)
        bad = body["next_cursor"][:-2] + "%C3%A9"
        status, answer, _ = self.get(served, "/api/v1/repos?cursor=" + bad)
        self.assertEqual((status, answer["code"], answer["error"]), (400, "api.bad_cursor", "bad_request"))

    def test_any_other_failure_of_a_route_of_the_prefix_is_the_envelope_of_a_500(self):
        from unittest import mock
        from github_actions_monitor.app import actions_monitor
        served = self.serve()
        with mock.patch.object(api_v1, "repos_payload", side_effect=RuntimeError("boom")):
            status, answer, _ = self.get(served, "/api/v1/repos")
        self.assertEqual((status, answer["code"], answer["error"]), (500, "api.server_error", "server_error"))
        self.assertNotIn("boom", json.dumps(answer))
        self.assertTrue(actions_monitor)


class TheSupervisorProtectsAgainstFraming(t170.Running):
    def test_every_kind_of_answer_carries_the_protection(self):
        for path, headers in (("/api/accounts", {}), ("/api/data?account=alpha", {}), ("/api/echo", {}), ("/?account=alpha", {"Accept": "text/html"}), ("/api/nothing-here?account=alpha", {}),
                              ("/api/data?account=ghost", {}), ("/screen/overview?account=alpha", {})):
            status, _body, head = t170.get(self.url + path, headers)
            lowered = {k.lower(): v for k, v in head.items()}
            for name in HEADERS:
                self.assertIn(name.lower(), lowered, (path, status, name))
            self.assertEqual(lowered["x-frame-options"], "DENY")
            self.assertEqual(sum(1 for k in head if k.lower() == "x-frame-options"), 1, "never twice")

    def test_a_refusal_of_the_gate_carries_it_too(self):
        from unittest import mock
        with mock.patch.object(localguard, "local_request_ok", return_value=False):
            status, _body, head = t170.get(self.url + "/api/accounts")
        self.assertEqual(status, 403)
        self.assertIn("X-Frame-Options", head)

    def test_the_version_header_of_a_route_of_the_prefix_is_passed_back(self):
        from github_actions_monitor.accounts import accounts_supervisor
        self.assertIn("x-api-version", accounts_supervisor.PASS_BACK)


if __name__ == "__main__":
    unittest.main()
