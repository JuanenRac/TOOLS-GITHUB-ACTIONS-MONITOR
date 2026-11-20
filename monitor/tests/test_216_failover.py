# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The change of source at the end of an allowance (quota.failover): a read that meets a limit is made once more with another source, and when all are spent the last good copy is served with its age."""
import subprocess
import unittest
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor as am
from github_actions_monitor.app import settings_api
from github_actions_monitor.data_pipeline import failover, readpool

ON = {"quota": {"failover": True, "failover_max_age_minutes": 60}}
LIMIT = "gh: API rate limit exceeded for user ID 1 (HTTP 403)"


def done(code, out="", err=""):
    return subprocess.CompletedProcess([], code, out, err)


class Settings(unittest.TestCase):
    def test_it_is_off_by_default_and_the_age_has_bounds(self):
        self.assertFalse(failover.settings({})["failover"])
        self.assertFalse(failover.settings({"quota": {"failover": "yes"}})["failover"])
        self.assertEqual(failover.settings({"quota": {"failover": True}})["failover_max_age_minutes"], 60)
        self.assertEqual(failover.settings({"quota": {"failover_max_age_minutes": 0}})["failover_max_age_minutes"], 60)
        self.assertEqual(failover.settings({"quota": {"failover_max_age_minutes": True}})["failover_max_age_minutes"], 60)
        self.assertEqual(failover.settings({"quota": {"failover_max_age_minutes": 5}})["failover_max_age_minutes"], 5)
        self.assertTrue(settings_api.check_value("quota.failover", True)[0])
        self.assertFalse(settings_api.check_value("quota.failover_max_age_minutes", 5000)[0])

    def test_a_limit_is_told_from_a_refusal(self):
        for text in (LIMIT, "HTTP 429", "You have exceeded a secondary rate limit", "Too Many Requests", "x-ratelimit-remaining: 0"):
            self.assertTrue(failover.is_limit(text), text)
        for text in ("HTTP 403: Resource not accessible by integration", "HTTP 404", "Bad credentials", ""):
            self.assertFalse(failover.is_limit(text), text)


class Copies(unittest.TestCase):
    def setUp(self):
        failover.reset()

    def test_a_copy_is_given_back_with_its_age_and_not_after_the_limit(self):
        failover.remember("api|x", {"a": 1}, now=1000.0)
        self.assertEqual(failover.recall("api|x", ON, now=1090.0), ({"a": 1}, 90))
        self.assertIsNone(failover.recall("api|x", ON, now=1000.0 + 61 * 60))
        self.assertIsNone(failover.recall("api|y", ON, now=1000.0))

    def test_the_memory_is_bounded_and_the_oldest_goes_first(self):
        for i in range(failover.MAX_COPIES + 5):
            failover.remember(f"k{i}", i, now=1.0 + i)
        self.assertIsNone(failover.recall("k0", {"quota": {"failover_max_age_minutes": 1440}}, now=100.0))
        self.assertIsNotNone(failover.recall(f"k{failover.MAX_COPIES + 4}", {"quota": {"failover_max_age_minutes": 1440}}, now=400.0))


class Switch(unittest.TestCase):
    def setUp(self):
        failover.reset()
        readpool._STATE.update({"left": {}, "failed": {}, "turn": 0})
        self.config = ON

    def run_gh(self, answers):
        calls = []

        def run(cmd, **kw):
            calls.append((cmd, (kw.get("env") or {}).get("GH_TOKEN", "")))
            return answers.pop(0)
        return run, calls

    def patched(self, run, available, source_env, config=None):
        config = ON if config is None else config
        return mock.patch.multiple(am, LIVE_CONFIG=config), mock.patch.object(am.subprocess, "run", run), \
            mock.patch.object(readpool, "available", lambda cfg, now=None: available), \
            mock.patch.object(readpool, "pick", lambda cfg, args, now=None: ("user", {})), \
            mock.patch.object(readpool, "env_for", lambda cfg, name: source_env.get(name, {})), \
            mock.patch.object(am.time, "sleep", lambda s: None)

    def enter(self, stack, *patches):
        for p in patches:
            stack.enter_context(p)

    def test_a_read_that_meets_the_limit_is_made_with_another_source(self):
        import contextlib
        run, calls = self.run_gh([done(1, "", LIMIT), done(0, '{"ok": true}')])
        with contextlib.ExitStack() as stack:
            self.enter(stack, *self.patched(run, ["app", "user"], {"app": {"env": {"GH_TOKEN": "app-token"}}}))
            data = am.gh("api", "repos/o/r/actions/runs", retries=0)
        self.assertEqual(data, {"ok": True})
        self.assertEqual(len(calls), 2)
        self.assertEqual(failover.STATE["switched"], 1)
        self.assertEqual(failover.STATE["last_switch"]["from"], "user")
        self.assertEqual(readpool._STATE["left"]["user"], 0)

    def test_with_the_switch_off_the_limit_is_an_error_as_before(self):
        import contextlib
        run, calls = self.run_gh([done(1, "", LIMIT)])
        with contextlib.ExitStack() as stack:
            self.enter(stack, *self.patched(run, ["app", "user"], {"app": {"env": {"GH_TOKEN": "t"}}}, config={}))
            with self.assertRaises(RuntimeError):
                am.gh("api", "repos/o/r/actions/runs", retries=0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(failover.STATE["switched"], 0)

    def test_every_source_spent_serves_the_last_good_copy_with_its_age(self):
        import contextlib
        run, calls = self.run_gh([done(0, '{"n": 1}'), done(1, "", LIMIT)])
        with contextlib.ExitStack() as stack:
            self.enter(stack, *self.patched(run, ["user"], {}))
            self.assertEqual(am.gh("api", "repos/o/r/actions/runs", retries=0), {"n": 1})
            self.assertEqual(am.gh("api", "repos/o/r/actions/runs", retries=0), {"n": 1})
        self.assertEqual(failover.STATE["stale_served"], 1)
        self.assertEqual(failover.snapshot(ON)["last_stale"]["read"], "api|repos/o/r/actions/runs")

    def test_without_a_copy_the_error_stands_and_a_refusal_never_switches(self):
        import contextlib
        run, calls = self.run_gh([done(1, "", LIMIT)])
        with contextlib.ExitStack() as stack:
            self.enter(stack, *self.patched(run, ["user"], {}))
            with self.assertRaises(RuntimeError):
                am.gh("api", "repos/o/never/actions/runs", retries=0)
        run, calls = self.run_gh([done(1, "", "HTTP 403: Resource not accessible by integration")])
        failover.reset()
        with contextlib.ExitStack() as stack:
            self.enter(stack, *self.patched(run, ["app", "user"], {"app": {"env": {"GH_TOKEN": "t"}}}))
            with self.assertRaises(am.AuthError):
                am.gh("api", "repos/o/r/actions/runs", retries=0)
        self.assertEqual(failover.STATE["switched"], 0)

    def test_a_write_never_fails_over(self):
        self.assertIsNone(am.failover_step(["api", "-X", "POST", "repos/o/r/dispatches"], "user", LIMIT, {"user"}))

    def test_the_status_of_the_quota_names_the_switch(self):
        failover.switched("user", "app")
        shown = failover.snapshot(ON)
        self.assertEqual((shown["enabled"], shown["switched"], shown["last_switch"]["to"]), (True, 1, "app"))
        self.assertNotIn("token", repr(shown).lower())


if __name__ == "__main__":
    unittest.main()
