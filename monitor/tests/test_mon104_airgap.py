# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The air-gapped mode of the AI: with it on, no socket leaves for an address that is not on this computer or declared as private, no matter which door the call comes through (the chat, the list of models,
the test of a model, the doctor, the fallback chain, the assistant), a cloud provider is never reached by a fallback, the mode cannot be switched off from the network, and the words the owner asks to hide
are hidden. The network is replaced by a trap that fails the test when anything tries to connect."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.integrations import assistant  # noqa: E402
from github_actions_monitor.security import localguard  # noqa: E402
from github_actions_monitor.sentinels import ai_airgap, ai_models, sentinel_ai  # noqa: E402

KEY_VAR = "MON104_TEST_KEY"
CLOUD = {"provider": "openai-compatible", "base_url": "https://api.example-cloud.test/v1", "model": "m", "api_key_env": KEY_VAR}


def cfg(**ai):
    return sentinel_ai.ai_config({"ai": dict({"airgapped": True}, **ai)})


class Trap:
    """Replaces the network: every attempt to connect is written down and refused."""

    def __init__(self, case):
        self.attempts = []
        case.addCleanup(mock.patch.stopall)

        def refuse(*args, **kwargs):
            self.attempts.append(args[0] if args and not isinstance(args[0], object.__class__) else args)
            raise ConnectionRefusedError("trap")
        mock.patch("socket.create_connection", side_effect=refuse).start()
        mock.patch("socket.socket.connect", side_effect=refuse).start()


class TheRule(unittest.TestCase):
    def test_it_is_off_by_default_and_three_doors_turn_it_on(self):
        self.assertFalse(sentinel_ai.ai_config({})["airgapped"])
        self.assertTrue(sentinel_ai.ai_config({"ai": {"airgapped": True}})["airgapped"])
        self.assertTrue(sentinel_ai.ai_config({"airgapped": True})["airgapped"])      # the general switch
        with mock.patch.dict(os.environ, {"MONITOR_AIRGAPPED": "1"}):
            self.assertTrue(sentinel_ai.ai_config({})["airgapped"])

    def test_this_computer_is_always_allowed_and_nothing_else_unless_declared(self):
        c = cfg(airgap_hosts=["192.168.1.20", "gpu.lan", "8.8.8.8", "example.com", "Box"])
        for url in ("http://127.0.0.1:11434", "http://localhost:1234/v1", "http://[::1]:8080", "http://192.168.1.20:11434", "http://gpu.lan/v1", "http://box/v1"):
            self.assertEqual(ai_airgap.problem(c, url), "", url)
        for url, why in (("http://192.168.1.99:11434", "host_not_allowed"), ("https://api.openai.com/v1", "host_not_allowed"), ("http://8.8.8.8/v1", "host_not_allowed"),
                         ("https://example.com/v1", "host_not_allowed"), ("not a url", "no_address")):
            self.assertEqual(ai_airgap.problem(c, url), why, url)

    def test_a_public_address_is_refused_even_when_it_is_listed(self):
        c = cfg(airgap_hosts=["8.8.8.8", "example.com", "1.1.1.1"])
        for host in ("8.8.8.8", "example.com", "1.1.1.1"):
            self.assertEqual(ai_airgap.problem(c, f"http://{host}/v1"), "host_not_allowed", host)

    def test_the_service_of_copilot_is_cloud_by_definition_and_anthropic_is_judged_by_its_address(self):
        self.assertEqual(ai_airgap.problem(cfg(provider="copilot"), None), "cloud_provider")
        self.assertEqual(ai_airgap.problem(cfg(provider="anthropic"), ai_airgap.target(cfg(provider="anthropic"))), "host_not_allowed")
        proxy = cfg(provider="anthropic", base_url="http://10.0.0.5:9000", airgap_hosts=["10.0.0.5"])
        self.assertEqual(ai_airgap.problem(proxy, ai_airgap.target(proxy)), "")

    def test_with_the_mode_off_nothing_is_refused(self):
        c = sentinel_ai.ai_config({"ai": dict(CLOUD)})
        self.assertEqual(ai_airgap.problem(c, ai_airgap.target(c)), "")
        self.assertEqual(ai_airgap.problem(sentinel_ai.ai_config({"ai": {"provider": "copilot"}}), None), "")

    def test_the_list_of_hosts_is_cleaned(self):
        c = sentinel_ai.ai_config({"ai": {"airgap_hosts": [" GPU.lan ", 5, "", "a" * 300] + ["h%d" % i for i in range(80)]}})
        self.assertEqual(c["airgap_hosts"][0], "gpu.lan")
        self.assertLessEqual(len(c["airgap_hosts"]), 50)
        self.assertTrue(all(len(h) <= 100 for h in c["airgap_hosts"]))

    def test_it_cannot_be_switched_off_from_the_network(self):
        for key in ("ai.airgapped", "ai.airgap_hosts", "ai.redact.extra_terms"):
            self.assertTrue(localguard.local_only_key(key), key)


