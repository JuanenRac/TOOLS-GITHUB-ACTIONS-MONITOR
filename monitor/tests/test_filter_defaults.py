# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A new user must never end up with almost no repository because of the example catalogue: the catch-all group, the template of the lite edition, what lite inherits and the warning about a filter that hides repositories."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import toolconfig  # noqa: E402

ACCOUNT = ["demo-alpha-core", "demo-alpha-app", "demo-beta-fw", "random-notes", "another-thing", "MYPROJECT-X", "TEAM-Y"]


class CatchAll(unittest.TestCase):
    def setUp(self):
        self.example = json.loads((HERE / "assets" / "examples" / "ecosystems.example.json").read_text(encoding="utf-8"))["ecosystems"]
        toolconfig.set_ecosystems(self.example)

    def tearDown(self):
        toolconfig.set_ecosystems(None)

    def test_the_neutral_catalogue_has_a_last_group_that_takes_everything_else(self):
        names = list(self.example)
        self.assertEqual(names[-1], "rest")
        self.assertEqual(self.example["rest"]["prefixes"], ["*"])
        self.assertFalse(self.example["rest"].get("external"))
        self.assertEqual(toolconfig.ecosystem_of("MYPROJECT-X"), "main")
        self.assertEqual(toolconfig.ecosystem_of("TEAM-Y"), "other-team")
        for repo in ("random-notes", "demo-alpha-app", "x"):
            self.assertEqual(toolconfig.ecosystem_of(repo), "rest", repo)

    def test_with_the_example_catalogue_and_all_ecosystems_every_repository_is_watched(self):
        am.DISCOVERED.update({"at": 0.0, "names": []})
        config = {**am.DEFAULTS, "ecosystems": "all", "exclude": [], "github_owner": "demo-owner"}
        with mock.patch.object(am, "gh", return_value=[{"name": n} for n in ACCOUNT]):
            watched = am.watched_repos(config, force=True)
        self.assertEqual(sorted(watched), sorted(ACCOUNT))
        self.assertEqual(am.HIDDEN["hidden"], 0)
        self.assertEqual(am.HIDDEN["discovered"], len(ACCOUNT))

    def test_the_example_catalogue_still_passes_the_release_checks(self):
        import make_release
        self.assertEqual(make_release.example_profiles_problems(HERE), [])


