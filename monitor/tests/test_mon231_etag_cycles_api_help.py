# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Two small closures: the conditional reads are noted after every cycle (the line of the cycle log, the last cycles in the ways of saving and in the doctor), and every error of the own
routes of the read API carries `help`, one sentence with the next step, in the eight languages."""
import tempfile
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor import i18n
from github_actions_monitor.app import api_v1
from github_actions_monitor.cli import doctor
from github_actions_monitor.data_pipeline import etagcache

LANGS = ("en", "es", "de", "fr", "it", "ja", "pt", "zh")
CODES = ("api.bad_cursor", "api.bad_limit", "api.unknown_field", "api.bad_profile", "api.server_error")


class TheCycleOfTheConditionalReads(unittest.TestCase):
    def cache(self):
        return etagcache.EtagCache(path=Path(tempfile.mkdtemp(prefix="cp_etag_")) / "etag.json")

    def test_a_cycle_reports_only_what_it_did(self):
        cache = self.cache()
        cache.calls, cache.saved, cache.misses, cache.no_etag = 10, 6, 4, 1
        first = cache.end_cycle()
        self.assertEqual((first["calls"], first["saved"], first["misses"], first["no_etag"], first["hit_pct"]), (10, 6, 4, 1, 60.0))
        cache.calls, cache.saved, cache.misses = 14, 9, 5
        second = cache.end_cycle()
        self.assertEqual((second["calls"], second["saved"], second["misses"], second["no_etag"]), (4, 3, 1, 0))
        quiet = cache.end_cycle()
        self.assertEqual((quiet["calls"], quiet["hit_pct"]), (0, None))
        self.assertEqual([row["calls"] for row in cache.stats()["recent_cycles"]], [10, 4, 0])

    def test_only_the_last_cycles_are_kept(self):
        cache = self.cache()
        for number in range(1, 41):
            cache.calls = number
            cache.end_cycle(keep=30)
        self.assertEqual(len(cache.stats()["recent_cycles"]), 30)

    def test_the_doctor_names_the_last_cycle_with_reads(self):
        ways = {"savings": {"ways": [{"id": "etag", "on": True, "saved": 150, "calls": 200, "no_etag": 0, "hit_pct": 75.0,
                                       "recent_cycles": [{"calls": 8, "saved": 6, "misses": 2, "no_etag": 0, "hit_pct": 75.0}, {"calls": 0, "saved": 0, "misses": 0, "no_etag": 0, "hit_pct": None}]}]}}
        status, detail = doctor.etag_check({}, [8765], reader=lambda port: ways)
        self.assertEqual(status, "ok")
        self.assertIn("last cycle 6/8", detail)


class TheHelpOfAnError(unittest.TestCase):
    def test_every_error_code_has_its_help_in_every_language(self):
        for lang in LANGS:
            with i18n.use_language(lang):
                for code in CODES:
                    _, body = api_v1.ApiError(400 if code != "api.server_error" else 500, code, max=200, field="x").envelope()
                    self.assertTrue(body.get("help"), (lang, code))
                    self.assertNotEqual(body["help"], code + ".help")
                    self.assertNotEqual(body["help"], body["message"])

    def test_the_help_follows_the_language_and_the_old_keys_stay(self):
        status, body = api_v1.ApiError(400, "api.bad_limit", max=200).envelope()
        self.assertEqual((status, body["error"], body["code"]), (400, "bad_request", "api.bad_limit"))
        self.assertIn("Guide: API_V1", body["help"])
        with i18n.use_language("es"):
            self.assertIn("Guía: API_V1", api_v1.ApiError(400, "api.bad_limit", max=200).envelope()[1]["help"])

    def test_a_code_without_help_has_no_help_key(self):
        self.assertNotIn("help", api_v1.ApiError(418, "api.not_a_code").envelope()[1])

    def test_the_guide_and_the_schema_know_the_field(self):
        guide = (Path(__file__).resolve().parent.parent / "docs" / "API_V1.md").read_text(encoding="utf-8")
        self.assertIn("`help`", guide)
        schema = api_v1.openapi("2.1.7") if hasattr(api_v1, "openapi") else None
        if schema:
            self.assertIn("help", schema["components"]["schemas"]["Error"]["properties"])


if __name__ == "__main__":
    unittest.main()
