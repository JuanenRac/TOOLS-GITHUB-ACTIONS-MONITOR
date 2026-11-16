# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Silences by pattern, workflows of the class service (no alert in a loop), grouping by commit and the summary when there are many. Synthetic events only; all of it is off by default."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import alertflow, events, redrule  # noqa: E402
from github_actions_monitor.sentinels import alert_center  # noqa: E402

NOW = 1_800_000_000.0


def red_row(repo="demo", workflow="nightly", file="nightly.yml", streak=1, kind="build", sha="aaa1111", branch="main", recent=10, rate=0):
    return {"repo": repo, "workflow": workflow, "file": file, "streak": streak, "kind": kind, "sha": sha, "branch": branch, "url": "https://example.invalid/run", "since": "2026-01-01T00:00:00Z",
            "recent_runs": recent, "fail_rate": rate}


def snap(*rows):
    return {"a1": {"stuck": []}, "a2": {"red": list(rows)}, "a3": {"rows": []}, "a4": {"dependabot": []}, "a5": {}, "rate": {"remaining": 4000}}


def event(kind="red_new", repo="demo", workflow="nightly", sha="aaa1111", branch="main"):
    return {"kind": kind, "code": kind, "level": "bad", "repo": repo, "owner": "main", "text": f"{repo} {workflow}", "url": None, "args": {"repo": repo, "workflow": workflow}, "sha": sha, "branch": branch}


class Base(unittest.TestCase):
    def setUp(self):
        alertflow.configure({})

    def tearDown(self):
        alertflow.configure({})

    def cfg(self, **blocks):
        alertflow.configure({"alerts": blocks})


class Silences(Base):
    def test_off_by_default_everything_passes(self):
        told, record = alertflow.Flow().shape([event(), event(workflow="b")], NOW)
        self.assertEqual((len(told), len(record)), (2, 2))
        self.assertFalse(any("silenced" in e for e in record))

    def test_parse(self):
        entry = alertflow.parse_silence("repo-a:nightly.yml:release/*;flaky external service;2027-03-01")
        self.assertEqual((entry["repo"], entry["workflow"], entry["branch"], entry["reason"], entry["review_by"]), ("repo-a", "nightly.yml", "release/*", "flaky external service", "2027-03-01"))
        self.assertEqual(alertflow.parse_silence("repo-a")["workflow"], "*")
        for bad in ("", "a b", "repo;reason;2027-13-45", "repo;a;b;c", 5, None):
            self.assertIsNone(alertflow.parse_silence(bad), bad)

    def test_a_pattern_silences_only_what_it_names(self):
        self.cfg(silences=["demo:nightly*;known flaky"])
        told, record = alertflow.Flow().shape([event(workflow="nightly build"), event(workflow="deploy"), event(repo="other", workflow="nightly build")], NOW)
        self.assertEqual([e["args"]["workflow"] for e in told], ["deploy", "nightly build"])
        silenced = [e for e in record if e.get("silenced")]
        self.assertEqual((len(silenced), silenced[0]["silence_reason"]), (1, "known flaky"))

    def test_branch_pattern_needs_the_branch(self):
        self.cfg(silences=["demo:*:release-*;old line"])
        told, _ = alertflow.Flow().shape([event(branch="release-1"), event(branch="main"), event(branch=None)], NOW)
        self.assertEqual(len(told), 2)

    def test_review_date_announces_one_reminder_and_keeps_the_silence(self):
        self.cfg(silences=["demo:nightly*;known flaky;2027-01-15"])
        flow = alertflow.Flow()
        before = 1_800_000_000.0      # 2027-01-15 08:00 UTC is 1_800_000_000 + ...: stay clearly before and after
        self.assertEqual(flow.shape([], before - 40 * 86400)[0], [])
        told, record = flow.shape([event()], before + 40 * 86400)
        self.assertEqual([e["kind"] for e in told], ["silence_review"])
        self.assertEqual(len(record), 2)
        again, _ = flow.shape([event()], before + 41 * 86400)
        self.assertEqual(again, [])      # silenced, and the reminder is not repeated

    def test_the_alerts_tab_shows_them_as_silenced(self):
        self.cfg(silences=["demo:nightly*;known flaky;2027-03-01"])
        alert = {"id": "ci.red:demo:nightly", "code": "ci.red", "repo": "demo", "details": {"workflow": "nightly", "file": "nightly.yml", "branch": "main"}}
        class Registry:
            def alerts(self):
                return [alert, dict(alert, id="ci.red:demo:other", details={"workflow": "other"})]
        with tempfile.TemporaryDirectory() as folder:
            old = alert_center.STATE_FILE
            alert_center.STATE_FILE = Path(folder) / "mutes.json"
            try:
                rows = alert_center.collect(Registry())
            finally:
                alert_center.STATE_FILE = old
        self.assertEqual([bool(r["muted_until"]) for r in rows], [True, False])
        self.assertEqual((rows[0]["muted_permanent"], rows[0]["muted_reason"]), (True, "known flaky"))


