# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The terminal application edits lists and maps: how a list or a map is shown in its box and how the text typed becomes the value the server checks (no Textual needed)."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.ui import tui_textual as tt  # noqa: E402


class ListsAndMaps(unittest.TestCase):
    def test_a_list_is_shown_and_read_back_as_items_separated_by_commas(self):
        field = {"type": "names", "value": ["alpha", "beta"]}
        self.assertEqual(tt.format_value(field), "alpha, beta")
        self.assertEqual(tt.parse_value(field, "alpha, beta"), (["alpha", "beta"], None))
        self.assertEqual(tt.parse_value(field, " one ,, two ,"), (["one", "two"], None))
        self.assertEqual(tt.parse_value(field, ""), ([], None))      # an empty box clears the list
        self.assertEqual(tt.parse_value(field, "a, b, a"), (None, "names"))      # a repeated item is refused here, before the server is asked

    def test_a_map_of_numbers_is_name_equals_number(self):
        field = {"type": "intmap", "value": {"HYDRA": 3, "ARMOR": 5}}
        self.assertEqual(tt.format_value(field), "HYDRA=3, ARMOR=5")
        self.assertEqual(tt.parse_value(field, "HYDRA=3, ARMOR=5"), ({"HYDRA": 3, "ARMOR": 5}, None))
        self.assertEqual(tt.parse_value(field, ""), ({}, None))
        for bad in ("HYDRA", "HYDRA=x", "=3", "A=1, A=2"):
            self.assertEqual(tt.parse_value(field, bad), (None, "map"), bad)

    def test_the_other_types_are_shown_as_before_and_no_secure_list_is_offered(self):
        self.assertEqual(tt.format_value({"type": "int", "value": 7}), "7")
        self.assertEqual(tt.format_value({"type": "text", "value": None}), "")
        settings = {"groups": [{"id": "general", "fields": [{"key": "exclude", "type": "names", "value": []}, {"key": "listen.allowed_hosts", "type": "names", "secure": True, "value": []}]}]}
        self.assertEqual([f["key"] for _g, f in tt.editable_fields(settings)], ["exclude"])

    def test_what_the_terminal_sends_passes_the_check_of_the_server(self):
        for key, text in (("exclude", "repo-a, repo-b"), ("discovery.hide", "old-one")):
            value, why = tt.parse_value({"type": "names"}, text)
            self.assertIsNone(why)
            ok, clean = settings_api.check_value(key, value)
            self.assertTrue(ok, (key, clean))
            self.assertEqual(clean, value)


if __name__ == "__main__":
    unittest.main()
