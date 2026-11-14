# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The four optional reports, all off by default: workflow hygiene read from GitHub, the wait of jobs for each kind of runner, the view of which repositories are ready for a release or blocked, and the
supply chain of the latest release. Pure analysers, a cycle that spends at most `reports.max_calls_per_cycle` calls, an endpoint and a block of the page."""
import base64
import json
import sys
import unittest
from pathlib import Path

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am, settings_api  # noqa: E402
from github_actions_monitor.integrations import reports  # noqa: E402

WORKFLOW = """name: ci
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - run: echo hi
  call:
    uses: o/r/.github/workflows/x.yml@main
"""
ON = {"reports": {"workflow_hygiene": {"enabled": True}, "queue": {"enabled": True}, "release_view": {"enabled": True}, "supply_chain": {"enabled": True}, "max_calls_per_cycle": 10}}


class Reset(unittest.TestCase):
    def setUp(self):
        reports.reset()
        self.addCleanup(reports.reset)


class TheSettings(Reset):
    def test_everything_is_off_by_default(self):
        cfg = reports.settings({})
        self.assertEqual([cfg[k] for k in reports.KINDS], [False] * 4)
        self.assertEqual(cfg["max_calls_per_cycle"], 4)
        self.assertEqual(reports.settings({"reports": {"queue": {"enabled": "yes"}, "max_calls_per_cycle": 0}})["queue"], False)
        self.assertEqual(reports.settings({"reports": {"max_calls_per_cycle": 999}})["max_calls_per_cycle"], 4)
        self.assertEqual(am.DEFAULTS["reports"]["supply_chain"], {"enabled": False})

    def test_the_settings_and_their_texts_exist_in_eight_languages(self):
        for key in ("reports.workflow_hygiene.enabled", "reports.queue.enabled", "reports.release_view.enabled", "reports.supply_chain.enabled", "reports.max_calls_per_cycle"):
            self.assertIn(key, settings_api.FIELDS)
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, "cfg.f." + key), "cfg.f." + key, (lang, key))
                self.assertNotEqual(i18n.tl(lang, "cfg.h." + key), "cfg.h." + key, (lang, key))
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            keys = ["ui.cfg_b_reports", "ui.rep_title", "ui.rep_none", "ui.rep_wait", "ui.rep_ready", "ui.rep_blocked", "ui.rep_sums", "ui.rep_sig", *[f"ui.rep_{k}" for k in reports.KINDS],
                    "ui.rep_r_ci_red", "ui.rep_r_signature_waiting", *[f"ui.rep_rule_{r}" for r in ("no_timeout", "no_concurrency", "unpinned_uses", "permissions", "secrets_in_clear", "injection", "pr_target")]]
            for key in keys:
                self.assertTrue(catalogue.get(key), (lang, key))


class WorkflowHygiene(Reset):
    def test_a_job_without_a_limit_and_a_workflow_without_concurrency_are_found(self):
        found = reports.hygiene_findings(WORKFLOW, "ci.yml")
        rules = {(f["rule"], f["detail"]) for f in found}
        self.assertIn(("no_timeout", "test"), rules)
        self.assertNotIn(("no_timeout", "build"), rules)
        self.assertFalse([f for f in found if f["rule"] == "no_timeout" and f["detail"] == "call"], "a call of a reusable workflow has no steps of its own")
        self.assertIn("no_concurrency", {f["rule"] for f in found})
        self.assertIn("unpinned_uses", {f["rule"] for f in found})

    def test_a_clean_file_has_only_what_it_lacks(self):
        clean = "name: x\nconcurrency:\n  group: a\npermissions:\n  contents: read\njobs:\n  a:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps:\n      - run: echo\n"
        self.assertEqual([f["rule"] for f in reports.hygiene_findings(clean)], [])


class TheQueue(Reset):
    def test_runners_are_grouped_by_their_labels(self):
        for labels, group in ((["ubuntu-latest"], "linux"), (["windows-2022"], "windows"), (["macos-15"], "macos"), (["self-hosted", "linux"], "self-hosted"), (["ubuntu-latest-4-core"], "larger"),
                              (["macos-15-large"], "larger"), ([], "other")):
            self.assertEqual(reports.runner_group(labels), group, labels)

    def test_the_wait_of_each_job_comes_from_its_created_and_started_times(self):
        body = {"jobs": [{"labels": ["macos-15"], "created_at": "2026-11-14T10:00:00Z", "started_at": "2026-11-14T10:02:00Z"},
                         {"labels": ["ubuntu-latest"], "created_at": "2026-11-14T10:00:00Z", "started_at": "2026-11-14T10:00:05Z"}, {"labels": ["x"], "created_at": None}]}
        stats = reports.queue_stats(reports.job_waits(body))
        self.assertEqual(stats["macos"], {"jobs": 1, "median": 120, "max": 120})
        self.assertEqual(stats["linux"]["median"], 5)


class ReleaseView(Reset):
    def test_ready_and_blocked_with_their_reasons(self):
        snapshot = {"a5": {"candidates": [{"repo": "one", "entries": 7}, {"repo": "two", "entries": 6}], "pending_sign": [{"repo": "two", "hours": 30}], "green_unreleased": [{"repo": "three"}]},
                    "a2": {"red": [{"repo": "one", "workflow": "ci"}]}}
        rows = {r["repo"]: r for r in reports.release_view(snapshot)}
        self.assertEqual((rows["one"]["state"], rows["one"]["reasons"], rows["one"]["entries"]), ("blocked", ["ci_red"], 7))
        self.assertEqual(rows["two"]["reasons"], ["signature_waiting"])
        self.assertEqual((rows["three"]["state"], rows["three"]["reasons"]), ("ready", []))
        self.assertEqual(reports.release_view({})[:0], [])
        self.assertEqual(reports.release_view(None), [])
        self.assertEqual([r["state"] for r in reports.release_view(snapshot)][0], "blocked", "the blocked ones first")


class SupplyChain(Reset):
    def test_assets_are_classified_by_name_only(self):
        self.assertEqual(reports.asset_class(["app.zip", "sbom.spdx.json", "SHA256SUMS", "app.zip.sig"]), {"sbom": True, "checksums": True, "signature": True})
        self.assertEqual(reports.asset_class(["app.zip"]), {"sbom": False, "checksums": False, "signature": False})
        self.assertTrue(reports.asset_class(["x.intoto.jsonl"])["signature"])
        self.assertEqual(reports.asset_class(None), {"sbom": False, "checksums": False, "signature": False})


class TheCycle(Reset):
    def make_read(self, calls):
        def read(endpoint):
            calls.append(endpoint)
            if endpoint.endswith("/contents/.github/workflows"):
                return [{"name": "ci.yml"}, {"name": "notes.txt"}, {"name": "../evil.yml"}]
            if "/contents/.github/workflows/ci.yml" in endpoint:
                return {"encoding": "base64", "content": base64.b64encode(WORKFLOW.encode()).decode()}
            if endpoint.endswith("/releases/latest"):
                return {"tag_name": "v1", "assets": [{"name": "a.zip"}, {"name": "SHA256SUMS"}]}
            if endpoint.endswith("/jobs?per_page=100"):
                return {"jobs": [{"labels": ["windows-2022"], "created_at": "2026-11-14T10:00:00Z", "started_at": "2026-11-14T10:01:00Z"}]}
            raise AssertionError(endpoint)
        return read

    def test_it_reads_nothing_while_everything_is_off(self):
        calls = []
        self.assertEqual(reports.cycle({}, "o", ["a"], [{"id": 1, "repo": "a", "status": "completed", "queued": 99}], self.make_read(calls)), 0)
        self.assertEqual(calls, [])

    def test_it_spends_at_most_the_calls_it_is_given(self):
        calls = []
        config = {"reports": {**ON["reports"], "max_calls_per_cycle": 3}}
        runs = [{"id": i, "repo": "a", "status": "completed", "queued": 60} for i in range(1, 6)]
        spent = reports.cycle(config, "o", ["a", "b"], runs, self.make_read(calls))
        self.assertEqual((spent, len(calls)), (3, 3))
        self.assertEqual(len(reports.STATE["queue_seen"]), 3)

    def test_the_hygiene_and_the_supply_chain_read_one_repository_at_a_time_and_only_once_a_day(self):
        calls = []
        config = {"reports": {"workflow_hygiene": {"enabled": True}, "supply_chain": {"enabled": True}, "max_calls_per_cycle": 10}}
        reports.cycle(config, "o", ["a", "b"], [], self.make_read(calls), now=1000.0)
        self.assertEqual(sorted(reports.STATE["hygiene"]), ["a"])
        self.assertEqual(reports.STATE["supply"]["a"]["checksums"], True)
        self.assertTrue(any(f["rule"] == "no_timeout" for f in reports.STATE["hygiene"]["a"]["findings"]))
        self.assertNotIn("../evil.yml", " ".join(calls))
        reports.cycle(config, "o", ["a", "b"], [], self.make_read(calls), now=1100.0)
        self.assertEqual(sorted(reports.STATE["hygiene"]), ["a", "b"], "the next repository, not the same one again")
        before = len(calls)
        reports.cycle(config, "o", ["a", "b"], [], self.make_read(calls), now=1200.0)
        self.assertEqual(len(calls), before, "both were read less than a day ago")

    def test_an_error_of_the_api_never_raises(self):
        def boom(endpoint):
            raise RuntimeError("HTTP 500")
        reports.cycle(ON, "o", ["a"], [{"id": 1, "repo": "a", "status": "completed", "queued": 99}], boom)

    def test_a_name_that_is_not_plain_is_never_asked(self):
        calls = []
        reports.cycle(ON, "o", ["../x", "bad name"], [], self.make_read(calls))
        self.assertEqual(calls, [])


class TheEndpointAndThePage(Reset):
    def test_the_payload_says_what_is_on_and_what_is_known(self):
        off = reports.payload({})
        self.assertEqual([off[k]["enabled"] for k in reports.KINDS], [False] * 4)
        calls = []
        TheCycle().make_read(calls)
        reports.STATE["supply"]["a"] = {"at": 1, "tag": "v1", "sbom": False, "checksums": True, "signature": False}
        reports.STATE["queue"] = [{"group": "macos", "wait": 90}]
        got = reports.payload(ON, {"a5": {"candidates": [{"repo": "a", "entries": 5}]}})
        self.assertEqual(got["supply_chain"]["repos"][0]["tag"], "v1")
        self.assertEqual(got["queue"]["groups"]["macos"]["median"], 90)
        self.assertEqual(got["release_view"]["repos"][0]["state"], "ready")
        json.dumps(got)

    def test_the_route_answers_and_the_page_draws_the_block(self):
        from test_164 import LiveServer
        with LiveServer({"session_guard": True}) as server:
            status, body = server.call("/api/reports")
            self.assertEqual(status, 200)
            self.assertFalse(body["queue"]["enabled"])
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        for needle in ('id="rep-box"', "function renderReports", "/api/reports"):
            self.assertIn(needle, page)

    def test_the_module_only_reads(self):
        text = (HERE / "src" / "github_actions_monitor" / "integrations" / "reports.py").read_text(encoding="utf-8")
        for forbidden in ("urllib", "subprocess", '"POST"', "method=", "write_text", "os.system"):
            self.assertNotIn(forbidden, text, forbidden)


if __name__ == "__main__":
    unittest.main()
