# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The command line leftovers: `alerts --since` (the ledger of what was open), `proposals` (list, show, approve, reject, execute), and the doctor checks `compare_window` and `etag`."""
import json
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_190_cli as base  # noqa: E402
from github_actions_monitor.cli import doctor, monitor_cli  # noqa: E402
from github_actions_monitor.integrations import ai_actions  # noqa: E402
from github_actions_monitor.sentinels import alert_center as ac  # noqa: E402

NOW = 1_800_000_000


def alert(id_, sentinel="ci", level="error", repo="o/r"):
    return {"id": id_, "code": "ci.red", "sentinel": sentinel, "level": level, "repo": repo, "title": "t " + id_, "details": {}}


class Ledger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(ac, "STATE_FILE", Path(self.tmp.name) / "alert_mutes.json")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_an_alert_is_open_from_the_first_time_it_is_seen(self):
        ac.track([alert("a")], NOW)
        rows = ac.recent(3600, now=NOW + 60)
        self.assertEqual([(r["id"], r["state"], r["resolved_at"]) for r in rows], [("a", "open", None)])

    def test_a_missing_alert_closes_only_after_the_grace(self):
        ac.track([alert("a")], NOW)
        ac.track([], NOW + 60)
        self.assertEqual(ac.recent(3600, now=NOW + 61)[0]["state"], "open")      # a restart or a cycle not yet run closes nothing
        ac.track([], NOW + 60 + ac.RESOLVE_GRACE)
        row = ac.recent(3600, now=NOW + 700)[0]
        self.assertEqual(row["state"], "resolved")
        self.assertEqual(row["resolved_at"], ac._iso(NOW + 60))

    def test_an_alert_that_comes_back_in_time_stays_the_same_row(self):
        ac.track([alert("a")], NOW)
        ac.track([], NOW + 60)
        ac.track([alert("a")], NOW + 120)
        ac.track([], NOW + 130 + ac.RESOLVE_GRACE)
        self.assertEqual(ac.recent(86400, now=NOW + 200)[0]["first_seen"], ac._iso(NOW))
        self.assertEqual(ac.recent(86400, now=NOW + 200)[0]["state"], "open")

    def test_a_list_that_is_not_complete_closes_nothing(self):
        ac.track([alert("a")], NOW)
        ac.track([], NOW + 10, complete=False)
        ac.track([], NOW + 10 + 5 * ac.RESOLVE_GRACE, complete=False)      # not looking is not fixing
        self.assertEqual(ac.recent(86400, now=NOW + 20 + 5 * ac.RESOLVE_GRACE)[0]["state"], "open")

    def test_a_closed_alert_that_returns_is_a_new_row(self):
        ac.track([alert("a")], NOW)
        ac.track([], NOW + 10)
        ac.track([], NOW + 10 + ac.RESOLVE_GRACE)
        ac.track([alert("a")], NOW + 5000)
        row = ac.recent(86400, now=NOW + 5001)[0]
        self.assertEqual((row["state"], row["first_seen"]), ("open", ac._iso(NOW + 5000)))

    def test_the_window_and_the_filters(self):
        ac.track([alert("a"), alert("b", sentinel="collab", level="warning")], NOW)
        ac.track([alert("b", sentinel="collab", level="warning")], NOW + 10)
        ac.track([alert("b", sentinel="collab", level="warning")], NOW + 10 + ac.RESOLVE_GRACE)
        self.assertEqual({r["id"] for r in ac.recent(3600, now=NOW + 700)}, {"a", "b"})
        self.assertEqual({r["id"] for r in ac.recent(3600, sentinel="collab", now=NOW + 700)}, {"b"})
        self.assertEqual({r["id"] for r in ac.recent(3600, level="error", now=NOW + 700)}, {"a"})
        self.assertEqual([r["id"] for r in ac.recent(60, now=NOW + 7 * 86400)], ["b"])      # "a" closed long before the window; "b" is still open

    def test_collect_feeds_the_ledger_and_a_failing_sentinel_closes_nothing(self):
        class Registry:
            def __init__(self, alerts, fail=False):
                self.alerts_, self.fail = alerts, fail

            def alerts(self):
                if self.fail:
                    raise RuntimeError("down")
                return self.alerts_

        ac.collect(Registry([alert("a")]), now=NOW)
        ac.collect(Registry([], fail=True), now=NOW + 5 * ac.RESOLVE_GRACE)
        ac.collect(Registry([], fail=True), now=NOW + 10 * ac.RESOLVE_GRACE)
        self.assertEqual(ac.recent(86400 * 3, now=NOW + 10 * ac.RESOLVE_GRACE)[0]["state"], "open")

    def test_the_ledger_is_bounded_and_a_damaged_file_is_ignored(self):
        ac.track([alert("a%d" % i) for i in range(ac.SEEN_MAX + 20)], NOW)
        self.assertLessEqual(len(ac._load()["seen"]), ac.SEEN_MAX)
        ac.STATE_FILE.write_text(json.dumps({"active": [], "history": [], "seen": {"x": "no", "y": {"first_seen": "z"}}}), encoding="utf-8")
        self.assertEqual(ac._load()["seen"], {})

    def test_a_silence_keeps_the_ledger_and_the_ledger_keeps_the_silences(self):
        ac.track([alert("a")], NOW)
        ac.mute("alert", "a", 1, now=NOW)
        self.assertEqual(len(ac._load()["seen"]), 1)
        ac.track([alert("a")], NOW + 1000)
        self.assertEqual(len(ac._load()["active"]), 1)

    def test_parse_since(self):
        self.assertEqual([ac.parse_since(x) for x in ("90m", "24h", "7d", "2w", "120", " 5 D ")], [5400, 86400, 604800, 1209600, 120, 432000])
        self.assertEqual([ac.parse_since(x) for x in ("", "x", "0h", "-1h", "91d", "1y", "1.5h", None)], [None] * 8)


