# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Scale: queues with back-pressure, the monitor's own metrics, the Prometheus text and the documented limits. Deterministic: no thread, no sleep, no clock."""
import re
import unittest

import _testenv  # noqa: F401
from github_actions_monitor.phase4 import scale


class Queues(unittest.TestCase):
    def test_accept_coalesce_and_refuse(self):
        q = scale.WorkQueues(depth=2)
        self.assertEqual(q.submit("a", "ci", "j1"), "accepted")
        self.assertEqual(q.submit("a", "ci", "j1"), "coalesced")
        self.assertEqual(q.submit("a", "ci", "j2"), "accepted")
        self.assertEqual(q.submit("a", "ci", "j3"), "rejected")
        self.assertEqual(q.depth_of("a", "ci"), 2)
        self.assertEqual(q.snapshot()["dropped"], {"a/ci": 1})
        self.assertEqual(q.snapshot()["coalesced"], {"a/ci": 1})

    def test_the_queue_never_grows_past_its_depth(self):
        q = scale.WorkQueues(depth=5)
        for i in range(1000):
            q.submit("a", "ci", "j%d" % i)
        self.assertEqual(q.depth_of("a", "ci"), 5)
        self.assertEqual(q.dropped[("a", "ci")], 995)

    def test_bad_names_are_rejected(self):
        q = scale.WorkQueues()
        for account, sentinel in (("A", "ci"), ("a b", "ci"), ("a", ""), ("", "ci"), (None, "ci"), ("a\n", "ci"), ("a", 5)):
            self.assertEqual(q.submit(account, sentinel, "j"), "rejected")
        self.assertEqual(q.queues, {})

    def test_a_running_job_is_coalesced_too(self):
        q = scale.WorkQueues()
        q.submit("a", "ci", "j")
        self.assertEqual(q.next(), ("a", "ci", "j"))
        self.assertEqual(q.submit("a", "ci", "j"), "coalesced")
        q.done("a", "ci", "j")
        self.assertEqual(q.submit("a", "ci", "j"), "accepted")

    def test_an_account_never_runs_more_than_its_parallel_limit(self):
        q = scale.WorkQueues(depth=10, per_account_parallel=2)
        for i in range(5):
            q.submit("a", "ci", "j%d" % i)
        first, second = q.next(), q.next()
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertIsNone(q.next())
        q.done(*first)
        self.assertIsNotNone(q.next())

    def test_accounts_are_served_in_turn_so_a_busy_one_cannot_starve_the_rest(self):
        q = scale.WorkQueues(depth=50, per_account_parallel=100)
        for i in range(20):
            q.submit("busy", "ci", "j%d" % i)
        q.submit("quiet", "ci", "only")
        order = [q.next()[0] for _ in range(4)]
        self.assertIn("quiet", order[:2])

    def test_a_drained_system_returns_none(self):
        q = scale.WorkQueues()
        self.assertIsNone(q.next())
        q.submit("a", "ci", "j")
        job = q.next()
        q.done(*job)
        self.assertIsNone(q.next())
        self.assertEqual(q.snapshot()["depth"], {})

    def test_every_queued_job_runs_exactly_once(self):
        q = scale.WorkQueues(depth=20, per_account_parallel=1)
        want = set()
        for account in ("a", "b", "c"):
            for sentinel in ("ci", "collab"):
                for i in range(3):
                    q.submit(account, sentinel, "j%d" % i)
                    want.add((account, sentinel, "j%d" % i))
        ran = []
        while True:
            job = q.next()
            if job is None:
                break
            ran.append(job)
            q.done(*job)
        self.assertEqual(sorted(ran), sorted(want))

    def test_backoff_doubles_and_resets(self):
        q = scale.WorkQueues(depth=1)
        q.submit("a", "ci", "j")
        self.assertEqual(q.backoff("a", "ci"), 0)
        delays = []
        for i in range(12):
            q.submit("a", "ci", "x%d" % i)
            delays.append(q.backoff("a", "ci"))
        self.assertEqual(delays[:4], [5, 10, 20, 40])
        self.assertEqual(max(delays), scale.MAX_BACKOFF)
        job = q.next()
        q.done(*job)
        self.assertEqual(q.submit("a", "ci", "fresh"), "accepted")
        self.assertEqual(q.backoff("a", "ci"), 0)


