# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The workflow linter and the workflow scan of the surface checks without a clone: the files are read through the contents API (budget, cache by SHA, reasons when a read fails) or from a sparse clone,
and the result says what was read how and what could not be evaluated. Synthetic repositories and a fake reader: no network, no `gh`."""
import base64
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import surface  # noqa: E402
from github_actions_monitor.cli import lint_workflows  # noqa: E402
from github_actions_monitor.integrations import remote_workflows as rw  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402

GOOD = "name: CI\non: [push]\npermissions:\n  contents: read\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1\n"
BAD = "name: CI\non: [push]\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n"


def setUpModule():
    from github_actions_monitor import i18n
    i18n.set_language("en")      # the sentences are judged in English whatever language an earlier test left in force
    unittest.addModuleCleanup(i18n.set_language, None)


class Api:
    """A fake of the contents API for repositories made of {path: text}; counts the calls and can fail a path."""

    def __init__(self, repos, fail=None):
        self.repos, self.fail, self.calls = repos, fail or {}, []

    def read(self, endpoint):
        self.calls.append(endpoint)
        for needle, error in self.fail.items():
            if needle in endpoint:
                raise RuntimeError(error)
        repo = endpoint.split("/")[2]
        files = self.repos[repo]
        tail = endpoint.split("/contents/.github/workflows", 1)[1]
        if tail == "":
            if not files:
                raise RuntimeError("gh: Not Found (HTTP 404)")
            return [{"name": n, "type": "file", "sha": f"sha-{abs(hash(t)) % 10**8}", "size": len(t)} for n, t in sorted(files.items())]
        return {"encoding": "base64", "content": base64.b64encode(files[tail[1:]].encode()).decode()}


def reader(api, clock=None):
    return rw.Reader(api.read, lambda: "acme", clock or (lambda: 1000.0))


class Reading(unittest.TestCase):
    def test_one_call_for_the_list_and_one_for_each_file(self):
        api = Api({"r": {"a.yml": GOOD, "b.yml": BAD}})
        r = reader(api)
        self.assertEqual(r.refresh("r", 10), 3)
        self.assertEqual(sorted(r.texts("r")), ["a.yml", "b.yml"])
        self.assertEqual(r.state("r")["state"], "ok")

    def test_a_file_whose_sha_did_not_change_is_not_read_again(self):
        api = Api({"r": {"a.yml": GOOD, "b.yml": BAD}})
        r = reader(api)
        r.refresh("r", 10)
        api.calls.clear()
        self.assertEqual(r.refresh("r", 10), 1)      # only the list
        api.repos["r"]["b.yml"] = BAD + "# changed\n"
        api.calls.clear()
        self.assertEqual(r.refresh("r", 10), 2)      # the list and the changed file
        self.assertIn("# changed", r.texts("r")["b.yml"])

    def test_the_budget_stops_the_reading_and_the_repository_stays_due(self):
        api = Api({"r": {f"w{i}.yml": GOOD + f"# {i}\n" for i in range(4)}})
        r = reader(api)
        self.assertEqual(r.refresh("r", 3), 3)      # the list and two files
        state = r.state("r")
        self.assertEqual((state["state"], state["reason"], len(state["skipped"])), ("partial", "budget", 2))
        self.assertEqual(r.due(["r"], 10**9), ["r"])      # a partial reading is due again at once
        r.refresh("r", 10)
        self.assertEqual(r.state("r")["state"], "ok")
        self.assertEqual(r.due(["r"], 10**9), [])

    def test_no_budget_means_no_call(self):
        api = Api({"r": {"a.yml": GOOD}})
        self.assertEqual(reader(api).refresh("r", 0), 0)
        self.assertEqual(api.calls, [])

    def test_a_repository_with_more_files_than_the_limit_is_read_in_part_and_says_so(self):
        api = Api({"r": {f"w{i:02}.yml": GOOD + f"# {i}\n" for i in range(5)}})
        r = reader(api)
        r.refresh("r", 50, max_files=3)
        state = r.state("r")
        self.assertEqual((state["files"], state["truncated"], state["reason"]), (3, True, "over_limit"))

    def test_a_file_that_is_too_big_is_skipped_with_its_reason(self):
        api = Api({"r": {"a.yml": GOOD}})
        original = api.read

        def big(endpoint):
            answer = original(endpoint)
            if isinstance(answer, list):
                answer[0]["size"] = rw.MAX_BYTES + 1
            return answer
        r = rw.Reader(big, lambda: "acme")
        r.refresh("r", 10)
        self.assertEqual((r.state("r")["skipped"], r.state("r")["reason"]), (["a.yml"], "too_big"))

    def test_no_workflows_folder_is_a_repository_without_workflows_not_an_error(self):
        r = reader(Api({"r": {}}))
        r.refresh("r", 5)
        self.assertEqual((r.state("r")["state"], r.texts("r")), ("ok", {}))

    def test_a_failed_read_says_why(self):
        for message, reason in (("gh: Resource protected by organization SAML enforcement. You must grant your Personal Access token access to this organization. (HTTP 403)", "sso"),
                                ("gh: API rate limit exceeded for user ID 1. (HTTP 403)", "rate_limited"), ("gh: Bad credentials (HTTP 401)", "auth"),
                                ("gh: Resource not accessible by personal access token (HTTP 403)", "forbidden"), ("something odd", "error")):
            r = reader(Api({"r": {"a.yml": GOOD}}, fail={"/contents/.github/workflows": message}))
            r.refresh("r", 5)
            self.assertEqual((r.state("r")["state"], r.state("r")["reason"]), ("not_evaluable", reason), message)

    def test_a_failure_does_not_throw_away_what_was_read_before(self):
        api = Api({"r": {"a.yml": BAD}})
        r = reader(api)
        r.refresh("r", 5)
        api.fail["/contents/.github/workflows"] = "gh: Bad credentials (HTTP 401)"
        r.refresh("r", 5)
        self.assertEqual(r.state("r")["state"], "not_evaluable")
        self.assertIn("a.yml", r.texts("r"))

    def test_a_name_that_is_not_a_repository_is_never_asked(self):
        api = Api({})
        self.assertEqual(reader(api).refresh("../x", 5), 0)
        self.assertEqual(api.calls, [])

    def test_due_orders_the_oldest_first_and_skips_the_fresh(self):
        now = [1000.0]
        api = Api({"a": {"x.yml": GOOD}, "b": {"x.yml": GOOD}})
        r = reader(api, lambda: now[0])
        r.refresh("a", 5)
        now[0] = 1500.0
        r.refresh("b", 5)
        now[0] = 1600.0
        self.assertEqual(r.due(["a", "b", "c"], 3600), ["c"])
        now[0] = 6000.0
        self.assertEqual(r.due(["a", "b", "c"], 3600), ["c", "a", "b"])


class Linting(unittest.TestCase):
    def test_the_rules_run_over_what_was_read_and_the_file_is_named_like_a_clone_would(self):
        api = Api({"r": {"a.yml": GOOD, "b.yml": BAD}, "ok": {"a.yml": GOOD}})
        r = reader(api)
        for repo in ("r", "ok"):
            r.refresh(repo, 10)
        found = lint_workflows.lint_remote(r, ["r", "ok"])
        self.assertEqual(sorted(found), ["r"])
        self.assertEqual({(f["file"], f["rule"]) for f in found["r"]}, {(".github/workflows/b.yml", "unpinned_uses"), (".github/workflows/b.yml", "permissions")})

    def test_the_ignore_patterns_apply(self):
        r = reader(Api({"r": {"b.yml": BAD}}))
        r.refresh("r", 10)
        self.assertEqual(lint_workflows.lint_remote(r, ["r"], ignore=["r:b.yml:*"]), {})
        self.assertTrue(lint_workflows.lint_remote(r, ["r"], ignore=["other:b.yml:*"]))

    def test_the_command_line_reads_a_repository_without_a_clone(self):
        api = Api({"r": {"b.yml": BAD}})
        found = lint_workflows.lint_remote_name("acme/r", api.read)
        self.assertEqual({f["rule"] for f in found}, {"unpinned_uses", "permissions"})

    def test_the_command_line_says_why_a_repository_cannot_be_read(self):
        api = Api({"r": {"b.yml": BAD}}, fail={"/contents/": "gh: Resource protected by organization SAML enforcement (HTTP 403)"})
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            self.assertEqual(lint_workflows.lint_remote_name("acme/r", api.read), [])
            self.assertEqual(lint_workflows.lint_remote_name("not a name", api.read), [])
        self.assertIn("SSO", error.getvalue())
        self.assertIn("OWNER/REPO", error.getvalue())


class Settings(unittest.TestCase):
    def test_the_defaults_are_conservative(self):
        cfg = lint_workflows.settings({})
        self.assertEqual(cfg["source"], "clone")
        self.assertEqual((cfg["api"]["max_calls_per_tick"], cfg["api"]["max_files_per_repo"], cfg["sparse"]["max_repos_per_tick"]), (20, 40, 2))

    def test_values_out_of_range_or_of_the_wrong_kind_are_ignored(self):
        cfg = lint_workflows.settings({"lint": {"source": "everything", "api": {"max_calls_per_tick": 5000, "max_files_per_repo": True, "refresh_seconds": 700}, "sparse": {"max_repos_per_tick": "3"}}})
        self.assertEqual(cfg["source"], "clone")
        self.assertEqual((cfg["api"]["max_calls_per_tick"], cfg["api"]["max_files_per_repo"], cfg["api"]["refresh_seconds"], cfg["sparse"]["max_repos_per_tick"]), (20, 40, 700, 2))
        self.assertEqual(lint_workflows.settings({"lint": {"source": "auto"}})["source"], "auto")


class Coverage(unittest.TestCase):
    def setUp(self):
        self.api = Api({"read": {"a.yml": GOOD}, "partial": {f"w{i}.yml": GOOD + f"# {i}\n" for i in range(3)}, "denied": {"a.yml": GOOD}})
        self.api.fail["denied/contents"] = "gh: Resource protected by organization SAML enforcement (HTTP 403)"
        self.reader = reader(self.api)

    def test_it_counts_what_was_read_how_and_names_what_could_not_be_evaluated(self):
        self.reader.refresh("read", 10)
        self.reader.refresh("partial", 2)
        self.reader.refresh("denied", 10)
        cov = rw.coverage(self.reader, ["cloned", "sparse", "read", "partial", "denied", "later"], ["cloned"], ["sparse"], "auto")
        self.assertEqual((cov["clone"], cov["sparse"], cov["api"], cov["partial"], cov["waiting"], cov["not_evaluable_total"]), (1, 1, 2, 1, 1, 1))
        self.assertEqual(cov["not_evaluable"], [{"repo": "denied", "reason": "sso"}])
        self.assertEqual(cov["by_reason"], {"sso": 1})
        self.assertIn("dependabot_yml", cov["api_cannot"])

    def test_in_clone_mode_a_repository_without_a_clone_is_not_evaluable_not_silent(self):
        cov = rw.coverage(self.reader, ["cloned", "other"], ["cloned"], [], "clone")
        self.assertEqual(cov["not_evaluable"], [{"repo": "other", "reason": "no_clone"}])
        self.assertEqual(cov["api_cannot"], [])

    def test_the_sentence_is_empty_when_everything_comes_from_clones(self):
        cov = rw.coverage(self.reader, ["cloned"], ["cloned"], [], "clone")
        self.assertEqual(rw.coverage_text(cov, i18n.t), "")

    def test_the_sentence_names_the_numbers_and_the_reasons_in_every_language(self):
        self.reader.refresh("read", 10)
        self.reader.refresh("denied", 10)
        cov = rw.coverage(self.reader, ["read", "denied", "later"], [], [], "auto")
        english = rw.coverage_text(cov, i18n.t)
        for needle in ("1 through the GitHub API", "Not evaluable: 1", "SSO", "1 waiting"):
            self.assertIn(needle, english)
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                text = rw.coverage_text(cov, i18n.t)
            self.assertTrue(text and "{" not in text and "ui.a13" not in text and "lint.reason" not in text, lang)


class Surface(unittest.TestCase):
    def test_the_scan_of_the_text_has_the_shape_of_a_clone_scan_and_names_what_it_cannot_say(self):
        scan = surface.scan_remote({"ci.yml": BAD, "cron.yml": "on:\n  schedule:\n    - cron: '0 3 * * *'\njobs: {}\n"})
        self.assertEqual([w["file"] for w in scan["workflows"]], ["ci.yml", "cron.yml"])
        self.assertEqual(scan["workflows"][0]["unpinned"], ["actions/checkout@v4"])
        self.assertEqual(scan["workflows"][1]["cron"], ["0 3 * * *"])
        self.assertEqual((scan["stacks"], scan["manifest"], scan["source"]), ([], None, "api"))
        self.assertIn("manifest", scan["not_evaluable"])

    def test_a_clone_wins_over_a_reading_through_the_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector = surface.Collector(lambda *a, **k: None, tmp, surface.settings({}))
            collector.set_remote("r", surface.scan_remote({"ci.yml": BAD}))
            self.assertEqual(collector.scans["r"]["source"], "api")
            clone = Path(tmp) / "r"
            (clone / ".git").mkdir(parents=True)
            (clone / ".github" / "workflows").mkdir(parents=True)
            (clone / ".github" / "workflows" / "ci.yml").write_text(GOOD, encoding="utf-8")
            collector.scan_local(["r"])
            self.assertNotIn("source", collector.scans["r"])
            collector.set_remote("r", surface.scan_remote({"ci.yml": BAD}))
            self.assertNotIn("source", collector.scans["r"])      # a late reading does not replace the clone
            collector.set_remote("r", None)
            self.assertIn("r", collector.scans)

    def test_the_checks_that_need_a_clone_do_not_guess_from_a_scan_without_one(self):
        now = surface.parse_time("2026-11-06T00:00:00Z")
        inp = {"now": now, "cfg": surface.settings({}), "repos": ["r"], "eco": {"r": "main"}, "repo_info": {"r": {}}, "alerts": {}, "runs": {"r": []}, "scans": {"r": surface.scan_remote({"ci.yml": BAD})}}
        built = surface.build(inp)
        rows = {s["key"]: s for s in built["sections"]}
        self.assertEqual(rows["unpinned_uses"]["rows"][0][:3], ["r", "ci.yml", "actions/checkout@v4"])
        self.assertEqual(rows["coverage"]["rows"], [])      # no "missing dependabot.yml or CodeQL" from a scan that cannot know the stacks


class Sparse(unittest.TestCase):
    def test_the_commands_bring_only_the_github_folder_with_depth_one(self):
        first = rw.sparse_commands("acme", "r", "/data/sparse/r", False)
        self.assertEqual(first[0][:5], ["gh", "repo", "clone", "acme/r", "/data/sparse/r"])
        self.assertIn("--depth", first[0])
        self.assertIn("--filter=blob:none", first[0])
        self.assertEqual(first[1], ["git", "-C", "/data/sparse/r", "sparse-checkout", "set", ".github"])
        again = rw.sparse_commands("acme", "r", "/data/sparse/r", True)
        self.assertEqual([c[3] for c in again], ["fetch", "reset"])

    def test_a_failing_command_stops_the_refresh_and_gives_its_reason(self):
        seen = []

        def runner(args, timeout=180):
            seen.append(args)
            return (1, "", "gh: Resource protected by organization SAML enforcement (HTTP 403)") if args[0] == "gh" else (0, "", "")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(rw.sparse_refresh("acme", "r", tmp, runner), (False, "sso"))
            self.assertEqual(len(seen), 1)
            self.assertEqual(rw.sparse_refresh("acme", "../x", tmp, runner), (False, "error"))
            self.assertEqual(rw.sparse_refresh("acme", "r", tmp, lambda a, t=180: (0, "", "")), (True, ""))


class InTheSentinel(unittest.TestCase):
    """The tick reads the files of the repositories without a clone, inside the budget, and the picture says how."""

    def make(self, tmp, fake, source="auto", rate=4000, **lint):
        ctx = {"gh": lambda *a, **k: fake.read(a[1]), "repos_fn": lambda: ["r1", "r2"], "runs_fn": lambda: {}, "data_fn": lambda: {"rate": {"remaining": rate, "limit": 5000}, "active": [], "issues": []},
               "eco_fn": lambda r: "main"}
        config = {"sentinel": {}, "lint": dict({"source": source}, **lint)}
        with mock.patch.object(sl, "CACHE_FILE", Path(tmp) / "c.json"), mock.patch.object(sl, "HISTORY_FILE", Path(tmp) / "h.json"), mock.patch.object(sl, "GITHUB_DIR", Path(tmp) / "none"):
            s = sl.Sentinel(ctx, config)
        s.repo_info = {"r1": {"branch": "main"}, "r2": {"branch": "main"}}
        return s

    def test_the_lint_and_the_surface_scan_use_the_same_reading(self):
        api = Api({"r1": {"b.yml": BAD}, "r2": {"a.yml": GOOD}})
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sl.workspace, "has_workspace", return_value=False):
            s = self.make(tmp, api)
            self.assertTrue(s._lint_remote_tick())
            lint = s._lint(["r1", "r2"])
            self.assertEqual(list(lint["by_repo"]), ["r1"])
            self.assertEqual((lint["coverage"]["api"], lint["coverage"]["waiting"]), (2, 0))
            self.assertEqual(s.surface.scans["r1"]["workflows"][0]["unpinned"], ["actions/checkout@v4"])

    def test_the_default_source_makes_no_call(self):
        api = Api({"r1": {"b.yml": BAD}})
        with tempfile.TemporaryDirectory() as tmp:
            s = self.make(tmp, api, source="clone")
            self.assertFalse(s._lint_remote_tick())
            self.assertEqual(api.calls, [])

    def test_a_low_allowance_pauses_the_reading_and_the_repositories_show_as_waiting(self):
        api = Api({"r1": {"b.yml": BAD}, "r2": {"a.yml": GOOD}})
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sl.workspace, "has_workspace", return_value=False):
            s = self.make(tmp, api, rate=10)
            self.assertFalse(s._lint_remote_tick())
            self.assertEqual(api.calls, [])
            self.assertEqual(s._lint(["r1", "r2"])["coverage"]["waiting"], 2)

    def test_the_calls_of_a_tick_are_limited(self):
        api = Api({"r1": {"a.yml": GOOD, "b.yml": BAD}, "r2": {"a.yml": GOOD}})
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sl.workspace, "has_workspace", return_value=False):
            s = self.make(tmp, api, **{"api": {"max_calls_per_tick": 2}})
            s._lint_remote_tick()
            self.assertLessEqual(len(api.calls), 2)
            self.assertEqual(s._lint(["r1", "r2"])["coverage"]["partial"], 1)

    def test_the_panel_carries_the_coverage_sentence(self):
        from github_actions_monitor.sentinels import sentinel_panels
        snapshot = {"lint": {"enabled": True, "summary": {"findings": 0, "repos": 0, "bad": 0, "warn": 0, "info": 0}, "rows": [],
                             "coverage": {"clone": 0, "sparse": 0, "api": 0, "partial": 0, "waiting": 0, "not_evaluable_total": 3, "by_reason": {"no_clone": 3}, "api_cannot": []}}}
        panel = next(p for p in sentinel_panels.panels(snapshot, i18n.t) if p["id"] == "a13")
        self.assertIn("Not evaluable: 3", panel["summary"])


if __name__ == "__main__":
    unittest.main()
