# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Who does each read: what depends on WHO asks is always the login of the user, a `gh` call is a read only when it is on a white list, the token file of the second account lives under the accounts
folder and is never reached through a link, and a base line dated in the future is not trusted."""
import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor as am
from github_actions_monitor.data_pipeline import readpool
from github_actions_monitor.integrations import github_app
from github_actions_monitor.sentinels import central_source

TOKEN = "ghp_" + "S" * 36


class IdentityReadsAreAlwaysTheUsers(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        patcher = mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": self.dir.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.file = Path(self.dir.name) / "second.txt"
        self.file.write_text(TOKEN + "\n", encoding="utf-8")
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update({**am.DEFAULTS, "extra_reader": {"enabled": True, "file": str(self.file)}})
        readpool.reset()
        self.addCleanup(lambda: (am.LIVE_CONFIG.clear(), readpool.reset()))

    def fake_run(self, argv, **kwargs):
        who = "SECOND-ACCOUNT" if (kwargs.get("env") or {}).get("GH_TOKEN", "").startswith("ghp_SSS") else "OWNER"
        if argv[1:3] == ["api", "user"]:
            out = {"login": who}
        elif "user/orgs" in " ".join(argv):
            out = [{"login": "org-of-" + who}]
        elif argv[1:3] == ["api", "rate_limit"]:
            out = {"resources": {"core": {"remaining": 4990 if who != "OWNER" else 3200, "limit": 5000, "reset": 2000000000}}}
        else:
            out = {"login": who, "argv": argv[1:]}
        return types.SimpleNamespace(returncode=0, stdout=json.dumps(out), stderr="")

    def test_the_account_and_its_organisations_are_answered_by_the_user_even_when_the_second_account_has_more_calls(self):
        with mock.patch.object(am.subprocess, "run", self.fake_run):
            first = [am.gh("api", "user", retries=0)["login"] for _ in range(4)]
            am.rate_probes(am.LIVE_CONFIG)      # the free probe of every cycle: the second account has more calls left
            later = [am.gh("api", "user", retries=0)["login"] for _ in range(3)]
            orgs = am.gh("api", "user/orgs?per_page=100")
            notifications = am.gh("api", "notifications")
            search = am.gh("api", "search/issues?q=is:open+author:@me")
        self.assertEqual(set(first + later), {"OWNER"})
        self.assertEqual(orgs, [{"login": "org-of-OWNER"}])
        self.assertEqual((notifications["login"], search["login"]), ("OWNER", "OWNER"))

    def test_an_ordinary_read_is_still_spread(self):
        readpool.note_probe("extra", 5000)
        readpool.note_probe("user", 100)
        self.assertEqual(readpool.pick(am.LIVE_CONFIG, ["api", "repos/o/r/actions/runs"])[0], "extra")

    def test_identity_endpoints_are_not_reads_for_the_pool(self):
        for args in (["api", "user"], ["api", "user/orgs?per_page=100"], ["api", "/user/repos"], ["api", "notifications"], ["api", "notifications/threads/1"], ["api", "search/issues?q=x+assignee:@me"],
                     ["api", "users/@me"], ["api", "-i", "user"], ["auth", "status"], ["auth", "token"], ["repo", "list"], ["repo", "list", "--limit", "5"], ["api", "app"], ["api", "installation/repositories"]):
            self.assertFalse(github_app.is_read(args), args)
        for args in (["api", "users/someone"], ["api", "search/issues?q=repo:o/r"], ["api", "repos/o/r/actions/runs"], ["repo", "list", "someone", "--limit", "5"], ["api", "rate_limit"]):
            self.assertTrue(github_app.is_read(args), args)


class AReadIsOnAWhiteList(unittest.TestCase):
    def test_the_attached_forms_of_a_write_are_not_reads(self):
        for args in (["api", "-XPOST", "repos/o/r/x"], ["api", "--method=DELETE", "repos/o/r/x"], ["api", "repos/o/r/x", "-fa=b"], ["api", "repos/o/r/x", "--field=a=b"], ["api", "repos/o/r/x", "--input=-"],
                     ["api", "-X", "PATCH", "repos/o/r/x"], ["api", "--method", "PUT", "repos/o/r/x"], ["api", "repos/o/r/x", "-F", "a=b"], ["api", "repos/o/r/x", "--raw-field", "a=b"],
                     ["api", "repos/o/r/x", "--unknown-option"], ["api", "repos/o/r/x", "-H", "X-HTTP-Method-Override: DELETE"], ["api", "repos/o/r/x", "-H"], ["api", "graphql", "-f", "query=x"],
                     ["api"], ["api", "a/b", "c/d"], ["api", "--jq=.x", "repos/o/r"], []):
            self.assertFalse(github_app.is_read(args), args)

    def test_the_known_options_of_a_read_pass(self):
        for args in (["api", "repos/o/r"], ["api", "-i", "repos/o/r"], ["api", "repos/o/r", "--paginate"], ["api", "repos/o/r", "--jq", ".[].name"], ["api", "-i", "-H", "If-None-Match: \"abc\"", "repos/o/r"],
                     ["api", "repos/o/r", "-H", "Accept: application/vnd.github.raw"], ["api", "repos/o/r", "--cache", "1h"], ["run", "list", "--limit", "5"], ["release", "view", "v1"]):
            self.assertTrue(github_app.is_read(args), args)

    def test_a_write_never_gets_the_pool(self):
        readpool.reset()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": tmp}):
            file = Path(tmp) / "t.txt"
            file.write_text(TOKEN + "\n", encoding="utf-8")
            config = {"extra_reader": {"enabled": True, "file": str(file)}}
            readpool.note_probe("extra", 5000)
            readpool.note_probe("user", 1)
            for args in (["api", "-XPOST", "repos/o/r/issues"], ["api", "repos/o/r/issues", "--field=title=x"], ["api", "user"]):
                self.assertEqual(readpool.pick(config, args), ("user", {}), args)
            readpool.reset()


class TheTokenFileOfTheSecondAccount(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.accounts = Path(self.dir.name) / "accounts"
        self.accounts.mkdir()
        self.outside = Path(self.dir.name) / "outside.txt"
        self.outside.write_text(TOKEN + "\n", encoding="utf-8")
        patcher = mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": str(self.accounts)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def file_for(self, path, **extra):
        return readpool.settings({"extra_reader": {"enabled": True, "file": str(path), **extra}})["file"]

    def test_a_path_outside_the_accounts_folder_is_empty_by_default(self):
        inside = self.accounts / "second.txt"
        inside.write_text(TOKEN + "\n", encoding="utf-8")
        self.assertEqual(self.file_for(inside), str(inside))
        self.assertEqual(self.file_for(self.outside), "")
        self.assertEqual(self.file_for(self.accounts / ".." / "outside.txt"), "")
        self.assertEqual(self.file_for(self.accounts), "")
        self.assertEqual(self.file_for("/etc/passwd"), "")
        self.assertEqual(readpool.token_from_file(self.file_for(self.outside)), "")

    def test_the_switch_that_allows_any_folder_is_off_by_default_and_a_real_true_turns_it_on(self):
        self.assertFalse(readpool.settings({})["any_folder"])
        self.assertFalse(readpool.DEFAULTS["any_folder"])
        self.assertEqual(self.file_for(self.outside, any_folder="yes"), "")
        self.assertEqual(self.file_for(self.outside, any_folder=True), str(self.outside))

    def test_a_link_is_never_followed(self):
        link = self.accounts / "link.txt"
        try:
            os.symlink(self.outside, link)
        except (OSError, NotImplementedError):
            self.skipTest("this system cannot make a symbolic link")
        self.assertEqual(self.file_for(link), "", "a link inside the folder that points outside")
        self.assertEqual(readpool.token_from_file(str(link)), "", "and the file behind it is not read even when the path is given")
        self.assertEqual(self.file_for(link, any_folder=True), str(link), "the path itself is acceptable with the switch")
        self.assertEqual(readpool.token_from_file(str(link)), "")
        real = Path(self.dir.name) / "realdir"
        real.mkdir()
        (real / "t.txt").write_text(TOKEN + "\n", encoding="utf-8")
        folder_link = self.accounts / "folder"
        try:
            os.symlink(real, folder_link, target_is_directory=True)
        except (OSError, NotImplementedError):
            return
        self.assertEqual(self.file_for(folder_link / "t.txt"), "", "a folder that is a link")

    def test_only_a_small_regular_file_is_read(self):
        inside = self.accounts / "t.txt"
        inside.write_text(TOKEN + "\n", encoding="utf-8")
        self.assertEqual(readpool.token_from_file(str(inside)), TOKEN)
        inside.write_text(TOKEN + "\n" + "x" * 2000, encoding="utf-8")
        self.assertEqual(readpool.token_from_file(str(inside)), "")
        self.assertEqual(readpool.token_from_file(str(self.accounts)), "", "a folder")
        self.assertEqual(readpool.token_from_file(""), "")

    def test_the_setting_is_local_only_and_in_the_schema(self):
        from github_actions_monitor.app import settings_api
        from github_actions_monitor.security import localguard
        self.assertIn("extra_reader.any_folder", settings_api.FIELDS)
        self.assertTrue(settings_api.META["extra_reader.any_folder"]["secure"])
        self.assertTrue(localguard.local_only_key("extra_reader.any_folder"))
        self.assertFalse(am.DEFAULTS["extra_reader"]["any_folder"])


class ACentralPanelDatedInTheFutureIsNotTrusted(unittest.TestCase):
    def setUp(self):
        central_source.reset()
        self.addCleanup(central_source.reset)

    def read(self, asof, now=1_800_000_000):
        doc = {"asof": asof, "ci": {"red": [], "red_total": 0}}
        return central_source.read({"central": {"source": "http"}}, "o", opener=lambda url: json.dumps(doc), now=now, force=True)

    def test_a_date_in_the_future_is_behind(self):
        got = self.read("2099-01-01T00:00:00Z")
        self.assertTrue(got["ok"])
        self.assertIsNone(got["age_seconds"])
        self.assertTrue(got["stale"])
        self.assertEqual(central_source.red_repos(got), set())
        self.assertIn("not trusted", central_source.summary(got))
        self.assertNotIn("0 min ago", central_source.summary(got))

    def test_a_clock_a_little_ahead_is_tolerated_and_a_recent_file_is_fresh(self):
        import calendar
        import time
        now = 1_800_000_000
        stamp = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))      # noqa: E731
        near = self.read(stamp(now + 120), now)
        self.assertEqual((near["age_seconds"], near["stale"]), (0, False))
        far = self.read(stamp(now + 3600), now)
        self.assertTrue(far["stale"])
        old = self.read(stamp(now - 100 * 3600), now)
        self.assertTrue(old["stale"])
        fresh = self.read(stamp(now - 600), now)
        self.assertEqual((fresh["age_seconds"], fresh["stale"]), (600, False))
        self.assertEqual(calendar.timegm(time.gmtime(now)), now)


if __name__ == "__main__":
    unittest.main()
