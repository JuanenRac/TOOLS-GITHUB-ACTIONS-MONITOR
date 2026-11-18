# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The overview wall screen shows the map of the fleet by groups, with the grouping of the Fleet view: the payload has the groups (and only a name and numbers, never a repository), the setting
screens.group_map switches it off, the real routes of the screen and of the Fleet view agree, and the page draws it in every theme and language without a text of its own."""
import json
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_206_wall_screens as wall  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor, screens, settings_api  # noqa: E402
from github_actions_monitor.health import fleet, repo_view  # noqa: E402

PAGE = (HERE / "assets" / "static" / "screens.html").read_text(encoding="utf-8")


def views():
    """Six repositories in two ecosystems, with every state."""
    rows = []
    for name, eco, state in (("a1", "armor", "bad"), ("a2", "armor", "warn"), ("a3", "armor", "ok"), ("h1", "hydra", "ok"), ("h2", "hydra", "unknown"), ("h3", "hydra", "ok")):
        rows.append({"repo": name, "ecosystem": eco, "state": state, "risk": {"bad": 30, "warn": 5}.get(state, 0), "ci": {"red_workflows": [], "failures_24h": 0}, "alerts": {"total": 0},
                     "activity": {"last_run_at": None}, "not_fully_seen": []})
    return rows


class ThePayload(unittest.TestCase):
    def build(self, group_by="ecosystem", **cfg):
        view = fleet.fleet_view(views(), {"fleet": {"group_by": group_by}})
        c = screens.settings({"screens": cfg})
        return screens.build("overview", wall.state(), wall.snapshot(), wall.alerts(), None, c, now=wall.NOW, fleet_view=view, labels={"armor": "A.R.M.O.R.", "hydra": "HYDRA-UMC"})

    def test_the_groups_are_the_ones_of_the_fleet_view_in_the_same_order(self):
        out = self.build()["groups"]
        view = fleet.fleet_view(views(), {"fleet": {"group_by": "ecosystem"}})
        self.assertEqual(out["by"], "ecosystem")
        self.assertEqual([g["key"] for g in out["groups"]], [g["key"] for g in view["groups"]])
        for shown, real in zip(out["groups"], view["groups"]):
            self.assertEqual((shown["repos"], shown["bad"], shown["warn"], shown["ok"], shown["unknown"]), (real["repos"], real["bad"], real["warn"], real["ok"], real["unknown"]))
        self.assertEqual(out["groups"][0]["label"], "A.R.M.O.R.", "the riskiest group first, with the name of the ecosystem")
        self.assertEqual(sum(g["repos"] for g in out["groups"]), 6)

    def test_every_way_of_grouping_of_the_fleet_view_is_followed(self):
        for by in fleet.GROUPS:
            out = self.build(by)["groups"]
            self.assertEqual(out["by"], by)
            self.assertEqual(sum(g["repos"] for g in out["groups"]), 6, by)
        self.assertEqual(sorted(g["key"] for g in self.build("state")["groups"]["groups"]), ["bad", "ok", "unknown", "warn"])
        self.assertEqual([g["key"] for g in self.build("none")["groups"]["groups"]], [""])

    def test_only_a_name_of_a_group_and_numbers_leave_the_server_never_a_repository(self):
        for mode in screens.NAMES:
            text = json.dumps(self.build(show_repo_names=mode)["groups"])
            for repo in ("a1", "a2", "h1", "pub-a", "priv-c"):
                self.assertNotIn(f'"{repo}"', text, mode)
            self.assertNotIn("https://", text)

    def test_the_switch_the_default_and_a_missing_view(self):
        self.assertTrue(screens.settings({})["group_map"], "on by default")
        self.assertIsNone(self.build(group_map=False)["groups"])
        self.assertIsNone(screens.build("overview", wall.state(), None, None, None, screens.settings({}), now=wall.NOW)["groups"], "no fleet view, no map")
        self.assertIsNone(screens.group_map({"groups": "bad"}))
        self.assertIsNone(screens.group_map(None))
        self.assertNotIn("groups", screens.build("now", wall.state(), None, None, None, screens.settings({}), now=wall.NOW))

    def test_a_very_long_list_shows_the_riskiest_and_says_how_many_more(self):
        many = {"group_by": "label", "groups": [{"key": f"g{i}", "repos": 1, "risk": 100 - i, "bad": 0, "warn": 0, "ok": 1, "unknown": 0} for i in range(30)]}
        out = screens.group_map(many)
        self.assertEqual((len(out["groups"]), out["more"], out["groups"][0]["key"]), (screens.GROUPS_SHOWN, 30 - screens.GROUPS_SHOWN, "g0"))

    def test_garbage_in_the_view_is_made_harmless(self):
        out = screens.group_map({"group_by": "<x>", "groups": [None, {"key": "k" * 99, "repos": "many", "bad": True}]})
        self.assertEqual(out["by"], "ecosystem")
        self.assertEqual(len(out["groups"][0]["key"]), 40)
        self.assertEqual((out["groups"][0]["repos"], out["groups"][0]["bad"]), (0, 0))


class TheSettings(unittest.TestCase):
    def test_the_setting_has_its_row_its_default_and_its_texts_in_eight_languages(self):
        self.assertIn("screens.group_map", settings_api.FIELDS)
        self.assertIs(actions_monitor.DEFAULTS["screens"]["group_map"], True)
        for lang in i18n.LANGS:
            for prefix in ("cfg.f.", "cfg.h."):
                self.assertNotEqual(i18n.tl(lang, prefix + "screens.group_map"), prefix + "screens.group_map", lang)

    def test_the_texts_of_the_map_are_in_eight_languages_and_reach_the_page(self):
        keys = ["ui.scr_grp_head", "ui.scr_grp_all", "ui.scr_grp_nogroup", "ui.scr_grp_more"] + ["ui.scr_grp_" + by for by in fleet.GROUPS]
        for key in keys:
            self.assertIn(key, screens.page_keys())
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))


class TheRoutes(unittest.TestCase):
    def setUp(self):
        actions_monitor.GROUPS_CACHE.update(at=0.0, view=None, labels=None)
        self.addCleanup(actions_monitor.GROUPS_CACHE.update, at=0.0, view=None, labels=None)

    def test_the_real_screen_and_the_fleet_view_agree_on_the_groups(self):
        config = {**wall.ON, "fleet": {"group_by": "state"}}
        server = wall.Running(self, config)
        with mock.patch.object(actions_monitor, "health_views", return_value=views()):
            status, body, _ = server.get("/api/screens/data?screen=overview")
            self.assertEqual(status, 200)
            groups = json.loads(body)["groups"]
            status, body, _ = server.get("/api/team/fleet")
            real = json.loads(body) if status == 200 else fleet.fleet_view(views(), config)
        self.assertEqual(groups["by"], "state")
        self.assertEqual([g["key"] for g in groups["groups"]], [g["key"] for g in real["groups"]])

    def test_the_switch_takes_the_map_out_of_the_real_answer(self):
        server = wall.Running(self, {**wall.ON, "screens": {**wall.ON["screens"], "group_map": False}})
        with mock.patch.object(actions_monitor, "health_views", return_value=views()):
            self.assertIsNone(json.loads(server.get("/api/screens/data?screen=overview")[1])["groups"])


class ThePage(unittest.TestCase):
    def test_the_page_draws_the_map_with_the_texts_of_its_language_and_the_colours_of_its_theme(self):
        for needle in ('id="gmap"', "d.groups", "ui.scr_grp_head", "ui.scr_grp_", "ui.lv_", "hasmap"):
            self.assertIn(needle, PAGE, needle)
        css = re.search(r"\.gmap\{.*?\.flash-ok", PAGE, re.S).group(0)
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,6}\b", "colours come from the theme variables, never fixed")
        for token in ("var(--bad)", "var(--warn)", "var(--ok)", "var(--mut)"):
            self.assertIn(token, css, token)
        self.assertIn(".gmap[hidden]{display:none}", PAGE, "a map that is off does not take room")


if __name__ == "__main__":
    unittest.main()
