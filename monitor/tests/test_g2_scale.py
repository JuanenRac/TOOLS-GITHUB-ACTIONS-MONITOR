# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Scale and cost: the limits table and its doctor check, one read for everybody, the ledger of notifications, the cost by kind of change with the carbon estimate and the local reusable workflows."""
import tempfile
import threading
import time
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.data_pipeline import change_cost, limits, sharedread  # noqa: E402
from github_actions_monitor.integrations import notify_dedupe  # noqa: E402


class Limits(unittest.TestCase):
    def test_a_big_account_fills_the_api_and_the_memory(self):
        rows = {r["id"]: r for r in limits.planned({"refresh_seconds": 30, "cold_refresh_seconds": 60, "runs_per_repo": 100, "discover_limit": 1000}, 900)}
        self.assertEqual(rows["api_calls_per_hour"]["level"], "bad")
        self.assertEqual(rows["repos_listed"]["percent"], 90.0)
        self.assertEqual(rows["repos_listed"]["level"], "warn")
        self.assertEqual(rows["memory_mb"]["level"], "ok")

    def test_a_small_account_is_fine_and_the_sampler_budget_is_a_ceiling_too(self):
        self.assertEqual(limits.verdict(limits.planned({}, 20))[0], "ok")
        rows = {r["id"]: r for r in limits.planned({"sampling": {"api_budget_per_hour": 100}}, 200)}
        self.assertEqual(rows["sampler_budget"]["level"], "bad")

    def test_warn_percent_and_wrong_values(self):
        self.assertEqual(limits.settings({"limits": {"warn_percent": 10, "memory_mb": "x"}}), {"warn_percent": 80, "memory_mb": 512})
        rows = limits.planned({"limits": {"warn_percent": 50}, "discover_limit": 1000}, 600)
        self.assertEqual([r["level"] for r in rows if r["id"] == "repos_listed"], ["warn"])

    def test_the_live_rows_leave_out_what_is_not_known(self):
        rows = limits.live({}, {"live_events": 95, "live_events_keep": 100, "sse_clients": 1, "sse_max": 3, "read_queue_depth": 4, "read_queue_wanted": 8})
        self.assertEqual({r["id"]: r["level"] for r in rows}, {"live_events": "warn", "live_streams": "ok", "read_queue": "ok"})
        self.assertEqual(limits.live({}, {}), [])
        text = "\n".join(limits.lines("ghamon_", rows))
        self.assertIn('ghamon_limit_used_percent{limit="live_events"} 95.0', text)

    def test_the_doctor_has_a_capacity_check(self):
        from github_actions_monitor.ops import checks
        status, detail = checks.capacity({"discover_limit": 10, "refresh_seconds": 1, "cold_refresh_seconds": 1}, repos=50)
        self.assertEqual(status, "fail")
        self.assertIn("repos_listed", detail)
        self.assertEqual(checks.capacity({}, repos=5)[0], "ok")
        self.assertEqual(checks.capacity({}, repos=None)[0], "ok")      # no picture yet: nothing to judge


class SharedRead(unittest.TestCase):
    def setUp(self):
        sharedread.SHARED.reset()

    def test_off_every_caller_reads(self):
        calls = []
        for _ in range(3):
            sharedread.read({}, "r/w", lambda: calls.append(1) or "x")
        self.assertEqual(len(calls), 3)

    def test_on_the_answer_is_kept_for_a_while_and_a_failure_is_not(self):
        cfg = {"refresh": {"share_by_workflow": True, "share_seconds": 20}}
        calls = []
        self.assertEqual(sharedread.read(cfg, "r/w", lambda: calls.append(1) or "jobs"), "jobs")
        self.assertEqual(sharedread.read(cfg, "r/w", lambda: calls.append(1) or "other"), "jobs")
        self.assertEqual(len(calls), 1)

        def boom():
            raise OSError("down")
        with self.assertRaises(OSError):
            sharedread.read(cfg, "r/x", boom)
        self.assertEqual(sharedread.read(cfg, "r/x", lambda: "back"), "back")      # the failure was not remembered

    def test_another_workflow_is_never_shared(self):
        cfg = {"refresh": {"share_by_workflow": True}}
        self.assertEqual(sharedread.read(cfg, "r/a", lambda: 1), 1)
        self.assertEqual(sharedread.read(cfg, "r/b", lambda: 2), 2)

    def test_callers_that_arrive_together_make_one_call(self):
        cfg = {"refresh": {"share_by_workflow": True}}
        gate, calls, answers = threading.Event(), [], []

        def slow():
            calls.append(1)
            gate.wait(2)
            return "one"
        threads = [threading.Thread(target=lambda: answers.append(sharedread.read(cfg, "r/w", slow))) for _ in range(5)]
        for t in threads:
            t.start()
        time.sleep(0.3)
        gate.set()
        for t in threads:
            t.join(5)
        self.assertEqual(answers, ["one"] * 5)
        self.assertEqual(len(calls), 1)
        self.assertGreaterEqual(sharedread.SHARED.stats["waited"], 1)
        self.assertIn("ghamon_shared_reads_spared_total", "\n".join(sharedread.lines("ghamon_", cfg)))

    def test_the_lifetime_ends(self):
        clock = [100.0]
        shared = sharedread.Shared(clock=lambda: clock[0])
        n = []
        shared.get("k", lambda: n.append(1) or 1, 10)
        clock[0] = 105.0
        shared.get("k", lambda: n.append(1) or 1, 10)
        clock[0] = 120.0
        shared.get("k", lambda: n.append(1) or 1, 10)
        self.assertEqual(len(n), 2)


