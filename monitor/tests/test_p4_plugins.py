# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Plugins: manifests, trust, the guard, the registry and the three official examples. No clock, no network, no GitHub."""
import json
import re
import tempfile
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.phase4 import official_plugins as op
from github_actions_monitor.phase4 import plugins
from github_actions_monitor.sentinels import sentinel_base

NOW = 1_800_000_000          # a fixed instant
DAY = 86400


def iso(seconds):
    return op._iso(seconds)


def manifest(**over):
    base = {"name": "demo", "version": "1.0.0", "api_compat": "1", "permissions": ["read_github"], "trust": "official", "entry": "pkg.mod:Cls"}
    base.update(over)
    return base


class FakeCtx:
    account_id = "acc"

    def __init__(self, data):
        self.data, self.seen = data, []

    def plugin_repos(self):
        return list(self.data)

    def plugin_fetch(self, kind, repo):
        self.seen.append((kind, repo))
        value = self.data[repo].get(kind, [])
        if isinstance(value, Exception):
            raise value
        return value


class Manifests(unittest.TestCase):
    def test_valid(self):
        m, problems = plugins.validate_manifest(manifest(author="me", description="d"))
        self.assertEqual((problems, m["name"]), ([], "demo"))

    def test_each_rejection_is_clear(self):
        cases = {
            "missing:name": {k: v for k, v in manifest().items() if k != "name"},
            "bad:name": manifest(name="Bad Name"),
            "reserved_name:ci": manifest(name="ci"),
            "bad:version": manifest(version="1.0"),
            "incompatible_api:2": manifest(api_compat="2"),
            "bad:trust": manifest(trust="trusted"),
            "bad:entry": manifest(entry="os.system"),
            "forbidden_permission:write_github": manifest(permissions=["write_github"]),
            "unknown_permission:root": manifest(permissions=["root"]),
            "bad:permissions": manifest(permissions="read_github"),
            "duplicate_permissions": manifest(permissions=["read_github", "read_github"]),
            "unknown_field:extra": manifest(extra=1),
            "bad:author": manifest(author=5),
        }
        for want, data in cases.items():
            m, problems = plugins.validate_manifest(data)
            self.assertIsNone(m, want)
            self.assertIn(want, problems)

    def test_not_an_object(self):
        for bad in (None, [], "x", 3):
            self.assertEqual(plugins.validate_manifest(bad), (None, ["not_an_object"]))

    def test_entry_check_refuses_a_trailing_line_feed(self):
        self.assertIsNone(plugins.ENTRY_RE.match("pkg.mod:Cls\n"))
        self.assertIsNone(plugins.NAME_RE.match("demo\n"))
        self.assertIsNone(plugins.VERSION_RE.match("1.0.0\n"))

    def test_text_is_translated(self):
        en = plugins.describe_problems(["bad:name"], "en")
        self.assertIn("bad:name", en)
        self.assertNotEqual(en, plugins.describe_problems(["bad:name"], "ja"))


class Discovery(unittest.TestCase):
    def test_finds_valid_and_reports_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name, content in (("good", json.dumps(manifest())), ("bad", json.dumps(manifest(trust="x"))), ("broken", "{not json")):
                (base / "plugins" / name).mkdir(parents=True)
                (base / "plugins" / name / "plugin.json").write_text(content, encoding="utf-8")
            (base / "plugins" / "nofile").mkdir()
            found = {p.parent.name: (m, probs) for p, m, probs in plugins.discover(["plugins"], base)}
        self.assertEqual(sorted(found), ["bad", "broken", "good"])
        self.assertIsNotNone(found["good"][0])
        self.assertEqual(found["bad"][1], ["bad:trust"])
        self.assertEqual(found["broken"][1], ["unreadable"])

    def test_a_directory_outside_the_base_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp)
            (outer / "base").mkdir()
            (outer / "evil" / "p").mkdir(parents=True)
            (outer / "evil" / "p" / "plugin.json").write_text(json.dumps(manifest()), encoding="utf-8")
            self.assertEqual(plugins.discover(["../evil", "missing"], outer / "base"), [])


