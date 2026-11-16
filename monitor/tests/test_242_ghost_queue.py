# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Runs that stay in the queue for days or months because GitHub never starts them (a closed pull request, a job that asks for a runner that does not exist): a ghost queue. They are not queued, not
stuck and not a red; they are counted and listed apart, and give one information notice per repository. The ages are the ones measured on public repositories."""
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am, settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import stuckrule  # noqa: E402
from github_actions_monitor.sentinels import sentinel_ci, sentinel_local  # noqa: E402

NOW = 1_800_000_000.0
DAY = 86400
# (repository, days the oldest queued run has waited) as measured
MEASURED = [("codex", 280), ("bun", 256), ("openssl", 239), ("micropython", 185), ("warp", 185), ("curl", 185), ("buzz", 102), ("mise", 90), ("Cap", 64), ("zephyr", 17)]


def stamp(days_ago):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - days_ago * DAY))


def queued(ident, repo="demo", days=0.1, attempt=1, status="queued"):
    return {"id": ident, "repo": repo, "name": "ci", "status": status, "conclusion": None, "event": "push", "branch": "main", "sha": "abc", "actor": "x", "url": f"https://x/{ident}",
            "seconds": None if days > 35 else int(days * DAY), "started": stamp(days), "path": "ci.yml", "attempt": attempt}


class TheRule(unittest.TestCase):
    cfg = stuckrule.settings({})

    def test_the_default_is_on_and_seven_days(self):
        self.assertEqual((self.cfg["ghost_enabled"], self.cfg["ghost_days"]), (True, 7))

    def test_every_measured_queue_is_a_ghost_and_never_stuck(self):
        for n, (repo, days) in enumerate(MEASURED):
            run = queued(n, repo, days)
            stuck, reason, _limit = stuckrule.evaluate(run, 120, self.cfg, now=NOW)
            self.assertEqual((stuck, reason), (False, "ghost"), (repo, days))

    def test_a_queue_of_hours_is_still_a_queue_and_can_still_be_stuck(self):
        self.assertEqual(stuckrule.evaluate(queued(1, days=0.02), 120, self.cfg, now=NOW)[:2], (False, "queue"))
        self.assertEqual(stuckrule.evaluate(queued(2, days=1), 120, self.cfg, now=NOW)[:2], (True, "queue"))
        self.assertEqual(stuckrule.evaluate(queued(3, days=6.9), 120, self.cfg, now=NOW)[:2], (True, "queue"))

    def test_the_limit_is_in_days_and_comes_from_the_configuration(self):
        cfg = stuckrule.settings({"ci": {"stuck": {"ghost_days": 30}}})
        self.assertEqual(stuckrule.evaluate(queued(1, days=20), 120, cfg, now=NOW)[1], "queue")
        self.assertEqual(stuckrule.evaluate(queued(2, days=31), 120, cfg, now=NOW)[1], "ghost")

    def test_the_switch_turns_the_whole_thing_off(self):
        cfg = stuckrule.settings({"ci": {"stuck": {"ghost_enabled": False}}})
        self.assertEqual(stuckrule.evaluate(queued(1, days=20), 120, cfg, now=NOW)[:2], (True, "queue"))

    def test_a_running_build_and_a_run_waiting_for_approval_are_never_ghosts(self):
        run = queued(1, days=30, status="in_progress")
        self.assertEqual(stuckrule.evaluate(run, 120, self.cfg, now=NOW)[1], "build")
        waiting = queued(2, days=30, status="waiting")
        self.assertEqual(stuckrule.evaluate(waiting, 120, self.cfg, now=NOW)[1], "awaiting_approval")

    def test_a_rerun_is_never_a_ghost_because_its_creation_date_is_the_first_try(self):
        self.assertEqual(stuckrule.evaluate(queued(1, days=200, attempt=2), 120, self.cfg, now=NOW)[1], "queue")
        self.assertIsNone(stuckrule.queue_age_days(queued(1, days=200, attempt=3), NOW))

    def test_a_bad_value_keeps_the_default(self):
        for bad in (0, -1, "7", True, 4000, None):
            self.assertEqual(stuckrule.settings({"ci": {"stuck": {"ghost_days": bad}}})["ghost_days"], 7, bad)
        self.assertTrue(stuckrule.settings({"ci": {"stuck": {"ghost_enabled": "no"}}})["ghost_enabled"])

    def test_an_unreadable_date_is_not_a_ghost(self):
        run = queued(1)
        run["started"] = "yesterday"
        self.assertEqual(stuckrule.evaluate(run, 120, self.cfg, now=NOW)[1], "queue")


class TheMonitor(unittest.TestCase):
    def build(self, runs, ghost_enabled=True):
        cache = {"demo": {"runs": runs, "at": 0, "error": None}}
        saved = (dict(am.RUN_CACHE), am.LITE["on"], dict(am.ISSUE_CACHE))
        am.RUN_CACHE.clear()
        am.RUN_CACHE.update(cache)
        am.LITE["on"] = False
        am.ISSUE_CACHE.update({"items": [], "at": time.time(), "busy": False})
        config = {"stuck_minutes": 60, "issues_refresh_seconds": 10 ** 6, "mode": "normal", "min_rate_remaining": 100, "refresh_seconds": 60, "max_workers": 1, "runs_per_repo": 30,
                  "ci": {"stuck": {"ghost_enabled": ghost_enabled}}}
        try:
            with mock.patch.object(am, "gh", side_effect=RuntimeError("offline")), mock.patch.object(am, "run_jobs", return_value=[]), mock.patch("time.time", return_value=NOW):
                return am.build(config, ["demo"], NOW, 0, False, "")
        finally:
            am.RUN_CACHE.clear()
            am.RUN_CACHE.update(saved[0])
            am.LITE["on"] = saved[1]
            am.ISSUE_CACHE.update(saved[2])

    def test_ghosts_leave_the_list_and_the_counts_and_are_counted_apart(self):
        runs = [queued(1, days=200), queued(2, days=90), queued(3, days=0.01), queued(4, days=0.01, status="in_progress")]
        data = self.build(runs)
        self.assertEqual(sorted(r["id"] for r in data["active"]), [3, 4])
        self.assertEqual((data["figures"]["queued"], data["figures"]["active"], data["figures"]["ghost"], data["figures"]["ghost_days"]), (1, 1, 2, 7))
        self.assertEqual(sorted(g["id"] for g in data["ghosts"]), [1, 2])
        self.assertFalse(any(r.get("stuck") for r in data["active"]))

    def test_with_the_switch_off_nothing_changes_for_the_old_behaviour(self):
        data = self.build([queued(1, days=20)], ghost_enabled=False)
        self.assertEqual((len(data["active"]), data["figures"]["ghost"], data["ghosts"]), (1, 0, []))
        self.assertTrue(data["active"][0]["stuck"])


class TheNotice(unittest.TestCase):
    SNAP = {"enabled": True, "generated": "2030-01-01T00:00:00Z", "loading": "", "level": "ok", "errors": [], "a2": {"red": []}, "a5": {"pending_sign": []}, "totals": {},
            "a1": {"stuck": [], "ghost_days": 7, "ghosts": [{"repo": "codex", "id": 1, "url": "https://x/1", "since": "2026-02-01T00:00:00Z"}, {"repo": "codex", "id": 2, "url": "https://x/2", "since": "2026-03-01T00:00:00Z"},
                                                        {"repo": "bun", "id": 3, "url": "https://x/3", "since": "2026-04-01T00:00:00Z"}]}}

    def make(self, tmp):
        from test_171 import ctx_stub
        with mock.patch.object(sentinel_local, "CACHE_FILE", Path(tmp) / "c.json"), mock.patch.object(sentinel_local, "HISTORY_FILE", Path(tmp) / "h.json"):
            return sentinel_ci.SentinelCI(ctx_stub(), {})

    def test_one_information_notice_per_repository_never_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ci = self.make(tmp)
            ci.core.last_snap = self.SNAP
            alerts = ci.get_alerts()
        self.assertEqual([(a["code"], a["level"], a["repo"]) for a in alerts], [("ci.ghost_queue", "info", "bun"), ("ci.ghost_queue", "info", "codex")])
        self.assertEqual(alerts[1]["details"]["count"], 2)
        self.assertEqual(alerts[1]["details"]["oldest"], "2026-02-01T00:00:00Z")
        self.assertIn("2 runs", alerts[1]["title"])

    def test_the_title_is_translated(self):
        with tempfile.TemporaryDirectory() as tmp:
            ci = self.make(tmp)
            ci.core.last_snap = self.SNAP
            with i18n.use_language("es"):
                self.assertIn("2 ejecuciones", ci.get_alerts()[1]["title"])


class TheSettings(unittest.TestCase):
    def test_the_two_settings_are_in_the_schema_with_texts_in_eight_languages(self):
        import json
        for key in ("ci.stuck.ghost_enabled", "ci.stuck.ghost_days"):
            self.assertIn(key, settings_api.META)
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            texts = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in ("ci.stuck.ghost_enabled", "ci.stuck.ghost_days"):
                self.assertTrue(texts.get("cfg.f." + key) and texts.get("cfg.h." + key), (lang, key))
            for key in ("ui.n_ghost", "ui.stuck_why_ghost", "evt.ghost_queue"):
                self.assertTrue(texts.get(key), (lang, key))

    def test_the_page_shows_the_line(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("now-ghost", page)
        self.assertIn("ui.n_ghost", page)


if __name__ == "__main__":
    unittest.main()
