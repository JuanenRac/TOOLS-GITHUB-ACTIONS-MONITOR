# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""One cleaner for everything that leaves the monitor towards an AI: the text the integrated AI sends to a provider, the feed, its state file, the endpoints and the body of the hook all go
through security/redactor.py; and the integrated AI follows no redirect with the key and uses no proxy of the environment."""
import json
import os
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor
from github_actions_monitor.integrations import ai_alerts
from github_actions_monitor.security import netguard, redactor
from github_actions_monitor.sentinels import sentinel_ai

TOKEN = "gh" + "p_abcdefghijklmnopqrstuvwxyz0123456789"
CANARIES = {
    "env": ("DB_PASSWORD=hunter2hunter2", "hunter2hunter2"),
    "json": ('{"password": "hunter2-json"}', "hunter2-json"),
    "url": ("https://deploy:Sup3rS3cret@pypi.interna.example.com/simple", "Sup3rS3cret"),
    "sk": ("key sk-proj-abcdefghijklmnopqrstuvwx", "sk-proj-abcdefghijklmnopqrstuvwx"),
    "aws": ("AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY", "bPxRfiCYEXAMPLEKEY"),
    "jwt": ("token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.abcdefghijk", "eyJzdWIiOiIxMjM0In0"),
    "mail": ("contact victima.canario@corp-ejemplo.com", "victima.canario@corp-ejemplo.com"),
    "ip": ("connect to 10.20.30.40 failed", "10.20.30.40"),
    "home": ("open /home/victima/proyecto/secreto.txt", "/home/victima"),
    "slack": ("POST https://hooks.slack.com/services/T000/B000/XXXXXXXXXXXX", "XXXXXXXXXXXX"),
}


class OneCleanerForTheProvider(unittest.TestCase):
    def test_every_typical_secret_of_a_log_is_cleaned_before_it_reaches_a_provider(self):
        log = "\n".join(text for text, _ in CANARIES.values())
        sent = []

        def transport(cfg, system, user):
            sent.append(user)
            return "the build failed"
        cfg = sentinel_ai.ai_config({"ai": {"provider": "ollama"}})
        with tempfile.TemporaryDirectory() as tmp:
            result = sentinel_ai.explain("build", log, cfg, sentinel_ai.Store(Path(tmp) / "c.json"), transport=transport)
        self.assertTrue(result["ok"], result)
        for name, (_, canary) in CANARIES.items():
            self.assertNotIn(canary, sent[0], name)

    def test_what_the_feed_cleaner_removes_the_provider_path_removes_too(self):
        for name, (text, canary) in CANARIES.items():
            self.assertNotIn(canary, redactor.redact(text), name)
            self.assertNotIn(canary, sentinel_ai.sanitize_text(text, 5000), name)

    def test_the_second_pass_catches_quoted_and_prefixed_keys_too(self):
        for text in ('{"password": "x y z"}', "MYSQL_PWD=abc password='two words'", "client_secret: abc"):
            out = sentinel_ai.sanitize_text(text, 500)
            self.assertNotRegex(out, r"x y z|two words|abc")

    def test_a_secret_inside_a_very_long_log_does_not_survive_the_cut(self):
        log = "x " * 50000 + "DB_PASSWORD=hunter2hunter2\n" + "y " * 10
        out = sentinel_ai.sanitize_text(log, 800)
        self.assertNotIn("hunter2hunter2", out)
        self.assertLessEqual(len(out), 803)

    def test_ai_alerts_keeps_the_names_of_the_cleaner(self):
        self.assertIs(ai_alerts.redact, redactor.redact)
        self.assertIs(ai_alerts.redact_data, redactor.redact_data)

    def test_no_other_module_defines_its_own_list_of_secret_patterns_for_the_ais(self):
        source = Path(redactor.__file__).parent.parent
        owners = [p.name for p in source.rglob("*.py") if re.search(r"^_SECRETS\s*=", p.read_text(encoding="utf-8"), re.M)]
        self.assertEqual(owners, ["redactor.py"])


class EveryOutputForTheAIsIsClean(unittest.TestCase):
    ROW = {"repo": "r1", "workflow": "CI victima.canario@corp-ejemplo.com 10.20.30.40", "conclusion": "failure", "since": None, "streak": 1,
           "url": "https://evil.example/x?token=" + TOKEN}
    CANARIES = ("victima.canario@corp-ejemplo.com", "10.20.30.40", TOKEN)

    def test_the_files_the_endpoints_and_the_body_of_the_hook_carry_no_canary(self):
        sent = []
        with tempfile.TemporaryDirectory() as tmp:
            config = {"ai_alerts": {"enabled": True, "folder": tmp, "hook": {"enabled": True, "url": "http://127.0.0.1:18999/h"}}}
            ai_alerts.HOOK.sent = []
            ai_alerts.update(config, [self.ROW], now=1000.0, opener=lambda request: sent.append(request.data.decode("utf-8")))
            texts = [(Path(tmp) / name).read_text(encoding="utf-8") for name in (ai_alerts.FEED, ai_alerts.STATE, ai_alerts.BRIEF)]
            texts.append(json.dumps(ai_alerts.alerts(config)))
            texts.append(json.dumps(ai_alerts.brief_info(config)))
            texts += sent
        self.assertTrue(sent, "the hook was called")
        for text in texts:
            for canary in self.CANARIES:
                self.assertNotIn(canary, text)

    def test_an_old_state_file_is_cleaned_on_the_way_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {"ai_alerts": {"enabled": True, "folder": tmp}}
            old = {"abc": {"id": "abc", "repo": "r", "workflow": "w victima.canario@corp-ejemplo.com", "state": "open", "class": "real", "first_seen": 5}}
            (Path(tmp) / ai_alerts.STATE).write_text(json.dumps(old), encoding="utf-8")
            self.assertNotIn("victima.canario", json.dumps(ai_alerts.alerts(config)))

    def test_get_ai_state_is_cleaned(self):
        doc = {"schema": 1, "repos": {"errors": [{"repo": "r", "text": "gh: could not read /home/victima/p as victima.canario@corp-ejemplo.com 10.20.30.40"}]}}
        server = actions_monitor.QuietServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        for p in (mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value={}), mock.patch.object(actions_monitor, "LITE", {"on": False}), mock.patch.object(actions_monitor, "ai_state", return_value=doc)):
            p.start()
            self.addCleanup(p.stop)
        body = urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}/api/ai/state", timeout=10).read().decode("utf-8")
        for canary in ("victima.canario", "10.20.30.40", "/home/victima"):
            self.assertNotIn(canary, body)


class _Third(BaseHTTPRequestHandler):
    hits = []

    def do_GET(self):
        _Third.hits.append((self.path, dict(self.headers)))
        self.rfile.read(int(self.headers.get("Content-Length") or 0))      # an unread body makes macOS reset the connection when the double closes it
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_POST = do_GET

    def log_message(self, *args):
        pass


class _Redirecting(BaseHTTPRequestHandler):
    target = ""

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.send_response(302)
        self.send_header("Location", _Redirecting.target)
        self.end_headers()

    def log_message(self, *args):
        pass


def _serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class TheIntegratedAIKeepsTheKeyAndStaysLocal(unittest.TestCase):
    def test_a_redirect_is_not_followed_and_the_key_goes_nowhere_else(self):
        third = _serve(_Third)
        redirecting = _serve(_Redirecting)
        self.addCleanup(third.shutdown)
        self.addCleanup(redirecting.shutdown)
        _Third.hits = []
        _Redirecting.target = f"http://127.0.0.1:{third.server_address[1]}/robbed"
        with self.assertRaises(urllib.error.HTTPError) as caught:
            sentinel_ai._post_json(f"http://127.0.0.1:{redirecting.server_address[1]}/v1/chat", {"a": 1}, {"Authorization": "Bearer canary-key-1234567890"}, 5)
        self.assertEqual(caught.exception.code, 302)
        self.assertEqual(_Third.hits, [])

    def test_the_provider_that_redirects_is_reported_as_an_answer(self):
        redirecting = _serve(_Redirecting)
        self.addCleanup(redirecting.shutdown)
        _Redirecting.target = "http://127.0.0.1:9/x"
        cfg = sentinel_ai.ai_config({"ai": {"provider": "openai-compatible", "base_url": f"http://127.0.0.1:{redirecting.server_address[1]}", "model": "m"}})
        with self.assertRaises(RuntimeError) as caught:
            sentinel_ai.openai_compatible_chat(cfg, "s", "u")
        self.assertIn("302", str(caught.exception))

    def test_a_local_provider_never_goes_through_the_proxy_of_the_environment(self):
        proxy = _serve(_Third)
        local = _serve(_Third)
        self.addCleanup(proxy.shutdown)
        self.addCleanup(local.shutdown)
        _Third.hits = []
        env = {"http_proxy": f"http://127.0.0.1:{proxy.server_address[1]}", "HTTP_PROXY": f"http://127.0.0.1:{proxy.server_address[1]}", "no_proxy": "", "NO_PROXY": ""}
        with mock.patch.dict(os.environ, env):
            cfg = sentinel_ai.ai_config({"ai": {"provider": "ollama", "ollama_url": f"http://localhost:{local.server_address[1]}"}})
            try:
                sentinel_ai._post_json(cfg["ollama_url"] + "/api/chat", {}, {}, 5)
            except ValueError:
                pass      # the double answers with an empty body: only the route matters
        self.assertEqual([h for h in _Third.hits], [(("/api/chat"), _Third.hits[0][1])])
        self.assertIn("localhost", _Third.hits[0][1].get("Host", ""))
        self.assertEqual(len(_Third.hits), 1, "the request arrived once, at the local server, not at the proxy")

    def test_use_proxy_comes_from_the_network_setting_and_is_off_by_default(self):
        self.assertFalse(sentinel_ai.ai_config({})["use_proxy"])
        self.assertTrue(sentinel_ai.ai_config({"network": {"use_proxy": True}})["use_proxy"])
        self.assertFalse(sentinel_ai.ai_config({"network": {"use_proxy": "yes"}})["use_proxy"])

    def test_no_urlopen_outside_the_guarded_modules_of_the_integrated_ai(self):
        text = Path(sentinel_ai.__file__).read_text(encoding="utf-8")
        self.assertNotIn("urlopen(", text)
        self.assertTrue(hasattr(netguard, "open_plain"))


if __name__ == "__main__":
    unittest.main()
