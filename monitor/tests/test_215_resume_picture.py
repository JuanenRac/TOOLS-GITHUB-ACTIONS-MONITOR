# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The last picture is kept after every complete cycle and shown again, with its age, when the monitor starts: setting, limits, files that do not read, the page and the eight languages."""
import json
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.app import lastpicture, settings_api


def picture(age_seconds=60):
    when = datetime.fromtimestamp(time.time() - age_seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"updated": when, "repos": [{"name": "a/b"}], "loading": 0, "took": 1.5}


class Roundtrip(unittest.TestCase):
    def test_saved_picture_comes_back_marked_with_its_age(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            self.assertTrue(lastpicture.save(tmp, picture(300), {}))
            back = lastpicture.load(tmp, {})
            self.assertEqual(back["repos"], [{"name": "a/b"}])
            self.assertTrue(295 <= back["resumed"]["age_seconds"] <= 330)
            self.assertFalse(back["loading"])

    def test_a_picture_that_was_itself_resumed_or_is_incomplete_is_not_written_again(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            self.assertFalse(lastpicture.save(tmp, {**picture(), "loading": 3}, {}))
            self.assertFalse(lastpicture.save(tmp, {**picture(), "resumed": {"age_seconds": 5}}, {}))
            self.assertFalse((Path(tmp) / lastpicture.FILE_NAME).exists())

    def test_older_than_the_setting_is_ignored_and_zero_is_off_and_deletes_the_file(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            lastpicture.save(tmp, picture(3 * 3600), {})
            self.assertIsNotNone(lastpicture.load(tmp, {"startup": {"resume_max_age_hours": 4}}))
            self.assertIsNone(lastpicture.load(tmp, {"startup": {"resume_max_age_hours": 2}}))
            self.assertIsNone(lastpicture.load(tmp, {"startup": {"resume_max_age_hours": 0}}))
            self.assertFalse(lastpicture.save(tmp, picture(), {"startup": {"resume_max_age_hours": 0}}))
            self.assertFalse((Path(tmp) / lastpicture.FILE_NAME).exists())

    def test_files_that_do_not_read_are_ignored(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = Path(tmp) / lastpicture.FILE_NAME
            self.assertIsNone(lastpicture.load(tmp, {}))
            for text in ("not json", "[]", json.dumps({"format": 99, "data": picture()}), json.dumps({"format": 1, "data": {"updated": "yesterday"}}),
                         json.dumps({"format": 1, "data": picture(-4000)})):       # a picture "from the future" is not believed
                path.write_text(text, encoding="utf-8")
                self.assertIsNone(lastpicture.load(tmp, {}), text)

    def test_the_setting_is_read_as_a_whole_number_between_zero_and_a_week(self):
        for value, wanted in ((None, 12), (True, 12), ("5", 12), (-3, 0), (999, 168), (6, 6)):
            self.assertEqual(lastpicture.max_age_hours({"startup": {"resume_max_age_hours": value}}), wanted, value)
        self.assertEqual(lastpicture.max_age_hours({"startup": "x"}), 12)


class Surfaces(unittest.TestCase):
    def test_the_setting_is_in_the_schema_with_its_help_and_its_text_in_every_language(self):
        self.assertIn("startup.resume_max_age_hours", settings_api.META)
        root = Path(__file__).resolve().parents[1] / "assets" / "locales"
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            catalogue = json.loads((root / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("cfg.f.startup.resume_max_age_hours", "cfg.h.startup.resume_max_age_hours", "ui.resumed"):
                self.assertTrue(catalogue.get(key), (lang, key))
            self.assertIn("{mins}", catalogue["ui.resumed"], lang)

    def test_the_page_writes_the_age_of_a_resumed_picture(self):
        page = (Path(__file__).resolve().parents[1] / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('T("ui.resumed"', page)


if __name__ == "__main__":
    unittest.main()
