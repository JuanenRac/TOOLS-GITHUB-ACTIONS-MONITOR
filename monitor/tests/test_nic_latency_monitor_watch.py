# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`doctor --latency` (how late the events of the account tell a push, reads only), `monitor [N]` (a `watch status` that refreshes) and the operator codes of `watch status` when the read fails. Fake
reads and a fake monitor: no network, no GitHub."""
import json
import sys
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
import threading

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_190_cli as base  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.cli import doctor, monitor_cli as cli, watch  # noqa: E402


def push(repo, sha, at):
    return {"type": "PushEvent", "repo": {"name": "acme/" + repo}, "payload": {"head": sha}, "created_at": at}


def runs_for(sha, at):
    return {"workflow_runs": [{"head_sha": "other", "created_at": "2026-01-05T11:00:00Z"}, {"head_sha": sha, "created_at": at}]}


class FakeGh:
    """The way of running `gh`: answers by endpoint, remembers every call (to prove that nothing but reads is asked)."""

    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def __call__(self, args, timeout=20):
        self.calls.append(list(args))
        if args[:3] == ["gh", "api", "user"]:
            return 0, "acme\n", ""
        answer = self.answers.get(args[2].split("?")[0])
        if answer is None:
            return 1, "", "gh: Not Found (HTTP 404)"
        return 0, json.dumps(answer), ""


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        self.t += 0.05
        return self.t


class Latency(unittest.TestCase):
    CONFIG = {"github_owner": "acme", "events_feed": {"interval_seconds": 60}}

    def test_it_measures_the_delay_between_the_run_and_the_event(self):
        gh = FakeGh({"orgs/acme/events": [push("a", "s1", "2026-01-05T12:00:30Z"), push("a", "s0", "2026-01-05T11:00:00Z"), push("b", "s2", "2026-01-05T12:05:10Z"), {"type": "WatchEvent"}],
                     "repos/acme/a/actions/runs": runs_for("s1", "2026-01-05T12:00:10Z"), "repos/acme/b/actions/runs": runs_for("s2", "2026-01-05T12:05:00Z")})
        check = doctor.latency_check(gh, self.CONFIG, Clock())
        self.assertEqual((check["id"], check["status"]), ("latency", "ok"))
        self.assertEqual((check["data"]["lag_median_s"], check["data"]["lag_max_s"], check["data"]["measured"]), (15, 20, 2))
        self.assertEqual(check["data"]["detect_worst_s"], 80)      # the worst delay plus the interval of events_feed
        self.assertIn("median 15 s, max 20 s", check["detail"])

    def test_it_only_reads(self):
        gh = FakeGh({"orgs/acme/events": [push("a", "s1", "2026-01-05T12:00:30Z")], "repos/acme/a/actions/runs": runs_for("s1", "2026-01-05T12:00:10Z")})
        doctor.latency_check(gh, self.CONFIG, Clock())
        for call in gh.calls:
            self.assertEqual(call[:2], ["gh", "api"])
            self.assertNotIn("-X", call)
            self.assertNotIn("--method", call)
            self.assertNotIn("-f", call)
            self.assertNotIn("-F", call)

    def test_a_late_event_warns_with_the_way_out(self):
        gh = FakeGh({"orgs/acme/events": [push("a", "s1", "2026-01-05T12:10:00Z")], "repos/acme/a/actions/runs": runs_for("s1", "2026-01-05T12:00:00Z")})
        check = doctor.latency_check(gh, self.CONFIG, Clock())
        self.assertEqual(check["status"], "warn")
        self.assertIn("doctor --latency", check["fix"])

    def test_a_user_account_falls_back_to_the_events_of_the_user(self):
        gh = FakeGh({"users/acme/events": [push("a", "s1", "2026-01-05T12:00:30Z")], "repos/acme/a/actions/runs": runs_for("s1", "2026-01-05T12:00:20Z")})
        check = doctor.latency_check(gh, self.CONFIG, Clock())
        self.assertEqual(check["data"]["endpoint"], "users")
        self.assertEqual(check["status"], "ok")

    def test_a_read_that_fails_is_not_evaluable_with_its_cause_and_never_a_failure(self):
        check = doctor.latency_check(FakeGh({}), self.CONFIG, Clock())
        self.assertEqual(check["status"], "warn")      # warn, never fail: the monitor is not defective because a read failed
        self.assertTrue(check["detail"].startswith("not evaluable: "))
        self.assertIn("404", check["detail"])
        self.assertFalse(check["data"]["evaluable"])
        unknown = doctor.latency_check(lambda args, timeout=20: (1, "", "no login"), {}, Clock())
        self.assertEqual((unknown["status"], unknown["detail"]), ("warn", "not evaluable: owner unknown"))

    def test_nothing_to_measure_is_not_a_warning(self):
        check = doctor.latency_check(FakeGh({"orgs/acme/events": [{"type": "WatchEvent"}]}), self.CONFIG, Clock())
        self.assertEqual(check["status"], "ok")
        self.assertIn("nothing to measure", check["detail"])

    def test_the_check_has_its_texts_and_the_flag_adds_it_to_the_doctor(self):
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            i18n.set_language(lang)
            self.addCleanup(i18n.set_language, "en")
            for key in ("doctor.t.latency", "doctor.f.latency", "cli.help_latency"):
                self.assertNotEqual(i18n.t(key), key, (lang, key))
        with mock.patch.object(doctor, "latency_check", return_value={"id": "latency", "status": "ok", "detail": "events 5 ms", "fix": "", "data": {}}) as probe, \
                mock.patch.object(doctor, "run", return_value=[{"id": "python", "status": "ok", "detail": "", "fix": ""}]):
            code, out, _ = base.run("doctor", "--latency", "--json", "--lang", "en")
        probe.assert_called_once()
        self.assertEqual(code, 0)
        self.assertEqual([c["id"] for c in json.loads(out)["data"]["checks"]] if "data" in json.loads(out) else [c["id"] for c in json.loads(out)["checks"]], ["python", "latency"])
        with mock.patch.object(doctor, "latency_check") as probe, mock.patch.object(doctor, "run", return_value=[{"id": "python", "status": "ok", "detail": "", "fix": ""}]):
            base.run("doctor", "--json", "--lang", "en")
        probe.assert_not_called()


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), base.Fake)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        base.ANSWERS.clear()
        base.SEEN.clear()
        base.ANSWERS["/api/health"] = {"ok": True, "version": "2.1.5", "uptime_seconds": 10, "lite": False, "account": "acme", "code_stale": False}
        base.ANSWERS["/api/data"] = {"data": {"repos": ["widgets"], "figures": {"active": 1, "queued": 0, "fail24": 0, "ok24": 9, "red": 0}, "rate": {"remaining": 4000, "limit": 5000}, "updated": "2026-01-05T12:00:00Z", "offline": {}}}

    def operator(self, *argv):
        with mock.patch.object(cli, "_config", return_value={}):
            return base.run(*argv, "--status-codes", "operator", "--url", self.url, "--lang", "en")


class MonitorN(Server):
    def test_the_words_become_a_watch_status(self):
        self.assertEqual(cli.monitor_words(["monitor", "10"]), ["watch", "status", "--interval", "10"])
        self.assertEqual(cli.monitor_words(["monitor"]), ["watch", "status"])
        self.assertEqual(cli.monitor_words(["monitor", "5", "--json", "--url", "x"]), ["watch", "status", "--interval", "5", "--json", "--url", "x"])
        self.assertEqual(cli.monitor_words(["monitor", "--once"]), ["watch", "status", "--once"])
        self.assertEqual(cli.monitor_words(["status", "10"]), ["status", "10"])
        self.assertEqual(cli.monitor_words(["monitor", "99999"]), ["watch", "status", "99999"])      # not a number of 1 to 9999: left for the parser to refuse

    def test_once_is_one_read_of_the_monitor(self):
        with mock.patch.object(cli, "_config", return_value={}):
            code, out, _ = base.run("monitor", "2", "--once", "--url", self.url, "--lang", "en")
        self.assertEqual(code, 0)
        self.assertIn("repos", out)
        self.assertEqual(sum(1 for path in base.SEEN if path.startswith("/api/data")), 1)      # --once: exactly one read

    def test_the_interval_is_raised_to_the_floor_of_the_setting(self):
        self.assertEqual(watch.interval_for(1, {"cli": {"watch": {"min_interval_seconds": 5}}}), 5)
        self.assertEqual(watch.interval_for(None, {}), watch.DEFAULT_INTERVAL)


class WatchStatusCodes(Server):
    def test_a_monitor_that_is_down_ends_watch_status_with_one_in_the_operator_scheme(self):
        with mock.patch.object(cli, "_config", return_value={}):
            code, _, _ = base.run("watch", "status", "--once", "--status-codes", "operator", "--url", "http://127.0.0.1:1", "--lang", "en")
            classic, _, _ = base.run("watch", "status", "--once", "--url", "http://127.0.0.1:1", "--lang", "en")
        self.assertEqual((code, classic), (1, 2))      # operator: nothing serving = 1; classic keeps the 2 every script knows

    def test_an_answer_that_is_not_a_monitor_is_two_and_a_refusal_is_one(self):
        del base.ANSWERS["/api/data"]
        code, _, _ = self.operator("watch", "status", "--once")
        self.assertEqual(code, 2)
        base.ANSWERS["/api/data"] = {"data": {"repos": "not a list", "figures": {}, "rate": {}, "updated": "", "offline": {}}}
        code, _, _ = self.operator("watch", "status", "--once")
        self.assertEqual(code, 2)

    def test_the_setting_chooses_the_scheme_for_watch_status_too(self):
        with mock.patch.object(cli, "_config", return_value={"cli": {"status_codes": "operator"}}):
            code, _, _ = base.run("watch", "status", "--once", "--url", "http://127.0.0.1:1", "--lang", "en")
        self.assertEqual(code, 1)

    def test_a_healthy_monitor_is_zero_and_alerts_keep_their_codes(self):
        self.assertEqual(self.operator("watch", "status", "--once")[0], 0)
        with mock.patch.object(cli, "_config", return_value={}):
            code, _, _ = base.run("watch", "alerts", "--once", "--status-codes", "operator", "--url", "http://127.0.0.1:1", "--lang", "en")
        self.assertEqual(code, 2)      # only `status` has the scheme


if __name__ == "__main__":
    unittest.main()
