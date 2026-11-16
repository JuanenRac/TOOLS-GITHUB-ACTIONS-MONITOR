# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Discovery of repositories: archived ones and forks are chosen by settings, a fork with a CI of its own is never lost, and the kind of account (user or organisation) sets the window.
Synthetic accounts and a fake gh, no network."""
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api as sa  # noqa: E402
from github_actions_monitor.data_pipeline import discovery  # noqa: E402

NOW = time.time()


def iso(days_ago):
    return (datetime.fromtimestamp(NOW, timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def workflow(state="active", path=".github/workflows/ci.yml"):
    return {"name": "CI", "state": state, "path": path}


class Reader:
    """A fake of the API: {fork: (workflows, last run days ago | None)}; counts the calls."""

    def __init__(self, forks, kind="User"):
        self.forks, self.kind, self.calls = forks, kind, []

    def __call__(self, endpoint):
        self.calls.append(endpoint)
        if endpoint.startswith("users/"):
            return {"type": self.kind}
        name = endpoint.split("/")[2]
        workflows, ago = self.forks[name]
        if isinstance(workflows, Exception):
            raise workflows
        if "/actions/workflows" in endpoint:
            return {"workflows": workflows}
        return {"workflow_runs": [] if ago is None else [{"created_at": iso(ago)}]}


class Settings(unittest.TestCase):
    def test_defaults_change_nothing(self):
        got = discovery.settings({})
        self.assertEqual((got["fork_policy"], got["skip_archived"], got["fork_ci_days"], got["fork_checks_per_pass"]), ("show", True, 90, 30))
        items = [{"name": "a"}, {"name": "f", "isFork": True}, {"name": "z", "isArchived": True}]
        self.assertEqual(discovery.lifecycle(items, {}), ["a", "f"])

    def test_bad_values_fall_back_one_by_one(self):
        got = discovery.settings({"discovery": {"fork_policy": "weird", "fork_ci_days": -3, "fork_checks_per_pass": True, "skip_archived": "no"}})
        self.assertEqual((got["fork_policy"], got["fork_ci_days"], got["fork_checks_per_pass"], got["skip_archived"]), ("show", 90, 30, False))

    def test_the_older_hide_fork_still_leaves_every_fork_out(self):
        self.assertEqual(discovery.settings({"discovery": {"hide": ["fork"]}})["fork_policy"], "skip")

    def test_archived_can_be_kept(self):
        items = [{"name": "a"}, {"name": "z", "isArchived": True}]
        self.assertEqual(discovery.lifecycle(items, {"skip_archived": False}), ["a", "z"])


class Policy(unittest.TestCase):
    ITEMS = [{"name": "own"}, {"name": "maintained", "isFork": True}, {"name": "dead", "isFork": True}, {"name": "unknown", "isFork": True}]
    ANSWERS = {"maintained": True, "dead": False, "unknown": None}

    def test_skip_leaves_every_fork_out(self):
        self.assertEqual(discovery.lifecycle(self.ITEMS, {"fork_policy": "skip"}, self.ANSWERS), ["own"])

    def test_skip_unless_ci_keeps_only_forks_with_their_own_ci(self):
        for policy in ("skip_unless_ci", "auto"):
            self.assertEqual(discovery.lifecycle(self.ITEMS, {"fork_policy": policy}, self.ANSWERS), ["own", "maintained"], policy)

    def test_show_keeps_them_all(self):
        self.assertEqual(discovery.lifecycle(self.ITEMS, {"fork_policy": "show"}, self.ANSWERS), ["own", "maintained", "dead", "unknown"])


class OwnCi(unittest.TestCase):
    def test_a_fork_whose_workflows_were_never_switched_on_has_no_ci(self):
        reader = Reader({"f": ([workflow("disabled_fork")], None)})
        self.assertIs(discovery.fork_has_ci(reader, "o", "f", 90, NOW), False)
        self.assertEqual(len(reader.calls), 1)      # no second read when nothing is enabled

    def test_an_enabled_workflow_and_a_recent_run(self):
        self.assertIs(discovery.fork_has_ci(Reader({"f": ([workflow()], 10)}), "o", "f", 90, NOW), True)
        self.assertIs(discovery.fork_has_ci(Reader({"f": ([workflow()], 200)}), "o", "f", 90, NOW), False)      # switched on once, silent since
        self.assertIs(discovery.fork_has_ci(Reader({"f": ([workflow()], None)}), "o", "f", 90, NOW), False)

    def test_zero_days_is_enough_with_an_enabled_workflow(self):
        reader = Reader({"f": ([workflow()], 999)})
        self.assertIs(discovery.fork_has_ci(reader, "o", "f", 0, NOW), True)
        self.assertEqual(len(reader.calls), 1)

    def test_a_dynamic_workflow_is_not_an_own_one(self):
        self.assertIs(discovery.fork_has_ci(Reader({"f": ([workflow(path="dynamic/pages/pages-build-deployment")], 1)}), "o", "f", 90, NOW), False)

    def test_no_answer_is_not_a_no(self):
        self.assertIsNone(discovery.fork_has_ci(Reader({"f": (RuntimeError("HTTP 502"), None)}), "o", "f", 90, NOW))

    def test_the_questions_are_limited_kept_and_asked_again_when_the_window_changes(self):
        forks = {f"f{i}": ([workflow()], 1) for i in range(5)}
        reader, known = Reader(forks), {}
        names = sorted(forks)
        first = discovery.check_forks(names, known, reader, "o", 90, 2, NOW)
        self.assertEqual(sum(1 for v in first.values() if v is True), 2)
        self.assertEqual(sum(1 for v in first.values() if v is None), 3)
        discovery.check_forks(names, known, reader, "o", 90, 10, NOW)
        before = len(reader.calls)
        discovery.check_forks(names, known, reader, "o", 90, 10, NOW + 60)
        self.assertEqual(len(reader.calls), before)      # answered for a week
        discovery.check_forks(names, known, reader, "o", 180, 10, NOW + 60)
        self.assertGreater(len(reader.calls), before)      # another window, another question
        gone = discovery.check_forks(names[:1], known, reader, "o", 180, 10, NOW + 60)
        self.assertEqual(list(gone), ["f0"])
        self.assertEqual(list(known), ["f0"])      # a fork that left the account is forgotten

    def test_the_kind_of_account_sets_the_window_only_in_auto(self):
        self.assertEqual(discovery.owner_kind(Reader({}, "Organization"), "o"), "organization")
        self.assertEqual(discovery.owner_kind(Reader({}, "User"), "o"), "user")
        self.assertIsNone(discovery.owner_kind(mock.Mock(side_effect=RuntimeError("x")), "o"))
        cfg = discovery.settings({"discovery": {"fork_policy": "auto", "fork_ci_days": 30}})
        self.assertEqual((discovery.fork_window(cfg, "user"), discovery.fork_window(cfg, "organization"), discovery.fork_window(cfg, None)), (30, 60, 30))
        plain = discovery.settings({"discovery": {"fork_policy": "skip_unless_ci", "fork_ci_days": 30}})
        self.assertEqual(discovery.fork_window(plain, "organization"), 30)


class WatchedRepos(unittest.TestCase):
    def setUp(self):
        am.DISCOVERED.update({"at": 0.0, "names": [], "snapshot": {}})
        am.FORKS.update({"known": {}, "kind": None, "kind_at": 0.0})

    def tearDown(self):
        am.DISCOVERED.update({"at": 0.0, "names": [], "snapshot": {}})
        am.FORKS.update({"known": {}, "kind": None, "kind_at": 0.0})

    def run_with(self, discovery_block, kind="User"):
        listing = [{"name": "demo-own"}, {"name": "demo-old", "isArchived": True}, {"name": "demo-fork-ci", "isFork": True}, {"name": "demo-fork-plain", "isFork": True}]
        reader = Reader({"demo-fork-ci": ([workflow()], 5), "demo-fork-plain": ([workflow("disabled_fork")], None)}, kind)

        def fake(*args, **kw):
            if args[0] == "repo":
                return listing
            return reader(args[1])

        config = {**am.DEFAULTS, "ecosystems": "all", "exclude": [], "github_owner": "demo-owner", "discovery": discovery_block}
        with mock.patch.object(am, "gh", side_effect=fake):
            return am.watched_repos(config, force=True), reader

    def test_default_behaviour_is_unchanged_and_asks_nothing_more(self):
        watched, reader = self.run_with({})
        self.assertEqual(sorted(watched), ["demo-fork-ci", "demo-fork-plain", "demo-own"])
        self.assertEqual(reader.calls, [])

    def test_a_maintained_fork_stays_and_a_plain_one_goes(self):
        watched, reader = self.run_with({"fork_policy": "skip_unless_ci"})
        self.assertEqual(sorted(watched), ["demo-fork-ci", "demo-own"])
        self.assertFalse(any(c.startswith("users/") for c in reader.calls))
        self.assertEqual({k: am.FORKS[k] for k in ("checked", "kept", "left", "waiting")}, {"checked": 2, "kept": 1, "left": 1, "waiting": 0})

    def test_auto_reads_the_kind_of_account_once(self):
        watched, reader = self.run_with({"fork_policy": "auto"}, "Organization")
        self.assertEqual(sorted(watched), ["demo-fork-ci", "demo-own"])
        self.assertEqual(am.FORKS["kind"], "organization")
        self.assertEqual(sum(1 for c in reader.calls if c.startswith("users/")), 1)
        self.assertEqual(am.discovery_payload()["owner_kind"], "organization")

    def test_forks_still_waiting_are_left_out_and_counted(self):
        watched, _ = self.run_with({"fork_policy": "skip_unless_ci", "fork_checks_per_pass": 1})
        self.assertEqual(am.FORKS["waiting"], 1)
        self.assertEqual(sorted(watched), ["demo-fork-ci", "demo-own"] if am.FORKS["kept"] else ["demo-own"])

    def test_archived_repositories_can_be_watched(self):
        watched, _ = self.run_with({"skip_archived": False})
        self.assertIn("demo-old", watched)


class Page(unittest.TestCase):
    def test_the_settings_are_in_the_basic_tab_and_checked(self):
        for key in ("discovery.skip_archived", "discovery.fork_policy", "discovery.fork_ci_days", "discovery.fork_checks_per_pass"):
            self.assertEqual(sa.FIELDS[key][0], "basic", key)
        self.assertTrue(sa.check_value("discovery.fork_policy", "auto")[0])
        self.assertFalse(sa.check_value("discovery.fork_policy", "all")[0])
        self.assertTrue(sa.check_value("discovery.fork_ci_days", 0)[0])
        self.assertFalse(sa.check_value("discovery.fork_ci_days", 400)[0])
        self.assertFalse(sa.check_value("discovery.fork_checks_per_pass", 0)[0])


if __name__ == "__main__":
    unittest.main()
