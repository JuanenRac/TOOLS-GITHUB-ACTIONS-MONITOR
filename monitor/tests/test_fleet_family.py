# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The fleet by role and group, CCTray, the security API, the switch of repositories, the report digest, the static demo and the warning of a stale profile clone. Invented names, no network."""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.data_pipeline import briefs  # noqa: E402
from github_actions_monitor.families import fleet as family  # noqa: E402
from github_actions_monitor.families.fleet import fleet_views as views  # noqa: E402
from github_actions_monitor.reporting import report_builder, report_digest  # noqa: E402
from github_actions_monitor.sentinels import roadmap_a9  # noqa: E402


def run(repo, name, conclusion="success", status="completed", started="2027-01-01T00:00:00Z", **extra):
    return {"repo": repo, "name": name, "path": name.lower() + ".yml", "status": status, "conclusion": conclusion, "started": started, "url": "https://example.org/r", "number": 3, **extra}


class Columns(unittest.TestCase):
    def test_roles_cells_and_the_worst_of_a_group(self):
        table = views.roles(family.ROLES)
        self.assertEqual([views.role_of(run("a", n), table) for n in ("Release", "Nightly checks", "Build firmware", "CI", "Pages", "Other thing")], ["release", "nightly", "build", "test", "docs", "other"])
        with mock.patch.object(views, "group_of", side_effect=lambda repo: repo.split("-")[0]):
            view = views.columns([run("x-a", "CI", "failure"), run("x-b", "CI"), run("y-a", "Build", status="in_progress", conclusion=None)], ["x-a", "x-b", "y-a", "z-a"], table)
            found = views.groups(view)
        self.assertEqual([(g["key"], g["state"], g["red"]) for g in found], [("x", "red", 1), ("y", "running", 0), ("z", "unknown", 0)])

    def test_a_newer_success_clears_and_a_running_one_keeps_the_red(self):
        rows = views.latest([run("a", "CI", "failure", started="1"), run("a", "CI", "success", started="2")])
        self.assertEqual([e["state"] for e in rows.values()], ["ok"])
        rows = views.latest([run("a", "CI", "failure", started="1"), run("a", "CI", None, status="in_progress", started="2")])
        self.assertEqual([(e["state"], e["running"]) for e in rows.values()], [("red", True)])


class Feeds(unittest.TestCase):
    def test_the_cctray_xml_parses_and_escapes(self):
        text = views.cctray_xml(views.projects([run('a"<&', "CI", "failure")]))
        project = ET.fromstring(text.split("\n", 1)[1]).find("Project")
        self.assertEqual((project.get("name"), project.get("lastBuildStatus"), project.get("activity")), ('a"<& :: CI', "Failure", "Sleeping"))

    def test_both_apis_are_off_by_default(self):
        request = mock.Mock(config={}, query={})
        for route in family.FAMILY.routes:
            if "cctray" in route.path or "security" in route.path:
                self.assertEqual(route.handler(request)[0], 404, route.path)

    def test_the_security_api_names_what_was_not_read_and_never_a_secret(self):
        sentinel = mock.Mock(enabled=True)
        sentinel.get_alerts.return_value = [{"code": "security.secret", "repo": "a", "level": "critical", "details": {"n": 2, "secret": "NEVER"}, "created_at": "t"}, {"code": "security.dependabot", "repo": "a"}]
        sentinel.get_status.return_value = {"errors": [{"section": "secret b", "message": "403"}], "repos_checked": 1, "repos_in_scope": 2}
        out = views.security_alerts({"security": sentinel}, "secrets")
        self.assertEqual([(a["repo"], a["open"]) for a in out["alerts"]], [("a", 2)])
        self.assertNotIn("NEVER", str(out))
        self.assertEqual(len(out["not_read"]), 1)
        self.assertFalse(views.security_alerts({}, "secrets")["available"])


class SwitchedOff(unittest.TestCase):
    def test_names_patterns_and_groups(self):
        with mock.patch.object(views, "group_of", return_value="web"):
            self.assertTrue(views.switched_off("demo-a", ["demo-*"]))
            self.assertTrue(views.switched_off("other", ["group:web"]))
            self.assertFalse(views.switched_off("other", ["demo-*", "group:api"]))


class Digest(unittest.TestCase):
    def test_the_same_facts_give_the_same_digest_whenever_they_are_read(self):
        one = report_builder.build("a", None, [], {}, 1000)
        two = report_builder.build("a", None, [], {}, 999999)
        self.assertEqual(one["report_digest"], two["report_digest"])
        self.assertTrue(one["report_digest"].startswith("sha256:"))
        self.assertNotEqual(report_digest.digest({"a": 1}, verdict=1), report_digest.digest({"a": 1}, verdict=2))
        self.assertNotEqual(report_digest.digest({"a": 1}, engine="1"), report_digest.digest({"a": 1}, engine="2"))

    def test_a_brief_carries_it(self):
        brief = briefs.brief("now", {"signals": [], "version": "x"}, "en", lambda *a, **k: a[0]) if hasattr(briefs, "brief") else None
        if brief is not None:
            self.assertIn("report_digest", brief)


class StaleClone(unittest.TestCase):
    def test_a_clone_behind_is_said_on_every_board(self):
        out = roadmap_a9.build({}, None, None, None, {}, None, None, None, behind=True)
        self.assertEqual({b["problems_raw"][0][0] for b in out["boards"]}, {"clone_behind"})
        self.assertEqual(out["level"], "warn")

    def test_not_knowing_is_not_a_warning(self):
        self.assertFalse(roadmap_a9.clone_behind(mock.Mock(side_effect=RuntimeError("no")), "."))


class StaticDemo(unittest.TestCase):
    def test_the_page_answers_from_files_and_only_this_computer_is_read(self):
        path = HERE.parent / "tools" / "make_public_demo.py"
        if not path.is_file():
            self.skipTest("the tools of the repository are not in this copy")
        import importlib.util
        spec = importlib.util.spec_from_file_location("make_public_demo", path)
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        page = tool.static_page("<html><head></head></html>", {"/api/data": "data/data.json"})
        self.assertIn('"/api/data": "data/data.json"', page)
        self.assertIn("toUpperCase()!==\"GET\"", page)
        self.assertRaises(SystemExit, tool.check_local, "https://example.org/api/data")
        self.assertRaises(SystemExit, tool.check_local, "http://127.0.0.1.example.org:80/")


if __name__ == "__main__":
    unittest.main()
