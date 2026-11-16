# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The models of the AI provider: the live list (three protocols, against a fake local server), the check of the name, the table of data per model (nothing invented), the test of one model with a
synthetic text, the doctor and the command line. No network beyond 127.0.0.1; the key never appears in an answer, a cache or a table."""
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor, settings_api
from github_actions_monitor.cli import monitor_cli
from github_actions_monitor.sentinels import ai_models, sentinel_ai as ai

KEY = "sk-test-" + "Q" * 30


class Fake(BaseHTTPRequestHandler):
    mode = "ok"
    seen = []

    def _send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        Fake.seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "x": self.headers.get("x-api-key")})
        if Fake.mode in ("401", "404", "429"):
            return self._send(int(Fake.mode), {"error": {"message": "echo " + KEY}})
        if self.path.startswith("/v1/models") and self.headers.get("x-api-key"):
            return self._send(200, {"data": [{"id": "alpha-1", "max_input_tokens": 200000, "capabilities": {"tools": {"supported": True}}}, {"id": "alpha-2"}], "has_more": False})
        if self.path == "/v1/models":
            return self._send(200, {"data": [{"id": "gpt-small", "context_length": 128000, "pricing": {"prompt": "0.0000005", "completion": "0.0000015"}},
                                             {"id": "models/gem-1"}, {"id": "bad name with spaces"}, {"id": "gpt-small"}, 7]})
        if self.path == "/api/tags":
            return self._send(200, {"models": [{"name": "llama3.2:latest"}, {"name": "qwen2.5:7b"}]})
        self._send(404, {})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        Fake.seen.append({"path": self.path, "body": json.loads(self.rfile.read(length) or b"{}")})
        usage = {"prompt_tokens": 120, "completion_tokens": 30} if Fake.mode == "usage" else {}
        self._send(200, {"choices": [{"message": {"content": "The test fails: expected 3, got 2. See https://example.com/x"}}], "usage": usage})

    def log_message(self, *a):
        pass


class Base(unittest.TestCase):
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

    def compat(self, **extra):
        return ai.ai_config({"ai": {"provider": "openai-compatible", "base_url": f"http://127.0.0.1:{self.port}/v1", "model": "gpt-small", "api_key_env": "FAKE_AI_KEY", "timeout_seconds": 5,
                                    "daily_limit": 50, **extra}})

    def ollama(self, **extra):
        return ai.ai_config({"ai": {"provider": "ollama", "ollama_url": f"http://127.0.0.1:{self.port}", "model": "llama3.2", "timeout_seconds": 5, **extra}})

    def anthropic(self, **extra):
        return ai.ai_config({"ai": {"provider": "anthropic", "base_url": f"http://127.0.0.1:{self.port}", "model": "alpha-1", "api_key_env": "FAKE_AI_KEY", "timeout_seconds": 5, **extra}})


class Catalog(Base):
    def test_openai_style_list_keeps_only_valid_names_and_what_the_provider_says(self):
        answer = ai_models.fetch(self.compat(), self.store)
        self.assertTrue(answer["ok"], answer)
        self.assertEqual([m["id"] for m in answer["models"]], ["gem-1", "gpt-small"])      # the "models/" prefix is dropped, a bad name and a repeated one are not kept
        small = next(m for m in answer["models"] if m["id"] == "gpt-small")
        self.assertEqual((small["context"], small["in_per_mtok"], small["out_per_mtok"], small["tools"]), (128000, 0.5, 1.5, None))
        gem = next(m for m in answer["models"] if m["id"] == "gem-1")
        self.assertEqual((gem["context"], gem["in_per_mtok"], gem["out_per_mtok"]), (None, None, None))      # what is not said stays unknown
        self.assertEqual(Fake.seen[0]["path"], "/v1/models")
        self.assertEqual(Fake.seen[0]["auth"], "Bearer " + KEY)

    def test_ollama_and_anthropic_lists(self):
        local = ai_models.fetch(self.ollama(), self.store)
        self.assertEqual([m["id"] for m in local["models"]], ["llama3.2:latest", "qwen2.5:7b"])
        self.assertEqual(ai_models.check_model(self.ollama(), local["models"])["state"], "exists")      # "llama3.2" is "llama3.2:latest"
        cloud = ai_models.fetch(self.anthropic(), self.store)
        self.assertTrue(cloud["ok"], cloud)
        self.assertEqual(Fake.seen[-1]["x"], KEY)
        first = cloud["models"][0]
        self.assertEqual((first["id"], first["context"], first["tools"]), ("alpha-1", 200000, True))

    def test_the_list_is_kept_and_the_cap_of_requests_is_respected(self):
        cfg = self.compat(catalog={"max_requests_per_day": 2})
        self.assertEqual(ai_models.fetch(cfg, self.store, force=False)["state"], "fresh")
        self.assertEqual(ai_models.fetch(cfg, self.store, force=False)["state"], "cached")      # fresh: no new request
        self.assertEqual(len([s for s in Fake.seen if s["path"] == "/v1/models"]), 1)
        self.assertTrue(ai_models.fetch(cfg, self.store, force=True)["ok"])
        capped = ai_models.fetch(cfg, self.store, force=True)
        self.assertEqual(capped["state"], "capped")
        self.assertEqual(len(capped["models"]), 2)      # the list kept is still given
        self.assertEqual(len([s for s in Fake.seen if s["path"] == "/v1/models"]), 2)

    def test_errors_never_show_the_key_and_keep_the_old_list(self):
        cfg = self.compat()
        ai_models.fetch(cfg, self.store)
        for mode, code in (("401", 401), ("404", 404), ("429", 429)):
            Fake.mode = mode
            answer = ai_models.fetch(cfg, self.store, force=True)
            self.assertFalse(answer["ok"])
            self.assertEqual(answer["code"], code)
            self.assertNotIn(KEY, json.dumps(answer))
            self.assertEqual(len(answer["models"]), 2)
        self.assertNotIn(KEY, json.dumps(self.store.data))

    def test_no_provider_copilot_and_a_missing_key_make_no_request(self):
        self.assertEqual(ai_models.fetch(ai.ai_config({}), self.store)["state"], "off")
        self.assertEqual(ai_models.fetch(ai.ai_config({"ai": {"provider": "copilot"}}), self.store)["state"], "unsupported")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FAKE_AI_KEY", None)
            answer = ai_models.fetch(self.compat(base_url="https://api.example.com/v1"), self.store)
        self.assertFalse(answer["ok"])
        self.assertEqual(Fake.seen, [])

    def test_the_catalog_settings_are_clamped_and_off_by_default(self):
        self.assertFalse(ai_models.catalog_config(ai.ai_config({}))["enabled"])
        cfg = ai_models.catalog_config({"catalog": {"enabled": "yes", "ttl_minutes": 1, "max_requests_per_day": "x"}})
        self.assertEqual((cfg["enabled"], cfg["ttl_minutes"], cfg["max_requests_per_day"]), (False, 5, 20))
        for key in ("ai.catalog.enabled", "ai.catalog.ttl_minutes", "ai.catalog.max_requests_per_day", "ai.catalog.fit_context"):
            self.assertIn(key, settings_api.FIELDS)


class Validation(Base):
    def test_exists_missing_unknown_and_similar_names(self):
        models = [{"id": "gpt-small"}, {"id": "gpt-large"}]
        self.assertEqual(ai_models.check_model(self.compat(), models)["state"], "exists")
        missing = ai_models.check_model(self.compat(model="gpt-smal"), models)
        self.assertEqual(missing["state"], "missing")
        self.assertIn("gpt-small", missing["similar"])
        self.assertEqual(ai_models.check_model(self.compat(), None)["state"], "unknown")      # no list = not "missing"
        self.assertEqual(ai_models.check_model(self.compat(model=""), models)["state"], "unknown")
        self.assertEqual(ai_models.check_model(self.compat(model="models/gpt-small"), models)["state"], "exists")

    def test_the_configured_model_is_only_checked_in_the_background_when_the_option_is_on(self):
        ai_models.fetch(self.compat(model="gone"), self.store)
        self.assertEqual(ai_models.state_of_configured(self.compat(model="gone"), self.store)["state"], "off")
        state = ai_models.state_of_configured(self.compat(model="gone", catalog={"enabled": True}), self.store)
        self.assertEqual(state["state"], "missing")
        self.assertIn("gone", state["message"])
        self.assertEqual(ai.status(self.compat(model="gone", catalog={"enabled": True}), self.store)["catalog"]["state"], "missing")
        self.assertEqual(len([s for s in Fake.seen if s["path"] == "/v1/models"]), 1)      # the status never asks the provider


class Table(Base):
    def test_the_provider_fills_the_table_and_what_you_type_wins(self):
        ai_models.fetch(self.compat(), self.store)
        row = ai_models.data_of(self.store, "127.0.0.1", "gpt-small")
        self.assertEqual((row["context"], row["context_source"], row["in_per_mtok"]), (128000, "provider", 0.5))
        ok, _ = ai_models.set_manual(self.store, "127.0.0.1", "gpt-small", {"context": 64000, "in_per_mtok": 2, "tools": True})
        self.assertTrue(ok)
        ai_models.fetch(self.compat(), self.store, force=True)      # a second read never overwrites a typed value
        row = ai_models.data_of(self.store, "127.0.0.1", "gpt-small")
        self.assertEqual((row["context"], row["context_source"], row["in_per_mtok"], row["tools"]), (64000, "manual", 2.0, True))
        self.assertEqual((row["out_per_mtok"], row["out_per_mtok_source"]), (1.5, "provider"))
        ai_models.set_manual(self.store, "127.0.0.1", "gpt-small", {"context": ""})      # empty = back to what the provider says
        self.assertEqual(ai_models.data_of(self.store, "127.0.0.1", "gpt-small")["context"], 128000)

    def test_unknown_stays_unknown_and_bad_values_are_refused(self):
        row = ai_models.data_of(self.store, "127.0.0.1", "never-seen")
        self.assertTrue(all(row[f] is None and row[f + "_source"] == "unknown" for f in ai_models.FIELDS))
        self.assertIsNone(ai_models.cost_of(self.store, "127.0.0.1", "never-seen", 1000, 1000))
        for values in ({"context": -1}, {"context": "abc"}, {"in_per_mtok": -3}, {"tools": "yes"}, {"in_per_mtok": True}):
            self.assertFalse(ai_models.set_manual(self.store, "127.0.0.1", "m", values)[0], values)
        self.assertFalse(ai_models.set_manual(self.store, "127.0.0.1", "bad name", {"context": 5})[0])
        self.assertEqual(ai_models.table(self.store), [])

    def test_the_input_is_fitted_to_the_window_only_when_asked_and_only_downwards(self):
        ai_models.fetch(self.compat(), self.store)      # gpt-small: 128000 tokens
        ai_models.set_manual(self.store, "127.0.0.1", "gpt-small", {"context": 2000})
        cfg = self.compat(max_input_chars=5000)
        self.assertEqual(ai_models.fit_chars(cfg, self.store), 5000)      # off: your value
        self.assertEqual(ai_models.fit_chars(self.compat(max_input_chars=5000, catalog={"fit_context": True}), self.store), 3000)
        ai_models.set_manual(self.store, "127.0.0.1", "gpt-small", {"context": 100000})
        self.assertEqual(ai_models.fit_chars(self.compat(max_input_chars=5000, catalog={"fit_context": True}), self.store), 5000)      # never above your limit
        self.assertEqual(ai_models.fit_chars(self.compat(model="other", catalog={"fit_context": True}), self.store), 5000)      # unknown window: your limit


class Probe(Base):
    def test_a_test_uses_a_synthetic_text_measures_and_keeps_the_result(self):
        result = ai_models.probe(self.compat(), self.store)
        self.assertTrue(result["ok"], result)
        sent = json.dumps(Fake.seen[-1]["body"])
        self.assertIn("example/demo-app", sent)
        self.assertNotIn(KEY, sent)
        self.assertTrue(result["tokens_estimated"])
        self.assertIsNone(result["cost"])      # no prices known: no cost
        self.assertNotIn("https://example.com", result["answer"])      # links are defused
        self.assertEqual(self.store.used_today(), 1)
        row = ai_models.data_of(self.store, "127.0.0.1", "gpt-small")
        self.assertTrue(row["tested"]["ok"])
        self.assertRegex(row["tested"]["at"], r"^\d{4}-\d\d-\d\d \d\d:\d\d$")

    def test_reported_tokens_and_a_known_price_give_a_cost(self):
        ai_models.set_manual(self.store, "127.0.0.1", "gpt-small", {"in_per_mtok": 1, "out_per_mtok": 2})
        Fake.mode = "usage"
        result = ai_models.probe(self.compat(), self.store)
        self.assertFalse(result["tokens_estimated"])
        self.assertEqual((result["tokens_in"], result["tokens_out"]), (120, 30))
        self.assertAlmostEqual(result["cost"], 120 / 1e6 + 60 / 1e6, places=9)

    def test_the_daily_cap_and_a_failing_provider_are_reported_not_raised(self):
        cfg = self.compat(daily_limit=1)
        self.assertTrue(ai_models.probe(cfg, self.store)["ok"])
        second = ai_models.probe(cfg, self.store)
        self.assertFalse(second["ok"])
        self.assertTrue(second["error"])
        self.assertEqual(len([s for s in Fake.seen if s["path"].endswith("completions")]), 1)
        self.assertFalse(ai_models.probe(ai.ai_config({}), self.store)["ok"])


class Doctor(Base):
    def test_every_cause_is_named_and_a_key_is_never_printed(self):
        none = ai_models.doctor(ai.ai_config({}), self.store)
        self.assertEqual(none["verdict"], "provider")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FAKE_AI_KEY", None)
            nokey = ai_models.doctor(self.compat(base_url="https://api.example.com/v1"), self.store, live=False)
        self.assertEqual(nokey["verdict"], "key")
        gone = ai_models.doctor(self.compat(model="gone"), self.store)
        self.assertEqual(gone["verdict"], "exists")
        good = ai_models.doctor(self.compat(), self.store)
        self.assertTrue(good["ok"], good)
        Fake.mode = "401"
        refused = ai_models.doctor(self.compat(), self.store)
        self.assertEqual(refused["verdict"], "network")
        self.assertIn("401", json.dumps(refused))
        Fake.mode = "429"
        self.assertIn("429", json.dumps(ai_models.doctor(self.compat(), self.store)))
        for answer in (none, nokey, gone, good, refused):
            self.assertNotIn(KEY, json.dumps(answer))

    def test_a_spent_daily_cap_is_the_cause(self):
        cfg = self.compat(daily_limit=1)
        self.store.add_call()
        self.assertEqual(ai_models.doctor(cfg, self.store)["verdict"], "budget")

    def test_ollama_that_is_not_running_is_the_cause(self):
        cfg = ai.ai_config({"ai": {"provider": "ollama", "ollama_url": "http://127.0.0.1:9", "model": "llama3.2"}})
        self.assertEqual(ai_models.doctor(cfg, self.store)["verdict"], "address")


class Resolve(Base):
    def test_a_preset_a_protocol_or_the_general_settings(self):
        cfg = self.compat()
        same, why = ai_models.resolve(cfg, "openai-compatible", "other")
        self.assertIsNone(why)
        self.assertEqual((same["base_url"], same["model"], same["api_key_env"]), (cfg["base_url"], "other", "FAKE_AI_KEY"))
        local, _ = ai_models.resolve(cfg, "ollama", "llama3.2")
        self.assertEqual((local["provider"], local["ollama_url"]), ("ollama", "http://127.0.0.1:11434"))
        preset, _ = ai_models.resolve(cfg, "openai", "gpt-x")
        self.assertEqual((preset["provider"], preset["base_url"], preset["api_key_env"]), ("openai-compatible", "https://api.openai.com/v1", "OPENAI_API_KEY"))
        self.assertIsNone(ai_models.resolve(cfg, "no-such-thing", "m")[0])
        self.assertEqual(ai_models.resolve(cfg, "", None)[0]["model"], "gpt-small")


class Routes(Base):
    def test_the_local_only_posts_and_the_read_only_listing(self):
        config = {"ai": {"provider": "openai-compatible", "base_url": f"http://127.0.0.1:{self.port}/v1", "model": "gpt-small", "api_key_env": "FAKE_AI_KEY"}}
        with mock.patch.object(actions_monitor.toolconfig, "raw_config", return_value=config), mock.patch.object(actions_monitor, "ai_store", return_value=self.store):
            for path in actions_monitor.AI_MODEL_POST:
                self.assertIn(path, actions_monitor.THIS_COMPUTER_POST)
            before = actions_monitor.handle_action_post("/api/ai/models/refresh", {})
            self.assertTrue(before["ok"], before)
            self.assertEqual(before["check"]["state"], "exists")
            listing = ai_models.listing(ai.ai_config(config), self.store)
            self.assertEqual(listing["catalog"]["count"], 2)
            self.assertEqual([r["model"] for r in listing["table"]], ["gpt-small"])      # only models the provider said something about have a row
            saved = actions_monitor.handle_action_post("/api/ai/models/data", {"model": "gpt-small", "values": {"context": 9000}})
            self.assertTrue(saved["ok"], saved)
            self.assertEqual(ai_models.listing(ai.ai_config(config), self.store)["models"][1]["context"], 9000)
            self.assertTrue(actions_monitor.handle_action_post("/api/ai/models/test", {})["ok"])
            self.assertFalse(actions_monitor.handle_action_post("/api/ai/models/test", {"provider": "nope"})["ok"])
            self.assertTrue(actions_monitor.handle_action_post("/api/ai/doctor", {})["ok"])
        self.assertNotIn(KEY, json.dumps(self.store.data))


class CommandLine(unittest.TestCase):
    def run_cli(self, argv, fetched=None, posted=None):
        lines = []
        with mock.patch.object(monitor_cli, "fetch", return_value=fetched or {}), mock.patch.object(monitor_cli, "post_json", return_value=posted or (200, {})), \
                mock.patch("builtins.print", lambda *a, **k: lines.append(" ".join(map(str, a)))):
            code = monitor_cli.main(argv)
        return code, "\n".join(lines)

    def test_models_lists_what_is_known_and_says_unknown_for_the_rest(self):
        code, out = self.run_cli(["ai", "models", "--refresh"], {"provider": "ollama", "label": "ollama", "model": "m", "check": {"message": "The model exists in the list of the provider."},
                                                                  "models": [{"id": "a", "context": 1000, "in_per_mtok": None, "out_per_mtok": 3}]}, (200, {"ok": True, "count": 1}))
        self.assertEqual(code, 0)
        self.assertIn("a", out)
        self.assertIn("unknown", out)
        self.assertIn("1000", out)

    def test_test_and_doctor_exit_codes(self):
        code, out = self.run_cli(["ai", "test", "--provider", "ollama", "--model", "m"], posted=(200, {"ok": True, "provider": "ollama", "model": "m", "ms": 12, "tokens_in": 5, "tokens_out": 6, "tokens_estimated": True, "cost": None, "answer": "hi", "tested_at": "2026-01-01 10:00"}))
        self.assertEqual(code, 0)
        self.assertIn("12 ms", out)
        self.assertEqual(self.run_cli(["ai", "test"], posted=(200, {"ok": False, "error": "x"}))[0], monitor_cli.EXIT_DEGRADED)
        self.assertEqual(self.run_cli(["ai", "doctor"], posted=(200, {"ok": False, "checks": [{"ok": False, "text": "key"}]}))[0], monitor_cli.EXIT_DEGRADED)
        self.assertEqual(self.run_cli(["ai", "doctor"], posted=(200, {"ok": True, "checks": []}))[0], 0)
        self.assertEqual(self.run_cli(["ai", "doctor"], posted=(403, {}))[0], monitor_cli.EXIT_AUTH)
        self.assertEqual(self.run_cli(["ai"], posted=(200, {}))[0], monitor_cli.EXIT_USAGE)


if __name__ == "__main__":
    unittest.main()
