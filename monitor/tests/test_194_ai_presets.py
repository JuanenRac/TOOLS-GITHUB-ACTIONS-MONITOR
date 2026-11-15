# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.9.4: presets of AI providers (a versioned file of data), a local server without a key, and the real transport against a fake server with the OpenAI protocol
(answers 200, 401, 429 and a timeout). The key is never in a log, a report, the answer of the API or the cache."""
import json
import os
import re
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import settings_api
from github_actions_monitor.sentinels import ai_presets
from github_actions_monitor.sentinels import sentinel_ai as ai

KEY = "sk-test-" + "Z" * 30
HOSTED = {"openai", "anthropic", "gemini", "xai", "mistral", "deepseek", "groq", "openrouter", "together", "fireworks", "perplexity", "cohere"}
LOCAL = {"ollama", "lmstudio", "llamacpp", "vllm", "localai", "jan"}


class Fake(BaseHTTPRequestHandler):
    mode = "ok"
    seen = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        Fake.seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": json.loads(self.rfile.read(length) or b"{}")})
        if Fake.mode == "timeout":
            threading.Event().wait(3)
            return
        code = {"ok": 200, "401": 401, "429": 429}[Fake.mode]
        body = json.dumps({"choices": [{"message": {"content": "ok"}}]} if code == 200 else {"error": {"message": "echo " + KEY}}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class PresetFile(unittest.TestCase):
    def test_the_file_is_valid_and_complete(self):
        data = json.loads(ai_presets.PATH.read_text(encoding="utf-8"))
        self.assertEqual(ai_presets.problems(data), [])
        ids = {p["id"] for p in data["presets"]}
        self.assertEqual(ids, HOSTED | LOCAL)
        self.assertEqual({p["id"] for p in ai_presets.load()}, ids)

    def test_nothing_is_tested_and_no_key_is_stored(self):
        for p in ai_presets.load():
            self.assertFalse(p["tested"], p["id"])
            self.assertRegex(p["api_key_env"], r"^[A-Z_]*\Z")
            self.assertFalse(re.search(r"(sk-|ghp_|AKIA)", json.dumps(p)), p["id"])
            self.assertEqual(p["privacy"], "local" if p["id"] in LOCAL else "cloud")

    def test_a_bad_preset_is_found(self):
        base = {"id": "x1", "kind": "hosted", "provider": "openai-compatible", "base_url": "http://example.com/v1", "api_key_env": "sk-abc def", "models": [],
                "privacy": "cloud", "checked": False, "tested": False}
        found = ai_presets.problems({"presets": [base]})
        self.assertGreaterEqual(len(found), 3)

    def test_changes_hold_no_key_and_every_value_passes_the_settings_check(self):
        for p in ai_presets.load():
            changes = ai_presets.changes_for(p["id"])
            self.assertEqual(changes["ai.provider"], p["provider"])
            self.assertNotIn("key", " ".join(k for k in changes if k != "ai.api_key_env"))
            self.assertRegex(changes["ai.base_url"], settings_api.AI_URL_RE.pattern)
            self.assertRegex(changes["ai.model"], settings_api.MODEL_RE.pattern)
            self.assertRegex(changes["ai.api_key_env"], settings_api.ENV_NAME_RE.pattern)
        self.assertIsNone(ai_presets.changes_for("nope"))

    def test_the_address_of_a_preset_can_be_saved_but_a_plain_http_one_cannot(self):
        self.assertTrue(settings_api.AI_URL_RE.match("http://127.0.0.1:1234/v1"))
        self.assertFalse(settings_api.AI_URL_RE.match("http://example.com/v1"))
        self.assertFalse(settings_api.HTTPS_RE.match("http://127.0.0.1:1234/v1"))


class Protocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Fake)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Fake.mode, Fake.seen = "ok", []
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.store = ai.Store(Path(self.dir.name) / "c.json")
        env = mock.patch.dict(os.environ, {"FAKE_AI_KEY": KEY})
        env.start()
        self.addCleanup(env.stop)

    def cfg(self, **extra):
        return ai.ai_config({"ai": {"provider": "openai-compatible", "base_url": f"http://127.0.0.1:{self.port}/v1", "model": "m", "api_key_env": "FAKE_AI_KEY",
                                    "timeout_seconds": 1, "daily_limit": 50, **extra}})

    def test_answers_and_sends_the_key_only_as_a_header(self):
        result = ai.test_connection(self.cfg(), self.store)
        self.assertTrue(result["ok"], result)
        self.assertEqual(Fake.seen[0]["path"], "/v1/chat/completions")
        self.assertEqual(Fake.seen[0]["auth"], "Bearer " + KEY)
        self.assertNotIn(KEY, json.dumps(result))
        self.assertNotIn(KEY, json.dumps(Fake.seen[0]["body"]))

    def test_rejected_key_rate_limit_and_timeout_never_show_the_key(self):
        for mode in ("401", "429", "timeout"):
            Fake.mode = mode
            result = ai.test_connection(self.cfg(), self.store)
            self.assertFalse(result["ok"], mode)
            self.assertNotIn(KEY, json.dumps(result), mode)
            self.assertTrue(result["error"], mode)
            explained = ai.explain("build", "log text", self.cfg(), self.store)
            self.assertFalse(explained["ok"], mode)
            self.assertNotIn(KEY, json.dumps(explained), mode)
        self.assertNotIn(KEY, Path(self.store.path).read_text(encoding="utf-8") if Path(self.store.path).exists() else "")

    def test_a_local_server_works_without_a_key_and_sends_no_authorization(self):
        cfg = self.cfg(api_key_env="")
        self.assertIsNone(ai.compat_problem(cfg))
        self.assertTrue(ai.test_connection(cfg, self.store)["ok"])
        self.assertIsNone(Fake.seen[0]["auth"])

    def test_a_remote_server_still_needs_its_key(self):
        cfg = self.cfg(base_url="https://api.example.com/v1", api_key_env="")
        self.assertIsNotNone(ai.compat_problem(cfg))
        self.assertIsNotNone(ai.compat_problem(self.cfg(api_key_env="NOT_SET_ANYWHERE")))


if __name__ == "__main__":
    unittest.main()
