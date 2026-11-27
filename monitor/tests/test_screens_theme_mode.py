# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The theme and the mode of the wall screens (docs/SCREENS.md). The theme: the whole product wears the one chosen in Settings (`ui.theme`), the wall screens inherit it unless a screen (or all of them) fixes another,
no colour is written in a screen outside its palettes, and the sixteen palettes are the ones of the main page. The mode: three screens as always, or one that rotates every N seconds and jumps to the screen of a new
red for X seconds (or until the red is gone), once per red. The behaviour of the page in a browser is in test_screens_rotation_browser.py."""
import http.client
import json
import re
import threading
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor import i18n
from github_actions_monitor.app import actions_monitor, screens, settings_api, toolconfig
from github_actions_monitor.security import auth_http

HERE = Path(__file__).resolve().parent.parent
SCREENS = (HERE / "assets" / "static" / "screens.html").read_text(encoding="utf-8")
MAIN = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
NEW = ("ui.theme", "screens.default_theme", "screens.theme_overview", "screens.theme_now", "screens.theme_sentinels", "screens.mode", "screens.rotate_every_seconds", "screens.alert_hold_seconds",
       "screens.logo_overview", "screens.logo_now", "screens.logo_sentinels", "screens.logo_corner", "screens.logo_max_width", "screens.logo_max_height")


class TheThemeOfEachScreen(unittest.TestCase):
    def test_the_screens_inherit_the_theme_of_the_product_by_default(self):
        cfg = screens.settings({})
        self.assertEqual((cfg["default_theme"], cfg["theme_overview"], cfg["theme_now"], cfg["theme_sentinels"]), ("inherit",) * 4)
        for name in screens.GLOBAL_THEMES:
            self.assertEqual([screens.resolve_theme(cfg, k, name) for k in screens.KINDS], [name] * 4, name)
        self.assertEqual(screens.global_theme({}), "auto")
        self.assertEqual(screens.global_theme({"ui": {"theme": "Armor"}}), "Armor")
        self.assertEqual(screens.global_theme({"ui": {"theme": "high contrast"}}), "High contrast", "the case does not matter")
        self.assertEqual(screens.global_theme({"ui": {"theme": "contrast"}}), "auto", "contrast is a theme of the screens, not of the product")
        self.assertEqual(screens.global_theme({"ui": "nonsense"}), "auto")

    def test_all_the_screens_can_fix_one_and_one_screen_can_fix_another(self):
        cfg = screens.settings({"screens": {"default_theme": "contrast", "theme_now": "Terminal"}})
        self.assertEqual([screens.resolve_theme(cfg, k, "dark") for k in screens.KINDS], ["contrast", "contrast", "Terminal", "contrast"])
        cfg = screens.settings({"screens": {"theme_sentinels": "light"}})
        self.assertEqual([screens.resolve_theme(cfg, k, "Armor") for k in screens.KINDS], ["Armor", "Armor", "Armor", "light"])
        self.assertEqual(screens.resolve_theme(cfg, None, "Ice"), "Ice")

    def test_a_value_that_is_not_a_theme_is_the_inherited_one(self):
        cfg = screens.settings({"screens": {"default_theme": "pink", "theme_now": "<script>", "theme_overview": 7}})
        self.assertEqual((cfg["default_theme"], cfg["theme_now"], cfg["theme_overview"]), ("inherit",) * 3)

    def test_the_address_fixes_the_theme_of_the_whole_window(self):
        cfg = screens.settings({"screens": {"theme_now": "Mono"}})
        prm = screens.params({"theme": "light"}, cfg, "now", "Armor")
        self.assertEqual((prm["theme"], prm["theme_locked"]), ("light", True))
        prm = screens.params({}, cfg, "now", "Armor")
        self.assertEqual((prm["theme"], prm["theme_locked"]), ("Mono", False))
        prm = screens.params({"theme": "high contrast"}, cfg, "now", "Armor")
        self.assertEqual(prm["theme"], "High contrast")
        prm = screens.params({"theme": "</script>"}, cfg, "overview", "Armor")
        self.assertEqual((prm["theme"], prm["theme_locked"]), ("Armor", False))

    def test_the_page_data_has_the_theme_of_each_screen(self):
        cfg = screens.settings({"screens": {"theme_now": "Mono"}})
        data = screens.page_data("now", cfg, screens.params({}, cfg, "now", "Ice"), global_name="Ice")
        self.assertEqual(data["themes"], {"overview": "Ice", "fleet": "Ice", "now": "Mono", "sentinels": "Ice"})

    def test_the_sixteen_themes_are_the_ones_of_the_main_page(self):
        listed = re.search(r'STUDIO_THEMES=\[([^\]]*)\]', MAIN).group(1)
        self.assertEqual(tuple(re.findall(r'"([^"]+)"', listed)), screens.STUDIO_THEMES)
        css = screens.theme_css()
        for name in screens.STUDIO_THEMES:
            self.assertIn(':root[data-theme="%s"]{' % name, css, name)
        self.assertEqual(css.count(":root[data-theme="), 16)
        self.assertNotIn("<", css)
        for rule in css.split("\n"):
            self.assertIn("--bg:", rule)
            self.assertIn("--panel:", rule)
            self.assertIn("--text:", rule)

    def test_no_colour_is_fixed_in_a_screen_outside_its_palettes(self):
        for number, line in enumerate(SCREENS.split("\n"), 1):
            if re.match(r"\s*:root", line) or number < 12:
                continue
            body = re.sub(r"<!--.*?--!?>", "", line, flags=re.S)
            self.assertNotRegex(body, r"#[0-9a-fA-F]{3,8}\b(?![^<]*</)", f"screens.html line {number} writes a colour: use a variable of the theme")
            self.assertNotRegex(body, r"rgba?\(|hsla?\(", f"screens.html line {number}")

    def test_every_colour_the_page_draws_with_is_defined_by_each_palette_family(self):
        used = set(re.findall(r"var\((--[a-z0-9]+)", re.sub(r":root\[data-studio\]\{[^}]*\}", "", SCREENS)))
        plain = ":root{" + SCREENS.split(":root{", 1)[1].split("}", 1)[0]
        for name in used - {"--k", "--d", "--i", "--sx", "--sy", "--len", "--lw", "--lh", "--page", "--a", "--safe", "--minpx"}:
            self.assertIn(name + ":", plain, f"{name} has no value in the default palette")
        alias = re.search(r":root\[data-studio\]\{([^}]*)\}", SCREENS).group(1)
        for name in used - {"--k", "--d", "--i", "--sx", "--sy", "--len", "--lw", "--lh", "--page", "--a", "--safe", "--minpx", "--ok", "--warn", "--bad", "--line", "--mut", "--bg"}:
            self.assertIn(name + ":", alias, f"{name} is not given to the sixteen themes")

    def test_the_page_wears_the_theme_and_changes_it_with_the_screen(self):
        self.assertIn("function applyTheme(", SCREENS)
        self.assertIn("applyTheme(THEME_OF(kind))", SCREENS, "every screen that comes up puts on its own theme")
        self.assertIn('prefers-color-scheme: light', SCREENS, "auto follows the computer")
        self.assertIn("/*THEME_CSS*/", SCREENS)


class TheMainPageAndTheSignIn(unittest.TestCase):
    def test_the_choice_of_the_selector_is_sent_to_the_monitor_and_the_monitors_theme_is_the_starting_point(self):
        self.assertIn('{changes:{"ui.theme":theme}}', MAIN)
        self.assertIn("I18N.theme", MAIN)
        self.assertIn('"theme": screens.global_theme(', Path(actions_monitor.__file__).read_text(encoding="utf-8"))
        row = settings_api.FIELDS["ui.theme"]
        self.assertEqual((row[1], row[2], row[3]), ("ui.theme", "enum", screens.GLOBAL_THEMES))
        self.assertEqual(actions_monitor.DEFAULTS["ui"]["theme"], "auto")

    def test_the_sign_in_page_wears_the_theme(self):
        self.assertNotIn("data-theme", auth_http.login_page({}).split("<style>")[0])
        for name, studio in (("light", False), ("dark", False), ("Armor", True), ("Terminal", True)):
            page = auth_http.login_page({"ui": {"theme": name}})
            head = page.split("<style>")[0]
            self.assertIn('data-theme="%s"' % name, head)
            self.assertEqual("data-studio" in head, studio, name)
            self.assertEqual(':root[data-theme="%s"]{' % name in page, studio, name)
        self.assertIn(':root[data-theme=light]{', auth_http.login_page({}))
        self.assertIn(":not([data-theme])", auth_http.login_page({}), "without a chosen theme it follows the computer")

    def test_a_screen_is_served_with_the_palettes_and_the_theme_of_the_monitor(self):
        config = {"screens": {"enabled": True, "theme_now": "Forest"}, "ui": {"theme": "Armor"}}
        with mock.patch.object(toolconfig, "raw_config", return_value=config):
            for kind, expected in (("overview", "Armor"), ("now", "Forest")):
                page = actions_monitor.render_screen(kind, {})
                data = json.loads(re.search(r"const D=(\{.*\});\n", page).group(1).replace("<\\/", "</"))
                self.assertEqual(data["params"]["theme"], expected)
                self.assertEqual(data["themes"], {"overview": "Armor", "fleet": "Armor", "now": "Forest", "sentinels": "Armor"})
                self.assertIn(':root[data-theme="Armor"]{', page)
                self.assertNotIn("/*THEME_CSS*/", page)
            self.assertEqual(json.loads(re.search(r"const D=(\{.*\});\n", actions_monitor.render_screen("now", {"theme": "light"})).group(1))["params"]["theme_locked"], True)


class TheModeOfTheScreens(unittest.TestCase):
    def test_conservative_defaults(self):
        cfg = screens.settings({})
        self.assertEqual((cfg["mode"], cfg["rotate_every_seconds"], cfg["alert_hold_seconds"], cfg["rotate_seconds"]), ("three", 20, 30, 0))
        prm = screens.params({}, cfg)
        self.assertEqual((prm["rotate"], prm["jump"], prm["mode"]), (0, False, "three"), "as before: three screens, nothing turns, nothing jumps")

    def test_the_limits(self):
        cfg = screens.settings({"screens": {"mode": "rotate", "rotate_every_seconds": 1, "alert_hold_seconds": 99999}})
        self.assertEqual((cfg["rotate_every_seconds"], cfg["alert_hold_seconds"]), (5, 600))
        cfg = screens.settings({"screens": {"rotate_every_seconds": 9999, "alert_hold_seconds": 1, "mode": "weird"}})
        self.assertEqual((cfg["rotate_every_seconds"], cfg["alert_hold_seconds"], cfg["mode"]), (300, 5, "three"))
        self.assertEqual(settings_api.FIELDS["screens.rotate_every_seconds"][3], (5, 300))
        self.assertEqual(settings_api.FIELDS["screens.alert_hold_seconds"][3], (5, 600))
        self.assertEqual(settings_api.FIELDS["screens.mode"][3], ("three", "rotate"))

    def test_in_rotate_mode_one_window_turns_every_n_seconds_and_jumps(self):
        cfg = screens.settings({"screens": {"mode": "rotate"}})
        prm = screens.params({}, cfg)
        self.assertEqual((prm["rotate"], prm["jump"], prm["hold"], prm["mode"]), (20, True, 30, "rotate"))
        cfg = screens.settings({"screens": {"mode": "rotate", "rotate_every_seconds": 45, "alert_hold_seconds": 12}})
        prm = screens.params({}, cfg)
        self.assertEqual((prm["rotate"], prm["hold"]), (45, 12))

    def test_the_address_can_only_make_a_window_calmer(self):
        cfg = screens.settings({"screens": {"mode": "rotate"}})
        self.assertEqual(screens.params({"rotate": "60"}, cfg)["rotate"], 60)
        still = screens.params({"rotate": "0"}, cfg)
        self.assertEqual((still["rotate"], still["jump"]), (0, False), "a window that stays on one screen has nowhere to jump")
        self.assertFalse(screens.params({"jump": "off"}, cfg)["jump"])
        self.assertEqual(screens.params({"rotate": "2"}, cfg)["rotate"], 0, "a turn every two seconds would be a strobe")
        three = screens.settings({})
        self.assertFalse(screens.params({"jump": "on", "rotate": "30"}, three)["jump"], "the address never turns on what the settings keep off")

    def test_the_old_per_window_rotation_stays_for_three_screens(self):
        cfg = screens.settings({"screens": {"rotate_seconds": 40}})
        self.assertEqual(screens.params({}, cfg)["rotate"], 40)
        self.assertFalse(screens.params({}, cfg)["jump"])

    def test_the_page_turns_and_jumps_by_the_rules_of_the_owner(self):
        for need in ("const JUMP_KINDS=[\"now\",\"sentinels\"]", "function startHold(", "function endHold(", "function observe(", "P.hold*1000", "R.shown", "R.seen", "function schedule("):
            self.assertIn(need, SCREENS, need)
        self.assertIn('redKeys', SCREENS)
        self.assertRegex(SCREENS, r'kind==="now"\)return \(d\.failures')
        self.assertRegex(SCREENS, r'kind==="sentinels"&&d\.enabled\)return \(d\.cards')
        # a red that is gone ends the stay; a red already shown is forgotten only when it disappears
        self.assertIn("shown.forEach(k=>{if(!cur.has(k))shown.delete(k)})", SCREENS)
        self.assertIn("!R.hold.keys", SCREENS.replace("![...R.hold.keys]", "!R.hold.keys"))

    def test_the_other_screens_are_watched_with_the_same_read_only_call(self):
        self.assertEqual(len(re.findall(r"fetch\(", SCREENS)), 2, "one call for the data, shared by the screen that is shown and by the ones that are only watched, and the look at the version of the monitor")
        self.assertEqual(len(re.findall(r"fetch\(\"/api/screens/data", SCREENS)), 1)
        self.assertIn("if(P.jump)JUMP_KINDS.forEach", SCREENS)

    def test_every_new_setting_has_its_row_its_default_and_its_texts_in_eight_languages(self):
        for key in NEW:
            self.assertIn(key, settings_api.FIELDS, key)
        for key in set(screens.DEFAULTS) - {"enabled"}:
            self.assertIn("screens." + key, settings_api.FIELDS, key)
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                for key in NEW:
                    for prefix in ("cfg.f.", "cfg.h."):
                        self.assertNotEqual(i18n.t(prefix + key), prefix + key, f"{lang} {prefix}{key}")
                self.assertNotEqual(i18n.t("ui.cfg_b_look"), "ui.cfg_b_look")
                self.assertNotEqual(i18n.t("ui.cfg_b_logo"), "ui.cfg_b_logo")

    def test_the_defaults_of_the_monitor_and_of_the_module_are_one(self):
        self.assertEqual(actions_monitor.DEFAULTS["screens"], screens.DEFAULTS)
        for key in ("screens.mode", "screens.rotate_every_seconds"):
            self.assertFalse(settings_api.FIELDS[key][4], "applies at once, no restart")


class Running:
    def __init__(self, case, config):
        patcher = mock.patch.object(toolconfig, "raw_config", return_value=config)
        patcher.start()
        case.addCleanup(patcher.stop)
        self.server = actions_monitor.QuietServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        case.addCleanup(self.server.server_close)
        case.addCleanup(self.server.shutdown)
        self.port = self.server.server_address[1]

    def get(self, path):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        try:
            connection.request("GET", path, headers={"Host": f"127.0.0.1:{self.port}"})
            answer = connection.getresponse()
            return answer.status, answer.read().decode("utf-8", "replace")
        finally:
            connection.close()


class OverTheWire(unittest.TestCase):
    def test_the_rotating_window_is_served_with_its_pace_and_its_hold(self):
        server = Running(self, {"screens": {"enabled": True, "mode": "rotate", "rotate_every_seconds": 33, "alert_hold_seconds": 41}})
        status, page = server.get("/screen/now")
        self.assertEqual(status, 200)
        params = json.loads(re.search(r"const D=(\{.*\});\n", page).group(1).replace("<\\/", "</"))["params"]
        self.assertEqual((params["mode"], params["rotate"], params["jump"], params["hold"]), ("rotate", 33, True, 41))

    def test_the_main_page_gets_the_theme_of_the_monitor(self):
        server = Running(self, {"ui": {"theme": "Violet"}})
        status, page = server.get("/")
        self.assertEqual(status, 200)
        self.assertRegex(page, r'"theme": "Violet"')


if __name__ == "__main__":
    unittest.main()
