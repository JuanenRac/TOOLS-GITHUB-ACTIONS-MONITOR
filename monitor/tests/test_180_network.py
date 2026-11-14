# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The network mode against a real server and a client that is NOT on loopback (the peer address is set by the handler, so nothing here needs a second network card):
the lock comes before the token for every address that is not this computer, a declared proxy makes loopback stop meaning "this computer", the settings a client of the network
cannot change are not read by it either, and every route that is "this computer only" says 403 to a client of the network."""
import http.client
import json
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor, settings_api
from github_actions_monitor.security import localguard

TOKEN = "T" * 24
REMOTE_IP = "203.0.113.9"
SOURCE = Path(actions_monitor.__file__).read_text(encoding="utf-8")


def handler_for(peer_ip, door=False):
    base = actions_monitor.LocalDoorHandler if door else actions_monitor.Handler

    class Peer(base):
        def setup(self):
            super().setup()
            self.client_address = (peer_ip, self.client_address[1])

    return Peer


class Running:
    """A real server of the monitor on an ephemeral loopback port whose connections claim to come from `peer_ip`."""

    def __init__(self, case, peer_ip=REMOTE_IP, door=False):
        self.server = actions_monitor.QuietServer(("127.0.0.1", 0), handler_for(peer_ip, door))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        case.addCleanup(self.server.server_close)
        case.addCleanup(self.server.shutdown)
        self.port = self.server.server_address[1]

    def call(self, method, path, body=None, headers=None, token=TOKEN):
        sent = {"Host": f"127.0.0.1:{self.port}", **({"X-Monitor-Access": token} if token else {}), **(headers or {})}
        if body is not None:
            sent.setdefault("Content-Type", "application/json")
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        try:
            connection.request(method, path, None if body is None else json.dumps(body), sent)
            answer = connection.getresponse()
            raw = answer.read()
        finally:
            connection.close()
        try:
            return answer.status, json.loads(raw)
        except ValueError:
            return answer.status, raw


class NetworkCase(unittest.TestCase):
    def setUp(self):
        _testenv.guard(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = Path(self.tmp.name) / "actions_monitor.json"
        self.config.write_text("{}", encoding="utf-8")
        for target, name, value in ((actions_monitor, "CONFIG_FILE", self.config), (settings_api, "CONFIG_FILE", self.config), (settings_api, "BACKUP_DIR", Path(self.tmp.name) / "b")):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(actions_monitor, "token_required", return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        localguard.reset_limits()
        self.addCleanup(localguard.reset_limits)
        self.addCleanup(localguard.configure, False)
        localguard.configure(True, "127.0.0.1", TOKEN, ())


class TheLockComesBeforeTheToken(NetworkCase):
    def guess(self, running, token):
        return running.call("GET", "/api/health", token=token)[0]

    def test_a_locked_address_cannot_keep_guessing_and_cannot_get_in_with_the_right_token(self):
        remote = Running(self)
        self.assertEqual([self.guess(remote, f"wrong-{i}") for i in range(10)][-1], 401)
        self.assertTrue(localguard.is_locked(REMOTE_IP), "ten wrong tokens lock the address")
        during = {self.guess(remote, f"dictionary-word-{i}") for i in range(30)}
        self.assertEqual(during, {429}, "during the lock every guess is refused without being judged")
        self.assertEqual(self.guess(remote, TOKEN), 429, "not even the right token gets in while the address is locked")

    def test_the_header_and_the_post_that_opens_the_session_follow_the_same_rule(self):
        remote = Running(self)
        for i in range(10):
            self.guess(remote, f"wrong-{i}")
        by_header = self.guess(remote, TOKEN)
        by_post = remote.call("POST", "/api/access", {"token": TOKEN}, token="")[0]
        self.assertEqual((by_header, by_post), (429, 429))

    def test_the_person_at_this_computer_is_never_locked_out_of_their_own_monitor(self):
        local = Running(self, peer_ip="127.0.0.1")
        for i in range(15):
            self.assertEqual(self.guess(local, f"wrong-{i}"), 401, "wrong tokens from this computer are refused but never lock it")
        self.assertEqual(self.guess(local, TOKEN), 200)
        self.assertEqual(local.call("POST", "/api/access", {"token": TOKEN}, token="")[0], 200)

    def test_after_the_lock_ends_the_right_token_works_again(self):
        remote = Running(self)
        for i in range(10):
            self.guess(remote, f"wrong-{i}")
        with mock.patch.object(localguard.time, "time", return_value=localguard.time.time() + localguard.LOCKOUT_SECONDS + 5):
            self.assertEqual(self.guess(remote, TOKEN), 200)


class ADeclaredProxyMakesLoopbackStopMeaningThisComputer(NetworkCase):
    def declare(self, **kwargs):
        localguard.configure(True, "127.0.0.1", TOKEN, (), secure=True, proxy_host="monitor.example", **kwargs)

    def test_without_a_proxy_declared_loopback_is_this_computer(self):
        running = Running(self, peer_ip="127.0.0.1")
        self.assertEqual(running.call("POST", "/api/ai/test", {})[1].get("errors", {}).get("_"), None)

    def test_the_documented_recipe_without_forwarding_headers_is_no_longer_this_computer(self):
        self.declare()
        loopback = Running(self, peer_ip="127.0.0.1")      # nginx: proxy_pass to 127.0.0.1 and Host rewritten to 127.0.0.1:PORT, no X-Forwarded-For at all
        for path in ("/api/ai/test", "/api/alerts/mute"):
            status, answer = loopback.call("POST", path, {})
            self.assertEqual((status, answer["errors"]["_"]), (403, "local_only"), path)
        self.assertEqual(loopback.call("GET", "/api/quota-pool/status")[0], 403)

    def test_each_kind_of_declared_proxy_counts(self):
        for kwargs in ({"proxy_host": "monitor.example"}, {"behind_proxy": True}, {"trusted_proxy": True}):
            localguard.configure(True, "127.0.0.1", TOKEN, (), **kwargs)
            self.assertTrue(localguard.STATE["behind_proxy"], kwargs)
            self.assertFalse(localguard.is_this_computer(("127.0.0.1", 1), {}), kwargs)
            self.assertTrue(localguard.is_this_computer(("127.0.0.1", 1), {}, door=True), kwargs)
        localguard.configure(True, "127.0.0.1", TOKEN, ())
        self.assertFalse(localguard.STATE["behind_proxy"])
        self.assertTrue(localguard.is_this_computer(("127.0.0.1", 1), {}))
        localguard.configure(False, proxy_host="monitor.example", trusted_proxy=True)
        self.assertFalse(localguard.STATE["behind_proxy"], "without the network mode there is no proxy to declare")

    def test_the_second_port_that_only_listens_on_loopback_is_the_way_in_of_the_owner(self):
        self.declare()
        door = Running(self, peer_ip="127.0.0.1", door=True)
        status, answer = door.call("POST", "/api/ai/test", {})
        self.assertNotEqual(answer.get("errors", {}).get("_") if isinstance(answer.get("errors"), dict) else None, "local_only")
        self.assertEqual(door.call("GET", "/api/quota-pool/status")[0], 200)
        self.assertEqual(door.call("GET", "/api/health", headers={"Host": "monitor.example"})[0], 403, "the public name is not a name of the local port")
        self.assertEqual(door.call("GET", "/api/health", headers={"Origin": "https://monitor.example"})[0], 403)
        self.assertEqual(door.call("GET", "/api/health", headers={"Origin": f"http://127.0.0.1:{door.port}"})[0], 200, "plain HTTP: the page of the local port is not HTTPS")
        self.assertEqual(door.call("GET", "/api/health", headers={"X-Forwarded-For": "198.51.100.7"})[0], 200)
        self.assertEqual(door.call("POST", "/api/ai/test", {}, headers={"X-Forwarded-For": "198.51.100.7"})[1]["errors"]["_"], "local_only", "a forwarded request is never this computer, not even on the local port")
        self.assertEqual(door.call("GET", "/api/health", token="bad")[0], 401, "the local port still asks for the token")

    def test_the_cookie_of_the_local_port_is_not_marked_secure_but_the_one_of_the_proxy_is(self):
        self.assertIn("Secure", localguard.cookie_header("x", secure=True))
        self.assertNotIn("Secure", localguard.cookie_header("x", secure=False))
        self.declare()
        self.assertIn("Secure", localguard.cookie_header("x"))

    def test_the_local_port_is_a_setting_off_by_default(self):
        self.assertEqual(localguard.settings_from({})["local_port"], 0)
        self.assertEqual(localguard.settings_from({"listen": {"local_port": 18899}})["local_port"], 18899)
        for bad in (80, 70000, "18899", True, -1, 1.5):
            self.assertEqual(localguard.settings_from({"listen": {"local_port": bad}})["local_port"], 0, bad)
        self.assertEqual(actions_monitor.DEFAULTS["listen"]["local_port"], 0)
        self.assertIn("listen.local_port", settings_api.FIELDS)
        self.assertTrue(localguard.local_only_key("listen.local_port"))

    def test_a_proxy_that_does_not_add_the_header_cannot_be_used_to_rotate_the_address(self):
        self.declare(trusted_proxy=True)
        loopback = Running(self, peer_ip="127.0.0.1")
        codes = [loopback.call("GET", "/api/health", headers={"Host": "monitor.example", "X-Forwarded-For": f"203.0.113.{i % 250 + 1}"}, token="bad")[0] for i in range(40)]
        self.assertIn(429, codes, "the clients of the proxy are also counted together")
        self.assertEqual(loopback.call("GET", "/api/health", headers={"Host": "monitor.example", "X-Forwarded-For": "198.51.100.77"})[0], 429)

    def test_one_person_still_does_not_lock_the_others_behind_a_trusted_proxy(self):
        self.declare(trusted_proxy=True)
        loopback = Running(self, peer_ip="127.0.0.1")
        for _ in range(10):
            loopback.call("GET", "/api/health", headers={"Host": "monitor.example", "X-Forwarded-For": "198.51.100.7"}, token="bad")
        self.assertTrue(localguard.is_locked("fwd:198.51.100.7"))
        self.assertEqual(loopback.call("GET", "/api/health", headers={"Host": "monitor.example", "X-Forwarded-For": "198.51.100.8"})[0], 200)


class TheSettingsAClientOfTheNetworkCannotChangeAreNotReadByItEither(NetworkCase):
    def setUp(self):
        super().setUp()
        self.config.write_text(json.dumps({"github_app": {"key_path": "/home/owner/SECRET_APP_KEY.pem"}, "extra_reader": {"file": "/home/owner/SECOND_ACCOUNT_TOKEN"},
                                           "workspace_root": "/home/owner/WORKSPACE_ROOT", "mirror": {"folder": "/home/owner/MY_TELEGRAM_VAR"}, "refresh_seconds": 77}), encoding="utf-8")

    def fields(self, answer):
        return {f["key"]: f for g in answer["groups"] for f in g["fields"]}

    def test_a_remote_client_gets_values_only_for_the_short_list_and_defined_yes_or_no_for_the_rest(self):
        status, answer = Running(self).call("GET", "/api/settings")
        self.assertEqual(status, 200)
        text = json.dumps(answer)
        for secret in ("SECRET_APP_KEY", "SECOND_ACCOUNT_TOKEN", "WORKSPACE_ROOT", "MY_TELEGRAM_VAR"):
            self.assertNotIn(secret, text, secret)
        fields = self.fields(answer)
        self.assertEqual(fields["refresh_seconds"]["value"], 77, "what a client of the network may change is shown")
        hidden = [f for key, f in fields.items() if key not in localguard.REMOTE_WRITABLE]
        self.assertTrue(hidden)
        for field in hidden:
            self.assertTrue(field.get("redacted"), field["key"])
            self.assertEqual(field["type"], "status", field["key"])
            self.assertIn(field["value"], ("defined", "undefined"), field["key"])
        self.assertEqual(fields["workspace_root"]["value"], "defined")

    def test_this_computer_gets_every_value(self):
        status, answer = Running(self, peer_ip="127.0.0.1").call("GET", "/api/settings")
        text = json.dumps(answer)
        self.assertEqual(status, 200)
        for shown in ("SECRET_APP_KEY", "WORKSPACE_ROOT", "MY_TELEGRAM_VAR"):
            self.assertIn(shown, text, shown)
        self.assertFalse([f for f in self.fields(answer).values() if f.get("redacted")])

    def test_without_the_network_mode_everything_is_shown(self):
        localguard.configure(False)
        self.assertIn("WORKSPACE_ROOT", json.dumps(settings_api.describe(self.config)))

    def test_describe_marks_nothing_for_a_local_asker(self):
        fields = self.fields(settings_api.describe(self.config, remote=False))
        self.assertFalse([f for f in fields.values() if f.get("redacted")])
        remote = self.fields(settings_api.describe(self.config, remote=True))
        self.assertEqual(set(fields), set(remote), "the same fields, only the values differ")


#: every route that answers 403 "local_only" to a client of the network (the keys, the actions on GitHub, the tests of channels, the state of the pool and of the App)
LOCAL_ONLY_POST = ("/api/ai/actions/confirm", "/api/ai/actions/unlock", "/api/ai/test", "/api/notify/test", "/api/gh-action/plan", "/api/gh-action/confirm", "/api/act/plan",
                   "/api/act/confirm", "/api/act/stop", "/api/github-token", "/api/welcome", "/api/ai/ack", "/api/alerts/mute", "/api/alerts/unmute", "/api/credential")
LOCAL_ONLY_GET = ("/api/quota-pool/status", "/api/github-app/status")


class EveryLocalOnlyRouteRefusesAClientOfTheNetwork(NetworkCase):
    def test_the_table_is_walked_against_a_real_server(self):
        remote = Running(self)
        for path in LOCAL_ONLY_POST:
            status, answer = remote.call("POST", path, {})
            self.assertEqual((status, answer.get("errors", {}).get("_")), (403, "local_only"), path)
        for path in LOCAL_ONLY_GET:
            status, answer = remote.call("GET", path)
            self.assertEqual((status, answer.get("errors", {}).get("_")), (403, "local_only"), path)
        status, answer = remote.call("POST", "/api/settings", {"changes": {"workspace_root": "/tmp/x"}})
        self.assertEqual((status, answer["errors"]["_"]), (403, "local_only"))
        self.assertEqual(self.config.read_text(encoding="utf-8"), "{}", "nothing was written")

    def test_the_same_routes_answer_to_this_computer(self):
        local = Running(self, peer_ip="127.0.0.1")
        for path in LOCAL_ONLY_GET:
            status, answer = local.call("GET", path)
            self.assertEqual(status, 200, path)

    def test_the_table_lists_every_route_that_asks_for_this_computer(self):
        found = set()
        for match in re.finditer(r'(?:path == "([^"]+)"|path in \(([^)]*)\)):[^\n]*\n\s+if not self\.guard\(\) or not self\.this_computer\(\)', SOURCE):
            found.update([match.group(1)] if match.group(1) else re.findall(r'"([^"]+)"', match.group(2)))
        self.assertEqual(found, set(LOCAL_ONLY_POST) | set(LOCAL_ONLY_GET), "a new route that is local only goes in the table (and a route that stops being local only must be taken out on purpose)")
        self.assertEqual(SOURCE.count("self.this_computer()"), 5, "a new call to this_computer() needs its row in the table above")


if __name__ == "__main__":
    unittest.main()
