# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The webhook without a public address (`gh webhook forward` over a WebSocket, supervised) and the recovery of the deliveries a switched-off computer missed (asking GitHub to send them again). Every
process and every call of GitHub is a fake: nothing is started and nothing reaches the network."""
import io
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import redeliver  # noqa: E402
from github_actions_monitor.security import webhook, wsforward  # noqa: E402

NOW = 1_800_000_000.0
STAMP = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - 3600))


class FakeProc:
    def __init__(self, lines):
        self.stdout = io.StringIO("".join(line + "\n" for line in lines))
        self.terminated = False

    def wait(self):
        return 0

    def terminate(self):
        self.terminated = True


class Settings(unittest.TestCase):
    def test_the_transport_is_http_unless_it_says_websocket_and_nothing_is_listed_by_default(self):
        self.assertEqual(wsforward.settings({})["transport"], "http")
        self.assertEqual(wsforward.settings({"webhook": {"transport": "carrier"}})["transport"], "http")
        self.assertEqual(wsforward.settings({"webhook": {"transport": "websocket"}})["targets"], [])

    def test_targets_are_plain_names_without_repeats_and_within_the_cap(self):
        config = {"webhook": {"transport": "websocket", "ws_targets": ["o/r", "o/r", "org", "../x", "o/r;rm", 5, "a/b/c", " p/q "], "ws_max_targets": 3}}
        self.assertEqual(wsforward.settings(config)["targets"], ["o/r", "org", "p/q"])
        self.assertEqual(wsforward.settings({"webhook": {"ws_max_targets": 0}})["max_targets"], 10)
        self.assertEqual(wsforward.settings({"webhook": {"ws_max_targets": 51}})["max_targets"], 10)
        self.assertFalse(wsforward.settings({"webhook": {"ws_cleanup": "yes"}})["cleanup"])

    def test_the_settings_of_the_page_check_the_same_shapes(self):
        self.assertTrue(settings_api.check_value("webhook.ws_targets", ["o/r", "org"])[0])
        for bad in (["../x"], ["a/b/c"], ["o/r;rm"], "o/r", [5]):
            self.assertFalse(settings_api.check_value("webhook.ws_targets", bad)[0], bad)
        self.assertTrue(settings_api.check_value("webhook.redeliver.hooks", ["repo:o/r#12", "org:o#7"])[0])
        for bad in (["repo:o/r"], ["x#1"], ["repo:o/r#abc"]):
            self.assertFalse(settings_api.check_value("webhook.redeliver.hooks", bad)[0], bad)
        self.assertFalse(settings_api.check_value("webhook.transport", "carrier")[0])
        self.assertTrue(settings_api.check_value("webhook.transport", "websocket")[0])
        self.assertEqual(redeliver.settings({"webhook": {"redeliver": {"hooks": ["repo:o/r#12", "org:o#7", "repo:o/r", "x#1", "repo:o/r#abc"]}}})["hooks"], ["repo:o/r#12", "org:o#7"])


class Forwarding(unittest.TestCase):
    CONFIG = {"webhook": {"transport": "websocket", "ws_targets": ["o/r", "org"]}}

    def setUp(self):
        wsforward.FORWARDERS.reset()
        self.addCleanup(wsforward.FORWARDERS.reset)

    def test_the_command_forwards_a_repository_or_an_organization_to_the_local_receiver(self):
        repo = wsforward.command("o/r", "http://127.0.0.1:8765/api/webhook", "S" * 8)
        self.assertEqual(repo[:5], ["gh", "webhook", "forward", "--repo", "o/r"])
        self.assertIn("--url", repo)
        self.assertEqual(repo[repo.index("--url") + 1], "http://127.0.0.1:8765/api/webhook")
        org = wsforward.command("org", "http://127.0.0.1:8765/api/webhook", "S")
        self.assertEqual(org[3:5], ["--org", "org"])
        self.assertIn("workflow_run", org[org.index("--events") + 1])

    def test_nothing_starts_with_the_http_transport_or_without_targets(self):
        spawned = []
        self.assertEqual(wsforward.FORWARDERS.start({}, 8765, spawn=lambda c: spawned.append(c), threaded=False), [])
        self.assertEqual(wsforward.FORWARDERS.start({"webhook": {"transport": "websocket"}}, 8765, spawn=lambda c: spawned.append(c), threaded=False), [])
        self.assertEqual(spawned, [])
        self.assertEqual(wsforward.FORWARDERS.local_secret(), "")

    def test_a_forwarder_that_forwards_is_seen_and_one_that_ends_is_started_again_with_a_longer_wait(self):
        waits, commands = [], []

        def spawn(command):
            commands.append(command)
            if len(commands) >= 4:
                wsforward.FORWARDERS.stopping = True
            return FakeProc(["Forwarding Webhook events from GitHub..."] if command[4] == "o/r" else ["Error: HTTP 403: Must have admin rights to Repository (https://api.github.com)"])
        wsforward.FORWARDERS.start({"webhook": {"transport": "websocket", "ws_targets": ["o/r"]}}, 8765, spawn=spawn, sleep=waits.append, threaded=False)
        row = wsforward.FORWARDERS.snapshot(self.CONFIG)["targets"][0]
        self.assertEqual(row["target"], "o/r")
        self.assertIn(row["state"], ("stopped", "forwarding", "restarting"))
        self.assertEqual(waits[:3], [5, 10, 20])
        self.assertGreaterEqual(row["restarts"], 3)

    def test_a_token_that_may_not_manage_hooks_is_seen_as_forbidden_and_asked_less_often(self):
        waits, commands = [], []

        def spawn(command):
            commands.append(command)
            wsforward.FORWARDERS.stopping = len(commands) >= 2
            return FakeProc(["HTTP 403: Resource not accessible by personal access token (https://api.github.com/repos/o/r/hooks)"])
        wsforward.FORWARDERS.start({"webhook": {"transport": "websocket", "ws_targets": ["org"]}}, 8765, spawn=spawn, sleep=waits.append, threaded=False)
        self.assertEqual(waits[0], 30)
        self.assertEqual(wsforward.classify("HTTP 403: nope"), "forbidden")
        self.assertEqual(wsforward.classify("Forwarding Webhook events from GitHub..."), "forwarding")
        self.assertEqual(wsforward.classify("something else"), "")

    def test_the_secret_of_the_forwarder_is_made_at_start_and_is_in_the_command_not_in_the_status(self):
        seen = []

        def spawn(command):
            seen.append(command)
            wsforward.FORWARDERS.stopping = True
            return FakeProc([])
        wsforward.FORWARDERS.start({"webhook": {"transport": "websocket", "ws_targets": ["o/r"]}}, 8765, spawn=spawn, sleep=lambda s: None, threaded=False)
        secret = wsforward.FORWARDERS.local_secret()
        self.assertEqual(len(secret), 64)
        self.assertEqual(seen[0][seen[0].index("--secret") + 1], secret)
        self.assertNotIn(secret, json.dumps(wsforward.FORWARDERS.snapshot(self.CONFIG)))

    def test_a_line_of_output_is_cut_and_cleaned_before_it_is_kept(self):
        line = wsforward.short("error\x00 token ghp_" + "A" * 36 + " " + "x" * 400)
        self.assertLessEqual(len(line), 160)
        self.assertNotIn("ghp_" + "A" * 36, line)
        self.assertNotIn("\x00", line)

    def test_stopping_ends_the_processes(self):
        proc = FakeProc([])
        wsforward.FORWARDERS.procs["o/r"] = proc
        wsforward.FORWARDERS.stop()
        self.assertTrue(proc.terminated)

    def test_a_process_that_cannot_start_is_noted_and_tried_again(self):
        waits = []

        def spawn(command):
            wsforward.FORWARDERS.stopping = True
            raise OSError("gh is not installed")
        wsforward.FORWARDERS.start({"webhook": {"transport": "websocket", "ws_targets": ["o/r"]}}, 8765, spawn=spawn, sleep=waits.append, threaded=False)
        self.assertIn("gh is not installed", wsforward.FORWARDERS.snapshot(self.CONFIG)["targets"][0]["last"])


class TheTemporaryHooks(unittest.TestCase):
    HOOKS = [{"id": 11, "active": True, "config": {"url": "https://webhook-forwarder.github.com/hook"}}, {"id": 12, "active": False, "config": {"url": "https://webhook-forwarder.github.com/hook"}},
             {"id": 13, "active": True, "config": {"url": "https://ci.example.org/hook"}}, {"id": "x"}, "junk"]

    def test_only_the_hooks_of_the_forwarder_are_listed(self):
        run = lambda args: (0, json.dumps(self.HOOKS), "")      # noqa: E731
        self.assertEqual(wsforward.orphans(run, "o/r"), [(11, True), (12, False)])
        self.assertEqual(wsforward.orphans(lambda args: (1, "", "boom"), "o/r"), [])
        self.assertEqual(wsforward.orphans(lambda args: (0, "not json", ""), "o/r"), [])

    def test_the_cleanup_deletes_only_what_the_forwarder_made_and_says_how_many(self):
        calls = []

        def run(args):
            calls.append(args)
            return (0, json.dumps(self.HOOKS), "") if args[0] == "api" and "-X" not in args else (0, "", "")
        self.assertEqual(wsforward.cleanup(run, ["o/r", "org"]), 4)
        deletes = [c[-1] for c in calls if "-X" in c]
        self.assertEqual(deletes, ["repos/o/r/hooks/11", "repos/o/r/hooks/12", "orgs/org/hooks/11", "orgs/org/hooks/12"])


class TheReceiverAcceptsTheLocalSecret(unittest.TestCase):
    SECRET = "s" * 40

    def setUp(self):
        webhook.reset()
        patch = mock.patch.dict(os.environ, {webhook.SECRET_ENV: self.SECRET})
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(lambda: webhook.set_local_secret(""))

    def deliver(self, secret):
        self.count = getattr(self, "count", 0) + 1
        body = json.dumps({"repository": {"name": "R", "full_name": "o/R"}, "n": self.count}).encode()
        head = {"X-GitHub-Event": "push", "X-GitHub-Delivery": f"00000000-0000-0000-0000-{self.count:012d}", "X-Hub-Signature-256": webhook.sign(secret, body)}
        return webhook.handle({"webhook": {"enabled": True, "allowed_owners": ["o"]}}, body, head, ["R"])[0]

    def test_the_secret_of_the_forwarder_is_accepted_only_once_it_is_set_and_the_shared_one_always(self):
        local = "f" * 64
        self.assertEqual(self.deliver(local), 401)
        webhook.set_local_secret(local)
        self.assertEqual(self.deliver(local), 200)
        self.assertEqual(self.deliver(self.SECRET), 200)
        self.assertEqual(self.deliver("z" * 64), 401)
        webhook.set_local_secret("")
        self.assertEqual(self.deliver(local), 401)


def hook_item(number, guid, code, when=STAMP, redelivery=False):
    return {"id": number, "guid": guid, "delivered_at": when, "status_code": code, "redelivery": redelivery, "event": "push"}


class Recovery(unittest.TestCase):
    GUIDS = [f"00000000-0000-0000-0000-{n:012d}" for n in range(1, 8)]
    CONFIG = {"webhook": {"redeliver": {"enabled": True, "hooks": ["repo:o/r#5"], "max_per_run": 2}}}

    def setUp(self):
        self.rec = redeliver.Recovery()

    def test_a_delivery_is_lost_when_no_attempt_of_it_was_answered_2xx(self):
        g = self.GUIDS
        items = [hook_item(1, g[0], 200), hook_item(2, g[1], 502), hook_item(3, g[1], 200, redelivery=True), hook_item(4, g[2], 0), hook_item(5, g[2], 500, redelivery=True), hook_item(6, g[3], 404)]
        found = dict(redeliver.lost(items, NOW, 24))
        self.assertEqual(found, {g[2]: 5, g[3]: 6})      # the newest attempt of each lost one; g[0] and g[1] arrived

    def test_old_deliveries_and_odd_rows_are_left_alone(self):
        old = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - 30 * 3600))
        items = [hook_item(1, self.GUIDS[0], 500, old), {"id": "x"}, "junk", {"id": 3, "guid": "bad guid", "status_code": 500}, None]
        self.assertEqual(redeliver.lost(items, NOW, 24), [])
        self.assertEqual(redeliver.lost(None, NOW, 24), [])
        self.assertEqual(len(redeliver.lost(items, NOW, 72)), 1)

    def test_it_asks_for_the_lost_ones_with_a_limit_and_not_for_the_same_one_twice(self):
        g = self.GUIDS
        calls = []

        def run(args):
            calls.append(args)
            return (0, json.dumps([hook_item(i + 1, g[i], 502) for i in range(4)]), "") if "-X" not in args else (0, "", "")
        self.assertEqual(self.rec.run(self.CONFIG, run, NOW), 2)
        posts = [c[-1] for c in calls if "-X" in c]
        self.assertEqual(len(posts), 2)
        self.assertTrue(all(p.startswith("repos/o/r/hooks/5/deliveries/") and p.endswith("/attempts") for p in posts))
        calls.clear()
        self.assertEqual(self.rec.run(self.CONFIG, run, NOW + 100), 0, "its turn comes every interval_minutes")
        self.assertEqual(self.rec.run(self.CONFIG, run, NOW + 3600 + 1), 2)
        self.assertEqual(sum(1 for c in calls if "-X" in c), 2)
        self.assertEqual(sorted(r["asks"] for r in self.rec.state.values()), [1, 1, 1, 1], "what was never asked for goes before what was asked once")

    def test_a_delivery_asked_for_eight_times_is_dead_and_never_asked_again(self):
        guid = self.GUIDS[0]
        run = lambda args: (0, json.dumps([hook_item(1, guid, 502)]), "") if "-X" not in args else (0, "", "")      # noqa: E731
        config = {"webhook": {"redeliver": {"enabled": True, "hooks": ["org:o#5"], "interval_minutes": 5}}}
        asked = 0
        now = NOW
        for _ in range(12):
            asked += self.rec.run(config, run, now)
            now += 3600
        self.assertEqual(asked, redeliver.MAX_ASKS)
        self.assertEqual(self.rec.state[guid]["state"], "dead")
        self.assertEqual(self.rec.snapshot(config)["dead"], 1)

    def test_nothing_is_asked_when_off_or_without_hooks_and_a_failure_is_counted(self):
        run = mock.Mock(side_effect=AssertionError("no call expected"))
        self.assertEqual(self.rec.run({}, run, NOW), 0)
        self.assertEqual(self.rec.run({"webhook": {"redeliver": {"enabled": True}}}, run, NOW), 0)
        broken = redeliver.Recovery()
        self.assertEqual(broken.run(self.CONFIG, lambda args: (1, "", "HTTP 404"), NOW), 0)
        self.assertEqual(broken.snapshot(self.CONFIG)["errors"], 1)
        self.assertIn("404", broken.snapshot(self.CONFIG)["last_error"])

    def test_the_memory_survives_a_restart_and_a_damaged_file_is_an_empty_memory(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "redelivered.json"
            first = redeliver.Recovery(path)
            first.asked(self.GUIDS[0], NOW)
            self.assertTrue(first.save())
            self.assertEqual(oct(path.stat().st_mode & 0o777)[-3:] in ("600", "666", "644", "777"), True)
            again = redeliver.Recovery()
            self.assertEqual(again.load(path), 1)
            self.assertFalse(again.due(self.GUIDS[0], NOW + 1), "it was asked a moment ago")
            self.assertTrue(again.due(self.GUIDS[0], NOW + 10))
            path.write_text("{ not json", encoding="utf-8")
            self.assertEqual(redeliver.Recovery().load(path), 0)
            path.write_text(json.dumps({"bad guid": {"asks": 1, "state": "asked"}, self.GUIDS[1]: {"asks": 99, "state": "asked", "next_at": 5}, self.GUIDS[2]: "x"}), encoding="utf-8")
            loaded = redeliver.Recovery()
            self.assertEqual(loaded.load(path), 1)
            self.assertEqual(loaded.state[self.GUIDS[1]]["asks"], redeliver.MAX_ASKS)

    def test_the_settings_are_bounded(self):
        cfg = redeliver.settings({"webhook": {"redeliver": {"max_per_run": 0, "max_age_hours": 73, "interval_minutes": 4}}})
        self.assertEqual((cfg["max_per_run"], cfg["max_age_hours"], cfg["interval_minutes"], cfg["enabled"], cfg["hooks"]), (20, 24, 60, False, []))
        self.assertEqual(redeliver.base_of("repo:o/r#5"), "repos/o/r/hooks/5")
        self.assertEqual(redeliver.base_of("org:o#9"), "orgs/o/hooks/9")


class InTheApp(unittest.TestCase):
    def test_the_status_of_the_receiver_carries_the_forwarders_and_the_recovery(self):
        status = am.webhook_status({})
        self.assertIn("forwarders", status)
        self.assertIn("redelivery", status)

    def test_asking_again_by_hand_works_even_when_the_schedule_is_off(self):
        calls = []
        config = {"webhook": {"redeliver": {"enabled": False, "hooks": ["repo:o/r#5"]}}}
        run = lambda args: (calls.append(args) or (0, json.dumps([hook_item(1, "00000000-0000-0000-0000-000000000009", 502)]), "")) if "-X" not in args else (calls.append(args) or (0, "", ""))      # noqa: E731
        with mock.patch.object(am, "run_gh", lambda args, timeout=40: run(args)):
            answer = am.webhook_redeliver_now(config)
        self.assertEqual(answer["asked"], 1)
        self.assertEqual(sum(1 for c in calls if "-X" in c), 1)


if __name__ == "__main__":
    unittest.main()
