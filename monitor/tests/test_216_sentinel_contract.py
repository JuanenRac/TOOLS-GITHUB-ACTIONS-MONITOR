# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The contract of every loop of a sentinel (see `sentinel_base`): one bad element never aborts the round, what could not be read is held and named (never closed as fixed, never counted as
checked), and what left the scope is dropped. The same checks run on EVERY sentinel of the registry, so a new sentinel that does not keep the contract fails here."""
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_173  # noqa: E402
import test_191_sentinel  # noqa: E402
import test_217_supply_chain  # noqa: E402
import test_223_delivery  # noqa: E402
from github_actions_monitor.sentinels import sentinel_base, sentinel_local, sentinel_registry  # noqa: E402

NOW = 1_800_000_000.0
BUILDERS = {"collab": test_173.build, "security": test_191_sentinel.build, "supply": test_217_supply_chain.build, "delivery": test_223_delivery.build}
LOCAL = ("ci",)      # the CI sentinel wraps the old object (sentinel_local), checked below stage by stage


def broken(sentinel, bad):
    """Replaces the reading of one repository: it raises for the names in `bad` and marks the others as read."""
    def scan(repo, now, *args, **kwargs):
        if repo in bad:
            raise RuntimeError("boom " + repo)
        with sentinel.lock:
            sentinel.state["per_repo"][repo] = {"scanned": now}
        return 1
    sentinel.scan = scan


class EveryLoopOfTheRegistry(unittest.TestCase):
    def test_the_contract_covers_every_registered_sentinel(self):
        self.assertEqual(sorted(sentinel_registry._registry()), sorted(list(BUILDERS) + list(LOCAL)),
                         "a new sentinel must be added to this contract (and keep it) before it is registered")

    def make(self, kind, repos, bad=()):
        sentinel, _fake, _folder = BUILDERS[kind](self, {}, repos=tuple(repos))
        broken(sentinel, set(bad))
        return sentinel

    def test_a_bad_repository_is_recorded_and_the_others_are_read(self):
        for kind in BUILDERS:
            with self.subTest(kind=kind):
                sentinel = self.make(kind, ["bad", "good1", "good2"], bad={"bad"})
                self.assertTrue(sentinel.tick(NOW))
                self.assertEqual(sorted(r for r, rec in sentinel.state["per_repo"].items() if rec.get("scanned")), ["good1", "good2"])
                self.assertIn("bad", sentinel.errors)
                self.assertIn("bad", sentinel.get_status().get("unchecked", []), "a repository that could not be read is named, it never counts as zero alerts")
                self.assertEqual(sentinel.get_status()["repos_checked"], 2)

    def test_what_was_known_of_an_unreadable_repository_is_held_not_closed(self):
        for kind in BUILDERS:
            with self.subTest(kind=kind):
                sentinel = self.make(kind, ["bad", "good"], bad={"bad"})
                with sentinel.lock:
                    sentinel.state["alerts"]["old"] = {"id": "old", "repo": "bad", "code": "x", "level": "error"}
                    sentinel.state["per_repo"]["bad"] = {"scanned": NOW - 50}
                sentinel.tick(NOW)
                self.assertIn("old", sentinel.state["alerts"], "not looking is not fixed")
                self.assertEqual(sentinel.state["per_repo"]["bad"]["scanned"], NOW - 50, "and it is not refreshed as if it had been looked at")

    def test_what_left_the_scope_is_dropped_with_its_alerts_and_its_errors(self):
        for kind in BUILDERS:
            with self.subTest(kind=kind):
                sentinel = self.make(kind, ["keep", "gone"], bad={"gone"})
                with sentinel.lock:
                    sentinel.state["alerts"]["a"] = {"id": "a", "repo": "gone", "code": "x", "level": "error"}
                    sentinel.state["per_repo"]["gone"] = {"scanned": NOW - 50}
                sentinel.tick(NOW)
                self.assertIn("gone", sentinel.errors)
                sentinel.ctx["repos_fn"] = lambda: ["keep"]
                sentinel.tick(NOW + 5000)
                self.assertNotIn("gone", sentinel.state["per_repo"])
                self.assertNotIn("a", sentinel.state["alerts"])
                self.assertNotIn("gone", sentinel.errors)

    def test_an_error_of_a_part_of_a_repository_leaves_with_it(self):
        errors = {"gone:files": {"message": "x", "at": "t"}, "keep": {"message": "y", "at": "t"}, "search": {"message": "z", "at": "t"}}
        sentinel_base.forget_errors(errors, ["keep"])
        self.assertEqual(sorted(errors), ["keep", "search"])


class TheHelper(unittest.TestCase):
    def test_guarded_records_the_cause_and_clears_it_on_success(self):
        errors = {}
        self.assertEqual(sentinel_base.guarded(errors, "k", lambda: 1 / 0, default="d", now=NOW), "d")
        self.assertIn("division", errors["k"]["message"])
        self.assertEqual(sentinel_base.guarded(errors, "k", lambda x: x + 1, 2), 3)
        self.assertEqual(errors, {})


class TheItemsOfOneRepository(unittest.TestCase):
    def test_one_malformed_item_is_skipped_and_the_repository_still_reads(self):
        sentinel, fake, _ = test_173.build(self, {}, repos=("r",))
        fake.issues = [test_173.issue(1, updated=20), {"number": 2, "title": None, "labels": "broken", "user": 7, "created_at": 5, "updated_at": []}, test_173.issue(3, updated=20)]
        sentinel.tick(NOW)
        self.assertTrue(sentinel.state["per_repo"]["r"].get("scanned"))
        self.assertGreaterEqual(len(sentinel.state["per_repo"]["r"]["issues"]), 2)

    def test_slim_each_counts_what_it_skips(self):
        sentinel, _fake, _ = test_173.build(self, {}, repos=("r",))
        out = sentinel._slim_each("r", "issues", [1, 0, 2], lambda x: 10 // x)
        self.assertEqual(out, [10, 5])
        self.assertIn("r:issues", sentinel.errors)
        sentinel._slim_each("r", "issues", [1], lambda x: x)
        self.assertNotIn("r:issues", sentinel.errors)

    def test_a_workflow_file_the_linter_cannot_process_is_skipped_alone(self):
        from github_actions_monitor.delivery import supply
        from github_actions_monitor.cli import lint_workflows
        real = lint_workflows.lint_text

        def lint(text, label, rules=None, *a, **k):
            if "broken" in text:
                raise ValueError("cannot parse")
            return real(text, label, rules, *a, **k)
        bad = []
        with mock.patch.object(lint_workflows, "lint_text", lint):
            found = supply.findings("r", {"a.yml": "broken", "b.yml": test_217_supply_chain.LOOSE}, None, "acme", unlintable=bad)
        self.assertEqual(bad, ["a.yml"])
        self.assertTrue(found, "the other file is still judged")


class TheCiSentinel(unittest.TestCase):
    def build(self, names):
        ctx = {"gh": lambda *a, **k: {}, "repos_fn": lambda: list(names), "runs_fn": lambda: {}, "data_fn": lambda: {"rate": {"remaining": 5000, "limit": 5000}, "active": [], "issues": []},
               "eco_fn": lambda r: "main"}
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for name in ("CACHE_FILE", "HISTORY_FILE"):
            patcher = mock.patch.object(sentinel_local, name, Path(tmp.name) / (name + ".json"))
            patcher.start()
            self.addCleanup(patcher.stop)
        sentinel = sentinel_local.Sentinel(ctx, {})
        sentinel.repo_info = {r: {"branch": "main"} for r in names}
        return sentinel

    def test_a_repository_that_raises_does_not_take_the_batch_and_is_named(self):
        sentinel = self.build(["bad", "good"])

        def fetch(repo):
            if repo == "bad":
                raise RuntimeError("boom")
            return repo, {"at": time.time(), "codeql": [], "secret": 0, "note": ""}
        self.assertTrue(sentinel._read_batch("alerts", fetch, ["bad", "good"], sentinel.alerts))
        self.assertIn("good", sentinel.alerts)
        self.assertNotIn("bad", sentinel.alerts)
        self.assertIn("alerts:bad", sentinel.errors)
        self.assertEqual(sentinel.unchecked_reads()["alerts"], ["bad"])
        sentinel._read_batch("alerts", lambda r: (r, {"at": time.time()}), ["bad"], sentinel.alerts)
        self.assertNotIn("alerts:bad", sentinel.errors)
        self.assertEqual(sentinel.unchecked_reads()["alerts"], [])

    def test_a_pass_out_of_time_starts_nothing_and_leaves_the_repositories_named(self):
        sentinel = self.build(["a", "b"])
        calls = []
        with mock.patch.object(sentinel_base, "expired", return_value=True):
            sentinel._read_batch("alerts", lambda r: calls.append(r) or (r, {"at": time.time()}), ["a", "b"], sentinel.alerts)
        self.assertEqual(calls, [])
        self.assertEqual(sentinel.unchecked_reads()["alerts"], ["a", "b"])
        self.assertEqual(sentinel.unchecked_reads()["hygiene"], ["a", "b"])

    def test_the_time_ceiling_setting_defaults_to_thirty_and_ignores_nonsense(self):
        self.assertEqual(sentinel_local.sentinel_config({})["deadline_s"], 30)
        self.assertEqual(sentinel_local.sentinel_config({"sentinel": {"deadline_s": 0}})["deadline_s"], 0)
        for bad in (-1, 601, "9", True, None, 2.5):
            self.assertEqual(sentinel_local.sentinel_config({"sentinel": {"deadline_s": bad}})["deadline_s"], 30, bad)

    def test_a_stage_that_breaks_does_not_stop_the_stages_after_it(self):
        sentinel = self.build(["a"])
        ran = []
        names = ("_org_files_tick", "_surface_tick", "_lint_remote_tick", "_a2_resolve_tick", "_workflow_marks_tick", "_upstream_tick", "_failed_jobs_tick", "_sign_probe_tick")

        def make(name):
            def stage():
                ran.append(name)
                if name == "_surface_tick":
                    raise RuntimeError("stage down")
                return False
            return stage
        for name in names:
            setattr(sentinel, name, make(name))
        sentinel.gql_at = time.time()
        sentinel._alerts_due = lambda: []
        sentinel._perms_due = lambda: []
        sentinel._tick_stages()
        self.assertEqual(ran, list(names), "every stage ran")
        self.assertIn("surface", sentinel.errors)

    def test_the_status_of_the_ci_sentinel_names_what_was_not_read(self):
        from github_actions_monitor.sentinels import sentinel_ci
        sentinel = self.build(["a", "b"])
        wrapper = sentinel_ci.SentinelCI.__new__(sentinel_ci.SentinelCI)
        wrapper.core = sentinel
        wrapper.ctx = sentinel.ctx
        wrapper.config = {}
        sentinel.last_snap = {"enabled": True, "level": "ok", "errors": [], "not_checked": {"alerts": ["a"], "hygiene": ["a", "b"]}}
        self.assertEqual(wrapper.get_status()["unchecked"], ["a", "b"])


class TheRunnersPass(unittest.TestCase):
    def test_the_repositories_the_pass_did_not_read_are_named(self):
        from github_actions_monitor.integrations import runners
        names = [f"r{i:02d}" for i in range(33)]

        def reader(endpoint):
            if "/r01/" in endpoint:
                raise RuntimeError("403")
            return {"runners": []}
        got = runners.collect({"runners": {"enabled": True, "scope": "repos"}}, reader, "acme", names)
        self.assertEqual(got["errors"], 1)
        self.assertEqual(got["unchecked"], ["r01", "r30", "r31", "r32"], "the one that failed and the ones past the thirty that are read")
        whole = runners.collect({"runners": {"enabled": True, "scope": "owner"}}, lambda endpoint: {"runners": []}, "acme", names)
        self.assertEqual(whole["unchecked"], [])


if __name__ == "__main__":
    unittest.main()
