# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The settings of the score: the page, the example file and the engine agree on every default and every range."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.scoring import engine  # noqa: E402

EXAMPLE = HERE / "assets" / "examples" / "actions_monitor.example.json"


def lookup(tree, dotted):
    for part in dotted.split("."):
        tree = tree[part]
    return tree


def score_keys():
    return sorted(k for k in settings_api.FIELDS if k.startswith("score."))


class Agreement(unittest.TestCase):
    def test_the_page_has_every_setting_of_the_engine_except_the_limits(self):
        expected = {"score.enabled", "score.source", "score.window_days", "score.calibrating_hours", "score.min_runs", "score.min_coverage", "score.trend_flat",
                    "score.alert.enabled", "score.alert.drop_points", "score.alert.notify_external"}
        expected |= {f"score.weights.{p}" for p in engine.PARTS} | {f"score.grades.{g}" for g in "ABCD"}
        self.assertIn("score.weights.security", expected)
        self.assertEqual(set(score_keys()), expected)

    def test_the_example_file_holds_the_defaults_of_the_engine(self):
        example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(example["score"], engine.DEFAULTS)

    def test_every_default_is_inside_the_range_the_page_accepts(self):
        for key in score_keys():
            ok, clean = settings_api.check_value(key, lookup(engine.DEFAULTS, key[len('score.'):]))
            self.assertTrue(ok, f"{key}: {clean}")

    def test_the_ranges_of_the_page_are_no_wider_than_what_the_engine_takes(self):
        for key in score_keys():
            row = settings_api.FIELDS[key]
            if row[2] not in ("int", "float"):
                continue
            low, high = row[3]
            for value in (low, high):
                config = {}
                node = config
                parts = key.split(".")
                for part in parts[:-1]:
                    node = node.setdefault(part, {})
                node[parts[-1]] = value
                cfg = engine.settings(config)
                if key.startswith(("score.weights.", "score.grades.")):
                    continue     # all-zero weights and cuts that do not descend are refused as a whole
                self.assertEqual(lookup(cfg, key[len('score.'):]), value, key)

    def test_the_notification_outside_the_panel_starts_off_and_is_a_safety_option(self):
        self.assertFalse(engine.DEFAULTS["alert"]["notify_external"])
        self.assertTrue(settings_api.META["score.alert.notify_external"]["secure"])

    def test_the_window_defaults_to_seven_days_and_the_user_can_pick_another(self):
        self.assertEqual(engine.settings({})["window_days"], 7)
        self.assertEqual(engine.settings({"score": {"window_days": 30}})["window_days"], 30)


if __name__ == "__main__":
    unittest.main()
