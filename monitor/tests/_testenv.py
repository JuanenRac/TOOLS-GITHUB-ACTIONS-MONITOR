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


import unittest  # noqa: E402


class Spanish:
    """Mixin for the test classes whose expectations are the Spanish texts: `class X(_testenv.Spanish, unittest.TestCase)`."""

    def setUp(self):
        super().setUp()
        i18n.set_language("es")

    def tearDown(self):
        i18n.set_language("en")
        super().tearDown()