class Cli(unittest.TestCase):
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

    def ask(self, *argv):
        return base.run(*argv, "--url", self.url, "--lang", "en")

    def test_alerts_since_lists_the_closed_ones_and_sends_the_length(self):
        base.ANSWERS["/api/alerts"] = {"since": {"seconds": 86400, "error": None, "alerts": [
            {"id": "a", "code": "ci.red", "sentinel": "ci", "level": "error", "repo": "o/r", "title": "red", "first_seen": "2026-01-01T00:00:00Z", "last_seen": "2026-01-01T01:00:00Z", "resolved_at": "2026-01-01T02:00:00Z", "state": "resolved"},
            {"id": "b", "code": "ci.red", "sentinel": "ci", "level": "warning", "repo": "o/q", "title": "slow", "first_seen": "2026-01-01T03:00:00Z", "last_seen": "2026-01-01T03:00:00Z", "resolved_at": None, "state": "open"}]}}
        code, out, _ = self.ask("alerts", "--since", "24h")
        self.assertEqual(code, 0, out)
        self.assertIn("2 alerts open at some moment of the last 24 h", out)
        self.assertIn("closed 2026-01-01 02:00:00 UTC", out)
        self.assertIn("still open", out)
        self.assertIn("since=24h", " ".join(base.SEEN))

    def test_alerts_since_with_a_bad_length_is_a_usage_error(self):
        base.ANSWERS["/api/alerts"] = {"since": {"seconds": None, "error": "bad_since", "alerts": []}}
        code, _, err = self.ask("alerts", "--since", "soon")
        self.assertEqual(code, 1)
        self.assertIn("--since needs a length", err)

    def test_alerts_since_against_an_older_monitor_says_so_instead_of_the_current_list(self):
        base.ANSWERS["/api/alerts"] = {"alerts": [{"id": "a", "level": "error"}]}
        code, _, err = self.ask("alerts", "--since", "24h")
        self.assertEqual(code, 4)
        self.assertIn("does not keep the history", err)

    def test_alerts_without_since_is_what_it_was(self):
        base.ANSWERS["/api/alerts"] = {"alerts": [{"id": "a", "level": "error", "sentinel": "ci", "code": "x", "title": "T"}]}
        code, out, _ = self.ask("alerts")
        self.assertEqual(code, 0)
        self.assertIn("1 alerts", out)
        self.assertNotIn("since=", " ".join(base.SEEN))

    PROPOSALS = {"state": {"enabled": True, "execute": True, "require_approval": True}, "log": [], "proposals": [
        {"id": "aaaa1111bbbb2222", "action": "rerun_failed", "command": "gh run rerun 5 -R o/r --failed", "repo": "r", "runnable": True, "status": "pending", "by": "", "age_s": 10, "expires_in_s": 590},
        {"id": "aaaa9999cccc3333", "action": "close_issue", "command": "gh issue close 7 -R o/r", "repo": "r", "runnable": True, "status": "approved", "by": "cli", "age_s": 20, "expires_in_s": 580}]}

    def test_proposals_list_and_show(self):
        base.ANSWERS["/api/ai/actions"] = self.PROPOSALS
        code, out, _ = self.ask("proposals")
        self.assertEqual(code, 0, out)
        self.assertIn("2 proposals of the AI waiting (approval needed before it runs)", out)
        self.assertIn("aaaa1111bbbb2222", out)
        code, out, _ = self.ask("proposals", "show", "aaaa1")
        self.assertEqual(code, 0, out)
        self.assertIn("rerun_failed", out)
        code, _, err = self.ask("proposals", "show", "aaaa")
        self.assertEqual((code, "More than one" in err), (1, True))
        code, _, err = self.ask("proposals", "show", "zzzz")
        self.assertEqual((code, "No proposal waiting" in err), (1, True))
        code, _, err = self.ask("proposals", "show")
        self.assertEqual((code, "Give the id" in err), (1, True))

    def test_proposals_list_table_has_columns(self):
        base.ANSWERS["/api/ai/actions"] = self.PROPOSALS
        code, out, _ = self.ask("proposals", "--format", "ndjson")
        self.assertEqual(code, 0)
        rows = [json.loads(line) for line in out.splitlines()]
        self.assertEqual([r["status"] for r in rows], ["pending", "approved"])

    def test_approve_reject_and_execute_post_to_the_right_routes(self):
        base.ANSWERS["/api/ai/actions"] = self.PROPOSALS
        sent = []

        def fake_post(base_url, path, payload, timeout=8, token="", guarded=False):
            sent.append((path, payload, guarded))
            return 200, {"ok": True, "reason": "ok"}

        with mock.patch.object(monitor_cli, "post_json", fake_post):
            self.assertEqual(self.ask("proposals", "approve", "aaaa1111")[0], 0)
            self.assertEqual(self.ask("proposals", "reject", "aaaa9999")[0], 0)
            self.assertEqual(self.ask("proposals", "execute", "aaaa9999")[0], 0)
        self.assertEqual(sent[0], ("/api/ai/actions/review", {"id": "aaaa1111bbbb2222", "decision": "approve", "by": "cli"}, True))
        self.assertEqual(sent[1][1]["decision"], "reject")
        self.assertEqual(sent[2], ("/api/ai/actions/confirm", {"id": "aaaa9999cccc3333", "command": "gh issue close 7 -R o/r"}, True))

    def test_a_refusal_is_told_with_its_reason_and_the_exit_code_is_4(self):
        base.ANSWERS["/api/ai/actions"] = self.PROPOSALS
        with mock.patch.object(monitor_cli, "post_json", lambda *a, **k: (200, {"ok": False, "reason": "not_approved"})):
            code, out, _ = self.ask("proposals", "execute", "aaaa1111")
        self.assertEqual(code, 4)
        self.assertIn("must be approved first", out)
        with mock.patch.object(monitor_cli, "post_json", lambda *a, **k: (403, {"error": "local_only"})):
            code, _, err = self.ask("proposals", "approve", "aaaa1111")
        self.assertEqual(code, 3)
        self.assertIn("this computer only", err)

    def test_proposals_is_in_the_completions_and_the_commands(self):
        self.assertIn("proposals", monitor_cli.COMMANDS)
        self.assertEqual(monitor_cli.WORDS_BY_COMMAND["proposals"], ("list", "show", "approve", "reject", "execute"))


