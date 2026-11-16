# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Lists read page by page and honest about a cut (no network): the helper, the jobs of a run, the workflows of a repository and the issues and pull requests of the Team tab."""
import json
import tempfile
import unittest
from unittest import mock

import _testenv  # noqa: F401
import test_a2_resolve as base
from github_actions_monitor.app import actions_monitor as am
from github_actions_monitor.data_pipeline import paging
from github_actions_monitor.sentinels import sentinel_local as sl
from test_173 import FakeGitHub, build, issue, pull


def pager(total, key="items", seen_paths=None, with_total=True):
    """A fake GitHub that has `total` items and answers any page of any size."""
    def read(path):
        if seen_paths is not None:
            seen_paths.append(path)
        per = int(path.split("per_page=")[1].split("&")[0])
        page = int(path.split("page=")[-1])
        chunk = [{"n": i} for i in range((page - 1) * per, min(total, page * per))]
        return {key: chunk, **({"total_count": total} if with_total else {})}
    return read


class Helper(unittest.TestCase):
    def test_a_short_list_costs_one_request_and_is_not_cut(self):
        seen = []
        out = paging.read_pages(pager(40, seen_paths=seen), "x/y", "items", 100, 3)
        self.assertEqual((out["seen"], out["total"], out["cut"], len(seen)), (40, 40, False, 1))

    def test_a_full_page_follows_the_next_one_until_all_is_read(self):
        seen = []
        out = paging.read_pages(pager(148, seen_paths=seen), "x/y", "items", 100, 3)
        self.assertEqual((out["seen"], out["cut"], len(seen)), (148, False, 2))
        self.assertTrue(all("per_page=100&page=" in p for p in seen))

    def test_the_limit_of_pages_cuts_and_says_how_many_exist(self):
        out = paging.read_pages(pager(348), "x/y", "items", 100, 3)
        self.assertEqual((out["seen"], out["total"], out["cut"]), (300, 348, True))

    def test_exactly_one_page_is_not_cut_when_github_gives_the_total(self):
        self.assertFalse(paging.read_pages(pager(100), "x/y", "items", 100, 3)["cut"])

    def test_without_a_total_a_last_full_page_may_hide_more(self):
        out = paging.read_pages(pager(500, with_total=False), "x/y", "items", 100, 2)
        self.assertEqual((out["seen"], out["total"], out["cut"]), (200, None, True))

    def test_a_query_string_is_extended_with_and(self):
        seen = []
        paging.read_pages(pager(3, seen_paths=seen), "x/y?state=open", "items", 100, 1)
        self.assertEqual(seen, ["x/y?state=open&per_page=100&page=1"])

    def test_the_settings_keep_the_defaults_for_nonsense(self):
        self.assertEqual(paging.settings({}), {"workflow_pages": 3, "job_pages": 2, "collab_pages": 3})
        self.assertEqual(paging.settings({"pagination": {"workflow_pages": 0, "job_pages": "9", "collab_pages": 21}}), paging.DEFAULTS)
        self.assertEqual(paging.settings({"pagination": {"job_pages": 5}})["job_pages"], 5)


class Jobs(unittest.TestCase):
    @staticmethod
    def job(i):
        return {"name": f"j{i}", "status": "in_progress", "conclusion": None, "steps": [], "started_at": "2026-01-01T00:00:00Z", "html_url": "https://x"}

    def jobs_of(self, total, config):
        def gh(*args, **kw):
            path = args[1]
            per = int(path.split("per_page=")[1].split("&")[0])
            page = int(path.split("page=")[-1])
            return {"total_count": total, "jobs": [self.job(i) for i in range((page - 1) * per, min(total, page * per))]}
        with mock.patch.object(am, "gh", gh), mock.patch.object(am.toolconfig, "raw_config", return_value=config), mock.patch.object(am.toolconfig, "github_owner", return_value="o"):
            return am.run_jobs_info("r", 1)

    def test_a_run_with_30_jobs_is_one_request_and_nothing_is_cut(self):
        jobs, seen, total = self.jobs_of(30, {})
        self.assertEqual((len(jobs), seen, total), (30, 30, None))

    def test_a_matrix_of_130_jobs_is_read_in_two_pages(self):
        jobs, seen, total = self.jobs_of(130, {})
        self.assertEqual((len(jobs), seen, total), (130, 130, None))

    def test_a_matrix_beyond_the_pages_says_seen_of_total(self):
        jobs, seen, total = self.jobs_of(450, {"pagination": {"job_pages": 2}})
        self.assertEqual((len(jobs), seen, total), (200, 200, 450))


