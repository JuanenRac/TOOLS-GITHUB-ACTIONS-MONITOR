# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The table of models that the person keeps by hand (`config/ai_models.json`) and the notice of retired models: figures above the provider's and below what was typed on the page, a retired model is
skipped by the chain and named by the AI doctor even without the live list of models. Nothing here reaches a provider."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.sentinels import ai_chain, ai_models, sentinel_ai  # noqa: E402
from github_actions_monitor.util import paths  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.file = Path(self.dir.name) / "ai_models.json"
        patcher = mock.patch.object(ai_models, "file_path", lambda: self.file)
        patcher.start()
        self.addCleanup(patcher.stop)
        ai_models._FILE_CACHE.update(key=None, data=None)
        self.store = sentinel_ai.Store(str(Path(self.dir.name) / "cache.json"))

    def write(self, doc):
        self.file.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")


class TheTableByHand(Base):
    def test_no_file_or_a_damaged_one_changes_nothing(self):
        self.assertEqual(ai_models.file_data(), {"rows": {}, "retired": {}, "problems": []})
        self.write("{not json")
        data = ai_models.file_data()
        self.assertEqual((data["rows"], data["retired"]), ({}, {}))
        self.assertTrue(data["problems"])
        self.write("[1, 2]")
        self.assertTrue(ai_models.file_data()["problems"])
        self.write(" " * (ai_models.FILE_MAX_BYTES + 10))
        self.assertTrue(ai_models.file_data()["problems"])
        self.assertEqual(ai_models.data_of(self.store, "api.example.com", "m")["context"], None)

    def test_the_figures_come_from_the_file_with_their_source(self):
        self.write({"models": [{"provider": "api.example.com", "model": "big-1", "context": 128000, "in_per_mtok": 1.5, "out_per_mtok": 6, "tools": True, "daily_limit": 40}]})
        data = ai_models.data_of(self.store, "api.example.com", "big-1")
        self.assertEqual((data["context"], data["in_per_mtok"], data["tools"], data["daily_limit"]), (128000, 1.5, True, 40))
        self.assertEqual({data[k + "_source"] for k in ("context", "tools", "daily_limit")}, {"file"})
        self.assertIn({"provider": "api.example.com", "model": "big-1"}, [{k: r[k] for k in ("provider", "model")} for r in ai_models.table(self.store)])

    def test_what_was_typed_on_the_page_wins_and_the_file_wins_over_the_provider(self):
        self.write({"models": [{"provider": "p.example", "model": "m1", "context": 1000, "in_per_mtok": 2}]})
        ai_models.remember_provider_data(self.store, {"provider": "openai-compatible", "base_url": "https://p.example/v1"}, {"id": "m1", "context": 9999, "in_per_mtok": 9, "out_per_mtok": 5})
        label = ai_models.provider_label({"provider": "openai-compatible", "base_url": "https://p.example/v1"})
        data = ai_models.data_of(self.store, label, "m1")
        self.assertEqual((data["context"], data["context_source"]), (1000, "file"))
        self.assertEqual((data["out_per_mtok"], data["out_per_mtok_source"]), (5, "provider"))
        ai_models.set_manual(self.store, label, "m1", {"context": 4000})
        self.assertEqual(ai_models.data_of(self.store, label, "m1")["context"], 4000)
        self.assertEqual(ai_models.data_of(self.store, label, "m1")["in_per_mtok_source"], "file")

    def test_a_wrong_row_or_figure_is_left_out_and_named(self):
        self.write({"models": [{"provider": "p.example", "model": "ok", "context": "lots", "in_per_mtok": -3, "tools": "yes", "out_per_mtok": 2},
                               {"provider": "bad provider!", "model": "x"}, "text", {"model": "no-provider"}]})
        data = ai_models.file_data()
        self.assertEqual(data["rows"], {"p.example/ok": {"out_per_mtok": 2.0}})
        self.assertEqual(sorted(data["problems"]), sorted(["models[1].context", "models[1].in_per_mtok", "models[1].tools", "models[2]", "models[3]", "models[4]"]))

    def test_the_file_is_read_again_only_when_it_changes(self):
        self.write({"retired": ["old-model"]})
        first = ai_models.file_data()
        self.assertIs(ai_models.file_data(), first)
        self.write({"retired": ["old-model", "older-model"]})
        self.assertEqual(sorted(ai_models.file_data()["retired"]), ["old-model", "older-model"])


class TheRetiredModels(Base):
    def cfg(self, **more):
        return sentinel_ai.ai_config({"ai": dict({"provider": "ollama", "model": "old-model", "fallback": "ollama=new-model"}, **more)})

    def test_a_retired_model_is_found_by_name_and_it_keeps_the_use_and_the_note(self):
        self.write({"retired": [{"model": "Old-Model", "use": "new-model", "note": "ended in spring ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"}, "plain-one", {"model": "bad name!"}]})
        gone = ai_models.retired_in_file("old-model")
        self.assertEqual(gone["use"], "new-model")
        self.assertNotIn("ghp_", gone["note"])
        self.assertIsNotNone(ai_models.retired_in_file("PLAIN-ONE"))
        self.assertIsNone(ai_models.retired_in_file("fine-model"))
        self.assertIsNone(ai_models.retired_in_file(""))

    def test_the_chain_skips_it_without_the_live_list(self):
        self.write({"retired": ["old-model"]})
        cfg = self.cfg()
        self.assertFalse(ai_models.catalog_config(cfg)["enabled"])
        self.assertTrue(ai_chain.retired(cfg, self.store))
        self.assertFalse(ai_chain.retired(self.cfg(model="new-model"), self.store))
        seen = []

        def transport(c, s, u):
            seen.append(c["model"])
            return "answer"
        out = sentinel_ai.explain("ask", "why?", cfg, self.store, transport)
        self.assertTrue(out["ok"])
        self.assertEqual(seen, ["new-model"])
        self.assertEqual(out["fallback"]["failed"][0]["reason"], "retired")

    def test_the_doctor_names_it_only_when_the_file_lists_it(self):
        cfg = self.cfg()
        plain = ai_models.doctor(cfg, self.store, live=False)
        self.assertNotIn("model_retired", [c["id"] for c in plain["checks"]])
        self.write({"retired": [{"model": "old-model", "use": "new-model"}]})
        with mock.patch.object(sentinel_ai, "ollama_available", return_value=(True, "")):
            report = ai_models.doctor(cfg, self.store, live=False)
        check = next(c for c in report["checks"] if c["id"] == "model_retired")
        self.assertFalse(check["ok"])
        self.assertIn("old-model", check["text"])
        self.assertIn("new-model", check["text"])
        self.assertFalse(report["ok"])

    def test_the_file_is_a_configuration_file_and_the_texts_exist(self):
        self.assertEqual(paths.kind_of("ai_models.json"), "config")
        for lang in LANGS:
            text = (HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")
            self.assertIn('"ai.doc_model_retired"', text)
            self.assertIn('"ai.doc_model_use"', text)
        self.assertIn("`config/ai_models.json`", (HERE / "docs" / "AI_CONNECTION.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
