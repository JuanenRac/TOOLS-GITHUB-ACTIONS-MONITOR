# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The kiosk profile: off by default, values kept inside their ranges, the addresses of the presets, the `kiosk` command, and the page honouring `kiosk=1` only when the setting is on."""
import json
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_190_cli as base  # noqa: E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.surfaces import kiosk  # noqa: E402

BASE = "http://127.0.0.1:8765"


class Settings(unittest.TestCase):
    def test_everything_is_off_by_default(self):
        s = kiosk.settings({})
        self.assertEqual((s["enabled"], s["high_contrast"], s["rotate_views"]), (False, False, False))
        self.assertEqual(actions_monitor.DEFAULTS["kiosk"], kiosk.DEFAULTS)

    def test_values_outside_their_range_are_the_defaults(self):
        s = kiosk.settings({"kiosk": {"enabled": "yes", "font_scale_percent": 9000, "rotate_seconds": 1, "high_contrast": 1}})
        self.assertEqual((s["enabled"], s["font_scale_percent"], s["rotate_seconds"], s["high_contrast"]), (False, 150, 30, False))
        self.assertEqual(kiosk.settings({"kiosk": {"font_scale_percent": 400}})["font_scale_percent"], 400)
        self.assertEqual(kiosk.settings({"kiosk": []})["font_scale_percent"], 150)

    def test_the_scale_of_an_address_is_kept_inside_the_range(self):
        self.assertEqual([kiosk.clamp_scale(v) for v in ("50", "150", "9999", "x", None)], [100, 150, 400, 100, 100])

    def test_the_settings_exist_in_the_schema_with_the_same_ranges(self):
        rows = {row[2]: row for row in settings_api.ROWS}
        self.assertEqual(rows["kiosk.font_scale_percent"][4], kiosk.SCALE_RANGE)
        self.assertEqual(rows["kiosk.rotate_seconds"][4], kiosk.ROTATE_RANGE)
        for key in ("kiosk.enabled", "kiosk.high_contrast", "kiosk.rotate_views", "cli.default_format", "cli.watch.min_interval_seconds", "cli.watch.default_interval_seconds"):
            self.assertIn(key, rows)


class Addresses(unittest.TestCase):
    def query(self, link):
        return {k: v[0] for k, v in parse_qs(urlparse(link).query).items()}

    def test_every_preset_builds_the_address_of_its_tabs(self):
        for preset, tabs in kiosk.PRESETS.items():
            q = self.query(kiosk.url(BASE, preset, {}))
            self.assertEqual((q["tabs"], q["chrome"], q["kiosk"], q["screen"]), (",".join(tabs), "0", "1", "1"))
            self.assertNotIn("rotate", q)      # the rotation is off unless it is asked for
            self.assertNotIn("contrast", q)

    def test_rotation_and_contrast_only_when_the_settings_say_so(self):
        raw = {"kiosk": {"rotate_views": True, "rotate_seconds": 45, "high_contrast": True, "font_scale_percent": 200}}
        q = self.query(kiosk.url(BASE, "ops", raw, "alpha"))
        self.assertEqual((q["rotate"], q["contrast"], q["scale"], q["account"]), ("45", "1", "200", "alpha"))
        self.assertNotIn("rotate", self.query(kiosk.url(BASE, "quiet", raw)))      # one tab has nothing to turn through

    def test_the_tabs_of_the_presets_exist_in_the_page(self):
        html = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        tabs = html[html.index("const TABS=LITE?"):].split("\n", 1)[0]
        for preset, names in kiosk.PRESETS.items():
            for name in names:
                self.assertIn('"%s"' % name, tabs, (preset, name))


class Command(unittest.TestCase):
    def test_the_command_prints_the_address_and_says_when_the_profile_is_off(self):
        code, out, _ = base.run("kiosk", "team", "--url", BASE, "--lang", "en")
        self.assertEqual(code, 0)
        self.assertIn("tabs=al,team", out)
        self.assertIn("kiosk.enabled", out)

    def test_json_names_the_preset_the_tabs_and_the_state(self):
        code, out, _ = base.run("kiosk", "--json", "--url", BASE, "--lang", "en")
        data = json.loads(out)["data"]
        self.assertEqual((code, data["preset"], data["tabs"], data["enabled"]), (0, "ops", ["now", "al", "charts"], False))

    def test_the_account_goes_into_the_address(self):
        _, out, _ = base.run("kiosk", "ops", "--account", "alpha", "--url", BASE, "--lang", "en")
        self.assertIn("account=alpha", out)


class Page(unittest.TestCase):
    html = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")

    def test_the_page_ignores_kiosk_when_the_setting_is_off(self):
        self.assertIn('k.enabled!==true||QS.get("kiosk")!=="1")return', self.html)

    def test_the_page_keeps_the_scale_inside_the_range(self):
        self.assertIn("Math.max(100,Math.min(400,", self.html)

    def test_the_server_hands_the_settings_to_the_page(self):
        self.assertIn('__import__("github_actions_monitor.surfaces.kiosk"', Path(actions_monitor.__file__).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
