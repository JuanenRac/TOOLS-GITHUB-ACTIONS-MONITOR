# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Reading less from the allowance: a quiet repository passes its slow turn with no call while the webhook is alive or while a free source says that nothing was pushed, a full read still comes
at the safety interval, anything unknown means 'read it as always', and the Quota tab says what each way spared. Everything is off by default."""
import json
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.data_pipeline import savings  # noqa: E402

SHA = "a" * 40
OTHER = "b" * 40
FEED = f"""<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom"><id>tag:github.com,2008:/o/r/commits/main</id><title>Recent Commits</title>
<entry><id>tag:github.com,2008:Grit::Commit/{SHA}</id><title>fix</title></entry><entry><id>tag:github.com,2008:Grit::Commit/{OTHER}</id></entry></feed>"""
NOW = 1_800_000_000.0
QUIET = {"runs": [{"status": "completed", "conclusion": "success", "started": "2020-01-01T00:00:00Z"}], "at": NOW - 5000, "full_at": NOW - 5000, "head": SHA, "error": None, "fails": 0}


class Answer:
    def __init__(self, body, status=200, kind="application/atom+xml"):
        self.body, self.status, self.headers = body.encode("utf-8"), status, {"Content-Type": kind}

    def read(self, size=-1):
        return self.body[:size] if size >= 0 else self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def opener(body=FEED, status=200, kind="application/atom+xml"):
    return lambda request, timeout=10: Answer(body, status, kind)


class Reset(unittest.TestCase):
    def setUp(self):
        savings.STATS.update({"webhook": 0, "feed": 0, "git": 0, "unknown": 0})
        savings.LAST_WEBHOOK["at"] = 0.0


class TheSettings(Reset, unittest.TestCase):
    def test_everything_is_off_by_default_and_a_bad_value_gives_the_default(self):
        cfg = savings.settings({})
        self.assertEqual((cfg["webhook_first"], cfg["feeds"]["enabled"], cfg["feeds"]["method"]), (False, False, "atom"))
        bad = savings.settings({"savings": {"webhook_first": "yes", "webhook_window_minutes": 0, "webhook_full_minutes": True, "feeds": {"enabled": 1, "method": "ftp", "max_age_minutes": 1}}})
        self.assertEqual((bad["webhook_first"], bad["webhook_window_minutes"], bad["webhook_full_minutes"], bad["feeds"]["enabled"], bad["feeds"]["method"], bad["feeds"]["max_age_minutes"]), (False, 60, 360, False, "atom", 240))
        self.assertEqual(am.DEFAULTS["savings"]["feeds"]["enabled"], False)

    def test_the_free_sources_are_never_used_when_airgapped(self):
        self.assertFalse(savings.settings({"airgapped": True, "savings": {"feeds": {"enabled": True}}})["feeds"]["enabled"])


class WebhookFirst(Reset, unittest.TestCase):
    CFG = {"savings": {"webhook_first": True, "webhook_window_minutes": 30, "webhook_full_minutes": 120}}

    def test_a_quiet_repository_is_spared_only_while_the_webhook_is_alive(self):
        self.assertFalse(savings.quiet_by_webhook(self.CFG, QUIET, NOW), "no event yet: nothing changes")
        savings.note_webhook(NOW - 60)
        self.assertTrue(savings.quiet_by_webhook(self.CFG, QUIET, NOW))
        self.assertFalse(savings.quiet_by_webhook(self.CFG, QUIET, NOW + 31 * 60), "the webhook went quiet")
        self.assertFalse(savings.quiet_by_webhook({}, QUIET, NOW), "the switch is off")

    def test_a_full_read_still_comes_at_the_safety_interval(self):
        savings.note_webhook(NOW)
        old = dict(QUIET, full_at=NOW - 121 * 60)
        self.assertFalse(savings.quiet_by_webhook(self.CFG, old, NOW))

    def test_the_cycle_skips_the_slow_turn_and_counts_it(self):
        entry = dict(QUIET)
        savings.note_webhook(NOW - 10)
        self.assertTrue(am.spare_by_webhook(entry, self.CFG, NOW))
        self.assertEqual(entry["at"], NOW, "its turn comes again after the usual interval")
        self.assertEqual(entry["full_at"], NOW - 5000, "the last full read is not touched")
        self.assertEqual(savings.STATS["webhook"], 1)
        self.assertFalse(am.spare_by_webhook(dict(QUIET), {}, NOW))


class FreeSources(Reset, unittest.TestCase):
    CFG = {"savings": {"feeds": {"enabled": True, "method": "atom", "max_age_minutes": 240}}}

    def test_the_newest_commit_is_read_from_the_feed(self):
        self.assertEqual(savings.head_from_atom(FEED), SHA)
        self.assertEqual(savings.head_from_atom("<html>not a feed</html>"), "")
        self.assertEqual(savings.head_from_atom("not xml at all"), "")
        self.assertEqual(savings.head_atom("o", "r", opener()), SHA)
        self.assertEqual(savings.head_atom("o", "r", opener(status=404)), "")
        self.assertEqual(savings.head_atom("o", "r", lambda request, timeout=10: (_ for _ in ()).throw(OSError("down"))), "")
        self.assertEqual(savings.head_atom("o/../x", "r", opener()), "", "a name that is not a plain name is not asked")

    def test_the_feed_cannot_load_an_external_entity(self):
        evil = '<?xml version="1.0"?><!DOCTYPE feed [<!ENTITY x SYSTEM "file:///etc/passwd">]><feed xmlns="http://www.w3.org/2005/Atom"><id>&x;</id></feed>'
        self.assertEqual(savings.head_from_atom(evil), "")

    def test_git_ls_remote_has_no_prompt_and_a_fixed_argument_list(self):
        seen = []

        def run(args):
            seen.append(args)
            return 0, f"{SHA}\tHEAD\n"
        self.assertEqual(savings.head_git("o", "r", run), SHA)
        self.assertEqual(seen[0], ["git", "-c", "credential.helper=", "ls-remote", "https://github.com/o/r.git", "HEAD"])
        self.assertEqual(savings.head_git("o", "r", lambda args: (128, "fatal: could not read Username")), "")
        self.assertEqual(savings.head_git("o", "r;rm", run), "")

    def test_auto_tries_the_feed_and_then_git(self):
        cfg = {"savings": {"feeds": {"enabled": True, "method": "auto"}}}
        self.assertEqual(savings.head(cfg, "o", "r", opener(), lambda a: (0, f"{OTHER}\tHEAD")), (SHA, "feed"))
        self.assertEqual(savings.head(cfg, "o", "r", opener(status=404), lambda a: (0, f"{OTHER}\tHEAD")), (OTHER, "git"))
        self.assertEqual(savings.head(self.CFG, "o", "r", opener(status=404), lambda a: (0, f"{OTHER}\tHEAD")), ("", ""), "atom alone does not try git")

    def test_a_repository_whose_head_did_not_move_is_spared(self):
        self.assertTrue(savings.feed_quiet(self.CFG, "o", "r", dict(QUIET), NOW, opener()))
        self.assertEqual(savings.STATS["feed"], 1)

    def test_everything_else_means_read_it_as_always(self):
        self.assertFalse(savings.feed_quiet(self.CFG, "o", "r", dict(QUIET, head=OTHER), NOW, opener()), "a newer commit")
        self.assertFalse(savings.feed_quiet(self.CFG, "o", "r", dict(QUIET), NOW, opener(status=404)), "private or unknown")
        self.assertEqual(savings.STATS["unknown"], 1)
        self.assertFalse(savings.feed_quiet(self.CFG, "o", "r", dict(QUIET, head=""), NOW, opener()), "no commit stored with the last read")
        self.assertFalse(savings.feed_quiet(self.CFG, "o", "r", dict(QUIET, full_at=NOW - 241 * 60), NOW, opener()), "the safety interval")
        self.assertFalse(savings.feed_quiet({}, "o", "r", dict(QUIET), NOW, opener()), "off")
        for run in ({"status": "in_progress", "conclusion": None}, {"status": "completed", "conclusion": "failure"}, {"status": "completed", "conclusion": "cancelled"}):
            self.assertFalse(savings.feed_quiet(self.CFG, "o", "r", dict(QUIET, runs=[run]), NOW, opener()), run)
        self.assertEqual(savings.STATS["feed"], 0)

    def test_nothing_is_asked_when_it_is_off(self):
        called = []
        self.assertEqual(savings.remember_head({}, "o", "r", lambda *a, **k: called.append(1)), "")
        self.assertEqual(called, [])


class InTheCycle(Reset, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.saved = (dict(am.RUN_CACHE), dict(am.HEADS_PENDING))
        am.RUN_CACHE.clear()
        am.HEADS_PENDING.clear()

    def tearDown(self):
        am.RUN_CACHE.clear()
        am.RUN_CACHE.update(self.saved[0])
        am.HEADS_PENDING.clear()
        am.HEADS_PENDING.update(self.saved[1])

    def config(self, **savings_block):
        return {**am.DEFAULTS, "savings": savings_block, "cold_refresh_seconds": 600}

    def test_a_quiet_repository_with_the_feed_on_is_not_read_and_a_moved_one_is(self):
        config = self.config(feeds={"enabled": True, "method": "atom"})
        now = time.time()
        am.RUN_CACHE["still"] = dict(QUIET, at=now - 1000, full_at=now - 1000)
        am.RUN_CACHE["moved"] = dict(QUIET, at=now - 1000, full_at=now - 1000, head=OTHER)
        reads = []

        def feed(owner, repo, opener=None, timeout=10):
            return SHA

        with mock.patch.object(savings, "head_atom", feed), mock.patch.object(am, "is_hot", return_value=False), mock.patch.object(am, "fetch_runs", side_effect=lambda repo, n: reads.append(repo) or ([], None)), \
                mock.patch.object(am, "graphql_cold", return_value={}):
            am.refresh_runs(["still", "moved"], config)
        self.assertEqual(reads, ["moved"])
        self.assertGreater(am.RUN_CACHE["still"]["at"], now - 5, "its slow turn starts again")
        self.assertEqual(am.RUN_CACHE["moved"]["head"], SHA, "the newest commit seen before the read is stored with it")
        self.assertEqual(savings.STATS["feed"], 1)

    def test_everything_is_read_when_the_savings_are_off(self):
        now = time.time()
        am.RUN_CACHE["still"] = dict(QUIET, at=now - 1000, full_at=now - 1000)
        reads = []
        with mock.patch.object(am, "is_hot", return_value=False), mock.patch.object(am, "fetch_runs", side_effect=lambda repo, n: reads.append(repo) or ([], None)), mock.patch.object(am, "graphql_cold", return_value={}):
            am.refresh_runs(["still"], self.config())
        self.assertEqual(reads, ["still"])

    def test_the_webhook_spares_the_cold_turn_and_a_forced_repository_is_still_read(self):
        config = self.config(webhook_first=True, webhook_window_minutes=60, webhook_full_minutes=360)
        now = time.time()
        savings.note_webhook(now - 5)
        am.RUN_CACHE["still"] = dict(QUIET, at=now - 1000, full_at=now - 1000)
        am.RUN_CACHE["touched"] = dict(QUIET, at=now - 1000, full_at=now - 1000)
        reads = []
        am.HOT_FORCED.add("touched")
        with mock.patch.object(am, "fetch_runs", side_effect=lambda repo, n: reads.append(repo) or ([], None)), mock.patch.object(am, "graphql_cold", return_value={}):
            am.refresh_runs(["still", "touched"], config)
        self.assertEqual(reads, ["touched"])
        self.assertEqual(savings.STATS["webhook"], 1)


class WhatTheQuotaTabSays(Reset, unittest.TestCase):
    def test_the_report_names_every_way_and_adds_up_what_they_spared(self):
        savings.count_webhook(3)
        savings.STATS["feed"] = 4
        report = am.savings_report({**am.DEFAULTS, "savings": {"webhook_first": True, "feeds": {"enabled": True, "method": "auto"}}})
        ways = {w["id"]: w for w in report["ways"]}
        self.assertEqual(set(ways), {"etag", "graphql", "webhook", "feed", "git", "central"})
        self.assertEqual((ways["webhook"]["on"], ways["webhook"]["spared"], ways["feed"]["spared"]), (True, 3, 4))
        self.assertEqual(report["total"], 7)
        self.assertFalse(am.savings_report(dict(am.DEFAULTS))["ways"][3]["on"])
        json.dumps(report)

    def test_the_settings_and_the_texts_exist_in_the_eight_languages(self):
        from github_actions_monitor.app import settings_api
        for key in ("savings.webhook_first", "savings.webhook_window_minutes", "savings.webhook_full_minutes", "savings.feeds.enabled", "savings.feeds.method", "savings.feeds.max_age_minutes"):
            self.assertIn(key, settings_api.FIELDS, key)
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, "cfg.f." + key), "cfg.f." + key, (lang, key))
                self.assertNotEqual(i18n.tl(lang, "cfg.h." + key), "cfg.h." + key, (lang, key))
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ui.cfg_b_savings", "ui.qt_saved", "ui.qt_off", *[f"ui.qt_w_{w}" for w in ("etag", "graphql", "webhook", "feed", "git", "central")]):
                self.assertTrue(catalogue.get(key), (lang, key))
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("d.savings", page)

    def test_the_module_sends_nothing_but_a_get_and_a_fixed_git_command(self):
        text = (HERE / "src" / "github_actions_monitor" / "data_pipeline" / "savings.py").read_text(encoding="utf-8")
        for forbidden in ("method=", '"POST"', "shell=True", "os.system", "data="):
            self.assertNotIn(forbidden, text, forbidden)


if __name__ == "__main__":
    unittest.main()
