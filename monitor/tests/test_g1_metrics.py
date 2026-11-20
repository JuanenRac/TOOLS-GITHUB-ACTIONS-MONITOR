# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Metrics of the server: histograms of the jobs from the webhook (counted once per job, bounded series), the figures of each runner, the cycle (tick) and its circuit, the queue of reads with
backpressure, the billing gauges and the tightest bucket of the allowance. No network."""
import json
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.data_pipeline import backpressure, quota_buckets, tickstats  # noqa: E402
from github_actions_monitor.integrations import job_metrics, outputs  # noqa: E402
from github_actions_monitor.security import webhook  # noqa: E402

ON = {"outputs": {"prometheus": {"histograms": True, "per_runner": True, "histogram_max_series": 10}}}


def job(status="completed", job_id=1, queue=12, seconds=60, conclusion="success", labels=("self-hosted", "linux", "gpu"), group="Default", runner="box-1"):
    return {"event": "workflow_job", "repo": "r", "status": status, "conclusion": conclusion if status == "completed" else None, "job_id": job_id, "queue": queue, "seconds": seconds,
            "labels": list(labels), "runner_group": group, "runner_name": runner}


class Parse(unittest.TestCase):
    def body(self, **extra):
        obj = {"id": 77, "run_id": 5, "name": "build", "workflow_name": "CI", "status": "completed", "conclusion": "success", "created_at": "2026-01-01T00:00:00Z",
               "started_at": "2026-01-01T00:00:30Z", "completed_at": "2026-01-01T00:01:30Z", "labels": ["self-hosted", "Linux", "bad label!"], "runner_group_name": "Default", "runner_name": "box-1"}
        obj.update(extra)
        return json.dumps({"repository": {"name": "r", "full_name": "o/r"}, "workflow_job": obj}).encode()

    def test_a_job_event_carries_the_fields_the_histograms_need(self):
        record = webhook.parse_event("workflow_job", self.body())
        self.assertEqual(record["job_id"], 77)
        self.assertEqual(record["labels"], ["self-hosted", "Linux"])      # a label that is not a plain word is dropped
        self.assertEqual((record["runner_group"], record["runner_name"], record["queue"], record["seconds"]), ("Default", "box-1", 30, 60))

    def test_those_fields_never_reach_the_live_list(self):
        for key in ("job_id", "labels", "runner_group", "runner_name"):
            self.assertNotIn(key, webhook.LIVE_FIELDS)


class Histograms(unittest.TestCase):
    def setUp(self):
        self.c = job_metrics.Collector(clock=lambda: 1000.0)

    def text(self, config=ON):
        return "\n".join(self.c.render("ghamon_", outputs._esc, config))

    def test_off_by_default_nothing_is_counted(self):
        self.assertFalse(self.c.feed(job(), {}))
        self.assertEqual(self.text({}), "")

    def test_the_queue_time_is_counted_once_per_job(self):
        self.assertTrue(self.c.feed(job("in_progress", 5, queue=12), ON))
        self.c.feed(job("completed", 5, queue=12), ON)      # the same job finishing: not counted again
        text = self.text()
        self.assertIn('ghamon_job_wait_seconds_count{label="self-hosted:gpu",runner_group="Default"} 1', text)
        self.assertIn('le="20"} 1', text)
        self.assertIn('le="10"} 0', text)

    def test_a_job_seen_only_when_it_finishes_is_counted_then(self):
        self.c.feed(job("completed", 9, queue=4), ON)
        self.assertIn("ghamon_job_wait_seconds_count", self.text())

    def test_the_demand_for_runners_is_the_jobs_waiting_by_label(self):
        self.c.feed(job("queued", 1, queue=None, seconds=None), ON)
        self.c.feed(job("queued", 2, queue=None, seconds=None, labels=("ubuntu-latest",)), ON)
        self.c.feed(job("in_progress", 2, queue=3), ON)      # it started: it no longer waits
        demand = self.c.demand()
        self.assertEqual(list(demand), ["self-hosted:gpu"])
        self.assertIn('ghamon_runner_jobs_waiting{label="self-hosted:gpu"} 1', self.text())

    def test_the_series_are_bounded_and_the_rest_is_other(self):
        for i in range(30):
            self.c.feed(job("completed", i, queue=5, labels=(f"pool-{i}",)), ON)
        series = {l.split("{")[1].split("}")[0] for l in self.text().splitlines() if l.startswith("ghamon_job_wait_seconds_count")}
        self.assertLessEqual(len(series), 11)
        self.assertTrue(any('label="other"' in s for s in series))

    def test_the_figures_of_each_runner(self):
        self.c.feed(job("completed", 1, seconds=100, queue=10, runner="box-1"), ON)
        self.c.feed(job("completed", 2, seconds=50, queue=20, conclusion="failure", runner="box-1"), ON)
        self.c.feed(job("completed", 3, seconds=5, labels=("ubuntu-latest",), runner="Hosted Agent"), ON)      # a hosted runner is not a runner of yours
        rows = self.c.runner_stats()
        self.assertEqual(rows, [{"runner": "box-1", "jobs": 2, "failed": 1, "busy_seconds": 150, "avg_queue_seconds": 15.0}])
        self.assertIn('ghamon_runner_busy_seconds_total{runner="box-1"} 150', self.text())

    def test_the_run_duration_and_the_jobs_by_conclusion(self):
        self.c.feed({"event": "workflow_run", "status": "completed", "conclusion": "failure", "seconds": 90}, ON)
        self.c.feed(job("completed", 1, conclusion="failure"), ON)
        text = self.text()
        self.assertIn('ghamon_workflow_run_seconds_count{conclusion="failure"} 1', text)
        self.assertIn('ghamon_jobs_total{label="self-hosted:gpu",conclusion="failure"} 1', text)

    def test_a_wrong_setting_falls_back(self):
        self.assertEqual(job_metrics.settings({"outputs": {"prometheus": {"histogram_max_series": "x", "histograms": "yes"}}}), {"histograms": False, "per_runner": False, "histogram_max_series": 200})


class Tick(unittest.TestCase):
    def setUp(self):
        tickstats.reset()

    def test_nothing_is_written_before_the_first_cycle(self):
        self.assertEqual(tickstats.lines("ghamon_", outputs._esc), [])

    def test_a_cycle_and_its_circuit(self):
        tickstats.note_retry(2)
        tickstats.note_cycle(3.5, True, {"collect": 2.0, "maintain": 1.0, "other": 9}, reads=40, now=100)
        tickstats.note_cycle(1.0, False, now=200)
        cache = {"a": {"fails": 3, "retry_at": 500}, "b": {"fails": 1, "retry_at": 0}, "c": {"fails": 0}}
        text = "\n".join(tickstats.lines("ghamon_", outputs._esc, cache, now=300))
        for want in ("ghamon_ticks_total 2", "ghamon_tick_failures_total 1", "ghamon_read_retries_total 2", "ghamon_repos_circuit_open 1", "ghamon_repos_read_failing 2",
                     "ghamon_repos_read_fail_streak_max 3", 'ghamon_tick_phase_seconds{phase="collect"} 2.0', "ghamon_tick_seconds_count 2", "ghamon_tick_last_ok_timestamp_seconds 100"):
            self.assertIn(want, text)
        self.assertNotIn('phase="other"', text)


class Backpressure(unittest.TestCase):
    def setUp(self):
        backpressure.reset()
        self.todo = [(f"r{i}", 20) for i in range(10)]

    def test_off_reads_everything(self):
        self.assertEqual(backpressure.plan(self.todo, {}), (self.todo, []))
        self.assertEqual(backpressure.lines("ghamon_", {}), [])

    def test_the_queue_is_ordered_and_bounded(self):
        cfg = {"backpressure": {"enabled": True, "max_reads_per_cycle": 4}}
        held = {f"r{i}": {"at": 100 - i} for i in range(1, 10)}      # r0 never read; r9 is the oldest read
        read, wait = backpressure.plan(self.todo, cfg, hot=["r5"], red=["r7"], held=held)
        self.assertEqual([r for r, _ in read], ["r7", "r5", "r0", "r9"])
        self.assertEqual(len(wait), 6)
        self.assertEqual(backpressure.snapshot()["depth"], 6)
        text = "\n".join(backpressure.lines("ghamon_", cfg))
        self.assertIn("ghamon_read_queue_depth 6", text)
        self.assertIn("ghamon_read_queue_deferred_total 6", text)

    def test_what_waited_longest_goes_first_next_time(self):
        cfg = {"backpressure": {"enabled": True, "max_reads_per_cycle": 5}}
        held = {f"r{i}": {"at": 100 + i} for i in range(10)}
        first, _ = backpressure.plan(self.todo, cfg, held=held)
        for repo, _n in first:
            held[repo]["at"] = 500
        second, _ = backpressure.plan(self.todo, cfg, held=held)
        self.assertEqual({r for r, _ in first} & {r for r, _ in second}, set())

    def test_a_slow_cycle_halves_the_allowance_and_a_fast_one_gives_it_back(self):
        cfg = {"backpressure": {"enabled": True, "max_reads_per_cycle": 100, "min_reads": 10, "shed_percent": 150}}
        todo = [(f"r{i}", 20) for i in range(200)]
        backpressure.plan(todo, cfg)
        self.assertEqual(backpressure.snapshot()["allowed"], 100)
        backpressure.plan(todo, cfg, last_seconds=100, interval=45)
        self.assertEqual(backpressure.snapshot()["allowed"], 50)
        backpressure.plan(todo, cfg, last_seconds=100, interval=45)
        backpressure.plan(todo, cfg, last_seconds=100, interval=45)
        backpressure.plan(todo, cfg, last_seconds=100, interval=45)
        self.assertEqual(backpressure.snapshot()["allowed"], 10)      # never under min_reads
        backpressure.plan(todo, cfg, last_seconds=5, interval=45)
        self.assertEqual(backpressure.snapshot()["allowed"], 11)
        self.assertGreaterEqual(backpressure.snapshot()["shed_cycles"], 4)

    def test_without_a_fixed_limit_a_slow_cycle_sets_one(self):
        cfg = {"backpressure": {"enabled": True, "min_reads": 5}}
        todo = [(f"r{i}", 20) for i in range(100)]
        self.assertEqual(len(backpressure.plan(todo, cfg)[0]), 100)
        read, wait = backpressure.plan(todo, cfg, last_seconds=200, interval=45)
        self.assertEqual((len(read), len(wait)), (50, 50))

    def test_wrong_values_fall_back(self):
        self.assertEqual(backpressure.settings({"backpressure": {"enabled": 1, "max_reads_per_cycle": -3, "shed_percent": "x"}}),
                         {"enabled": False, "max_reads_per_cycle": 0, "shed_percent": 150, "min_reads": 20})


class Buckets(unittest.TestCase):
    RES = {"core": {"limit": 5000, "remaining": 4000, "reset": 1700000000}, "graphql": {"limit": 5000, "remaining": 300, "reset": 1700000100}, "search": {"limit": 30, "remaining": 30, "reset": 1},
           "bad name!": {"limit": 1, "remaining": 1}, "scim": {"limit": "x"}}

    def setUp(self):
        quota_buckets.reset()

    def test_the_buckets_are_parsed_and_junk_is_left_out(self):
        rows = quota_buckets.parse_resources(self.RES)
        self.assertEqual([r["bucket"] for r in rows], ["core", "graphql", "search"])
        self.assertEqual(rows[1]["used_percent"], 94.0)

    def test_the_tightest_bucket_wins_and_an_unused_one_never_does(self):
        quota_buckets.note("user", self.RES)
        best = quota_buckets.tightest()
        self.assertEqual((best["source"], best["bucket"], best["others"]), ("user", "graphql", 1))      # search is untouched (30/30): it does not count as in use

    def test_two_sources_have_their_own_buckets(self):
        quota_buckets.note("user", self.RES)
        quota_buckets.note("app", {"core": {"limit": 12500, "remaining": 100, "reset": 5}})
        view = quota_buckets.view(trend={"x": 1})
        self.assertEqual([s["source"] for s in view["sources"]], ["app", "user"])
        self.assertEqual(view["tightest"]["source"], "app")
        chip = quota_buckets.chip()
        self.assertEqual(chip["bucket"], "core")
        self.assertEqual(len(chip["breakdown"]), 3)

    def test_nothing_known_is_none(self):
        self.assertIsNone(quota_buckets.tightest())
        self.assertIsNone(quota_buckets.chip())


class Exposition(unittest.TestCase):
    def setUp(self):
        tickstats.reset()
        backpressure.reset()
        job_metrics.COLLECTOR.reset()

    def test_the_billing_runners_and_waits_reach_the_exposition(self):
        extra = {"config": ON, "quota": {"included_minutes": 2000, "billing": {"minutes": 2500.5, "by_sku": {"linux": 2000.0, "windows": 500.5}, "usd": {"actions": 4.2}}},
                 "runners": {"counts": {"idle": 1, "busy": 1, "offline": 0}, "runners": [{"name": "box-1", "state": "busy"}, {"name": "box-2", "state": "offline"}]},
                 "runner_waits": {"selfhosted": {"jobs": 2, "oldest_seconds": 90}}}
        text = outputs.metrics_text(None, None, extra=extra)
        for want in ("ghamon_billing_minutes_total 2500.5", "ghamon_billing_minutes_included 2000", "ghamon_billing_minutes_paid 500.5", 'ghamon_billing_sku_minutes{sku="windows"} 500.5',
                     'ghamon_billing_usd{product="actions"} 4.2', 'ghamon_runners{state="busy"} 1', 'ghamon_runner_up{runner="box-2"} 0', 'ghamon_runner_busy{runner="box-1"} 1',
                     'ghamon_runner_kind_jobs_waiting{kind="selfhosted"} 2', 'ghamon_runner_kind_oldest_wait_seconds{kind="selfhosted"} 90'):
            self.assertIn(want, text)

    def test_every_type_line_is_written_once_and_a_scrape_without_the_extras_still_works(self):
        job_metrics.COLLECTOR.feed(job("completed", 1), ON)
        tickstats.note_cycle(2.0)
        text = outputs.metrics_text(None, None, extra={"config": ON})
        types = [l for l in text.splitlines() if l.startswith("# TYPE")]
        self.assertEqual(len(types), len(set(types)))
        self.assertIn("ghamon_job_wait_seconds_bucket", text)
        self.assertTrue(text.endswith("\n"))
        self.assertTrue(outputs.metrics_text(None, None).startswith("# HELP ghamon_info"))

    def test_the_new_settings_are_in_the_schema_with_a_conservative_default(self):
        from github_actions_monitor.app import actions_monitor, settings_api
        for key in ("outputs.prometheus.histograms", "outputs.prometheus.per_runner", "outputs.prometheus.histogram_max_series", "backpressure.enabled", "backpressure.max_reads_per_cycle",
                    "backpressure.shed_percent", "backpressure.min_reads", "quota.chip"):
            self.assertIn(key, settings_api.FIELDS)
        self.assertIs(actions_monitor.DEFAULTS["backpressure"]["enabled"], False)
        self.assertIs(settings_api.OUTPUT_DEFAULTS["prometheus"]["histograms"], False)


class ObservabilityPack(unittest.TestCase):
    """The rules of docs/grafana only name metrics the monitor writes, and the pack holds no address that is not an example."""
    GRAFANA = Path(__file__).resolve().parent.parent / "docs" / "grafana"
    SRC = Path(__file__).resolve().parent.parent / "src" / "github_actions_monitor"

    def written(self):
        text = ""
        for name in ("integrations/outputs.py", "integrations/job_metrics.py", "data_pipeline/tickstats.py", "data_pipeline/backpressure.py"):
            text += (self.SRC / name).read_text(encoding="utf-8")
        return text

    def test_every_metric_of_the_rules_is_written_by_the_code(self):
        rules = (self.GRAFANA / "ghamon_alert_rules.yml").read_text(encoding="utf-8")
        code = self.written()
        names = set(re.findall(r"ghamon_[a-z_]+", rules))
        self.assertGreater(len(names), 15)
        for name in sorted(names):
            base = re.sub(r"_(bucket|count|sum)$", "", name)
            short = base[len("ghamon_"):]
            self.assertTrue(short in code or base in code, name)

    def test_the_addresses_are_examples_and_the_flow_is_json(self):
        manager = (self.GRAFANA / "alertmanager.example.yml").read_text(encoding="utf-8")
        for url in re.findall(r"https?://[^\s\"]+", manager):
            self.assertIn("example.invalid", url)
        flow = json.loads((self.GRAFANA / "n8n_ghamon_alerts.json").read_text(encoding="utf-8"))
        self.assertEqual({n["name"] for n in flow["nodes"]} & set(flow["connections"]), {"Alertmanager webhook", "Write the message"})
        self.assertIs(flow["active"], False)


if __name__ == "__main__":
    unittest.main()
