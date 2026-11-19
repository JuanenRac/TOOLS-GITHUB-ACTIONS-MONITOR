# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The example file of the configuration carries EVERY setting (the computed ones apart), and what it says for the AI and read-pool settings is what the code does when the setting is absent: the page
of Settings takes the default from that file, so a wrong value there would be a lie. No network."""
import json
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api as sa  # noqa: E402
from github_actions_monitor.data_pipeline import readpool  # noqa: E402
from github_actions_monitor.sentinels import ai_chain, sentinel_ai  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
EXAMPLE = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))


def example(key):
    node = EXAMPLE
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(key)
        node = node[part]
    return node


def walk(tree, key):
    for part in key.split("."):
        tree = tree[part]
    return tree


class TheExampleCarriesEverySetting(unittest.TestCase):
    def test_every_setting_is_in_the_example_but_the_computed_ones(self):
        missing = []
        for key in sa.FIELDS:
            if key in sa.STATUS_KEYS:
                continue
            try:
                example(key)
            except KeyError:
                missing.append(key)
        self.assertEqual(missing[:20], [], "add the setting and its default to assets/examples/actions_monitor.example.json")

    def test_a_computed_setting_is_not_in_the_example(self):
        for key in sa.STATUS_KEYS:
            with self.assertRaises(KeyError):
                example(key)


class WhatTheExampleSaysIsWhatTheCodeDoes(unittest.TestCase):
    def test_the_ai_settings(self):
        cfg = sentinel_ai.ai_config({})
        for key in ("airgap_hosts", "airgapped", "allow_private_targets", "api_key_env", "base_url", "cost_limit_daily", "fallback", "fallback_after_seconds", "fallback_cloud_allowed",
                    "fallback_max_attempts", "model_cost_limit_daily", "model_daily_limit", "ollama_url", "skill", "skill_max_chars", "untrusted_text_max"):
            self.assertEqual(example("ai." + key), cfg[key], key)
        self.assertEqual(example("ai.assistant.enabled"), cfg["assistant"]["enabled"])
        self.assertEqual(example("ai.prompt_log.enabled"), cfg["prompt_log"]["enabled"])
        self.assertEqual(example("ai.redact.extra_terms"), cfg["redact"]["extra_terms"])
        self.assertEqual(example("ai.redact.extra_patterns"), cfg["redact"]["extra_patterns"])
        self.assertEqual(example("ai.similar.enabled"), sentinel_ai.AI_DEFAULTS["similar"]["enabled"])
        self.assertEqual(example("ai.similar.max"), sentinel_ai.AI_DEFAULTS["similar"]["max"])

    def test_a_task_that_says_nothing_uses_the_general_model_and_limits(self):
        general = sentinel_ai.ai_config({"ai": {"provider": "ollama"}})
        for task in ai_chain.TASKS:
            for key, value in ai_chain.TASK_DEFAULTS.items():
                self.assertEqual(example(f"ai.tasks.{task}.{key}"), value, (task, key))
            chosen, role = ai_chain.task_cfg(general, task)
            self.assertEqual(role, "general")
            for key in ai_chain.TASK_LIMITS:
                self.assertEqual(chosen[key], general[key], (task, key))

    def test_the_read_pool(self):
        pool = readpool.pool_settings({})
        self.assertEqual(pool, readpool.POOL_DEFAULTS)
        for kind in readpool.KINDS:
            self.assertEqual(example(f"readpool.prefer.{kind}"), pool["prefer"][kind])
        for source in readpool.SOURCES:
            self.assertEqual(example(f"readpool.reserve.{source}"), pool["reserve"][source])

    def test_the_folders_and_the_silences(self):
        for key in ("workspace_root", "audit_dir", "signed_dir", "alerts.silences_expire_days", "github_app.app_id"):
            self.assertEqual(example(key), walk(am.DEFAULTS, key), key)
        self.assertEqual(example("notify.allow_private_targets"), False)
        self.assertEqual(example("lint.ignore"), [])

    def test_the_values_of_the_example_pass_the_checks_of_the_page(self):
        refused = []
        for key in sa.FIELDS:
            if key in sa.STATUS_KEYS or key == "github_app.app_id":      # an empty application id means "none": the page asks for a number only when it is written
                continue
            try:
                value = example(key)
            except KeyError:
                continue
            ok = sa.check_value(key, value)[0]
            if not ok and value not in ("", [], 0):
                refused.append((key, value))
        self.assertEqual(refused[:10], [])


if __name__ == "__main__":
    unittest.main()