class Service(Base):
    def test_off_by_default_a_single_failure_alerts(self):
        self.assertEqual(len(events.summarize(snap(red_row(kind="service", streak=1)))["reds"]), 1)

    def test_service_class_needs_failures_in_a_row(self):
        self.cfg(service={"enabled": True, "failures": 3})
        self.assertEqual(events.summarize(snap(red_row(kind="service", streak=1)))["reds"], {})
        self.assertEqual(events.summarize(snap(red_row(kind="service", streak=2)))["reds"], {})
        self.assertEqual(len(events.summarize(snap(red_row(kind="service", streak=3)))["reds"]), 1)
        self.assertEqual(len(events.summarize(snap(red_row(kind="build", streak=1)))["reds"]), 1)      # a build keeps alerting at once

    def test_flapping_cron_does_not_alert_in_a_loop(self):
        self.cfg(service={"enabled": True, "failures": 3})
        old = events.summarize(snap())
        told = 0
        for streak in (1, 0, 1, 0, 1, 1, 0, 1):      # fails, recovers, fails ... never three in a row
            new = events.summarize(snap(red_row(kind="service", streak=streak)) if streak else snap())
            told += len(events.diff(old, new, True))
            old = new
        self.assertEqual(told, 0)

    def test_it_is_announced_once_and_cleared_once(self):
        self.cfg(service={"enabled": True, "failures": 2})
        states = [snap(), snap(red_row(kind="service", streak=1)), snap(red_row(kind="service", streak=2)), snap(red_row(kind="service", streak=3)), snap()]
        old, kinds = events.summarize(states[0]), []
        for state in states[1:]:
            new = events.summarize(state)
            kinds += [e["kind"] for e in events.diff(old, new, True)]
            old = new
        self.assertEqual(kinds, ["red_new", "red_fixed"])

    def test_rate_and_extra_patterns(self):
        self.cfg(service={"enabled": True, "failures": 5, "rate_percent": 60, "workflows": ["demo:nightly*"]})
        self.assertEqual(len(events.summarize(snap(red_row(kind="build", streak=1, rate=80)))["reds"]), 1)      # not the service class: alerts at once
        self.assertEqual(events.summarize(snap(red_row(workflow="nightly build", streak=1, rate=33)))["reds"], {})
        self.assertEqual(len(events.summarize(snap(red_row(workflow="nightly build", streak=1, rate=80)))["reds"]), 1)
        self.assertEqual(events.summarize(snap(red_row(workflow="nightly build", streak=1, rate=80, recent=3)))["reds"], {})      # too few runs to judge a rate

    def test_rows_carry_the_recent_rate(self):
        runs = [{"repo": "demo", "id": i, "name": "cron", "path": "cron.yml", "branch": "main", "event": "schedule", "status": "completed", "conclusion": "failure" if i % 3 == 0 else "success",
                 "started": f"2026-01-{i + 1:02d}T00:00:00Z"} for i in range(9)]
        rows = redrule.red_workflows({"demo": runs[:7]}, {"demo": "main"}, now=1_769_904_000.0)[0]
        self.assertEqual((rows[0]["file"], rows[0]["recent_runs"], rows[0]["fail_rate"], rows[0]["kind"]), ("cron.yml", 7, 43, "service"))


