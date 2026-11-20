# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The self-hosted runners the jobs really ran on, crossed with what the workflow files say (runners.model.observed_reads_per_cycle): the reader of `runs-on`, the reasons, the wiring and the reads."""
import inspect
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor as am
from github_actions_monitor.app import settings_api
from github_actions_monitor.integrations import runner_model as rm

ON = {"runners": {"model": {"enabled": True, "observed_reads_per_cycle": 3}}}
CFG = rm.settings(ON)
FILE = """name: CI
on: [push]
jobs:
  a:
    runs-on: ubuntu-latest
  b:
    runs-on: ${{ matrix.os }}
  c:
    runs-on: [self-hosted, Linux]  # my box
  d:
    runs-on:
      group: big
      labels: [gpu]
  e:
    runs-on:
      - self-hosted
      - arm
"""


def row(repo, labels, runner="box", group=""):
    return {"repo": repo, "run": 1, "name": "j", "status": "in_progress", "labels": labels, "created": None, "started": None, "runner": runner, "group": group}


class StaticRunsOn(unittest.TestCase):
    def test_it_reads_the_forms_of_runs_on_and_marks_an_expression(self):
        out = rm.static_runs_on(FILE)
        self.assertEqual(out["a"], {"labels": ["ubuntu-latest"], "group": "", "dynamic": False})
        self.assertEqual(out["b"], {"labels": [], "group": "", "dynamic": True})
        self.assertEqual(out["c"]["labels"], ["self-hosted", "linux"])
        self.assertEqual((out["d"]["group"], out["d"]["labels"]), ("big", ["gpu"]))
        self.assertEqual(out["e"]["labels"], ["self-hosted", "arm"])

    def test_a_text_that_is_not_a_workflow_gives_nothing_and_never_raises(self):
        for text in (None, "", "jobs:", "a: [", "\x00\x01", "jobs:\n  x:\n    runs-on:\n"):
            self.assertIsInstance(rm.static_runs_on(text), dict)


class Observed(unittest.TestCase):
    def test_it_is_off_by_default_and_a_setting_with_a_range(self):
        self.assertEqual(rm.settings({})["observed_reads_per_cycle"], 0)
        self.assertEqual(rm.settings({"runners": {"model": {"observed_reads_per_cycle": 99}}})["observed_reads_per_cycle"], 0)
        self.assertEqual(rm.settings({"runners": {"model": {"observed_reads_per_cycle": True}}})["observed_reads_per_cycle"], 0)
        self.assertTrue(settings_api.check_value("runners.model.observed_reads_per_cycle", 5)[0])
        self.assertFalse(settings_api.check_value("runners.model.observed_reads_per_cycle", 21)[0])

    def test_an_expression_that_hides_the_self_hosted_runner_is_named(self):
        declared = {"r": {"ci.yml": rm.static_runs_on("jobs:\n  b:\n    runs-on: ${{ vars.RUNNER }}\n")}}
        out = rm.observed([row("r", ["self-hosted", "linux"], "box1")], declared, CFG)
        self.assertEqual((out[0]["reasons"], out[0]["runners"], out[0]["files"]), (["dynamic"], ["box1"], "read"))

    def test_a_file_that_says_self_hosted_is_not_a_finding(self):
        out = rm.observed([row("r", ["self-hosted"])], {"r": {"ci.yml": rm.static_runs_on(FILE)}}, CFG)
        self.assertEqual(out[0]["reasons"], [])

    def test_no_file_and_no_expression_is_undeclared(self):
        out = rm.observed([row("r", ["self-hosted"])], {"r": {"ci.yml": rm.static_runs_on("jobs:\n  a:\n    runs-on: ubuntu-latest\n")}}, CFG)
        self.assertEqual(out[0]["reasons"], ["undeclared"])

    def test_a_repository_whose_files_were_not_read_is_unread_never_judged(self):
        out = rm.observed([row("r", ["self-hosted"])], {}, CFG)
        self.assertEqual((out[0]["files"], out[0]["reasons"]), ("unread", []))

    def test_a_public_repository_is_named_only_when_its_visibility_is_known(self):
        rows = [row("pub", ["self-hosted"]), row("priv", ["self-hosted"]), row("odd", ["self-hosted"])]
        out = {r["repo"]: r["reasons"] for r in rm.observed(rows, {}, CFG, private={"priv"}, known={"pub", "priv"})}
        self.assertEqual(out, {"pub": ["public"], "priv": [], "odd": []})

    def test_a_hosted_job_is_never_listed_and_the_labels_of_the_job_decide(self):
        self.assertEqual(rm.observed([row("r", ["ubuntu-latest"], "GitHub Actions 7")], {}, CFG), [])

    def test_the_model_carries_it_only_when_the_setting_is_on(self):
        rows = [row("r", ["self-hosted"])]
        off = rm.build({"runners": {"model": {"enabled": True}}}, rows, [], [], {}, None, 0)
        on = rm.build(ON, rows, [], [], {}, None, 0)
        self.assertEqual(off["observed"], {"enabled": False, "rows": []})
        self.assertTrue(on["observed"]["enabled"])
        self.assertEqual(on["observed"]["rows"][0]["repo"], "r")


class Wiring(unittest.TestCase):
    def setUp(self):
        am.RUNNER_FILES["reader"] = None
        am.RUNNER_JOBS["rows"].clear()

    def tearDown(self):
        am.RUNNER_FILES["reader"] = None
        am.RUNNER_JOBS["rows"].clear()

    def test_it_reads_nothing_while_off_and_only_the_repositories_with_a_self_hosted_job_when_on(self):
        am.RUNNER_JOBS["rows"][("r", 1)] = {"at": 0, "rows": [row("r", ["self-hosted"])]}
        am.RUNNER_JOBS["rows"][("h", 2)] = {"at": 0, "rows": [row("h", ["ubuntu-latest"])]}
        seen = []

        def read(endpoint, retries=0):
            seen.append(endpoint)
            raise OSError("404 not found")
        with mock.patch.object(am, "gh_read", read):
            self.assertEqual(am.read_runner_workflows({"runners": {"model": {"enabled": True}}}, {}), 0)
            self.assertEqual(seen, [])
            self.assertEqual(am.read_runner_workflows(ON, {}), 1)
        self.assertEqual(len(seen), 1)
        self.assertIn("/r/contents/.github/workflows", seen[0])

    def test_the_cycle_and_the_ui_and_the_setting_are_wired(self):
        self.assertIn('("runner_workflows", lambda: spare and read_runner_workflows(config, data))', inspect.getsource(am.maintain_extras))
        html = (Path(__file__).resolve().parent.parent / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("ui.adv_model_observed", html)
        self.assertIn("observed_reads_per_cycle", inspect.getsource(rm.settings))


if __name__ == "__main__":
    unittest.main()