class HiddenRepositories(unittest.TestCase):
    def tearDown(self):
        toolconfig.set_ecosystems(None)
        am.DISCOVERED.update({"at": 0.0, "names": []})

    def test_a_filter_that_leaves_repositories_out_is_counted(self):
        toolconfig.set_ecosystems({"main": {"label": "Mine", "prefixes": ["demo-"]}})
        am.DISCOVERED.update({"at": 0.0, "names": []})
        config = {**am.DEFAULTS, "ecosystems": "all", "exclude": [], "github_owner": "demo-owner", "show_unclassified": False}
        with mock.patch.object(am, "gh", return_value=[{"name": n} for n in ACCOUNT]):
            watched = am.watched_repos(config, force=True)
        self.assertEqual(sorted(watched), ["demo-alpha-app", "demo-alpha-core", "demo-beta-fw"])
        self.assertEqual((am.HIDDEN["hidden"], am.HIDDEN["discovered"]), (4, 7))
        self.assertEqual(am.HIDDEN["names"], ["MYPROJECT-X", "TEAM-Y", "another-thing", "random-notes"])

    def test_a_repository_that_no_group_claims_is_shown_as_unclassified_by_default(self):
        toolconfig.set_ecosystems({"main": {"label": "Mine", "prefixes": ["demo-"]}})
        am.DISCOVERED.update({"at": 0.0, "names": []})
        config = {**am.DEFAULTS, "ecosystems": "all", "exclude": [], "github_owner": "demo-owner"}
        with mock.patch.object(am, "gh", return_value=[{"name": n} for n in ACCOUNT]):
            watched = am.watched_repos(config, force=True)
        self.assertEqual(sorted(watched), sorted(ACCOUNT))
        self.assertEqual(am.HIDDEN["hidden"], 0)
        self.assertEqual(am.ecosystem_of("random-notes"), "other")
        self.assertIn("other", am.render_page().split("/*I18N_DATA*/")[0] + am.render_page())
        with mock.patch.object(am, "gh", return_value=[{"name": n} for n in ACCOUNT]):
            only_main = am.watched_repos({**config, "ecosystems": ["main"]}, force=True)      # an explicit choice of ecosystems is respected
        self.assertEqual(sorted(only_main), ["demo-alpha-app", "demo-alpha-core", "demo-beta-fw"])

    def test_the_numbers_travel_to_the_page_and_the_page_warns_in_every_language(self):
        data = am.build({**am.DEFAULTS, "mode": "full"}, [], 0.0, 0, False, "")
        self.assertIn("hidden", data)
        self.assertIn("discovered", data)
        page = (HERE / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")
        for needle in ('id="hidden"', "ui.hidden_repos", "d.repos.length<tot/2"):
            self.assertIn(needle, page, needle)
        for lang in i18n.LANGS:
            cat = i18n.catalogue(lang)
            self.assertIn("{n}", cat["ui.hidden_repos"])
            self.assertIn("{m}", cat["ui.hidden_repos"])
            self.assertIn("mon.lite_inherited", cat)
            self.assertIn("ui.hidden_repos", i18n.ui_catalogues()[lang])


class LiteStart(unittest.TestCase):
    def start(self, complete):
        saved = (am.LITE["on"], am.CONFIG_FILE)
        out = io.StringIO()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                am.LITE["on"], am.CONFIG_FILE = True, Path(tmp) / "actions_monitor_lite.json"
                with mock.patch.object(am, "HERE", Path(tmp)):
                    (Path(tmp) / "actions_monitor.example.json").write_bytes((HERE / "assets" / "examples" / "actions_monitor.example.json").read_bytes())
                    if complete is not None:
                        (Path(tmp) / "actions_monitor.json").write_text(json.dumps(complete), encoding="utf-8")
                    with contextlib.redirect_stdout(out):
                        config = am.load_config()
                    written = json.loads(am.CONFIG_FILE.read_text(encoding="utf-8"))
        finally:
            am.LITE["on"], am.CONFIG_FILE = saved
        return config, written, out.getvalue()

    def test_the_neutral_template_watches_every_ecosystem(self):
        config, written, said = self.start(None)
        self.assertEqual(written["ecosystems"], "all")
        self.assertEqual((written["mode"], written["sentinel"]), ("lite", {"enabled": False}))
        self.assertEqual(said, "")

    def test_it_inherits_what_to_watch_and_nothing_else(self):
        complete = {"github_owner": "demo-owner", "ecosystems": ["main"], "ecosystems_file": "my_ecosystems.json", "targets_file": "t.json", "profiles_file": "p.json", "exclude": ["old-repo"],
                    "repos": "all", "language": "de", "sentinel": {"enabled": True, "notify_command": ["rm"]}, "ai": {"provider": "ollama"}, "webhook": {"enabled": True, "secret": "S" * 40},
                    "outputs": {"prometheus": {"enabled": True}}, "notify": {"enabled": True}, "refresh_seconds": 77}
        config, written, said = self.start(complete)
        for key in ("github_owner", "ecosystems", "ecosystems_file", "targets_file", "profiles_file", "exclude", "language"):
            self.assertEqual(written[key], complete[key], key)
        self.assertEqual(written["sentinel"], {"enabled": False})           # never the sentinel, the AI, the webhook, the outputs or the notifications
        self.assertEqual(written["webhook"], {"enabled": False, "secret": ""})
        self.assertNotEqual(written.get("ai"), complete["ai"])
        self.assertNotEqual(written.get("outputs"), complete["outputs"])
        self.assertNotEqual(written.get("notify"), complete["notify"])
        self.assertEqual(written["refresh_seconds"], 77)                    # the pace of the complete monitor is inherited, so both editions read at the same rhythm
        self.assertNotIn("S" * 40, json.dumps(written))
        self.assertIn("github_owner", said)
        self.assertNotIn("S" * 40, said)
        self.assertEqual(config["github_owner"], "demo-owner")

    def test_an_existing_lite_file_is_never_overwritten(self):
        saved = (am.LITE["on"], am.CONFIG_FILE)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                am.LITE["on"], am.CONFIG_FILE = True, Path(tmp) / "actions_monitor_lite.json"
                am.CONFIG_FILE.write_text(json.dumps({"ecosystems": ["mine"]}), encoding="utf-8")
                with mock.patch.object(am, "HERE", Path(tmp)):
                    (Path(tmp) / "actions_monitor.json").write_text(json.dumps({"github_owner": "other"}), encoding="utf-8")
                    config = am.load_config()
                self.assertEqual(json.loads(am.CONFIG_FILE.read_text(encoding="utf-8")), {"ecosystems": ["mine"]})
                self.assertEqual(config["ecosystems"], ["mine"])
        finally:
            am.LITE["on"], am.CONFIG_FILE = saved


if __name__ == "__main__":
    unittest.main()
