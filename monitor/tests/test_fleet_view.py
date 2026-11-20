# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The fleet view: grouping, labels, ordering, saved filters and paging over a synthetic account of 250 repositories (no network), the settings that drive it, the route and the page."""
import inspect
import re
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor, settings_api  # noqa: E402
from github_actions_monitor.health import fleet, repo_view  # noqa: E402
from github_actions_monitor.security import auth  # noqa: E402

NOW = 1_800_000_000.0
REPOS = 250


def synthetic_views(n=REPOS):
    """n repositories: every 25th is red, every 10th has a warning, every 7th is in the second ecosystem, the names start with team-a, team-b or tool."""
    runs, failing, alerts = [], [], []
    names = [f"{('team-a', 'team-b', 'tool')[i % 3]}-{i:03d}" for i in range(n)]
    for i, name in enumerate(names):
        runs.append({"repo": name, "name": "CI", "status": "completed", "conclusion": "failure" if i % 25 == 0 else "success", "started": NOW - 60 * (i + 1), "seconds": 30})
        if i % 25 == 0:
            failing.append({"repo": name, "workflow": "CI"})
        if i % 10 == 3:
            alerts.append({"id": f"c:{name}", "code": "collab.issue.stale", "level": "warning", "sentinel": "collab", "repo": name, "title": "t", "created_at": "2026-01-01T00:00:00Z"})
    return [repo_view.repo_view(name, runs, failing, [], alerts, None, {"ci": "healthy"}, "beta" if i % 7 == 0 else "alpha", NOW) for i, name in enumerate(names)]


CFG = {"fleet": {"labels": ["team-a-*=alpha-team", "team-b-*=beta-team"], "saved_filters": ["attention=bad|||", "betas=|beta||"], "page_size": 40}}


class Grouping(unittest.TestCase):
    def setUp(self):
        self.views = synthetic_views()

    def test_every_repository_is_in_exactly_one_group_and_the_totals_add_up(self):
        out = fleet.fleet_view(self.views, CFG)
        self.assertEqual((out["all"], out["shown"], len(out["rows"])), (REPOS, REPOS, REPOS))
        self.assertEqual(sum(g["repos"] for g in out["groups"]), REPOS)
        self.assertEqual(len({r["repo"] for r in out["rows"]}), REPOS)
        self.assertEqual(sum(out["totals"].values()), REPOS)
        self.assertFalse(out["truncated"])

    def test_the_default_is_by_ecosystem_and_groups_come_by_risk(self):
        out = fleet.fleet_view(self.views, {})
        self.assertEqual((out["group_by"], out["sort"], out["page_size"]), ("ecosystem", "risk", 50))
        self.assertEqual([g["risk"] for g in out["groups"]], sorted((g["risk"] for g in out["groups"]), reverse=True))
        self.assertEqual({g["key"] for g in out["groups"]}, {"alpha", "beta"})

    def test_a_label_is_the_first_pattern_that_fits_and_the_rest_have_no_label(self):
        out = fleet.fleet_view(self.views, CFG, group="label")
        self.assertEqual({g["key"] for g in out["groups"]}, {"alpha-team", "beta-team", ""})
        self.assertEqual({r["label"] for r in out["rows"] if r["repo"].startswith("tool")}, {""})
        self.assertEqual(fleet.label_of("TEAM-A-001", ["team-a-*=x"]), "x")      # names are compared without case

    def test_grouping_by_state_and_not_at_all(self):
        by_state = fleet.fleet_view(self.views, CFG, group="state")
        self.assertEqual({g["key"] for g in by_state["groups"]}, {"bad", "warn", "ok"})
        flat = fleet.fleet_view(self.views, CFG, group="none")
        self.assertEqual([g["key"] for g in flat["groups"]], [""])
        self.assertEqual(fleet.fleet_view(self.views, CFG, group="nonsense")["group_by"], "ecosystem")      # an unknown value falls back to the setting

    def test_the_orders_inside_a_group(self):
        flat = lambda sort: [r["repo"] for r in fleet.fleet_view(self.views, CFG, group="none", sort=sort)["rows"]]      # noqa: E731
        self.assertEqual(flat("name"), sorted(flat("name")))
        self.assertEqual(flat("risk")[0], "team-a-000")      # the red one with the most risk, then by name
        self.assertEqual(flat("last_run")[0], "team-a-000")      # the most recent run first
        self.assertEqual(fleet.fleet_view(self.views, CFG, group="none", sort="state")["rows"][0]["state"], "bad")

    def test_the_filters_narrow_the_groups_and_the_totals(self):
        out = fleet.fleet_view(self.views, CFG, severity="bad")
        self.assertEqual(out["shown"], out["totals"]["bad"])
        self.assertEqual(out["shown"], sum(1 for v in self.views if v["state"] == "bad"))
        self.assertEqual(fleet.fleet_view(self.views, CFG, text="tool-0")["shown"], sum(1 for v in self.views if "tool-0" in v["repo"]))
        self.assertEqual(fleet.fleet_view(self.views, CFG, label="beta-team")["shown"], sum(1 for v in self.views if v["repo"].startswith("team-b")))
        self.assertEqual(fleet.fleet_view(self.views, CFG, text="zzz")["rows"], [])

    def test_a_saved_filter_fills_what_was_not_asked_and_an_explicit_filter_wins(self):
        saved = fleet.fleet_view(self.views, CFG, saved="attention")
        self.assertEqual(saved["filters"]["severity"], "bad")
        self.assertEqual({r["state"] for r in saved["rows"]}, {"bad"})
        self.assertEqual(saved["saved_filters"], ["attention", "betas"])
        beta = fleet.fleet_view(self.views, CFG, saved="betas")
        self.assertEqual({r["ecosystem"] for r in beta["rows"]}, {"beta"})
        self.assertEqual(fleet.fleet_view(self.views, CFG, saved="attention", severity="warn")["filters"]["severity"], "warn")
        self.assertEqual(fleet.fleet_view(self.views, CFG, saved="missing")["shown"], REPOS)      # a name that is not saved is ignored

    def test_a_list_longer_than_the_limit_is_cut_and_says_so(self):
        out = fleet.fleet_view(self.views, CFG, limit=100)
        self.assertEqual((len(out["rows"]), out["truncated"], out["shown"]), (100, True, REPOS))


