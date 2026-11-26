# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The identity of a repository (source, owner, name): two with one name never meet, saved data moves to it without loss, a second owner needs its switch."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from github_actions_monitor.accounts import accounts
from github_actions_monitor.app import settings_api, toolconfig
from github_actions_monitor.data_pipeline import events, repo_identity as ids
from github_actions_monitor.integrations.external_ci import extci_engine as engine
from github_actions_monitor.sentinels import alert_center
from github_actions_monitor.storage import identity_migration as migration

TWO = {"external_ci": {"enabled": True, "sources": ["gitlab;repo=app;url=https://one.example.org;project=group/app", "gitlab;repo=app;url=https://two.example.org;project=group/app"]}}


class Keys(unittest.TestCase):
    def test_a_key_goes_and_comes_back(self):
        for source, owner, name in (("github", "Me", "App"), ("gitlab@host.example.org:8443", "a/b", "c"), ("jenkins@10.0.0.5", "", "job")):
            found = ids.parse(ids.key(source, owner, name))
            self.assertEqual(found.source, source)
            self.assertEqual(found.name.lower(), name.lower())
        self.assertEqual(ids.github("Me", "App"), "github:me/app")
        self.assertIsNone(ids.parse("app"))

    def test_one_name_in_two_places_is_two_repositories(self):
        here = ids.github("me", "app")
        there = ids.external("gitlab", "https://one.example.org", "me/app", "app")
        self.assertNotEqual(here, there)
        self.assertEqual(ids.of_record({"repo": "app"}, "me"), here)
        self.assertEqual(ids.of_record({"repo": "app", "repo_key": there}, "me"), there)
        self.assertTrue(ids.same_owner(there, "someone"))
        self.assertFalse(ids.same_owner(here, "someone"))


class ExternalSources(unittest.TestCase):
    def tearDown(self):
        engine.forget()

    def test_two_servers_that_mirror_one_name_stay_apart_in_ids_runs_and_alerts(self):
        found = engine.configured(TWO)
        self.assertEqual(len(found), 2)
        self.assertEqual(len({s["id"] for s in found}), 2)
        self.assertEqual(len({s["repo_key"] for s in found}), 2)
        one_run = {"repo": "app", "name": "pipeline", "conclusion": "failure", "status": "completed", "branch": "main", "started": "2026-01-01T00:00:00Z", "url": "", "sha": "", "id": 1, "event": "push", "source": "external:gitlab"}
        for source in found:
            item = {"workflow": "pipeline", "run": one_run, "streak": 1, "total": 1, "failed": 1}
            engine._entry(source).update(reds=[engine.row_of(source, item)], runs=[one_run], last_ok=1.0, last_try=1.0, judged=1)
        self.assertEqual(len({r["workflow"] for r in engine.red_rows(TWO)}), 2)
        names = {r["name"] for r in engine.runs(TWO)}
        self.assertEqual(len(names), 2)
        self.assertNotIn("pipeline", names)      # never the name of a workflow of Actions
        self.assertEqual(len({a["id"] for a in engine.alerts(TWO) if a["code"] == engine.CODE_RED}), 2)

    def test_one_server_keeps_its_short_label(self):
        source = engine.configured({"external_ci": {"sources": TWO["external_ci"]["sources"][:1]}})[0]
        self.assertEqual((source["label"], source["id"]), ("gitlab", "gitlab:app:group/app"))


class Migration(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.ledger = self.dir / "alert_mutes.json"
        silences = [{"scope": scope, "value": value, "until_ts": 9999999999, "until": "2200-01-01T00:00:00Z"} for scope, value in (("alert", "x:app"), ("code", "x"))]
        seen = {"x:app": {"repo": "app", "first_seen": 1, "last_seen": 1}, "sys:disk": {"repo": "", "first_seen": 1, "last_seen": 1}}
        self.ledger.write_text(json.dumps({"active": silences, "history": [], "seen": seen}), encoding="utf-8")
        self.feed = self.dir / "events_state.json"
        self.feed.write_text(json.dumps({"reds": {"app|ci": {"repo": "app"}}}), encoding="utf-8")
        for patch in (mock.patch.object(alert_center, "STATE_FILE", self.ledger), mock.patch.object(events, "STATE_FILE", self.feed), mock.patch.dict(toolconfig._owner, {"pinned": None})):
            patch.start()
            self.addCleanup(patch.stop)

    def test_the_plan_only_reads_and_the_first_apply_only_records(self):
        before = self.ledger.read_bytes()
        self.assertEqual(migration.plan({"github_owner": "Alpha"})["reason"], "first")
        self.assertIsNone(migration.recorded())
        self.assertTrue(migration.apply({"github_owner": "Alpha"}, now=100)["applied"])
        self.assertEqual(migration.recorded()["owner"], "alpha")
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertFalse(migration.apply({"github_owner": "alpha"}, now=101)["applied"])

    def test_another_owner_sets_aside_what_was_decided_about_repositories_with_a_copy_first(self):
        migration.apply({"github_owner": "alpha"}, now=100)
        old_ledger = json.loads(self.ledger.read_text(encoding="utf-8"))
        self.assertEqual(migration.plan({"github_owner": "beta"})["reason"], "owner_changed")
        done = migration.apply({"github_owner": "beta"}, now=200)
        copy = json.loads((Path(done["backup"]) / "alert_mutes.json").read_text(encoding="utf-8"))
        self.assertEqual(copy, old_ledger)
        data = json.loads(self.ledger.read_text(encoding="utf-8"))
        self.assertEqual([e["scope"] for e in data["active"]], ["code"])
        self.assertEqual(list(data["seen"]), ["sys:disk"])
        aside = json.loads(migration.aside_file().read_text(encoding="utf-8"))["rows"][-1]
        self.assertEqual((aside["owner"], list(aside["ledger"]), len(aside["silences"])), ("alpha", ["x:app"], 1))
        self.assertEqual(aside["events_state"]["reds"]["app|ci"]["repo"], "app")
        self.assertEqual([p["owner"] for p in migration.recorded()["previous"]], ["alpha"])


class SecondOwner(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        for patch in (mock.patch.dict("os.environ", {"MONITOR_ACCOUNTS_DIR": str(self.base / "accounts")}), mock.patch.object(settings_api, "BACKUP_DIR", self.base / "config_backups")):
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(toolconfig.forget)
        accounts.create_account("one", "alpha")
        accounts.create_account("two", "")

    def test_the_settings_refuse_a_second_owner_until_the_switch_is_on(self):
        path = accounts.config_path("two")
        self.assertEqual(settings_api.apply({"github_owner": "beta"}, path)["errors"], {"github_owner": "extci_owner"})
        self.assertTrue(settings_api.apply({"github_owner": "alpha"}, path)["ok"])
        self.assertTrue(settings_api.apply({"sources.multi_owner": True}, path)["ok"])
        self.assertTrue(settings_api.apply({"github_owner": "beta"}, path)["ok"])
        self.assertEqual(accounts.owners(), {"one": "alpha", "two": "beta"})


if __name__ == "__main__":
    unittest.main()
