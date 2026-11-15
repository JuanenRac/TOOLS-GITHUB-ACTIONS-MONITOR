# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The phone web app: manifest, service worker, views and the settings of the expansion modules."""
import json
import unittest

import _testenv  # noqa: F401
from github_actions_monitor import phase4
from github_actions_monitor.phase4 import pwa


class Views(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(pwa.parse_view({"view": "alerts", "chrome": "0"}), ("alerts", False))
        self.assertEqual(pwa.parse_view({"view": "ALERTS"}), ("alerts", True))
        self.assertEqual(pwa.parse_view({"view": "<script>"}), ("now", True))
        self.assertEqual(pwa.parse_view(None), ("now", True))

    def test_every_view_has_endpoints_and_refresh_uses_the_api(self):
        for view in pwa.VIEWS:
            plan = pwa.refresh_plan(view, pwa.VIEW_ENDPOINTS)
            self.assertTrue(plan and all(p.startswith("/api/v1/") for p in plan), view)
        self.assertEqual(pwa.refresh_plan("zzz", pwa.VIEW_ENDPOINTS), pwa.VIEW_ENDPOINTS["now"])


class Manifest(unittest.TestCase):
    def test_default(self):
        m = pwa.manifest(phase4.DEFAULTS["pwa"], "pt")
        self.assertEqual((m["display"], m["lang"], m["scope"]), ("standalone", "pt-PT", "/"))
        self.assertEqual(len(m["icons"]), 2)
        self.assertTrue(all(s["url"].startswith("/?view=") for s in m["shortcuts"]))
        json.loads(pwa.manifest_json(phase4.DEFAULTS["pwa"], "zh"))

    def test_bad_values_fall_back(self):
        m = pwa.manifest({"name": "x" * 99, "short_name": "", "theme_color": "red", "background_color": "#12345"})
        base = phase4.DEFAULTS["pwa"]
        self.assertEqual((m["name"], m["short_name"], m["theme_color"], m["background_color"]), (base["name"], base["short_name"], base["theme_color"], base["background_color"]))

    def test_good_values_are_kept(self):
        m = pwa.manifest({"name": "Mine", "short_name": "M", "theme_color": "#112233", "background_color": "#ffffff"})
        self.assertEqual((m["name"], m["theme_color"]), ("Mine", "#112233"))


class Worker(unittest.TestCase):
    def test_never_caches_data_or_login(self):
        js = pwa.service_worker(phase4.DEFAULTS["pwa"], "2.1.0")
        for prefix in ("/api/", "/auth/", "/metrics"):
            self.assertIn(json.dumps(prefix), js)
        self.assertIn("NEVER.some", js)
        self.assertIn("req.method !== 'GET'", js)
        self.assertIn("url.origin !== self.location.origin", js)

    def test_cache_name_carries_the_version_and_is_clean(self):
        js = pwa.service_worker({"cache_name": "gam-shell"}, "2.1.0")
        self.assertIn('"gam-shell-2.1.0"', js)
        js = pwa.service_worker({"cache_name": "bad name\"; evil()"}, 'x"; evil();//')
        self.assertRegex(js, r'(?m)^const CACHE = "[A-Za-z0-9.-]+";$')
        self.assertEqual(js.count("evil"), 1)      # only the sanitised text of the build, inside the quoted name
        self.assertNotIn("@CACHE@", js)

    def test_the_script_is_balanced(self):
        js = pwa.service_worker(phase4.DEFAULTS["pwa"], "1")
        self.assertEqual(js.count("{"), js.count("}"))
        self.assertEqual(js.count("("), js.count(")"))

    def test_head_links(self):
        self.assertTrue(any("manifest" in line for line in pwa.page_head_links()))


class Settings(unittest.TestCase):
    def test_everything_is_off_by_default(self):
        s = phase4.settings({})
        for section in s.values():
            self.assertFalse(section["enabled"])
        self.assertFalse(s["proposals"]["execute_enabled"])
        self.assertFalse(s["proposals"]["merge_allowed"])
        self.assertTrue(s["assistant"]["airgapped"])
        self.assertFalse(s["assistant"]["log_prompts"])
        self.assertFalse(s["plugins"]["allow_third_party"])

    def test_good_values_merge_and_bad_ones_keep_the_default(self):
        s = phase4.settings({"expansion": {"api_v1": {"enabled": True, "max_limit": 5000, "default_limit": "x"}, "scale": {"queue_depth": 20, "bogus": 1},
                                           "plugins": {"directories": ["a", 3]}, "assistant": {"enabled": 1}}})
        self.assertTrue(s["api_v1"]["enabled"])
        self.assertEqual(s["api_v1"]["max_limit"], phase4.DEFAULTS["api_v1"]["max_limit"])
        self.assertEqual(s["api_v1"]["default_limit"], 50)
        self.assertEqual(s["scale"]["queue_depth"], 20)
        self.assertNotIn("bogus", s["scale"])
        self.assertEqual(s["plugins"]["directories"], ["plugins"])
        self.assertFalse(s["assistant"]["enabled"])

    def test_default_limit_is_capped_by_the_maximum(self):
        s = phase4.settings({"expansion": {"api_v1": {"default_limit": 100, "max_limit": 10}}})
        self.assertEqual(s["api_v1"]["default_limit"], 10)

    def test_non_dict_inputs(self):
        for bad in (None, [], {"expansion": []}, {"expansion": {"api_v1": 5}}):
            self.assertEqual(phase4.settings(bad)["api_v1"]["max_limit"], 200)

    def test_defaults_are_not_shared(self):
        a = phase4.settings({})
        a["plugins"]["directories"].append("x")
        self.assertEqual(phase4.DEFAULTS["plugins"]["directories"], ["plugins"])


if __name__ == "__main__":
    unittest.main()
