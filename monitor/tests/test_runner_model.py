# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The model of the runners: the kinds told from the labels of the jobs, the queue and the cost by kind, the workflows that fire themselves, the self-hosted queues with nobody to take them, the
alerts, the settings and the wiring (no network: the reads of GitHub are replaced)."""
import inspect
import re
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am, settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import quota  # noqa: E402
from github_actions_monitor.integrations import runner_model as rm  # noqa: E402
from github_actions_monitor.security import auth  # noqa: E402

NOW = 1_800_000_000.0
ON = {"runners": {"model": {"enabled": True}}}
CFG = rm.settings(ON)


def iso(ago):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - ago))


def job(labels, status="queued", ago=0, repo="a", run=1, seconds=None):
    return {"repo": repo, "run": run, "name": "j", "status": status, "labels": labels, "created": iso(ago), "started": None, "runner": "", **({"seconds": seconds} if seconds is not None else {})}


class Kinds(unittest.TestCase):
    def test_the_five_kinds_from_the_labels(self):
        kind = lambda *labels: rm.kind_of(list(labels), CFG)      # noqa: E731
        self.assertEqual(kind("ubuntu-latest"), "hosted")
        self.assertEqual(kind("windows-2022"), "hosted")
        self.assertEqual(kind("macos-14"), "hosted")
        self.assertEqual(kind("ubuntu-latest-8-cores"), "large")
        self.assertEqual(kind("macos-latest-xlarge"), "large")
        self.assertEqual(kind("macos-14-large"), "large")
        self.assertEqual(kind("self-hosted", "linux", "x64"), "selfhosted")
        self.assertEqual(kind("blacksmith-4vcpu-ubuntu-2204"), "thirdparty")
        self.assertEqual(kind("runs-on=123/runner=2cpu-linux-x64"), "thirdparty")
        self.assertEqual(kind("namespace-profile-big"), "thirdparty")
        self.assertEqual(rm.kind_of([], CFG), "unknown")
        self.assertEqual(kind("my-farm"), "unknown")

    def test_the_taxonomy_is_configurable_and_case_does_not_matter(self):
        cfg = rm.settings({"runners": {"model": {"enabled": True, "large_labels": ["my-big-*"], "self_labels": ["lab-farm"], "thirdparty_labels": ["acme"]}}})
        self.assertEqual(rm.kind_of(["My-Big-Linux"], cfg), "large")
        self.assertEqual(rm.kind_of(["lab-farm"], cfg), "selfhosted")
        self.assertEqual(rm.kind_of(["acme-fast"], cfg), "thirdparty")
        self.assertEqual(rm.kind_of(["blacksmith-4vcpu-ubuntu-2204"], cfg), "unknown")      # the list was replaced: the old names are no longer known
        self.assertEqual(rm.kind_of(["SELF-HOSTED"], CFG), "selfhosted")

    def test_self_hosted_wins_over_everything_else(self):
        self.assertEqual(rm.kind_of(["self-hosted", "ubuntu-latest-8-cores"], CFG), "selfhosted")


class Settings(unittest.TestCase):
    def test_defaults_are_conservative(self):
        cfg = rm.settings({})
        self.assertFalse(cfg["enabled"])
        self.assertEqual((cfg["jobs_per_cycle"], cfg["queue_warn_minutes"], cfg["runaway_runs_per_hour"], cfg["alert_level"], cfg["thirdparty_usd_per_minute"]), (10, 20, 20, "warning", 0.0))
        self.assertFalse(am.DEFAULTS["runners"]["model"]["enabled"])
        self.assertEqual(rm.build({}, [], [], [], {}, None, NOW), {"schema": 1, "enabled": False})

    def test_wrong_values_fall_back(self):
        cfg = rm.settings({"runners": {"model": {"enabled": "yes", "jobs_per_cycle": -1, "queue_warn_minutes": 0, "alert_level": "loud", "thirdparty_usd_per_minute": -3, "thirdparty_labels": "x", "runaway_ignore_events": [3]}}})
        self.assertEqual((cfg["enabled"], cfg["jobs_per_cycle"], cfg["queue_warn_minutes"], cfg["alert_level"], cfg["thirdparty_usd_per_minute"]), (False, 10, 20, "warning", 0.0))
        self.assertEqual(cfg["thirdparty_labels"], rm.DEFAULT_THIRDPARTY)
        self.assertEqual(cfg["runaway_ignore_events"], [])

    def test_the_settings_page_checks_them(self):
        ok = settings_api.check_value
        self.assertEqual(ok("runners.model.enabled", True), (True, True))
        self.assertEqual(ok("runners.model.jobs_per_cycle", 101), (False, "range"))
        self.assertEqual(ok("runners.model.large_labels", ["my-big-*"]), (True, ["my-big-*"]))
        self.assertEqual(ok("runners.model.thirdparty_labels", ["a b"]), (False, "names"))
        self.assertEqual(ok("runners.model.thirdparty_usd_per_minute", 0.008), (True, 0.008))
        self.assertEqual(ok("runners.model.alert_level", "critical"), (False, "enum"))
        self.assertEqual(ok("runners.model.runaway_ignore_events", ["pull_request"]), (True, ["pull_request"]))


class Queue(unittest.TestCase):
    def test_the_queue_is_counted_by_kind_with_the_oldest_wait(self):
        rows = [job(["self-hosted", "linux"], ago=1800), job(["self-hosted", "linux"], ago=60), job(["ubuntu-latest"], ago=30), job(["ubuntu-latest"], "in_progress", ago=5000), job(["macos-latest-xlarge"], "waiting", ago=400)]
        out = rm.queue_by_kind(rows, NOW, CFG)
        self.assertEqual(out["selfhosted"], {"jobs": 2, "oldest_wait_seconds": 1800})
        self.assertEqual(out["hosted"], {"jobs": 1, "oldest_wait_seconds": 30})
        self.assertEqual(out["large"]["jobs"], 1)
        self.assertNotIn("thirdparty", out)

    def test_selfhosted_down_tells_a_missing_runner_from_a_busy_one(self):
        rows = [job(["self-hosted", "linux"], ago=3000, repo="a"), job(["self-hosted", "gpu"], ago=3000, repo="b"), job(["self-hosted", "arm"], ago=3000, repo="c"), job(["self-hosted", "linux"], ago=60, repo="d")]
        runners = [{"name": "r1", "state": "busy", "labels": ["self-hosted", "linux", "x64"]}, {"name": "r2", "state": "offline", "labels": ["self-hosted", "gpu"]}, {"name": "r3", "state": "idle", "labels": ["self-hosted", "arm"]}]
        out = {r["repo"]: r for r in rm.selfhosted_down(rows, runners, NOW, CFG)}
        self.assertEqual(out["a"]["reason"], "all_busy")      # a queue, not a failure
        self.assertEqual(out["b"]["reason"], "no_online_runner")      # the only runner with that label is offline
        self.assertEqual(out["c"]["reason"], "idle_not_picking")
        self.assertNotIn("d", out)      # it has waited a minute only
        self.assertEqual(out["b"]["oldest_wait_minutes"], 50)

    def test_without_the_list_of_runners_the_reason_is_unknown_not_a_failure(self):
        rows = [job(["self-hosted"], ago=3000)]
        self.assertEqual(rm.selfhosted_down(rows, None, NOW, CFG)[0]["reason"], "unknown")
        self.assertEqual(rm.alerts({"enabled": True, "selfhosted": rm.selfhosted_down(rows, None, NOW, CFG)}, ON), [])      # no alert without evidence

    def test_the_limit_of_minutes_is_a_setting(self):
        rows = [job(["self-hosted"], ago=600)]
        self.assertEqual(rm.selfhosted_down(rows, [], NOW, CFG), [])
        cfg = rm.settings({"runners": {"model": {"enabled": True, "queue_warn_minutes": 5}}})
        self.assertEqual(len(rm.selfhosted_down(rows, [], NOW, cfg)), 1)


class Runaway(unittest.TestCase):
    def runs(self, n, event="push", repo="a", name="CI", ago=60):
        return [{"repo": repo, "name": name, "event": event, "branch": "main", "started": iso(ago + i)} for i in range(n)]

    def test_a_workflow_that_fires_itself_is_found_and_a_busy_normal_one_is_not(self):
        out = rm.runaway(self.runs(25) + self.runs(5, repo="b"), NOW, CFG, sample_cap=30)
        self.assertEqual([(r["repo"], r["workflow"], r["runs_last_hour"]) for r in out["rows"]], [("a", "CI", 25)])
        self.assertFalse(out["limited"])

    def test_pull_requests_and_old_runs_do_not_count(self):
        self.assertEqual(rm.runaway(self.runs(40, event="pull_request"), NOW, CFG)["rows"], [])
        self.assertEqual(rm.runaway(self.runs(40, ago=7200), NOW, CFG)["rows"], [])

    def test_a_limit_the_sample_cannot_reach_says_so(self):
        out = rm.runaway(self.runs(20), NOW, CFG, sample_cap=10)
        self.assertTrue(out["limited"])
        self.assertEqual(rm.runaway(self.runs(40), NOW, rm.settings({"runners": {"model": {"enabled": True, "runaway_runs_per_hour": 0}}}))["rows"], [])      # 0 = off


class Cost(unittest.TestCase):
    TABLE = quota.load()

    def test_a_third_party_minute_is_never_billed_by_github(self):
        jobs = [{"seconds": 90, "labels": ["ubuntu-latest"]}, {"seconds": 61, "labels": ["blacksmith-4vcpu-ubuntu-2204"]}, {"seconds": 600, "labels": ["self-hosted"]}, {"seconds": 30, "labels": ["ubuntu-latest-8-cores"]}]
        out = rm.tally(jobs, self.TABLE, "linux", CFG)
        self.assertEqual(out["minutes"], {"hosted": 2, "thirdparty": 2, "selfhosted": 10, "large": 1})      # each job rounded up to the minute
        self.assertGreater(out["billable"], 2)      # the larger runner costs more than a standard minute
        self.assertEqual(rm.tally([{"seconds": 600, "labels": ["blacksmith-2vcpu"]}], self.TABLE, "linux", CFG)["billable"], 0)

    def test_usage_by_kind_has_a_price_only_where_there_is_one(self):
        tallies = [rm.tally([{"seconds": 600, "labels": ["ubuntu-latest"]}, {"seconds": 600, "labels": ["blacksmith-2vcpu"]}, {"seconds": 600, "labels": ["self-hosted"]}], self.TABLE, "linux", CFG)]
        out = rm.usage(tallies, self.TABLE, CFG)
        self.assertEqual(out["selfhosted"], {"minutes": 10, "usd": 0.0})
        self.assertIsNone(out["thirdparty"]["usd"])      # no price set: counted, not priced
        self.assertAlmostEqual(out["hosted"]["usd"], 10 * 0.006, places=2)
        priced = rm.usage(tallies, self.TABLE, rm.settings({"runners": {"model": {"enabled": True, "thirdparty_usd_per_minute": 0.004}}}))
        self.assertEqual(priced["thirdparty"]["usd"], 0.04)

    def test_read_costs_keeps_the_kinds_and_does_not_price_a_third_party_job_as_github(self):
        run = {"repo": "r", "id": 7, "status": "completed", "started": iso(3600)}
        body = {"jobs": [{"started_at": iso(3600), "completed_at": iso(3600 - 600), "labels": ["blacksmith-4vcpu-ubuntu-2204"]}, {"started_at": iso(3600), "completed_at": iso(3600 - 120), "labels": ["ubuntu-latest"]}]}
        config = {"finops": {"jobs_per_cycle": 5}, **ON}
        am.RUN_COSTS.clear()
        am.RUN_KINDS.clear()
        self.addCleanup(am.RUN_COSTS.clear)
        self.addCleanup(am.RUN_KINDS.clear)
        with mock.patch.object(am, "gh_read", return_value=body), mock.patch.object(am, "PRIVATE", {"r"}), mock.patch.object(am.toolconfig, "github_owner", return_value="o"):
            with mock.patch.object(am.time, "time", return_value=NOW):
                self.assertEqual(am.read_costs(config, {"runs": [run]}), 1)
        self.assertEqual(am.RUN_COSTS[7]["by_system"], {"linux": 2})      # only the GitHub-hosted minutes are billed
        self.assertEqual(am.RUN_KINDS[7]["minutes"], {"thirdparty": 10, "hosted": 2})

    def test_with_the_model_off_read_costs_is_what_it_was(self):
        run = {"repo": "r", "id": 8, "status": "completed", "started": iso(3600)}
        body = {"jobs": [{"started_at": iso(3600), "completed_at": iso(3600 - 600), "labels": ["blacksmith-4vcpu-ubuntu-2204"]}]}
        am.RUN_COSTS.clear()
        am.RUN_KINDS.clear()
        self.addCleanup(am.RUN_COSTS.clear)
        with mock.patch.object(am, "gh_read", return_value=body), mock.patch.object(am, "PRIVATE", {"r"}), mock.patch.object(am.toolconfig, "github_owner", return_value="o"), mock.patch.object(am.time, "time", return_value=NOW):
            am.read_costs({"finops": {"jobs_per_cycle": 5}}, {"runs": [run]})
        self.assertEqual(am.RUN_KINDS, {})
        self.assertEqual(am.RUN_COSTS[8]["by_system"], {"linux": 10})


class Alerts(unittest.TestCase):
    MODEL = {"enabled": True, "selfhosted": [{"repo": "a", "labels": ["gpu", "self-hosted"], "jobs": 2, "oldest_wait_minutes": 50, "reason": "no_online_runner"}, {"repo": "b", "labels": ["self-hosted"], "jobs": 1, "oldest_wait_minutes": 90, "reason": "all_busy"}],
             "runaway": {"rows": [{"repo": "c", "workflow": "CI", "runs_last_hour": 44, "events": {"push": 44}, "branches": ["main"]}], "limited": False}}

    def test_a_missing_runner_and_a_runaway_are_alerts_and_a_plain_queue_is_not(self):
        out = rm.alerts(self.MODEL, ON, "acct", NOW)
        self.assertEqual(sorted(a["code"] for a in out), ["runner.runaway", "runner.selfhosted_down"])
        self.assertTrue(all(a["sentinel"] == "system" and a["level"] == "warning" and a["id"] and a["title"] and a["created_at"] for a in out))
        self.assertEqual({a["repo"] for a in out}, {"a", "c"})

    def test_the_alerts_have_their_own_switch_and_level(self):
        self.assertEqual(rm.alerts(self.MODEL, {"runners": {"model": {"enabled": True, "alerts": False}}}, "", NOW), [])
        self.assertEqual({a["level"] for a in rm.alerts(self.MODEL, {"runners": {"model": {"enabled": True, "alert_level": "info"}}}, "", NOW)}, {"info"})
        self.assertEqual(rm.alerts({"enabled": False}, ON, "", NOW), [])

    def test_the_titles_are_in_the_language_of_the_page(self):
        with i18n.use_language("es"):
            titles = " ".join(a["title"] for a in rm.alerts(self.MODEL, ON, "", NOW))
        self.assertIn("esperando", titles)
        self.assertIn("última hora", titles)

    def test_runner_alerts_of_the_monitor_is_empty_while_off_and_never_raises(self):
        with mock.patch.object(am, "LIVE_CONFIG", {}), mock.patch.object(am.toolconfig, "raw_config", return_value={}):
            self.assertEqual(am.runner_alerts(), [])
        with mock.patch.object(am, "LIVE_CONFIG", ON), mock.patch.object(am, "runner_model_payload", side_effect=RuntimeError("x")):
            self.assertEqual(am.runner_alerts(), [])


class Wiring(unittest.TestCase):
    def setUp(self):
        am.RUNNER_JOBS["rows"].clear()
        am.RUNNER_JOBS.update(list=None, list_at=0.0)
        self.addCleanup(am.RUNNER_JOBS["rows"].clear)

    def test_the_jobs_of_unfinished_runs_are_read_within_the_limit_and_forgotten_when_the_run_ends(self):
        data = {"active": [{"repo": "r", "id": i, "status": "queued"} for i in range(1, 8)]}
        calls = []

        def reader(endpoint, retries=0):
            calls.append(endpoint)
            return {"jobs": [{"name": "j", "status": "queued", "labels": ["self-hosted", "linux"], "created_at": iso(100), "started_at": None}]}
        config = {"runners": {"model": {"enabled": True, "jobs_per_cycle": 3}}}
        with mock.patch.object(am, "gh_read", reader), mock.patch.object(am.toolconfig, "github_owner", return_value="o"):
            self.assertEqual(am.read_runner_jobs(config, data), 3)
            self.assertEqual(am.read_runner_jobs(config, data), 3)      # the ones read longest ago are not read again at once
            self.assertEqual(len(am.RUNNER_JOBS["rows"]), 6)
            self.assertEqual(am.read_runner_jobs(config, {"active": []}), 0)
        self.assertEqual(am.RUNNER_JOBS["rows"], {})
        self.assertTrue(all(c.startswith("repos/o/r/actions/runs/") and c.endswith("/jobs?per_page=100") for c in calls))

    def test_nothing_is_read_while_it_is_off_or_the_limit_is_zero(self):
        data = {"active": [{"repo": "r", "id": 1, "status": "queued"}]}
        with mock.patch.object(am, "gh_read", side_effect=AssertionError("no read")):
            self.assertEqual(am.read_runner_jobs({}, data), 0)
            self.assertEqual(am.read_runner_jobs({"runners": {"model": {"enabled": True, "jobs_per_cycle": 0}}}, data), 0)

    def test_a_job_that_cannot_be_read_does_not_stop_the_others(self):
        data = {"active": [{"repo": "r", "id": 1, "status": "queued"}, {"repo": "r", "id": 2, "status": "queued"}]}
        answers = iter([RuntimeError("boom"), {"jobs": []}])

        def reader(endpoint, retries=0):
            a = next(answers)
            if isinstance(a, Exception):
                raise a
            return a
        with mock.patch.object(am, "gh_read", reader), mock.patch.object(am.toolconfig, "github_owner", return_value="o"):
            self.assertEqual(am.read_runner_jobs(ON, data), 1)

    def test_the_payload_joins_everything_a_cycle_held(self):
        am.RUNNER_JOBS["rows"][("r", 1)] = {"at": NOW, "rows": [job(["self-hosted", "gpu"], ago=3000, repo="r")]}
        runs = [{"repo": "x", "name": "CI", "event": "push", "branch": "main", "started": iso(30 + i)} for i in range(22)]
        with mock.patch.object(am, "LIVE_CONFIG", ON), mock.patch.object(am, "runner_list", return_value=[]), mock.patch.dict(am.STATE, {"data": {"runs": runs}}):
            out = am.runner_model_payload(NOW)
        self.assertTrue(out["enabled"])
        self.assertEqual(out["queue"]["selfhosted"]["jobs"], 1)
        self.assertEqual(out["selfhosted"][0]["reason"], "no_online_runner")
        self.assertEqual(out["runaway"]["rows"][0]["runs_last_hour"], 22)
        self.assertTrue(out["runners_known"])
        with mock.patch.object(am, "LIVE_CONFIG", {}), mock.patch.object(am.toolconfig, "raw_config", return_value={}):
            self.assertEqual(am.runner_model_payload(NOW), {"schema": 1, "enabled": False})

    def test_the_route_is_read_only_and_the_alerts_include_the_model(self):
        self.assertIn('path == "/api/runners/model"', inspect.getsource(am.Handler))
        self.assertEqual(auth.required_role("GET", "/api/runners/model"), "viewer")
        self.assertIn("/api/runners", am.LITE_PATHS)
        self.assertEqual(inspect.getsource(am).count("credential_alerts() + score_alerts() + runner_alerts()"), 3)
        self.assertIn('("runner_model", lambda: spare and read_runner_jobs(config, data))', inspect.getsource(am.maintain_extras))

    def test_the_page_shows_the_model_in_the_advanced_tab(self):
        html = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('pick("/api/runners/model")', html)
        self.assertIn("ui.adv_model_queue", html)


class Texts(unittest.TestCase):
    def test_every_text_exists_in_the_eight_languages_with_the_same_placeholders(self):
        ph = re.compile(r"\{[a-z]+\}")
        keys = ("ui.cfg_b_runner_model", "ui.adv_model_h", "ui.adv_model_queue", "ui.adv_model_usage", "ui.adv_model_runaway", "ui.adv_model_down", "ui.adv_model_limited", "ui.adv_model_none", "ui.adv_model_usd_unknown",
                "runner.alert_down", "runner.alert_runaway", "ui.runner_kind_thirdparty", "ui.runner_reason_all_busy", "runner.reason_no_online_runner", "cfg.f.runners.model.enabled", "cfg.h.runners.model.runaway_runs_per_hour")
        for key in keys:
            base = sorted(ph.findall(i18n.tl("en", key)))
            for lang in i18n.LANGS:
                text = i18n.tl(lang, key)
                self.assertNotEqual(text, key, f"{lang}:{key}")
                self.assertEqual(sorted(ph.findall(text)), base, f"{lang}:{key}")


if __name__ == "__main__":
    unittest.main()
