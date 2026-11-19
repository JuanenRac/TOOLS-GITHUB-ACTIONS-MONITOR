# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The check of the configuration file at the start: a key nobody reads, a wrong type and a number out of range are named; nothing is refused unless the strict switch is on."""
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

from github_actions_monitor.app import actions_monitor as am, configcheck  # noqa: E402


class WhatIsFound(unittest.TestCase):
    def test_the_example_file_that_ships_has_no_problem(self):
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(configcheck.check(example), [])

    def test_the_defaults_of_the_monitor_have_no_problem(self):
        self.assertEqual(configcheck.check(json.loads(json.dumps(am.DEFAULTS))), [])

    def test_a_typo_is_named_with_the_closest_key(self):
        found = configcheck.check({"refresh_secnds": 30, "cache": {"etag": {"enabld": True}}})
        by_path = {item["path"]: item for item in found}
        self.assertEqual(by_path["refresh_secnds"]["problem"], "unknown")
        self.assertEqual(by_path["refresh_secnds"]["hint"], "refresh_seconds")
        self.assertEqual(by_path["cache.etag.enabld"]["hint"], "cache.etag.enabled")

    def test_a_wrong_type_and_a_number_out_of_range_are_told_apart(self):
        found = {item["path"]: item["problem"] for item in configcheck.check({"refresh_seconds": "fast", "cache": {"etag": {"ttl_hours": 99999}}})}
        self.assertEqual(found, {"refresh_seconds": "type", "cache.etag.ttl_hours": "range"})

    def test_notes_with_an_underscore_are_never_judged(self):
        self.assertEqual(configcheck.check({"_note": "anything", "cache": {"_why": 1}}), [])

    def test_what_lies_inside_a_value_read_whole_is_not_judged(self):
        self.assertEqual(configcheck.check({"repos": ["a", "b"], "exclude": ["x"]}), [])

    def test_a_key_nobody_knows_without_a_close_one_has_no_hint(self):
        found = configcheck.check({"zzzzzzzzzzzz": 1})
        self.assertEqual(found, [{"path": "zzzzzzzzzzzz", "problem": "unknown", "hint": ""}])

    def test_things_that_are_not_a_configuration_give_nothing(self):
        for value in (None, [], "text", 5):
            self.assertEqual(configcheck.check(value), [])

    def test_the_list_is_bounded(self):
        found = configcheck.check({f"nokey{n}x": 1 for n in range(500)})
        self.assertEqual(len(found), configcheck.MAX_PROBLEMS)


class AtTheStart(unittest.TestCase):
    def run_report(self, raw):
        out = io.StringIO()
        with mock.patch.object(am.toolconfig, "raw_config", return_value=raw), contextlib.redirect_stdout(out):
            return am.report_config_problems(am.DEFAULTS), out.getvalue()

    def test_a_clean_file_says_nothing_and_starts(self):
        ok, text = self.run_report({"refresh_seconds": 60})
        self.assertTrue(ok)
        self.assertEqual(text, "")

    def test_a_problem_is_printed_and_the_monitor_starts_anyway_by_default(self):
        ok, text = self.run_report({"refresh_secnds": 30})
        self.assertTrue(ok)
        self.assertIn("refresh_secnds", text)
        self.assertIn("refresh_seconds", text)

    def test_with_the_strict_switch_on_the_monitor_does_not_start(self):
        ok, text = self.run_report({"refresh_secnds": 30, "config_check": {"strict": True}})
        self.assertFalse(ok)
        self.assertIn("config_check.strict", text)

    def test_with_the_strict_switch_on_and_nothing_wrong_it_starts(self):
        ok, _text = self.run_report({"config_check": {"strict": True}})
        self.assertTrue(ok)

    def test_the_switch_is_off_by_default_and_is_a_setting(self):
        from github_actions_monitor.app import settings_api
        self.assertIs(am.DEFAULTS["config_check"]["strict"], False)
        self.assertIn("config_check.strict", settings_api.FIELDS)
        self.assertFalse(configcheck.settings({})["strict"])

    def test_the_check_that_fails_by_itself_never_stops_the_start(self):
        with mock.patch.object(configcheck, "check", side_effect=RuntimeError("boom")), mock.patch.object(am.toolconfig, "raw_config", return_value={}):
            self.assertTrue(am.report_config_problems({}))


if __name__ == "__main__":
    unittest.main()
