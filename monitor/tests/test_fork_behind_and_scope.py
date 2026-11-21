# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Three opt-in additions, all read only and with no call of their own beyond the ones counted by their settings:
  * `fleet.fork_behind`: the commits the original has that a fork lacks (a column of the Repositories table); a fork that cannot be read is "not evaluable", never marked;
  * `ci.reusable_out_of_rankings` and `ci.orphan_workflows`: reusable workflows out of the failure lists, and the information list of orphans;
  * `runners.group_by`: the runners and the jobs held, grouped by label or by runner group.
No network: the reads of GitHub are replaced."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am, settings_api, surface  # noqa: E402
from github_actions_monitor.data_pipeline import fork_behind, workflow_scope  # noqa: E402
from github_actions_monitor.integrations import runner_model, runners  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402

ON_FORKS = {"fleet": {"fork_behind": True}}


def fork_answer(parent="up/orig", branch="main", parent_branch="main"):
    return {"default_branch": branch, "parent": {"full_name": parent, "default_branch": parent_branch}}


def reader_for(behind=None, parent=True, fail=None):
    """A fake read(endpoint) that records its calls."""
    calls = []

    def read(endpoint):
        calls.append(endpoint)
        if fail and fail in endpoint:
            raise RuntimeError("no access")
        if "/compare/" in endpoint:
            return {"ahead_by": behind} if behind is not None else {}
        return fork_answer() if parent else {"default_branch": "main"}
    return read, calls


class ForkBehindSettings(unittest.TestCase):
    def test_off_by_default_and_the_values_are_checked(self):
        self.assertEqual(fork_behind.settings({}), {"enabled": False, "per_call": 5, "ttl_hours": 6})
        self.assertEqual(fork_behind.settings({"fleet": {"fork_behind": "yes", "fork_behind_per_call": 0}})["enabled"], False)
        self.assertEqual(fork_behind.settings({"fleet": {"fork_behind": True, "fork_behind_per_call": 51}})["per_call"], 5)
        self.assertEqual(fork_behind.settings({"fleet": {"fork_behind": True, "fork_behind_per_call": 7, "meta_ttl_hours": 12}}), {"enabled": True, "per_call": 7, "ttl_hours": 12})

    def test_the_default_configuration_and_the_page_of_settings_know_the_keys(self):
        self.assertEqual((am.DEFAULTS["fleet"]["fork_behind"], am.DEFAULTS["fleet"]["fork_behind_per_call"]), (False, 5))
        self.assertEqual((am.DEFAULTS["ci"]["reusable_out_of_rankings"], am.DEFAULTS["ci"]["orphan_workflows"], am.DEFAULTS["runners"]["group_by"]), (False, False, "none"))
        for key in ("fleet.fork_behind", "fleet.fork_behind_per_call", "ci.reusable_out_of_rankings", "ci.orphan_workflows", "runners.group_by"):
            self.assertIn(key, settings_api.FIELDS)
        self.assertEqual(settings_api.FIELDS["runners.group_by"][2], "enum")


class ForkBehindReads(unittest.TestCase):
    def test_a_fork_that_is_behind_says_how_many_commits(self):
        read, calls = reader_for(behind=12)
        got = fork_behind.read_one("me/fork", read)
        self.assertEqual((got["state"], got["behind"], got["parent"]), ("behind", 12, "up/orig"))
        self.assertEqual(calls, ["repos/me/fork", "repos/me/fork/compare/main...up:main"])      # fork branch ... parent owner:parent branch: ahead_by is what the original has more

    def test_a_fork_with_nothing_to_catch_up_is_current(self):
        read, _calls = reader_for(behind=0)
        self.assertEqual(fork_behind.read_one("me/fork", read)["state"], "current")

    def test_a_fork_that_cannot_be_read_is_not_marked_either_way(self):
        for why, kwargs in (("no_parent", {"parent": False}), ("unreadable", {"fail": "compare"}), ("unreadable", {"fail": "repos/me/fork"}), ("no_answer", {"behind": None})):
            read, _ = reader_for(**kwargs)
            got = fork_behind.read_one("me/fork", read)
            self.assertEqual((got["state"], got["behind"], got["why"]), ("unknown", None, why), kwargs)

    def test_a_wrong_number_is_not_believed(self):
        for bad in (-1, True, "3", None, 1.5):
            self.assertIsNone(fork_behind.behind_of({"ahead_by": bad}), bad)
        self.assertEqual(fork_behind.behind_of({"ahead_by": 10 ** 9}), fork_behind.MAX_BEHIND)

    def test_the_branch_names_are_quoted(self):
        read, calls = reader_for(behind=1)
        read2 = lambda endpoint: (calls.append(endpoint) or ({"ahead_by": 1} if "/compare/" in endpoint else fork_answer(branch="feat x", parent_branch="a b")))      # noqa: E731
        fork_behind.read_one("me/fork", read2)
        self.assertIn("compare/feat%20x...up:a%20b", calls[-1])