class Ledger(unittest.TestCase):
    ON = {"notify": {"dedupe_ledger": True, "dedupe_hours": 24}}

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / notify_dedupe.FILE_NAME
        notify_dedupe.reset(self.path)

    def tearDown(self):
        notify_dedupe.reset(None)
        self.dir.cleanup()

    def event(self, **extra):
        return {"kind": "red_new", "repo": "r", "workflow": "ci", "url": "https://github.com/o/r/actions/runs/1", "text": "ci is red", **extra}

    def test_off_everything_passes(self):
        self.assertTrue(notify_dedupe.allow({}, self.event()))
        self.assertTrue(notify_dedupe.allow({}, self.event()))

    def test_the_same_label_is_not_sent_again_but_a_new_run_is(self):
        self.assertTrue(notify_dedupe.allow(self.ON, self.event(), now=1000))
        self.assertFalse(notify_dedupe.allow(self.ON, self.event(text="ci is red (again)"), now=1100))
        self.assertTrue(notify_dedupe.allow(self.ON, self.event(url="https://github.com/o/r/actions/runs/2"), now=1100))
        self.assertTrue(notify_dedupe.allow(self.ON, self.event(), now=1000 + 25 * 3600))      # after the window it may be said again
        self.assertEqual(notify_dedupe.stats()["dropped"], 1)

    def test_it_survives_a_restart_and_holds_no_text(self):
        notify_dedupe.allow(self.ON, self.event(), now=1000)
        notify_dedupe.reset(self.path)      # a new process: only the file is left
        self.assertFalse(notify_dedupe.allow(self.ON, self.event(), now=1200))
        saved = self.path.read_text(encoding="utf-8")
        self.assertNotIn("ci is red", saved)
        self.assertNotIn("github.com", saved)

    def test_an_event_with_old_evidence_is_dropped(self):
        cfg = {"notify": {"max_event_age_hours": 48}}
        now = time.time()
        old = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 5 * 86400))
        fresh = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 3600))
        self.assertFalse(notify_dedupe.allow(cfg, self.event(at=old), now=now))
        self.assertTrue(notify_dedupe.allow(cfg, self.event(at=fresh), now=now))
        self.assertTrue(notify_dedupe.allow(cfg, self.event(), now=now))      # no date: no way to say it is old
        self.assertEqual(notify_dedupe.stats()["stale"], 1)

    def test_a_broken_file_starts_empty(self):
        self.path.write_text("{nope", encoding="utf-8")
        notify_dedupe.reset(self.path)
        self.assertTrue(notify_dedupe.allow(self.ON, self.event(), now=1000))

    def test_notify_asks_the_ledger_and_the_teams_channel_takes_a_power_automate_address(self):
        from github_actions_monitor.integrations import channels, notifiers
        sent = []
        cfg = {"notify": {"enabled": True, "events": ["red_new"], "dedupe_ledger": True, "channels": {"http_local": {"enabled": True, "url": "http://127.0.0.1:9/x"}}}}
        send = lambda *a, **k: sent.append(1) or {"ok": True}      # noqa: E731
        original = notifiers.send_channel
        notifiers.send_channel = send
        try:
            notifiers.notify(cfg, self.event(), now=1000)
            notifiers.notify(cfg, self.event(), now=1001)
        finally:
            notifiers.send_channel = original
        self.assertEqual(len(sent), 1)
        teams = channels.CHANNELS["teams"] if hasattr(channels, "CHANNELS") else None
        for host in ("prod-12.westus.logic.azure.com", "default.environment.api.powerplatform.com", "contoso.webhook.office.com"):
            self.assertTrue(any(host == h or host.endswith("." + h) for h in channels.TEAMS_HOSTS), host)
        self.assertIsNotNone(teams) if teams is not None else None


