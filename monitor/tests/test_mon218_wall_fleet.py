# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Fleet wall screen (the fourth one: Overview, Fleet, Right now, Sentinels) and the settings that give the screens life: the payload groups the repositories, caps what it sends, names them the way the
other screens do and never names a hidden one; the settings of the screens (life, glance, transition, hide the healthy, rest when quiet, smallest letter) are clamped; the screen has its theme, logo, menu entry,
decision and texts in the eight languages."""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import screenmenu, screens, settings_api  # noqa: E402

NOW = 1_794_856_800


def view(groups=2, per_group=5, states=("bad", "ok", "warn", "ok", "unknown")):
    rows, gs = [], []
    for g in range(groups):
        counts = {"bad": 0, "warn": 0, "ok": 0, "unknown": 0}
        for r in range(per_group):
            state = states[(g + r) % len(states)]
            counts[state] += 1
            rows.append({"repo": f"repo-{g}-{r}", "group": f"g{g}", "state": state, "risk": (9 - r) if state == "bad" else r, "red_workflows": 1 if state == "bad" else 0, "running": r % 2})
        gs.append({"key": f"g{g}", "repos": per_group, "risk": 10 - g, **counts})
    return {"group_by": "ecosystem", "groups": gs, "rows": rows}


def meta(private=()):
    return {"repo_meta": {f"repo-{g}-{r}": {"private": f"repo-{g}-{r}" in private} for g in range(40) for r in range(80)}}


class TheFleetPayload(unittest.TestCase):
    def build(self, fleet_view, mode="all", private=(), labels=None):
        cfg = screens.settings({"screens": {"show_repo_names": mode}})
        state = {"updated": "2026-11-20T10:00:00Z", "repos": [f"repo-{g}-{r}" for g in range(40) for r in range(80)], **meta(private), "runs": [], "active": []}
        return screens.build("fleet", state, None, None, None, cfg, now=NOW, fleet_view=fleet_view, labels=labels)

    def test_the_screen_is_the_second_of_four_and_has_its_address(self):
        self.assertEqual(screens.KINDS, ("overview", "fleet", "now", "sentinels"))
        self.assertEqual(screens.kind_of("/screen/fleet"), "fleet")
        self.assertEqual(screens.kind_of("/screen/fleet/"), "fleet")
        self.assertIsNone(screens.kind_of("/screen/fleets"))
        self.assertEqual(screens.TAB_DECISIONS["fleet"], {"screen": "fleet", "field": "groups"})

    def test_the_groups_come_with_their_tiles_worst_first(self):
        out = self.build(view(), labels={"g0": "ARMOR"})
        self.assertEqual(out["screen"], "fleet")
        self.assertEqual([g["key"] for g in out["groups"]], ["g0", "g1"])
        self.assertEqual(out["groups"][0]["label"], "ARMOR")
        for group in out["groups"]:
            order = [t["state"] for t in group["tiles"]]
            self.assertEqual(order, sorted(order, key=lambda s: screens.STATE_ORDER[s]), "the worst first")
            self.assertEqual(group["repos"], 5)
            self.assertEqual(group["hidden"], 0)
        self.assertEqual(out["totals"], {"bad": 2, "warn": 2, "unknown": 2, "ok": 4})
        self.assertEqual(out["by"], "ecosystem")
        self.assertEqual(sorted(out["fleet"]), ["green", "idle", "red", "stuck", "total", "waiting"])

    def test_what_is_sent_is_capped_and_the_rest_is_counted(self):
        out = self.build(view(groups=screens.FLEET_GROUPS + 3, per_group=screens.FLEET_TILES + 9))
        self.assertEqual(len(out["groups"]), screens.FLEET_GROUPS)
        self.assertEqual(out["more_groups"], 3)
        for group in out["groups"]:
            self.assertEqual(len(group["tiles"]), screens.FLEET_TILES)
            self.assertEqual(group["hidden"], 9)
            self.assertEqual(group["repos"], screens.FLEET_TILES + 9)

    def test_a_hidden_repository_is_never_named(self):
        private = {"repo-0-0", "repo-0-1", "repo-1-3"}
        for mode in ("public", "none"):
            text = json.dumps(self.build(view(), mode, private))
            for name in private:
                self.assertNotIn(name, text, (mode, name))
        self.assertIn("private-1", json.dumps(self.build(view(), "public", private)))
        none = json.dumps(self.build(view(), "none"))
        self.assertNotIn("repo-0-", none)
        self.assertIn('"name": "repo-', none)      # the aliases are repo-N, in the order of a keyed hash
        everything = json.dumps(self.build(view(), "all", private))
        self.assertIn("repo-0-0", everything)

    def test_without_the_fleet_view_the_screen_is_still_an_answer(self):
        for nothing in (None, {}, {"groups": "no"}):
            out = self.build(nothing)
            self.assertIsNone(out["groups"])
            self.assertEqual(out["more_groups"], 0)
            self.assertIn("fleet", out)

    def test_a_broken_row_is_left_out_and_a_strange_state_is_unknown(self):
        v = view(groups=1, per_group=2)
        v["rows"].append("not a row")
        v["rows"].append({"repo": 5})
        v["rows"][0]["state"] = "exploding"
        out = self.build(v)
        self.assertEqual([t["state"] for t in out["groups"][0]["tiles"]], ["unknown", "ok"])

    def test_no_text_that_could_leak(self):
        text = json.dumps(self.build(view()))
        for forbidden in ("https://", "github.com", "token", "SECRET"):
            self.assertNotIn(forbidden, text)


class TheSettingsOfTheScreens(unittest.TestCase):
    def test_the_defaults_keep_the_screens_as_they_were_and_give_them_life(self):
        cfg = screens.settings({})
        self.assertEqual((cfg["life"], cfg["glance_seconds"], cfg["transition"], cfg["hide_healthy"], cfg["idle_dim_minutes"], cfg["min_font_px"]), (True, 3, "fade", False, 0, 12))
        self.assertEqual((cfg["theme_fleet"], cfg["logo_fleet"]), ("inherit", False))

    def test_every_number_is_clamped_and_a_wrong_choice_is_the_default(self):
        cfg = screens.settings({"screens": {"glance_seconds": 999, "idle_dim_minutes": -4, "min_font_px": 2, "transition": "spin", "hide_healthy": "yes", "life": "off", "theme_fleet": "nonsense", "logo_fleet": True}})
        self.assertEqual((cfg["glance_seconds"], cfg["idle_dim_minutes"], cfg["min_font_px"], cfg["transition"]), (30, 0, screens.MIN_FONT_LOW, "fade"))
        self.assertEqual((cfg["hide_healthy"], cfg["life"], cfg["theme_fleet"], cfg["logo_fleet"]), (True, False, "inherit", True))
        self.assertEqual(screens.settings({"screens": {"min_font_px": 99}})["min_font_px"], screens.MIN_FONT_HIGH)
        self.assertEqual(screens.settings({"screens": {"transition": "SLIDE"}})["transition"], "slide")

    def test_they_are_settings_of_the_page_with_their_texts(self):
        for key in ("screens.life", "screens.glance_seconds", "screens.transition", "screens.hide_healthy", "screens.idle_dim_minutes", "screens.min_font_px", "screens.theme_fleet", "screens.logo_fleet"):
            self.assertIn(key, settings_api.META, key)
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, "cfg.f." + key), "cfg.f." + key, (lang, key))
                self.assertNotEqual(i18n.tl(lang, "cfg.h." + key), "cfg.h." + key, (lang, key))

    def test_the_page_receives_what_it_needs_and_the_screen_has_its_theme_and_logo(self):
        cfg = screens.settings({"screens": {"theme_fleet": "Terminal", "logo_fleet": True}})
        data = screens.page_data("fleet", cfg, screens.params({}, cfg))
        for key in ("life", "glance_seconds", "transition", "hide_healthy", "idle_dim_minutes", "min_font_px"):
            self.assertIn(key, data["settings"])
        self.assertEqual(data["kinds"], list(screens.KINDS))
        self.assertEqual(data["themes"]["fleet"], "Terminal")
        self.assertTrue(screens.logo_block(cfg, {"present": True, "tag": "x"})["show"]["fleet"])

    def test_the_texts_of_the_screen_exist_in_the_eight_languages(self):
        for lang in i18n.LANGS:
            for key in ("ui.scr_title_fleet", "ui.scr_fleet_groups", "ui.scrm_e_fleet", "ui.scrm_d_fleet"):
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))
        cfg = screens.settings({})
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                texts = screens.page_data("fleet", cfg, screens.params({}, cfg))["texts"]
            self.assertTrue(texts["ui.scr_title_fleet"] and texts["ui.scr_fleet_groups"], lang)


class TheMenu(unittest.TestCase):
    def test_the_fleet_screen_is_in_the_menu_and_in_the_set_of_four_windows(self):
        entry = next(e for e in screenmenu.CATALOGUE if e["id"] == "fleet")
        self.assertEqual((entry["group"], entry["path"], entry["needs"]), ("wall", "/screen/fleet", "wall"))
        windows = screenmenu.multi_urls({"windows": "4"}, screenmenu.menu_settings({}))
        self.assertEqual([w["id"] for w in windows], ["overview", "now", "sentinels", "fleet"])
        self.assertEqual(windows[3]["url"], "/screen/fleet?monitor=4")


if __name__ == "__main__":
    unittest.main()