class ForkBehindRounds(unittest.TestCase):
    def test_a_round_reads_at_most_per_call_forks_two_reads_each_and_the_rest_waits(self):
        reader = fork_behind.Reader()
        read, calls = reader_for(behind=3)
        forks = ["f1", "f2", "f3", "f4"]
        left = reader.fill(forks, read, 2, 6, "me", now=1000.0)
        self.assertEqual((left, len(calls)), (2, 4))
        self.assertEqual(calls[0], "repos/me/f1")      # a bare name is completed with the owner
        self.assertEqual({r: v["state"] for r, v in reader.rows(forks).items()}, {"f1": "behind", "f2": "behind", "f3": "unknown", "f4": "unknown"})
        self.assertTrue(reader.rows(forks)["f3"]["pending"])      # not read yet: not evaluable, and it says it waits

    def test_two_rounds_are_at_least_thirty_seconds_apart(self):
        reader = fork_behind.Reader()
        read, calls = reader_for(behind=1)
        reader.fill(["a", "b"], read, 1, 6, "me", now=1000.0)
        n = len(calls)
        self.assertEqual(reader.fill(["a", "b"], read, 1, 6, "me", now=1010.0), 1)
        self.assertEqual(len(calls), n)      # too soon: nothing read
        reader.fill(["a", "b"], read, 1, 6, "me", now=1031.0)
        self.assertGreater(len(calls), n)

    def test_an_answer_lives_the_hours_of_the_metadata_and_an_unreadable_one_is_asked_again_within_the_hour(self):
        reader = fork_behind.Reader()
        read, calls = reader_for(behind=1)
        reader.fill(["a"], read, 5, 6, "me", now=1000.0)
        self.assertEqual(reader.pending(["a"], 6, now=1000.0 + 5 * 3600), 0)
        self.assertEqual(reader.pending(["a"], 6, now=1000.0 + 6 * 3600), 1)
        bad, _ = reader_for(fail="repos/")
        other = fork_behind.Reader()
        other.fill(["b"], bad, 5, 6, "me", now=1000.0)
        self.assertEqual(other.pending(["b"], 6, now=1000.0 + 1800), 0)
        self.assertEqual(other.pending(["b"], 6, now=1000.0 + 3600), 1)

    def test_the_part_of_the_page_is_absent_while_the_switch_is_off_and_never_reads_then(self):
        with mock.patch.object(am, "gh_read") as gh_read:
            self.assertIsNone(am.fork_behind_part({}, ["a"]))
            self.assertIsNone(am.fork_behind_part({"fleet": {"fork_behind": False}}, ["a"]))
            gh_read.assert_not_called()

    def test_only_the_forks_are_asked_about_and_the_rows_say_not_evaluable_until_read(self):
        am.META["fork_reader"], am.META["fork_running"] = None, False

        class Inline:      # the thread of the reads, run on the spot
            def __init__(self, target=None, **_kw):
                self.target = target

            def start(self):
                self.target()
        read, calls = reader_for(behind=4)
        with mock.patch.object(am, "repo_meta", return_value={"a": {"fork": True}, "b": {"fork": False}}), mock.patch.object(am, "gh_read", side_effect=lambda e, retries=0: read(e)), \
                mock.patch.object(am.threading, "Thread", Inline), mock.patch.object(am.toolconfig, "github_owner", return_value="me"):
            part = am.fork_behind_part(ON_FORKS, ["a", "b"])
        self.assertEqual(sorted(part["rows"]), ["a"])      # a repository that is not a fork has no value
        self.assertEqual(part["pending"], 1)
        self.assertEqual(am.META["fork_reader"].rows(["a"])["a"], {"state": "behind", "behind": 4})
        self.assertTrue(all(c.startswith("repos/me/a") for c in calls))
        am.META["fork_reader"] = None


