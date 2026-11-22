# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Corrections of the page, the guides and the command line: the Fleet screen says how many tiles the server left out, the kiosk follows screens.show_repo_names, the guides count four screens,
the command line refuses a format it cannot write, lists every command it has, and the panels of the Sentinel grow when they carry information."""
import json
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401
import test_190_cli as base
from github_actions_monitor.cli import completions, monitor_cli
import test_206_wall_screens as t206
from github_actions_monitor import i18n
from github_actions_monitor.app import screens
from github_actions_monitor.surfaces import kiosk

HERE = Path(__file__).resolve().parent.parent
SCREENS = HERE / "assets" / "static" / "screens.html"


class TheFleetScreenCountsWhatTheServerLeftOut(unittest.TestCase):
    def setUp(self):
        self.html = SCREENS.read_text(encoding="utf-8")

    def test_fit_takes_the_rows_the_server_left_out(self):
        self.assertRegex(self.html, r"function fit\(list,keep,extra\)")
        self.assertIn('T("ui.scr_more",{n:hid+left})', self.html)
        self.assertRegex(self.html, r"if\(hid>0\|\|left>0\)")

    def test_the_fleet_gives_the_hidden_number_of_each_group(self):
        self.assertRegex(self.html, r'querySelectorAll\("\.tiles"\)\.forEach\(\(l,i\)=>fit\(l,0,num\(gs\[i\]&&gs\[i\]\.hidden\)\)\)')


DATA = {"repos": ["owner/secret-api", "owner/open-docs"], "repo_meta": {"owner/secret-api": {"private": True}, "owner/open-docs": {"private": False}},
        "rows": [{"repo": "owner/secret-api", "workflow": "deploy-prod", "title": "Fix the payroll export", "branch": "payroll-fix", "html_url": "https://github.com/owner/secret-api/actions/runs/1", "state": "bad"},
                 {"repo": "owner/open-docs", "workflow": "pages", "title": "Fix a typo", "branch": "main", "state": "ok"}]}


class TheKioskNamesRepositoriesLikeTheWallScreens(unittest.TestCase):
    def names(self, mode):
        return screens.Names(DATA["repos"], DATA["repo_meta"], mode)

    def test_a_private_repository_is_private_n_and_loses_its_texts_with_public(self):
        text = kiosk.redact({"data": DATA}, self.names("public"))
        for secret in ("secret-api", "payroll", "deploy-prod"):
            self.assertNotIn(secret, text)
        self.assertIn("private-1", text)
        self.assertIn("owner/open-docs", text)
        self.assertIn("Fix a typo", text)

    def test_none_hides_every_repository_and_all_shows_them(self):
        text = kiosk.redact({"data": DATA}, self.names("none"))
        self.assertNotIn("open-docs", text)
        self.assertIn("repo-1", text)
        self.assertIn("secret-api", kiosk.redact({"data": DATA}, self.names("all")))

    def test_the_data_given_is_not_changed(self):
        before = repr(DATA)
        kiosk.redact({"data": DATA}, self.names("public"))
        self.assertEqual(repr(DATA), before)

    def test_only_an_address_that_asks_for_it_with_the_profile_on_is_redacted(self):
        on, off = {"kiosk": {"enabled": True}}, {}
        self.assertTrue(kiosk.asked(on, "kiosk=1"))
        self.assertFalse(kiosk.asked(on, ""))
        self.assertFalse(kiosk.asked(off, "kiosk=1"))

    def test_the_route_and_the_page_use_it(self):
        server = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn("kiosk_profile.redact(", server)
        self.assertIn('screens.settings(raw)["show_repo_names"]', server)
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('?kiosk=1":""', page)


class TheRouteOfTheKioskData(unittest.TestCase):
    def test_a_kiosk_gets_the_names_of_the_wall_screens_and_a_plain_page_gets_the_real_ones(self):
        cfg = {"kiosk": {"enabled": True}, "screens": {"show_repo_names": "public"}}
        server = t206.Running(self, cfg)
        plain = server.get("/api/data")[1].decode("utf-8")
        self.assertIn("priv-c", plain)
        status, body, _kind = server.get("/api/data?kiosk=1")
        text = body.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertNotIn("priv-c", text)
        private = [r for r in json.loads(text)["data"]["runs"] if r["repo"] == "private-1"]
        self.assertTrue(private and all(r["title"] == "" and r["name"] == "" and r["url"] == "" for r in private))
        self.assertIn("SECRET COMMIT TITLE", text)      # a public repository keeps its titles
        self.assertIn("private-1", text)
        self.assertIn("pub-a", text)

    def test_with_the_profile_off_the_address_changes_nothing(self):
        server = t206.Running(self, {"screens": {"show_repo_names": "public"}})
        self.assertIn("priv-c", server.get("/api/data?kiosk=1")[1].decode("utf-8"))

    def test_all_shows_the_names_as_before(self):
        server = t206.Running(self, {"kiosk": {"enabled": True}, "screens": {"show_repo_names": "all"}})
        self.assertIn("priv-c", server.get("/api/data?kiosk=1")[1].decode("utf-8"))


class TheGuidesOfTheNames(unittest.TestCase):
    SUFFIXES = ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho")

    def test_the_kiosk_guide_names_the_setting_in_the_eight_languages(self):
        for suffix in self.SUFFIXES:
            text = (HERE / "docs" / f"KIOSK{suffix}.md").read_text(encoding="utf-8")
            self.assertIn("`screens.show_repo_names`", text, suffix)
            self.assertIn("private-N", text, suffix)

    def test_the_chat_names_private_repositories_by_default_and_says_so(self):
        from github_actions_monitor.app import actions_monitor
        from github_actions_monitor.chatops import inbound
        self.assertEqual(actions_monitor.DEFAULTS["chatops"]["show_repo_names"], "public")
        self.assertEqual(inbound.settings({})["show_repo_names"], "public")
        for suffix in self.SUFFIXES:
            text = (HERE / "docs" / f"CHATOPS{suffix}.md").read_text(encoding="utf-8")
            self.assertNotRegex(text, r"`all` \((the default|Standard|par défaut|predefinito|既定|por defeito|por defecto|默认)", suffix)

    def test_the_migration_tells_the_change_of_the_default(self):
        import json
        manual = json.loads((HERE / "assets" / "migrations" / "manual.json").read_text(encoding="utf-8"))
        notice = [n for n in manual["2.1.8"]["notices"] if n["id"] == "chatops_names_public"][0]
        self.assertEqual((notice["keys"], notice["old_value"], notice["new_value"]), (["chatops.show_repo_names"], "all", "public"))
        self.assertEqual(sorted(notice["text"]), ["de", "en", "es", "fr", "it", "ja", "pt", "zh"])


class TheGuideOfTheScreensCountsFour(unittest.TestCase):
    SUFFIXES = ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho")
    COUNTED = {"": r"\bthree pages\b", "_spa": r"\btres páginas\b", "_deu": r"\bdrei Seiten\b", "_fra": r"\btrois pages\b", "_ita": r"\btre pagine\b", "_jpn": "3つのページ", "_por": r"\btrês páginas\b",
               "_zho": "三个页面"}

    def test_the_four_screens_are_the_kinds_of_the_code(self):
        self.assertEqual(len(screens.KINDS), 4)

    def test_every_guide_names_every_screen_and_its_theme_and_logo_setting(self):
        for suffix in self.SUFFIXES:
            text = (HERE / "docs" / f"SCREENS{suffix}.md").read_text(encoding="utf-8")
            for kind in screens.KINDS:
                self.assertIn(f"`/screen/{kind}`", text, (suffix, kind))
                self.assertIn(f"`screens.theme_{kind}`", text, (suffix, kind))
                self.assertIn(f"`screens.logo_{kind}`", text, (suffix, kind))
            row = [line for line in text.split("\n") if line.startswith("| `screens.enabled`")][0]
            self.assertIn("/screen/fleet", row, suffix)
            self.assertNotRegex(text, self.COUNTED[suffix], suffix)

    def test_the_help_of_the_mode_and_the_rotation_does_not_say_three(self):
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                for key in ("cfg.h.screens.mode", "cfg.h.screens.rotate_seconds", "cfg.h.screens.menu_rotate_seconds", "ui.scrm_ph_set"):
                    text = i18n.t(key)
                    self.assertNotEqual(text, key, (lang, key))
                    self.assertNotRegex(text.replace("(three)", "").replace("three =", ""), r"(?i)(three|tres|drei|trois|tre|três)|3画面|3つ|3 つ|三个|三屏", (lang, key))      # `three` is the name of the mode, not a count
                self.assertIn(i18n.t("ui.scr_fleet"), i18n.t("cfg.h.screens.mode"), lang)


class TheCommandLine(unittest.TestCase):
    URL = ("--url", "http://127.0.0.1:1", "--timeout", "1")

    def test_a_format_csv_that_the_command_cannot_write_is_a_wrong_use(self):
        for command in ("status", "alerts", "score", "live"):
            code, out, err = base.run(command, "--format", "csv", *self.URL, "--lang", "en")
            self.assertEqual(code, 1, command)
            self.assertEqual(out, "", command)
            self.assertIn("csv", err, command)
            self.assertIn("compare", err, command)

    def test_the_message_comes_in_the_language_asked(self):
        for lang in i18n.LANGS:
            code, _out, err = base.run("status", "--format", "csv", *self.URL, "--lang", lang)
            self.assertEqual(code, 1, lang)
            self.assertEqual(err.split("\n")[0], i18n.tl(lang, "cli.csv_only_compare", command="status"), lang)

    def test_compare_still_takes_csv(self):
        code, _out, err = base.run("compare", "--format", "csv", *self.URL, "--lang", "en")
        self.assertNotEqual(code, 1, err)      # the monitor is not there: it is a failure of the connection (2), not a wrong use

    def test_monitor_is_a_command_of_the_parser_and_of_the_four_scripts_of_completion(self):
        action = next(a for a in monitor_cli.build_parser()._actions if a.dest == "command")
        self.assertIn("monitor", action.choices)
        for shell in completions.SHELLS:
            text = completions.script(shell, monitor_cli.build_parser(), monitor_cli.WORDS_BY_COMMAND)
            self.assertRegex(text, r"(?<![\w-])monitor(?![\w-])", shell)
        for lang in i18n.LANGS:
            self.assertIn("monitor [N]", i18n.tl(lang, "cli.help_command"), lang)

    def test_monitor_n_still_means_watch_status_even_after_an_option(self):
        self.assertEqual(monitor_cli.monitor_words(["monitor", "30", "--json"]), ["watch", "status", "--interval", "30", "--json"])
        self.assertEqual(monitor_cli.monitor_words(["--lang", "es", "monitor", "10"]), ["--lang", "es", "watch", "status", "--interval", "10"])
        self.assertEqual(monitor_cli.monitor_words(["--json", "monitor"]), ["--json", "watch", "status"])
        self.assertEqual(monitor_cli.monitor_words(["status", "--repo", "monitor"]), ["status", "--repo", "monitor"])
        self.assertEqual(monitor_cli.monitor_words(["--repo", "monitor", "status"]), ["--repo", "monitor", "status"])

    def test_the_words_of_argparse_come_in_the_language_asked(self):
        english = ("usage:", "positional arguments", "options:", "show this help message and exit", "invalid choice")
        for lang in i18n.LANGS:
            code, out, _err = base.run("--help", "--lang", lang)
            self.assertEqual(code, 0, lang)
            self.assertIn(i18n.tl(lang, "cli.argparse_usage"), out, lang)
            self.assertIn(i18n.tl(lang, "cli.argparse_help"), out, lang)
            self.assertIn(i18n.tl(lang, "cli.argparse_options"), out, lang)
            self.assertIn("monitor", out.split("\n\n")[0], lang)      # the line of usage lists every command, `monitor` too
            code, _out, err = base.run("bogus-command", "--lang", lang)
            self.assertEqual(code, 1, lang)
            self.assertIn(i18n.tl(lang, "cli.argparse_error"), err, lang)
            if lang != "en":
                ours = {i18n.tl(lang, key) + suffix for key in ("cli.argparse_usage", "cli.argparse_positional", "cli.argparse_options") for suffix in ("", ":", " :")}
                for word in english:
                    if word not in ours:      # a word that the language shares with English ("options" in French) is not a leftover
                        self.assertNotIn(word, out + err, (lang, word))


if __name__ == "__main__":
    unittest.main()
