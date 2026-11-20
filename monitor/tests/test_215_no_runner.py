# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A queued run that waits for a label nobody carries is named `no_runner` (switch `ci.stuck.no_runner_check`, off by default) instead of just `queue`."""
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
from github_actions_monitor.data_pipeline import stuckrule  # noqa: E402

RUNNERS = {"runners": [{"state": "online", "labels": ["self-hosted", "Linux", "lab"]}, {"state": "offline", "labels": ["self-hosted", "gpu"]}]}
ON = stuckrule.settings({"ci": {"stuck": {"no_runner_check": True}}})


def queued(age_minutes=10):
    return {"repo": "r", "name": "build", "path": "b.yml", "status": "queued", "seconds": age_minutes * 60, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - age_minutes * 60)), "attempt": 1}


class TheSetting(unittest.TestCase):
    def test_it_is_off_by_default_and_only_true_switches_it_on(self):
        self.assertFalse(stuckrule.settings({})["no_runner_check"])
        self.assertFalse(stuckrule.settings({"ci": {"stuck": {"no_runner_check": "yes"}}})["no_runner_check"])
        self.assertTrue(ON["no_runner_check"])


class TheKnownLabels(unittest.TestCase):
    def test_every_label_of_every_listed_runner_online_or_not(self):
        self.assertEqual(stuckrule.known_labels(RUNNERS), {"self-hosted", "linux", "lab", "gpu"})

    def test_no_list_means_no_answer(self):
        self.assertIsNone(stuckrule.known_labels(None))
        self.assertIsNone(stuckrule.known_labels({"runners": None}))


class TheReason(unittest.TestCase):
    known = stuckrule.known_labels(RUNNERS)

    def test_a_label_nobody_carries_is_named(self):
        self.assertEqual(stuckrule.evaluate(queued(), 120, ON, labels=["self-hosted", "plotter"], known_labels=self.known, now=time.time())[1], "no_runner")

    def test_a_label_of_a_listed_runner_is_just_queue(self):
        self.assertEqual(stuckrule.evaluate(queued(), 120, ON, labels=["self-hosted", "lab"], known_labels=self.known, now=time.time())[1], "queue")

    def test_an_offline_runner_keeps_its_own_reason(self):
        self.assertEqual(stuckrule.evaluate(queued(), 120, ON, labels=["self-hosted", "gpu"], offline_labels=["gpu"], known_labels=self.known, now=time.time())[1], "runner_down")

    def test_github_hosted_and_generic_labels_are_never_missing(self):
        for labels in (["ubuntu-latest"], ["ubuntu-24.04-arm"], ["windows-2022"], ["macos-14-xlarge"], ["self-hosted", "linux", "x64"]):
            self.assertEqual(stuckrule.missing_labels(labels, self.known), [], labels)

    def test_with_the_switch_off_or_no_list_nothing_changes(self):
        off = stuckrule.settings({})
        self.assertEqual(stuckrule.evaluate(queued(), 120, off, labels=["plotter"], known_labels=self.known, now=time.time())[1], "queue")
        self.assertEqual(stuckrule.evaluate(queued(), 120, ON, labels=["plotter"], known_labels=None, now=time.time())[1], "queue")

    def test_a_run_that_is_running_is_not_asked(self):
        run = dict(queued(), status="in_progress")
        self.assertEqual(stuckrule.evaluate(run, 120, ON, labels=["plotter"], known_labels=self.known, now=time.time())[1], "build")

    def test_it_is_stuck_after_the_same_limit_as_a_queue(self):
        self.assertTrue(stuckrule.evaluate(queued(200), 120, ON, labels=["plotter"], known_labels=self.known, now=time.time())[0])
        self.assertFalse(stuckrule.evaluate(queued(5), 120, ON, labels=["plotter"], known_labels=self.known, now=time.time())[0])


if __name__ == "__main__":
    unittest.main()
