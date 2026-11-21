# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The receiver of the webhook under stress: the limit of the body is a setting and is counted, hostile and odd deliveries never break it, the state only moves forward whatever the order of the deliveries,
a full queue answers 503 and forgets the delivery, /readyz names what holds the monitor back, a run that never ended is reconciled, and the Teams channel always sends a Content-Length. No network."""
import http.server
import itertools
import json
import os
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.integrations import channels  # noqa: E402
from github_actions_monitor.security import webhook  # noqa: E402

SECRET = "s" * 40
CONFIG = {"webhook": {"enabled": True, "allowed_owners": ["o"], "reject_stale": False}}
COUNTER = itertools.count(1)


def delivery():
    return f"00000000-0000-0000-0000-{next(COUNTER):012d}"


def run_body(status="in_progress", conclusion=None, run_id=77, repo="R", attempt=1):
    return json.dumps({"repository": {"name": repo, "full_name": "o/" + repo},
                       "workflow_run": {"id": run_id, "name": "CI", "path": ".github/workflows/ci.yml", "status": status, "conclusion": conclusion, "head_branch": "main", "head_sha": "a" * 40,
                                        "run_attempt": attempt, "event": "push", "created_at": "2026-01-01T00:00:00Z", "run_started_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:05:00Z",
                                        "html_url": f"https://github.com/o/{repo}/actions/runs/{run_id}"}}).encode()


def headers(body, event="workflow_run", ident=None, sign=True):
    out = {"X-GitHub-Event": event, "X-GitHub-Delivery": ident or delivery()}
    if sign:
        out["X-Hub-Signature-256"] = webhook.sign(SECRET, body)
    return out


class Base(unittest.TestCase):
    def setUp(self):
        webhook.reset()
        patch = mock.patch.dict(os.environ, {webhook.SECRET_ENV: SECRET})
        patch.start()
        self.addCleanup(patch.stop)
        saved = dict(am.WEBHOOK_STATS), list(am.LIVE_EVENTS), dict(am.RUN_CACHE), set(am.HOT_FORCED), am.STATE.get("data"), am.LIVE_TOTAL[0]
        self.addCleanup(self.restore, saved)
        for key in am.WEBHOOK_STATS:
            am.WEBHOOK_STATS[key] = 0 if key != "last_at" else None
        am.LIVE_EVENTS.clear()
        am.RUN_CACHE.clear()
        am.HOT_FORCED.clear()
        am.STATE["data"] = {"repos": ["R"]}
        webhook.INBOX.worker = False

    def restore(self, saved):
        stats, events, cache, hot, data, total = saved
        am.WEBHOOK_STATS.update(stats)
        am.LIVE_EVENTS[:] = events
        am.RUN_CACHE.clear()
        am.RUN_CACHE.update(cache)
        am.HOT_FORCED.clear()
        am.HOT_FORCED.update(hot)
        am.STATE["data"] = data
        am.LIVE_TOTAL[0] = total
        webhook.INBOX.worker = False
        webhook.reset()


class BodyLimit(Base):
    def test_the_limit_is_a_setting_with_a_default_of_one_mebibyte_and_a_ceiling_of_the_one_of_github(self):
        self.assertEqual(webhook.guard_settings({})["max_body"], 1024 * 1024)
        self.assertEqual(webhook.guard_settings({"webhook": {"max_body_kb": 64}})["max_body"], 64 * 1024)
        self.assertEqual(webhook.guard_settings({"webhook": {"max_body_kb": 25600}})["max_body"], 25600 * 1024)
        for bad in (0, -1, 25601, "big", True, None, 1.5):
            self.assertEqual(webhook.guard_settings({"webhook": {"max_body_kb": bad}})["max_body"], 1024 * 1024, bad)

    def test_a_body_over_the_limit_gets_413_and_one_under_it_goes_on(self):
        config = {"webhook": {"enabled": True, "allowed_owners": ["o"], "reject_stale": False, "max_body_kb": 2}}
        big = run_body() + b" " * 3000
        self.assertEqual(webhook.handle(config, big, headers(big), ["R"])[0], 413)
        small = run_body()
        self.assertEqual(webhook.handle(config, small, headers(small), ["R"])[0], 200)

    def test_a_declared_size_over_the_limit_answers_413_without_a_body_to_read(self):
        code, answer, repo = webhook.handle(CONFIG, b"", {}, ["R"], size=webhook.MAX_BODY + 1)
        self.assertEqual((code, repo), (413, None))
        self.assertFalse(answer["ok"])
        self.assertEqual(webhook.handle({}, b"", {}, ["R"], size=10 ** 9)[0], 404)      # off: nothing is said, whatever the size

    def test_the_413_is_counted_apart_and_in_the_refused_box(self):
        am.webhook_count(413)
        am.webhook_count(413)
        self.assertEqual((am.WEBHOOK_STATS["too_big"], am.WEBHOOK_STATS["refused"]), (2, 2))

    def test_the_receiver_answers_413_through_the_whole_path(self):
        code, answer = am.webhook_receive(CONFIG, b"", {}, None, size=webhook.MAX_BODY + 5)
        self.assertEqual(code, 413)
        self.assertEqual(am.WEBHOOK_STATS["too_big"], 1)


class HostileCorpus(Base):
    """What GitHub, a tunnel or a person with the secret can send: nothing of it may raise or wait."""
    CASES = [b"", b"null", b"[]", b"0", b'"text"', b"{", b"{}", b'{"repository": null}', b'{"repository": []}', b'{"repository": {"name": 5}}', b'{"repository": {"name": null, "full_name": null}}',
             b'{"repository": {"name": "R"}}', b'{"repository": {"name": "R", "full_name": 7}}', b'{"repository": {"name": "R", "full_name": "o/Other"}}',
             b'{"repository": {"name": "R", "full_name": "evil/R"}}', b'{"repository": {"name": "' + b"R" * 5000 + b'", "full_name": "o/R"}}', b'{"workflow_run": {}, "repository": {"name": "R", "full_name": "o/R"}}',
             b'{"workflow_run": null, "repository": {"name": "R", "full_name": "o/R"}}', b'{"workflow_job": [], "repository": {"name": "R", "full_name": "o/R"}}',
             b'{"workflow_run": {"id": "x"}, "repository": {"name": "R", "full_name": "o/R"}}', b"\xff\xfe\x00bad", b'{"a":' * 200 + b"1" + b"}" * 200]

    def test_every_odd_body_with_a_good_signature_is_answered_with_a_code_and_never_raises(self):
        for event in ("workflow_run", "workflow_job", "check_run", "push", "ping", "unknown_event", "", None):
            for body in self.CASES:
                head = headers(body, event=event) if event is not None else {k: v for k, v in headers(body).items() if k != "X-GitHub-Event"}
                code, answer, repo = webhook.handle(CONFIG, body, head, ["R"])
                self.assertIn(code, (200, 202, 400), (event, body[:40]))
                self.assertIsInstance(answer, dict)
                if code == 200:
                    self.assertIn(repo, (None, "R"))

    def test_parsing_an_odd_event_gives_nothing_and_never_raises(self):
        for event in ("workflow_run", "workflow_job"):
            for body in self.CASES:
                self.assertIsNone(webhook.parse_event(event, body)) if body in (b"", b"null", b"[]", b"0", b"{", b"{}", b'"text"') else webhook.parse_event(event, body)

    def test_a_missing_or_wrong_signature_and_a_missing_delivery_id_are_refused(self):
        body = run_body()
        self.assertEqual(webhook.handle(CONFIG, body, headers(body, sign=False), ["R"])[0], 401)
        self.assertEqual(webhook.handle(CONFIG, body, {**headers(body), "X-Hub-Signature-256": "sha256=" + "0" * 64}, ["R"])[0], 401)
        self.assertEqual(webhook.handle(CONFIG, body, {k: v for k, v in headers(body).items() if k != "X-GitHub-Delivery"}, ["R"])[0], 400)
        self.assertEqual(webhook.handle(CONFIG, body, headers(body, ident="x" * 300), ["R"])[0], 400)

    def test_the_same_delivery_twice_is_answered_and_not_acted_on(self):
        body = run_body()
        head = headers(body)
        self.assertEqual(webhook.handle(CONFIG, body, head, ["R"])[0], 200)
        code, answer, repo = webhook.handle(CONFIG, body, head, ["R"])
        self.assertEqual((code, answer.get("duplicate"), repo), (202, True, None))

    def test_a_signed_body_with_a_huge_field_is_cut_before_it_reaches_the_live_list(self):
        record = webhook.parse_event("workflow_run", json.dumps({"repository": {"name": "R", "full_name": "o/R"}, "workflow_run": {"id": 1, "name": "N" * 5000, "head_branch": "b" * 5000,
                                                                                                                              "status": "completed", "conclusion": "success"}}).encode())
        self.assertLessEqual(len(record["workflow"]), 100)
        self.assertLessEqual(len(record["branch"]), 100)


class Monotonic(Base):
    ORDER = ("queued", "in_progress", "completed")

    def feed(self, statuses, seeded=False):
        am.RUN_CACHE["R"] = {"runs": [], "at": time.time()}
        for status in statuses:
            body = run_body(status, "success" if status == "completed" else None)
            record = webhook.parse_event("workflow_run", body)
            am.apply_live_event(record, {})
        return am.RUN_CACHE["R"]["runs"]

    def test_every_order_of_the_three_states_ends_completed(self):
        for perm in itertools.permutations(self.ORDER):
            webhook.reset()
            am.WEBHOOK_STATS["out_of_order"] = 0
            runs = self.feed(perm)
            self.assertEqual([r["status"] for r in runs], ["completed"], perm)
            self.assertEqual(runs[0]["conclusion"], "success", perm)

    def test_every_sequence_with_repeats_never_goes_back(self):
        for length in (3, 4):
            for seq in itertools.product(self.ORDER, repeat=length):
                webhook.reset()
                runs = self.feed(seq)
                best = max(self.ORDER.index(s) for s in seq)
                self.assertEqual(runs[0]["status"], self.ORDER[best], seq)

    def test_a_late_event_is_counted_and_leaves_no_trace_in_the_live_list(self):
        self.feed(["completed"])
        held = len(am.LIVE_EVENTS)
        self.feed_more("in_progress")
        self.assertEqual(am.WEBHOOK_STATS["out_of_order"], 1)
        self.assertEqual(len(am.LIVE_EVENTS), held)

    def feed_more(self, status):
        am.apply_live_event(webhook.parse_event("workflow_run", run_body(status)), {})

    def test_what_the_cycle_already_read_counts_as_known(self):
        am.RUN_CACHE["R"] = {"runs": [{"id": 77, "status": "completed", "conclusion": "failure", "started": "2026-01-01T00:00:00Z"}], "at": time.time()}
        self.feed_more("in_progress")
        self.assertEqual(am.RUN_CACHE["R"]["runs"][0]["status"], "completed")
        self.assertEqual(am.WEBHOOK_STATS["out_of_order"], 1)

    def test_a_new_attempt_of_the_same_run_starts_again(self):
        self.feed(["completed"])
        am.apply_live_event(webhook.parse_event("workflow_run", run_body("queued", attempt=2)), {})
        self.assertEqual(am.WEBHOOK_STATS["out_of_order"], 0)

    def test_the_memory_of_the_order_is_bounded(self):
        for number in range(webhook.ORDER_MAX + 50):
            webhook.is_late({"event": "workflow_run", "repo": "R", "run_id": number, "status": "queued"})
        self.assertLessEqual(len(webhook._order), webhook.ORDER_MAX)


class Queue(Base):
    def setUp(self):
        super().setUp()
        webhook.INBOX.worker = True      # a worker is "there": nobody takes the jobs, so the queue fills
        self.config = {"webhook": {"enabled": True, "allowed_owners": ["o"], "reject_stale": False, "queue_max": 2}}

    def post(self, body=None):
        body = body or run_body(run_id=next(COUNTER))
        head = headers(body)
        return am.webhook_receive(self.config, body, head, None), body, head

    def test_a_full_queue_answers_503_and_never_drops_in_silence(self):
        (a, _), _, _ = self.post()
        (b, _), _, _ = self.post()
        (c, answer), _, _ = self.post()
        self.assertEqual((a, b, c), (200, 200, 503))
        self.assertEqual(answer["error"], "queue_full")
        self.assertEqual((am.WEBHOOK_STATS["queue_full"], am.WEBHOOK_STATS["accepted"]), (1, 2))
        self.assertEqual(webhook.INBOX.snapshot(self.config)["depth"], 2)
        self.assertEqual(am.LIVE_EVENTS, [])      # nothing was applied yet: the worker has not run

    def test_the_resend_of_a_refused_delivery_is_accepted_and_not_taken_for_a_duplicate(self):
        self.post()
        self.post()
        (code, _), body, head = self.post()
        self.assertEqual(code, 503)
        while webhook.INBOX.depth():
            webhook.INBOX.take(0)()
        self.assertEqual(am.webhook_receive(self.config, body, head, None)[0], 200)

    def test_the_worker_applies_what_was_queued_in_order(self):
        for number in (1, 2):
            self.post(run_body("queued", run_id=900 + number))
        while webhook.INBOX.depth():
            webhook.INBOX.take(0)()
        self.assertEqual([e["run_id"] for e in am.LIVE_EVENTS], [901, 902])

    def test_without_a_worker_the_event_is_applied_at_once(self):
        webhook.INBOX.worker = False
        code, _ = am.webhook_receive(self.config, *self.pair())
        self.assertEqual(code, 200)
        self.assertEqual(len(am.LIVE_EVENTS), 1)

    def pair(self):
        body = run_body("queued", run_id=next(COUNTER))
        return body, headers(body), None

    def test_the_queue_depth_is_in_the_status_and_the_setting_is_bounded(self):
        self.post()
        self.assertEqual(am.webhook_status(self.config)["queue"]["depth"], 1)
        self.assertEqual(webhook.guard_settings({"webhook": {"queue_max": 0}})["queue_max"], 500)
        self.assertEqual(webhook.guard_settings({"webhook": {"queue_max": 10001}})["queue_max"], 500)
        self.assertEqual(webhook.guard_settings({"webhook": {"queue_max": 10000}})["queue_max"], 10000)

    def test_a_job_that_raises_is_counted_and_the_next_one_still_runs(self):
        def boom():
            raise RuntimeError("no")
        ran = []
        webhook.INBOX.put(boom, 5)
        webhook.INBOX.put(lambda: ran.append(1), 5)
        self.assertFalse(am.webhook_apply(webhook.INBOX.take(0)))
        self.assertTrue(am.webhook_apply(webhook.INBOX.take(0)))
        self.assertEqual((ran, webhook.INBOX.stats["failed"], webhook.INBOX.stats["done"]), ([1], 1, 1))


class Readiness(Base):
    def setUp(self):
        super().setUp()
        patch = mock.patch.dict(am.DEMO, {"on": True})      # the demo has no refresh loop to judge
        patch.start()
        self.addCleanup(patch.stop)

    def test_ready_when_loaded_and_the_queue_has_room(self):
        payload, code = am.readiness()
        self.assertEqual(code, 200, payload)
        self.assertTrue(payload["ready"])
        self.assertEqual(set(payload["checks"]), {"loaded", "cycle", "store", "queue"})
        self.assertTrue(all(payload["checks"].values()))

    def test_not_ready_before_the_first_read(self):
        am.STATE["data"] = None
        payload, code = am.readiness()
        self.assertEqual(code, 503)
        self.assertFalse(payload["checks"]["loaded"])

    def test_not_ready_when_the_queue_is_full_and_it_says_which_check(self):
        with mock.patch.object(am, "LIVE_CONFIG", {"webhook": {"queue_max": 1}}):
            webhook.INBOX.put(lambda: None, 5)
            payload, code = am.readiness()
        self.assertEqual(code, 503)
        self.assertEqual([k for k, v in payload["checks"].items() if not v], ["queue"])
        self.assertEqual(payload["queue"], {"depth": 1, "max": 1})


class Ghosts(Base):
    def test_a_run_open_for_longer_than_the_limit_is_reconciled_and_a_finished_one_is_not(self):
        config = {"webhook": {"stale_after_h": 2}}
        now = 1_800_000_000.0
        webhook.note_open(webhook.parse_event("workflow_run", run_body("in_progress", run_id=1)), now)
        webhook.note_open(webhook.parse_event("workflow_run", run_body("queued", run_id=2)), now)
        webhook.note_open(webhook.parse_event("workflow_run", run_body("completed", "success", run_id=2)), now + 10)
        self.assertEqual(webhook.open_count(), 1)
        self.assertEqual(webhook.stale_open(config, now + 3600), [])
        self.assertEqual(webhook.stale_open(config, now + 3 * 3600), [("R", 1)])
        self.assertEqual((webhook.open_count(), webhook.stale_total()), (0, 1))
        self.assertEqual(webhook.stale_open(config, now + 9 * 3600), [])      # it is forgotten once handed over

    def test_the_sweep_marks_the_run_and_asks_for_a_read_of_its_repository(self):
        now = time.time()
        am.RUN_CACHE["R"] = {"runs": [{"id": 1, "status": "in_progress"}, {"id": 5, "status": "completed"}], "at": now}
        webhook.note_open(webhook.parse_event("workflow_run", run_body("in_progress", run_id=1)), now - 7 * 3600)
        self.assertEqual(am.webhook_sweep({}), 1)
        self.assertTrue(am.RUN_CACHE["R"]["runs"][0].get("stale"))
        self.assertNotIn("stale", am.RUN_CACHE["R"]["runs"][1])
        self.assertEqual(am.RUN_CACHE["R"]["at"], 0)
        self.assertIn("R", am.HOT_FORCED)
        self.assertEqual(am.WEBHOOK_STATS["stale"], 1)

    def test_the_limit_is_a_bounded_setting(self):
        self.assertEqual(webhook.guard_settings({})["stale_after_h"], 6)
        self.assertEqual(webhook.guard_settings({"webhook": {"stale_after_h": 0}})["stale_after_h"], 6)
        self.assertEqual(webhook.guard_settings({"webhook": {"stale_after_h": 169}})["stale_after_h"], 6)
        self.assertEqual(webhook.guard_settings({"webhook": {"stale_after_h": 168}})["stale_after_h"], 168)

    def test_a_late_open_event_does_not_open_a_finished_run_again(self):
        self.assertFalse(webhook.is_late(webhook.parse_event("workflow_run", run_body("completed", "success", run_id=3))))
        record = webhook.parse_event("workflow_run", run_body("in_progress", run_id=3))
        self.assertTrue(webhook.is_late(record))
        self.assertEqual(webhook.open_count(), 0)


class FakeTeams(http.server.BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        chunked = "chunked" in (self.headers.get("Transfer-Encoding") or "").lower()
        length = self.headers.get("Content-Length")
        FakeTeams.seen.append({"chunked": chunked, "length": length, "body": self.rfile.read(int(length)) if length else b""})
        self.send_response(411 if chunked or not length else 202)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


class TeamsLength(unittest.TestCase):
    def setUp(self):
        FakeTeams.seen = []
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeTeams)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/hook"

    def send(self, secret, message):
        channels.Teams().send({}, {}, secret, message, opener=lambda request, timeout: urllib.request.urlopen(request, timeout=timeout))

    def test_the_message_goes_with_its_content_length_and_never_in_pieces(self):
        self.send(self.url, {"title": "Red", "text": "repo failed", "url": "https://github.com/o/R/actions/runs/1"})
        row = FakeTeams.seen[0]
        self.assertFalse(row["chunked"])
        self.assertEqual(int(row["length"]), len(row["body"]))
        self.assertIn("repo failed", json.loads(row["body"])["text"])

    def test_the_workflows_of_teams_get_an_adaptive_card_and_the_old_connector_gets_text(self):
        card = channels.Teams.payload("https://prod-12.westeurope.logic.azure.com/workflows/abc", {"title": "Red", "text": "boom", "url": "https://github.com/o/R"})
        self.assertEqual(card["type"], "message")
        content = card["attachments"][0]
        self.assertEqual(content["contentType"], "application/vnd.microsoft.card.adaptive")
        self.assertEqual(content["content"]["type"], "AdaptiveCard")
        self.assertEqual([b["text"] for b in content["content"]["body"]], ["Red", "boom", "https://github.com/o/R"])
        old = channels.Teams.payload("https://contoso.webhook.office.com/webhookb2/abc", {"title": "Red", "text": "boom"})
        self.assertEqual(old, {"text": "boom"})

    def test_a_card_never_carries_a_line_break_trick_in_the_title(self):
        card = channels.Teams.payload("https://x.logic.azure.com/w", {"title": "a\r\nb\x00c", "text": "t"})
        self.assertEqual(card["attachments"][0]["content"]["body"][0]["text"], "a b c")


if __name__ == "__main__":
    unittest.main()
