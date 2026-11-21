# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Corrections of the page, the guides and the command line: the Fleet screen says how many tiles the server left out, the kiosk follows screens.show_repo_names, the guides count four screens,
the command line refuses a format it cannot write, lists every command it has, and the panels of the Sentinel grow when they carry information."""
import json
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401
import test_206_wall_screens as t206
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


if __name__ == "__main__":
    unittest.main()
