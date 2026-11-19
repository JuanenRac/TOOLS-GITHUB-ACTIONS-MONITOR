# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The records kept by state_io carry a version of their schema: the callers never see it, a record without it still reads, and a record of a newer version is left aside and named."""
import json
import tempfile
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.storage import state_io


class Marked(unittest.TestCase):
    def test_a_saved_object_carries_the_version_and_reads_back_without_it(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = Path(tmp) / "state.json"
            state_io.save_text(path, json.dumps({"alerts": {"a": 1}}, indent=2))
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw["schema_version"], state_io.RECORD_SCHEMA)
            self.assertEqual(list(raw)[0], "schema_version")
            self.assertEqual(state_io.load_json(path), {"alerts": {"a": 1}})

    def test_an_empty_object_and_a_list_and_a_text_that_is_not_json(self):
        self.assertEqual(json.loads(state_io.mark("{}")), {"schema_version": state_io.RECORD_SCHEMA})
        self.assertEqual(state_io.mark("[1, 2]"), "[1, 2]")
        self.assertEqual(state_io.mark("{not json"), "{not json")
        self.assertEqual(state_io.mark('{"schema_version": 7}'), '{"schema_version": 7}')

    def test_a_record_from_before_the_mark_reads_as_version_zero(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = Path(tmp) / "old.json"
            path.write_text('{"per_repo": {}}', encoding="utf-8")
            self.assertEqual(state_io.load_json(path), {"per_repo": {}})
            self.assertNotIn("old.json", state_io.NEWER)


class Newer(unittest.TestCase):
    def test_a_newer_record_is_left_aside_and_named_and_a_good_one_clears_the_name(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = Path(tmp) / "future.json"
            path.write_text(json.dumps({"schema_version": state_io.RECORD_SCHEMA + 1, "x": 1}), encoding="utf-8")
            with self.assertRaises(ValueError):
                state_io.load_json(path)
            self.assertEqual(state_io.NEWER["future.json"], state_io.RECORD_SCHEMA + 1)
            state_io.save_text(path, json.dumps({"x": 2}))
            self.assertEqual(state_io.load_json(path), {"x": 2})
            self.assertNotIn("future.json", state_io.NEWER)

    def test_a_version_that_is_not_a_whole_number_is_also_left_aside(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            for bad in ("2", True, -1, None, 1.5):
                path = Path(tmp) / "bad.json"
                path.write_text(json.dumps({"schema_version": bad}), encoding="utf-8")
                with self.assertRaises(ValueError, msg=repr(bad)):
                    state_io.load_json(path)


if __name__ == "__main__":
    unittest.main()