def lib_scan(*items):
    return {"R": {"workflows": [surface.scan_workflow(text, name) for name, text in items], "stacks": [], "dependabot_yml": True, "codeql_yml": True, "manifest": None, "changelog_top": None}}


LIB = ("lib.yml", "on:\n  workflow_call:\n")
CI = ("ci.yml", "on: push\n")
BOTH = ("both.yml", "on:\n  workflow_call:\n  push:\n")


def run(rid, path, conclusion="failure", name=None):
    return {"repo": "R", "id": rid, "name": name or path, "path": path, "branch": "main", "status": "completed", "conclusion": conclusion, "event": "push",
            "started": f"2026-11-06T0{rid}:00:00Z", "url": f"https://x/{rid}", "seconds": 5 * rid, "actor": "o", "sha": "abc1234"}


def snapshot(runs, scans, scope, perms=None):
    now = datetime.now(timezone.utc)
    info = {"R": {"branch": "main", "pushed": None, "release": None, "vuln_total": 0, "vuln_sev": {}, "prs": [], "rulesets": [], "label_dependencies": True, "files": {}}}
    cfg = dict(sl.DEFAULTS, ci_scope=scope)
    inp = {"now": now, "today": now.strftime("%Y-%m-%d"), "cfg": cfg, "repos": ["R"], "eco": {"R": "main"}, "repo_info": info, "alerts": {}, "perms": perms or {}, "runs": {"R": runs},
           "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}}, "history": {"days": {}}, "unreleased": {}, "targets": {}, "errors": {}, "loading": "",
           "audits": None, "sample_caps": {"runs_per_repo": 50, "cold_runs_per_repo": 20}, "scans": scans, "a2_resolved": {}}
    return sl.compute_snapshot(inp)["a2"]


class ReusableOutOfRankings(unittest.TestCase):
    def test_the_switch_is_off_by_default(self):
        self.assertEqual(workflow_scope.settings({}), {"reusable_out": False, "orphans": False})
        self.assertEqual(workflow_scope.settings({"ci": {"reusable_out_of_rankings": True, "orphan_workflows": "yes"}}), {"reusable_out": True, "orphans": False})
        self.assertFalse(sl.sentinel_config({})["ci_scope"]["reusable_out"])

    def test_the_scan_tells_which_files_only_others_call(self):
        scans = lib_scan(LIB, CI, BOTH)
        self.assertEqual(workflow_scope.reusable_files(scans), {"R": {"lib.yml"}})      # a file that also has push is a workflow of its own

    def test_an_old_red_of_a_file_that_only_others_call_leaves_the_red_list_only_when_asked(self):
        runs = [run(1, "lib.yml"), run(2, "ci.yml", "success")]
        scans = lib_scan(LIB, CI)
        before = snapshot(runs, scans, {})
        self.assertEqual([r["workflow"] for r in before["red"]], ["lib.yml"])      # as it always was
        self.assertEqual(before["reusable_out"], [])
        after = snapshot(runs, scans, {"reusable_out": True})
        self.assertEqual(after["red"], [])
        self.assertEqual(after["reusable_out"], [{"repo": "R", "workflow": "lib.yml"}])      # and it says what it left out

    def test_a_workflow_that_has_its_own_triggers_stays_red(self):
        after = snapshot([run(1, "both.yml"), run(2, "ci.yml", "failure")], lib_scan(BOTH, CI), {"reusable_out": True})
        self.assertEqual(sorted(r["workflow"] for r in after["red"]), ["both.yml", "ci.yml"])

    def test_a_repository_without_a_scan_is_not_touched(self):
        after = snapshot([run(1, "lib.yml")], {}, {"reusable_out": True})
        self.assertEqual([r["workflow"] for r in after["red"]], ["lib.yml"])

    def test_the_rankings_of_the_analytics_do_not_see_those_runs(self):
        runs = [dict(run(1, "lib.yml"), repo="R"), dict(run(2, "ci.yml", "success"), repo="R")]
        kept = workflow_scope.drop_flat(runs, {"R": {"lib.yml"}})
        self.assertEqual([r["path"] for r in kept], ["ci.yml"])
        self.assertEqual(workflow_scope.drop_flat(runs, {}), runs)
        self.assertEqual(workflow_scope.drop_flat(runs, {"other": {"lib.yml"}}), runs)

    def test_the_file_of_a_run_is_told_by_its_base_name(self):
        kept, dropped = workflow_scope.drop_runs([{"path": ".github/workflows/lib.yml@refs/heads/main"}, {"path": "ci.yml"}, {"name": "x"}], {"lib.yml"})
        self.assertEqual((len(kept), dropped), (2, ["lib.yml"]))


