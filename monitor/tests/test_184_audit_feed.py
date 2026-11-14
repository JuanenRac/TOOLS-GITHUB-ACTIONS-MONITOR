# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The feed of alerts for the AIs and the cap of the notices to an external AI, with several accounts and several threads or processes working at the same time.

1. Every account has its own feed, brief and ledger (a folder derived from the account); an alert carries its account and its id depends on it; a refresh of one account never closes
   the alerts of another, also when the folder is shared on purpose.
2. Refresh, acknowledgement and status of the feed are ONE exclusive step at a time (threads of this process and other processes): an acknowledgement is never undone by a refresh.
3. The cap of calls and of cost an hour is reserved in one step before anything is sent, so notices that run at the same time cannot pass it.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.integrations import ai_alerts, ai_notify  # noqa: E402
from github_actions_monitor.storage import locks  # noqa: E402

NOW = 1_800_000_000
ROW = {"repo": "repo-a", "workflow": "CI", "conclusion": "failure", "streak": 1, "since": "2026-01-01T00:00:00Z", "url": "https://github.com/o/repo-a/actions/runs/9"}


class Feed(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.config = {"ai_alerts": {"enabled": True, "folder": str(self.folder)}}
        self.addCleanup(ai_alerts.ACCOUNT.update, {"id": ""})

    def as_account(self, name):
        ai_alerts.ACCOUNT["id"] = name

    def state(self, folder=None):
        return json.loads(((folder or self.folder) / ai_alerts.STATE).read_text(encoding="utf-8"))


class OneFeedPerAccount(Feed):
    def test_the_single_account_keeps_its_ids_and_the_others_get_their_own(self):
        self.assertEqual(ai_alerts.alert_id("repo-a", "CI"), hashlib.sha1(b"repo-a|CI").hexdigest()[:12], "nothing changes for the one account of the product folder")
        self.as_account("alpha")
        alpha = ai_alerts.alert_id("repo-a", "CI")
        self.as_account("beta")
        self.assertNotEqual(alpha, ai_alerts.alert_id("repo-a", "CI"))
        self.assertNotEqual(alpha, ai_alerts.alert_id("repo-a", "CI", account=""))

    def test_an_account_does_not_close_the_alerts_of_another_in_a_shared_folder(self):
        self.as_account("alpha")
        opened = ai_alerts.update(self.config, [ROW], now=NOW)["opened"]
        self.assertEqual([a["account_id"] for a in opened], ["alpha"])
        self.as_account("beta")
        result = ai_alerts.update(self.config, [], now=NOW + 60)
        self.assertEqual(result["resolved"], [], "beta does not see the red of alpha and must not close it")
        self.assertEqual({a["state"] for a in self.state().values()}, {"open"})
        ai_alerts.update(self.config, [ROW], now=NOW + 120)      # the same workflow is red in beta too: a second alert, not the same one
        self.assertEqual(sorted(a["account_id"] for a in self.state().values()), ["alpha", "beta"])
        self.as_account("alpha")
        result = ai_alerts.update(self.config, [], now=NOW + 180)
        self.assertEqual([a["account_id"] for a in result["resolved"]], ["alpha"], "alpha closes its own")
        self.assertEqual({a["account_id"]: a["state"] for a in self.state().values()}, {"alpha": "resolved", "beta": "open"})

    def test_an_alert_of_an_older_version_belongs_to_the_account_of_the_product_folder(self):
        legacy = {"id": "oldid", "severity": "high", "class": "real", "repo": "r", "workflow": "w", "conclusion": "failure", "cause": "x", "action": "y", "url": None, "state": "open", "first_seen": NOW - 5, "since": None, "streak": 1}
        (self.folder / ai_alerts.STATE).write_text(json.dumps({"oldid": legacy}), encoding="utf-8")
        self.as_account("alpha")
        self.assertEqual(ai_alerts.update(self.config, [], now=NOW)["resolved"], [])
        self.as_account("")
        self.assertEqual([a["id"] for a in ai_alerts.update(self.config, [], now=NOW + 1)["resolved"]], ["oldid"])

    def test_without_a_folder_chosen_every_account_gets_its_own_folder(self):
        root = self.folder / "ai"
        with mock.patch.object(ai_alerts.paths, "folder", lambda kind, base=None: root):
            settings = ai_alerts.settings({})
            self.assertEqual(ai_alerts.folder_of(settings), root)
            self.as_account("alpha")
            alpha = ai_alerts.folder_of(settings)
            self.as_account("beta")
            beta = ai_alerts.folder_of(settings)
        self.assertEqual((alpha, beta), (root / "accounts" / "alpha", root / "accounts" / "beta"))

    def test_each_account_writes_its_feed_brief_and_ledger_in_its_own_folder(self):
        root = self.folder / "ai"
        config = {"ai_alerts": {"enabled": True}}
        with mock.patch.object(ai_alerts.paths, "folder", lambda kind, base=None: root):
            for name in ("alpha", "beta"):
                self.as_account(name)
                ai_alerts.update(config, [ROW], now=NOW)
            for name in ("alpha", "beta"):
                folder = root / "accounts" / name
                self.assertTrue((folder / ai_alerts.BRIEF).is_file() and (folder / ai_alerts.FEED).is_file(), name)
                self.assertEqual([a["account_id"] for a in self.state(folder).values()], [name])
            self.assertFalse((root / ai_alerts.BRIEF).exists(), "nothing is shared in the folder of the product")


class OneStepAtATime(Feed):
    def open_one(self):
        ai_alerts.update(self.config, [ROW], now=NOW)
        return ai_alerts.alert_id("repo-a", "CI")

    def test_a_refresh_in_progress_holds_back_the_acknowledgement_and_neither_is_lost(self):
        ident = self.open_one()
        inside, release, order = threading.Event(), threading.Event(), []
        real_brief = ai_alerts.brief

        def slow_brief(*args, **kwargs):
            inside.set()
            release.wait(10)
            return real_brief(*args, **kwargs)

        def refresh():
            with mock.patch.object(ai_alerts, "brief", slow_brief):
                ai_alerts.update(self.config, [ROW], now=NOW + 60)
            order.append("refresh done")

        def acknowledge():
            inside.wait(10)
            order.append("ack asked")
            order.append(("ack", ai_alerts.ack(self.config, ident, now=NOW + 61)))
        threads = [threading.Thread(target=refresh), threading.Thread(target=acknowledge)]
        for thread in threads:
            thread.start()
        inside.wait(10)
        for _ in range(100):
            if "ack asked" in order:
                break
            threading.Event().wait(0.02)
        threading.Event().wait(0.3)
        self.assertNotIn(("ack", True), order, "the acknowledgement waits while the refresh holds the state")
        release.set()
        for thread in threads:
            thread.join(15)
        self.assertEqual(order[-2:], ["refresh done", ("ack", True)])
        self.assertEqual(self.state()[ident]["state"], "acknowledged", "the acknowledgement survives the refresh")

    def test_a_refresh_that_comes_after_an_acknowledgement_keeps_it(self):
        ident = self.open_one()
        self.assertTrue(ai_alerts.ack(self.config, ident, now=NOW + 1))
        ai_alerts.update(self.config, [ROW], now=NOW + 60)
        self.assertEqual(self.state()[ident]["state"], "acknowledged")
        events = [json.loads(line) for line in (self.folder / ai_alerts.FEED).read_text(encoding="utf-8").splitlines()]
        self.assertEqual([e["event"] for e in events], ["opened", "acknowledged"])

    def test_many_acknowledgements_at_once_write_one_event_each_and_a_consistent_state(self):
        rows = [{**ROW, "workflow": f"W{i}"} for i in range(6)]
        ai_alerts.update(self.config, rows, now=NOW)
        ids = [ai_alerts.alert_id("repo-a", f"W{i}") for i in range(6)]
        gate, results = threading.Barrier(len(ids) + 1), {}

        def acknowledge(ident):
            gate.wait(10)
            results[ident] = ai_alerts.ack(self.config, ident, now=NOW + 1)
        threads = [threading.Thread(target=acknowledge, args=(i,)) for i in ids]
        for thread in threads:
            thread.start()
        gate.wait(10)
        refresh = threading.Thread(target=lambda: ai_alerts.update(self.config, rows, now=NOW + 2))
        refresh.start()
        for thread in threads + [refresh]:
            thread.join(30)
        self.assertEqual(results, {i: True for i in ids})
        self.assertEqual({a["state"] for a in self.state().values()}, {"acknowledged"})
        events = [json.loads(line)["event"] for line in (self.folder / ai_alerts.FEED).read_text(encoding="utf-8").splitlines()]
        self.assertEqual((events.count("opened"), events.count("acknowledged")), (6, 6))

    def test_another_process_that_holds_the_state_makes_this_one_wait_and_then_go_on(self):
        ident = self.open_one()
        script = ("import sys, time; sys.path.insert(0, sys.argv[1]); from github_actions_monitor.storage import locks; from pathlib import Path\n"
                  "with locks.process_lock(Path(sys.argv[2]), 20):\n    print('held', flush=True); time.sleep(1.5)\n")
        holder = subprocess.Popen([sys.executable, "-I", "-c", script, str(HERE / "src"), str(self.folder / ai_alerts.STATE)], stdout=subprocess.PIPE, text=True)
        self.addCleanup(holder.wait, 20)
        self.assertEqual(holder.stdout.readline().strip(), "held")
        with mock.patch.object(ai_alerts, "LOCK_WAIT", 0.2):
            self.assertFalse(ai_alerts.ack(self.config, ident, now=NOW + 1), "it gives up cleanly while the other process keeps the state")
            result = ai_alerts.update(self.config, [], now=NOW + 2)
            self.assertEqual((result["opened"], result["resolved"]), ([], []), "a refresh that cannot take the state is skipped, not forced")
        self.assertEqual(self.state()[ident]["state"], "open")
        with mock.patch.object(ai_alerts, "LOCK_WAIT", 20.0):
            self.assertTrue(ai_alerts.ack(self.config, ident, now=NOW + 3))
        self.assertEqual(self.state()[ident]["state"], "acknowledged")

    def test_the_status_note_takes_the_same_step(self):
        self.open_one()
        with locks.process_lock(self.folder / ai_alerts.STATE, 5), mock.patch.object(ai_alerts, "LOCK_WAIT", 0.2):
            self.assertFalse(ai_alerts.monitor_status(self.config, "refreshing", now=NOW + 1))
        self.assertTrue(ai_alerts.monitor_status(self.config, "refreshing", now=NOW + 2))


class CapOfTheNotices(unittest.TestCase):
    CFG = {"max_calls_per_hour": 3, "max_cost_per_hour_cents": 1000, "cost_per_call_cents": 1}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = {"ai_alerts": {"enabled": True, "folder": self.tmp.name}}
        self.ledger = Path(self.tmp.name) / ai_notify.LEDGER

    def race(self, cfg, count=12):
        gate, answers = threading.Barrier(count), []

        def one():
            gate.wait(10)
            answers.append(ai_notify._spend(self.config, NOW, cfg))
        threads = [threading.Thread(target=one) for _ in range(count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
        return answers

    def test_notices_at_the_same_moment_never_pass_the_number_of_calls(self):
        answers = self.race(self.CFG)
        self.assertEqual((answers.count(None), answers.count("cap_calls")), (3, 9))
        self.assertEqual(len(json.loads(self.ledger.read_text(encoding="utf-8"))["calls"]), 3, "every reserved call is on disk")

    def test_notices_at_the_same_moment_never_pass_the_cost(self):
        answers = self.race({**self.CFG, "max_calls_per_hour": 60, "max_cost_per_hour_cents": 5, "cost_per_call_cents": 2})
        self.assertEqual((answers.count(None), answers.count("cap_cost")), (2, 10))

    def test_a_reservation_is_on_disk_before_anything_is_sent_and_it_counts_if_the_process_dies(self):
        self.assertIsNone(ai_notify._spend(self.config, NOW, self.CFG))
        self.assertEqual(len(json.loads(self.ledger.read_text(encoding="utf-8"))["calls"]), 1)      # nothing was sent: the process died here
        for _ in range(2):
            self.assertIsNone(ai_notify._spend(self.config, NOW + 1, self.CFG))
        self.assertEqual(ai_notify._spend(self.config, NOW + 2, self.CFG), "cap_calls", "the lost call counts until its hour is over")
        self.assertIsNone(ai_notify._spend(self.config, NOW + 3601, self.CFG), "and it is forgotten after the hour, with nothing to clean up")

    def test_a_ledger_that_is_locked_for_too_long_sends_nothing(self):
        with locks.process_lock(self.ledger, 5), mock.patch.object(ai_notify, "LOCK_WAIT", 0.2):
            self.assertEqual(ai_notify._spend(self.config, NOW, self.CFG), "no_ledger")

    def test_a_notice_whose_sending_fails_still_spent_its_call(self):
        config = {**self.config, "ai": {"provider": "ollama", "model": "m"},
                  "ai_notify": {"enabled": True, "confirmed_provider": "ollama", "max_calls_per_hour": 1, "cost_per_call_cents": 1, "max_cost_per_hour_cents": 50}}
        alert = {"id": "abc", "class": "real", "state": "open", "repo": "r", "workflow": "w"}

        def broken(cfg, system, user):
            raise OSError("down")
        self.assertEqual(ai_notify.notify(config, alert, now=NOW, transport=broken)["reason"], "error")
        self.assertEqual(ai_notify.notify(config, alert, now=NOW + 1, transport=lambda *a: "ok")["reason"], "cap_calls")


if __name__ == "__main__":
    unittest.main()
