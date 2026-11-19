# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`savings.webhook_live_per_repo`: with it on, a quiet repository is spared its slow read only when an event of ITS OWN arrived in the window; a repository whose webhook never worked is read as always.
Off by default, and off nothing changes. The memory of the repositories is bounded. No network."""
import json
import time
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import savings  # noqa: E402
from github_actions_monitor.security import webhook  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
NOW = 1_800_000_000.0
QUIET = {"runs": [{"status": "completed", "conclusion": "success", "started": "2020-01-01T00:00:00Z"}], "at": NOW - 5000, "full_at": NOW - 5000, "head": "a" * 40, "error": None, "fails": 0}


def config(per_repo=True, first=True):
    return {"savings": {"webhook_first": first, "webhook_live_per_repo": per_repo, "webhook_window_minutes": 30, "webhook_full_minutes": 120}, "webhook": {"enabled": True}}


class Reset(unittest.TestCase):
    def setUp(self):
        savings.STATS.update({"webhook": 0, "feed": 0, "git": 0, "unknown": 0})
        savings.LAST_WEBHOOK["at"] = 0.0
        savings.LAST_WEBHOOK_REPO.clear()
        webhook.reset()


class TheSwitch(Reset):
    def test_it_is_off_by_default_and_a_bad_value_is_off(self):
        self.assertFalse(savings.settings({})["webhook_live_per_repo"])
        self.assertFalse(am.DEFAULTS["savings"]["webhook_live_per_repo"])
        self.assertFalse(savings.settings({"savings": {"webhook_live_per_repo": "yes"}})["webhook_live_per_repo"])
        self.assertTrue(savings.settings(config())["webhook_live_per_repo"])

    def test_it_is_on_the_page_in_eight_languages_with_its_tip(self):
        key = "savings.webhook_live_per_repo"
        self.assertIn(key, settings_api.FIELDS)
        for lang in i18n.LANGS:
            table = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for name in (settings_api.help_key(key), "cfg.f." + key, "cfg.t." + key):
                self.assertTrue(table.get(name), (lang, name))


class WhoIsAlive(Reset):
    def test_without_the_switch_any_event_counts_for_every_repository(self):
        savings.note_webhook(NOW - 60, repo="one")
        self.assertTrue(savings.webhook_alive(config(per_repo=False), NOW, repo="two"))
        self.assertTrue(savings.quiet_by_webhook(config(per_repo=False), QUIET, NOW, repo="two"))

    def test_with_the_switch_only_the_events_of_the_repository_count(self):
        savings.note_webhook(NOW - 60, repo="one")
        cfg = config()
        self.assertTrue(savings.quiet_by_webhook(cfg, QUIET, NOW, repo="one"))
        self.assertFalse(savings.quiet_by_webhook(cfg, QUIET, NOW, repo="two"), "its webhook never delivered anything")
        self.assertTrue(savings.webhook_alive(cfg, NOW), "no repository named: the general answer")

    def test_the_window_the_safety_net_and_the_clock_still_apply(self):
        cfg = config()
        savings.note_webhook(NOW - 60, repo="one")
        self.assertFalse(savings.quiet_by_webhook(cfg, QUIET, NOW + 31 * 60, repo="one"), "the repository went quiet")
        self.assertFalse(savings.quiet_by_webhook(cfg, dict(QUIET, full_at=NOW - 121 * 60), NOW, repo="one"), "a full read is due")
        savings.note_webhook(NOW + 3 * 86400, repo="ahead")
        self.assertFalse(savings.quiet_by_webhook(cfg, QUIET, NOW, repo="ahead"), "a mark ahead of the clock is not believed")

    def test_webhook_first_off_spares_nothing_whatever_the_switch_says(self):
        savings.note_webhook(NOW - 60, repo="one")
        self.assertFalse(savings.quiet_by_webhook(config(first=False), QUIET, NOW, repo="one"))

    def test_a_name_that_is_not_a_repository_name_is_not_remembered(self):
        for bad in (None, "", "a/b", "x" * 200, 5, "a b"):
            savings.note_webhook(NOW, repo=bad)
        self.assertEqual(savings.LAST_WEBHOOK_REPO, {})

    def test_the_memory_is_bounded_and_forgets_the_oldest(self):
        with mock.patch.object(savings, "MAX_REPOS", 20):
            for index in range(25):
                savings.note_webhook(NOW + index, repo=f"repo{index}")
            self.assertLessEqual(len(savings.LAST_WEBHOOK_REPO), 20)
            self.assertIn("repo24", savings.LAST_WEBHOOK_REPO)
            self.assertNotIn("repo0", savings.LAST_WEBHOOK_REPO)


class TheCycle(Reset):
    def test_the_cold_turn_spares_only_the_repository_that_has_its_own_event(self):
        cfg = {**am.DEFAULTS, **config(), "mode": "full"}
        now = time.time()
        savings.note_webhook(now - 5, repo="alive")
        am.RUN_CACHE["alive"] = dict(QUIET, at=now - 1000, full_at=now - 1000)
        am.RUN_CACHE["silent"] = dict(QUIET, at=now - 1000, full_at=now - 1000)
        reads = []
        with mock.patch.object(am, "fetch_runs", side_effect=lambda repo, n: reads.append(repo) or ([], None)), mock.patch.object(am, "graphql_cold", return_value={}):
            am.refresh_runs(["alive", "silent"], cfg)
        self.assertEqual(reads, ["silent"])
        self.assertEqual(savings.STATS["webhook"], 1)

    def test_live_repos_counts_the_repositories_with_an_event_in_the_window(self):
        savings.note_webhook(NOW - 60, repo="a")
        savings.note_webhook(NOW - 90 * 60, repo="b")
        self.assertEqual(savings.live_repos(config(), NOW), 1)
        self.assertEqual(savings.live_repos(config(per_repo=False), NOW), 0)


class TheCoverageRecord(Reset):
    def test_it_names_the_live_repositories_only_with_the_switch(self):
        webhook.note_accepted(now=1000)
        savings.note_webhook(1000, repo="one")
        with mock.patch.dict("os.environ", {webhook.SECRET_ENV: "s" * 40}):
            self.assertNotIn("live_repos", webhook.coverage(config(per_repo=False), now=1060))
            self.assertEqual(webhook.coverage(config(), now=1060)["live_repos"], 1)


if __name__ == "__main__":
    unittest.main()
