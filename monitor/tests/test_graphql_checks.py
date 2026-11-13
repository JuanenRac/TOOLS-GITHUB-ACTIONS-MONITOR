# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Reading the workflows of cold repositories through GraphQL (network.graphql_checks, OFF by default): the query, the reading of the answer, the batches, the fall back to REST and the
accounting. GitHub is simulated: no network, no `gh`."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import graphql_checks as gc  # noqa: E402
from github_actions_monitor.data_pipeline import signals  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")


def suite(conclusion="SUCCESS", status="COMPLETED", run_id=11, name="CI", path="/o/r/actions/workflows/ci.yml", app=False):
    return {"conclusion": conclusion, "status": status, "createdAt": "2026-01-01T10:00:00Z",
            "workflowRun": None if app else {"event": "PUSH", "runNumber": 7, "databaseId": run_id, "url": f"https://github.com/o/r/actions/runs/{run_id}", "workflow": {"name": name, "resourcePath": path}}}


def repo_node(*suites, branch="main", oid="abcdef1234567"):
    return {"defaultBranchRef": {"name": branch, "target": {"oid": oid, "checkSuites": {"nodes": list(suites)}}}}


class Reading(unittest.TestCase):
    def setUp(self):
        for key in gc.STATS:
            gc.STATS[key] = 0

    def test_it_is_off_unless_the_switch_is_true(self):
        self.assertEqual(gc.settings({}), {"enabled": False, "batch": 20})
        self.assertEqual(gc.settings({"network": {"graphql_checks": "yes"}})["enabled"], False)
        self.assertEqual(gc.settings({"network": {"graphql_checks": True, "graphql_batch": 5}}), {"enabled": True, "batch": 5})
        self.assertEqual(gc.settings({"network": {"graphql_checks": True, "graphql_batch": 99}})["batch"], 20)
        self.assertEqual(gc.settings({"network": {"graphql_checks": True, "graphql_batch": True}})["batch"], 20)
        self.assertEqual(am.DEFAULTS["network"]["graphql_checks"], False)

    def test_the_query_has_an_alias_per_repository_and_never_a_strange_name(self):
        text = gc.query("owner-1", ["alpha", "beta"])
        self.assertIn('r0: repository(owner: "owner-1", name: "alpha")', text)
        self.assertIn('r1: repository(owner: "owner-1", name: "beta")', text)
        self.assertIn("rateLimit { cost remaining }", text)
        self.assertNotIn("bad", gc.query("o", ['bad"name', "good"]))
        with self.assertRaises(ValueError):
            gc.query('o"wner', ["x"])

    def test_the_answer_becomes_the_runs_the_rest_of_the_monitor_reads(self):
        answer = {"data": {"r0": repo_node(suite("FAILURE", run_id=1, name="CI"), suite("SUCCESS", run_id=2, name="Lint", path="/o/r/actions/workflows/lint.yml"), suite(app=True)),
                           "r1": None, "rateLimit": {"cost": 1, "remaining": 4999}}}
        got = gc.parse(answer, ["alpha", "beta"])
        self.assertEqual(sorted(got), ["alpha"])      # beta came back null: REST reads it
        runs = got["alpha"]
        self.assertEqual([r["name"] for r in runs], ["CI", "Lint"])      # the suite of an app that is not a workflow is left out
        first = runs[0]
        self.assertEqual((first["status"], first["conclusion"], first["branch"], first["sha"], first["path"], first["event"]), ("completed", "failure", "main", "abcdef1", "ci.yml", "push"))
        self.assertEqual(set(first), {"repo", "id", "name", "title", "event", "branch", "path", "sha", "actor", "status", "number", "queued", "conclusion", "started", "seconds", "url", "attempt"})
        pending = gc.parse({"data": {"r0": repo_node(suite(None, "IN_PROGRESS"))}}, ["alpha"])["alpha"][0]
        self.assertEqual((pending["status"], pending["conclusion"]), ("in_progress", None))
        self.assertEqual(gc.parse(None, ["a"]), {})
        self.assertEqual(gc.parse({"errors": [{"message": "x"}]}, ["a"]), {})

    def test_batches_failures_and_the_accounting(self):
        seen = []

        def call(text):
            seen.append(text)
            if "name: \"boom\"" in text:
                raise RuntimeError("HTTP 502")
            return {"data": {"r0": repo_node(suite()), "r1": None, "rateLimit": {"cost": 2, "remaining": 4990}}}
        found, rest = gc.read_batches("o", ["one", "two", "boom", "bad name"], 2, call)
        self.assertEqual(len(seen), 2)      # two batches of two; the odd name never goes into a query
        self.assertEqual(sorted(found), ["one"])
        self.assertEqual(sorted(rest), ["bad name", "boom", "two"])      # nothing is lost: REST reads them
        self.assertEqual(gc.stats(), {"calls": 1, "repos": 1, "fallbacks": 2, "cost": 2, "errors": 1})

    def test_the_stats_are_hidden_while_the_feature_is_off_and_unused(self):
        self.assertIsNone(gc.stats({}))
        self.assertEqual(gc.stats({"network": {"graphql_checks": True}})["calls"], 0)