class ChangeCost(unittest.TestCase):
    ON = {"finops": {"by_change": True}}

    def run_(self, repo="a", title="", event="push", actor="me", bot=False, seconds=120, path="ci.yml", status="completed"):
        return {"repo": repo, "title": title, "event": event, "actor": actor, "actor_bot": bot, "seconds": seconds, "path": path, "status": status}

    def test_the_kinds(self):
        c = change_cost.classify
        self.assertEqual(c(self.run_(title="feat(ui): a thing")), "feature")
        self.assertEqual(c(self.run_(title="Fix!: crash")), "fix")
        self.assertEqual(c(self.run_(title="docs: x")), "docs")
        self.assertEqual(c(self.run_(title="build: x")), "ci")
        self.assertEqual(c(self.run_(actor="dependabot[bot]", bot=True, title="feat: x")), "dependencies")
        self.assertEqual(c(self.run_(title="Bump lodash from 1 to 2")), "dependencies")
        self.assertEqual(c(self.run_(event="schedule")), "scheduled")
        self.assertEqual(c(self.run_(event="workflow_dispatch", title="feat: x")), "manual")
        self.assertEqual(c(self.run_(title="Merge pull request #3")), "other")

    def test_off_nothing_is_built(self):
        self.assertEqual(change_cost.build({}, [self.run_()]), {"enabled": False})

    def test_minutes_share_and_dollars_by_kind(self):
        runs = [self.run_(title="feat: a", seconds=600), self.run_(title="feat: b", seconds=300, repo="pub"), self.run_(event="schedule", seconds=100), self.run_(title="fix: c", seconds=60, status="in_progress")]
        out = change_cost.build(self.ON, runs, private={"a"}, usd_per_minute=0.01)
        rows = {r["type"]: r for r in out["rows"]}
        self.assertEqual(out["total_minutes"], 17)
        self.assertEqual((rows["feature"]["runs"], rows["feature"]["minutes"], rows["feature"]["estimated_usd"]), (2, 15, 0.1))      # the public repository costs no dollars
        self.assertEqual(rows["scheduled"]["minutes"], 2)
        self.assertNotIn("fix", rows)      # an unfinished run is not counted
        self.assertEqual(out["rows"][0]["type"], "feature")
        self.assertAlmostEqual(sum(r["share"] for r in out["rows"]), 100.0, places=0)

    def test_local_reusable_workflows_are_left_out(self):
        runs = [self.run_(path="deploy-call.yml", seconds=600), self.run_(path="ci.yml", seconds=60)]
        out = change_cost.build(self.ON, runs, local_reusables={"a": {"deploy-call.yml"}})
        self.assertEqual(out["total_minutes"], 1)

    def test_the_carbon_is_an_estimate_from_your_figures(self):
        cfg = {"finops": {"co2": True, "co2_watts": 60, "co2_grams_per_kwh": 500}}
        out = change_cost.build(cfg, [self.run_(seconds=3600)])
        self.assertEqual(out["co2"], {"kwh": 0.06, "grams": 30.0, "watts": 60, "grams_per_kwh": 500, "estimate": True})
        self.assertEqual(out["rows"], [])      # by_change is off: only the carbon
        self.assertIn("ghamon_ci_co2_grams_estimate 30.0", "\n".join(change_cost.lines("ghamon_", out)))

    def test_the_exposition_has_one_series_per_kind(self):
        out = change_cost.build(self.ON, [self.run_(title="fix: a"), self.run_(title="docs: b")])
        text = "\n".join(change_cost.lines("ghamon_", out))
        self.assertIn('ghamon_ci_change_minutes{change="fix"} 2', text)
        self.assertIn('ghamon_ci_change_runs{change="docs"} 1', text)


if __name__ == "__main__":
    unittest.main()
