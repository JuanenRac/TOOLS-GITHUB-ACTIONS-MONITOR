# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The monitor watches its own memory and threads: real numbers, a verdict with a threshold that is a setting, one note when it goes high and one when it comes back, relief when it goes high, the answer
of /api/health carries it, and a job of the CI runs the monitor in a container with one processor and 512 MB with a simulated account of 120 workflows."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(ROOT / "tools"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor, selfwatch, settings_api  # noqa: E402

try:
    import limits_check  # noqa: E402
except ImportError:      # the tools of the repository do not travel with the zip of the product
    limits_check = None


def reading(rss, threads, at=1000):
    return {"rss_mb": rss, "threads": threads, "cpu_percent": 5.0, "at": at, "_wall": at, "_cpu": 0.0}


class Numbers(unittest.TestCase):
    def test_the_numbers_are_real(self):
        first = selfwatch.sample()
        self.assertGreater(first["threads"], 0)
        self.assertIsNone(first["cpu_percent"])      # the first reading has nothing to compare with
        if first["rss_mb"] is not None:
            self.assertGreater(first["rss_mb"], 5)
        blob = bytearray(40 * 1024 * 1024)      # 40 MB that are touched really show in the next reading
        for i in range(0, len(blob), 4096):
            blob[i] = 1
        second = selfwatch.sample(first)
        if first["rss_mb"] is not None and sys.platform.startswith(("linux", "win")):
            self.assertGreater(second["rss_mb"], first["rss_mb"] + 20)
        self.assertIsNotNone(second["cpu_percent"])
        del blob

    def test_the_settings_keep_to_their_ranges(self):
        self.assertEqual(selfwatch.settings({}), selfwatch.DEFAULTS)
        got = selfwatch.settings({"selfwatch": {"enabled": False, "rss_warn_mb": 1, "threads_warn": "x", "interval_seconds": 30}})
        self.assertEqual((got["enabled"], got["rss_warn_mb"], got["threads_warn"], got["interval_seconds"]), (False, 1024, 400, 30))
        self.assertEqual(actions_monitor.DEFAULTS["selfwatch"], selfwatch.DEFAULTS)
        for key in ("selfwatch.enabled", "selfwatch.rss_warn_mb", "selfwatch.threads_warn", "selfwatch.interval_seconds"):
            self.assertIn(key, settings_api.FIELDS)


class Verdict(unittest.TestCase):
    def setUp(self):
        self.notes = []
        self.watch = selfwatch.Watch(note=lambda origin, text: self.notes.append((origin, text)))
        self.watch.configure({"selfwatch": {"rss_warn_mb": 500, "threads_warn": 100}})
        self.relieved = []
        self.watch.relief = [lambda: self.relieved.append(1)]

    def test_going_high_is_noted_once_with_its_numbers_and_relieves_and_coming_back_is_noted_too(self):
        self.assertEqual(self.watch.tick(reading(300, 20))["state"], "ok")
        self.assertEqual(self.notes, [])
        snap = self.watch.tick(reading(600, 20, at=1060))
        self.assertEqual((snap["state"], snap["high_since"]), ("high", 1060))
        self.assertIn("600", snap["reason"])
        self.watch.tick(reading(700, 20, at=1120))      # still high: no second note, no second relief
        self.assertEqual([n[0] for n in self.notes], ["selfwatch.high"])
        self.assertEqual(self.relieved, [1])
        self.assertEqual(self.watch.tick(reading(200, 20, at=1180))["state"], "ok")
        self.assertEqual([n[0] for n in self.notes], ["selfwatch.high", "selfwatch.ok"])

    def test_too_many_threads_count_too_and_a_number_that_cannot_be_read_is_not_a_verdict(self):
        self.assertEqual(self.watch.tick(reading(100, 150))["state"], "high")
        self.assertEqual(self.watch.tick(reading(None, None))["state"], "ok")

    def test_a_relief_or_a_note_that_breaks_never_stops_the_watch(self):
        def boom(*args):
            raise RuntimeError("x")
        self.watch.note = boom
        self.watch.relief = [boom]
        self.assertEqual(self.watch.tick(reading(900, 1))["state"], "high")

    def test_the_health_answer_carries_it(self):
        payload = actions_monitor.health_payload()
        self.assertIn(payload["selfwatch"]["state"], ("ok", "high"))
        self.assertEqual(set(payload["selfwatch"]), {"state", "reason", "rss_mb", "threads", "cpu_percent", "rss_warn_mb", "threads_warn", "high_since"})
        json.dumps(payload)


@unittest.skipIf(limits_check is None, "the tools of the repository are not in this folder")
class Limits(unittest.TestCase):
    def test_an_account_of_120_workflows_is_built_and_answered_within_the_limits(self):
        import subprocess
        done = subprocess.run([sys.executable, str(ROOT / "tools" / "limits_check.py"), "--repos", "120", "--requests", "24", "--max-rss-mb", "400"], capture_output=True, text=True, timeout=300)      # a process of its own: its memory is the monitor's, not the one of the whole suite
        self.assertEqual(done.returncode, 0, done.stdout[-1500:] + done.stderr[-500:])
        self.assertIn('"repos": 120', done.stdout)

    def test_the_ci_runs_it_in_a_container_with_one_processor_and_512_mb(self):
        path = ROOT / ".github" / "workflows" / "ci.yml"
        if not path.is_file():
            self.skipTest("the workflows are not part of the package")
        text = path.read_text(encoding="utf-8")
        block = text.split("\n  limits:\n")[1].split("\n  pictures:\n")[0]
        self.assertIn("--cpus 1", block)
        self.assertIn("--memory 512m", block)
        self.assertIn("tools/limits_check.py", block)
        self.assertIn("timeout-minutes:", block)


if __name__ == "__main__":
    unittest.main()
