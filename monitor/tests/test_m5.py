# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.3.2 (and 1.3.3: A2 ignores workflows that never run on the branch): A2 `unknown` on a full, inconclusive run sample; profiles.example.json; clean-install check of the zip; the "writes to GitHub" wording in the
8 languages; the A10 quota settings. Offline, nothing is written outside temporary directories."""
import json
import shutil
import tempfile
import unittest
import zipfile
import _testenv  # noqa: F401
from datetime import datetime, timezone
from pathlib import Path

import make_release as mr  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402
from github_actions_monitor.app import surface  # noqa: E402

NOW = datetime(2026, 11, 6, 12, 0, 0, tzinfo=timezone.utc)
CAPS = {"runs_per_repo": 6, "cold_runs_per_repo": 3}
HERE = Path(mr.HERE)


def run(name, conclusion, path, rid, started="2026-11-06T09:00:00Z"):
    return {"repo": "R", "id": rid, "name": name, "path": path, "branch": "main", "status": "completed", "conclusion": conclusion, "started": started,
            "url": f"https://github.com/o/R/actions/runs/{rid}", "seconds": 60, "actor": "o", "sha": "abc1234"}


def clone(*files):
    """A local scan of repository R with these workflow files (the shape surface.scan_clone returns)."""
    return {"R": {"workflows": [surface.scan_workflow("on: push", f) for f in files], "stacks": ["python"], "dependabot_yml": True, "codeql_yml": True,
                  "manifest": None, "changelog_top": None}}


def snapshot(runs, scans=None, cfg=None, **over):
    info = {"R": {"branch": "main", "pushed": "2026-11-05T10:00:00Z", "release": {"tagName": "v1", "publishedAt": "2026-10-01T00:00:00Z"}, "vuln_total": 0, "vuln_sev": {},
                  "prs": [], "rulesets": [], "label_dependencies": True, "files": {}}}
    inp = {"now": NOW, "today": "2026-11-06", "cfg": cfg or sl.DEFAULTS, "repos": ["R"], "eco": {"R": "main"}, "repo_info": info, "alerts": {}, "perms": {}, "runs": {"R": runs},
           "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}}, "history": {"days": {}}, "unreleased": {}, "targets": {}, "errors": {},
           "loading": "", "audits": None, "sample_caps": CAPS, "scans": scans}
    inp.update(over)
    return sl.compute_snapshot(inp)


class A2FullSample(unittest.TestCase):
    FULL = [run("CI", "success", "ci.yml", i, f"2026-11-06T0{i}:00:00Z") for i in range(6)]

    def test_full_sample_without_a_clone_is_unknown_not_green(self):
        a2 = snapshot(self.FULL)["a2"]
        self.assertEqual(a2["full_sample"], ["R"])
        self.assertEqual(a2["inconclusive"], ["R"])
        self.assertEqual(a2["level"], "unknown")

    def test_full_sample_that_shows_every_workflow_of_the_clone_is_green(self):
        scans = clone("ci.yml")
        a2 = snapshot(self.FULL, scans)["a2"]
        self.assertEqual(a2["full_sample"], ["R"])
        self.assertEqual(a2["inconclusive"], [])
        self.assertEqual(a2["level"], "ok")

    def test_full_sample_that_hides_a_workflow_of_the_clone_is_unknown(self):
        scans = clone("ci.yml", "release.yml")
        self.assertEqual(snapshot(self.FULL, scans)["a2"]["level"], "unknown")

    def test_a_short_sample_is_conclusive(self):
        a2 = snapshot(self.FULL[:4])["a2"]
        self.assertEqual((a2["full_sample"], a2["inconclusive"], a2["level"]), ([], [], "ok"))

    def test_red_always_wins(self):
        runs = self.FULL[:5] + [run("CI", "failure", "ci.yml", 9, "2026-11-06T11:00:00Z")]
        self.assertEqual(snapshot(runs)["a2"]["level"], "bad")

    def scans_of(self, **texts):
        return {"R": {"workflows": [surface.scan_workflow(t, f) for f, t in texts.items()], "stacks": [], "dependabot_yml": True, "codeql_yml": True,
                      "manifest": None, "changelog_top": None}}

    def test_workflows_that_never_run_on_the_branch_are_ignored(self):
        for text in ("on: workflow_dispatch", "on:\n  workflow_dispatch:\n  release:\n    types: [published]", "on: [release, workflow_call]",
                     "true:\n  workflow_call:\n", "on:\n  push:\n    tags:\n      - 'v*'\n", "on:\n  - workflow_dispatch\n  - workflow_call\n"):
            scans = self.scans_of(**{"ci.yml": "on: push", "other.yml": text})
            self.assertEqual(snapshot(self.FULL, scans)["a2"]["level"], "ok", text)

    def test_workflows_that_run_on_the_branch_still_count(self):
        for text in ("on: push", "on: [push]", "on:\n  pull_request:\n  push:\n", "on:\n  schedule:\n    - cron: '0 1 * * *'\n",
                     "on:\n  push:\n    tags: ['v*']\n    branches: [main]\n", "on:\n  push:\n    paths: ['a/**']\n", "on:\n  issues:\n    types: [opened]\n"):
            scans = self.scans_of(**{"ci.yml": "on: push", "other.yml": text})
            self.assertEqual(snapshot(self.FULL, scans)["a2"]["level"], "unknown", text)

    def test_an_unparseable_on_counts_as_before(self):
        for text in ("on: {push: {tags: ['v*']}}", "name: x\n", "on: [push"):
            self.assertIsNone(surface.main_triggered(text), text)
            scans = self.scans_of(**{"ci.yml": "on: push", "other.yml": text})
            self.assertEqual(snapshot(self.FULL, scans)["a2"]["level"], "unknown", text)

    def test_only_manual_workflows_in_a_known_clone_is_conclusive(self):
        scans = self.scans_of(**{"a.yml": "on: workflow_dispatch", "b.yml": "on:\n  release:\n    types: [created]\n", "c.yml": "on:\n  pull_request:\n    paths: ['x/**']\n"})
        self.assertEqual(snapshot(self.FULL, scans)["a2"]["inconclusive"], [])

    def test_the_parser_handles_comments_and_quoted_keys(self):
        self.assertFalse(surface.main_triggered("name: x\n\"on\": # trigger\n  workflow_dispatch: # manual\n"))
        self.assertTrue(surface.main_triggered("name: x\non:\n  # push too\n  push: # yes\n  workflow_dispatch:\njobs:\n  a: {}\n"))

    def test_the_switch_restores_the_informative_behaviour(self):
        cfg = dict(sl.DEFAULTS, a2_full_sample_unknown=False)
        a2 = snapshot(self.FULL, cfg=cfg)["a2"]
        self.assertEqual(a2["inconclusive"], ["R"])
        self.assertEqual(a2["level"], "ok")

    def test_no_data_is_still_unknown(self):
        self.assertEqual(snapshot([])["a2"]["level"], "unknown")

    def test_the_switch_is_a_known_option_of_the_sentinel(self):
        self.assertIs(sl.sentinel_config({})["a2_full_sample_unknown"], True)
        self.assertIs(sl.sentinel_config({"sentinel": {"a2_full_sample_unknown": False}})["a2_full_sample_unknown"], False)


class A10Quota(unittest.TestCase):
    def test_budget_share_is_configurable_with_a_conservative_default(self):
        self.assertEqual(surface.DEFAULTS["budget_share"], 0.5)
        self.assertEqual(surface.settings({})["budget_share"], 0.5)
        self.assertEqual(surface.settings({"sentinel": {"surface": {"budget_share": 0.25}}})["budget_share"], 0.25)
        self.assertEqual(surface.settings({"sentinel": {"surface": {"budget_share": "all"}}})["budget_share"], 0.5)   # a bad type keeps the default

    def test_the_example_configuration_shows_the_quota_options(self):
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["sentinel"]["surface"]["budget_share"], 0.5)
        self.assertEqual(example["sentinel"]["surface"]["min_rate_factor"], 2.0)
        self.assertIs(example["sentinel"]["a2_full_sample_unknown"], True)

    def test_the_pause_is_reported_in_the_snapshot(self):
        paused = {"remaining": 900, "needed": 1600}
        self.assertEqual(snapshot([], surface_paused=paused)["a10"]["paused"], paused)
        self.assertIsNone(snapshot([])["a10"]["paused"])


class ProfilesExample(unittest.TestCase):
    def test_the_example_is_coherent_with_the_neutral_catalogues(self):
        self.assertEqual(mr.example_profiles_problems(), [])
        data = json.loads((HERE / "assets" / "examples" / "profiles.example.json").read_text(encoding="utf-8"))
        self.assertIn("MYPROJECT-FIRMWARE", json.dumps(data))
        self.assertNotIn("HYDRA", json.dumps(data))

    def test_it_is_in_the_zip_and_has_the_authorship(self):
        self.assertIn("profiles.example.json", mr.DATA_JSON)
        self.assertIn("assets/examples/profiles.example.json", mr.REQUIRED_MEMBERS)
        self.assertEqual(mr.authorship_problems({"p/profiles.example.json": (HERE / "assets" / "examples" / "profiles.example.json").read_bytes(), **{f"p/{n}": (HERE / n).read_bytes() for n in mr.LEGAL}}), [])

    def test_a_broken_example_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "assets" / "examples").mkdir(parents=True)
            for name in ("targets.example.json", "ecosystems.example.json", "profiles.example.json"):
                shutil.copy(HERE / "assets" / "examples" / name, Path(tmp) / "assets" / "examples")
            data = json.loads((Path(tmp) / "assets" / "examples" / "profiles.example.json").read_text(encoding="utf-8"))
            data["profiles"]["bad"] = {"names": ["NOT-A-TARGET"]}
            data["profiles"]["empty"] = {"workflows": ["apk-build.yml"], "ecosystems": ["main"]}   # valid, but the example has no APK target
            data["profiles"]["wrong_eco"] = {"workflows": ["firmware-build.yml"], "ecosystems": ["nope"]}
            (Path(tmp) / "assets" / "examples" / "profiles.example.json").write_text(json.dumps(data), encoding="utf-8")
            problems = "; ".join(mr.example_profiles_problems(Path(tmp)))
        self.assertIn("NOT-A-TARGET", problems)
        self.assertIn("profile empty selects no target", problems)
        self.assertIn("nope", problems)

    def test_the_global_state_is_restored(self):
        from github_actions_monitor.cli import gha_dispatch_all as gd
        before = gd.ECOSYSTEMS
        mr.example_profiles_problems()
        self.assertEqual(gd.ECOSYSTEMS, before)


class CleanInstall(unittest.TestCase):
    def test_a_zip_with_a_missing_file_fails_the_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "x.zip"
            entries = {"github_actions_monitor/tool_version.py": b"TOOL_VERSION = '0'\n"}
            mr.write_zip(archive, entries)
            with self.assertRaises(SystemExit) as ctx:
                mr.clean_install_check(archive, entries)
            self.assertIn("required files missing", str(ctx.exception))

    def test_a_member_that_does_not_compile_fails_the_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            entries = {f"github_actions_monitor/{m}": b"x = 1\n" for m in mr.REQUIRED_MEMBERS}
            entries["github_actions_monitor/broken.py"] = b"def (:\n"
            archive = Path(tmp) / "x.zip"
            mr.write_zip(archive, entries)
            with self.assertRaises(SystemExit) as ctx:
                mr.clean_install_check(archive, entries)
            self.assertIn("does not compile", str(ctx.exception))

    def test_the_writer_keeps_the_executable_bit_of_the_launchers(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "x.zip"
            mr.write_zip(archive, {"p/a.sh": b"#!/bin/sh\n", "p/b.txt": b"x"})
            with zipfile.ZipFile(archive) as z:
                modes = {i.filename: (i.external_attr >> 16) & 0o777 for i in z.infolist()}
        self.assertEqual(modes, {"p/a.sh": 0o755, "p/b.txt": 0o644})


class WritesToGithubWording(unittest.TestCase):
    """The package writes to GitHub only when YOU run `dispatch --go`, `dispatch --real` or `finalize --execute`; every language says so."""
    NEEDLES = ("dispatch --go", "dispatch --real", "finalize --execute")

    def test_readme_and_quickstart_in_the_eight_languages_name_the_three_commands(self):
        for lang in mr.LANGS:
            for stem in ("README", "QUICKSTART"):
                text = (HERE / f"{stem}_{lang}.txt").read_text(encoding="utf-8")
                for needle in self.NEEDLES if stem == "README" else ("dispatch --go", "--real", "finalize --execute"):
                    self.assertIn(needle, text, f"{stem}_{lang}.txt lacks {needle}")

    def test_the_language_chooser_says_it_too(self):
        text = (HERE / "README.txt").read_text(encoding="utf-8")
        self.assertIn("finalize --execute", text)
        self.assertNotIn("writes nothing to GitHub and keeps", text)


class Version(unittest.TestCase):
    def test_new_texts_exist_in_the_eight_catalogues(self):
        for lang in mr.LANGS:
            cat = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ui.a2_inconclusive", "ui.a10_paused"):
                self.assertTrue(cat.get(key, "").strip(), f"{lang}: {key}")


if __name__ == "__main__":
    unittest.main()
