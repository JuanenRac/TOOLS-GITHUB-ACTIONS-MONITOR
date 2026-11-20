# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Two opt-in watches: the Supply chain sentinel that lints only what changed (`sentinels.supply.incremental`) and the Security signal for runs deleted after the monitor saw them
(`sentinels.security.signals.runs_deleted`)."""
import time
import unittest

import _testenv  # noqa: F401
import test_217_supply_chain as base
from github_actions_monitor.app import settings_api
from github_actions_monitor.sentinels import deleted_runs as dr
from github_actions_monitor.sentinels import sentinel_security as sec

NOW = 1_800_000_000.0


def stamp(offset):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - offset))


def run(i, event="push", branch="main", age=3600, actor="ana"):
    return {"id": i, "name": "CI", "event": event, "head_branch": branch, "created_at": stamp(age), "triggering_actor": {"login": actor}}


class Incremental(unittest.TestCase):
    def test_it_is_a_setting_and_off_by_default(self):
        self.assertFalse(base.ss.settings({})["incremental"])
        self.assertFalse(base.ss.settings({"sentinels": {"supply": {"incremental": "yes"}}})["incremental"])
        self.assertTrue(base.ss.settings({"sentinels": {"supply": {"incremental": True}}})["incremental"])
        self.assertIn("sentinels.supply.incremental", {row[2] for row in settings_api.ROWS})

    def test_an_unchanged_repository_is_not_linted_again_and_keeps_its_alerts(self):
        sentinel, fake, _ = base.build(self, {"incremental": True})
        fake.repos["r"] = {"a.yml": base.LOOSE}
        sentinel.tick(now=base.NOW)
        alerts = {a["id"] for a in sentinel.get_alerts()}
        self.assertTrue(alerts)
        calls = []
        real = base.supply.findings
        base.supply.findings = lambda *a, **k: calls.append(1) or real(*a, **k)
        self.addCleanup(lambda: setattr(base.supply, "findings", real))
        sentinel.tick(now=base.NOW + 7200)
        self.assertEqual(calls, [])
        self.assertEqual({a["id"] for a in sentinel.get_alerts()}, alerts)
        self.assertEqual(sentinel.get_status()["unchanged"], 1)

    def test_a_changed_file_or_a_changed_rule_is_linted_again(self):
        sentinel, fake, _ = base.build(self, {"incremental": True})
        fake.repos["r"] = {"a.yml": base.LOOSE}
        sentinel.tick(now=base.NOW)
        fake.repos["r"] = {"a.yml": base.CLEAN}
        sentinel.tick(now=base.NOW + 7200)
        self.assertEqual(sentinel.get_alerts(), [])
        before = sentinel._fingerprint("r")
        sentinel.cfg["signals"]["unpinned"]["enabled"] = False
        self.assertNotEqual(sentinel._fingerprint("r"), before)

    def test_off_it_lints_every_pass(self):
        sentinel, fake, _ = base.build(self)
        fake.repos["r"] = {"a.yml": base.LOOSE}
        sentinel.tick(now=base.NOW)
        calls = []
        real = base.supply.findings
        base.supply.findings = lambda *a, **k: calls.append(1) or real(*a, **k)
        self.addCleanup(lambda: setattr(base.supply, "findings", real))
        sentinel.tick(now=base.NOW + 7200)
        self.assertEqual(len(calls), 1)


class DeletedRuns(unittest.TestCase):
    def test_it_is_off_by_default_with_the_documented_bounds(self):
        cfg = sec.settings({})["signals"]["runs_deleted"]
        self.assertEqual(cfg, {"enabled": False, "check_window_days": 14, "max_checks": 50})
        bad = sec.settings({"sentinels": {"security": {"signals": {"runs_deleted": {"check_window_days": 0, "max_checks": 9999}}}}})["signals"]["runs_deleted"]
        self.assertEqual((bad["check_window_days"], bad["max_checks"]), (14, 50))
        keys = {row[2] for row in settings_api.ROWS}
        for key in ("enabled", "check_window_days", "max_checks"):
            self.assertIn("sentinels.security.signals.runs_deleted." + key, keys)

    def test_only_the_runs_that_matter_are_remembered(self):
        runs = [run(1), run(2, branch="feature"), run(3, "workflow_dispatch", "feature"), run(4, "pull_request_target", "x"), run(5, "pull_request", "main")]
        seen, listed = dr.observe([], runs, "main", NOW, 14 * 86400)
        self.assertEqual(sorted(row[0] for row in seen), [1, 3, 4])
        self.assertEqual(listed, {1, 2, 3, 4, 5})

    def test_a_404_is_a_deletion_and_a_refusal_or_an_error_is_not(self):
        runs = [run(1), run(2), run(3)]
        seen, deleted, _ = dr.update([], [], runs, "main", NOW, 14, 50, lambda i: 200)
        self.assertEqual((len(seen), deleted), (3, []))
        answers = {1: 404, 2: 403, 3: 200}

        def ask(i):
            if i == 3:
                raise RuntimeError("network")
            return answers[i]
        seen, deleted, checks = dr.update(seen, [], [], "main", NOW + 60, 14, 50, ask)
        self.assertEqual([d["id"] for d in deleted], [1])
        self.assertEqual(checks, 2)
        self.assertEqual(sorted(row[0] for row in seen), [2, 3])      # the refused and the failed one stay for the next pass
        self.assertEqual(deleted[0]["actor"], "ana")

    def test_a_run_that_only_left_the_list_is_alive_and_forgotten(self):
        seen, _, _ = dr.update([], [], [run(1)], "main", NOW, 14, 50, lambda i: 200)
        seen, deleted, _ = dr.update(seen, [], [], "main", NOW + 60, 14, 50, lambda i: 200)
        self.assertEqual((seen, deleted), ([], []))

    def test_a_run_older_than_the_window_is_not_asked_for(self):
        asked = []
        seen = [[7, "CI", "ana", "main", "push", NOW - 20 * 86400]]
        seen, deleted, checks = dr.update(seen, [], [], "main", NOW, 14, 50, lambda i: asked.append(i) or 404)
        self.assertEqual((asked, deleted, checks), ([], [], 0))

    def test_the_checks_per_round_are_capped(self):
        seen, _, _ = dr.update([], [], [run(i, age=i) for i in range(1, 11)], "main", NOW, 14, 50, lambda i: 200)
        asked = []
        dr.update(seen, [], [], "main", NOW + 60, 14, 3, lambda i: asked.append(i) or 200)
        self.assertEqual(len(asked), 3)

    def test_a_noticed_deletion_raises_one_alert_naming_the_run_and_expires_with_the_window(self):
        seen, deleted, _ = dr.update([], [], [run(1)], "main", NOW, 14, 50, lambda i: 200)
        seen, deleted, _ = dr.update(seen, [], [], "main", NOW + 60, 14, 50, lambda i: 404)
        cfg = sec.settings({"sentinels": {"security": {"signals": {"runs_deleted": {"enabled": True}}}}})
        found = sec.evaluate("r", {"runs_deleted": deleted}, cfg, NOW)
        alert = found["security.runs_deleted:r"]
        self.assertEqual((alert["level"], alert["detail"]["n"], alert["detail"]["actor"], alert["detail"]["branch"]), ("error", 1, "ana", "main"))
        self.assertEqual(sec.evaluate("r", {"runs_deleted": deleted}, sec.settings({}), NOW), {})      # off: nothing
        _, deleted, _ = dr.update([], deleted, [], "main", NOW + 15 * 86400, 14, 50, lambda i: 200)
        self.assertEqual(deleted, [])
        self.assertEqual(sec.penalty(list(found.values()), cfg), cfg["penalty"]["runs_deleted"])


if __name__ == "__main__":
    unittest.main()