class Proposals(unittest.TestCase):
    CFG = {"ai": {"actions": {"enabled": True, "execute": True}}}

    def make(self, config=None, now=[1000.0]):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        actions = ai_actions.Actions(log_file=Path(self.tmp.name) / "log.jsonl", clock=lambda: now[0])
        out = actions.propose("run gh run rerun 5 --failed", "r", config or self.CFG, {"r"}, lambda repo, n: True, lambda repo, n: True, "o")
        return actions, out[0]["id"], out[0]["command"], now

    def test_a_new_proposal_is_pending_and_listed_without_its_arguments(self):
        actions, ident, command, _ = self.make()
        rows = actions.listing(self.CFG)
        self.assertEqual([(r["id"], r["status"], r["command"]) for r in rows], [(ident, "pending", command)])
        self.assertNotIn("argv", rows[0])
        self.assertEqual(rows[0]["expires_in_s"], 600)

    def test_without_the_setting_nothing_needs_approval(self):
        actions, ident, command, _ = self.make()
        done = actions.run(ident, command, self.CFG, runner=lambda argv, **kw: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
        self.assertEqual(done["reason"], "ok")

    def test_with_the_setting_it_runs_only_after_approval(self):
        config = {"ai": {"actions": {"enabled": True, "execute": True, "require_approval": True}}}
        actions, ident, command, _ = self.make(config)
        runner = lambda argv, **kw: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()      # noqa: E731
        self.assertEqual(actions.run(ident, command, config, runner=runner)["reason"], "not_approved")
        self.assertEqual(actions.review(ident, "approve", "ana"), {"ok": True, "reason": "ok", "status": "approved"})
        self.assertEqual(actions.listing(config)[0]["by"], "ana")
        self.assertEqual(actions.run(ident, command, config, runner=runner)["reason"], "ok")

    def test_a_rejected_proposal_never_runs_even_without_the_setting(self):
        actions, ident, command, _ = self.make()
        self.assertTrue(actions.review(ident, "reject", "ana")["ok"])
        self.assertEqual(actions.run(ident, command, self.CFG, runner=lambda *a, **k: self.fail("it ran"))["reason"], "rejected")

    def test_a_decision_is_final_and_bad_input_is_refused(self):
        actions, ident, _, _ = self.make()
        self.assertEqual(actions.review(ident, "maybe")["reason"], "bad_decision")
        self.assertEqual(actions.review("nope", "approve")["reason"], "unknown")
        actions.review(ident, "approve")
        self.assertEqual(actions.review(ident, "reject")["reason"], "decided")

    def test_an_expired_proposal_cannot_be_reviewed_or_listed(self):
        actions, ident, _, now = self.make()
        now[0] += 601
        self.assertEqual(actions.review(ident, "approve")["reason"], "expired")
        self.assertEqual(actions.listing(self.CFG), [])

    def test_the_review_leaves_a_line_in_the_log(self):
        actions, ident, _, _ = self.make()
        actions.review(ident, "approve", "ana")
        self.assertEqual(actions.log()[0]["review"], "approved")

    def test_the_setting_is_off_by_default_and_read_as_a_bool(self):
        self.assertIs(ai_actions.settings({})["require_approval"], False)
        self.assertIs(ai_actions.settings({"ai": {"actions": {"require_approval": True}}})["require_approval"], True)
        self.assertIs(ai_actions.settings({"ai": {"actions": {"require_approval": "yes"}}})["require_approval"], False)

    def test_the_route_is_for_this_computer_and_audited(self):
        from github_actions_monitor.app import actions_monitor
        from github_actions_monitor.security import audited_posts
        self.assertIn("/api/ai/actions/review", actions_monitor.THIS_COMPUTER_ACTIONS)
        self.assertIn("/api/ai/actions/review", audited_posts.AUDITED)


class DoctorChecks(unittest.TestCase):
    def test_compare_window_is_off_when_the_comparison_is_off(self):
        self.assertEqual(doctor.compare_window_check({}), ("ok", "off"))

    def test_a_window_the_history_floor_cannot_cover_warns_with_the_numbers(self):
        status, detail = doctor.compare_window_check({"compare": {"enabled": True, "default_window_days": 30, "min_days_of_history": 14}})
        self.assertEqual(status, "warn")
        self.assertIn("60 d", detail)
        self.assertIn("compare.min_days_of_history is 14", detail)

    def test_a_window_that_fits_is_ok(self):
        status, detail = doctor.compare_window_check({"compare": {"enabled": True, "default_window_days": 7, "min_days_of_history": 14}})
        self.assertEqual(status, "ok")
        self.assertIn("14 d of history", detail)

    def test_a_short_retention_is_said(self):
        status, detail = doctor.compare_window_check({"compare": {"enabled": True, "default_window_days": 7, "min_days_of_history": 30}, "retention": {"events_days": 10}})
        self.assertEqual(status, "warn")
        self.assertIn("retention.events_days is 10", detail)

    def test_the_checks_are_in_the_list_with_their_texts(self):
        from github_actions_monitor import i18n
        for name in ("compare_window", "etag"):
            self.assertIn(name, doctor.ORDER)
            self.assertIn(name, doctor.FIX)
            for lang in ("en", "es", "de", "fr", "it", "ja", "pt", "zh"):
                with i18n.use_language(lang):
                    self.assertNotEqual(i18n.t("doctor.t." + name), "doctor.t." + name)
                    self.assertNotEqual(i18n.t("doctor.f." + name), "doctor.f." + name)

    @staticmethod
    def quota(calls, saved, no_etag=0, hit=None):
        return lambda port: {"savings": {"ways": [{"id": "etag", "on": True, "spared": saved, "saved": saved, "calls": calls, "no_etag": no_etag, "hit_pct": hit}]}}

    def test_etag_off_not_running_and_few_reads(self):
        self.assertEqual(doctor.etag_check({"network": {"etag": False}}, [8765], reader=self.quota(100, 50)), ("ok", "off"))
        self.assertEqual(doctor.etag_check({}, [], reader=self.quota(100, 50)), ("ok", "not running"))
        self.assertEqual(doctor.etag_check({}, [8765], reader=lambda port: None), ("ok", "not running"))
        status, detail = doctor.etag_check({}, [8765], reader=self.quota(10, 5))
        self.assertEqual((status, "few reads" in detail), ("ok", True))

    def test_etag_says_the_share_and_warns_when_the_header_is_stripped(self):
        status, detail = doctor.etag_check({}, [8765], reader=self.quota(200, 150, 0, 75.0))
        self.assertEqual(status, "ok")
        self.assertIn("75.0 % of 200 reads were 304 (150 spared)", detail)
        status, detail = doctor.etag_check({}, [8765], reader=self.quota(200, 0, 120, 0.0))
        self.assertEqual(status, "warn")
        self.assertIn("120 answers without ETag", detail)

    def test_the_run_includes_both_checks_and_never_fails_on_them(self):
        checks = doctor.run(runner=lambda *a, **k: (1, "", ""), config={"compare": {"enabled": True, "default_window_days": 30}}, ports=(), etag_reader=lambda port: None)
        by_id = {c["id"]: c for c in checks}
        self.assertEqual(by_id["compare_window"]["status"], "warn")
        self.assertEqual(by_id["etag"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
