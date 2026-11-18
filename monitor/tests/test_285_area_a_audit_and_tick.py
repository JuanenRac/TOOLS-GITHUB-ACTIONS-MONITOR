# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The log of actions keeps a number of rotated files that can be chosen and can be made a condition of the actions (`audit_log.required`: no action while it cannot be written), the stages of a tick of the
sentinel share one count of calls, and a repository whose reads keep failing is left alone for a while instead of being read in every cycle."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_216_load as t216  # noqa: E402
import test_275_area_a_sentinel_quota as t275  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am, settings_api  # noqa: E402
from github_actions_monitor.security import audit_log  # noqa: E402
from github_actions_monitor.util import resilience  # noqa: E402
from test_200_contract import Served  # noqa: E402


class TheGenerations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(audit_log, "FILE", Path(self.tmp.name) / "audit_actions.jsonl")
        patcher.start()
        self.addCleanup(patcher.stop)
        real = audit_log.settings
        patcher = mock.patch.object(audit_log, "settings", lambda config: dict(real(config), max_mb=0.003))      # a file is rotated past 3 KB: a few lines make a generation
        patcher.start()
        self.addCleanup(patcher.stop)
        self.counter = 0

    def write(self, config, count, start=0):
        for _ in range(count):
            self.counter += 1
            self.assertIsNotNone(audit_log.record(config, "settings_change", "root", "admin", "", "t%d" % self.counter, details={"a": "x" * 190, "b": "y" * 190, "c": "z" * 190}))

    def files(self):
        return sorted(p.name for p in Path(self.tmp.name).glob("audit_actions.jsonl*") if not p.name.endswith((".lock", ".oslock")))

    def test_the_default_keeps_five_and_the_range_is_one_to_twenty(self):
        self.assertEqual(audit_log.settings({})["keep_generations"], 5)
        for bad in (0, 21, True, "3", -1, 2.5):
            self.assertEqual(audit_log.settings({"audit_log": {"keep_generations": bad}})["keep_generations"], 5, bad)
        self.assertEqual(audit_log.settings({"audit_log": {"keep_generations": 20}})["keep_generations"], 20)

    def test_the_files_are_shifted_up_to_the_number_asked_and_the_chain_is_whole_across_all_of_them(self):
        config = {"audit_log": {"keep_generations": 3}}
        self.write(config, 40)      # three rotations and a bit
        self.assertEqual(self.files(), ["audit_actions.jsonl", "audit_actions.jsonl.1", "audit_actions.jsonl.2", "audit_actions.jsonl.3"])
        self.write(config, 25)      # two more rotations: the oldest generation goes
        self.assertEqual(self.files(), ["audit_actions.jsonl", "audit_actions.jsonl.1", "audit_actions.jsonl.2", "audit_actions.jsonl.3"])
        result = audit_log.verify()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["segments"], 4)
        self.assertFalse(result["complete"], "the beginning of the history is gone: what is there is whole but not all of it")

    def test_a_smaller_number_removes_the_generations_that_are_left_over(self):
        self.write({"audit_log": {"keep_generations": 5}}, 60)
        self.assertEqual(len(self.files()), 6)
        self.write({"audit_log": {"keep_generations": 2}}, 20)
        self.assertEqual(self.files(), ["audit_actions.jsonl", "audit_actions.jsonl.1", "audit_actions.jsonl.2"])
        self.assertTrue(audit_log.verify()["ok"])

    def test_a_changed_line_in_an_old_generation_is_found(self):
        config = {"audit_log": {"keep_generations": 3}}
        self.write(config, 40)
        old = Path(self.tmp.name) / "audit_actions.jsonl.3"
        lines = old.read_text(encoding="utf-8").splitlines()
        lines[5] = lines[5].replace("t", "T", 1)
        old.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = audit_log.verify()
        self.assertFalse(result["ok"])
        self.assertEqual(result["segment"], "rotated")


