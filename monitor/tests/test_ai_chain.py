# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A model per task, the chain of fallbacks and the budget per model, against a fake local server that fails by the NAME of the model (m-401, m-429, m-404, m-empty, m-slow).
With nothing configured the behaviour is the one of before. No network beyond 127.0.0.1; the key never appears in an answer, a store or the brief."""
import json
import os
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import settings_api
from github_actions_monitor.integrations import ai_alerts, ai_notify
from github_actions_monitor.sentinels import ai_chain, ai_models, sentinel_ai as ai

KEY = "sk-test-" + "R" * 30


class Fake(BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        model = body.get("model", "")
        Fake.seen.append(model)
        if model == "m-slow":
            time.sleep(2.5)
        code = {"m-401": 401, "m-429": 429, "m-404": 404}.get(model, 200)
        content = "" if model == "m-empty" else "answer from " + model
        raw = json.dumps({"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 1000, "completion_tokens": 500}} if code == 200 else {"error": {"message": "echo " + KEY}}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        try:
            self.wfile.write(raw)
        except OSError:
            pass

    def log_message(self, *a):
        pass


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Fake.seen = []
        ai_chain.STATE["failovers"] = []
        self.addCleanup(lambda: ai_chain.STATE.update(failovers=[]))
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.store = ai.Store(Path(self.dir.name) / "c.json")
        env = mock.patch.dict(os.environ, {"FAKE_AI_KEY": KEY})
        env.start()
        self.addCleanup(env.stop)

    def cfg(self, model="m-ok", **extra):
        return ai.ai_config({"ai": {"provider": "openai-compatible", "base_url": f"http://127.0.0.1:{self.port}/v1", "model": model, "api_key_env": "FAKE_AI_KEY", "timeout_seconds": 5,
                                    "daily_limit": 50, "skill": False, **extra}})

    def ask(self, cfg, text="log one", kind="build", **kw):
        return ai.explain(kind, text, cfg, self.store, **kw)


class Nothing(Base):
    def test_with_nothing_configured_the_one_general_model_answers_as_before(self):
        cfg = self.cfg()
        self.assertEqual([c["label"] for c in ai_chain.candidates(cfg, "build")], ["127.0.0.1/m-ok"])
        result = self.ask(cfg)
        self.assertTrue(result["ok"], result)
        self.assertEqual((result["model"], result["provider"]), ("m-ok", "openai-compatible"))
        self.assertNotIn("fallback", result)
        self.assertEqual(Fake.seen, ["m-ok"])
        self.assertEqual(self.ask(cfg)["cached"], True)
        self.assertEqual(Fake.seen, ["m-ok"])
        self.assertEqual(ai_chain.brief_lines(), "")

    def test_the_new_settings_exist_and_are_clamped(self):
        for key in ("ai.fallback", "ai.fallback_max_attempts", "ai.fallback_after_seconds", "ai.model_daily_limit", "ai.cost_limit_daily", "ai.model_cost_limit_daily", "ai.tasks.build.model",
                    "ai.tasks.alert.provider", "ai.tasks.diagnose.timeout_seconds"):
            self.assertIn(key, settings_api.FIELDS)
        cfg = ai.ai_config({"ai": {"fallback_max_attempts": 99, "model_daily_limit": -4, "cost_limit_daily": "x"}})
        self.assertEqual((cfg["fallback_max_attempts"], cfg["model_daily_limit"], cfg["cost_limit_daily"]), (5, 0, 0))      # each value is clamped on its own, a wrong one goes back to its default
        cfg = ai.ai_config({"ai": {"fallback_max_attempts": 99, "tasks": "no"}})
        self.assertEqual((cfg["fallback_max_attempts"], cfg["tasks"]), (5, {}))


class PerTask(Base):
    def test_a_task_uses_its_own_model_and_limits_and_the_others_the_general_one(self):
        cfg = self.cfg(tasks={"codeql": {"model": "m-code", "max_input_chars": 700, "timeout_seconds": 9}, "report": {"provider": "", "model": ""}})
        code = ai_chain.candidates(cfg, "codeql")[0]
        self.assertEqual((code["label"], code["role"], code["cfg"]["max_input_chars"], code["cfg"]["timeout_seconds"]), ("127.0.0.1/m-code", "task", 700, 9))
        self.assertEqual(ai_chain.candidates(cfg, "build")[0]["role"], "general")
        self.assertEqual(ai_chain.candidates(cfg, "report")[0]["label"], "127.0.0.1/m-ok")      # a task that names no model uses the general one
        self.assertEqual(self.ask(cfg, "alert x", kind="codeql")["model"], "m-code")
        self.assertEqual(self.ask(cfg, "build x", kind="build")["model"], "m-ok")
        self.assertEqual(Fake.seen, ["m-code", "m-ok"])

    def test_a_task_may_name_another_provider_by_its_preset_and_a_wrong_one_is_ignored(self):
        cfg = self.cfg(tasks={"build": {"provider": "ollama", "model": "llama3.2"}, "report": {"provider": "no-such", "model": "x"}, "diagnose": {"provider": "bad name!", "model": "x"}})
        first = ai_chain.candidates(cfg, "build")[0]
        self.assertEqual((first["cfg"]["provider"], first["cfg"]["ollama_url"], first["label"]), ("ollama", "http://127.0.0.1:11434", "ollama/llama3.2"))
        self.assertEqual(ai_chain.candidates(cfg, "report")[0]["role"], "general")
        self.assertEqual(ai_chain.candidates(cfg, "ask")[0]["role"], "general")      # the task of a question to the monitor is `diagnose`

    def test_the_task_of_each_kind_and_an_explicit_task(self):
        self.assertEqual([ai_chain.task_of(k) for k in ("build", "codeql", "report", "release_notes", "ask")], ["build", "codeql", "report", "report", "diagnose"])
        self.assertEqual(ai_chain.task_of("build", "alert"), "alert")
        cfg = self.cfg(tasks={"alert": {"model": "m-alert"}})
        self.assertEqual(self.ask(cfg, "x", task="alert")["model"], "m-alert")


class Fallback(Base):
    def chain(self, first, *rest, **extra):
        return self.cfg(model=first, fallback=", ".join(f"openai-compatible={m}" for m in rest), **extra)

    def test_every_kind_of_failure_goes_to_the_next_model_and_is_written_down(self):
        for bad, reason in (("m-401", "auth"), ("m-404", "model_not_found"), ("m-429", "quota"), ("m-empty", "no_text")):
            Fake.seen, ai_chain.STATE["failovers"] = [], []
            self.store = ai.Store(Path(self.dir.name) / (bad + ".json"))
            with self.assertLogs("github_actions_monitor.ai", "WARNING") as logs:
                result = self.ask(self.chain(bad, "m-good"))
            self.assertTrue(result["ok"], (bad, result))
            self.assertEqual(result["model"], "m-good")
            self.assertEqual(result["fallback"]["failed"][0]["reason"], reason, bad)
            self.assertEqual(result["fallback"]["used"], "127.0.0.1/m-good")
            self.assertEqual(Fake.seen, [bad, "m-good"])
            self.assertIn(reason, logs.output[0])
            self.assertNotIn(KEY, json.dumps(result) + json.dumps(self.store.data) + logs.output[0])
            text = ai_chain.brief_lines()
            self.assertIn(f"main model 127.0.0.1/{bad} failed", text)
            self.assertIn("m-good answered instead", text)

    def test_a_slow_main_model_is_given_up_after_the_time_of_the_chain(self):
        started = time.time()
        result = self.ask(self.chain("m-slow", "m-good", fallback_after_seconds=1))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["fallback"]["failed"][0]["reason"], "slow")
        self.assertLess(time.time() - started, 2.4)

    def test_the_chain_is_capped_never_repeats_a_model_and_is_not_a_loop(self):
        cfg = self.chain("m-401", "m-429", "m-404", "m-good", fallback_max_attempts=2)
        self.assertEqual([c["label"] for c in ai_chain.candidates(cfg, "build")], ["127.0.0.1/m-401", "127.0.0.1/m-429"])
        result = self.ask(cfg)
        self.assertFalse(result["ok"])
        self.assertEqual(Fake.seen, ["m-401", "m-429"])
        self.assertEqual(ai_chain.brief_lines().count("nobody answered"), 1)
        again = self.chain("m-ok", "m-ok", "openai-compatible=m-ok", "bad item", "x=")
        self.assertEqual(len(ai_chain.candidates(again, "build")), 1)
        self.assertEqual(ai_chain.parse_fallback("a=b, nothing, =x, c=d:e"), [("a", "b"), ("c", "d:e")])
        self.assertEqual(ai_chain.parse_fallback([{"provider": "ollama", "model": "llama3.2"}, 5, "z=y"]), [("ollama", "llama3.2"), ("z", "y")])

    def test_an_answer_that_is_kept_costs_nothing_and_each_call_is_counted_once(self):
        cfg = self.chain("m-401", "m-good")
        self.assertTrue(self.ask(cfg)["ok"])
        self.assertEqual(self.store.used_today(), 2)      # the failed call and the good one: the cap counts both, nothing is duplicated
        again = self.ask(cfg)
        self.assertTrue(again["cached"])
        self.assertEqual(self.store.used_today(), 2)
        self.assertEqual(Fake.seen, ["m-401", "m-good"])

    def test_the_daily_cap_stops_the_chain_too(self):
        cfg = self.chain("m-401", "m-good", daily_limit=1)
        result = self.ask(cfg)
        self.assertFalse(result["ok"])
        self.assertEqual(Fake.seen, ["m-401"])

    def test_a_retired_model_is_skipped_without_a_call_but_only_when_the_option_is_on(self):
        self.store.data["catalog"] = {ai_models.key_of(self.cfg()): {"at": time.time(), "models": [{"id": "m-good"}]}}
        off = self.chain("m-gone", "m-good")
        self.assertTrue(self.ask(off)["ok"])
        self.assertEqual(Fake.seen, ["m-gone"])      # the check is off: the main model is called (it answers on the fake server)
        Fake.seen = []
        on = self.chain("m-gone", "m-good", catalog={"enabled": True})
        result = self.ask(on, "other log")
        self.assertEqual(Fake.seen, ["m-good"])
        self.assertEqual(result["fallback"]["failed"][0]["reason"], "retired")
        Fake.seen = []
        alone = self.cfg(model="m-gone", catalog={"enabled": True})
        self.ask(alone, "third log")
        self.assertEqual(Fake.seen, ["m-gone"])      # a single model is always tried: the list may be incomplete

    def test_the_failure_of_the_main_model_is_in_the_brief_of_the_ais(self):
        self.ask(self.chain("m-429", "m-good"))
        text = ai_alerts.brief([], 2000)
        self.assertIn("## AI models", text)
        self.assertIn("(quota)", text)
        self.assertNotIn("## AI models", ai_alerts.brief([], 2000, now=time.time() - 3 * 86400))      # a brief of the past says nothing of it


class Budget(Base):
    def test_calls_per_model_skip_to_the_next_and_the_limit_is_never_jumped(self):
        cfg = self.cfg(model="m-a", fallback="openai-compatible=m-b", model_daily_limit=1)
        self.assertEqual(self.ask(cfg, "one")["model"], "m-a")
        second = self.ask(cfg, "two")
        self.assertEqual((second["ok"], second["model"]), (True, "m-b"))
        self.assertEqual(second["fallback"]["failed"][0]["reason"], "model_calls")
        third = self.ask(cfg, "three")
        self.assertFalse(third["ok"])
        self.assertIn("m-b", third["error"])
        self.assertEqual(Fake.seen, ["m-a", "m-b"])      # nothing was called past the limit
        view = ai_chain.view(cfg, self.store)
        self.assertEqual({m["model"]: m["calls"] for m in view["models"]}, {"127.0.0.1/m-a": 1, "127.0.0.1/m-b": 1})
        self.assertEqual(view["calls"], 2)

    def test_a_limit_typed_in_the_table_wins_over_the_general_one(self):
        ai_models.set_manual(self.store, "127.0.0.1", "m-a", {"daily_limit": 2})
        cfg = self.cfg(model="m-a", model_daily_limit=1)
        self.assertEqual(ai_chain.limits_of(cfg, self.store), (2, 0.0))
        self.assertTrue(self.ask(cfg, "one")["ok"])
        self.assertTrue(self.ask(cfg, "two")["ok"])
        self.assertFalse(self.ask(cfg, "three")["ok"])

    def test_the_cost_is_estimated_only_with_known_prices_and_stops_at_its_limit(self):
        cfg = self.cfg(model="m-a", cost_limit_daily=0.0015)
        self.assertTrue(self.ask(cfg, "one")["ok"])      # no prices: the cost is unknown, only the calls count
        self.assertIsNone(ai_chain.view(cfg, self.store)["models"][0]["cost"])
        self.assertFalse(ai_chain.view(cfg, self.store)["models"][0]["cost_known"])
        ai_models.set_manual(self.store, "127.0.0.1", "m-b", {"in_per_mtok": 1, "out_per_mtok": 2})      # 1000 in + 500 out = 0.001 + 0.001
        priced = self.cfg(model="m-b", cost_limit_daily=0.0015)
        self.assertTrue(self.ask(priced, "two")["ok"])
        view = ai_chain.view(priced, self.store)
        self.assertAlmostEqual(view["cost"], 0.002, places=6)
        blocked = self.ask(priced, "three")
        self.assertFalse(blocked["ok"])
        self.assertEqual(Fake.seen, ["m-a", "m-b"])
        per_model = self.cfg(model="m-b", model_cost_limit_daily=0.0015)
        self.assertEqual(ai_chain.budget_block(per_model, self.store), "model_cost")

    def test_the_model_test_respects_the_budget_and_counts_in_it(self):
        cfg = self.cfg(model="m-a", model_daily_limit=1)
        self.assertTrue(ai_models.probe(cfg, self.store)["ok"])
        refused = ai_models.probe(cfg, self.store)
        self.assertFalse(refused["ok"])
        self.assertEqual(Fake.seen, ["m-a"])
        self.assertEqual(ai_chain.view(cfg, self.store)["models"][0]["calls"], 1)

    def test_the_counters_start_again_on_a_new_day_and_nothing_secret_is_kept(self):
        self.ask(self.cfg(model="m-a"), "one")
        self.store.data["usage"]["day"] = "2000-01-01"
        self.assertEqual(ai_chain.view(self.cfg(model="m-a"), self.store)["models"], [])
        self.assertNotIn(KEY, json.dumps(self.store.data))


class Notice(Base):
    def test_the_alert_task_may_change_the_model_but_never_the_provider(self):
        seen = []

        def transport(cfg, system, user):
            seen.append((cfg["provider"], cfg["model"]))
            return "advice"

        alert = {"id": "abc", "class": "real", "state": "open", "severity": "bad", "repo": "repo-a", "workflow": "CI", "conclusion": "failure", "streak": 2, "cause": "step failed",
                 "action": "re-run once", "url": "https://github.com/o/repo-a/actions/runs/9", "since": "x", "diagnosis": {"lines": []}, "origin": None}
        with tempfile.TemporaryDirectory() as tmp:
            for index, (tasks, expected) in enumerate((({}, "m-ok"), ({"alert": {"model": "m-alert"}}, "m-alert"), ({"alert": {"provider": "ollama", "model": "llama3.2"}}, "m-ok"))):
                config = {"ai": {"provider": "openai-compatible", "base_url": f"http://127.0.0.1:{self.port}/v1", "model": "m-ok", "api_key_env": "FAKE_AI_KEY", "tasks": tasks},
                          "ai_alerts": {"enabled": True, "folder": tmp}, "ai_notify": {"enabled": True, "confirmed_provider": "openai-compatible", "max_calls_per_hour": 9, "max_cost_per_hour_cents": 500}}
                seen.clear()
                answer = ai_notify.notify(config, dict(alert, id="a%d" % index), now=1_800_000_000 + index * 4000, transport=transport)
                self.assertTrue(answer["sent"], answer)
                self.assertEqual(seen, [("openai-compatible", expected)])


if __name__ == "__main__":
    unittest.main()
