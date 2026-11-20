# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The clock of the webhook receiver (`webhook.clock_skew_s`): the clock of this computer is the reference, an event is not stale or dead because two clocks differ by a few minutes, and the batch of GraphQL
is on by default after its measure. No network."""
import json
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import graphql_checks, savings  # noqa: E402
from github_actions_monitor.security import webhook  # noqa: E402

NOW = 1_800_000_000.0
QUIET = {"runs": [{"status": "completed", "conclusion": "success", "started": "2020-01-01T00:00:00Z"}], "at": NOW - 5000, "full_at": NOW - 5000, "head": "a" * 40, "error": None, "fails": 0}


def config(skew=None, per_repo=True):
    cfg = {"savings": {"webhook_first": True, "webhook_live_per_repo": per_repo, "webhook_window_minutes": 30, "webhook_full_minutes": 120}, "webhook": {"enabled": True}}
    if skew is not None:
        cfg["webhook"]["clock_skew_s"] = skew
    return cfg


def stamp(moment):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(moment))


class Reset(unittest.TestCase):
    def setUp(self):
        savings.LAST_WEBHOOK["at"] = 0.0
        savings.LAST_WEBHOOK_REPO.clear()
        webhook.reset()


class TheSetting(unittest.TestCase):
    def test_it_is_300_seconds_between_0_and_3600_and_nonsense_keeps_the_default(self):
        self.assertEqual(webhook.guard_settings({})["clock_skew_s"], 300)
        self.assertEqual(am.DEFAULTS["webhook"]["clock_skew_s"], 300)
        for bad in ("5", True, -1, 3601, 2.5, None):
            self.assertEqual(webhook.guard_settings({"webhook": {"clock_skew_s": bad}})["clock_skew_s"], 300, bad)
        self.assertEqual(webhook.guard_settings({"webhook": {"clock_skew_s": 0}})["clock_skew_s"], 0)
        self.assertEqual(webhook.guard_settings({"webhook": {"clock_skew_s": 3600}})["clock_skew_s"], 3600)
        self.assertEqual(savings.clock_skew({"webhook": {"clock_skew_s": 60}}), 60)
        self.assertEqual(savings.clock_skew({}), 300)
        self.assertTrue(settings_api.check_value("webhook.clock_skew_s", 600)[0])
        self.assertFalse(settings_api.check_value("webhook.clock_skew_s", 5000)[0])


class Stale(unittest.TestCase):
    def body(self, moment):
        return json.dumps({"workflow_run": {"updated_at": stamp(moment)}}).encode()

    def test_an_event_a_little_older_than_the_window_is_not_stale_when_the_clocks_differ(self):
        window = 3600
        body = self.body(NOW - window - 120)      # two minutes past the window, within the skew
        self.assertTrue(webhook.event_is_stale("workflow_run", body, window, now=NOW))
        self.assertFalse(webhook.event_is_stale("workflow_run", body, window, now=NOW, skew=300))
        self.assertTrue(webhook.event_is_stale("workflow_run", self.body(NOW - window - 400), window, now=NOW, skew=300))
        self.assertFalse(webhook.event_is_stale("workflow_run", self.body(NOW + 900), window, now=NOW, skew=0), "an event dated ahead is never stale")


class Alive(Reset):
    def test_a_delivery_marked_while_the_clock_was_ten_minutes_ahead_does_not_kill_the_repository(self):
        cfg = config()
        savings.note_webhook(NOW + 600, repo="one")      # marked by a clock that has been set back by ten minutes since
        self.assertTrue(savings.quiet_by_webhook(cfg, QUIET, NOW, repo="one"), "the event happened: the repository is alive")
        self.assertEqual(savings.LAST_WEBHOOK_REPO["one"], NOW, "it ages from the moment it is noticed, not from a moment that has not come")
        self.assertFalse(savings.quiet_by_webhook(cfg, QUIET, NOW + 31 * 60, repo="one"), "and it goes quiet after the window like any other")

    def test_a_mark_inside_the_skew_counts_as_it_is_and_one_a_day_ahead_is_not_believed(self):
        cfg = config()
        savings.note_webhook(NOW + 200, repo="near")
        self.assertTrue(savings.webhook_alive(cfg, NOW, repo="near"))
        self.assertEqual(savings.LAST_WEBHOOK_REPO["near"], NOW + 200)
        savings.note_webhook(NOW + 2 * 86400, repo="far")
        self.assertFalse(savings.webhook_alive(cfg, NOW, repo="far"))

    def test_the_skew_of_zero_keeps_the_marks_exact(self):
        cfg = config(skew=0)
        savings.note_webhook(NOW + 60, repo="one")
        self.assertTrue(savings.webhook_alive(cfg, NOW, repo="one"), "still believed (a clock set back), and settled to now")
        self.assertEqual(savings.LAST_WEBHOOK_REPO["one"], NOW)

    def test_the_general_mark_and_the_count_of_live_repositories_follow_the_same_rule(self):
        cfg = config(per_repo=True)
        savings.note_webhook(NOW + 600, repo="a")
        savings.note_webhook(NOW + 700, repo="b")
        savings.note_webhook(NOW + 5 * 86400, repo="c")
        self.assertEqual(savings.live_repos(cfg, NOW), 2)
        flat = config(per_repo=False)
        savings.LAST_WEBHOOK["at"] = NOW + 600
        self.assertTrue(savings.webhook_alive(flat, NOW))
        self.assertEqual(savings.LAST_WEBHOOK["at"], NOW)

    def test_the_coverage_is_live_for_an_event_marked_ahead_and_waiting_for_one_three_days_ahead(self):
        cfg = config()
        cfg["webhook"]["secret_env"] = "SKEW_TEST_SECRET"
        old = webhook.active
        webhook.active = lambda c: True
        try:
            webhook.note_accepted(NOW + 600)
            self.assertEqual(webhook.coverage(cfg, now=NOW)["state"], "live")
            self.assertEqual(webhook.coverage(cfg, now=NOW + 31 * 60)["state"], "quiet", "it ages from the moment it was noticed")
            webhook.reset()
            webhook.note_accepted(NOW + 3 * 86400)
            self.assertEqual(webhook.coverage(cfg, now=NOW)["state"], "waiting")
        finally:
            webhook.active = old


class TheBatch(unittest.TestCase):
    def test_the_batch_of_graphql_is_on_by_default_since_its_measure(self):
        self.assertTrue(am.DEFAULTS["network"]["graphql_checks"])
        self.assertEqual(graphql_checks.settings({}), {"enabled": True, "batch": 20})
        self.assertEqual(graphql_checks.settings({"network": {}}), {"enabled": True, "batch": 20})
        self.assertFalse(graphql_checks.settings({"network": {"graphql_checks": False}})["enabled"])
        self.assertFalse(graphql_checks.settings({"network": {"graphql_checks": "yes"}})["enabled"], "nothing but a clean true turns it on or keeps it on")

    def test_a_batch_spares_the_calls_the_measure_found_and_falls_back_for_the_unanswered(self):
        names = [f"repo{i}" for i in range(40)]

        def call(text):
            answer = {"data": {"rateLimit": {"cost": 1, "remaining": 4000}}}
            for index in range(20):
                if f"r{index}:" in text:
                    answer["data"][f"r{index}"] = {"defaultBranchRef": {"name": "main", "target": {"oid": "a" * 40, "checkSuites": {"nodes": []}}}}
            return answer
        for key in graphql_checks.STATS:
            graphql_checks.STATS[key] = 0
        found, rest = graphql_checks.read_batches("owner", names, 20, call)
        self.assertEqual((len(found), rest), (40, []))
        self.assertEqual(graphql_checks.STATS["calls"], 2)      # two calls instead of forty
        self.assertGreaterEqual(1 - graphql_checks.STATS["calls"] / len(names), 0.30, "the rule: it stays on only while it saves at least 30 % of the calls")
        self.assertEqual(graphql_checks.STATS["errors"], 0)
        broken_found, broken_rest = graphql_checks.read_batches("owner", names[:20], 20, lambda text: (_ for _ in ()).throw(RuntimeError("HTTP 403")))
        self.assertEqual((broken_found, broken_rest), ({}, names[:20]))      # a failure sends the batch to REST: nothing is lost


if __name__ == "__main__":
    unittest.main()
