# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The history of downloads and traffic against a made-up GitHub, and the "say that you use it" link: nothing is read while it is off, each repository at most once a day, a refusal is said and is not an
error, nothing is called when the page only looks at what is kept, and nothing external is touched until the person clicks. Invented names, no real calls."""
import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.families.traffic import traffic_engine as engine  # noqa: E402
from github_actions_monitor.ui import about  # noqa: E402

NOW = 1_800_000_000.0      # 2027-01-15 UTC
DAY = 86400


def config(**extra):
    return {"traffic": dict({"enabled": True, "repos": ["app"]}, **extra)}


class FakeGitHub:
    def __init__(self, counts=None, traffic=None, refuse=None):
        self.counts = {"v1/app.zip": 10} if counts is None else counts
        self.traffic, self.refuse, self.asked = traffic, refuse or {}, []

    def __call__(self, endpoint):
        self.asked.append(endpoint)
        for part, reason in self.refuse.items():
            if part in endpoint:
                raise engine.Refused(reason)
        if "/releases" in endpoint:
            releases = {}
            for key, count in self.counts.items():
                tag, name = key.split("/")
                releases.setdefault(tag, []).append({"name": name, "download_count": count})
            return [{"tag_name": tag, "assets": assets} for tag, assets in releases.items()]
        kind = endpoint.rsplit("/", 1)[1]
        rows = self.traffic if self.traffic is not None else [{"timestamp": "2027-01-14T00:00:00Z", "count": 7, "uniques": 3}]
        return {kind: rows}


class Traffic(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patch = mock.patch.object(engine, "state_file", lambda account="": Path(folder.name) / "traffic.json")
        patch.start()
        self.addCleanup(patch.stop)

    def test_nothing_is_read_while_it_is_off_air_gapped_or_without_repositories(self):
        github = FakeGitHub()
        for cfg in ({}, {"traffic": {"repos": ["app"]}}, dict(config(), airgapped=True), config(repos=[])):
            self.assertEqual(engine.refresh(cfg, "demo-owner", get=github, now=NOW), [])
        self.assertEqual(github.asked, [])
        self.assertIsNone(engine.tick({}))

    def test_the_chosen_names_belong_to_the_watched_account_unless_they_say_another(self):
        cfg = config(repos=["app", "other-org/lib", "app", "..", "bad name"])
        self.assertEqual(engine.selected(cfg, "demo-owner"), ["demo-owner/app", "other-org/lib"])

    def test_each_repository_once_a_day_and_new_downloads_never_go_down(self):
        github = FakeGitHub({"v1/app.zip": 10, "v0/old.zip": 90})
        self.assertEqual(engine.refresh(config(), "demo-owner", get=github, now=NOW), ["demo-owner/app"])
        calls = len(github.asked)
        self.assertEqual(engine.refresh(config(), "demo-owner", get=github, now=NOW + 60), [])
        self.assertEqual(len(github.asked), calls)
        github.counts = {"v1/app.zip": 25, "v2/app.zip": 4}      # one more release, the old one deleted
        engine.refresh(config(), "demo-owner", get=github, now=NOW + DAY)
        repo = engine.report(config(), "demo-owner")["repos"][0]
        self.assertEqual(repo["downloads"], 29)
        self.assertEqual([(d["date"], d["downloads"], d["new"]) for d in repo["days"] if d["downloads"] is not None], [("2027-01-15", 100, None), ("2027-01-16", 29, 19)])
        seen = [d for d in repo["days"] if d["date"] == "2027-01-14"][0]
        self.assertEqual((seen["views"], seen["views_unique"], seen["clones"], seen["clones_unique"], seen["downloads"]), (7, 3, 7, 3, None))
        self.assertTrue(all(e.startswith("repos/demo-owner/app/") for e in github.asked))

    def test_only_some_repositories_in_each_cycle(self):
        github = FakeGitHub()
        cfg = config(repos=["a", "b", "c"], repos_per_cycle=2)
        self.assertEqual(engine.refresh(cfg, "demo-owner", get=github, now=NOW), ["demo-owner/a", "demo-owner/b"])
        self.assertEqual(engine.refresh(cfg, "demo-owner", get=github, now=NOW), ["demo-owner/c"])

    def test_without_permission_it_is_said_and_the_downloads_are_kept(self):
        engine.refresh(config(), "demo-owner", get=FakeGitHub(refuse={"/traffic/": "no_permission"}), now=NOW)
        repo = engine.report(config(), "demo-owner")["repos"][0]
        self.assertEqual((repo["releases_status"], repo["traffic_status"], repo["downloads"]), ("ok", "no_permission", 10))
        self.assertEqual(engine.reason_of("HTTP 403: Must have push access to repository"), "no_permission")
        self.assertEqual(engine.reason_of("HTTP 403: API rate limit exceeded"), "rate_limited")
        self.assertEqual(engine.reason_of("HTTP 404: Not Found"), "missing")

    def test_visits_and_clones_can_be_switched_off(self):
        github = FakeGitHub()
        engine.refresh(config(views_clones=False), "demo-owner", get=github, now=NOW)
        self.assertFalse([e for e in github.asked if "/traffic/" in e])
        self.assertEqual(engine.report(config(), "demo-owner")["repos"][0]["traffic_status"], "off")

    def test_a_rate_limit_stops_and_the_day_is_tried_again(self):
        self.assertEqual(engine.refresh(config(), "demo-owner", get=FakeGitHub(refuse={"/releases": "rate_limited"}), now=NOW), [])
        self.assertEqual(engine.refresh(config(), "demo-owner", get=FakeGitHub(), now=NOW), ["demo-owner/app"])

    def test_old_days_are_deleted(self):
        engine.refresh(config(keep_days=30), "demo-owner", get=FakeGitHub(), now=NOW)
        engine.refresh(config(keep_days=30), "demo-owner", get=FakeGitHub(traffic=[]), now=NOW + 40 * DAY)
        self.assertEqual([d["date"] for d in engine.report(config(), "demo-owner")["repos"][0]["days"]], ["2027-02-24"])

    def test_the_csv_never_starts_a_formula_and_looking_calls_nobody(self):
        engine.refresh(config(), "demo-owner", get=FakeGitHub({"v1/=cmd.zip": 2}), now=NOW)
        with mock.patch.object(engine, "reader", side_effect=AssertionError("GitHub was asked")):
            days, files = engine.csv_text("days"), engine.csv_text("assets")
            out = engine.report(config(), "demo-owner")
        self.assertTrue(days.startswith("date,repository,downloads_total,downloads_new,views,views_unique,clones,clones_unique\n"))
        self.assertIn("2027-01-15,demo-owner/app,2,,,,,\n", days)
        self.assertIn("2027-01-15,demo-owner/app,v1,'=cmd.zip,2\n", files)
        self.assertTrue(i18n.t("cli.traffic.help"))
        self.assertEqual(len(engine.text_lines(out)), 1)


class SayThatYouUseIt(unittest.TestCase):
    def test_the_link_is_a_page_of_this_repository_with_nothing_filled_in(self):
        url = urllib.parse.urlsplit(about.LINKS["i_use_it"])
        self.assertEqual((url.scheme, url.netloc, url.path), ("https", "github.com", urllib.parse.urlsplit(about.REPO_URL).path + "/issues/new"))
        self.assertEqual(urllib.parse.parse_qs(url.query), {"template": ["i-use-it.yml"]})

    def test_showing_about_calls_nothing_external(self):
        boom = AssertionError("something external was called without a click")
        data = about.info(False, {}, {}, {"enabled": False}, "en")
        with mock.patch.object(subprocess, "Popen", side_effect=boom), mock.patch.object(urllib.request, "urlopen", side_effect=boom), mock.patch.object(socket, "create_connection", side_effect=boom):
            data = about.info(False, {}, {}, {"enabled": False}, "en")
            text = about.console_text(data, i18n.t)
        self.assertIn(about.LINKS["i_use_it"], text)
        self.assertIn(i18n.t("ui.about_i_use_it_note"), text)

    def test_only_the_about_window_knows_the_address(self):
        named = [p.name for p in (HERE / "src").rglob("*.py") if "i-use-it" in p.read_text(encoding="utf-8")]
        self.assertEqual(named, ["about.py"])
        for page in (HERE / "assets" / "static").glob("*.*"):
            self.assertNotIn("template=i-use-it", page.read_text(encoding="utf-8"), page.name)

    def test_the_form_says_that_it_is_public(self):
        form = HERE.parent / ".github" / "ISSUE_TEMPLATE" / "i-use-it.yml"
        if not form.is_file():
            self.skipTest("the repository files are not in the package")
        text = form.read_text(encoding="utf-8")
        self.assertIn("Everything you write here is public", text)
        self.assertNotIn("value: |\n        {", text)


if __name__ == "__main__":
    unittest.main()
