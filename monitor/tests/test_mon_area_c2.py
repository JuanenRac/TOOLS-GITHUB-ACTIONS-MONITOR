# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The store of the AI shared by several processes (a lock of the operating system, msvcrt on Windows and fcntl elsewhere, that the system itself lets go when the process dies), and the single budget
of the AI that also counts the active notice."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _testenv  # noqa: F401
import _timing
from github_actions_monitor.sentinels import sentinel_ai
from github_actions_monitor.storage import locks

SRC = str(Path(__file__).resolve().parent.parent / "src")
FLAGS = 0x08000000 if os.name == "nt" else 0      # no console window on Windows


def run_python(code, *args, timeout=60):
    env = {**os.environ, "PYTHONPATH": SRC, "MONITOR_CONFIG_DIR": tempfile.gettempdir(), "MONITOR_DATA_DIR": tempfile.gettempdir(), "MONITOR_LOGS_DIR": tempfile.gettempdir(),
           "MONITOR_AI_DIR": tempfile.gettempdir()}
    return subprocess.run([sys.executable, "-c", code, *args], capture_output=True, text=True, timeout=_timing.limit(timeout), creationflags=FLAGS, env=env)


HOLD = """
import sys, time, os
from github_actions_monitor.storage import locks
with locks.os_lock(sys.argv[1], 5):
    print("held", flush=True)
    if sys.argv[2] == "die":
        os._exit(0)      # no release at all: the process just goes
    time.sleep(float(sys.argv[2]))
"""

CALLS = """
import sys
from github_actions_monitor.sentinels import sentinel_ai as ai
store = ai.Store(sys.argv[1])
cfg = ai.ai_config({"ai": {"provider": "openai-compatible", "base_url": "http://127.0.0.1:1/v1", "model": "m", "daily_limit": 50, "model_daily_limit": 5, "skill": False}})
calls = []
def transport(c, s, u):
    calls.append(1)
    return "answer"
for index in range(8):
    ai.explain("build", "log %s %d" % (sys.argv[2], index), cfg, store, transport=transport)
print(len(calls))
"""


class TheLockOfTheSystem(unittest.TestCase):
    def test_a_process_that_holds_it_keeps_the_others_out_until_it_lets_go(self):
        with tempfile.TemporaryDirectory() as folder:
            target = str(Path(folder) / "x.json")
            holder = subprocess.Popen([sys.executable, "-c", HOLD, target, "1.5"], stdout=subprocess.PIPE, text=True, creationflags=FLAGS,
                                      env={**os.environ, "PYTHONPATH": SRC})
            self.addCleanup(holder.kill)
            self.assertEqual(holder.stdout.readline().strip(), "held")
            with self.assertRaises(TimeoutError):
                with locks.os_lock(target, 0.3):
                    pass
            with locks.os_lock(target, _timing.limit(20)):      # once the holder is over it is ours
                pass

    def test_a_lock_left_by_a_process_that_died_is_free_at_once(self):
        with tempfile.TemporaryDirectory() as folder:
            target = str(Path(folder) / "x.json")
            done = run_python(HOLD, target, "die")
            self.assertIn("held", done.stdout)
            with locks.os_lock(target, _timing.limit(5)):
                pass
            self.assertTrue(Path(target + ".oslock").exists())      # the file stays, and it does not matter

    def test_the_rescue_of_the_other_lock_is_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "y.json"
            Path(str(target) + ".lock").write_text("99999999", encoding="ascii")
            os.utime(str(target) + ".lock", (1, 1))
            with locks.process_lock(target, _timing.limit(5)):
                pass


