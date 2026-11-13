# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The central panel as a base line that spends no allowance: git or http, its age, behind = not trusted, and Low mode asks live only for what the file cannot say."""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.sentinels import central_source  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402

EXAMPLE = (HERE / "tests" / "fixtures" / "central_sentinel_example.json").read_text(encoding="utf-8")
ASOF = 1767261600       # 2026-01-01T10:00:00Z


class CentralSource(unittest.TestCase):
    def setUp(self):
        central_source.reset()

    def test_it_is_off_by_default_and_wrong_values_fall_back(self):
        self.assertEqual(central_source.settings({})["source"], "off")
        self.assertEqual(central_source.settings({"central": {"source": "ftp", "max_age_minutes": 1}}), {"source": "off", "max_age_minutes": 120, "git_dir": ""})
        self.assertFalse(central_source.read({}, "o")["ok"])

    def test_http_reads_the_raw_file_and_says_how_old_it_is(self):
        urls = []
        result = central_source.read({"central": {"source": "http"}}, "demo-owner", opener=lambda url: urls.append(url) or EXAMPLE, now=ASOF + 600)
        self.assertEqual(urls, ["https://raw.githubusercontent.com/demo-owner/demo-owner/main/data/sentinel.json"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["age_seconds"], 600)
        self.assertFalse(result["stale"])
        self.assertEqual(central_source.red_repos(result), {"demo-beta-fw", "demo-gamma-api"})
        self.assertIn("source: central panel, 10 min ago: 2 red, 1 release candidate(s)", central_source.summary(result))

    def test_a_file_older_than_two_hours_is_behind_and_not_trusted(self):
        result = central_source.read({"central": {"source": "http"}}, "o", opener=lambda url: EXAMPLE, now=ASOF + 3 * 3600)
        self.assertTrue(result["ok"])
        self.assertTrue(result["stale"])
        self.assertEqual(central_source.red_repos(result), set(), "a base line that is behind says nothing about what is red")
        self.assertIn("behind", central_source.summary(result))
        fresh = central_source.read({"central": {"source": "http", "max_age_minutes": 600}}, "o", opener=lambda url: EXAMPLE, now=ASOF + 3 * 3600, force=True)
        self.assertFalse(fresh["stale"])

    def test_git_uses_fetch_and_show_and_no_api(self):
        calls = []

        def runner(args, cwd):
            calls.append(args)
            return (0, EXAMPLE, "") if args[1] == "show" else (0, "", "")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "demo-owner").mkdir()
            result = central_source.read({"central": {"source": "git"}}, "demo-owner", workspace=tmp, runner=runner, now=ASOF + 60)
        self.assertTrue(result["ok"])
        self.assertEqual(calls, [["git", "fetch", "origin", "main", "--quiet"], ["git", "show", "origin/main:data/sentinel.json"]])
        self.assertNotIn("gh", [c[0] for c in calls])

    def test_a_missing_clone_or_a_broken_file_is_no_base_line_and_never_an_error(self):
        self.assertFalse(central_source.read({"central": {"source": "git"}}, "o", workspace="", runner=lambda a, c: (0, "", ""))["ok"])
        for text in ("not json", "[1]", '{"asof": 3}', '{"asof": "x", "ci": {"red": "no"}}'):
            central_source.reset()
            result = central_source.read({"central": {"source": "http"}}, "o", opener=lambda url, t=text: t, now=1)
            self.assertFalse(result["ok"], text)
            self.assertEqual(central_source.red_repos(result), set())
            self.assertIn("not readable", central_source.summary(result))

    def test_the_reads_are_cached_between_cycles(self):
        calls = []
        config = {"central": {"source": "http"}}
        central_source.read(config, "o", opener=lambda url: calls.append(1) or EXAMPLE, now=ASOF)
        central_source.read(config, "o", opener=lambda url: calls.append(1) or EXAMPLE, now=ASOF + 100)
        self.assertEqual(len(calls), 1)
        central_source.read(config, "o", opener=lambda url: calls.append(1) or EXAMPLE, now=ASOF + 400)
        self.assertEqual(len(calls), 2)

    def test_the_red_rule_is_the_one_of_the_file(self):
        """The file keeps the same rows as redrule.red_workflows (repo, workflow, since): the monitor and the central panel agree on what is red."""
        from github_actions_monitor.data_pipeline import redrule
        runs = {"demo-beta-fw": [{"repo": "demo-beta-fw", "name": "ci", "path": "ci.yml", "status": "completed", "conclusion": "failure", "branch": "main", "started": "2026-01-01T08:00:00Z", "url": "u"}]}
        rows = redrule.red_workflows(runs, None)[0]
        data = json.loads(EXAMPLE)
        self.assertEqual({r["repo"] for r in rows}, {r["repo"] for r in data["ci"]["red"]} & {"demo-beta-fw"})
        self.assertTrue({"repo", "wf"} <= set(data["ci"]["red"][0]))      # the real rows: {"repo", "wf"}

    def test_the_real_file_of_the_profile_repository_is_read_when_it_is_there(self):
        real = Path("C:/Users/juane/Documents/GitHub/JuanenRac/data/sentinel.json")
        if not real.is_file():
            self.skipTest("no copy of the real file on this computer")
        result = central_source.read({"central": {"source": "http"}}, "o", opener=lambda url: real.read_text(encoding="utf-8"), now=time.time())
        self.assertTrue(result["ok"], result)
        self.assertIsInstance(result["data"]["ci"]["red"], list)
        for row in result["data"]["ci"]["red"]:
            self.assertTrue(row["repo"] and "wf" in row)

