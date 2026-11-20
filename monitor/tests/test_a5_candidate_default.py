# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A release is suggested only from five entries under [Unreleased] (the rule of the owner), the number is a setting, and a value a person chose is kept."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402


class CandidateDefault(unittest.TestCase):
    def test_the_default_is_five_and_the_example_file_agrees(self):
        import json
        self.assertEqual(sl.DEFAULTS["candidate_min_entries"], 5)
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["sentinel"]["candidate_min_entries"], 5)

    def test_it_is_a_setting_with_its_range_and_its_help_in_the_eight_languages(self):
        from github_actions_monitor import i18n
        row = next(r for r in settings_api.SCHEMA if r[1] == "sentinel.candidate_min_entries")
        self.assertEqual(tuple(row[3]), (1, 100))
        for lang in i18n.LANGS:
            self.assertIn("5", i18n.tl(lang, "cfg.h.sentinel.candidate_min_entries"), lang)

    def test_one_to_four_entries_do_not_make_a_candidate_and_a_chosen_value_is_kept(self):
        for n, expected in ((1, 0), (4, 0), (5, 1)):
            rows = sl.release_candidates_rule({"R": n}, {"R": 10.0}, 2.0, sl.DEFAULTS["candidate_min_entries"])
            self.assertEqual(len(rows), expected, n)
        self.assertEqual(len(sl.release_candidates_rule({"R": 1}, {"R": 10.0}, 2.0, 1)), 1)      # a person who asked for 1 still gets 1


if __name__ == "__main__":
    unittest.main()