def listed(*pairs):
    return {"R": {"at": 1, "wf_listed": [list(p) for p in pairs]}}


class Orphans(unittest.TestCase):
    def test_off_by_default_and_it_lists_nothing(self):
        self.assertEqual(workflow_scope.orphans(listed(("old", ".github/workflows/old.yml")), lib_scan(CI), False), {"enabled": False, "rows": [], "unverifiable": 0})
        a2 = snapshot([run(1, "ci.yml", "success")], lib_scan(CI), {})
        self.assertEqual(a2["orphans"], {"enabled": False, "rows": [], "unverifiable": 0})

    def test_a_workflow_that_github_lists_and_whose_file_is_gone_is_an_orphan(self):
        perms = listed(("CI", ".github/workflows/ci.yml"), ("Old", ".github/workflows/old.yml"), ("Ghost", ""), ("Dependabot", "dynamic/dependabot/dependabot-updates"))
        got = workflow_scope.orphans(perms, lib_scan(CI), True)
        self.assertEqual(got["unverifiable"], 0)
        self.assertEqual([(r["workflow"], r["reason"]) for r in got["rows"]], [("Old", "file_missing"), ("Ghost", "no_path")])

    def test_without_the_workflow_files_it_is_not_evaluable_and_never_guessed(self):
        got = workflow_scope.orphans(listed(("Old", ".github/workflows/old.yml")), {}, True)
        self.assertEqual((got["rows"], got["unverifiable"]), ([], 1))
        many = lib_scan(*[("w%d.yml" % i, "on: push\n") for i in range(70)])
        cut = workflow_scope.orphans(listed(("Old", ".github/workflows/old.yml")), many, True)      # the scan reads 60 files at most: it may have been cut
        self.assertEqual((cut["rows"], cut["unverifiable"]), ([], 1))

    def test_a_repository_whose_list_was_not_kept_is_skipped(self):
        self.assertEqual(workflow_scope.orphans({"R": {"at": 1}}, lib_scan(CI), True), {"enabled": True, "rows": [], "unverifiable": 0})

    def test_it_never_makes_anything_red_and_comes_in_the_snapshot(self):
        a2 = snapshot([run(1, "ci.yml", "success")], lib_scan(CI), {"orphans": True}, listed(("Old", ".github/workflows/old.yml")))
        self.assertEqual(a2["level"], "ok")
        self.assertEqual(a2["red"], [])
        self.assertEqual([(r["repo"], r["workflow"], r["reason"]) for r in a2["orphans"]["rows"]], [("R", "Old", "file_missing")])
        json.dumps(a2["orphans"])

    def test_the_list_that_the_hygiene_reading_makes_is_kept_without_one_more_call(self):
        calls = []

        def gh(*args, **kw):
            calls.append(args[1])
            if args[1].endswith("/actions/permissions"):
                return {"allowed_actions": "all"}
            return {"total_count": 3, "workflows": [{"name": "CI", "path": ".github/workflows/ci.yml", "state": "active"}, {"name": "Old", "path": "", "state": "active"},
                                                    {"name": "Dep", "path": "dynamic/dependabot/x", "state": "active"}]}
        for scope_on in (True, False):
            calls.clear()
            with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sl, "CACHE_FILE", Path(tmp) / "c.json"), mock.patch.object(sl, "HISTORY_FILE", Path(tmp) / "h.json"):
                s = sl.Sentinel({"gh": gh, "repos_fn": lambda: ["R"], "runs_fn": lambda: {}, "data_fn": lambda: {}, "eco_fn": lambda r: "main"},
                                {"sentinel": {"hygiene": {"ruleset_mode": "off", "community_fallback": False}}, "ci": {"orphan_workflows": scope_on}})
                s._gh = lambda *args, **kw: gh(*args, **kw)
                _repo, res = s._fetch_perms("R")
            self.assertEqual(res.get("wf_listed"), [["CI", ".github/workflows/ci.yml"], ["Old", ""]] if scope_on else None)
            self.assertEqual(len(calls), 2, calls)      # permissions and the list of workflows, as before


