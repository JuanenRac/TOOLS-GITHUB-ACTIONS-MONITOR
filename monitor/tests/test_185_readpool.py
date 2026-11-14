# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Sharing the allowance of GitHub between the sources of the monitor (user, GitHub App, second account).

1. A kind of read can have a preferred source, and a source can keep a reserve of calls for the programs of the user.
2. The preferred source is only the first try: a failure, a missing token or a reserve hands the read to the others, the user last; writes never leave the user.
3. The allowances are added up for the bar and the modes; with one source nothing changes.
4. Every default is the spread of always.
"""
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import readpool  # noqa: E402
from github_actions_monitor.integrations import github_app  # noqa: E402

TOKEN = "github_pat_" + "Ab1Cd2Ef3G" * 4
APP_TOKEN = "ghs_" + "A1b2C3d4E5" * 3
APP = {"github_app": {"enabled": True, "app_id": "1", "key_path": "/k.pem"}}
RUNS = ["api", "repos/o/r/actions/runs"]
ISSUES = ["api", "repos/o/r/issues"]


class Sources(unittest.TestCase):
    def setUp(self):
        readpool.reset()
        github_app.reset()
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        patcher = mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": self.dir.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.file = Path(self.dir.name) / "second.txt"
        self.file.write_text(TOKEN + "\n", encoding="utf-8")
        app = mock.patch.object(github_app, "token", lambda config, *a, **k: APP_TOKEN)
        app.start()
        self.addCleanup(app.stop)

    def config(self, **pool):
        return {**APP, "extra_reader": {"enabled": True, "file": str(self.file)}, "readpool": pool}

    def probe(self, user, app, extra):
        readpool.note_probe("user", user)
        readpool.note_probe("app", app)
        readpool.note_probe("extra", extra)


class TheKindOfARead(unittest.TestCase):
    def test_the_call_tells_the_kind(self):
        for args, kind in ((["api", "repos/o/r/actions/runs"], "runs"), (["api", "repos/o/r/commits/abc/check-runs"], "runs"), (["run", "list"], "runs"),
                           (["api", "repos/o/r/code-scanning/alerts"], "security"), (["api", "repos/o/r/dependabot/alerts"], "security"),
                           (["api", "repos/o/r/issues?state=open"], "issues"), (["pr", "list"], "issues"), (["api", "repos/o/r/pulls"], "issues"),
                           (["api", "repos/o/r/releases/latest"], "history"), (["api", "repos/o/r/commits"], "history"), (["release", "view", "v1"], "history"),
                           (["api", "orgs/o/repos"], "discovery"), (["api", "search/repositories?q=x"], "discovery"), (["api", "rate_limit"], "other"), ([], "other")):
            self.assertEqual(readpool.kind_of(args), kind, args)


class Settings(unittest.TestCase):
    def test_every_default_is_the_spread_of_always(self):
        cfg = readpool.pool_settings({})
        self.assertEqual(set(cfg["prefer"].values()), {"auto"})
        self.assertEqual(set(cfg["reserve"].values()), {0})
        self.assertEqual(set(cfg["prefer"]), set(readpool.KINDS))

    def test_a_wrong_value_keeps_the_default(self):
        cfg = readpool.pool_settings({"readpool": {"prefer": {"runs": "everybody", "issues": "app", "x": "user"}, "reserve": {"user": True, "app": -1, "extra": 99999}}})
        self.assertEqual((cfg["prefer"]["runs"], cfg["prefer"]["issues"]), ("auto", "app"))
        self.assertEqual(cfg["reserve"], {"user": 0, "app": 0, "extra": 0})
        self.assertEqual(readpool.pool_settings({"readpool": "x"})["reserve"]["user"], 0)

    def test_the_settings_are_in_the_quota_tab_with_their_texts_in_eight_languages(self):
        keys = [f"readpool.prefer.{k}" for k in readpool.KINDS] + [f"readpool.reserve.{s}" for s in readpool.SOURCES]
        for key in keys:
            self.assertEqual(settings_api.META[key]["tab"], "quota", key)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            data = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in keys:
                for text_key in (*settings_api.label_keys(key), settings_api.help_key(key)):
                    self.assertTrue(data.get(text_key), (lang, text_key))
            for block in ("rp_prefer", "rp_reserve"):
                self.assertTrue(data.get("ui.cfg_b_" + block), (lang, block))


class Choosing(Sources):
    def test_without_settings_the_source_with_most_calls_left_answers(self):
        self.probe(100, 9000, 3000)
        self.assertEqual(readpool.pick(self.config(), RUNS)[0], "app")

    def test_a_preferred_source_answers_its_kind_and_only_its_kind(self):
        self.probe(4000, 9000, 3000)
        config = self.config(prefer={"issues": "user"})
        self.assertEqual(readpool.pick(config, ISSUES), ("user", {}))
        self.assertEqual(readpool.pick(config, RUNS)[0], "app", "the other kinds keep the spread")

    def test_the_preferred_app_gets_its_token_as_the_environment_of_gh_and_nothing_else(self):
        self.probe(4000, 10, 3000)
        name, extra = readpool.pick(self.config(prefer={"runs": "app"}), RUNS)
        self.assertEqual((name, extra["env"]["GH_TOKEN"]), ("app", APP_TOKEN))

    def test_a_preferred_source_that_has_no_token_hands_the_read_on(self):
        self.probe(4000, 9000, 3000)
        with mock.patch.object(github_app, "token", lambda config, *a, **k: ""):
            name, _env = readpool.pick(self.config(prefer={"runs": "app"}), RUNS)
        self.assertIn(name, ("user", "extra"))

    def test_a_preferred_source_that_is_off_is_ignored(self):
        self.probe(4000, 9000, 3000)
        config = {"extra_reader": {"enabled": True, "file": str(self.file)}, "readpool": {"prefer": {"runs": "app"}}}
        self.assertIn(readpool.pick(config, RUNS)[0], ("user", "extra"))

    def test_a_source_under_its_reserve_takes_no_read_while_another_can(self):
        self.probe(900, 9000, 3000)
        config = self.config(reserve={"user": 1000})
        picks = {readpool.pick(config, RUNS)[0] for _ in range(20)}
        self.assertNotIn("user", picks, "the user keeps its last 1000 calls for the gh of the tools")
        self.assertTrue(readpool.below_reserve("user", config))
        self.assertFalse(readpool.below_reserve("app", config))

    def test_a_reserve_does_not_stop_reads_when_nothing_else_is_there(self):
        readpool.note_probe("user", 10)
        self.assertEqual(readpool.pick({"readpool": {"reserve": {"user": 1000}}}, RUNS), ("user", {}))

    def test_a_preferred_source_under_its_reserve_is_not_preferred(self):
        self.probe(4000, 500, 3000)
        config = self.config(prefer={"runs": "app"}, reserve={"app": 600})
        self.assertNotEqual(readpool.pick(config, RUNS)[0], "app")

    def test_when_every_source_is_under_its_reserve_the_reads_still_happen(self):
        self.probe(10, 10, 10)
        config = self.config(reserve={"user": 100, "app": 100, "extra": 100})
        self.assertIn(readpool.pick(config, RUNS)[0], ("user", "app", "extra"))

    def test_a_write_is_the_user_whatever_the_settings_say(self):
        self.probe(0, 9000, 9000)
        config = self.config(prefer={"runs": "app", "other": "extra"}, reserve={"user": 4000})
        self.assertEqual(readpool.pick(config, ["api", "-X", "POST", "repos/o/r/actions/runs/1/rerun"]), ("user", {}))
        self.assertEqual(readpool.pick(config, ["workflow", "run", "ci.yml"]), ("user", {}))

    def test_a_failing_source_is_left_out_whatever_it_prefers(self):
        self.probe(4000, 9000, 3000)
        readpool.note_failure("app", 1000)
        name, _ = readpool.pick(self.config(prefer={"runs": "app"}), RUNS, now=1001)
        self.assertNotEqual(name, "app")

    def test_picks_from_many_threads_keep_the_reserve(self):
        self.probe(1500, 40000, 30000)
        config = self.config(reserve={"user": 1000}, prefer={"runs": "user"})
        barrier, names = threading.Barrier(16), []

        def go():
            barrier.wait()
            names.extend(readpool.pick(config, RUNS)[0] for _ in range(50))
        threads = [threading.Thread(target=go) for _ in range(16)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertLessEqual(names.count("user"), 500 + 16, "the user is preferred until it falls to its reserve (500 reads); from then on nothing reads with it, but the reads already in flight")
        self.assertEqual(len(names), 800)


class TheSum(unittest.TestCase):
    def test_the_allowances_are_added_up(self):
        got = readpool.pooled({"user": {"remaining": 4000, "limit": 5000, "reset": "2026-01-01T10:00:00Z"}, "app": {"remaining": 9000, "limit": 10600, "reset": "2026-01-01T10:30:00Z"}})
        self.assertEqual(got, {"remaining": 13000, "limit": 15600, "reset": "2026-01-01T10:00:00Z"})

    def test_without_the_user_the_earliest_reset_is_used(self):
        got = readpool.pooled({"app": {"remaining": 1, "limit": 2, "reset": "B"}, "extra": {"remaining": 3, "limit": 4, "reset": "A"}})
        self.assertEqual((got["remaining"], got["limit"], got["reset"]), (4, 6, "A"))

    def test_one_source_keeps_its_own_figures_and_none_is_an_error(self):
        one = {"remaining": 7, "limit": 5000, "reset": "R"}
        self.assertEqual(readpool.pooled({"user": one}), one)
        with self.assertRaises(ValueError):
            readpool.pooled({})

    def test_the_status_adds_the_total_next_to_each_source(self):
        config = {"extra_reader": {"enabled": False}}
        old = am.LIVE_CONFIG
        am.LIVE_CONFIG = config
        try:
            core = {"resources": {"core": {"remaining": 4000, "limit": 5000, "reset": 1}}}
            app = {"enabled": True, "ok": True, "rate": {"remaining": 9000, "limit": 10600, "reset": 2}, "permissions": {}}
            with mock.patch.object(am, "gh", lambda *a, **k: core), mock.patch.object(github_app, "status", return_value=app):
                status = am.pool_status()
            self.assertEqual(status["total"], {"remaining": 13000, "limit": 15600, "sources": 2})
            with mock.patch.object(am, "gh", lambda *a, **k: core), mock.patch.object(github_app, "status", return_value={"enabled": False}):
                self.assertIsNone(am.pool_status()["total"], "one source: no total")
        finally:
            am.LIVE_CONFIG = old

    def test_the_page_shows_the_sum_and_the_figure_of_each_source(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("d.rate_sources", page)
        self.assertIn("d.total", page)
        self.assertIn("Σ", page)


if __name__ == "__main__":
    unittest.main()