class Metrics(unittest.TestCase):
    def test_percentiles(self):
        self.assertEqual(scale.percentile([], 95), 0.0)
        self.assertEqual(scale.percentile([5], 50), 5.0)
        values = list(range(1, 101))
        self.assertEqual((scale.percentile(values, 50), scale.percentile(values, 95), scale.percentile(values, 100)), (50.0, 95.0, 100.0))
        self.assertEqual(scale.percentile([3, 1, 2], 50), 2.0)

    def test_record_and_summary(self):
        m = scale.TickMetrics(history=3)
        for seconds in (1, 2, 3, 10):
            m.record_tick("a", "ci", seconds, ok=seconds != 2, state_bytes=100 * seconds)
        s = m.summary()[("a", "ci")]
        self.assertEqual((s["count"], s["errors"], s["max"], s["state_bytes"]), (4, 1, 10.0, 1000))      # the window keeps the last 3: 2, 3, 10
        self.assertEqual(s["p50"], 3.0)

    def test_bad_values_are_not_recorded(self):
        m = scale.TickMetrics()
        for args in (("A", "ci", 1), ("a", "ci", -1), ("a", "ci", "x"), ("a", "ci", True), ("a", "", 1)):
            self.assertFalse(m.record_tick(*args))
        m.record_rate("a", -5)
        m.record_rate("a", True)
        m.record_rate("A", 5)
        self.assertEqual((m.summary(), m.rate_remaining), ({}, {}))
        self.assertTrue(m.record_tick("a", "ci", 0.5, state_bytes=-1))
        self.assertIsNone(m.summary()[("a", "ci")]["state_bytes"])


class Prometheus(unittest.TestCase):
    def build(self):
        m = scale.TickMetrics()
        for s in (0.5, 1.5):
            m.record_tick("acc-1", "ci", s, state_bytes=2048)
        m.record_tick("acc-1", "collab", 0.1, ok=False)
        m.record_rate("acc-1", 4321)
        q = scale.WorkQueues(depth=1)
        q.submit("acc-1", "ci", "j")
        q.submit("acc-1", "ci", "k")
        q.next()
        return m, q

    def test_text_is_valid_exposition(self):
        text = scale.render_metrics(*self.build())
        self.assertTrue(text.endswith("\n"))
        helped, typed = set(), set()
        for line in text.splitlines():
            if line.startswith("# HELP "):
                helped.add(line.split()[2])
            elif line.startswith("# TYPE "):
                typed.add(line.split()[2])
            else:
                self.assertRegex(line, r'^ghamon_[a-z_]+(\{([a-z_]+="[^"\n]*",?)+\})? -?[0-9.e+-]+$')
        self.assertEqual(helped, typed)
        self.assertIn('ghamon_rate_limit_remaining{account="acc-1"} 4321', text)
        self.assertIn('ghamon_tick_errors_total{account="acc-1",sentinel="collab"} 1', text)
        self.assertIn('ghamon_queue_dropped_total{account="acc-1",sentinel="ci"} 1', text)
        self.assertIn('ghamon_tick_seconds{account="acc-1",quantile="0.95",sentinel="ci"} 1.5', text)

    def test_help_and_type_appear_once_per_name(self):
        text = scale.render_metrics(*self.build())
        for name in re.findall(r"# TYPE (\S+)", text):
            self.assertEqual(text.count("# TYPE %s " % name), 1)

    def test_empty_and_queues_optional(self):
        self.assertEqual(scale.render_metrics(scale.TickMetrics()), "")
        self.assertIn("ghamon_ticks_total", scale.render_metrics(self.build()[0]))

    def test_series_are_capped(self):
        m = scale.TickMetrics()
        for i in range(scale.MAX_SERIES):
            m.record_tick("a%d" % i, "ci", 1.0)
        self.assertLessEqual(len([line for line in scale.render_metrics(m).splitlines() if not line.startswith("#")]), scale.MAX_SERIES)


class Limits(unittest.TestCase):
    def test_inside_near_and_over(self):
        self.assertEqual(scale.limits_report(3, 100), [])
        near = scale.limits_report(17, 100)
        self.assertEqual([(r["code"], r["level"]) for r in near], [("accounts_near", "info")])
        over = scale.limits_report(21, 501)
        self.assertEqual(sorted(r["code"] for r in over), ["accounts_over", "repos_over"])
        self.assertEqual(scale.limits_report(5, 60, {"max_repos_per_install": 60})[0]["code"], "repos_near")
        self.assertEqual(scale.limits_report(5, 60, {"max_repos_per_install": 100})[0:], [])

    def test_the_documented_limits_match_the_default_settings(self):
        from github_actions_monitor import phase4
        d = phase4.DEFAULTS["scale"]
        self.assertEqual(scale.DOCUMENTED_LIMITS["accounts_per_install"], d["max_accounts"])
        self.assertEqual(scale.DOCUMENTED_LIMITS["repos_per_install"], d["max_repos_per_install"])
        self.assertEqual(scale.DOCUMENTED_LIMITS["queue_depth"], d["queue_depth"])
        self.assertEqual(scale.DOCUMENTED_LIMITS["per_account_parallel"], d["per_account_parallel"])


if __name__ == "__main__":
    unittest.main()
