# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The page in every size from a phone to 4K, upright and turned, and the screens of one monitor (/screen/N). In a headless browser: no sideways scroll, no text cut off, every tab opens, in each size. Skipped when
there is no browser (and on a CI runner unless MONITOR_BROWSER_TESTS=1)."""
import json
import os
import re
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(TOOLS))
import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402

try:
    import check_overflow  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    check_overflow = None

SIZES = {"1080p": (1920, 1080), "ultrawide 21:9": (2560, 1080), "3440x1440": (3440, 1440), "super ultrawide 32:9": (5120, 1440), "4K": (3840, 2160),
         "1080p turned": (1080, 1920), "4K turned": (2160, 3840), "tablet": (768, 1024), "phone": (390, 844)}
SETTINGS = ("ui.orientation", "ui.rotate_seconds", "ui.screen1_tabs", "ui.screen1_orientation", "ui.screen2_tabs", "ui.screen2_orientation", "ui.screen3_tabs", "ui.screen3_orientation")


def _port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@unittest.skipUnless(check_overflow is not None and check_overflow.edge(), "no tools folder, or no Edge, Chrome or Chromium on this computer")
@unittest.skipIf(os.environ.get("CI") and not os.environ.get("MONITOR_BROWSER_TESTS"), "the browser tests run on your computer (or with MONITOR_BROWSER_TESTS=1)")
class EverySize(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _port()
        cls.demo = subprocess.Popen([sys.executable, "-I", str(TOOLS / "demo_monitor.py"), str(cls.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    env={**os.environ, "MONITOR_TIMEZONE": "Europe/Madrid"})
        for _ in range(80):
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("the demo monitor did not start")
        cls.relay = check_overflow.relay(cls.port)
        cls.base = f"http://127.0.0.1:{cls.relay.server_address[1]}/"

    @classmethod
    def tearDownClass(cls):
        cls.relay.shutdown()
        cls.demo.terminate()

    def test_no_size_overflows_and_every_tab_opens(self):
        for name, size in SIZES.items():
            found = check_overflow.measure(check_overflow.edge(), f"{self.base}?lang=en&nowizard=1", size)
            self.assertEqual(found, [], (name, size, found[:3]))

    def test_a_screen_shows_only_its_tabs(self):
        found = check_overflow.measure(check_overflow.edge(), f"{self.base}screen/1?lang=en&nowizard=1&tabs=now,charts", (1920, 1080))
        self.assertEqual(found, [], found[:3])


class TheSettingsAndTheGuide(unittest.TestCase):
    def test_every_setting_has_its_text_in_the_eight_languages(self):
        for lang in i18n.LANGS:
            catalogue = json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertTrue(catalogue.get("ui.cfg_b_screens"), lang)
            for key in SETTINGS:
                self.assertTrue(catalogue.get("cfg.f." + key), (lang, key))
                self.assertTrue(catalogue.get("cfg.h." + key), (lang, key))

    def test_the_guide_exists_in_the_eight_languages_and_names_every_setting(self):
        for tail in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por"):
            text = (HERE / "docs" / f"SCREENS{tail}.md").read_text(encoding="utf-8")
            for key in SETTINGS:
                self.assertIn(key, text, (tail, key))
            self.assertIn("/screen/", text)

    def test_the_page_and_the_server_know_the_screens(self):
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn("data-orient", page)
        self.assertIn("(orientation:portrait)", page)
        self.assertIn("I18N.screens", page)
        source = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertTrue(re.search(r'/screen/\[1-3\]', source))


if __name__ == "__main__":
    unittest.main()
