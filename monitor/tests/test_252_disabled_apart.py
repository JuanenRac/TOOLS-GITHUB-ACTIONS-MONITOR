# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A workflow the owner switched off by hand is not a red (`ci.disabled_apart`). The case is the one of the accounts of the study of forks: a nightly job copied from the project that is followed fails
for lack of its secrets, the owner switches the workflow off, and its last run stays "failure" for ever. Also the neutral conclusions and a default branch that is not called main, with the
shapes measured on public repositories."""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am, settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import redrule  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402

NOW = 1_800_000_000.0


def stamp(days_ago):
    return datetime.fromtimestamp(NOW - days_ago * 86400, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(repo, ident, path, conclusion, event="schedule", branch="main", days=1):
    return {"repo": repo, "id": ident, "name": path.split(".")[0].title(), "path": path, "branch": branch, "event": event, "fork": False, "status": "completed", "conclusion": conclusion, "started": stamp(days)}


class TheRule(unittest.TestCase):
    def setUp(self):
        redrule.configure({})

    def tearDown(self):
        redrule.configure({})

    def red(self, runs, branch="main"):
        return redrule.red_workflows({"fork": runs}, {"fork": branch}, now=NOW)[0]

    def test_a_nightly_job_copied_from_the_project_followed_is_red_until_the_owner_switches_it_off(self):
        rows = self.red([run("fork", 1, "publish.yml", "failure"), run("fork", 2, "ci.yml", "success", "push")])
        self.assertEqual([r["file"] for r in rows], ["publish.yml"])
        perms = {"fork": {"wf_manual_files": ["publish.yml"]}}
        kept, apart = redrule.split_disabled(rows, perms)
        self.assertEqual((kept, [r["file"] for r in apart]), ([], ["publish.yml"]))

    def test_only_the_workflow_switched_off_leaves_and_only_in_its_own_repository(self):
        rows = [{"repo": "fork", "file": "publish.yml", "workflow": "Publish"}, {"repo": "fork", "file": "build.yml", "workflow": "Build"}, {"repo": "other", "file": "publish.yml", "workflow": "Publish"}]
        kept, apart = redrule.split_disabled(rows, {"fork": {"wf_manual_files": ["publish.yml"]}})
        self.assertEqual([(r["repo"], r["file"]) for r in kept], [("fork", "build.yml"), ("other", "publish.yml")])
        self.assertEqual([(r["repo"], r["file"]) for r in apart], [("fork", "publish.yml")])

    def test_a_workflow_with_no_information_about_it_stays_red(self):
        rows = [{"repo": "fork", "file": "publish.yml", "workflow": "Publish"}]
        for perms in ({}, {"fork": None}, {"fork": {}}, {"fork": {"wf_manual_files": []}}, {"fork": {"wf_error": True}}, None):
            self.assertEqual(redrule.split_disabled(rows, perms), (rows, []), perms)

    def test_the_switch_turns_it_off(self):
        redrule.configure({"ci": {"disabled_apart": False}})
        rows = [{"repo": "fork", "file": "publish.yml", "workflow": "Publish"}]
        self.assertEqual(redrule.split_disabled(rows, {"fork": {"wf_manual_files": ["publish.yml"]}}), (rows, []))
        redrule.configure({"ci": {"disabled_apart": "no"}})      # a value of the wrong type keeps the default (on)
        self.assertEqual(redrule.split_disabled(rows, {"fork": {"wf_manual_files": ["publish.yml"]}})[0], [])


class TheMeasuredShapes(unittest.TestCase):
    def setUp(self):
        redrule.configure({})

    def red(self, runs, branch="main"):
        return redrule.red_workflows({"r": runs}, {"r": branch}, now=NOW)[0]

    def test_cancelled_and_skipped_are_never_red_whatever_their_number(self):
        for conclusion in ("cancelled", "skipped", "neutral", "stale"):
            runs = [run("r", 1, "ci.yml", "success", "push", days=9)] + [run("r", 10 + n, "ci.yml", conclusion, "push", days=1) for n in range(40)]
            self.assertEqual(self.red(runs), [], conclusion)      # TDengine 49 of 100 cancelled, git 47 of 100 skipped

    def test_a_cancelled_run_after_a_failure_does_not_hide_it_and_does_not_replace_it(self):
        runs = [run("r", 1, "ci.yml", "failure", "push", days=3), run("r", 2, "ci.yml", "cancelled", "push", days=1)]
        self.assertEqual(len(self.red(runs)), 1)

    def test_a_default_branch_that_is_not_called_main_is_judged_by_its_own_name(self):
        for branch in ("unstable", "v1.x", "develop", "dev", "v3", "canary"):      # redis, libuv, 215 forks of one account...
            runs = [run("r", 1, "ci.yml", "failure", "push", branch=branch), run("r", 2, "ci.yml", "success", "push", branch="main", days=0.5)]
            self.assertEqual(len(self.red(runs, branch)), 1, branch)
            self.assertEqual(self.red(runs, "main"), [], branch)      # and the branch called main does not decide for it


class TheSnapshot(unittest.TestCase):
    def snapshot(self, perms, config=None):
        redrule.configure(config or {})
        repo = {"branch": "main", "pushed": None, "release": None, "vuln_total": 0, "vuln_sev": {}, "prs": [], "rulesets": [], "label_dependencies": False, "files": {}, "license": None, "fork": False}
        info = {"fork": dict(repo)}
        inp = {"now": datetime.fromtimestamp(NOW, timezone.utc), "today": "2026-11-04", "cfg": sl.DEFAULTS, "repos": ["fork"], "eco": {"fork": "main"}, "repo_info": info, "alerts": {}, "perms": perms,
               "runs": {"fork": [run("fork", 1, "publish.yml", "failure")]}, "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}}, "history": {"days": {}}, "unreleased": {},
               "targets": {}, "errors": {}, "loading": "", "audits": None, "lint": None}
        try:
            return sl.compute_snapshot(inp)
        finally:
            redrule.configure({})

    def test_the_red_of_a_workflow_switched_off_goes_apart_in_the_panel(self):
        on = self.snapshot({"fork": {"at": 4102444800, "wf_manual_files": ["publish.yml"], "wf_manual": ["Publish"], "wf_disabled": []}})
        self.assertEqual((on["a2"]["red"], [r["workflow"] for r in on["a2"]["disabled_by_hand"]]), ([], ["Publish"]))
        self.assertEqual(on["a2"]["level"], "ok")
        off = self.snapshot({"fork": {"at": 4102444800, "wf_manual_files": ["publish.yml"]}}, {"ci": {"disabled_apart": False}})
        self.assertEqual((len(off["a2"]["red"]), off["a2"]["disabled_by_hand"]), (1, []))

    def test_without_the_information_of_the_workflows_the_red_stays(self):
        snap = self.snapshot({})
        self.assertEqual(len(snap["a2"]["red"]), 1)
        self.assertEqual(snap["a2"]["disabled_by_hand"], [])


class TheSurface(unittest.TestCase):
    def test_the_setting_is_on_by_default_and_has_texts_in_eight_languages(self):
        self.assertIs(am.DEFAULTS["ci"]["disabled_apart"], True)
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertIs(example["ci"]["disabled_apart"], True)
        self.assertIn("ci.disabled_apart", settings_api.META)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertTrue(texts.get("cfg.f.ci.disabled_apart") and texts.get("cfg.h.ci.disabled_apart") and "{n}" in texts.get("ui.a2_disabled", ""), lang)
        self.assertIn("ui.a2_disabled", (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
