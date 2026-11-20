# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The cheap reads that keep the monitor in step with the world: the events of the account read with an ETag (which repository changed), the state of GitHub (githubstatus.com) and what it says about a red,
and the outside heartbeat. Every read is a fake: no network, no GitHub."""
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.data_pipeline import events, eventfeed, githubstatus  # noqa: E402
from github_actions_monitor.integrations import heartbeat  # noqa: E402
from github_actions_monitor.security import envguard  # noqa: E402

NOW = 1_800_000_000.0


def answer(status, etag='"abc"', body=None, poll=None):
    head = f"HTTP/2.0 {status} X\r\netag: {etag}\r\n" + (f"x-poll-interval: {poll}\r\n" if poll is not None else "") + "\r\n"
    return (0 if status in (200, 304) else 1), head + (json.dumps(body) if body is not None else ""), ""


def event(number, repo, kind="PushEvent"):
    return {"id": str(number), "type": kind, "repo": {"name": "o/" + repo}}


class FakeRun:
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def __call__(self, args):
        self.calls.append(args)
        item = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        return item(args) if callable(item) else item


class EventFeed(unittest.TestCase):
    CONFIG = {"events_feed": {"enabled": True, "interval_seconds": 60}}

    def test_the_settings_are_bounded_and_off_by_default(self):
        self.assertFalse(eventfeed.settings({})["enabled"])
        self.assertEqual(eventfeed.settings({"events_feed": {"interval_seconds": 5}})["interval_seconds"], 60)
        self.assertEqual(eventfeed.settings({"events_feed": {"interval_seconds": 3601}})["interval_seconds"], 60)
        self.assertEqual(eventfeed.settings({"events_feed": {"interval_seconds": 30}})["interval_seconds"], 30)
        self.assertEqual(eventfeed.settings({"events_feed": {"owner_kind": "x"}})["owner_kind"], "auto")
        self.assertEqual(eventfeed.settings({"events_feed": {"max_per_tick": 0}})["max_per_tick"], 20)
        self.assertFalse(eventfeed.settings({"events_feed": {"enabled": "yes"}})["enabled"])

    def test_the_addresses(self):
        self.assertEqual(eventfeed.endpoints("o", "auto"), ["orgs/o/events?per_page=30", "users/o/events?per_page=30"])
        self.assertEqual(eventfeed.endpoints("o", "user"), ["users/o/events?per_page=30"])
        self.assertEqual(eventfeed.endpoints("../x", "auto"), [])
        self.assertEqual(eventfeed.endpoints("", "org"), [])

    def test_a_read_says_304_or_200_and_what_to_wait(self):
        status, tag, body, poll = eventfeed.read(FakeRun(answer(200, '"t1"', [event(5, "R")], 90)), "e")
        self.assertEqual((status, tag, poll, len(body)), (200, '"t1"', 90, 1))
        run = FakeRun(answer(304, '"t1"'))
        self.assertEqual(eventfeed.read(run, "e", '"t1"')[:3], (304, '"t1"', None))
        self.assertIn("If-None-Match: \"t1\"", run.calls[0])
        with self.assertRaises(RuntimeError):
            eventfeed.read(FakeRun(answer(404)), "e")
        with self.assertRaises(RuntimeError):
            eventfeed.read(lambda args: (0, "HTTP/2.0 200 OK\r\n\r\nnot json", ""), "e")

    def test_only_new_events_of_watched_repositories_that_can_change_a_run_count(self):
        events_ = [event(9, "A"), event(8, "B", "WatchEvent"), event(7, "A"), event(6, "C"), {"id": "x", "type": "PushEvent"}, "junk", {"id": "5", "type": "PushEvent", "repo": {"name": "o/D"}}, event(4, "../bad")]
        repos, newest = eventfeed.fresh_repos(events_, 5, ["A", "B", "C", "D"], 10)
        self.assertEqual((repos, newest), (["A", "C"], 9))
        self.assertEqual(eventfeed.fresh_repos(events_, 0, ["A", "B", "C", "D"], 1)[0], ["A"])
        self.assertEqual(eventfeed.fresh_repos(None, 3, ["A"], 5), ([], 3))

    def test_the_first_read_learns_and_the_next_one_marks(self):
        feed = eventfeed.Feed()
        run = FakeRun(answer(200, '"t1"', [event(10, "A"), event(9, "B")]), answer(304), answer(200, '"t2"', [event(12, "B"), event(11, "A"), event(10, "A")]))
        self.assertEqual(feed.tick(run, "o", self.CONFIG, ["A", "B"], NOW), [])
        self.assertEqual(feed.tick(run, "o", self.CONFIG, ["A", "B"], NOW + 10), [], "before its time it does not read")
        self.assertEqual(len(run.calls), 1)
        self.assertEqual(feed.tick(run, "o", self.CONFIG, ["A", "B"], NOW + 61), [])
        self.assertEqual(feed.snapshot(self.CONFIG)["unchanged"], 1)
        self.assertEqual(feed.tick(run, "o", self.CONFIG, ["A", "B"], NOW + 130), ["B", "A"])
        snap = feed.snapshot(self.CONFIG)
        self.assertEqual((snap["changed"], snap["marked"], snap["newest"], snap["endpoint"]), (1, 2, 12, "orgs/o/events"))

    def test_an_empty_first_list_still_counts_as_learned(self):
        feed = eventfeed.Feed()
        run = FakeRun(answer(200, '"t1"', []), answer(200, '"t2"', [event(3, "A")]))
        feed.tick(run, "o", self.CONFIG, ["A"], NOW)
        self.assertEqual(feed.tick(run, "o", self.CONFIG, ["A"], NOW + 70), ["A"])

    def test_a_user_account_is_found_after_the_organization_fails(self):
        feed = eventfeed.Feed()
        run = FakeRun(lambda args: answer(404) if "orgs/" in args[-1] else answer(200, '"u"', [event(1, "A")]))
        feed.tick(run, "me", self.CONFIG, ["A"], NOW)
        self.assertEqual(feed.snapshot(self.CONFIG)["endpoint"], "users/me/events")
        self.assertEqual(feed.snapshot(self.CONFIG)["errors"], 0)

    def test_the_wait_that_github_asks_for_wins_and_a_failure_is_counted_not_raised(self):
        feed = eventfeed.Feed()
        feed.tick(FakeRun(answer(200, '"t"', [event(1, "A")], 300)), "o", self.CONFIG, ["A"], NOW)
        self.assertEqual(feed.next_at, NOW + 300)
        broken = eventfeed.Feed()
        self.assertEqual(broken.tick(FakeRun(answer(403)), "o", self.CONFIG, ["A"], NOW), [])
        self.assertEqual(broken.snapshot(self.CONFIG)["errors"], 1)
        self.assertIn("403", broken.snapshot(self.CONFIG)["last_error"])

    def test_off_it_never_reads(self):
        run = FakeRun(answer(200, '"t"', []))
        self.assertEqual(eventfeed.Feed().tick(run, "o", {}, ["A"], NOW), [])
        self.assertEqual(run.calls, [])

    def test_the_most_repositories_marked_per_turn_is_a_setting(self):
        feed = eventfeed.Feed()
        config = {"events_feed": {"enabled": True, "max_per_tick": 1}}
        run = FakeRun(answer(200, '"t1"', [event(1, "A")]), answer(200, '"t2"', [event(4, "C"), event(3, "B"), event(2, "A")]))
        feed.tick(run, "o", config, ["A", "B", "C"], NOW)
        self.assertEqual(feed.tick(run, "o", config, ["A", "B", "C"], NOW + 70), ["C"])


SUMMARY = {"status": {"indicator": "minor", "description": "Minor Service Outage"},
           "components": [{"name": "Actions", "status": "degraded_performance"}, {"name": "Git Operations", "status": "operational"}, {"name": "Something Else", "status": "major_outage"}],
           "incidents": [{"name": "Delays in Actions", "status": "investigating", "impact": "minor", "components": [{"name": "Actions"}]},
                         {"name": "Old one", "status": "resolved", "impact": "major", "components": [{"name": "Actions"}]}]}
CALM = {"status": {"indicator": "none", "description": "All Systems Operational"}, "components": [{"name": "Actions", "status": "operational"}], "incidents": []}


class FakeOpener:
    def __init__(self, payload=None, error=None):
        self.payload, self.error, self.requests = payload, error, []

    def __call__(self, request, timeout=0):
        self.requests.append(request.full_url)
        if self.error:
            raise self.error
        return io.BytesIO(json.dumps(self.payload).encode() if not isinstance(self.payload, bytes) else self.payload)


class GitHubStatus(unittest.TestCase):
    def setUp(self):
        githubstatus.STATUS.reset()
        self.addCleanup(githubstatus.STATUS.reset)

    def test_the_summary_is_read_into_a_few_facts(self):
        info = githubstatus.parse(SUMMARY)
        self.assertEqual(info["indicator"], "minor")
        self.assertTrue(info["actions"])
        self.assertEqual(info["components"], {"Actions": "degraded_performance", "Git Operations": "operational"})
        self.assertEqual([i["name"] for i in info["incidents"]], ["Delays in Actions"])
        self.assertFalse(githubstatus.parse(CALM)["actions"])

    def test_an_incident_that_names_actions_counts_even_when_the_component_looks_fine(self):
        data = json.loads(json.dumps(SUMMARY))
        data["components"][0]["status"] = "operational"
        self.assertTrue(githubstatus.parse(data)["actions"])
        data["incidents"][0]["components"] = [{"name": "Pages"}]
        self.assertFalse(githubstatus.parse(data)["actions"])

    def test_what_is_not_a_summary_is_nothing_and_text_is_cut(self):
        for bad in (None, [], {}, {"status": "x"}, "text"):
            self.assertIsNone(githubstatus.parse(bad))
        data = json.loads(json.dumps(SUMMARY))
        data["incidents"][0]["name"] = "x\n" * 500
        self.assertLessEqual(len(githubstatus.parse(data)["incidents"][0]["name"]), 120)
        data["status"]["indicator"] = "weird"
        self.assertEqual(githubstatus.parse(data)["indicator"], "none")

    def test_the_read_asks_only_for_the_public_summary_and_a_failure_is_none(self):
        opener = FakeOpener(SUMMARY)
        self.assertTrue(githubstatus.fetch(opener)["actions"])
        self.assertEqual(opener.requests, [githubstatus.URL])
        self.assertTrue(githubstatus.URL.startswith("https://www.githubstatus.com/"))
        self.assertIsNone(githubstatus.fetch(FakeOpener(error=OSError("down"))))
        self.assertIsNone(githubstatus.fetch(FakeOpener(payload=b"not json")))

    def test_an_incident_of_actions_starts_and_ends_once(self):
        status = githubstatus.Status()
        self.assertEqual(status.update(githubstatus.parse(CALM), NOW), "")
        self.assertEqual(status.update(githubstatus.parse(SUMMARY), NOW + 10), "start")
        self.assertEqual(status.update(githubstatus.parse(SUMMARY), NOW + 20), "")
        self.assertTrue(status.incident())
        self.assertEqual(status.update(None, NOW + 30), "")      # a failed read changes nothing
        self.assertTrue(status.incident())
        self.assertEqual(status.update(githubstatus.parse(CALM), NOW + 40), "over")
        self.assertFalse(status.incident())

    def test_the_turn_reads_only_when_on_and_at_its_time(self):
        status = githubstatus.Status()
        opener = FakeOpener(SUMMARY)
        self.assertEqual(status.tick(opener, {}, NOW), "")
        self.assertEqual(opener.requests, [])
        config = {"github_status": {"enabled": True, "interval_seconds": 120}}
        self.assertEqual(status.tick(opener, config, NOW), "start")
        self.assertEqual(status.tick(opener, config, NOW + 30), "")
        self.assertEqual(len(opener.requests), 1)
        snap = status.snapshot(config, NOW + 60)
        self.assertEqual((snap["ok"], snap["indicator"], snap["actions_incident"], snap["incident_seconds"]), (True, "minor", True, 60))

    def test_the_marking_can_be_turned_off(self):
        status = githubstatus.Status()
        status.tick(FakeOpener(SUMMARY), {"github_status": {"enabled": True, "mark_reds": False}}, NOW)
        self.assertFalse(status.incident())

    def test_a_new_red_says_it_may_be_an_incident_of_github_and_is_not_hidden(self):
        before = events.summarize({})
        red = {"a2": {"red": [{"repo": "R", "workflow": "CI", "url": "u", "streak": 1, "since": "2026-01-01T00:00:00Z"}]}}
        after = events.summarize(red)
        calm = events.diff(before, after, True)
        self.assertEqual([e["kind"] for e in calm], ["red_new"])
        self.assertNotIn("possible_cause", calm[0])
        with mock.patch.object(githubstatus, "STATUS", githubstatus.Status()) as status:
            status.update(githubstatus.parse(SUMMARY), NOW)
            status.mark = True
            marked = events.diff(before, after, True)
        self.assertEqual(marked[0]["possible_cause"], "github_incident")
        self.assertIn("GitHub", marked[0]["text"])
        self.assertTrue(marked[0]["text"].startswith(calm[0]["text"]))

    def test_the_new_kinds_are_known_to_the_notifications(self):
        from github_actions_monitor.integrations import dispatcher, notifiers
        for kind in ("github_incident", "github_incident_over"):
            self.assertIn(kind, notifiers.KNOWN_EVENTS)
            self.assertIn(kind, dispatcher.FAMILIES["system"])


class Heartbeat(unittest.TestCase):
    URL = "https://hc-ping.com/abc-123"

    def setUp(self):
        heartbeat.HEARTBEAT.reset()
        patch = mock.patch.dict(os.environ, {heartbeat.ENV_NAME: self.URL})
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(heartbeat.HEARTBEAT.reset)
        saved = dict(envguard.HELD)
        self.addCleanup(lambda: (envguard.HELD.clear(), envguard.HELD.update(saved)))

    def config(self, **extra):
        return {"heartbeat": {"enabled": True, **extra}}

    def test_off_by_default_and_every_setting_is_bounded(self):
        self.assertFalse(heartbeat.settings({})["enabled"])
        self.assertEqual(heartbeat.settings({"heartbeat": {"interval_seconds": 5}})["interval_seconds"], 300)
        self.assertEqual(heartbeat.settings({"heartbeat": {"interval_seconds": 86401}})["interval_seconds"], 300)
        self.assertEqual(heartbeat.settings({"heartbeat": {"fail_suffix": "/fail"}})["fail_suffix"], "/fail")
        for bad in ("fail", "/a/b", "/FAIL", "/toolongsuffix", "?x"):
            self.assertEqual(heartbeat.settings({"heartbeat": {"fail_suffix": bad}})["fail_suffix"], "", bad)
        for bad in ("PATH", "GH_TOKEN", "MONITOR_WEBHOOK_SECRET", "lower", "A B"):
            self.assertEqual(heartbeat.settings({"heartbeat": {"url_env": bad}})["url_env"], heartbeat.ENV_NAME, bad)
        self.assertEqual(heartbeat.settings({"heartbeat": {"url_env": "MY_PING"}})["url_env"], "MY_PING")

    def test_the_address_must_be_a_plain_https_address(self):
        self.assertIsNone(heartbeat.check_url(self.URL))
        self.assertEqual(heartbeat.check_url(""), "empty")
        self.assertEqual(heartbeat.check_url("ftp://x.example/a"), "bad_url")
        self.assertEqual(heartbeat.check_url("https://u:p@x.example/a"), "credentials")
        self.assertEqual(heartbeat.check_url("http://192.168.1.5:3001/api/push/k"), "not_https")
        self.assertIsNone(heartbeat.check_url("http://192.168.1.5:3001/api/push/k", allow_private=True))
        self.assertEqual(heartbeat.check_url("https://x.example/a b"), "bad_url")
        self.assertEqual(heartbeat.check_url("https://x.example/" + "a" * 500), "bad_url")

    def test_the_ping_carries_the_version_and_the_state_and_nothing_else(self):
        where = heartbeat.target(self.config(), True, self.URL, "2.1.7")
        self.assertEqual(where, self.URL + "?msg=2.1.7%20ok")
        self.assertEqual(heartbeat.target(self.config(send_state=False), True, self.URL, "2.1.7"), self.URL)
        self.assertEqual(heartbeat.target(self.config(), True, self.URL + "?create=1", "2.1.7"), self.URL + "?create=1&msg=2.1.7%20ok")

    def test_an_unhealthy_monitor_stays_silent_unless_there_is_a_fail_address(self):
        self.assertEqual(heartbeat.target(self.config(), False, self.URL, "2.1.7"), "")
        self.assertEqual(heartbeat.target(self.config(fail_suffix="/fail"), False, self.URL, "2.1.7"), self.URL + "/fail?msg=2.1.7%20degraded")

    def test_a_turn_sends_counts_and_waits_for_the_interval(self):
        seen = []

        def opener(request, timeout=0):
            seen.append((request.full_url, request.get_method()))
            return mock.MagicMock(__enter__=lambda s: mock.MagicMock(status=200), __exit__=lambda *a: False)
        beat = heartbeat.Heartbeat()
        self.assertEqual(beat.tick(self.config(), True, "2.1.7", opener=opener, now=NOW), "sent")
        self.assertEqual(beat.tick(self.config(), True, "2.1.7", opener=opener, now=NOW + 10), "")
        self.assertEqual(beat.tick(self.config(), False, "2.1.7", opener=opener, now=NOW + 400), "skipped")
        self.assertEqual(seen, [(self.URL + "?msg=2.1.7%20ok", "GET")])
        snap = beat.snapshot(self.config())
        self.assertEqual((snap["sent"], snap["skipped"], snap["failed"], snap["address_defined"]), (1, 1, 0, True))
        self.assertNotIn("hc-ping", json.dumps(snap))

    def test_a_refused_or_failed_ping_is_counted_and_never_raises(self):
        def broken(request, timeout=0):
            raise OSError("down")
        beat = heartbeat.Heartbeat()
        self.assertEqual(beat.tick(self.config(), True, "2.1.7", opener=broken, now=NOW), "failed")
        self.assertFalse(beat.snapshot(self.config())["last_ok"])

    def test_without_a_valid_address_or_when_off_nothing_is_sent(self):
        calls = []
        opener = lambda request, timeout=0: calls.append(request)      # noqa: E731
        with mock.patch.dict(os.environ, {heartbeat.ENV_NAME: "http://x.example/a"}):
            self.assertEqual(heartbeat.Heartbeat().tick(self.config(), True, "2.1.7", opener=opener, now=NOW), "")
        with mock.patch.dict(os.environ, {heartbeat.ENV_NAME: ""}):
            self.assertEqual(heartbeat.Heartbeat().tick(self.config(), True, "2.1.7", opener=opener, now=NOW), "")
        self.assertEqual(heartbeat.Heartbeat().tick({}, True, "2.1.7", opener=opener, now=NOW), "")
        self.assertEqual(calls, [])

    def test_the_variable_is_one_of_the_secrets_of_the_monitor(self):
        self.assertIn("heartbeat.url_env", envguard.ENV_SETTINGS)
        self.assertIn(heartbeat.ENV_NAME, envguard.SECRET_NAMES)
        self.assertTrue(envguard.forbidden_name(heartbeat.ENV_NAME))


class TurnOfTheApp(unittest.TestCase):
    def setUp(self):
        eventfeed.FEED.reset()
        githubstatus.STATUS.reset()
        heartbeat.HEARTBEAT.reset()
        saved = am.STATE.get("data"), set(am.HOT_FORCED), dict(am.RUN_CACHE)
        self.addCleanup(self.restore, saved)
        am.STATE["data"] = {"repos": ["A", "B"], "paused_quota": False}
        am.HOT_FORCED.clear()

    def restore(self, saved):
        am.STATE["data"] = saved[0]
        am.HOT_FORCED.clear()
        am.HOT_FORCED.update(saved[1])
        am.RUN_CACHE.clear()
        am.RUN_CACHE.update(saved[2])
        eventfeed.FEED.reset()
        githubstatus.STATUS.reset()
        heartbeat.HEARTBEAT.reset()

    def test_nothing_happens_when_everything_is_off_or_in_the_demo(self):
        with mock.patch.object(am, "run_gh", side_effect=AssertionError("no read expected")):
            self.assertEqual(am.outside_tick({}, NOW), {"feed": [], "status": "", "heartbeat": ""})
            with mock.patch.dict(am.DEMO, {"on": True}):
                self.assertEqual(am.outside_tick({"events_feed": {"enabled": True}}, NOW)["feed"], [])

    def test_a_change_in_the_events_marks_the_repository_to_be_read_again(self):
        run = FakeRun(answer(200, '"t1"', [event(1, "A")]), answer(200, '"t2"', [event(2, "B"), event(1, "A")]))
        config = {"github_owner": "o", "events_feed": {"enabled": True, "interval_seconds": 30}}
        with mock.patch.object(am, "run_gh", run), mock.patch.object(am.toolconfig, "github_owner", return_value="o"):
            self.assertEqual(am.outside_tick(config, NOW)["feed"], [])
            am.RUN_CACHE["B"] = {"runs": [], "at": NOW}
            self.assertEqual(am.outside_tick(config, NOW + 40)["feed"], ["B"])
        self.assertIn("B", am.HOT_FORCED)
        self.assertEqual(am.RUN_CACHE["B"]["at"], 0)

    def test_a_spent_allowance_is_not_asked(self):
        am.STATE["data"]["paused_quota"] = True
        with mock.patch.object(am, "run_gh", side_effect=AssertionError("no read expected")):
            self.assertEqual(am.outside_tick({"events_feed": {"enabled": True}}, NOW)["feed"], [])

    def test_the_status_turn_announces_the_start_and_the_end(self):
        config = {"github_status": {"enabled": True, "interval_seconds": 60}}
        told = []
        with mock.patch.object(githubstatus, "fetch", side_effect=[githubstatus.parse(SUMMARY), githubstatus.parse(CALM)]), \
                mock.patch.object(am, "announce_github_status", side_effect=lambda transition, cfg: told.append(transition)):
            self.assertEqual(am.outside_tick(config, NOW)["status"], "start")
            self.assertEqual(am.outside_tick(config, NOW + 100)["status"], "over")
        self.assertEqual(told, ["start", "over"])

    def test_the_announcement_has_its_text_and_goes_to_the_notices(self):
        githubstatus.STATUS.update(githubstatus.parse(SUMMARY), NOW)
        with mock.patch("github_actions_monitor.integrations.notifiers.notify") as notify, mock.patch("builtins.print") as printed:
            am.announce_github_status("start", {})
            am.announce_github_status("over", {})
        kinds = [call.args[1]["kind"] for call in notify.call_args_list]
        self.assertEqual(kinds, ["github_incident", "github_incident_over"])
        self.assertIn("Delays in Actions", printed.call_args_list[0].args[0])

    def test_the_status_of_the_receiver_and_the_health_carry_the_new_figures(self):
        self.assertIn("feed", am.webhook_status({}))
        self.assertIn("polls", am.webhook_status({})["feed"])
        with mock.patch.dict(am.DEMO, {"on": True}):
            self.assertIn("heartbeat", am.health_payload())


if __name__ == "__main__":
    unittest.main()
