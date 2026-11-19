# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The repository filter of the wall screens (`?repo=` on /screen/overview and /screen/now): what an address may ask for, which repositories are kept, that a hidden name can never be found with it, that
the figures follow the rows that are kept, and that the menu, the page and the route carry it."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _testenv  # noqa: F401,E402
import test_206_wall_screens as base  # noqa: E402
from github_actions_monitor.app import screenmenu, screens  # noqa: E402

CFG = screens.settings({"screens": {"show_repo_names": "public"}})
STATIC = HERE.parent / "assets" / "static"


def build(kind, repo, cfg=CFG, with_alerts=True):
    alerts = base.alerts()
    alerts["alerts"] = [{"repo": "pub-b", "level": "error", "sentinel": "ci"}, {"repo": "priv-c", "level": "error", "sentinel": "ci"}, {"repo": "pub-a", "level": "warning", "sentinel": "collab"}]
    return screens.build(kind, base.state(), base.snapshot(), alerts if with_alerts else None, {"enabled": True, "score": 80, "letter": "B", "state": "scored"}, cfg, now=base.NOW, repo=repo)


class Address(unittest.TestCase):
    def test_a_filter_keeps_words_made_of_safe_characters_only(self):
        self.assertEqual(screens.clean_repo_filter(" pub-a , pub.b/x "), "pub-a,pub.b/x")
        self.assertEqual(screens.clean_repo_filter("a<script>,b"), "b")
        self.assertEqual(screens.clean_repo_filter(""), "")
        self.assertEqual(screens.clean_repo_filter(None), "")
        self.assertEqual(len(screens.clean_repo_filter(",".join("w%d" % i for i in range(30))).split(",")), screens.REPO_FILTER_WORDS)
        self.assertLessEqual(len(screens.clean_repo_filter("a" * 500)), screens.REPO_FILTER_MAX)

    def test_the_window_carries_the_clean_filter(self):
        self.assertEqual(screens.params({"repo": "pub-a,x y"}, CFG, "overview")["repo"], "pub-a")
        self.assertEqual(screens.params({}, CFG, "overview")["repo"], "")

    def test_the_menu_offers_it_for_every_wall_screen(self):
        entries = {e["id"]: e for e in screenmenu.CATALOGUE}
        for name in ("overview", "now", "sentinels", "wall_turning", "tv", "multi"):
            self.assertIn("repo", entries[name]["params"], name)


class Filtering(unittest.TestCase):
    def test_without_a_filter_nothing_changes(self):
        full, none = build("overview", ""), build("overview", None)
        self.assertEqual(full, none)
        self.assertEqual(full["fleet"]["total"], 4)

    def test_only_the_repositories_that_match_and_are_shown_are_kept(self):
        out = build("overview", "pub-")
        self.assertEqual(out["fleet"]["total"], 3)
        self.assertEqual(out["meta"]["repos"], 3)
        text = repr(out)
        self.assertNotIn("priv-c", text)
        self.assertNotIn("private-1", text, "a hidden repository is dropped, not renamed")

    def test_a_hidden_name_is_never_matched(self):
        out = build("overview", "priv-c")
        self.assertEqual(out["fleet"]["total"], 0)
        self.assertEqual(out["alerts"]["total"], 0)
        self.assertNotIn("priv-c", repr(out))
        none = screens.settings({"screens": {"show_repo_names": "none"}})
        self.assertEqual(build("overview", "pub", none)["fleet"]["total"], 0)
        shown = screens.settings({"screens": {"show_repo_names": "all"}})
        self.assertEqual(build("overview", "priv-c", shown)["fleet"]["total"], 1)

    def test_the_figures_follow_the_rows_that_are_kept(self):
        out = build("overview", "pub-b")
        self.assertEqual(out["fleet"]["total"], 1)
        self.assertEqual(out["fleet"]["red"], 1)
        self.assertEqual(out["alerts"]["total"], 1)
        self.assertEqual(out["alerts"]["by_level"]["error"], 1)
        self.assertEqual([r["repo"] for r in out["top_red"]], ["pub-b"])

    def test_the_score_and_the_map_of_groups_of_the_whole_fleet_are_not_shown(self):
        self.assertIsNotNone(build("overview", "")["score"]["value"])
        self.assertIsNone(build("overview", "pub-")["score"]["value"])

    def test_several_words_and_case(self):
        self.assertEqual(build("overview", "PUB-A,pub-d")["fleet"]["total"], 2)

    def test_right_now_keeps_only_the_matching_rows(self):
        out = build("now", "pub-a")
        text = repr(out)
        self.assertIn("pub-a", text)
        self.assertNotIn("pub-b", text)
        self.assertNotIn("priv-c", text)

    def test_the_sentinels_screen_is_not_filtered(self):
        self.assertEqual(build("sentinels", "pub-a")["totals"], build("sentinels", "")["totals"])


class Carried(unittest.TestCase):
    def test_the_page_asks_for_the_data_with_the_filter(self):
        page = (STATIC / "screens.html").read_text(encoding="utf-8")
        self.assertIn('"&repo="+encodeURIComponent(P.repo)', page)

    def test_the_route_hands_the_filter_to_the_payload(self):
        source = (HERE.parent / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn('screens_payload(kind, screens.settings(toolconfig.raw_config()), ask.get("repo", ""))', source)


if __name__ == "__main__":
    unittest.main()