class NoSocketLeaves(unittest.TestCase):
    def setUp(self):
        self.trap = Trap(self)
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.store = sentinel_ai.Store(str(Path(self.dir.name) / "cache.json"))
        patcher = mock.patch.dict(os.environ, {KEY_VAR: "not-a-real-key"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_chat_to_a_cloud_provider_opens_no_connection(self):
        c = cfg(**CLOUD)
        out = sentinel_ai.explain("ask", "why is it red", c, self.store)
        self.assertFalse(out["ok"])
        self.assertEqual(self.trap.attempts, [])
        self.assertEqual(self.store.used_today(), 0)      # a refused call spends nothing
        self.assertIn("api.example-cloud.test", out["error"])

    def test_the_post_itself_refuses_before_connecting(self):
        with self.assertRaises(ai_airgap.Airgapped):
            sentinel_ai._post_json("https://api.example-cloud.test/v1", {}, {}, 5, ai=cfg(**CLOUD))
        self.assertEqual(self.trap.attempts, [])

    def test_the_fallback_never_moves_to_a_cloud_model(self):
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": "not-a-real-key"}):
            c = cfg(provider="ollama", model="m", fallback="groq=llama-3.3-70b-versatile", fallback_cloud_allowed=["groq"], ollama_url="http://127.0.0.1:1")
            out = sentinel_ai.explain("ask", "why is it red", c, self.store)
        self.assertFalse(out["ok"])
        hosts = {str(a) for a in self.trap.attempts}
        self.assertFalse([h for h in hosts if "groq" in h], hosts)
        reasons = [f["reason"] for f in (out.get("fallback") or {}).get("failed", [])]
        self.assertIn("airgap", reasons)

    def test_a_local_model_is_still_reached(self):
        c = cfg(provider="ollama", model="m", ollama_url="http://127.0.0.1:1")
        out = sentinel_ai.explain("ask", "why is it red", c, self.store)
        self.assertFalse(out["ok"])      # the trap refuses the connection, but it was ATTEMPTED: loopback is allowed
        self.assertTrue(self.trap.attempts)

    def test_the_test_of_a_model_and_the_test_of_the_connection_open_nothing(self):
        c = cfg(**CLOUD)
        self.assertFalse(sentinel_ai.test_connection(c, self.store)["ok"])
        self.assertFalse(ai_models.probe(c, self.store)["ok"])
        self.assertFalse(sentinel_ai.run_call(c, self.store, "build", "x")["ok"])
        self.assertEqual(self.trap.attempts, [])

    def test_the_list_of_models_opens_nothing(self):
        c = cfg(**CLOUD, catalog={"enabled": True})
        out = ai_models.fetch(c, self.store, force=True)
        self.assertEqual((out["ok"], out["state"]), (False, "airgap"))
        self.assertEqual(self.trap.attempts, [])

    def test_copilot_is_refused_without_starting_the_cli(self):
        c = cfg(provider="copilot", model="m")
        with mock.patch("subprocess.run", side_effect=AssertionError("the CLI must not start")):
            out = sentinel_ai.explain("ask", "x", c, self.store)
        self.assertFalse(out["ok"])

    def test_the_assistant_obeys_it_too(self):
        c = cfg(**CLOUD, assistant={"enabled": True})
        reader = {"views": lambda: [], "score": lambda: {}}
        out = assistant.ask("summarize_week", {}, c, reader, lambda text: sentinel_ai.explain("assistant", text, c, self.store))
        self.assertFalse(out["ok"])
        self.assertEqual(self.trap.attempts, [])


class TheDoctor(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.store = sentinel_ai.Store(str(Path(self.dir.name) / "cache.json"))

    def test_the_check_only_exists_while_the_mode_is_on(self):
        off = ai_models.doctor(sentinel_ai.ai_config({"ai": {"provider": "ollama", "ollama_url": "http://127.0.0.1:1"}}), self.store, live=False)
        self.assertNotIn("ai_egress", [c["id"] for c in off["checks"]])
        on = ai_models.doctor(cfg(provider="ollama", ollama_url="http://127.0.0.1:1"), self.store, live=False)
        self.assertTrue(next(c for c in on["checks"] if c["id"] == "ai_egress")["ok"])
        bad = ai_models.doctor(cfg(provider="openai-compatible", base_url="https://api.example-cloud.test/v1", model="m"), self.store, live=False)
        self.assertFalse(next(c for c in bad["checks"] if c["id"] == "ai_egress")["ok"])

    def test_the_report_says_what_it_would_do(self):
        report = ai_airgap.report(cfg(provider="openai-compatible", base_url="http://10.0.0.7/v1", airgap_hosts=["10.0.0.7"]))
        self.assertEqual((report["on"], report["problem"], report["target"]), (True, "", "http://10.0.0.7/v1"))


class TheWordsOfTheOwner(unittest.TestCase):
    def test_a_listed_word_is_hidden_whatever_its_case_and_the_secrets_still_are(self):
        c = sentinel_ai.ai_config({"ai": {"redact": {"extra_terms": ["Project-Falcon", "buildbox"]}}})
        text = "project-FALCON failed on BuildBox with ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
        out = sentinel_ai.sanitize_text(text, 500, keep="head", terms=c["redact"]["extra_terms"])
        self.assertNotIn("alcon", out)
        self.assertNotIn("uildbox".lower(), out.lower())
        self.assertNotIn("ghp_a1B2", out)
        self.assertEqual(out.count("[hidden]"), 2)

    def test_no_word_can_remove_a_base_pattern_and_a_word_is_not_a_pattern(self):
        out = sentinel_ai.sanitize_text("a.b (c) ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8", 200, keep="head", terms=[".", "("])
        self.assertNotIn("ghp_a1B2", out)      # the dot is a letter to hide, not a pattern that matches everything
        self.assertIn("a[hidden]b", out)

    def test_the_list_is_cleaned_and_limited(self):
        c = sentinel_ai.ai_config({"ai": {"redact": {"extra_terms": ["ok", "x", "", 5, "w" * 200] + ["t%d" % i for i in range(100)]}}})
        terms = c["redact"]["extra_terms"]
        self.assertIn("ok", terms)
        self.assertNotIn("x", terms)
        self.assertLessEqual(len(terms), 50)

    def test_the_text_that_reaches_the_model_has_the_words_hidden(self):
        seen = []

        def transport(config, system, user):
            seen.append(user)
            return "answer"
        with tempfile.TemporaryDirectory() as folder:
            store = sentinel_ai.Store(str(Path(folder) / "c.json"))
            c = sentinel_ai.ai_config({"ai": {"provider": "ollama", "redact": {"extra_terms": ["falcon"]}}})
            self.assertTrue(sentinel_ai.explain("ask", "why is Falcon red", c, store, transport)["ok"])
        self.assertNotIn("alcon", seen[0].lower().replace("[hidden]", ""))


class TheSkillsAndTheGuideKnowIt(unittest.TestCase):
    def text(self, kind):
        base = HERE / "skills" / kind
        return "\n".join(p.read_text(encoding="utf-8") for p in [base / "SKILL.md"] + sorted((base / "references").glob("*.md")))

    def test_both_skills_name_the_mode_its_hosts_and_the_hidden_words(self):
        for kind in ("internal", "external"):
            text = self.text(kind)
            for needle in ("ai.airgapped", "ai.airgap_hosts", "ai.redact.extra_terms"):
                self.assertIn(needle, text, (kind, needle))
        self.assertIn("ai_egress", self.text("external"))

    def test_the_guide_explains_it_in_the_eight_languages(self):
        for suffix in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho"):
            text = (HERE / "docs" / f"AI_CONNECTION{suffix}.md").read_text(encoding="utf-8")
            for needle in ("`ai.airgapped`", "`ai.airgap_hosts`", "`ai_egress`", "`ai.redact.extra_terms`", "192.168.1.20"):
                self.assertIn(needle, text, (suffix, needle))


if __name__ == "__main__":
    unittest.main()