class Boom(sentinel_base.BaseSentinel):
    name = "boom"
    refresh_seconds = 10

    def tick(self):
        raise RuntimeError("tick exploded")

    def get_status(self):
        raise ValueError("status exploded")

    def get_alerts(self):
        raise KeyError("alerts exploded")

    def get_metrics(self):
        raise OSError("metrics exploded")

    def get_config_schema(self):
        return {}


class Fine(sentinel_base.BaseSentinel):
    name = "fine"
    refresh_seconds = 10
    ticks = 0

    def tick(self):
        self.ticks += 1

    def get_status(self):
        return {"enabled": True, "level": "ok"}

    def get_alerts(self):
        good = {"id": "x:1", "code": "demo.thing", "level": "info", "sentinel": "ci", "account_id": "", "repo": None, "title": "t", "details": {}, "created_at": "now"}
        return [good, {"id": "no-code"}, "junk", dict(good, level="fatal"), dict(good, code="Bad Code"), dict(good, id="")]

    def get_metrics(self):
        return {"a": 1, "b": "text", "c": True, "d": 2.5}

    def get_config_schema(self):
        return {}


class GuardTests(unittest.TestCase):
    def test_a_plugin_that_raises_never_propagates(self):
        guard = plugins.Guard("boom", Boom(None, {}), max_failures=3)
        self.assertFalse(guard.tick())
        self.assertIn("RuntimeError in tick", guard.last_error)
        self.assertEqual(guard.alerts(), [])
        self.assertTrue(guard.status()["failures"] >= 1)
        self.assertIsInstance(guard.metrics(), dict)

    def test_set_aside_after_the_failures_in_a_row_and_back_by_hand(self):
        guard = plugins.Guard("boom", Boom(None, {}), max_failures=3)
        for _ in range(3):
            guard.tick()
        self.assertTrue(guard.set_aside)
        self.assertEqual(guard.status()["level"], "error")
        before = guard.total_failures
        self.assertFalse(guard.tick())
        self.assertEqual(guard.total_failures, before)       # not even called
        guard.reset()
        self.assertFalse(guard.set_aside)
        self.assertEqual(guard.failures, 0)

    def test_success_resets_the_run(self):
        sentinel = Fine(None, {})
        guard = plugins.Guard("fine", sentinel, 3)
        guard.failures = 2
        self.assertTrue(guard.tick())
        self.assertEqual((guard.failures, guard.ticks_ok), (0, 1))

    def test_alerts_are_filtered_and_stamped_with_the_plugin_name(self):
        guard = plugins.Guard("fine", Fine(None, {}), 3)
        alerts = guard.alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["sentinel"], "fine")      # it cannot pass for the core's "ci"

    def test_metrics_keep_numbers_only(self):
        m = plugins.Guard("fine", Fine(None, {}), 3).metrics()
        self.assertEqual((m["a"], m["d"]), (1, 2.5))
        self.assertNotIn("b", m)
        self.assertNotIn("c", m)
        self.assertEqual(m["plugin_set_aside"], 0)