class Workflows(unittest.TestCase):
    def perms(self, total, config=None):
        calls = []

        def gh(*args, **kw):
            path = args[1]
            calls.append(path)
            if path.endswith("/permissions"):
                return {"allowed_actions": "selected", "sha_pinning_required": True}
            per = int(path.split("per_page=")[1].split("&")[0])
            page = int(path.split("page=")[-1])
            return {"total_count": total, "workflows": [{"name": f"w{i}", "state": "disabled_manually" if i == 120 else "active"} for i in range((page - 1) * per, min(total, page * per))]}
        with tempfile.TemporaryDirectory() as tmp:
            s, _ = base.make(tmp, {})
            s.config = dict(s.config, **(config or {}))
            s._gh = gh
            repo, res = s._fetch_perms("R")
        return res, calls

    def test_148_workflows_are_all_seen_and_the_disabled_one_beyond_the_first_page_is_found(self):
        res, calls = self.perms(148)
        self.assertEqual((res["wf_seen"], res["wf_total"], res["wf_manual"]), (148, None, ["w120"]))
        self.assertEqual(len(calls), 3)

    def test_a_small_repository_costs_the_same_two_requests_as_before(self):
        res, calls = self.perms(12)
        self.assertEqual(len(calls), 2)
        self.assertIsNone(res["wf_total"])

    def test_348_workflows_are_cut_and_the_hygiene_says_so(self):
        res, _calls = self.perms(348)
        self.assertEqual((res["wf_seen"], res["wf_total"]), (300, 348))
        problems = sl.hygiene_problems({"ruleset": True, "label_dependencies": True, "files": {"README.md": 1}, "rulesets": [{}]}, res, [])
        self.assertIn("cut", [k for k, _t in problems])
        self.assertTrue(any("300" in t and "348" in t for k, t in problems if k == "cut"))


class PagedFake(FakeGitHub):
    """Lists of `n_issues` issues and `n_pulls` pull requests, 100 to a page."""

    def __init__(self, n_issues, n_pulls):
        super().__init__()
        self.all_issues = [issue(i + 1) for i in range(n_issues)]
        self.all_pulls = [pull(1000 + i) for i in range(n_pulls)]

    def run_gh(self, args):
        endpoint = args[-1]
        if "/issues?" in endpoint or "/pulls?" in endpoint:
            self.calls.append(list(args))
            page = int(endpoint.split("&page=")[1]) if "&page=" in endpoint else 1
            source = self.all_issues if "/issues?" in endpoint else self.all_pulls
            body = source[(page - 1) * 100:page * 100]
            return 0, "HTTP/2.0 200 OK\r\nContent-Type: application/json\r\n\r\n" + json.dumps(body), ""
        return super().run_gh(args)


class Team(unittest.TestCase):
    def scan(self, n_issues, n_pulls, config=None):
        fake = PagedFake(n_issues, n_pulls)
        sentinel, fake, _folder = build(self, config, fake=fake)
        sentinel.tick()
        return sentinel, fake

    def test_a_repository_with_few_items_costs_two_requests_as_before(self):
        sentinel, fake = self.scan(5, 5)
        self.assertEqual(len([c for c in fake.calls if "?" in c[-1]]), 2)      # the lists; the detail of a pull request is another call
        self.assertEqual(sentinel.get_status()["truncated_count"], 0)

    def test_300_pull_requests_are_followed_to_the_end_with_the_default_pages(self):
        sentinel, fake = self.scan(0, 250)
        self.assertEqual(sentinel.state["per_repo"]["r"]["prs"].__len__(), 250)
        self.assertEqual(sentinel.get_status()["truncated_count"], 0)

    def test_more_than_the_pages_is_said(self):
        sentinel, _fake = self.scan(0, 450, {})
        status = sentinel.get_status()
        self.assertEqual((len(sentinel.state["per_repo"]["r"]["prs"]), status["truncated"], status["truncated_count"], status["pages"]), (300, ["r"], 1, 3))


if __name__ == "__main__":
    unittest.main()
