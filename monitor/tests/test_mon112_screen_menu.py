# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Screens menu of the page (docs/SCREENS.md): the closed catalogue of every kind of screen, the addresses it builds (each value checked, a rotation below five seconds left out), the multi-monitor set, the
settings of the menu inside their ranges, the read-only route, and the page: the button, the dialog, a help text on every control, the eight languages, and that opening a screen goes through the
configured target and never through a script or a link of its own."""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_org_logo as logo_tests  # noqa: E402
from github_actions_monitor.app import screenmenu, screens, settings_api  # noqa: E402

PAGE = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
LOCALES = {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}
BY_ID = {e["id"]: e for e in screenmenu.CATALOGUE}
CFG = screenmenu.menu_settings({})


class TheCatalogue(unittest.TestCase):
    def test_every_kind_of_screen_that_exists_is_listed(self):
        ids = set(screenmenu.IDS)
        self.assertTrue({"dashboard", "kiosk", "team", "screen1", "screen2", "screen3", "overview", "now", "sentinels", "wall_turning", "tv", "multi"} <= ids)
        for kind in screens.KINDS:
            self.assertIn(kind, ids, "a wall screen of screens.KINDS is missing from the menu")
        self.assertEqual(len(ids), len(screenmenu.IDS), "an id is repeated")

    def test_every_entry_has_its_words_in_the_eight_languages(self):
        for entry in screenmenu.CATALOGUE:
            for lang in LANGS:
                for key in ("ui.scrm_e_" + entry["id"], "ui.scrm_d_" + entry["id"]):
                    self.assertTrue(LOCALES[lang].get(key), (lang, key))
            self.assertIn(entry["group"], screenmenu.GROUPS)
        for name in screenmenu.PARAMS:
            for lang in LANGS:
                self.assertTrue(LOCALES[lang].get("ui.scrm_p_" + name), (lang, name))
                self.assertTrue(LOCALES[lang].get("ui.scrm_ph_" + name), (lang, name))

    def test_every_parameter_of_an_entry_is_a_known_one(self):
        for entry in screenmenu.CATALOGUE:
            for name in entry["params"]:
                self.assertIn(name, screenmenu.PARAMS, (entry["id"], name))

    def test_the_wall_paths_are_the_ones_of_the_screens(self):
        for kind in screens.KINDS:
            self.assertTrue(screens.PATH_RE.match(BY_ID[kind]["path"]), kind)

    def test_the_choices_of_a_parameter_are_the_ones_the_screens_accept(self):
        self.assertEqual(set(screenmenu.PARAMS["density"][1]) - {""}, set(screens.DENSITIES))
        self.assertEqual(set(screenmenu.PARAMS["theme"][1]) - {""}, set(screens.SCREEN_THEMES))
        self.assertEqual(screenmenu.PARAMS["refresh"][1:], (5, 120))
        self.assertEqual(screenmenu.PARAMS["rotate"][1:], (0, 3600))


class TheAddresses(unittest.TestCase):
    def test_a_plain_entry_is_its_path(self):
        self.assertEqual(screenmenu.build_url(BY_ID["dashboard"], None, CFG), "/")
        self.assertEqual(screenmenu.build_url(BY_ID["overview"], None, CFG), "/screen/overview")

    def test_the_kiosk_carries_its_fixed_parameter_and_the_view(self):
        self.assertEqual(screenmenu.build_url(BY_ID["kiosk"], None, CFG), "/?chrome=0&view=now")
        self.assertEqual(screenmenu.build_url(BY_ID["kiosk"], {"view": "fleet", "repo": "armor-"}, CFG), "/?chrome=0&view=fleet&repo=armor-")
        self.assertEqual(screenmenu.build_url(BY_ID["team"], None, CFG), "/?chrome=0&view=team")

    def test_a_value_that_is_not_valid_is_left_out(self):
        url = screenmenu.build_url(BY_ID["overview"], {"refresh": "3", "scale": "9", "theme": "pink", "density": "large", "monitor": "2", "lang": "xx"}, CFG)
        self.assertEqual(url, "/screen/overview?density=large&monitor=2")
        self.assertEqual(screenmenu.build_url(BY_ID["dashboard"], {"repo": "a b;c"}, CFG), "/")
        self.assertEqual(screenmenu.build_url(BY_ID["dashboard"], {"repo": "x" * 81}, CFG), "/")
        self.assertEqual(screenmenu.build_url(BY_ID["dashboard"], {"repo": "<script>"}, CFG), "/")

    def test_a_rotation_below_five_seconds_is_no_rotation(self):
        self.assertEqual(screenmenu.build_url(BY_ID["wall_turning"], {"rotate": "3"}, CFG), "/screen/overview")
        self.assertEqual(screenmenu.build_url(BY_ID["wall_turning"], {"rotate": "30", "jump": "off"}, CFG), "/screen/overview?rotate=30&jump=off")
        self.assertEqual(screenmenu.build_url(BY_ID["screen2"], {"rotate": "0"}, CFG), "/screen/2")

    def test_the_presets_come_from_the_settings(self):
        cfg = screenmenu.menu_settings({"screens": {"menu_rotate_seconds": 45, "menu_tv_scale": 2}})
        self.assertEqual(screenmenu.build_url(BY_ID["wall_turning"], None, cfg), "/screen/overview?rotate=45")
        self.assertEqual(screenmenu.build_url(BY_ID["tv"], None, cfg), "/screen/overview?theme=contrast&density=large&scale=2.0&rotate=45")

    def test_tabs_are_checked_one_by_one(self):
        self.assertEqual(screenmenu.build_url(BY_ID["screen1"], {"tabs": "now,al"}, CFG), "/screen/1?tabs=now,al")
        self.assertEqual(screenmenu.build_url(BY_ID["screen1"], {"tabs": "now,nothing"}, CFG), "/screen/1")
        self.assertEqual(screenmenu.build_url(BY_ID["screen3"], {"orient": "portrait"}, CFG), "/screen/3?orient=portrait")

    def test_a_parameter_the_entry_does_not_have_is_ignored(self):
        self.assertEqual(screenmenu.build_url(BY_ID["dashboard"], {"theme": "dark", "view": "now"}, CFG), "/")

    def test_nothing_in_an_address_is_a_token_a_host_or_a_path_of_this_computer(self):
        for row in screenmenu.entries({"screens": {"enabled": True}}):
            self.assertTrue(row["url"].startswith("/"))
            self.assertNotIn("//", row["url"])
            self.assertNotRegex(row["url"], r"(?i)token|key=|password|[a-z]:\\")


class TheMultiMonitorSet(unittest.TestCase):
    def test_default_is_three_windows_with_the_three_wall_screens(self):
        wins = screenmenu.multi_urls(None, CFG)
        self.assertEqual([w["id"] for w in wins], ["overview", "now", "sentinels"])
        self.assertEqual([w["url"] for w in wins], ["/screen/overview?monitor=1", "/screen/now?monitor=2", "/screen/sentinels?monitor=3"])

    def test_the_number_is_capped_by_the_setting(self):
        cfg = screenmenu.menu_settings({"screens": {"menu_max_windows": 2}})
        self.assertEqual(len(screenmenu.multi_urls({"windows": "9"}, cfg)), 2)
        self.assertEqual(len(screenmenu.multi_urls({"windows": "0"}, CFG)), 3)
        self.assertEqual(len(screenmenu.multi_urls({"windows": "5"}, screenmenu.menu_settings({"screens": {"menu_max_windows": 9}}))), 5)

    def test_the_sets_and_the_common_values(self):
        cfg = screenmenu.menu_settings({"screens": {"menu_max_windows": 6}})
        wins = screenmenu.multi_urls({"windows": "4", "set": "tabs", "theme": "dark"}, cfg)
        self.assertEqual([w["id"] for w in wins], ["screen1", "screen2", "screen3", "screen1"])
        self.assertEqual([w["url"] for w in wins], ["/screen/1", "/screen/2", "/screen/3", "/screen/1"], "the screens of tabs wear the theme of the page: no theme in their address")
        walls = screenmenu.multi_urls({"windows": "4", "theme": "dark"}, cfg)
        self.assertTrue(all("theme=dark" in w["url"] for w in walls))
        turning = screenmenu.multi_urls({"windows": "2", "set": "wall_turning"}, CFG)
        self.assertEqual([w["url"] for w in turning], ["/screen/overview?monitor=1&rotate=20", "/screen/overview?monitor=2&rotate=20"])


class TheSettings(unittest.TestCase):
    def test_defaults_are_navigation_only_and_the_rest_is_inside_its_range(self):
        self.assertEqual(CFG, {"menu": True, "menu_target": "new", "menu_max_windows": 4, "menu_rotate_seconds": 20, "menu_tv_scale": 1.5})
        bad = screenmenu.menu_settings({"screens": {"menu": "no", "menu_target": "popup", "menu_max_windows": 99, "menu_rotate_seconds": 1, "menu_tv_scale": 50}})
        self.assertEqual(bad, {"menu": False, "menu_target": "new", "menu_max_windows": 9, "menu_rotate_seconds": 5, "menu_tv_scale": 3.0})
        self.assertEqual(screenmenu.menu_settings({"screens": {"menu_tv_scale": True}})["menu_tv_scale"], 1.5)
        self.assertEqual(screenmenu.menu_settings({"screens": "x"}), CFG)

    def test_they_are_settings_of_the_page_with_the_same_defaults_as_the_template(self):
        from github_actions_monitor.app import actions_monitor
        for key, value in CFG.items():
            self.assertIn("screens." + key, settings_api.META)
            self.assertEqual(actions_monitor.DEFAULTS["screens"][key], value, key)

    def test_the_menu_changes_nothing_so_none_of_its_settings_is_secure_or_needs_a_restart(self):
        for key in CFG:
            self.assertFalse(settings_api.META["screens." + key]["secure"])
        self.assertEqual(settings_api.FIELDS["screens.menu"][2], "bool")


class TheEntries(unittest.TestCase):
    def test_wall_screens_say_why_they_cannot_be_opened(self):
        rows = {r["id"]: r for r in screenmenu.entries({})}
        for name in ("overview", "now", "sentinels", "wall_turning", "tv", "multi"):
            self.assertFalse(rows[name]["available"])
            self.assertEqual(rows[name]["reason"], "wall_off")
        self.assertTrue(rows["dashboard"]["available"])
        on = {r["id"]: r for r in screenmenu.entries({"screens": {"enabled": True}})}
        self.assertTrue(all(r["available"] for r in on.values()))

    def test_the_team_view_is_not_in_the_lite_edition(self):
        rows = {r["id"]: r for r in screenmenu.entries({"screens": {"enabled": True}}, lite=True)}
        self.assertFalse(rows["team"]["available"])
        self.assertEqual(rows["team"]["reason"], "edition")
        self.assertTrue(rows["overview"]["available"])

    def test_the_payload_is_empty_when_the_menu_is_off(self):
        out = screenmenu.payload({"screens": {"menu": False}})
        self.assertFalse(out["enabled"])
        self.assertEqual(out["entries"], [])
        full = screenmenu.payload({})
        self.assertEqual(len(full["entries"]), len(screenmenu.CATALOGUE))
        self.assertEqual(full["max_windows"], 4)

    def test_the_multi_entry_carries_its_windows_and_the_cap_on_their_number(self):
        row = [r for r in screenmenu.payload({"screens": {"enabled": True, "menu_max_windows": 2}})["entries"] if r["id"] == "multi"][0]
        windows = [p for p in row["params"] if p["name"] == "windows"][0]
        self.assertEqual(windows["max"], 2)
        self.assertEqual(len(row["windows"]), 2)


class TheRoute(unittest.TestCase):
    def test_it_answers_with_the_catalogue_and_never_writes(self):
        server = logo_tests.Running(self, {"screens": {"enabled": True}})
        status, body, headers = server.call("GET", "/api/screens/menu")
        self.assertEqual(status, 200)
        out = json.loads(body)
        self.assertTrue(out["enabled"] and out["wall_enabled"])
        self.assertEqual([e["id"] for e in out["entries"]], list(screenmenu.IDS))
        self.assertEqual(server.call("POST", "/api/screens/menu", b"{}", "application/json")[0] in (404, 405, 403, 400), True)

    def test_it_works_while_the_wall_screens_are_off_and_says_so(self):
        out = json.loads(logo_tests.Running(self, {}).call("GET", "/api/screens/menu")[1])
        self.assertFalse(out["wall_enabled"])
        self.assertFalse([e for e in out["entries"] if e["id"] == "overview"][0]["available"])

    def test_the_page_receives_only_the_three_settings_it_needs(self):
        from github_actions_monitor.app import actions_monitor
        self.assertIn('"screen_menu"', Path(actions_monitor.__file__).read_text(encoding="utf-8"))


class TheCommandAndTheTool(unittest.TestCase):
    def test_the_command_lists_and_prints_the_addresses(self):
        import contextlib
        import io
        from unittest import mock

        from github_actions_monitor import i18n
        from github_actions_monitor.app import toolconfig
        from github_actions_monitor.cli import monitor_cli as cli
        self.assertIn("screens", cli.COMMANDS)
        self.assertNotIn("screens", cli.LITE_COMMANDS)
        self.assertEqual(cli.SCREENS_ACTIONS, ("list", "urls"))
        self.addCleanup(i18n.set_language, "en")
        with mock.patch.object(toolconfig, "raw_config", return_value={"screens": {"enabled": True}}):
            served = logo_tests.Running(self, {"screens": {"enabled": True}})
            url = f"http://127.0.0.1:{served.port}"
            for action, expect in (("list", "/screen/overview"), ("urls", url + "/screen/overview?theme=contrast")):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = cli.main(["screens", action, "--url", url, "--lang", "en"])
                self.assertEqual(code, cli.EXIT_OK)
                self.assertIn(expect, out.getvalue())
                self.assertIn("12 kinds of screen", out.getvalue())
            bad = io.StringIO()
            with contextlib.redirect_stdout(bad), contextlib.redirect_stderr(bad):
                self.assertEqual(cli.main(["screens", "open", "--url", url, "--lang", "en"]), cli.EXIT_USAGE)

    def test_the_words_of_the_command_exist_in_the_eight_languages(self):
        for lang in LANGS:
            for key in ("cli.screens_action", "cli.screens_head", "cli.screens_wall_on", "cli.screens_wall_off"):
                self.assertTrue(LOCALES[lang].get(key), (lang, key))
            self.assertRegex(LOCALES[lang]["cli.help_command"], "screens", lang)

    def test_the_tool_of_the_mcp_server_returns_the_catalogue_and_only_reads(self):
        from github_actions_monitor.integrations import mcp_server
        tool = [t for t in mcp_server.TOOLS if t["name"] == "screens_menu"]
        self.assertEqual(len(tool), 1)
        self.assertEqual(tool[0]["inputSchema"]["properties"], {})
        seen = []

        def getter(path):
            seen.append(path)
            return screenmenu.payload({"screens": {"enabled": True}})
        text = mcp_server.call("screens_menu", {}, {}, getter=getter)
        self.assertEqual(seen, ["/api/screens/menu"])
        self.assertEqual([e["id"] for e in json.loads(text)["entries"]], list(screenmenu.IDS))


class ThePage(unittest.TestCase):
    def test_the_button_and_the_dialog_exist_with_their_help(self):
        self.assertRegex(PAGE, r'<button id="scrm-open" class="ib"[^>]*hidden[^>]*data-i18n-title="ui.scrm_btn_tip"')
        self.assertRegex(PAGE, r'<div id="scrm-dlg" class="dlg" role="dialog" aria-modal="true" aria-labelledby="scrm-h" hidden>')
        self.assertIn("dlgs={scrm:$(\"scrm-dlg\")", PAGE)
        self.assertIn('id="i-screens"', PAGE)

    def test_every_control_the_dialog_draws_has_a_help_text(self):
        draw = PAGE[PAGE.index("function scrmControl"):PAGE.index("function scrmRefresh")]
        self.assertEqual(len(re.findall(r'title="\$\{tip\}"', draw)), 4, "the select, the number, the text and the label of each parameter")
        for button in re.findall(r"<button type=\"button\" data-act=[^>]*>", draw):
            self.assertIn("title=", button)

    def test_every_text_the_script_asks_for_exists_in_the_eight_languages(self):
        script = PAGE[PAGE.index("const SCRV="):PAGE.index('$("about-open").addEventListener')]
        keys = set(re.findall(r'T\("(ui\.scrm_[a-z_]+)"', script))
        keys = {k for k in keys if not k.endswith("_")} | {"ui.scrm_title", "ui.scrm_btn_tip"}
        self.assertGreater(len(keys), 12)
        for lang in LANGS:
            for key in keys:
                self.assertTrue(LOCALES[lang].get(key), (lang, key))

    def test_the_choice_labels_exist(self):
        for lang in LANGS:
            for value in ("default", "off", "row", "column", "grid", "set_wall", "set_wall_turning", "set_tabs", "auto", "portrait", "landscape", "compact", "normal", "large"):
                self.assertTrue(LOCALES[lang].get("ui.scrm_v_" + value), (lang, value))

    def test_opening_goes_through_the_target_and_the_only_addresses_are_the_ones_of_the_catalogue(self):
        script = PAGE[PAGE.index("const SCRV="):PAGE.index('$("about-open").addEventListener')]
        self.assertIn('SCRM.target==="same"', script)
        self.assertIn('window.open(abs,"_blank","noopener")', script)
        self.assertIn("location.origin+url", script)
        self.assertNotRegex(script, r"https?://|eval\(|new Function")
        self.assertIn("getScreenDetails", script)

    def test_the_javascript_checks_a_value_like_the_server_does(self):
        script = PAGE[PAGE.index("function scrmOk"):PAGE.index("function scrmUrl")]
        for needle in ("p.min", "p.max", "p.max_length", "p.choices.includes", "A-Za-z0-9._"):
            self.assertIn(needle, script)
        self.assertIn('Number(v)<5', PAGE[PAGE.index("function scrmUrl"):PAGE.index("function scrmWindows")])


if __name__ == "__main__":
    unittest.main()