class Registry(unittest.TestCase):
    def settings(self, **over):
        s = {"enabled": True, "allow_third_party": False, "disabled_by_account": {}, "max_consecutive_failures": 2}
        s.update(over)
        return s

    def factory(self, built=None):
        def make(m, ctx, cfg):
            if m["name"] == "nobuild":
                raise RuntimeError("cannot")
            if built is not None:
                built.append(m["name"])
            return Boom(ctx, cfg) if m["name"] == "boom" else Fine(ctx, cfg)
        return make

    def test_off_loads_nothing(self):
        reg = plugins.PluginRegistry(self.settings(enabled=False), self.factory())
        self.assertIsNone(reg.load(manifest()))
        self.assertEqual(reg.rejected["demo"], "plugins_off")

    def test_third_party_is_not_loaded_by_default_and_the_text_says_why(self):
        built = []
        reg = plugins.PluginRegistry(self.settings(), self.factory(built))
        self.assertIsNone(reg.load(manifest(name="outsider", trust="third_party")))
        self.assertEqual(built, [])
        self.assertIn("same power", reg.rejection_text("outsider", "en"))
        self.assertNotEqual(reg.rejection_text("outsider", "en"), reg.rejection_text("outsider", "de"))
        reg2 = plugins.PluginRegistry(self.settings(allow_third_party=True), self.factory(built))
        self.assertIsNotNone(reg2.load(manifest(name="outsider", trust="third_party")))

    def test_a_build_failure_and_a_duplicate_are_rejected_not_raised(self):
        reg = plugins.PluginRegistry(self.settings(), self.factory())
        self.assertIsNone(reg.load(manifest(name="nobuild")))
        self.assertEqual(reg.rejected["nobuild"], "build_failed")
        self.assertIsNotNone(reg.load(manifest()))
        self.assertIsNone(reg.load(manifest()))
        self.assertEqual(reg.rejected["demo"], "duplicate")

    def test_a_failing_plugin_does_not_stop_the_others(self):
        reg = plugins.PluginRegistry(self.settings(), self.factory())
        reg.load(manifest(name="boom"))
        reg.load(manifest(name="fine"))
        for _ in range(3):
            result = reg.tick_all()
        self.assertEqual(result, {"boom": False, "fine": True})
        self.assertTrue(reg.health()["boom"]["set_aside"])
        self.assertFalse(reg.health()["fine"]["set_aside"])
        self.assertEqual(len(reg.alerts()), 1)

    def test_switch_per_account(self):
        reg = plugins.PluginRegistry(self.settings(disabled_by_account={"acc2": ["fine"]}), self.factory())
        reg.load(manifest(name="fine"))
        self.assertEqual(list(reg.tick_all("acc1")), ["fine"])
        self.assertEqual(reg.tick_all("acc2"), {})
        self.assertEqual(reg.alerts("acc2"), [])
        self.assertFalse(reg.enabled_for("ghost", "acc1"))

    def test_load_all_records_invalid_manifests(self):
        reg = plugins.PluginRegistry(self.settings(), self.factory())
        loaded = reg.load_all([(Path("a/plugin.json"), manifest(name="fine"), []), (Path("b/plugin.json"), None, ["bad:name"])])
        self.assertEqual(loaded, ["fine"])
        self.assertEqual(reg.rejected[str(Path("b/plugin.json"))], "invalid:bad:name")
        self.assertIn("bad:name", reg.rejection_text(str(Path("b/plugin.json"))))

    def test_official_factory_builds_only_official_entries(self):
        ctx = FakeCtx({})
        for name, m in op.MANIFESTS.items():
            self.assertEqual(plugins.validate_manifest(m)[1], [], name)
            self.assertEqual(op.official_factory(m, ctx, {}).name, name)
        with self.assertRaises(LookupError):
            op.official_factory(manifest(entry="os:system"), ctx, {})