class WhenTheLogIsRequired(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "audit_actions.jsonl"
        patcher = mock.patch.object(audit_log, "FILE", self.file)
        patcher.start()
        self.addCleanup(patcher.stop)
        saved = dict(audit_log.STATS)
        self.addCleanup(audit_log.STATS.update, saved)

    def test_it_is_off_by_default_and_an_unwritable_log_does_not_stop_anything(self):
        self.assertFalse(audit_log.settings({})["required"])
        with mock.patch.object(audit_log.private_io, "open_append", side_effect=OSError("disk full")):
            self.assertTrue(audit_log.writable({}))

    def test_when_on_it_says_whether_the_log_can_be_written(self):
        config = {"audit_log": {"required": True}}
        self.assertTrue(audit_log.writable(config))
        before = audit_log.STATS["write_failures"]
        with mock.patch.object(audit_log.private_io, "open_append", side_effect=OSError("read only")):
            self.assertFalse(audit_log.writable(config))
        self.assertEqual(audit_log.STATS["write_failures"], before + 1)
        self.assertTrue(audit_log.writable({"audit_log": {"required": True, "enabled": False}}), "a log that is switched off is not a log that failed")

    def test_an_audited_action_is_refused_with_a_503_and_not_done_while_the_log_cannot_be_written(self):
        served = Served(self, lite=False)
        config = {"audit_log": {"required": True}}
        from github_actions_monitor.app import modes
        fresh = modes.State()
        for patcher in (mock.patch.object(am.toolconfig, "raw_config", return_value=config), mock.patch.object(am, "LIVE_CONFIG", dict(am.DEFAULTS, **config)), mock.patch.object(am, "MODE", fresh)):
            patcher.start()
            self.addCleanup(patcher.stop)
        body = json.dumps({"mode": "turbo", "minutes": 5})
        headers = {"Content-Type": "application/json"}
        with mock.patch.object(audit_log.private_io, "open_append", side_effect=OSError("read only")):
            status, raw, _ = served.raw("POST", "/api/mode", headers, body)
            self.assertEqual((status, json.loads(raw)["code"]), (503, "audit_unwritable"))
            self.assertEqual(fresh.name, "normal", "the action was not done")
            status, raw, _ = served.raw("POST", "/api/alerts/mute", headers, "{}")
            self.assertEqual(status, 503)
            status, raw, _ = served.raw("POST", "/api/settings", headers, json.dumps({"changes": {"audit_log.required": False}}))
            self.assertNotEqual(status, 503, "the settings stay open so that the log can be put right")
        status, raw, _ = served.raw("POST", "/api/mode", headers, body)
        self.assertNotEqual(status, 503)
        self.assertIn(status, (200, 400, 403), "and with the log in order the request reaches its handler (the one-use token is checked there)")

    def test_without_the_setting_the_same_action_is_not_refused(self):
        served = Served(self, lite=False)
        with mock.patch.object(am.toolconfig, "raw_config", return_value={}), mock.patch.object(audit_log.private_io, "open_append", side_effect=OSError("read only")):
            status, raw, _ = served.raw("POST", "/api/mode", {"Content-Type": "application/json"}, json.dumps({"mode": "turbo", "minutes": 5}))
        self.assertNotEqual(status, 503)


class TheTwoSettings(unittest.TestCase):
    def test_they_have_a_row_a_default_and_texts_in_eight_languages(self):
        for name in ("required", "keep_generations"):
            self.assertIn("audit_log." + name, settings_api.FIELDS)
            self.assertIn(name, audit_log.DEFAULTS)
            self.assertTrue(settings_api.META["audit_log." + name]["secure"], "a security option is changed from this computer only in the network mode")
            for lang in i18n.LANGS:
                with i18n.use_language(lang):
                    for prefix in ("cfg.f.audit_log.", "cfg.h.audit_log."):
                        self.assertNotEqual(i18n.t(prefix + name), prefix + name, (lang, prefix + name))
        self.assertEqual(settings_api.FIELDS["audit_log.keep_generations"][3], (1, 20))


class OneCountForTheWholeTick(unittest.TestCase):
    def test_the_stages_of_a_tick_do_not_each_spend_the_whole_limit(self):
        account = t275.Account(self, 250, lambda *a: {"allowed_actions": "all", "workflows": [], "protected": False})
        s = account.sentinel
        s.cfg["max_calls_per_tick"] = 70
        s.cfg["budget_per_hour"] = 100000
        s.cfg["hygiene"] = dict(s.cfg["hygiene"], ruleset_mode="effective")
        s.repo_info = {r: {"branch": "main"} for r in account.names}
        s.tick()
        self.assertLessEqual(len(account.calls), 70, "a tick of limit 70 made %d calls" % len(account.calls))
        self.assertGreater(len(account.calls), 20, "and it did work")
        self.assertIsNone(s.tick_began)

    def test_outside_a_tick_nothing_is_counted_against_the_limit(self):
        account = t275.Account(self, 2, lambda *a: {})
        s = account.sentinel
        for _ in range(10):
            s._gh("api", "x")
        self.assertEqual(s._tick_spent(), 0)
        self.assertGreater(s._budget(), 0)

    def test_the_stage_never_asks_for_more_than_its_share(self):
        account = t275.Account(self, 2, lambda *a: {})
        s = account.sentinel
        s.cfg["max_calls_per_tick"] = 100
        self.assertEqual(s._stage_budget(0.25), 25)
        s.cfg["budget_per_hour"] = 10
        self.assertEqual(s._stage_budget(0.25), 10, "nor more than the hour has left")


class ARepositoryThatKeepsFailing(unittest.TestCase):
    def test_the_delay_grows_from_the_third_failure_and_stops_at_ten_minutes(self):
        self.assertEqual([resilience.retry_delay(n) for n in range(0, 9)], [0, 0, 0, 30, 60, 120, 240, 480, 600])

    def test_a_bad_gateway_is_not_read_again_at_every_cycle(self):
        reads = []

        def failing(path, **kwargs):
            reads.append(path)
            raise RuntimeError("HTTP 502: Bad Gateway")
        config = {"mode": "full", "cold_runs_per_repo": 5, "runs_per_repo": 20, "max_workers": 8, "refresh_seconds": 45, "cold_refresh_seconds": 600, "hot_hours": 3}
        am.RUN_CACHE.clear()
        self.addCleanup(am.RUN_CACHE.clear)
        names = t216.repo_names()[:40]
        with mock.patch.object(am, "gh_read", failing), mock.patch.object(am.toolconfig, "github_owner", return_value="o"), mock.patch.object(am, "tuned", lambda c, k, d=None: c[k]):
            for _ in range(6):
                am.refresh_runs(names, config)
            self.assertLessEqual(len(reads), 3 * len(names), "six cycles, three reads of each repository")
            before = len(reads)
            for entry in am.RUN_CACHE.values():
                entry["retry_at"] = time.time() - 1
            am.refresh_runs(names, config)
            self.assertEqual(len(reads) - before, len(names), "after the wait they are read again")

    def test_a_good_read_forgets_the_wait(self):
        am.RUN_CACHE.clear()
        self.addCleanup(am.RUN_CACHE.clear)
        for _ in range(4):
            am.note_read("r", [], "HTTP 502: Bad Gateway")
        self.assertGreater(am.RUN_CACHE["r"]["retry_at"], time.time())
        am.note_read("r", [], None)
        self.assertNotIn("retry_at", am.RUN_CACHE["r"])
        self.assertTrue(os)


if __name__ == "__main__":
    unittest.main()
