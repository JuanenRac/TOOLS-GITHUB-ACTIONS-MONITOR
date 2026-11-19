# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The curl examples of the guide of the read API are real: the same four commands are in the eight languages, and each address they show answers 200 on a monitor (the cursor is the one the
previous page gave)."""
import re
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor
from test_200_contract import Served

HERE = Path(__file__).resolve().parent.parent
TAILS = ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho")
BLOCK = re.compile(r"```\n((?:curl [^\n]*\n)+)```")


def view(name):
    return {"repo": name, "ecosystem": "HYDRA", "ecosystem_label": "HYDRA", "state": "bad" if name.endswith("0") else "ok", "risk": 3,
            "ci": {"runs_24h": 4, "successes_24h": 3, "failures_24h": 1, "success_rate_24h": 75, "red_workflows": ["a"], "stuck_runs": 0},
            "alerts": {"total": 2, "by_sentinel": {}, "by_level": {}, "items": []}, "readiness": None, "activity": {"last_run_at": None, "runs_7d": 9, "idle_days": 0},
            "sources": {}, "not_fully_seen": []}


def examples(tail=""):
    text = (HERE / "docs" / f"API{tail}.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    blocks = [b for b in BLOCK.findall(text) if "/api/v1/" in b]
    return blocks[0].strip().split("\n") if blocks else []


class TheExamples(unittest.TestCase):
    def test_the_eight_languages_show_the_same_commands(self):
        english = examples()
        self.assertEqual(len(english), 4)
        for tail in TAILS[1:]:
            self.assertEqual(examples(tail), english, tail)

    def test_each_address_answers_and_the_cursor_is_the_one_of_the_previous_page(self):
        import http.client
        import json
        served = Served(self, lite=False)
        views = [view("repo%03d" % n) for n in range(120)]
        for patcher in (mock.patch.object(actions_monitor, "service_mode", return_value=True), mock.patch.object(actions_monitor, "health_views", return_value=views)):
            patcher.start()
            self.addCleanup(patcher.stop)
        cursor = ""
        for line in examples():
            address = re.search(r'"?(http://127\.0\.0\.1:8765(/api/v1/[^"\s]*))"?', line)
            self.assertIsNotNone(address, line)
            self.assertIn("X-Monitor-Access", line)
            path = address.group(2)
            if "THE_NEXT_CURSOR" in path:
                status, raw, _ = served.raw("GET", "/api/v1/repos?limit=50")      # the page before: its next_cursor is what the example needs
                cursor = json.loads(raw)["next_cursor"]
                self.assertTrue(cursor)
                path = path.replace("THE_NEXT_CURSOR", cursor)
            status, raw, _ = served.raw("GET", path)
            self.assertEqual(status, 200, line)
            json.loads(raw)
        self.assertTrue(cursor, "the guide shows how to follow the cursor")

    def test_the_header_of_the_examples_is_the_one_the_monitor_reads(self):
        self.assertIn("X-Monitor-Access", (HERE / "src" / "github_actions_monitor" / "security" / "localguard.py").read_text(encoding="utf-8") + (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
