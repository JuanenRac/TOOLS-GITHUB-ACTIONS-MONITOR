# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Imported first by every test module: the tests run in English and as the same GitHub owner whatever the system language and the logged-in account are.
A test that checks another language switches it with `with i18n.use_language("es"):` (see tests/test_i18n.py)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["MONITOR_TARGETS_FILE"] = str(Path(__file__).resolve().parent / "fixtures" / "fixture_targets.json")          # the maintainer's catalogue, whatever the configuration says
os.environ["MONITOR_ECOSYSTEMS_FILE"] = str(Path(__file__).resolve().parent / "fixtures" / "fixture_ecosystems.json")
os.environ["MONITOR_PROFILES_FILE"] = str(Path(__file__).resolve().parent / "fixtures" / "fixture_profiles.json")
import i18n  # noqa: E402
import toolconfig  # noqa: E402

i18n.set_language("en")
toolconfig.set_owner("JuanenRac")


WATCHED = ("actions_monitor.json", "actions_monitor_lite.json", "update_check.json", "update_check_lite.json", "actions_monitor_log.txt", "actions_monitor_log_lite.txt",
           "github_actions_log.jsonl", "ai_actions_log.jsonl", "collab_state.json", "alert_mutes.json")


def guard(case):
    """Registers a cleanup on a TestCase: the files of the monitor that this test creates next to the code (the template of a first start, the update notice) are removed afterwards. Only
    what did not exist before is removed."""
    folder = Path(__file__).resolve().parent.parent
    before = {name for name in WATCHED if (folder / name).exists()}

    def remove_new():
        for name in WATCHED:
            if name not in before:
                try:
                    (folder / name).unlink()
                except OSError:
                    pass
    case.addCleanup(remove_new)
    return remove_new


import unittest  # noqa: E402


class Spanish:
    """Mixin for the test classes whose expectations are the Spanish texts: `class X(_testenv.Spanish, unittest.TestCase)`."""

    def setUp(self):
        super().setUp()
        i18n.set_language("es")

    def tearDown(self):
        i18n.set_language("en")
        super().tearDown()