class RunnerGroups(unittest.TestCase):
    RUNNERS = [{"name": "a", "state": "idle", "labels": ["self-hosted", "Linux", "X64", "gpu"]}, {"name": "b", "state": "busy", "labels": ["self-hosted", "linux", "gpu"]},
               {"name": "c", "state": "offline", "labels": ["self-hosted", "linux"]}]

    def test_off_by_default_and_the_modes_are_checked(self):
        self.assertEqual(runners.group_mode({}), "none")
        self.assertEqual(runners.group_mode({"runners": {"group_by": "zone"}}), "none")
        self.assertEqual(runners.group_mode({"runners": {"group_by": "label"}}), "label")
        self.assertEqual(runner_model.settings({"runners": {"group_by": "group"}})["group_by"], "group")

    def test_the_runners_are_grouped_by_their_first_label_that_is_not_generic(self):
        got = runners.group_runners(self.RUNNERS, "label")
        self.assertEqual(got["by"], "label")
        self.assertEqual([(r["key"], r["runners"], r["idle"], r["busy"], r["offline"]) for r in got["rows"]], [("(none)", 1, 0, 0, 1), ("gpu", 2, 1, 1, 0)])

    def test_the_group_of_a_runner_is_not_in_the_list_of_github_so_it_is_not_evaluable_there(self):
        self.assertEqual(runners.group_runners(self.RUNNERS, "group"), {"by": "group", "available": False, "rows": []})

    def test_the_list_gets_groups_only_when_asked_and_costs_no_call(self):
        calls = []

        def reader(endpoint):
            calls.append(endpoint)
            return {"runners": [{"id": i, "name": f"r{i}", "status": "online", "busy": i == 1, "os": "Linux", "labels": [{"name": n} for n in r["labels"]]} for i, r in enumerate(self.RUNNERS)]}
        plain = runners.collect({"runners": {"enabled": True}}, reader, "me")
        self.assertNotIn("groups", plain)      # the answer of the contract does not change by default
        grouped = runners.collect({"runners": {"enabled": True, "group_by": "label"}}, reader, "me")
        self.assertEqual(len(calls), 2)
        self.assertEqual([r["key"] for r in grouped["groups"]["rows"]], ["(none)", "gpu"])

    JOBS = [{"repo": "a", "labels": ["self-hosted", "gpu"], "group": "Fast", "status": "queued", "created": "2026-01-01T00:00:00Z"},
            {"repo": "a", "labels": ["self-hosted", "gpu"], "group": "Fast", "status": "in_progress", "created": "2026-01-01T00:00:00Z"},
            {"repo": "b", "labels": ["ubuntu-latest"], "group": "", "status": "waiting", "created": "2026-01-01T00:10:00Z"}]

    def test_the_jobs_are_grouped_by_runner_group_or_by_label(self):
        now = 1767225600 + 3600      # 2026-01-01T01:00:00Z
        by_group = runner_model.grouped(self.JOBS, now, "group")
        self.assertEqual([(r["key"], r["jobs"], r["queued"], r["oldest_wait_seconds"]) for r in by_group["rows"]], [("Fast", 2, 1, 3600), ("(none)", 1, 1, 3000)])
        by_label = runner_model.grouped(self.JOBS, now, "label")
        self.assertEqual([(r["key"], r["jobs"]) for r in by_label["rows"]], [("gpu", 2), ("ubuntu-latest", 1)])

    def test_the_model_carries_the_groups_only_when_asked(self):
        now = 1767225600 + 3600
        base = {"runners": {"model": {"enabled": True}}}
        self.assertNotIn("grouped", runner_model.build(base, self.JOBS, [], [], {}, None, now))
        model = runner_model.build({"runners": {"group_by": "group", "model": {"enabled": True}}}, self.JOBS, [], [], {}, None, now)
        self.assertEqual(model["grouped"]["by"], "group")
        json.dumps(model)


if __name__ == "__main__":
    unittest.main()
