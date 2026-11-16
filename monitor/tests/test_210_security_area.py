# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Security sentinel and the score: "could not be read" is never "clean", a few repositories that always fail do not starve the rest, a source that stops answering does not close its alert as fixed."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from test_191_sentinel import Fake, NOW, build, dep, quiet_repo  # noqa: E402


class Registry:
    def __init__(self, sentinel):
        self.sentinel = sentinel

    def get(self, name):
        return self.sentinel if name == "security" else None


def blind(fake):
    for fragment in ("dependabot/alerts", "code-scanning/alerts", "secret-scanning/alerts"):
        fake.set(fragment, 403)


class UnreadableIsNotClean(unittest.TestCase):
    def test_a_sentinel_that_can_read_nothing_is_not_ok_and_gives_the_score_no_security_part(self):
        sentinel, fake, _ = build(self, repos=("r1", "r2", "r3"))
        quiet_repo(fake)
        blind(fake)
        for _ in range(2):
            sentinel.tick(NOW)
        status = sentinel.get_status()
        self.assertEqual(status["repos_checked"], 3)
        self.assertEqual((status["sources_readable"], status["sources_total"]), (0, 9))
        self.assertNotEqual(status["level"], "ok")
        self.assertEqual(status["lifecycle"], "degraded")
        self.assertIsNone(actions_monitor.score_security(Registry(sentinel), {}))

    def test_half_of_the_sources_readable_is_enough_when_the_score_asks_for_half_and_not_when_it_asks_for_more(self):
        sentinel, fake, _ = build(self, repos=("r1", "r2"))
        quiet_repo(fake)
        fake.set("secret-scanning/alerts", 403)
        sentinel.tick(NOW)
        self.assertEqual(sentinel.source_coverage(), (4, 6))
        self.assertEqual(sentinel.get_status()["level"], "ok")
        self.assertIsNotNone(actions_monitor.score_security(Registry(sentinel), {}))
        self.assertIsNone(actions_monitor.score_security(Registry(sentinel), {"score": {"min_coverage": 0.9}}))

    def test_everything_readable_stays_ok(self):
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        sentinel.tick(NOW)
        self.assertEqual(sentinel.get_status()["level"], "ok")
        self.assertEqual(actions_monitor.score_security(Registry(sentinel), {}), {"penalty": 0, "repos": 1})

    def test_a_gh_that_prints_nothing_is_not_a_clean_reading(self):
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        real = fake.run_gh

        def silent(args):
            return (0, "", "") if "dependabot" in args[-1] else real(args)
        sentinel.ctx["run_gh"] = silent
        sentinel.tick(NOW)
        self.assertNotIn("dependabot", (sentinel.state["per_repo"]["r"].get("facts") or {}))
        self.assertIn("r", sentinel.errors)
        self.assertNotEqual(sentinel.get_status()["level"], "ok")

    def test_a_branch_with_a_slash_is_asked_for_encoded(self):
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        fake.set("repos/acme/r", 200, {"default_branch": "release/1.x", "archived": False}, '"repo1"')
        sentinel.tick(NOW)
        self.assertTrue(any(call[-1].endswith("branches/release%2F1.x/protection") for call in fake.calls), fake.calls)


class AnAlertWhoseSourceGoesSilent(unittest.TestCase):
    def test_a_403_after_an_open_alert_keeps_it_marked_unread_and_never_says_fixed(self):
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        fake.set("dependabot/alerts", 200, [dep("critical")], '"d1"')
        sentinel.tick(NOW)
        fake.set("dependabot/alerts", 403)
        sentinel.tick(NOW + 2000)
        alerts = sentinel.get_alerts()
        self.assertEqual([a["code"] for a in alerts], ["security.dependabot"])
        self.assertIn("unread_since", alerts[0]["details"])
        self.assertEqual(sentinel.get_metrics()["security_penalty"], 25)
        self.assertEqual([e["kind"] for batch in sentinel.listened for e in batch if e["kind"] == "security_fixed"], [])

    def test_when_it_answers_again_the_marker_goes_and_a_real_fix_is_announced(self):
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        fake.set("dependabot/alerts", 200, [dep("critical")], '"d1"')
        sentinel.tick(NOW)
        fake.set("dependabot/alerts", 403)
        sentinel.tick(NOW + 2000)
        fake.set("dependabot/alerts", 200, [], '"d3"')
        sentinel.tick(NOW + 4000)
        self.assertEqual(sentinel.get_alerts(), [])
        self.assertEqual([e["kind"] for batch in sentinel.listened for e in batch], ["security_fixed"])

    def test_after_a_week_without_reading_it_is_dropped_but_still_not_called_fixed(self):
        from github_actions_monitor.sentinels import sentinel_security as ss
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        fake.set("dependabot/alerts", 200, [dep("critical")], '"d1"')
        sentinel.tick(NOW)
        fake.set("dependabot/alerts", 403)
        sentinel.tick(NOW + 2000)
        sentinel.tick(NOW + 2000 + ss.UNREAD_KEEP)
        self.assertEqual(sentinel.get_alerts(), [])
        self.assertEqual([e for batch in sentinel.listened for e in batch if e["kind"] == "security_fixed"], [])


class RepositoriesThatAlwaysFail(unittest.TestCase):
    def test_five_that_fail_forever_do_not_keep_the_healthy_ones_from_being_looked_at(self):
        names = [f"a{i}" for i in range(5)] + [f"z{i:02d}" for i in range(10)]
        sentinel, fake, _ = build(self, repos=names)
        quiet_repo(fake)
        real = fake.run_gh

        def run(args):
            return (1, "", "HTTP 500") if "/a" in args[-1].split("?")[0].replace("repos/acme/", "/") and args[-1].startswith("repos/acme/a") else real(args)
        fake.set("repos/acme/", 200, {"default_branch": "main", "archived": False}, '"x"')
        sentinel.ctx["run_gh"] = run
        for n in range(4):
            sentinel.tick(NOW + n * 1800)
        seen = [r for r in names if (sentinel.state["per_repo"].get(r) or {}).get("scanned")]
        self.assertEqual(sorted(seen), sorted(n for n in names if n.startswith("z")))

    def test_the_wait_grows_with_each_failure(self):
        from github_actions_monitor.sentinels import sentinel_security as ss
        sentinel, fake, _ = build(self)
        sentinel.ctx["run_gh"] = lambda args: (1, "", "HTTP 500")
        waits = []
        now = NOW
        for _ in range(4):
            sentinel.tick(now)
            waits.append(sentinel.state["per_repo"]["r"]["retry"] - now)
            now = sentinel.state["per_repo"]["r"]["retry"]
        self.assertEqual(waits, [ss.RETRY_AFTER[0], ss.RETRY_AFTER[1], ss.RETRY_AFTER[2], ss.RETRY_AFTER[2]])


if __name__ == "__main__":
    unittest.main()