class Examples(unittest.TestCase):
    def build(self, cls, data, **cfg):
        return cls(FakeCtx(data), cfg, clock=lambda: NOW)

    def test_discussions(self):
        old, fresh = iso(NOW - 10 * DAY), iso(NOW - 2 * DAY)
        s = self.build(op.DiscussionsSentinel, {"o/r": {"discussions": [
            {"number": 1, "is_question": True, "answered": False, "created_at": old},
            {"number": 2, "is_question": True, "answered": True, "created_at": old},
            {"number": 3, "is_question": True, "answered": False, "created_at": fresh},
            {"number": 4, "is_question": False, "created_at": old},
            {"number": 5, "is_question": True, "answered": False, "closed": True, "created_at": old},
            {"number": 6, "is_question": True, "answered": False, "created_at": "garbage"}]}})
        s.tick()
        alerts = s.get_alerts()
        self.assertEqual([a["id"] for a in alerts], ["discussions.unanswered:o/r:#1"])
        self.assertEqual((alerts[0]["details"]["days"], alerts[0]["level"], alerts[0]["account_id"]), (10, "info", "acc"))
        s2 = self.build(op.DiscussionsSentinel, {"o/r": {"discussions": [{"number": 3, "is_question": True, "answered": False, "created_at": iso(NOW - 2 * DAY)}]}}, unanswered_days=2)
        s2.tick()
        self.assertEqual(len(s2.get_alerts()), 1)

    def test_releases(self):
        s = self.build(op.ReleaseNotesSentinel, {"o/r": {"releases": [
            {"tag": "v1", "draft": True, "created_at": iso(NOW - 20 * DAY)}, {"tag": "v2", "draft": True, "created_at": iso(NOW - 1 * DAY)},
            {"tag": "v3", "draft": False, "body": "  "}, {"tag": "v4", "draft": False, "body": "notes"}]}})
        s.tick()
        self.assertEqual(sorted(a["code"] for a in s.get_alerts()), ["releases.draft_old", "releases.no_notes"])

    def test_packages(self):
        s = self.build(op.PackagesSentinel, {"o/r": {"packages": [
            {"name": "a", "last_published_at": iso(NOW - 400 * DAY), "versions": 3}, {"name": "b", "last_published_at": iso(NOW - 1 * DAY), "versions": 500},
            {"name": "c", "last_published_at": iso(NOW - 1 * DAY), "versions": True}]}})
        s.tick()
        self.assertEqual(sorted(a["code"] for a in s.get_alerts()), ["packages.many_versions", "packages.stale"])

    def test_one_repository_that_fails_does_not_hide_the_others(self):
        s = self.build(op.PackagesSentinel, {"bad/r": {"packages": OSError("403")}, "good/r": {"packages": [{"name": "a", "last_published_at": iso(NOW - 400 * DAY)}]}})
        s.tick()
        st = s.get_status()
        self.assertEqual((st["repos_checked"], len(st["errors"]), len(s.get_alerts())), (1, 1, 1))
        self.assertEqual(sentinel_base.lifecycle(st), "degraded")

    def test_status_before_and_after_the_first_tick(self):
        s = self.build(op.ReleaseNotesSentinel, {"o/r": {}})
        self.assertEqual(sentinel_base.lifecycle(s.get_status()), "degraded")
        s.tick()
        self.assertEqual(sentinel_base.lifecycle(s.get_status()), "healthy")

    def test_tick_twice_changes_nothing_the_second_time(self):
        s = self.build(op.ReleaseNotesSentinel, {"o/r": {"releases": [{"tag": "v3", "draft": False, "body": ""}]}})
        s.tick()
        first = s.get_alerts()
        s.tick()
        self.assertEqual(s.get_alerts(), first)

    def test_config_is_validated_and_has_a_schema(self):
        s = self.build(op.PackagesSentinel, {}, stale_days=0, max_versions="x", refresh_seconds=120, bogus=1)
        self.assertEqual((s.cfg["stale_days"], s.cfg["max_versions"], s.refresh_seconds), (180, 100, 120))
        self.assertEqual(set(s.get_config_schema()), {"refresh_seconds", "stale_days", "max_versions"})

    def test_alert_shape_is_the_contract_and_goes_through_the_guard(self):
        s = self.build(op.ReleaseNotesSentinel, {"o/r": {"releases": [{"tag": "v3", "draft": False, "body": ""}]}})
        guard = plugins.Guard("releases", s, 3)
        guard.tick()
        alerts = guard.alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(set(alerts[0]), set(sentinel_base.Alert.__annotations__))

    def test_titles_have_eight_languages_and_the_same_placeholders(self):
        for code, entry in op.TITLES.items():
            self.assertEqual(set(entry), set(op.msgs.LANGS), code)
            self.assertEqual(len({tuple(sorted(re.findall(r"\{(\w+)\}", t))) for t in entry.values()}), 1, code)
        s = op.DiscussionsSentinel(FakeCtx({"o/r": {"discussions": [{"number": 1, "is_question": True, "created_at": iso(NOW - 9 * DAY)}]}}), {}, clock=lambda: NOW, lang="pt")
        s.tick()
        self.assertIn("sem resposta", s.get_alerts()[0]["title"])


if __name__ == "__main__":
    unittest.main()
