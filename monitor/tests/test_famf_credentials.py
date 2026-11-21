# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The assistant of the credentials: the installation of a GitHub App is found by itself (the one of the account of the monitor, else the only one, never "the first"), and the test of the token says who it
is, classic or fine-grained, which scopes it lacks, how many repositories it sees and how much allowance is left. Every answer of GitHub is a fake."""
import json
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.integrations import credential_probe, github_app  # noqa: E402

NOW = 1_800_000_000.0
CONFIG = {"github_owner": "demo-owner", "github_app": {"enabled": True, "app_id": "123", "key_path": "/home/me/app.pem"}}
SECRET_TOKEN = "ghs_" + "A" * 36


def fake_signer(data, key_path):
    return b"signature-bytes" * 16


class FakeGitHub:
    def __init__(self, installations):
        self.installations, self.calls = installations, []

    def __call__(self, request):
        path, method = request.full_url.replace(github_app.API, ""), request.get_method()
        self.calls.append((method, path))
        if path == "/app/installations":
            return self.installations, {}
        if path.endswith("/access_tokens"):
            return {"token": SECRET_TOKEN, "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 3600))}, {}
        raise AssertionError(path)


def row(number, login, kind="User"):
    return {"id": number, "account": {"login": login, "type": kind}, "target_type": kind}


class Installations(unittest.TestCase):
    def setUp(self):
        github_app.reset()
        self.addCleanup(github_app.reset)

    def test_the_rows_keep_only_what_is_a_plain_installation(self):
        rows = github_app.installation_rows([row(7, "a"), {"id": "x"}, "junk", {"id": 123456789012345}, {"id": 8}, row(9, "b" * 200, "Organization")])
        self.assertEqual([r["id"] for r in rows], ["7", "8", "9"])
        self.assertEqual(rows[1], {"id": "8", "account": "", "type": ""})
        self.assertLessEqual(len(rows[2]["account"]), 60)
        self.assertEqual(github_app.installation_rows(None), [])

    def test_the_one_of_the_account_of_the_monitor_wins_and_the_first_is_never_a_guess(self):
        rows = github_app.installation_rows([row(1, "someone-else"), row(2, "Demo-Owner")])
        self.assertEqual(github_app.pick_installation(rows, "", "demo-owner"), ("2", ""))
        self.assertEqual(github_app.pick_installation(rows, "", "nobody"), ("", "several"))
        self.assertEqual(github_app.pick_installation(rows, "", ""), ("", "several"))
        self.assertEqual(github_app.pick_installation(rows[:1], "", "nobody"), ("1", ""))      # the only one
        self.assertEqual(github_app.pick_installation([], "", "x"), ("", "none"))

    def test_the_one_that_is_written_must_be_one_of_the_App(self):
        rows = github_app.installation_rows([row(1, "a"), row(2, "b")])
        self.assertEqual(github_app.pick_installation(rows, "2", "a"), ("2", ""))
        self.assertEqual(github_app.pick_installation(rows, "99", "a"), ("", "unknown_id"))

    def test_the_token_is_asked_for_the_installation_of_the_account_and_not_for_the_first(self):
        fake = FakeGitHub([row(1, "someone-else"), row(2, "JuanenRac")])
        self.assertEqual(github_app.token(CONFIG, opener=fake, signer=fake_signer, now=NOW), SECRET_TOKEN)
        self.assertEqual([c[1] for c in fake.calls], ["/app/installations", "/app/installations/2/access_tokens"])

    def test_with_several_accounts_and_none_of_them_the_monitor_one_it_reads_with_the_user_and_says_why(self):
        fake = FakeGitHub([row(1, "a"), row(2, "b")])
        self.assertEqual(github_app.token(CONFIG | {"github_owner": "c"}, opener=fake, signer=fake_signer, now=NOW), "")
        self.assertEqual([c[1] for c in fake.calls], ["/app/installations"])      # no token was asked for the wrong account
        self.assertIn("installation_id", github_app._STATE["error"])

    def test_the_shared_token_takes_the_same_rule(self):
        fake = FakeGitHub([row(5, "x"), row(6, "JuanenRac")])
        github_app.shared_token(CONFIG, opener=lambda request: ({"token": SECRET_TOKEN, "permissions": {"actions": "read"}}, {}) if request.get_method() == "POST" else fake(request), signer=fake_signer, now=NOW)
        self.assertEqual(fake.calls, [("GET", "/app/installations")])

    def test_discover_lists_and_chooses_and_never_carries_a_secret(self):
        found = github_app.discover(CONFIG, opener=FakeGitHub([row(1, "x"), row(2, "JuanenRac", "Organization")]), signer=fake_signer, now=NOW)
        self.assertEqual((found["ok"], found["chosen"], found["reason"]), (True, "2", ""))
        self.assertEqual(found["installations"][1], {"id": "2", "account": "JuanenRac", "type": "Organization"})
        self.assertNotIn(SECRET_TOKEN, json.dumps(found))
        several = github_app.discover(CONFIG | {"github_owner": "z"}, opener=FakeGitHub([row(1, "x"), row(2, "y")]), signer=fake_signer, now=NOW)
        self.assertEqual((several["chosen"], several["reason"], len(several["installations"])), ("", "several", 2))

    def test_discover_without_an_App_or_with_a_failure_says_so(self):
        self.assertEqual(github_app.discover({}, signer=fake_signer)["reason"], "off")

        def broken(request):
            raise RuntimeError("HTTP 401 Bearer eyJhbGciOiJSUzI1NiJ9.abcdefghijklmnop.sig")
        found = github_app.discover(CONFIG, opener=broken, signer=fake_signer, now=NOW)
        self.assertEqual((found["ok"], found["reason"], found["installations"]), (False, "failed", []))

    def test_a_configured_installation_that_the_App_does_not_have_is_reported(self):
        config = {**CONFIG, "github_app": {**CONFIG["github_app"], "installation_id": "999"}}
        found = github_app.discover(config, opener=FakeGitHub([row(1, "JuanenRac")]), signer=fake_signer, now=NOW)
        self.assertEqual((found["chosen"], found["reason"]), ("", "unknown_id"))


def gh(scopes="repo, read:org", login="demo-owner", owner_status=200, kind="Organization", repos=7, sso=False, rate=(5000, 4321, 1_800_000_900), user_status=200):
    """A fake `gh`: the answers of user, orgs/OWNER, the list of repositories and rate_limit."""
    def run(args):
        endpoint = args[-1]
        headers = (f"x-oauth-scopes: {scopes}\r\n" if scopes is not None else "")
        if endpoint == "user":
            return (0, f"HTTP/2.0 {user_status} OK\r\n{headers}\r\n" + json.dumps({"login": login}), "") if user_status == 200 else (1, "", "HTTP 401: Bad credentials")
        if endpoint.startswith("orgs/") and "repos" not in endpoint:
            return (0, "HTTP/2.0 200 OK\r\n\r\n" + json.dumps({"public_repos": repos - 2, "total_private_repos": 2}), "") if kind == "Organization" else (1, "", "HTTP 404 Not Found")
        if endpoint.startswith("users/") and "repos" not in endpoint:
            return 0, "HTTP/2.0 200 OK\r\n\r\n" + json.dumps({"public_repos": repos}), ""
        if "repos" in endpoint:
            return 0, "HTTP/2.0 200 OK\r\n" + ("x-github-sso: partial-results; organizations=1\r\n" if sso else "") + "\r\n[]", ""
        if endpoint == "rate_limit":
            return 0, json.dumps({"resources": {"core": {"limit": rate[0], "remaining": rate[1], "reset": rate[2]}}}), ""
        raise AssertionError(endpoint)
    return run


class TheToken(unittest.TestCase):
    def setUp(self):
        credential_probe.reset()
        self.addCleanup(credential_probe.reset)

    def test_the_kind_and_what_is_missing(self):
        self.assertEqual(credential_probe.kind_of(["repo"]), "classic")
        self.assertEqual(credential_probe.kind_of([]), "classic")
        self.assertEqual(credential_probe.kind_of(None), "fine_grained_or_app")
        self.assertEqual(credential_probe.missing(["repo"], "organization"), ["read:org"])
        self.assertEqual(credential_probe.missing(["repo", "admin:org"], "organization"), [])
        self.assertEqual(credential_probe.missing([], "user"), ["repo"])
        self.assertEqual(credential_probe.missing(None, "organization"), [])

    def test_a_good_classic_token_says_who_what_how_many_and_how_much_is_left(self):
        user = credential_probe.user_side(gh(), "demo-owner")
        self.assertEqual((user["ok"], user["login"], user["kind"], user["scopes"], user["missing"]), (True, "demo-owner", "classic", ["read:org", "repo"], []))
        self.assertEqual((user["owner_kind"], user["repos"], user["partial"]), ("organization", 7, False))
        self.assertEqual(user["rate"], {"limit": 5000, "remaining": 4321, "reset": 1_800_000_900})

    def test_a_fine_grained_token_has_no_scopes_and_nothing_is_missing_by_scope(self):
        user = credential_probe.user_side(gh(scopes=None), "demo-owner")
        self.assertEqual((user["kind"], user["scopes"], user["missing"], user["ok"]), ("fine_grained_or_app", None, [], True))

    def test_a_token_without_the_scope_for_an_organization_says_which(self):
        user = credential_probe.user_side(gh(scopes="repo"), "demo-owner")
        self.assertEqual(user["missing"], ["read:org"])

    def test_single_sign_on_leaves_the_list_incomplete(self):
        user = credential_probe.user_side(gh(sso=True), "demo-owner")
        self.assertTrue(user["partial"])
        self.assertEqual(user["cause"], "sso")
        self.assertFalse(user["ok"])

    def test_a_refused_login_has_a_cause_and_no_allowance_is_asked(self):
        asked = []

        def refused(args):
            asked.append(args[-1])
            return gh(user_status=401)(args)
        user = credential_probe.user_side(refused, "demo-owner")
        self.assertEqual((user["ok"], user["cause"], user["kind"], user["rate"]), (False, "auth", "unknown", None))
        self.assertNotIn("rate_limit", asked)

    def test_an_answer_of_the_allowance_that_is_not_one_is_nothing(self):
        for out in ("", "not json", json.dumps({"resources": {}}), json.dumps({"resources": {"core": {"limit": "x", "remaining": 1, "reset": 2}}})):
            self.assertIsNone(credential_probe.rate_of(lambda args, o=out: (0, o, "")))
        self.assertIsNone(credential_probe.rate_of(lambda args: (1, "", "boom")))

    def test_the_whole_answer_without_an_App_and_the_wait_between_two_asks(self):
        first = credential_probe.probe({}, gh(), "demo-owner", now=NOW)
        self.assertIsNone(first["app"])
        self.assertFalse(first["cached"])
        second = credential_probe.probe({}, gh(scopes="x"), "demo-owner", now=NOW + 3)
        self.assertTrue(second["cached"])
        self.assertEqual(second["user"]["scopes"], first["user"]["scopes"])
        third = credential_probe.probe({}, gh(scopes="x"), "demo-owner", now=NOW + 11)
        self.assertFalse(third["cached"])
        self.assertEqual(third["user"]["scopes"], ["x"])
        forced = credential_probe.probe({}, gh(scopes="y"), "demo-owner", now=NOW + 12, force=True)
        self.assertEqual(forced["user"]["scopes"], ["y"])

    def test_the_app_side_shows_what_the_App_lacks_its_allowance_and_the_installations(self):
        status = lambda config: {"ok": True, "app": "demo-reader", "installation_id": "2", "rate": {"remaining": 9000, "limit": 10550, "reset": 5},      # noqa: E731
                                 "permissions": {"actions": "read", "contents": "missing", "metadata": "read"}}
        discover = lambda config: {"ok": True, "installations": [{"id": "2", "account": "demo-owner", "type": "User"}], "chosen": "2", "reason": ""}      # noqa: E731
        app = credential_probe.app_side(CONFIG, status, discover)
        self.assertEqual((app["ok"], app["app"], app["installation_id"], app["missing"], app["chosen"]), (True, "demo-reader", "2", ["contents"], "2"))
        self.assertEqual(app["rate"]["remaining"], 9000)
        self.assertIsNone(credential_probe.app_side({}, status, discover))

    def test_an_App_with_several_accounts_lists_them_so_one_can_be_written(self):
        status = lambda config: {"ok": False, "error": "the App is installed on several accounts", "permissions": {}}      # noqa: E731
        discover = lambda config: {"ok": True, "installations": [{"id": "1", "account": "a", "type": "User"}, {"id": "2", "account": "b", "type": "User"}], "chosen": "", "reason": "several"}      # noqa: E731
        app = credential_probe.app_side(CONFIG, status, discover)
        self.assertEqual((app["ok"], app["chosen"], app["choose_reason"], len(app["installations"])), (False, "", "several", 2))

    def test_no_answer_carries_a_token_or_a_key(self):
        answer = credential_probe.probe(CONFIG, gh(), "demo-owner", status=lambda c: {"ok": True, "permissions": {}}, discover=lambda c: {"installations": [], "chosen": ""}, now=NOW, force=True)
        text = json.dumps(answer)
        for secret in (SECRET_TOKEN, "BEGIN", "app.pem", "ghp_"):
            self.assertNotIn(secret, text)

    def test_the_page_route_and_the_button_exist(self):
        source = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn('"/api/credential/probe"', source)
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("/api/credential/probe", page)
        self.assertIn("ui.qt_test_token", page)


if __name__ == "__main__":
    unittest.main()