class SeveralProcessesOneQuota(unittest.TestCase):
    def test_three_processes_cannot_pass_the_limit_of_a_model_together(self):
        with tempfile.TemporaryDirectory() as folder:
            target = str(Path(folder) / "ai.json")
            workers = [subprocess.Popen([sys.executable, "-c", CALLS, target, str(n)], stdout=subprocess.PIPE, text=True, creationflags=FLAGS,
                                        env={**os.environ, "PYTHONPATH": SRC, "MONITOR_CONFIG_DIR": folder, "MONITOR_DATA_DIR": folder, "MONITOR_LOGS_DIR": folder, "MONITOR_AI_DIR": folder})
                       for n in range(3)]
            made = []
            for worker in workers:
                out, _ = worker.communicate(timeout=_timing.limit(120))
                made.append(int(out.strip().splitlines()[-1]))
            self.assertEqual(sum(made), 5, made)
            data = json.loads(Path(target).read_text(encoding="utf-8"))
            self.assertEqual(data["count"], 5)

    def test_the_second_store_sees_what_the_first_wrote(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "ai.json"
            one, two = sentinel_ai.Store(target), sentinel_ai.Store(target)
            with one.exclusive():
                one.add_call()
            with two.exclusive():
                two.add_call()
            self.assertEqual(two.used_today(), 2)
            with one.exclusive():
                self.assertEqual(one.used_today(), 2)


class TheActiveNoticeSpendsTheSameBudget(unittest.TestCase):
    def test_the_notice_counts_in_the_daily_total_and_stops_at_the_limit(self):
        from unittest import mock
        from github_actions_monitor.integrations import ai_notify
        from github_actions_monitor.sentinels import ai_chain
        alert = {"id": "abc", "class": "real", "state": "open", "severity": "bad", "repo": "repo-a", "workflow": "CI", "conclusion": "failure", "streak": 2, "cause": "step failed",
                 "action": "re-run once", "url": "https://github.com/o/repo-a/actions/runs/9", "since": "x"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ai.json"
            config = {"ai": {"provider": "openai-compatible", "base_url": "http://127.0.0.1:1/v1", "model": "m-ok", "daily_limit": 1, "model_daily_limit": 5},
                      "ai_alerts": {"enabled": True, "folder": folder}, "ai_notify": {"enabled": True, "confirmed_provider": "openai-compatible", "max_calls_per_hour": 9, "max_cost_per_hour_cents": 500}}
            seen = []

            def transport(cfg, system, user):
                seen.append(cfg["model"])
                return "advice"
            with mock.patch.object(sentinel_ai, "CACHE_FILE", path):
                first = ai_notify.notify(config, dict(alert, id="a1"), now=1_800_000_000, transport=transport)
                second = ai_notify.notify(config, dict(alert, id="a2"), now=1_800_000_100, transport=transport)
                store = sentinel_ai.Store(path)
                view = ai_chain.view(sentinel_ai.ai_config(config), store)
            self.assertTrue(first["sent"], first)
            self.assertEqual((second["sent"], second["reason"]), (False, "daily_cap"))
            self.assertEqual(seen, ["m-ok"])
            self.assertEqual((view["calls"], view["models"][0]["calls"]), (1, 1))


class TheGroupOfFailedJobsIsCutAndCleaned(unittest.TestCase):
    def test_the_key_of_a_group_has_a_limit_and_no_secret(self):
        from github_actions_monitor.data_pipeline import causes
        token = "gh" + "p_abcdefghijklmnopqrstuvwxyz0123456789"
        body = {"jobs": [{"name": "x" * 5000 + " " + token, "conclusion": "failure"}, {"name": "ok\nline " + token, "conclusion": "failure"}]}
        out = causes.summarize_jobs(body)
        text = json.dumps(out)
        self.assertNotIn(token, text)
        self.assertTrue(all(len(g["group"]) <= 80 and "\n" not in g["group"] for g in out["groups"]))


class AProviderOnAPrivateAddressNeedsTheSwitch(unittest.TestCase):
    def test_it_is_refused_unless_the_switch_is_on(self):
        import urllib.error
        from github_actions_monitor.security import netguard
        cfg = sentinel_ai.ai_config({"ai": {}})
        self.assertFalse(cfg["allow_private_targets"])
        self.assertTrue(sentinel_ai.ai_config({"ai": {"allow_private_targets": True}})["allow_private_targets"])
        self.assertFalse(sentinel_ai.ai_config({"ai": {"allow_private_targets": "yes"}})["allow_private_targets"])
        for url in ("https://10.255.255.1/v1", "https://169.254.169.254/latest"):
            with self.assertRaises(urllib.error.URLError) as caught:
                sentinel_ai._post_json(url, {}, {"Authorization": "Bearer x"}, 2)
            self.assertEqual(netguard.reason_of(caught.exception), "private_target", url)


class ACloudFallbackNeedsAPermission(unittest.TestCase):
    def run_chain(self, allowed):
        import tempfile
        from github_actions_monitor.sentinels import ai_chain
        calls = []

        def transport(cfg, system, user):
            calls.append(cfg["provider"])
            if cfg["provider"] == "ollama":
                raise RuntimeError("down")
            return "answer from the internet"
        cfg = sentinel_ai.ai_config({"ai": {"provider": "ollama", "model": "llama", "fallback": "anthropic=claude-x", "fallback_cloud_allowed": allowed, "skill": False}})
        seen = []
        hook = lambda first, used: seen.append((first, used))      # noqa: E731
        ai_chain.CLOUD_HOOKS.append(hook)
        self.addCleanup(ai_chain.CLOUD_HOOKS.remove, hook)
        with tempfile.TemporaryDirectory() as folder:
            result = sentinel_ai.explain("build", "log one", cfg, sentinel_ai.Store(Path(folder) / "c.json"), transport=transport)
        return result, calls, seen

    def test_without_the_permission_the_text_never_goes_to_the_internet(self):
        result, calls, seen = self.run_chain([])
        self.assertFalse(result["ok"])
        self.assertEqual(calls, ["ollama"])
        self.assertEqual(seen, [])
        self.assertEqual(result["fallback"]["failed"][-1]["reason"], "not_allowed")

    def test_with_the_permission_it_goes_and_it_is_written_down_and_told(self):
        from unittest import mock
        with mock.patch("github_actions_monitor.security.audit_log.record") as record:
            result, calls, seen = self.run_chain(["anthropic"])
        self.assertTrue(result["ok"], result)
        self.assertEqual(calls, ["ollama", "anthropic"])
        self.assertEqual(len(seen), 1)
        self.assertEqual(record.call_args[0][1], "ai.cloud_fallback")


class TheFlowSurvivesARestartAndCountsWhatIsSent(unittest.TestCase):
    NOW = 1_800_000_000.0

    def setUp(self):
        from github_actions_monitor.data_pipeline import alertflow
        self.alertflow = alertflow
        self.addCleanup(alertflow.configure, {})

    def event(self, kind, repo="r", level="bad"):
        return {"kind": kind, "code": kind, "level": level, "repo": repo, "owner": "main", "text": repo, "url": None, "args": {"repo": repo, "workflow": "CI"}}

    def test_only_what_a_channel_sends_counts_for_the_threshold(self):
        self.alertflow.configure({"alerts": {"digest": {"minutes": 60, "threshold": 3}}, "notify": {"enabled": True, "events": ["red_new"]}})
        flow = self.alertflow.Flow()
        told, _ = flow.shape([self.event("prs_up", "p%d" % n, "info") for n in range(10)] + [self.event("red_new", "x")], self.NOW)
        self.assertEqual(len(told), 11)      # nothing was held: ten events nobody sends do not count
        self.assertEqual(flow.held, [])

    def test_what_is_held_and_the_reminders_survive_a_restart(self):
        import tempfile
        from github_actions_monitor.data_pipeline import events
        self.alertflow.configure({"alerts": {"digest": {"minutes": 1440, "threshold": 3}, "silences": ["demo;why;2020-01-01"]}})
        with tempfile.TemporaryDirectory() as folder:
            feed = events.Feed(Path(folder) / "e.jsonl", Path(folder) / "state.json")
            feed.state = {"reds": {}, "stuck": {}}
            feed.flow.shape([self.event("red_new", "r%d" % n) for n in range(5)], self.NOW)
            feed._write_state()
            again = events.Feed(Path(folder) / "e.jsonl", Path(folder) / "state.json")
            self.assertEqual(len(again.flow.held), 3)      # five reds and the reminder: three go out, three are held
            self.assertEqual(again.flow.reminded, feed.flow.reminded)
            self.assertEqual(len(again.flow.sent), 3)

    def test_the_reminder_of_a_review_is_not_repeated_after_a_restart(self):
        self.alertflow.configure({"alerts": {"silences": ["demo;why;2020-01-01"]}})
        flow = self.alertflow.Flow()
        first, _ = flow.shape([], self.NOW)
        self.assertEqual([e["kind"] for e in first], ["silence_review"])
        other = self.alertflow.Flow()
        other.restore(json.loads(json.dumps(flow.dump())))
        second, _ = other.shape([], self.NOW + 60)
        self.assertEqual(second, [])


class ASilenceCanExpire(unittest.TestCase):
    NOW = 1_800_000_000.0      # 2027-01-15

    def setUp(self):
        from github_actions_monitor.data_pipeline import alertflow
        self.alertflow = alertflow
        self.addCleanup(alertflow.configure, {})

    def event(self):
        return {"kind": "red_new", "code": "red_new", "level": "bad", "repo": "demo", "owner": "main", "text": "t", "url": None, "args": {"repo": "demo", "workflow": "CI"}, "branch": "main"}

    def test_it_works_for_ever_by_default_and_expires_when_asked(self):
        self.alertflow.configure({"alerts": {"silences": ["demo;why;2026-12-01"]}})
        told, _ = self.alertflow.Flow().shape([self.event()], self.NOW)
        self.assertEqual([e["kind"] for e in told], ["silence_review"])      # silenced, with the reminder
        self.alertflow.configure({"alerts": {"silences": ["demo;why;2026-12-01"], "silences_expire_days": 30}})
        told, _ = self.alertflow.Flow().shape([self.event()], self.NOW)
        self.assertIn("red_new", [e["kind"] for e in told])      # 45 days past the date: it no longer silences
        self.alertflow.configure({"alerts": {"silences": ["demo;why"], "silences_expire_days": 30}})
        told, _ = self.alertflow.Flow().shape([self.event()], self.NOW)
        self.assertEqual(told, [])      # without a date it never expires

    def test_the_signal_lists_the_silences_that_need_a_decision(self):
        from github_actions_monitor.data_pipeline import signals
        self.alertflow.configure({"alerts": {"silences": ["demo;why;2026-12-01", "other;why", "fine;why;2099-01-01"]}})
        doc = signals.inventory({}, now=self.NOW)
        row = next(s for s in doc if s["id"] == "alerts.silences")
        self.assertEqual((row["level"], sorted(r["repo"] for r in row["rows"])), ("watch", ["demo", "other"]))
        self.alertflow.configure({})
        self.assertNotIn("alerts.silences", [s["id"] for s in signals.inventory({}, now=self.NOW)])


class TheSummaryReachesTheChannelsThatAskedForWhatItHolds(unittest.TestCase):
    def test_a_summary_of_stuck_builds_goes_to_a_channel_that_asked_only_for_stuck(self):
        from unittest import mock
        from github_actions_monitor.integrations import notifiers
        config = {"notify": {"enabled": True, "events": ["stuck_new"], "channels": {"http_local": {"enabled": True, "url": "http://127.0.0.1:1/x"}}}}
        digest = {"kind": "alerts_digest", "owner": "main", "level": "warn", "repo": "", "text": "2 held", "args": {"items": [{"kind": "stuck_new", "repo": "a"}, {"kind": "stuck_new", "repo": "b"}]}}
        sent = []
        with mock.patch.object(notifiers, "send_channel", side_effect=lambda *a, **k: sent.append(a[0]) or {"ok": True}), mock.patch.object(notifiers, "check_channel", return_value=None):
            notifiers.notify(config, digest)
            self.assertEqual(sent, ["http_local"])
            sent.clear()
            notifiers.notify(config, dict(digest, args={"items": [{"kind": "prs_up"}]}))
            self.assertEqual(sent, [])


if __name__ == "__main__":
    unittest.main()
