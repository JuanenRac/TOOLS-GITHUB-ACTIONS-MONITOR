# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The notice of a newer version names the exact command of the way the monitor was installed (unpacked product, service, container, pipx, uv, gh extension), in the eight languages."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import updatecheck  # noqa: E402

NO = lambda path: False  # noqa: E731


class Channel(unittest.TestCase):
    def test_every_way_of_installing_is_told_apart(self):
        c = updatecheck.install_channel
        self.assertEqual(c({}, "C:/Tools/monitor/src/x.py", NO), "zip")
        self.assertEqual(c({"MONITOR_SERVICE": "1"}, "/opt/monitor/src", NO), "service")
        self.assertEqual(c({"INVOCATION_ID": "abc"}, "/opt/monitor/src", NO), "service")
        self.assertEqual(c({}, "/opt/monitor", lambda p: p == "/.dockerenv"), "docker")
        self.assertEqual(c({"MONITOR_IN_CONTAINER": "1"}, "/app", NO), "docker")
        self.assertEqual(c({}, "/home/u/.local/pipx/venvs/github-actions-monitor/lib/x.py", NO), "pipx")
        self.assertEqual(c({}, "C:\\Users\\u\\AppData\\Roaming\\uv\\tools\\github-actions-monitor\\lib", NO), "uv")
        self.assertEqual(c({}, "/home/u/.local/share/gh/extensions/gh-actions-monitor/x.py", NO), "gh-extension")
        self.assertEqual(c({"MONITOR_SERVICE": "1"}, "/home/u/.local/pipx/venvs/m/x.py", NO), "pipx")      # what it was installed with wins over how it is run

    def test_every_channel_has_a_command_and_the_container_one_names_the_new_tag(self):
        for channel in updatecheck.CHANNELS:
            self.assertTrue(updatecheck.update_command(channel, "v2.1.7"), channel)
        self.assertEqual(updatecheck.update_command("docker", "v2.1.7"), "docker pull ghcr.io/juanenrac/tools-github-actions-monitor:2.1.7")
        self.assertIn("monitor_cli.py update", updatecheck.update_command("zip", "2.1.7"))
        self.assertEqual(updatecheck.update_command("unknown", "2.1.7"), updatecheck.update_command("zip", "2.1.7"))

    def test_the_notice_carries_the_command_in_every_language(self):
        info = {"newer": True, "latest": "9.9.9", "current": "2.1.5", "url": "https://github.com/x", "command": "docker pull ghcr.io/x:9.9.9"}
        for lang in i18n.LANGS:
            line = updatecheck.notice(info, lambda key, **kw: i18n.tl(lang, key).format(**kw))
            self.assertIn("docker pull ghcr.io/x:9.9.9", line, lang)
            self.assertIn("9.9.9", line, lang)
        self.assertEqual(updatecheck.notice({"newer": False}, lambda *a, **k: "x"), "")

    def test_the_view_gives_the_channel_and_the_command_only_when_there_is_something_newer(self):
        state = {"checked_at": 1, "release": {"tag": "v9.9.9", "url": "", "published": ""}}
        newer = updatecheck.view({}, "2.1.5", state)
        self.assertTrue(newer["newer"])
        self.assertIn(newer["channel"], updatecheck.CHANNELS)
        self.assertTrue(newer["command"])
        same = updatecheck.view({}, "9.9.9", state)
        self.assertEqual((same["newer"], same["command"]), (False, ""))


if __name__ == "__main__":
    unittest.main()
