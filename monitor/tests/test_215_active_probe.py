# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The light look at the runs that are still going (sampling.active_probe): a full list also asks for the `in_progress` and the `queued` runs, so a long run older than the sample is kept."""
import time
import unittest
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor as am
from github_actions_monitor.app import settings_api
from github_actions_monitor.data_pipeline import sampling

NOW = 1_800_000_000.0


def stamp(offset):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - offset))


def raw(i, status="completed", conclusion="success"):
    return {"id": i, "name": "CI", "path": ".github/workflows/ci.yml", "head_branch": "main", "event": "push", "status": status, "conclusion": conclusion if status == "completed" else None,
            "created_at": stamp(i * 10), "run_started_at": stamp(i * 10), "updated_at": stamp(i * 10), "head_sha": "abcdef1234", "html_url": f"https://x/{i}"}


class ActiveProbe(unittest.TestCase):
    def setUp(self):
        self.calls = []
        am.SAMPLE_INFO.clear()

    def reader(self, first, running, queued):
        def read(path, **kw):
            self.calls.append(path)
            if "status=in_progress" in path:
                return running
            if "status=queued" in path:
                return queued
            return first
        return read

    def test_it_is_off_by_default_and_a_setting(self):
        self.assertFalse(sampling.settings({})["active_probe"])
        self.assertFalse(sampling.settings({"sampling": {"active_probe": "yes"}})["active_probe"])
        self.assertTrue(sampling.settings({"sampling": {"active_probe": True}})["active_probe"])
        self.assertTrue(settings_api.check_value("sampling.active_probe", True)[0])

    def test_a_full_list_also_gets_the_running_and_queued_runs_older_than_the_sample(self):
        first = {"workflow_runs": [raw(i) for i in range(1, 4)]}
        running = {"workflow_runs": [raw(900, "in_progress")]}
        queued = {"workflow_runs": [raw(901, "queued")]}
        with mock.patch.object(am, "gh_read", self.reader(first, running, queued)):
            merged, error = am.fetch_sampled("R", 3, {"sampling": {"active_probe": True}})
        self.assertIsNone(error)
        self.assertEqual(sorted(r["id"] for r in merged if r.get("probe")), [900, 901])
        self.assertEqual(len(merged), 5)
        self.assertEqual(am.SAMPLE_INFO["R"]["probe"], 2)
        self.assertEqual(len(self.calls), 3)

    def test_a_run_already_in_the_list_is_not_added_twice(self):
        first = {"workflow_runs": [raw(1, "in_progress"), raw(2), raw(3)]}
        with mock.patch.object(am, "gh_read", self.reader(first, {"workflow_runs": [raw(1, "in_progress")]}, {"workflow_runs": []})):
            merged, _error = am.fetch_sampled("R", 3, {"sampling": {"active_probe": True}})
        self.assertEqual(len(merged), 3)

    def test_nothing_extra_when_it_is_off_or_the_list_is_not_full(self):
        first = {"workflow_runs": [raw(i) for i in range(1, 4)]}
        with mock.patch.object(am, "gh_read", self.reader(first, {}, {})):
            am.fetch_sampled("R", 3, {})
            am.fetch_sampled("R", 5, {"sampling": {"active_probe": True}})
        self.assertEqual(len(self.calls), 2)

    def test_a_failed_look_keeps_the_first_list(self):
        first = {"workflow_runs": [raw(i) for i in range(1, 4)]}

        def read(path, **kw):
            if "status=" in path:
                raise OSError("boom")
            return first
        with mock.patch.object(am, "gh_read", read):
            merged, error = am.fetch_sampled("R", 3, {"sampling": {"active_probe": True}})
        self.assertEqual((len(merged), error), (3, None))


if __name__ == "__main__":
    unittest.main()
