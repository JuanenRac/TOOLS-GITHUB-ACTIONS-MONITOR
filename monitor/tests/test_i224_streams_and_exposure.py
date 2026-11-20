# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A live stream ends when its session is revoked or expires (looked at again every `auth.stream_revalidate_min` minutes), the monitor asks the search engines to stay out and says what a network
exposure means, and the check of Host and Origin accepts what a proxy such as Caddy or a Cloudflare Tunnel forwards (and nothing else)."""
import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.cli import doctor  # noqa: E402
from github_actions_monitor.security import auth, auth_http, localguard  # noqa: E402


class Headers(dict):
    def get(self, key, default=None):
        for k, v in self.items():
            if k.lower() == key.lower():
                return v
        return default


class FakeHandler:
    def __init__(self, token=None):
        token = auth.TOKEN_PREFIX + "T" * 40 if token is None else token
        self.headers = Headers({"Authorization": "Bearer " + token})
        self.client_address = ("10.0.0.5", 1234)
        self.path = "/api/live-events/stream"


class Revalidate(unittest.TestCase):
    CONFIG = {"auth": {"enabled": True, "allow_bearer": True}}

    def test_a_valid_session_goes_on_a_revoked_one_a_removed_user_and_a_lost_role_end_the_stream(self):
        context = {"user": "ana", "role": "viewer", "accounts": None, "csrf": "x", "kind": "bearer"}
        with mock.patch.object(auth, "get_storage", return_value=object()), mock.patch.object(auth_http, "_users_exist", return_value=True), \
                mock.patch.object(auth, "audit") as audit, mock.patch.object(auth, "find_session", return_value=context):
            self.assertTrue(auth_http.revalidate(FakeHandler(), self.CONFIG, "/api/live-events/stream"))
            with mock.patch.object(auth, "allows", return_value=False):
                self.assertFalse(auth_http.revalidate(FakeHandler(), self.CONFIG, "/api/live-events/stream"))
            with mock.patch.object(auth, "find_session", return_value=None):
                self.assertFalse(auth_http.revalidate(FakeHandler(), self.CONFIG, "/api/live-events/stream"))
                self.assertEqual(audit.call_args[0][1], "stream_closed")
            with mock.patch.object(auth, "find_session", return_value=None):
                self.assertFalse(auth_http.revalidate(FakeHandler(token=""), self.CONFIG))      # no token at all

    def test_there_is_nothing_to_revoke_without_the_team_mode_or_before_the_first_user(self):
        self.assertTrue(auth_http.revalidate(FakeHandler(), {}))
        with mock.patch.object(auth, "get_storage", return_value=object()), mock.patch.object(auth_http, "_users_exist", return_value=False):
            self.assertTrue(auth_http.revalidate(FakeHandler(), self.CONFIG))

    def test_the_guard_of_a_stream_looks_only_every_n_minutes(self):
        handler = actions_monitor.Handler.__new__(actions_monitor.Handler)
        handler.path, handler.headers = "/api/live-events/stream", Headers()
        calls = []
        clock = {"t": 1000.0}
        with mock.patch.object(actions_monitor.time, "time", lambda: clock["t"]), mock.patch.object(auth_http, "revalidate", side_effect=lambda *a: calls.append(1) or len(calls) < 2), \
                mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value={"auth": {"stream_revalidate_min": 5}}):
            stop = handler.stream_guard()
            self.assertFalse(stop())
            clock["t"] += 299
            self.assertFalse(stop())
            self.assertEqual(calls, [], "not looked at before the five minutes")
            clock["t"] += 2
            self.assertFalse(stop())      # looked at: still valid
            clock["t"] += 301
            self.assertTrue(stop())      # looked at again: gone
        self.assertEqual(len(calls), 2)

    def test_the_setting_has_its_default_range_and_help(self):
        self.assertEqual(auth.settings({})["stream_revalidate_min"], 10)
        self.assertEqual(auth.settings({"auth": {"stream_revalidate_min": 0}})["stream_revalidate_min"], 10)
        self.assertEqual(auth.settings({"auth": {"stream_revalidate_min": 30}})["stream_revalidate_min"], 30)
        self.assertIn("auth.stream_revalidate_min", settings_api.FIELDS)
        self.assertEqual(actions_monitor.DEFAULTS["auth"]["stream_revalidate_min"], 10)

    def test_a_stream_is_given_the_guard(self):
        source = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("stop=self.stream_guard()"), 2, "the live events and the AI stream both revalidate")


class NoIndex(unittest.TestCase):
    def serve(self, config):
        server = actions_monitor.QuietServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        for p in (mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=config), mock.patch.object(actions_monitor, "LITE", {"on": False}),
                  mock.patch.dict(actions_monitor.LIVE_CONFIG, config)):
            p.start()
            self.addCleanup(p.stop)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def test_every_answer_says_noindex_and_robots_txt_disallows_everything(self):
        base = self.serve({})
        with urllib.request.urlopen(base + "/api/health", timeout=10) as answer:
            self.assertEqual(answer.headers["X-Robots-Tag"], "noindex, nofollow")
        with urllib.request.urlopen(base + "/robots.txt", timeout=10) as answer:
            self.assertEqual(answer.read().decode(), "User-agent: *\nDisallow: /\n")
            self.assertEqual(answer.headers["X-Robots-Tag"], "noindex, nofollow")

    def test_it_can_be_switched_off(self):
        base = self.serve({"listen": {"noindex": False}})
        with urllib.request.urlopen(base + "/api/health", timeout=10) as answer:
            self.assertIsNone(answer.headers["X-Robots-Tag"])
        with self.assertRaises(urllib.error.HTTPError) as gone:
            urllib.request.urlopen(base + "/robots.txt", timeout=10)
        self.assertEqual(gone.exception.code, 404)
        self.assertFalse(actions_monitor.noindex_on({"listen": {"noindex": False}}))
        self.assertTrue(actions_monitor.noindex_on({"listen": {"noindex": "no"}}))      # only a real false turns it off
        self.assertIn("listen.noindex", settings_api.FIELDS)

    def test_the_exposure_check_says_what_the_exposure_is(self):
        open_ = doctor.exposure_detail({}, {"network": True, "host": "0.0.0.0"})
        self.assertIn("no tls", open_)
        self.assertIn("token only", open_)
        self.assertIn("phishing", open_)
        safe = doctor.exposure_detail({"auth": {"enabled": True}}, {"network": True, "host": "10.0.0.2", "proxy_public_host": "monitor.example.org"})
        self.assertIn("tls", safe)
        self.assertNotIn("no tls", safe)
        self.assertIn("team login", safe)
        self.assertNotIn("phishing", safe)
        self.assertIn("indexable", doctor.exposure_detail({}, {"network": True, "noindex": False}))


class BehindAProxy(unittest.TestCase):
    """Caddy and a Cloudflare Tunnel forward the public name without a port; the same-origin check of the streams and of the actions accepts exactly that name, under HTTPS."""
    PUBLIC = "monitor.example.org"

    def tearDown(self):
        localguard.configure(False)

    def test_caddy_and_the_tunnel_with_the_public_name_are_accepted(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True, proxy_host=self.PUBLIC, trusted_proxy=True)
        for headers in ({"Host": self.PUBLIC}, {"Host": self.PUBLIC, "Origin": "https://" + self.PUBLIC}, {"Host": "127.0.0.1:8765", "Origin": "https://127.0.0.1:8765"}):
            self.assertTrue(localguard.local_request_ok(Headers(headers), 8765), headers)

    def test_another_name_the_other_scheme_or_a_forged_port_are_refused(self):
        localguard.configure(True, "127.0.0.1", "T" * 32, secure=True, proxy_host=self.PUBLIC, trusted_proxy=True)
        for headers in ({"Host": "evil.example.net"}, {"Host": self.PUBLIC, "Origin": "http://" + self.PUBLIC}, {"Host": self.PUBLIC + ":80"}, {"Host": self.PUBLIC, "Origin": "https://evil.example.net"},
                        {"Host": "x." + self.PUBLIC}):
            self.assertFalse(localguard.local_request_ok(Headers(headers), 8765), headers)

    def test_the_new_texts_exist_in_the_eight_languages(self):
        for key in ("cfg.f.auth.stream_revalidate_min", "cfg.h.auth.stream_revalidate_min", "cfg.f.listen.noindex", "cfg.h.listen.noindex"):
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, key), key, (key, lang))


if __name__ == "__main__":
    unittest.main()
