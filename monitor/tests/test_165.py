# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.6.5: integrity and security. What is not proven is never taken as safe: the dispatch needs the REQUIRED CI of the commit, a fresh fetch, a plain tool name, plain workflow
inputs and a batch that recorded its commit check; `act` stays inside the workspace and dies as a whole tree; the network mode, the webhook and the MCP server refuse the odd
request; the notification limit counts messages; the test suite and the clean-install check are separate stages."""
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import gha_dispatch_all as gd  # noqa: E402
import toolconfig  # noqa: E402

SHA = "a" * 40


def run(name, path, status="completed", conclusion="success", rid=1):
    return {"id": rid, "name": name, "path": f".github/workflows/{path}", "status": status, "conclusion": conclusion}


def page(runs, total=None):
    return {"total_count": len(runs) if total is None else total, "workflow_runs": runs}


class RequiredCi(unittest.TestCase):
    """Green means the REQUIRED workflow passed on that commit, nothing failed or waits for an approval, and the list is complete."""

    def green(self, runs, **kwargs):
        with mock.patch.object(gd, "ghj", return_value=page(runs)):
            return gd.ci_green("R", SHA, config={}, **kwargs)

    def test_a_successful_documentation_only_workflow_is_not_a_green_commit(self):
        ok, bad, pending = self.green([run("docs-only", "docs.yml")])
        self.assertFalse(ok)
        self.assertTrue(any("ci.yml" in b for b in bad))

    def test_the_required_ci_passing_is_green(self):
        self.assertEqual(self.green([run("A.R.M.O.R. CI baseline", "ci.yml"), run("docs", "docs.yml", rid=2)]), (True, [], 0))

    def test_action_required_blocks(self):
        ok, bad, _ = self.green([run("CI", "ci.yml"), run("Deploy", "deploy.yml", conclusion="action_required", rid=2)])
        self.assertFalse(ok)
        self.assertEqual(bad, ["Deploy"])

    def test_a_workflow_that_is_still_running_blocks(self):
        ok, _bad, pending = self.green([run("CI", "ci.yml"), run("Lint", "lint.yml", status="in_progress", conclusion=None, rid=2)])
        self.assertEqual((ok, pending), (False, 1))

    def test_a_required_workflow_that_is_still_running_is_not_green(self):
        self.assertFalse(self.green([run("CI", "ci.yml", status="queued", conclusion=None)])[0])

    def test_a_failed_required_workflow_is_not_green(self):
        ok, bad, _ = self.green([run("CI", "ci.yml", conclusion="failure")])
        self.assertEqual((ok, bad[0]), (False, "CI"))

    def test_a_cancelled_required_workflow_does_not_count_as_passed(self):
        self.assertFalse(self.green([run("CI", "ci.yml", conclusion="cancelled")])[0])

    def test_a_truncated_sample_is_never_green(self):
        full = [run("Other", f"o{i}.yml", rid=i + 10) for i in range(100)]
        pages = [page(full, total=900)] * gd.CI_PAGES
        with mock.patch.object(gd, "ghj", side_effect=pages):
            ok, bad, _ = gd.ci_green("R", SHA, config={})
        self.assertFalse(ok)
        self.assertTrue(any("incomplete" in b for b in bad))

    def test_several_pages_are_read_until_the_list_is_complete(self):
        first = [run("W", f"w{i}.yml", rid=i + 10) for i in range(100)]
        second = [run("CI", "ci.yml", rid=1)]
        answers = [page(first, total=101), page(second, total=101)]
        with mock.patch.object(gd, "ghj", side_effect=answers) as fake:
            ok, bad, _ = gd.ci_green("R", SHA, config={})
        self.assertEqual((ok, bad, fake.call_count), (True, [], 2))

    def test_the_required_list_comes_from_the_configuration_per_repository(self):
        config = {"dispatch": {"required_ci": ["ci.yml", "tests.yml"], "required_ci_repos": {"R": ["build-check.yml"]}}}
        self.assertEqual(gd.required_ci("R", config), ["build-check.yml"])
        self.assertEqual(gd.required_ci("Other", config), ["ci.yml", "tests.yml"])
        self.assertEqual(gd.required_ci("Other", {}), ["ci.yml"])
        self.assertEqual(gd.required_ci("Other", {"dispatch": {"required_ci": "nope"}}), ["ci.yml"])
        self.assertEqual(gd.required_ci("Other", {"dispatch": {"required_ci_profiles": {"night": ["x.yml"]}}}, profile="night"), ["x.yml"])
        with mock.patch.object(gd, "ghj", return_value=page([run("CI", "ci.yml")])):
            self.assertFalse(gd.ci_green("Other", SHA, config=config)[0])   # tests.yml is required and absent

    def test_the_batch_skips_a_repository_whose_ci_is_not_green(self):
        name = next(iter(gd.TARGETS))
        batch = gd.run_batch([name], False, True, head_fn=lambda repo: (SHA, ""), green_fn=lambda repo, sha: (False, ["x"], 0), fire_fn=mock.Mock(side_effect=AssertionError("fired")))
        self.assertIn("skipped", batch["targets"][name])


class FreshFetch(unittest.TestCase):
    """A failed fetch, a hung git or a value that is not a commit id blocks the dispatch."""

    def clone(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        (Path(tmp.name) / "R").mkdir()
        return mock.patch.object(gd, "ROOT", Path(tmp.name))

    @staticmethod
    def git(fetch=(0, "", ""), head=(0, SHA, ""), remote=(0, SHA, "")):
        answers = {"fetch": fetch, "HEAD": head, "origin/main": remote}

        def fake(path, *args, timeout=60):
            return answers[args[1] if args[0] == "rev-parse" else args[0]]
        return fake

    def test_a_failed_fetch_blocks_even_when_an_old_origin_main_is_there(self):
        with self.clone(), mock.patch.object(gd, "git_run", self.git(fetch=(1, "", "could not resolve host"))):
            sha, why = gd.local_head("R")
        self.assertIsNone(sha)
        self.assertIn("fetch", why)

    def test_a_git_that_does_not_finish_blocks(self):
        with self.clone(), mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 1)):
            sha, why = gd.local_head("R")
        self.assertEqual(sha, None)
        self.assertTrue(why)

    def test_something_that_is_not_a_commit_id_blocks(self):
        with self.clone(), mock.patch.object(gd, "git_run", self.git(head=(0, "abc123", ""), remote=(0, "abc123", ""))):
            self.assertIsNone(gd.local_head("R")[0])
        with self.clone(), mock.patch.object(gd, "git_run", self.git(remote=(128, "", "bad revision"))):
            self.assertIsNone(gd.local_head("R")[0])

    def test_a_fresh_fetch_and_the_same_commit_is_fine_and_a_different_head_is_reported(self):
        with self.clone(), mock.patch.object(gd, "git_run", self.git()):
            self.assertEqual(gd.local_head("R"), (SHA, ""))
        with self.clone(), mock.patch.object(gd, "git_run", self.git(head=(0, "b" * 40, ""))):
            sha, why = gd.local_head("R")
        self.assertEqual(sha, SHA)
        self.assertTrue(why)

    def test_the_dispatch_loop_skips_a_repository_when_the_head_has_a_problem(self):
        name = next(iter(gd.TARGETS))
        batch = gd.run_batch([name], False, True, head_fn=lambda repo: (None, "git fetch failed"), green_fn=mock.Mock(side_effect=AssertionError("asked")), fire_fn=mock.Mock(side_effect=AssertionError("fired")))
        self.assertEqual(batch["targets"][name], {"skipped": "git fetch failed"})


class CatalogueBounds(unittest.TestCase):
    """The catalogue cannot name a tool outside the tools folder or change the repository, the ref or dry_run."""

    @staticmethod
    def target(**changes):
        return {"X": {"workflow": "package-build.yml", "tool": "t.py", "extra": [], **changes}}

    def test_a_tool_must_be_a_plain_file_name(self):
        for bad in ("../../evil.py", "..\\evil.py", "sub/t.py", "C:\\evil.py", "/etc/evil.py", "..py", "a..py", "-x.py", "t.py ", "", ".py"):
            self.assertTrue(gd.validate_targets(self.target(tool=bad)), repr(bad))
        self.assertEqual(gd.validate_targets(self.target(tool="fetch_and_sign.py")), [])

    def test_a_catalogue_name_cannot_be_a_folder_trick(self):
        for bad in ("..", ".", "-rf", "..:part"):
            self.assertTrue(gd.validate_targets({bad: self.target()["X"]}), repr(bad))

    def test_finalize_and_preflight_refuse_a_tool_outside_the_folder(self):
        hostile = {"X": {"workflow": "package-build.yml", "tool": "../../evil.py", "extra": []}}
        with self.assertRaises(ValueError):
            gd.finalize_command("X", 5, hostile)
        with mock.patch.dict(gd.TARGETS, hostile):
            problems = gd.preflight(["X"], workflows=False)
        self.assertEqual(len(problems), 1)
        self.assertIn("../../evil.py", problems[0])

    def test_a_symbolic_link_out_of_the_tools_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools, outside = Path(tmp) / "tools", Path(tmp) / "elsewhere"
            tools.mkdir(), outside.mkdir()
            (outside / "evil.py").write_text("print(1)\n", encoding="utf-8")
            (tools / "ok.py").write_text("print(1)\n", encoding="utf-8")
            try:
                os.symlink(outside / "evil.py", tools / "link.py")
            except (OSError, NotImplementedError):
                self.skipTest("symbolic links are not available here")
            self.assertEqual(gd.tool_path("ok.py", tools), tools / "ok.py")
            self.assertIsNone(gd.tool_path("link.py", tools))

    def test_extra_may_only_hold_workflow_inputs(self):
        for bad in (["-R", "other/repo"], ["--repo", "o/r"], ["--ref", "dev"], ["-f", "dry_run=false"], ["-f", "ref=dev"], ["-f", "a=b", "-f", "a=c"], ["-f"], ["-F", "a=b"],
                    ["-f", "no equals"], ["-f", "bad key=1"], ["workflow", "x.yml"], ["-f", "a=" + "x" * 301], ["-f", "a=line\nbreak"]):
            self.assertTrue(gd.validate_targets(self.target(extra=bad)), bad)
        self.assertEqual(gd.validate_targets(self.target(extra=["-f", "idf_image=espressif/idf:v5.5.5", "-f", "mode=fast"])), [])

    def test_the_dispatch_command_is_built_from_the_validated_inputs(self):
        args = gd.dispatch_args("firmware-build.yml", "REPO", False, ["-f", "idf_image=img"])
        self.assertEqual(args[:2], ["workflow", "run"])
        self.assertEqual(args.count("-R"), 1)
        self.assertEqual(args.count("--ref"), 1)
        self.assertIn("dry_run=true", args)
        self.assertEqual(args[-2:], ["-f", "idf_image=img"])
        self.assertIn("dry_run=false", gd.dispatch_args("firmware-build.yml", "REPO", True, []))
        with self.assertRaises(ValueError):
            gd.dispatch_args("firmware-build.yml", "REPO", False, ["-f", "dry_run=false"])
        with self.assertRaises(ValueError):
            gd.dispatch_args("firmware-build.yml", "REPO", False, ["-R", "evil/repo"])

    def test_a_target_changed_after_loading_is_still_refused_at_dispatch_time(self):
        hostile = {"X-FAKE": {"workflow": "firmware-build.yml", "tool": "t.py", "extra": ["-f", "dry_run=false"]}}
        with mock.patch.dict(gd.TARGETS, hostile), mock.patch.object(gd, "gh", side_effect=AssertionError("gh called")):
            with self.assertRaises(RuntimeError):
                gd.fire("X-FAKE", "X-FAKE", SHA, False)

    def test_finalize_flags_are_long_flags(self):
        self.assertTrue(gd.validate_targets(self.target(finalize_flags=["--run", "9;rm"])))
        self.assertTrue(gd.validate_targets(self.target(finalize_flags=["-x"])))
        self.assertEqual(gd.validate_targets(self.target(finalize_flags=["--bench"])), [])


class LegacyBatches(unittest.TestCase):
    """A batch that did not record the commit check is not offered for signing unless the run is matched again, on GitHub, to the recorded commit."""

    def setUp(self):
        self.name = next(iter(gd.TARGETS))
        self.batch = {"targets": {self.name: {"run": 11, "sha": SHA}}}
        self.state = lambda repo, run: ("completed", "success", "https://example.invalid/1", [])

    def test_strict_by_default(self):
        row = gd.finalize_rows(self.batch, state_fn=self.state)[0]
        self.assertEqual((row["state"], row["reason"]), ("not_ready", "needs_review"))
        self.assertNotIn("argv", row)

    def test_legacy_needs_the_commit_to_match_on_github(self):
        row = gd.finalize_rows(self.batch, state_fn=self.state, legacy=True, sha_fn=lambda repo, run: SHA)[0]
        self.assertEqual((row["state"], row.get("legacy")), ("ready", True))
        row = gd.finalize_rows(self.batch, state_fn=self.state, legacy=True, sha_fn=lambda repo, run: "b" * 40)[0]
        self.assertEqual(row["state"], "not_ready")
        row = gd.finalize_rows(self.batch, state_fn=self.state, legacy=True, sha_fn=mock.Mock(side_effect=RuntimeError("down")))[0]
        self.assertEqual(row["state"], "not_ready")

    def test_legacy_never_rescues_a_run_that_was_marked_as_another_commit(self):
        self.batch["targets"][self.name]["sha_matched"] = False
        row = gd.finalize_rows(self.batch, state_fn=self.state, legacy=True, sha_fn=lambda repo, run: SHA)[0]
        self.assertEqual(row["reason"], "sha_mismatch")

    def test_legacy_without_a_recorded_commit_is_not_ready(self):
        self.batch["targets"][self.name].pop("sha")
        self.assertEqual(gd.finalize_rows(self.batch, state_fn=self.state, legacy=True, sha_fn=lambda repo, run: SHA)[0]["state"], "not_ready")

    def test_a_matched_run_is_ready_without_a_legacy_flag(self):
        self.batch["targets"][self.name]["sha_matched"] = True
        row = gd.finalize_rows(self.batch, state_fn=self.state)[0]
        self.assertEqual(row["state"], "ready")
        self.assertNotIn("legacy", row)


if __name__ == "__main__":
    unittest.main()