class Paging(unittest.TestCase):
    def test_the_pages_of_the_client_cover_every_row_once(self):
        out = fleet.fleet_view(synthetic_views(), CFG)
        size = out["page_size"]
        self.assertEqual(size, 40)
        pages = [out["rows"][i:i + size] for i in range(0, len(out["rows"]), size)]
        self.assertEqual(len(pages), 7)      # 250 rows, 40 per page
        self.assertEqual([r["repo"] for page in pages for r in page], [r["repo"] for r in out["rows"]])

    def test_the_page_draws_one_page_and_has_a_pager(self):
        html = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('id="fleet-sec"', html)
        self.assertIn("slice(FLEET_PAGE*size,(FLEET_PAGE+1)*size)", html)      # one page of rows is drawn, never all
        self.assertIn('"/api/team/fleet?"', html)


class Load(unittest.TestCase):
    def test_250_repositories_group_and_order_fast_through_the_real_health(self):
        data = {"runs": [{"repo": f"r{i:03d}", "name": "CI", "status": "completed", "conclusion": "success", "started": NOW - 30 * i} for i in range(REPOS)], "failing": [], "active": [],
                "repos": [f"r{i:03d}" for i in range(REPOS)]}
        old = (actions_monitor.STATE.get("data"), actions_monitor.SENTINEL["registry"], actions_monitor.SENTINEL["obj"])
        self.addCleanup(lambda: (actions_monitor.STATE.update(data=old[0]), actions_monitor.SENTINEL.update(registry=old[1], obj=old[2])))
        actions_monitor.STATE["data"] = data
        actions_monitor.SENTINEL.update(registry=None, obj=None)
        with mock.patch.object(actions_monitor, "credential_alerts", return_value=[]), mock.patch.object(actions_monitor, "score_alerts", return_value=[]):
            views = actions_monitor.health_views(NOW)
        started = time.perf_counter()
        for group in ("ecosystem", "label", "state", "none"):
            out = fleet.fleet_view(views, CFG, group=group)
            self.assertEqual(len(out["rows"]), REPOS)
        self.assertLess(time.perf_counter() - started, 10)      # wide on purpose: it catches a cost that grows with repositories squared, not milliseconds


class Settings(unittest.TestCase):
    def test_the_defaults_are_conservative_and_a_bad_value_falls_back(self):
        self.assertEqual(fleet.settings({}), {"page_size": 50, "group_by": "ecosystem", "sort": "risk", "show_all_active": True, "labels": [], "saved_filters": []})
        self.assertEqual(actions_monitor.DEFAULTS["fleet"]["page_size"], 50)
        bad = fleet.settings({"fleet": {"page_size": 3, "group_by": "x", "sort": 7, "labels": ["no equals", 5], "saved_filters": ["bad"]}})
        self.assertEqual((bad["page_size"], bad["group_by"], bad["sort"], bad["labels"], bad["saved_filters"]), (50, "ecosystem", "risk", [], []))
        self.assertEqual(fleet.settings({"fleet": {"page_size": True}})["page_size"], 50)

    def test_the_settings_page_checks_them(self):
        ok = settings_api.check_value
        self.assertEqual(ok("fleet.page_size", 100), (True, 100))
        self.assertEqual(ok("fleet.page_size", 5), (False, "range"))
        self.assertEqual(ok("fleet.group_by", "label"), (True, "label"))
        self.assertEqual(ok("fleet.group_by", "owner"), (False, "enum"))
        self.assertEqual(ok("fleet.labels", ["team-*=backend"]), (True, ["team-*=backend"]))
        self.assertEqual(ok("fleet.labels", ["team-*"]), (False, "names"))
        self.assertEqual(ok("fleet.labels", ["a=b;rm"]), (False, "names"))
        self.assertEqual(ok("fleet.saved_filters", ["attention=bad||backend|"]), (True, ["attention=bad||backend|"]))
        self.assertEqual(ok("fleet.saved_filters", ["x=critical|||"]), (False, "names"))

    def test_every_text_exists_in_the_eight_languages_with_the_same_placeholders(self):
        keys = ("ui.cfg_b_fleet", "ui.fleet_title", "ui.fleet_summary", "ui.fleet_page", "ui.fleet_group_line", "ui.fleet_truncated", "cfg.f.fleet.labels", "cfg.h.fleet.saved_filters")
        ph = re.compile(r"\{[a-z]+\}")
        for key in keys:
            base = sorted(ph.findall(i18n.tl("en", key)))
            for lang in i18n.LANGS:
                text = i18n.tl(lang, key)
                self.assertNotEqual(text, key, f"{lang}:{key}")
                self.assertEqual(sorted(ph.findall(text)), base, f"{lang}:{key}")


class Route(unittest.TestCase):
    def test_the_route_is_served_read_only_for_viewers_and_lite_does_not_have_it(self):
        self.assertIn('path == "/api/team/fleet"', inspect.getsource(actions_monitor.Handler))
        self.assertEqual(auth.required_role("GET", "/api/team/fleet"), "viewer")
        self.assertIn("/api/team", actions_monitor.LITE_PATHS)


if __name__ == "__main__":
    unittest.main()
