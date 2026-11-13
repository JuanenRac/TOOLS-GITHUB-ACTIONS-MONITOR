# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.6.2: the webhook makes a repository hot, a damaged cache entry is only a miss, the core never imports rich and the lite edition stays out of the way of the complete one."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.data_pipeline import etagcache  # noqa: E402
from github_actions_monitor.security import webhook  # noqa: E402
from test_release_160 import WebhookEvents  # noqa: E402


class WebhookMakesItHot(unittest.TestCase):
    def tearDown(self):
        am.HOT_FORCED.clear()
        am.RUN_CACHE.pop("demo-repo", None)
        del am.LIVE_EVENTS[:]

    def test_an_event_marks_the_repository_and_the_next_cycle_reads_it_even_if_it_is_cold(self):
        am.RUN_CACHE["demo-repo"] = {"runs": [], "at": 1.0, "error": None}
        ok_event = webhook.parse_event("workflow_run", WebhookEvents().payload("workflow_run", **{}))
        ok_event.update({"conclusion": "success", "status": "completed"})
        am.apply_live_event(ok_event, {"runs_per_repo": 20})
        self.assertIn("demo-repo", am.HOT_FORCED)
        self.assertTrue(am.is_hot("demo-repo", am.DEFAULTS, 0))
        # the next cycle reads it (a "success" must not be taken for the final word) and the mark goes away
        am.RUN_CACHE["demo-repo"]["at"] = 10 ** 12          # a cold repository that was read a moment ago
        with mock.patch.object(am, "fetch_runs", return_value=([], None)) as read:
            am.refresh_runs(["demo-repo"], {**am.DEFAULTS, "mode": "full"})
        read.assert_called_once()
        self.assertNotIn("demo-repo", am.HOT_FORCED)

    def test_the_run_list_after_the_event_and_the_poll_agree(self):
        am.RUN_CACHE["demo-repo"] = {"runs": [], "at": 1.0, "error": None}
        record = webhook.parse_event("workflow_run", WebhookEvents().payload("workflow_run"))
        record.update({"conclusion": "success", "status": "completed"})
        am.apply_live_event(record, {"runs_per_repo": 20})
        from_event = am.RUN_CACHE["demo-repo"]["runs"][0]
        polled = {"id": 77, "name": "CI", "conclusion": "success", "status": "completed"}
        self.assertEqual((from_event["id"], from_event["conclusion"], from_event["status"]), (polled["id"], polled["conclusion"], polled["status"]))


class DamagedCache(unittest.TestCase):
    def test_a_304_on_a_damaged_entry_is_a_miss_that_reads_again_and_is_counted(self):
        cache = etagcache.EtagCache(Path(tempfile.mkdtemp()) / "c.json")
        cache.entries["e"] = {"etag": '"a"', "at": 10 ** 12, "data": "not what the API sends"}
        answers = iter([(1, "HTTP/2.0 304 Not Modified\r\n\r\n", "gh: HTTP 304"), (0, 'HTTP/2.0 200 OK\r\nEtag: "b"\r\n\r\n{"ok": 1}', "")])
        data, status = cache.fetch("e", lambda args: next(answers), now=10 ** 12)
        self.assertEqual((data, status), ({"ok": 1}, "200"))
        self.assertEqual(cache.stats()["invalid"], 1)
        self.assertEqual(cache.entries["e"]["etag"], '"b"')

    def test_the_counter_is_in_the_metrics(self):
        from github_actions_monitor.integrations import outputs
        text = outputs.metrics_text({}, {}, extra={"etag": {"saved": 1, "entries": 1, "invalid": 2}})
        self.assertIn("ghamon_etag_invalid_total 2", text)


class CoreWithoutRich(unittest.TestCase):
    def test_importing_the_monitor_and_the_sentinel_never_loads_rich_or_the_terminal_view(self):
        code = ("import sys; sys.path.insert(0, %r); from github_actions_monitor.app import actions_monitor; from github_actions_monitor.sentinels import sentinel_local; from github_actions_monitor.integrations import outputs; from github_actions_monitor.app import settings_api; from github_actions_monitor.integrations import notifiers; from github_actions_monitor.data_pipeline import analytics; from github_actions_monitor.cli import lint_workflows; "
                "bad = [m for m in ('rich', 'textual', 'tui') if m in sys.modules]; print(bad); sys.exit(1 if bad else 0)" % str(HERE / "src"))
        done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_the_release_does_not_require_rich(self):
        import make_release
        self.assertNotIn("rich", " ".join(make_release.REQUIRED_MEMBERS).lower())

    def test_the_terminal_view_follows_the_lite_port(self):
        import os
        from github_actions_monitor.ui import tui
        with mock.patch.dict(os.environ, {"MONITOR_MODE": ""}):
            self.assertEqual((tui.default_port(True), tui.default_port(False)), (8766, 8765))
        with mock.patch.dict(os.environ, {"MONITOR_MODE": "lite"}):
            self.assertEqual(tui.default_port(False), 8766)


class LiteStaysOut(unittest.TestCase):
    def test_lite_writes_neither_ci_red_nor_the_signing_queue_and_uses_other_files(self):
        text = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertRegex(text, r"if not LITE\[\"on\"\]:\n\s+start_sentinel\(config\)")          # ci_red.json and the queue are written by the sentinel only
        saved = (am.LITE["on"], am.CONFIG_FILE, am.LOG_FILE)
        from github_actions_monitor.data_pipeline import etagcache as ec
        saved_cache = ec.CACHE_FILE
        try:
            am.enable_lite()
            names = {am.CONFIG_FILE.name, am.LOG_FILE.name, ec.CACHE_FILE.name}
            self.assertTrue(all("lite" in n for n in names), names)
            self.assertNotIn("ci_red", " ".join(names))
        finally:
            am.LITE["on"], am.CONFIG_FILE, am.LOG_FILE = saved
            ec.CACHE_FILE = saved_cache

    def test_the_readme_warns_not_to_point_both_at_the_same_ci_red_file(self):
        root = HERE.parent
        if not (root / "README.md").is_file():
            self.skipTest("the READMEs live in the repository")
        self.assertIn("ci_red_file", (HERE / "docs" / "LITE.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
