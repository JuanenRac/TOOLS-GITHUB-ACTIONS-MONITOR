# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`--demo` is what a person reads to write a client against the frozen contract, so it has to hold it (both editions), and it writes nothing into the folder it runs from (no `ai/LESSONS.md`)."""
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
import check_api_contract as tool
from github_actions_monitor.app import actions_monitor
from test_200_contract import Served

TOOLS = Path(__file__).resolve().parent.parent.parent / "tools" / "demo_monitor.py"


class DemoHoldsTheContract(unittest.TestCase):
    def test_the_demo_of_the_product_holds_it_in_both_editions(self):
        for lite, edition in ((False, "complete"), (True, "lite")):
            with self.subTest(edition=edition):
                served = Served(self, lite=lite)
                with mock.patch.dict(actions_monitor.DEMO, {"on": True}):
                    self.assertEqual(tool.check(tool.make_caller(served.url), edition), [])

    def test_the_organizations_of_the_demo_carry_checked_at(self):
        with mock.patch.dict(actions_monitor.DEMO, {"on": True}):
            box = actions_monitor.discovery_view() if hasattr(actions_monitor, "discovery_view") else None
        if box is None:
            served = Served(self, lite=False)
            with mock.patch.dict(actions_monitor.DEMO, {"on": True}):
                body = tool.make_caller(served.url)("GET", "/api/discovery")[1]
            box = body
        self.assertIn("checked_at", box["organizations"])

    @unittest.skipUnless(TOOLS.is_file(), "tools/demo_monitor.py is only in the repository")
    def test_the_demo_of_the_tools_folder_answers_what_the_update_notice_needs(self):
        text = TOOLS.read_text(encoding="utf-8")
        line = next(ln for ln in text.splitlines() if "am.update_info" in ln)
        for key in ('"checked_at"', '"offline"'):
            self.assertIn(key, line)


class DemoWritesNothing(unittest.TestCase):
    def test_a_new_red_in_the_demo_does_not_write_the_lessons(self):
        from github_actions_monitor.integrations import ai_alerts, lessons
        opened = [{"class": "real", "repo": "r", "workflow": "w", "id": "1"}]
        update = {"opened": opened, "resolved": [], "alerts": []}
        for demo, expected in ((True, 0), (False, 1)):
            with self.subTest(demo=demo), mock.patch.dict(actions_monitor.DEMO, {"on": demo}), \
                    mock.patch.object(ai_alerts, "update", return_value=update), mock.patch.object(lessons, "record") as record, \
                    mock.patch.object(lessons, "write_markdown") as write, mock.patch.object(actions_monitor, "panel_list", return_value=[]), \
                    mock.patch.object(actions_monitor, "ai_state", return_value={}), mock.patch.object(actions_monitor, "red_rows", return_value=[]), \
                    mock.patch.object(actions_monitor, "notify_new_alert", create=True), mock.patch.object(actions_monitor.toolconfig, "github_owner", return_value="o"):
                try:
                    actions_monitor.feed_alerts({}, {"repos": []}, diagnose=False)
                except Exception:      # noqa: BLE001 - only the writes before the notification matter here
                    pass
                self.assertEqual((record.call_count, write.call_count), (expected, expected))


if __name__ == "__main__":
    unittest.main()
