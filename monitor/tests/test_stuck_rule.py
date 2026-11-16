# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""When a run is stuck: the classic single limit stays the default; a learned limit per workflow, fixed limits per workflow or runner label, a longer limit for the queue of runners,
and the reason why a run waits. Synthetic runs only."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import stuckrule  # noqa: E402


def done(n, minutes, path="build.yml", conclusion="success", repo="demo"):
    return {"repo": repo, "id": n, "path": path, "name": path, "status": "completed", "conclusion": conclusion, "seconds": minutes * 60}


def live(minutes, status="in_progress", path="build.yml", repo="demo"):
    return {"repo": repo, "id": 99, "path": path, "name": path, "status": status, "conclusion": None, "seconds": minutes * 60}


class StuckDefaults(unittest.TestCase):
    def test_default_is_the_single_limit(self):
        cfg = stuckrule.settings({})
        self.assertFalse(cfg["learned"])
        self.assertEqual(stuckrule.evaluate(live(119), 120, cfg)[0], False)
        self.assertEqual(stuckrule.evaluate(live(121), 120, cfg)[0], True)
        self.assertEqual(stuckrule.evaluate(live(121, "queued"), 120, cfg)[0], True)

    def test_invalid_values_keep_the_defaults(self):
        cfg = stuckrule.settings({"ci": {"stuck": {"percentile": "x", "margin": 0, "min_samples": True, "workflow_minutes": ["bad", "a=zz", "ok.yml=5"], "queue_minutes": -3}}})
        self.assertEqual((cfg["percentile"], cfg["margin"], cfg["min_samples"], cfg["queue_minutes"]), (95, 2.0, 3, 0))
        self.assertEqual(cfg["workflow_minutes"], [("ok.yml", 5)])

    def test_reasons(self):
        cfg = stuckrule.settings({})
        self.assertEqual(stuckrule.evaluate(live(1), 120, cfg)[1], "build")
        self.assertEqual(stuckrule.evaluate(live(1, "queued"), 120, cfg)[1], "queue")
        self.assertEqual(stuckrule.evaluate(live(1, "waiting"), 120, cfg)[1], "awaiting_approval")
        self.assertEqual(stuckrule.evaluate(live(1, "queued"), 120, cfg, labels=["gpu"], offline_labels=["gpu"])[1], "runner_down")


class LearnedLimit(unittest.TestCase):
    CFG = {"ci": {"stuck": {"learned": True, "min_minutes": 30, "max_minutes": 720}}}

    def test_a_six_hour_build_is_not_stuck_at_hour_three(self):
        cfg = stuckrule.settings(self.CFG)
        learned = stuckrule.learn([done(i, 330 + i) for i in range(4)], cfg)
        self.assertEqual(learned[("demo", "build.yml")], 666)      # 95th percentile (333 min) x 2, inside the minimum and the maximum
        self.assertFalse(stuckrule.evaluate(live(180), 120, cfg, learned)[0])
        self.assertFalse(stuckrule.evaluate(live(660), 120, cfg, learned)[0])
        self.assertTrue(stuckrule.evaluate(live(667), 120, cfg, learned)[0])
        capped = stuckrule.settings({"ci": {"stuck": {"learned": True, "max_minutes": 400}}})
        self.assertEqual(stuckrule.learn([done(i, 330 + i) for i in range(4)], capped)[("demo", "build.yml")], 400)

    def test_a_quick_workflow_is_stuck_sooner_but_never_below_the_minimum(self):
        cfg = stuckrule.settings(self.CFG)
        learned = stuckrule.learn([done(i, 2) for i in range(5)], cfg)
        self.assertEqual(learned[("demo", "build.yml")], 30)
        self.assertTrue(stuckrule.evaluate(live(31), 120, cfg, learned)[0])
        self.assertFalse(stuckrule.evaluate(live(29), 120, cfg, learned)[0])

    def test_too_few_samples_or_failures_keep_the_common_limit(self):
        cfg = stuckrule.settings(self.CFG)
        self.assertEqual(stuckrule.learn([done(1, 300), done(2, 300)], cfg), {})
        self.assertEqual(stuckrule.learn([done(i, 300, conclusion="failure") for i in range(6)], cfg), {})
        self.assertTrue(stuckrule.evaluate(live(130), 120, cfg, {})[0])

    def test_learning_is_off_by_default(self):
        cfg = stuckrule.settings({})
        learned = {("demo", "build.yml"): 720}
        self.assertTrue(stuckrule.evaluate(live(130), 120, cfg, learned)[0])

    def test_workflows_are_learned_apart(self):
        cfg = stuckrule.settings(self.CFG)
        runs = [done(i, 300) for i in range(3)] + [done(10 + i, 5, path="lint.yml") for i in range(3)] + [done(20 + i, 5, repo="other") for i in range(3)]
        learned = stuckrule.learn(runs, cfg)
        self.assertEqual(sorted(learned), [("demo", "build.yml"), ("demo", "lint.yml"), ("other", "build.yml")])
        self.assertEqual(learned[("demo", "lint.yml")], 30)