class InTheCycle(unittest.TestCase):
    def setUp(self):
        am.RUN_CACHE.clear()
        am.HOT_ONLY.update({"on": False, "until": 0.0})
        for key in gc.STATS:
            gc.STATS[key] = 0
        self.config = dict(am.DEFAULTS)
        self.config["network"] = {**am.DEFAULTS["network"], "graphql_checks": True}
        self.rest = []
        self.graph = []
        self.orig = am.fetch_runs
        am.fetch_runs = lambda repo, per_page: (self.rest.append(repo) or [], None)

    def tearDown(self):
        am.fetch_runs = self.orig
        am.RUN_CACHE.clear()

    def gh(self, *args, **kwargs):
        self.assertEqual(args[:2], ("api", "graphql"))
        self.assertTrue(kwargs.get("as_user"))      # GraphQL is asked with the login of the user (its own allowance)
        self.graph.append(args[3])
        return {"data": {"r0": repo_node(suite("FAILURE", run_id=5)), "r1": None, "rateLimit": {"cost": 1, "remaining": 4999}}}

    def prime(self):
        am.RUN_CACHE["cold-a"] = {"runs": [], "at": 0.0, "error": None, "fails": 0}
        am.RUN_CACHE["cold-b"] = {"runs": [], "at": 0.0, "error": None, "fails": 0}
        am.RUN_CACHE["hot-c"] = {"runs": [{"repo": "hot-c", "id": 1, "status": "in_progress", "conclusion": None}], "at": 0.0, "error": None, "fails": 0}

    def test_cold_repositories_go_in_a_batch_the_hot_one_and_the_unanswered_go_by_rest(self):
        self.prime()
        with mock.patch.object(am, "gh", self.gh):
            total = am.refresh_runs(["cold-a", "cold-b", "hot-c"], self.config)
        self.assertEqual(total, 3)
        self.assertEqual(len(self.graph), 1)      # ONE call for the two cold repositories
        self.assertEqual(sorted(self.rest), ["cold-b", "hot-c"])      # the hot one, and the one GraphQL did not answer
        self.assertEqual(am.RUN_CACHE["cold-a"]["runs"][0]["conclusion"], "failure")
        self.assertIsNone(am.RUN_CACHE["cold-a"]["error"])

    def test_with_the_switch_off_nothing_goes_to_graphql(self):
        self.prime()
        self.config["network"] = {**am.DEFAULTS["network"], "graphql_checks": False}
        with mock.patch.object(am, "gh", self.gh):
            am.refresh_runs(["cold-a", "cold-b", "hot-c"], self.config)
        self.assertEqual(self.graph, [])
        self.assertEqual(sorted(self.rest), ["cold-a", "cold-b", "hot-c"])

    def test_a_graphql_failure_sends_everything_to_rest(self):
        self.prime()

        def broken(*args, **kwargs):
            raise RuntimeError("HTTP 403 rate limit exceeded")
        with mock.patch.object(am, "gh", broken):
            am.refresh_runs(["cold-a", "cold-b", "hot-c"], self.config)
        self.assertEqual(sorted(self.rest), ["cold-a", "cold-b", "hot-c"])
        self.assertEqual(gc.STATS["errors"], 1)


class Shown(unittest.TestCase):
    def test_the_accounting_reaches_the_brief_and_the_settings_exist_in_eight_languages(self):
        data = {"etag": {"calls": 10, "saved": 4}, "graphql": {"calls": 2, "repos": 30, "cost": 2, "fallbacks": 1}, "rate": {"remaining": 4000, "limit": 5000, "reset": "x"}}
        text = json.dumps(signals.inventory(data))
        self.assertIn("GraphQL: 2 batch(es) read 30 repositories for 2 point(s), 1 went to REST", text)
        self.assertIn("network.graphql_checks", settings_api.META)
        self.assertIn("network.graphql_batch", settings_api.META)
        for lang in LANGS:
            texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("cfg.f.network.graphql_checks", "cfg.h.network.graphql_checks", "cfg.f.network.graphql_batch", "cfg.h.network.graphql_batch"):
                self.assertTrue(texts.get(key), (lang, key))
            self.assertIn("QUOTA.md", texts["cfg.h.network.graphql_checks"])


if __name__ == "__main__":
    unittest.main()
