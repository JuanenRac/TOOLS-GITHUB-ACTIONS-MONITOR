# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The wall screens never show the name of a repository whose visibility was not read (a list of repositories written by hand, an older gh), and they answer to the Host and Origin guard like the rest."""
import copy
import http.client
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_206_wall_screens as t206  # noqa: E402
from github_actions_monitor.app import actions_monitor, screens  # noqa: E402

LISTING = [{"name": "client-secret", "isPrivate": True}, {"name": "web-public", "isPrivate": False}]


class VisibilityIsThreeStates(unittest.TestCase):
    def setUp(self):
        for target in (actions_monitor.PRIVATE, actions_monitor.VISIBILITY["known"]):
            saved = set(target)
            self.addCleanup(lambda t=target, s=saved: (t.clear(), t.update(s)))
            target.clear()
        saved_at = actions_monitor.VISIBILITY["at"]
        self.addCleanup(actions_monitor.VISIBILITY.__setitem__, "at", saved_at)
        actions_monitor.VISIBILITY["at"] = 0.0
        patcher = mock.patch.dict(actions_monitor.DISCOVERED, {"at": 0.0, "names": [], "snapshot": {}})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.config = copy.deepcopy(actions_monitor.DEFAULTS)

    def names(self, config=None):
        repos = actions_monitor.watched_repos(config or self.config, force=True)
        meta = actions_monitor.repo_meta(repos, config or self.config)
        return meta, screens.Names(repos, meta, "public")

    def test_a_list_written_by_hand_reads_the_visibility_with_one_listing(self):
        self.config["repos"] = ["client-secret", "web-public"]
        calls = []
        with mock.patch.object(actions_monitor, "gh", side_effect=lambda *a, **k: calls.append(a) or LISTING):
            meta, names = self.names()
        self.assertEqual((meta["client-secret"]["private"], meta["web-public"]["private"]), (True, False))
        self.assertEqual((names.name("web-public"), names.name("client-secret")), ("web-public", "private-1"))
        self.assertEqual(len(calls), 1)

    def test_a_listing_that_cannot_be_read_leaves_every_repository_hidden(self):
        self.config["repos"] = ["client-secret", "web-public"]
        with mock.patch.object(actions_monitor, "gh", side_effect=RuntimeError("no gh")):
            meta, names = self.names()
        self.assertEqual((meta["client-secret"]["private"], meta["web-public"]["private"]), (None, None))
        self.assertTrue(names.hidden("client-secret") and names.hidden("web-public"))

    def test_an_older_gh_without_the_visibility_field_leaves_every_repository_hidden(self):
        self.config["repos"] = "all"

        def old_gh(*args, **kwargs):
            if "--no-archived" in args:
                return [{"name": "client-secret"}, {"name": "web-public"}]
            raise RuntimeError("Unknown JSON field: isPrivate")
        with mock.patch.object(actions_monitor, "gh", side_effect=old_gh):
            meta, names = self.names()
        self.assertEqual([r["private"] for r in meta.values()], [None, None])
        self.assertTrue(names.hidden("client-secret") and names.hidden("web-public"))

    def test_all_the_repositories_of_the_account_keep_their_names_when_public(self):
        self.config["repos"] = "all"
        with mock.patch.object(actions_monitor, "gh", return_value=LISTING):
            meta, names = self.names()
        self.assertEqual((meta["client-secret"]["private"], meta["web-public"]["private"]), (True, False))
        self.assertEqual(names.name("web-public"), "web-public")

    def test_a_visibility_that_is_missing_or_unknown_is_private_for_a_screen(self):
        names = screens.Names(["a", "b", "c"], {"a": {"private": None}, "b": {}, "c": {"private": False}}, "public")
        self.assertEqual([names.hidden(r) for r in ("a", "b", "c", "never-seen")], [True, True, False, True])

    def test_the_listing_is_not_asked_again_before_the_refresh_time(self):
        self.config["repos"] = ["web-public"]
        with mock.patch.object(actions_monitor, "gh", side_effect=RuntimeError("down")) as gh:
            actions_monitor.watched_repos(self.config)
            actions_monitor.watched_repos(self.config)
        self.assertEqual(gh.call_count, 1)
        self.assertLess(time.time() - actions_monitor.VISIBILITY["at"], 5)


class TheRoutesAnswerToTheHostGuard(unittest.TestCase):
    def ask(self, server, path, headers):
        connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=20)
        try:
            connection.request("GET", path, headers=headers)
            return connection.getresponse().status
        finally:
            connection.close()

    def test_a_foreign_host_or_origin_is_refused_on_the_pages_and_on_the_data(self):
        server = t206.Running(self, t206.ON)
        own = f"127.0.0.1:{server.port}"
        for path in ("/screen/overview", "/screen/now", "/screen/sentinels", "/api/screens/data?screen=now"):
            self.assertEqual(self.ask(server, path, {"Host": own}), 200, path)
            self.assertEqual(self.ask(server, path, {"Host": "attacker.example"}), 403, path)
            self.assertEqual(self.ask(server, path, {"Host": own, "Origin": "http://attacker.example"}), 403, path)


if __name__ == "__main__":
    unittest.main()
