# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Fixes of a security review of the team mode and its edges: the first administrator through the local port behind a proxy, the test message counted against the hourly limit, the default
sender of the e-mail channel, a token for other tools that can only read, a proxy in another container, the lock of a login, and the two secrets that leave the environment."""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_auth  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am, settings_api  # noqa: E402
from github_actions_monitor.cli import monitor_cli  # noqa: E402
from github_actions_monitor.integrations import ai_notify, channels, dispatcher, github_app  # noqa: E402
from github_actions_monitor.security import auth, auth_http, envguard, localguard  # noqa: E402

PASSWORD = test_auth.PASSWORD
ACCESS = "T" * 24


class Headers(dict):
    def get(self, key, default=None):
        for k, v in self.items():
            if k.lower() == key.lower():
                return v
        return default


def only_mine(cls):
    for name in dir(cls):
        if name.startswith("test") and name not in cls.__dict__:
            setattr(cls, name, None)
    return cls


@only_mine
class TeamEdges(test_auth.LiveTeam):
    def team(self, extra=None):
        self.start({"auth": {"enabled": True}, "session_guard": False, **(extra or {})})
        self.make_admin()
        self.admin = self.sign_in("root")

    def test_the_first_administrator_is_created_through_the_local_port_behind_a_proxy(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        localguard.configure(True, "127.0.0.1", ACCESS, secure=True, proxy_host="monitor.example", behind_proxy=True)
        door_handler = type("Door", (am.Handler,), {"local_door": True})
        door = ThreadingHTTPServer(("127.0.0.1", 0), door_handler)
        threading.Thread(target=door.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (door.shutdown(), door.server_close()))
        main_base, self.base = self.base, f"http://127.0.0.1:{door.server_address[1]}"
        status, body, _ = self.call("/api/auth/bootstrap", {"username": "root", "password": PASSWORD}, {"X-Monitor-Access": ACCESS})
        self.assertEqual(status, 200, body)
        self.base = main_base
        status, body, _ = self.call("/api/auth/bootstrap", {"username": "other", "password": PASSWORD}, {"X-Monitor-Access": ACCESS})
        self.assertIn(status, (403, 409), "the main port, behind a proxy, is never this computer")

    def test_the_test_message_counts_against_the_hourly_limit(self):
        self.team({"notify": {"users": {"enabled": True, "max_per_hour": 2}, "channels": {"email": {"enabled": True, "sender": "monitor@example.org"}}}})
        self.add_user(self.admin, "vic", "viewer")
        vic = self.sign_in("vic")
        status, body, _ = self.call("/api/auth/me/notify", {"enabled": True, "channels": ["email"], "destinations": {"email": {"address": "somebody@other-domain.example"}}}, vic)
        self.assertEqual(status, 200, body)
        sent = []

        class FakeSMTP:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def send_message(self, mail):
                sent.append(mail["To"])
        dispatcher._sent.clear()
        with mock.patch.object(channels.smtplib, "SMTP", FakeSMTP):
            codes = [self.call("/api/auth/me/notify/test", {}, vic)[0] for _ in range(8)]
        self.assertEqual(len(sent), 2, "only the allowed ones reach the relay")
        self.assertEqual(codes.count(200), 2)
        self.assertEqual(set(codes) - {200}, {429})

    def test_a_person_at_the_computer_is_not_locked_out_of_the_login(self):
        self.team()
        for i in range(8):
            status, body, _ = self.call("/api/auth/login", {"username": "root", "password": "wrong password %d" % i})
            self.assertEqual((status, body["code"]), (401, "invalid_credentials"), "a wrong password from this computer never locks")
        status, body, _ = self.call("/api/auth/login", {"username": "root", "password": PASSWORD})
        self.assertEqual(status, 200, body)


class DefaultSender(unittest.TestCase):
    def test_the_default_email_settings_pass_the_check_and_a_wrong_sender_is_named(self):
        cfg = channels.server_settings({"notify": {"channels": {"email": {"enabled": True}}}})["email"]
        self.assertIsNone(channels.PLUGINS["email"].check_server(cfg))
        result = channels.deliver("email", cfg, {"address": "ana@example.org"}, "", {"title": "t", "text": "x", "url": None, "level": "info", "repo": ""}, smtp=_FakeRelay)
        self.assertEqual(result, {"channel": "email", "ok": True, "reason": ""})
        for sender in ("nobody", "a b@example.org", "x@", "@localhost"):
            self.assertEqual(channels.PLUGINS["email"].check_server({**cfg, "sender": sender}), "bad_sender", sender)
        self.assertIsNone(channels.PLUGINS["email"].check_server({**cfg, "sender": "monitor@example.org"}))


class _FakeRelay:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def send_message(self, mail):
        pass


class SharedToken(unittest.TestCase):
    CONFIG = {"github_app": {"enabled": True, "app_id": "1", "key_path": "/nonexistent/key.pem", "installation_id": "7", "share_reads": True}}

    def run_command(self, granted):
        sent = []

        def fake_call(method, path, bearer, body=None, opener=None):
            sent.append((method, path, body))
            asked = json.loads(body or b"{}").get("permissions")
            return {"token": "ghs_" + "x" * 36, "expires_at": "2099-01-01T00:00:00Z", "permissions": granted(asked)}, {}
        github_app._STATE.update({"token": "", "expires": 0.0, "failed_at": 0.0})
        from github_actions_monitor.app import toolconfig
        with mock.patch.object(github_app, "_call", fake_call), mock.patch.object(github_app, "make_jwt", lambda *a, **k: "jwt"), mock.patch.object(toolconfig, "raw_config", lambda: self.CONFIG):
            try:
                return monitor_cli.cmd_gh_token({"read_only": True}), sent
            except monitor_cli.CliError as error:
                return error, sent

    def test_the_token_is_asked_with_read_permissions_only(self):
        result, sent = self.run_command(lambda asked: asked)
        (data, lines, code), = (result,)
        self.assertEqual(code, monitor_cli.EXIT_OK)
        body = json.loads(next(b for m, p, b in sent if p.endswith("/access_tokens")))
        self.assertEqual(set(body["permissions"].values()), {"read"})
        self.assertEqual(set(body["permissions"]), set(github_app.PERMISSIONS))
        self.assertTrue(lines[0].startswith("ghs_"))

    def test_a_token_that_could_write_is_refused(self):
        result, _ = self.run_command(lambda asked: {**asked, "contents": "write"})
        self.assertIsInstance(result, monitor_cli.CliError)
        self.assertIn(i18n.t("cli.gh_token_not_read_only"), str(result.args))
        result, _ = self.run_command(lambda asked: None)
        self.assertIsInstance(result, monitor_cli.CliError, "an answer that does not prove read-only is not handed out")

    def test_the_text_exists_in_eight_languages(self):
        for lang in i18n.LANGUAGES if hasattr(i18n, "LANGUAGES") else ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            self.assertNotEqual(i18n.tl(lang, "cli.gh_token_not_read_only"), "cli.gh_token_not_read_only", lang)


class ProxyInAnotherContainer(unittest.TestCase):
    PROXY = ("172.29.77.5", 40000)
    VISITOR = Headers({"X-Forwarded-For": "203.0.113.9"})

    def tearDown(self):
        localguard.configure(False)
        localguard.reset_limits()

    def test_only_the_declared_networks_are_believed(self):
        localguard.configure(True, "0.0.0.0", ACCESS, trusted_proxy=True, trusted_proxies=["172.29.77.0/24"])
        self.assertEqual(localguard.client_key(self.PROXY, self.VISITOR), "fwd:203.0.113.9")
        self.assertEqual(localguard.client_key(("172.29.78.5", 40000), self.VISITOR), "172.29.78.5", "an address outside the declared network is counted as itself")
        self.assertEqual(localguard.client_key(("203.0.113.50", 40000), self.VISITOR), "203.0.113.50", "a stranger cannot choose the address it is counted as")
        self.assertEqual(localguard.client_key(("127.0.0.1", 40000), self.VISITOR), "fwd:203.0.113.9", "this computer stays trusted")
        self.assertFalse(localguard.from_this_computer(self.PROXY), "it never makes a request count as this computer")
        self.assertTrue(localguard.trusted_peer(self.PROXY))

    def test_nothing_changes_without_trusted_proxy_or_without_networks(self):
        localguard.configure(True, "0.0.0.0", ACCESS, trusted_proxy=False, trusted_proxies=["172.29.77.0/24"])
        self.assertEqual(localguard.client_key(self.PROXY, self.VISITOR), "172.29.77.5")
        localguard.configure(True, "0.0.0.0", ACCESS, trusted_proxy=True)
        self.assertEqual(localguard.client_key(self.PROXY, self.VISITOR), "172.29.77.5")

    def test_one_visitor_does_not_lock_out_the_others_behind_the_proxy(self):
        localguard.configure(True, "0.0.0.0", ACCESS, trusted_proxy=True, trusted_proxies=["172.29.77.0/24"])
        for _ in range(10):
            localguard.note_failure(localguard.client_key(self.PROXY, self.VISITOR), 10)
        self.assertTrue(localguard.is_locked_out(self.PROXY, self.VISITOR))
        self.assertFalse(localguard.is_locked_out(self.PROXY, Headers({"X-Forwarded-For": "198.51.100.7"})), "another person is not locked")

    def test_the_setting_is_read_checked_and_documented(self):
        listen = localguard.settings_from({"listen": {"trusted_proxies": ["172.29.77.0/24", "10.0.0.5", 5]}})
        self.assertEqual(listen["trusted_proxies"], ["172.29.77.0/24", "10.0.0.5"])
        self.assertEqual(localguard.settings_from({})["trusted_proxies"], [])
        self.assertEqual(len(localguard.proxy_networks(["172.29.77.0/24", "nonsense", "fd00::/8"])), 2)
        self.assertIn("listen.trusted_proxies", settings_api.FIELDS)
        self.assertTrue(localguard.local_only_key("listen.trusted_proxies"))
        self.assertEqual(settings_api.check_value("listen.trusted_proxies", ["172.29.77.0/24"])[0], True)
        self.assertEqual(settings_api.check_value("listen.trusted_proxies", ["bad value;"])[0], False)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            for prefix in ("cfg.f.", "cfg.h."):
                self.assertNotEqual(i18n.tl(lang, prefix + "listen.trusted_proxies"), prefix + "listen.trusted_proxies", lang)

    def test_the_compose_file_gives_the_proxy_a_known_network(self):
        compose, example = REPO / "deploy" / "compose.yaml", REPO / "deploy" / ".env.example"
        if not (compose.is_file() and example.is_file()):
            self.skipTest("the deploy files live in the repository, not in the product folder")
        text = compose.read_text(encoding="utf-8")
        for needle in ("MONITOR_TRUSTED_PROXY:", "MONITOR_TRUSTED_PROXIES:", "MONITOR_SUBNET"):
            self.assertIn(needle, text)
        for needle in ("MONITOR_TRUSTED_PROXY=", "MONITOR_TRUSTED_PROXIES=", "MONITOR_SUBNET=", "MONITOR_PROXY_IP="):
            self.assertIn(needle, example.read_text(encoding="utf-8"))
        # the proxy has ONE fixed address and the monitor is told that address, not the whole network: a container that skips Caddy would be believed
        self.assertIn("ipv4_address: ${MONITOR_PROXY_IP:-172.29.77.250}", text)
        self.assertIn("MONITOR_TRUSTED_PROXIES=", example.read_text(encoding="utf-8"))
        from github_actions_monitor import service
        self.assertEqual(service.LISTEN_ENV["MONITOR_TRUSTED_PROXIES"], ("listen", "trusted_proxies", "list"))


class LoginLock(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.storage = test_auth.new_storage(self.tmp.name)
        self.addCleanup(self.storage.close)
        auth.GHOSTS.clear()
        self.addCleanup(auth.GHOSTS.clear)
        auth.create_user(self.storage, "root", PASSWORD, "admin")
        self.cfg = auth.settings({"auth": {"enabled": True, "max_failed_logins": 5}})

    def attempts(self, name, count, **kw):
        return [auth.login(self.storage, name, "wrong password %d" % i, self.cfg, **kw)[1] for i in range(count)]

    def test_a_name_that_does_not_exist_is_locked_like_one_that_does(self):
        real, ghost = self.attempts("root", 6), self.attempts("nobody", 6)
        self.assertEqual(real, ghost)
        self.assertEqual(real[-2:], ["locked", "locked"])
        self.assertGreater(auth.locked_for(self.storage, "nobody"), 0, "the answer carries a wait time for both")
        self.assertEqual(auth.locked_for(self.storage, "nobody") > 0, auth.locked_for(self.storage, "root") > 0)

    def test_a_person_at_the_computer_is_neither_locked_nor_counted(self):
        self.assertEqual(set(self.attempts("root", 12, local=True)), {"invalid_credentials"})
        self.assertEqual(set(self.attempts("nobody", 12, local=True)), {"invalid_credentials"})
        session, code = auth.login(self.storage, "root", PASSWORD, self.cfg, local=True)
        self.assertEqual(code, "")
        self.assertEqual(self.attempts("root", 2)[-1], "invalid_credentials", "the counter was not moved by this computer")

    def test_the_person_at_the_computer_gets_in_while_the_network_has_the_user_locked(self):
        self.assertEqual(self.attempts("root", 5)[-1], "locked")
        self.assertEqual(auth.login(self.storage, "root", PASSWORD, self.cfg)[1], "locked")
        session, code = auth.login(self.storage, "root", PASSWORD, self.cfg, local=True)
        self.assertEqual(code, "")
        self.assertIsNotNone(session)

    def test_the_names_that_do_not_exist_are_bounded(self):
        with mock.patch.object(auth, "MAX_GHOSTS", 12), mock.patch.object(auth, "burn_time", lambda password: None):
            for i in range(40):
                auth.login(self.storage, "ghost%d" % i, "wrong password", self.cfg)
        self.assertLessEqual(len(auth.GHOSTS), 12)


class SecretsLeaveTheEnvironment(unittest.TestCase):
    def setUp(self):
        self.saved = (dict(envguard.HELD), set(envguard.NAMES), {k: os.environ.get(k) for k in ("MONITOR_SUPERVISOR_KEY", "MONITOR_ACCESS_TOKEN", "MONITOR_TEST_TOKEN_NAME")})
        self.addCleanup(self.restore)

    def restore(self):
        envguard.HELD.clear()
        envguard.HELD.update(self.saved[0])
        envguard.NAMES.clear()
        envguard.NAMES.update(self.saved[1])
        for key, value in self.saved[2].items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_the_two_secrets_are_taken_out_of_the_environment_and_kept_here(self):
        os.environ["MONITOR_SUPERVISOR_KEY"], os.environ["MONITOR_ACCESS_TOKEN"] = "supervisor-key-for-the-test", "access-token-for-the-test"
        os.environ["MONITOR_TEST_TOKEN_NAME"] = "renamed-token-for-the-test"
        envguard.hold("MONITOR_TEST_TOKEN_NAME")
        for name in ("MONITOR_SUPERVISOR_KEY", "MONITOR_ACCESS_TOKEN", "MONITOR_TEST_TOKEN_NAME"):
            self.assertNotIn(name, os.environ)
            self.assertTrue(envguard.get(name))
        self.assertNotIn("MONITOR_SUPERVISOR_KEY", envguard.clean_environment())
        wanted = envguard.for_account_process({"MONITOR_AUTH_CHILD": "1"})
        self.assertEqual(wanted["MONITOR_SUPERVISOR_KEY"], "supervisor-key-for-the-test")
        self.assertEqual(wanted["MONITOR_AUTH_CHILD"], "1")
        os.environ["MONITOR_SUPERVISOR_KEY"] = "set-again-by-a-parent"
        self.assertEqual(envguard.get("MONITOR_SUPERVISOR_KEY"), "set-again-by-a-parent", "what the environment says now wins")
        self.assertNotIn("MONITOR_SUPERVISOR_KEY", envguard.clean_environment(), "and still never goes to a program")

    def test_the_programs_the_monitor_starts_do_not_get_them(self):
        os.environ["MONITOR_SUPERVISOR_KEY"], os.environ["MONITOR_ACCESS_TOKEN"] = "supervisor-key-for-the-test", "access-token-for-the-test"
        seen = {}

        def fake_run(args, **kwargs):
            seen.update(kwargs)
            return mock.Mock(stdout="")
        with mock.patch.object(ai_notify.subprocess, "run", fake_run):
            ai_notify._command(str(Path(sys.executable)), "{}", 5)
        self.assertNotIn("MONITOR_SUPERVISOR_KEY", seen["env"])
        self.assertNotIn("MONITOR_ACCESS_TOKEN", seen["env"])
        from github_actions_monitor.security import secretstore
        secretstore.APPLIED["token"] = "ghp_for_the_test"
        self.addCleanup(secretstore.APPLIED.update, token="")
        env = secretstore.gh_kwargs()["env"]
        self.assertEqual(env["GH_TOKEN"], "ghp_for_the_test")
        self.assertNotIn("MONITOR_SUPERVISOR_KEY", env)
        self.assertNotIn("MONITOR_ACCESS_TOKEN", env)

    def test_the_network_setup_reads_the_token_once_and_removes_it(self):
        os.environ["MONITOR_ACCESS_TOKEN"] = "a-long-enough-access-token-for-the-test"
        saved = dict(localguard.STATE)
        self.addCleanup(lambda: (localguard.STATE.clear(), localguard.STATE.update(saved)))
        listen, _tls, token, generated = am.network_setup({"listen": {"network": True, "host": "127.0.0.1"}})
        self.assertEqual((token, generated), ("a-long-enough-access-token-for-the-test", False))
        self.assertNotIn("MONITOR_ACCESS_TOKEN", os.environ)
        self.assertEqual(am.secret_from_environment("MONITOR_ACCESS_TOKEN"), token, "it can still be read by the monitor")


if __name__ == "__main__":
    unittest.main()