class Integration(unittest.TestCase):
    def setUp(self):
        central_source.reset()

    def test_the_state_carries_the_central_panel_with_its_age_and_does_not_trust_a_late_one(self):
        from github_actions_monitor.data_pipeline import signals
        fresh = central_source.read({"central": {"source": "http"}}, "o", opener=lambda url: EXAMPLE, now=ASOF + 600)
        doc = signals.state({"figures": {}}, [], "complete", {"central": fresh}, now=ASOF + 600)
        sig = [s for s in doc["signals"] if s["id"] == "health.central"][0]
        self.assertEqual(sig["level"], "info")
        self.assertIn("central panel, 10 min ago", sig["summary"])
        self.assertEqual({r["repo"] for r in sig["rows"]}, {"demo-beta-fw", "demo-gamma-api"})
        central_source.reset()
        late = central_source.read({"central": {"source": "http"}}, "o", opener=lambda url: EXAMPLE, now=ASOF + 5 * 3600)
        sig = [s for s in signals.state({"figures": {}}, [], "complete", {"central": late}, now=ASOF + 5 * 3600)["signals"] if s["id"] == "health.central"][0]
        self.assertEqual((sig["level"], sig["rows"]), ("watch", []))
        self.assertIn("behind", sig["summary"])
        off = signals.state({"figures": {}}, [], "complete", {"central": None})
        self.assertFalse([s for s in off["signals"] if s["id"] == "health.central"])

    def test_in_low_the_repositories_red_in_the_panel_are_read_live_and_the_rest_waits(self):
        from github_actions_monitor.app import actions_monitor as am
        from github_actions_monitor.app import modes
        central_source.read({"central": {"source": "http"}}, "o", opener=lambda url: EXAMPLE, now=ASOF + 60)
        original = am.central_result
        am.central_result = lambda config=None: central_source.read({"central": {"source": "http"}}, "o", opener=lambda url: EXAMPLE, now=ASOF + 60)
        old_mode = am.MODE
        try:
            am.MODE = modes.State()
            am.MODE.set("low", 0, {})
            am.RUN_CACHE["demo-beta-fw"] = {"runs": [], "at": 0, "error": None}
            am.RUN_CACHE["demo-alpha-core"] = {"runs": [], "at": 0, "error": None}
            config = {"hot_hours": 6, "refresh_seconds": 45, "cold_refresh_seconds": 600, "min_rate_remaining": 800}
            self.assertTrue(am.is_hot("demo-beta-fw", config, 0), "red in the panel: asked live")
            self.assertFalse(am.is_hot("demo-alpha-core", config, 0), "nothing in the panel and no runs: waits")
        finally:
            am.MODE = old_mode
            am.RUN_CACHE.pop("demo-beta-fw", None)
            am.RUN_CACHE.pop("demo-alpha-core", None)
            am.central_result = original

    def test_the_settings_exist_in_the_eight_languages(self):
        from github_actions_monitor.app import settings_api
        for key in ("central.source", "central.max_age_minutes"):
            self.assertIn(key, settings_api.FIELDS)
            for lang in i18n.LANGS:
                for prefix in ("cfg.f.", "cfg.h."):
                    self.assertNotEqual(i18n.tl(lang, prefix + key), prefix + key, (lang, key))
        for lang in i18n.LANGS:
            self.assertNotEqual(i18n.tl(lang, "ui.cfg_b_central"), "ui.cfg_b_central", lang)


if __name__ == "__main__":
    unittest.main()
