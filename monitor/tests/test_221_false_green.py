# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What was not looked at is never shown as fine: a sample that was full stays full after a batch read, and one source of the external CI never stops the reading of the others."""
import unittest
from unittest import mock

import _testenv  # noqa: F401

from github_actions_monitor.app import actions_monitor as am
from github_actions_monitor.integrations.external_ci import extci_adapters as adapters
from github_actions_monitor.integrations.external_ci import extci_engine as engine
from github_actions_monitor.sentinels import sentinel_local


def run(name, ident):
    return {"repo": "big", "name": name, "id": ident, "attempt": 1, "status": "completed", "conclusion": "success", "branch": "main", "path": f".github/workflows/{name}.yml"}


class FullSampleAfterABatch(unittest.TestCase):
    def tearDown(self):
        am.SAMPLE_INFO.pop("big", None)

    def check(self, held, merged, info):
        if info is not None:
            am.SAMPLE_INFO["big"] = dict(info)
        am.keep_sample_full("big", held, merged, {"cold_runs_per_repo": 5})
        asked = (am.SAMPLE_INFO.get("big") or {}).get("asked")
        return sentinel_local._is_full("big", merged, {"asked": {"big": asked}, "cold_runs_per_repo": 5, "runs_per_repo": 30})

    def test_a_shorter_list_after_the_batch_is_still_full(self):
        held = [run("ci", n) for n in range(10)]
        self.assertTrue(self.check(held, [run("ci", 99), run("docs", 100)], {"asked": 10, "total": 40, "probe": 0}))

    def test_a_full_list_with_nothing_recorded_stays_full(self):
        self.assertTrue(self.check([run("ci", n) for n in range(5)], [run("ci", 99)], None))

    def test_a_list_that_saw_everything_is_not_made_full(self):
        self.assertFalse(self.check([run("ci", 1), run("ci", 2)], [run("ci", 3)], {"asked": 10, "total": 2, "probe": 0}))


class HostileTime(unittest.TestCase):
    def tearDown(self):
        engine.forget()

    def test_one_source_that_breaks_is_degraded_and_the_next_one_is_read(self):
        config = {"external_ci": {"enabled": True, "sources": ["gitlab;repo=one;url=https://one.example.org;project=group/one", "gitlab;repo=two;url=https://two.example.org;project=group/two"]}}

        def hostile(reader, source, cfg):
            if source["repo"] == "one":
                raise OSError(22, "Invalid argument")      # what time.gmtime gives for an enormous time
            return [], []
        with mock.patch.dict(adapters.ADAPTERS, {"gitlab": hostile}):
            self.assertEqual(engine.refresh(config, now=1000.0), 2)
        entries = {s["repo"]: engine._entry(s) for s in engine.configured(config)}
        self.assertEqual((entries["one"]["reason"], entries["one"]["failures"]), ("not_json", 1))
        self.assertEqual((entries["two"]["reason"], entries["two"]["last_ok"]), ("", 1000.0))


if __name__ == "__main__":
    unittest.main()