class FixedLimits(unittest.TestCase):
    def test_workflow_limit_beats_runner_label_and_learned(self):
        cfg = stuckrule.settings({"ci": {"stuck": {"learned": True, "workflow_minutes": ["build.yml=420"], "runner_minutes": ["self-hosted=60"]}}})
        self.assertEqual(stuckrule.evaluate(live(300), 120, cfg, {("demo", "build.yml"): 45}, labels=["self-hosted"]), (False, "build", 420))
        self.assertTrue(stuckrule.evaluate(live(421), 120, cfg, labels=["self-hosted"])[0])

    def test_runner_label_limit(self):
        cfg = stuckrule.settings({"ci": {"stuck": {"runner_minutes": ["gpu-*=600"]}}})
        self.assertFalse(stuckrule.evaluate(live(500), 120, cfg, labels=["linux", "gpu-large"])[0])
        self.assertTrue(stuckrule.evaluate(live(500), 120, cfg, labels=["linux"])[0])

    def test_queue_limit_only_changes_runs_that_wait_for_a_runner(self):
        cfg = stuckrule.settings({"ci": {"stuck": {"queue_minutes": 600}}})
        self.assertFalse(stuckrule.evaluate(live(300, "queued"), 120, cfg)[0])
        self.assertTrue(stuckrule.evaluate(live(300), 120, cfg)[0])

    def test_awaiting_approval_can_be_exempt(self):
        cfg = stuckrule.settings({"ci": {"stuck": {"awaiting_stuck": False}}})
        self.assertEqual(stuckrule.evaluate(live(900, "waiting"), 120, cfg)[:2], (False, "awaiting_approval"))
        self.assertTrue(stuckrule.evaluate(live(900, "waiting"), 120, stuckrule.settings({}))[0])

    def test_offline_labels_are_the_ones_only_offline_runners_carry(self):
        payload = {"runners": [{"state": "offline", "labels": ["self-hosted", "linux", "gpu"]}, {"state": "idle", "labels": ["self-hosted", "linux", "small"]}]}
        self.assertEqual(stuckrule.offline_labels(payload), {"gpu"})
        self.assertEqual(stuckrule.offline_labels(None), set())


class Wiring(unittest.TestCase):
    def test_settings_are_editable_with_checks(self):
        for path, good, bad in (("ci.stuck.learned", True, "yes"), ("ci.stuck.percentile", 90, 10), ("ci.stuck.workflow_minutes", ["build.yml=420"], ["build.yml"]),
                                ("ci.stuck.runner_minutes", ["self-hosted=720"], ["a=b"]), ("ci.stuck.queue_minutes", 0, -1)):
            self.assertTrue(settings_api.check_value(path, good)[0], path)
            self.assertFalse(settings_api.check_value(path, bad)[0], path)

    def test_defaults_do_not_change_the_behaviour(self):
        block = actions_monitor.DEFAULTS["ci"]["stuck"]
        self.assertFalse(block["learned"])
        self.assertEqual((block["queue_minutes"], block["workflow_minutes"], block["runner_minutes"], block["awaiting_stuck"]), (0, [], [], True))
        self.assertEqual(actions_monitor.DEFAULTS["stuck_minutes"], 120)


if __name__ == "__main__":
    unittest.main()