class Grouping(Base):
    def test_off_by_default(self):
        told, _ = alertflow.Flow().shape([event(workflow=f"w{i}") for i in range(5)], NOW)
        self.assertEqual(len(told), 5)

    def test_reds_of_one_commit_are_one_message(self):
        self.cfg(group={"by_commit": True, "min": 3})
        batch = [event(workflow=f"w{i}") for i in range(4)] + [event(workflow="x", sha="bbb2222"), event(repo="other", workflow="y")]
        told, record = alertflow.Flow().shape(batch, NOW)
        self.assertEqual(len(told), 3)
        group = told[0]
        self.assertEqual((group["kind"], group["grouped"], group["args"]["count"], group["sha"]), ("red_new", 4, 4, "aaa1111"))
        self.assertIn("w0, w1, w2, w3", group["text"])
        self.assertEqual(sum(1 for e in record if e.get("grouped_into")), 4)

    def test_fewer_than_the_minimum_stay_apart(self):
        self.cfg(group={"by_commit": True, "min": 3})
        told, _ = alertflow.Flow().shape([event(workflow="a"), event(workflow="b")], NOW)
        self.assertEqual(len(told), 2)


class Digest(Base):
    def test_off_by_default(self):
        told, _ = alertflow.Flow().shape([event(workflow=f"w{i}") for i in range(40)], NOW)
        self.assertEqual(len(told), 40)

    def test_many_events_become_one_summary(self):
        self.cfg(digest={"minutes": 60, "threshold": 5})
        flow = alertflow.Flow()
        told, record = flow.shape([event(workflow=f"w{i}") for i in range(8)], NOW)
        self.assertEqual(len(told), 5)
        self.assertEqual(sum(1 for e in record if e.get("held")), 3)
        self.assertEqual(flow.shape([event(workflow="late")], NOW + 600)[0], [])      # still inside the hour: held
        told, record = flow.shape([], NOW + 3600)
        self.assertEqual([e["kind"] for e in told], ["alerts_digest"])
        self.assertEqual((told[0]["args"]["n"], told[0]["args"]["red"]), (4, 4))
        self.assertEqual(flow.shape([], NOW + 3700)[0], [])      # nothing more to say

    def test_after_an_hour_individual_alerts_flow_again(self):
        self.cfg(digest={"minutes": 60, "threshold": 3})
        flow = alertflow.Flow()
        flow.shape([event(workflow=f"w{i}") for i in range(4)], NOW)
        told, _ = flow.shape([event(workflow="z")], NOW + 3700)
        self.assertEqual(sorted(e["kind"] for e in told), ["alerts_digest", "red_new"])


class Wiring(Base):
    def test_feed_writes_everything_but_tells_only_what_is_left(self):
        self.cfg(silences=["demo:nightly*;known flaky"])
        with tempfile.TemporaryDirectory() as folder:
            feed = events.Feed(Path(folder) / "events.jsonl", Path(folder) / "state.json")
            told = []
            feed.listeners.append(told.extend)
            feed.feed(snap())
            written = feed.feed(snap(red_row(workflow="nightly build"), red_row(workflow="deploy", file="deploy.yml")))
            lines = [json.loads(x) for x in (Path(folder) / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(written), 2)
        self.assertEqual([e["args"]["workflow"] for e in told], ["deploy"])
        self.assertEqual(sorted(bool(x.get("silenced")) for x in lines), [False, True])

    def test_settings_are_editable_with_checks(self):
        for path, good, bad in (("alerts.silences", ["demo:ci.yml:main;why;2027-01-01"], ["two words"]), ("alerts.service.enabled", True, "yes"), ("alerts.service.failures", 3, 1),
                                ("alerts.service.workflows", ["demo:nightly.yml"], ["a b c"]), ("alerts.group.by_commit", False, 1), ("alerts.group.min", 3, 1),
                                ("alerts.digest.minutes", 60, 5000), ("alerts.digest.threshold", 10, 2)):
            self.assertTrue(settings_api.check_value(path, good)[0], path)
            self.assertFalse(settings_api.check_value(path, bad)[0], path)

    def test_defaults_change_nothing(self):
        block = actions_monitor.DEFAULTS["alerts"]
        self.assertEqual(block["silences"], [])
        self.assertFalse(block["service"]["enabled"])
        self.assertFalse(block["group"]["by_commit"])
        self.assertEqual(block["digest"]["minutes"], 0)
        self.assertEqual(alertflow.settings({}), {"silences": [], "service": {"enabled": False, "failures": 3, "rate_percent": 0, "workflows": []}, "group": {"by_commit": False, "min": 3}, "digest": {"minutes": 0, "threshold": 10}})


if __name__ == "__main__":
    unittest.main()
