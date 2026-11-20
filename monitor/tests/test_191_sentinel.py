# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Security sentinel (1.9.1): what it flags and what it does not, that a source it cannot read is never a clean bill of health, that nothing is announced at the first look, the cost, and that it is
registered but off by default."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import toolconfig  # noqa: E402
from github_actions_monitor.data_pipeline import events  # noqa: E402
from github_actions_monitor.sentinels import sentinel_registry, sentinel_security as ss  # noqa: E402

NOW = 1_800_000_000
CFG = ss.settings({})


def dep(severity):
    return {"security_advisory": {"severity": severity}}


def code(severity=None, level=None):
    return {"rule": {"security_severity_level": severity, "severity": level}}


class Settings(unittest.TestCase):
    def test_off_by_default_with_the_documented_defaults(self):
        self.assertFalse(CFG["enabled"])
        self.assertEqual((CFG["refresh_seconds"], CFG["max_repos_per_tick"], CFG["min_rate_remaining"]), (1800, 5, 1500))
        self.assertFalse(CFG["signals"]["codeowners"]["enabled"])
        self.assertEqual(CFG["signals"]["dependabot"]["min_severity"], "high")

    def test_bad_values_keep_the_default_and_good_ones_are_taken(self):
        bad = ss.settings({"sentinels": {"security": {"enabled": "yes", "refresh_seconds": 5, "max_repos_per_tick": 0, "repos": 3, "signals": {"dependabot": {"min_severity": "huge", "enabled": 1}, "x": {}}, "penalty": {"high": -1}}}})
        self.assertEqual(bad, CFG)
        good = ss.settings({"sentinels": {"security": {"enabled": True, "refresh_seconds": 600, "signals": {"dependabot": {"min_severity": "low"}, "codeowners": {"enabled": True}}, "penalty": {"high": 20}}}})
        self.assertTrue(good["enabled"])
        self.assertEqual((good["refresh_seconds"], good["signals"]["dependabot"]["min_severity"], good["signals"]["codeowners"]["enabled"], good["penalty"]["high"]), (600, "low", True, 20))


class Counting(unittest.TestCase):
    def test_severity_of_dependabot_and_code_scanning(self):
        self.assertEqual(ss.severity_of("dependabot", dep("critical")), "critical")
        self.assertEqual(ss.severity_of("dependabot", {"security_vulnerability": {"severity": "low"}}), "low")
        self.assertEqual(ss.severity_of("code_scanning", code("high")), "high")
        self.assertEqual(ss.severity_of("code_scanning", code(None, "error")), "high")
        self.assertEqual(ss.severity_of("code_scanning", code(None, "note")), "low")
        self.assertEqual(ss.severity_of("dependabot", {}), "medium")

    def test_the_least_severity_cuts_the_count(self):
        items = [dep("critical"), dep("high"), dep("medium"), dep("low"), "x", None]
        self.assertEqual(ss.counts("dependabot", items, "high"), {"n": 2, "critical": 1, "high": 1, "medium": 0, "low": 0})
        self.assertEqual(ss.counts("dependabot", items, "low")["n"], 4)


class Rules(unittest.TestCase):
    def test_dependabot_level_follows_the_worst_severity(self):
        for items, level in (([dep("critical")], "critical"), ([dep("high")], "error"), ([dep("medium")], None)):
            found = ss.evaluate("r", {"dependabot": {"items": items}}, CFG, NOW)
            if level is None:
                self.assertEqual(found, {})          # below the least severity (high): nothing
            else:
                self.assertEqual(found["security.dependabot:r"]["level"], level)

    def test_a_lower_least_severity_flags_a_medium(self):
        cfg = ss.settings({"sentinels": {"security": {"signals": {"dependabot": {"min_severity": "medium"}}}}})
        self.assertEqual(ss.evaluate("r", {"dependabot": {"items": [dep("medium")]}}, cfg, NOW)["security.dependabot:r"]["level"], "warning")

    def test_a_secret_is_always_critical(self):
        found = ss.evaluate("r", {"secret": {"items": [{}, {}]}}, CFG, NOW)
        self.assertEqual((found["security.secret:r"]["level"], found["security.secret:r"]["detail"]["n"]), ("critical", 2))

    def test_branch_workflow_and_codeowners(self):
        facts = {"branch_protected": False, "default_branch": "main", "workflow_permissions": "write", "codeowners": False}
        found = ss.evaluate("r", facts, CFG, NOW)
        self.assertEqual(sorted(found), ["security.branch_unprotected:r", "security.workflow_write:r"])      # codeowners is off by default
        on = ss.settings({"sentinels": {"security": {"signals": {"codeowners": {"enabled": True}}}}})
        self.assertIn("security.codeowners_missing:r", ss.evaluate("r", facts, on, NOW))

    def test_not_knowing_is_not_an_alert(self):
        self.assertEqual(ss.evaluate("r", {"branch_protected": None, "workflow_permissions": None, "dependabot": None, "secret": None}, CFG, NOW), {})
        self.assertEqual(ss.evaluate("r", {}, CFG, NOW), {})

    def test_a_signal_switched_off_raises_nothing(self):
        off = ss.settings({"sentinels": {"security": {"signals": {name: {"enabled": False} for name in ss.SIGNALS}}}})
        facts = {"dependabot": {"items": [dep("critical")]}, "secret": {"items": [{}]}, "branch_protected": False, "workflow_permissions": "write"}
        self.assertEqual(ss.evaluate("r", facts, off, NOW), {})

    def test_an_alert_keeps_its_first_time(self):
        first = ss.evaluate("r", {"secret": {"items": [{}]}}, CFG, NOW)
        again = ss.evaluate("r", {"secret": {"items": [{}, {}]}}, CFG, NOW + 999, first)
        self.assertEqual(again["security.secret:r"]["created_at"], first["security.secret:r"]["created_at"])

    def test_the_penalty_weighs_what_is_open(self):
        facts = {"dependabot": {"items": [dep("critical"), dep("high"), dep("high")]}, "secret": {"items": [{}]}, "branch_protected": False, "workflow_permissions": "write"}
        found = ss.evaluate("r", facts, CFG, NOW)
        self.assertEqual(ss.penalty(list(found.values()), CFG), 25 + 2 * 10 + 25 + 5 + 3)
        self.assertEqual(ss.penalty([], CFG), 0)


class Fake:
    """`gh api -i` for the sentinel: {endpoint fragment: (status, body, etag)}; the first fragment contained in the endpoint answers."""

    def __init__(self):
        self.answers, self.calls = {}, []

    def set(self, fragment, status, body=None, etag='"e1"'):
        self.answers[fragment] = (status, body, etag)

    def run_gh(self, args):
        self.calls.append(list(args))
        endpoint = args[-1]
        for fragment, (status, body, tag) in self.answers.items():
            if fragment in endpoint:
                if status == 200 and f"If-None-Match: {tag}" in args:
                    return 0, f"HTTP/2.0 304 Not Modified\r\nEtag: {tag}\r\n\r\n", ""
                text = {200: "OK", 403: "Forbidden", 404: "Not Found"}[status]
                return (0 if status == 200 else 1), f"HTTP/2.0 {status} {text}\r\nEtag: {tag}\r\n\r\n" + json.dumps(body if body is not None else {}), ""
        return 1, "", "HTTP 500"


def build(case, config=None, repos=("r",), rate=None, fake=None):
    fake = fake or Fake()
    folder = Path(tempfile.mkdtemp(prefix="security_test_"))
    saved = (ss.STATE_FILE, events.EVENTS_FILE, events.STATE_FILE)
    ss.STATE_FILE, events.EVENTS_FILE, events.STATE_FILE = folder / "security_state.json", folder / "events.jsonl", folder / "events_state.json"
    case.addCleanup(lambda: (setattr(ss, "STATE_FILE", saved[0]), setattr(events, "EVENTS_FILE", saved[1]), setattr(events, "STATE_FILE", saved[2])))
    old_owner = toolconfig.github_owner()
    toolconfig.set_owner("acme")
    case.addCleanup(lambda: toolconfig.set_owner(old_owner))
    settings = {"sentinels": {"security": {"enabled": True, **(config or {})}}}
    ctx = {"gh": lambda *a, **k: {}, "run_gh": fake.run_gh, "repos_fn": lambda: list(repos), "eco_fn": lambda r: "web" if r.startswith("w") else "other", "data_fn": lambda: {"rate": rate} if rate else None, "account_id": ""}
    sentinel = ss.SentinelSecurity(ctx, settings)
    sentinel.listened = []
    sentinel.feed.listeners.append(sentinel.listened.append)
    return sentinel, fake, folder


def quiet_repo(fake):
    fake.set("/branches/", 200, {"protected": True})
    fake.set("/actions/permissions/workflow", 200, {"default_workflow_permissions": "read"})
    fake.set("dependabot/alerts", 200, [])
    fake.set("code-scanning/alerts", 200, [])
    fake.set("secret-scanning/alerts", 200, [])
    fake.set("repos/acme/r", 200, {"default_branch": "main", "archived": False}, '"repo1"')


class Scanning(unittest.TestCase):
    def test_a_quiet_repository_has_no_alerts_and_is_ok(self):
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        self.assertTrue(sentinel.tick(NOW))
        self.assertEqual(sentinel.get_alerts(), [])
        status = sentinel.get_status()
        self.assertEqual((status["level"], status["repos_checked"], status["unavailable"]), ("ok", 1, {}))

    def test_the_first_look_finds_alerts_but_announces_nothing_and_a_change_does(self):
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        fake.set("dependabot/alerts", 200, [dep("critical")], '"d1"')
        sentinel.tick(NOW)
        self.assertEqual([a["code"] for a in sentinel.get_alerts()], ["security.dependabot"])
        self.assertEqual(sentinel.listened, [])
        fake.set("dependabot/alerts", 200, [], '"d2"')
        fake.set("secret-scanning/alerts", 200, [{}], '"s2"')
        sentinel.tick(NOW + 2000)
        kinds = sorted(e["kind"] for batch in sentinel.listened for e in batch)
        self.assertEqual(kinds, ["security_fixed", "security_new"])
        self.assertEqual([a["code"] for a in sentinel.get_alerts()], ["security.secret"])

    def test_a_source_that_does_not_answer_is_unavailable_not_clean(self):
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        fake.set("dependabot/alerts", 403)
        fake.set("code-scanning/alerts", 404)
        sentinel.tick(NOW)
        status = sentinel.get_status()
        self.assertEqual(status["unavailable"], {"dependabot": 1, "code_scanning": 1})
        self.assertEqual(sentinel.get_alerts(), [])

    def test_an_unprotected_default_branch_is_an_alert_but_a_403_is_not(self):
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        fake.set("/branches/", 404)
        sentinel.tick(NOW)
        self.assertEqual([a["code"] for a in sentinel.get_alerts()], ["security.branch_unprotected"])
        fake.set("/branches/", 403)
        sentinel.tick(NOW + 2000)
        self.assertEqual(sentinel.get_alerts(), [])
        self.assertEqual(sentinel.get_status()["unavailable"], {"branch": 1})

    def test_a_304_keeps_what_was_known_and_the_conditional_header_is_sent(self):
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        fake.set("secret-scanning/alerts", 200, [{}], '"s1"')
        sentinel.tick(NOW)
        fake.calls.clear()
        sentinel.tick(NOW + 2000)
        self.assertEqual([a["code"] for a in sentinel.get_alerts()], ["security.secret"])
        self.assertTrue(any("If-None-Match: \"s1\"" in c for c in fake.calls))

    def test_an_archived_repository_is_not_asked_for_anything_else(self):
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        fake.set("repos/acme/r", 200, {"default_branch": "main", "archived": True}, '"repo1"')
        sentinel.tick(NOW)
        self.assertEqual(len(fake.calls), 1)

    def test_one_repository_that_fails_does_not_stop_the_others(self):
        sentinel, fake, _ = build(self, repos=("bad", "r"))
        quiet_repo(fake)
        fake.answers = {"repos/acme/bad": fake.answers.get("none", (500, None, "")), **fake.answers}
        del fake.answers["repos/acme/bad"]
        sentinel.tick(NOW)
        self.assertEqual(sentinel.get_status()["repos_checked"], 1)
        self.assertEqual([e["section"] for e in sentinel.get_status()["errors"]], ["bad"])

    def test_the_round_is_capped_and_goes_by_age(self):
        sentinel, fake, _ = build(self, {"max_repos_per_tick": 1}, repos=("r1", "r2", "r3"))
        for name in ("r1", "r2", "r3"):
            fake.set(f"repos/acme/{name}", 200, {"default_branch": "main", "archived": True})
        sentinel.tick(NOW)
        sentinel.tick(NOW + 1)
        sentinel.tick(NOW + 2)
        self.assertEqual(sentinel.get_status()["repos_checked"], 3)

    def test_the_round_pauses_while_the_allowance_is_low(self):
        sentinel, fake, _ = build(self, rate={"remaining": 10})
        quiet_repo(fake)
        self.assertFalse(sentinel.tick(NOW))
        self.assertEqual(fake.calls, [])
        self.assertTrue(sentinel.get_status()["paused"])

    def test_off_it_reads_nothing_and_says_so(self):
        sentinel, fake, _ = build(self, {"enabled": False})
        self.assertFalse(sentinel.tick(NOW))
        self.assertEqual((fake.calls, sentinel.get_alerts(), sentinel.get_status()["level"], sentinel.get_metrics()), ([], [], "off", {}))

    def test_nothing_checked_yet_is_unknown_never_ok(self):
        sentinel, _, _ = build(self)
        self.assertEqual(sentinel.get_status()["level"], "unknown")

    def test_the_metrics_carry_the_penalty_and_the_state_survives_a_restart(self):
        sentinel, fake, folder = build(self)
        quiet_repo(fake)
        fake.set("secret-scanning/alerts", 200, [{}], '"s1"')
        sentinel.tick(NOW)
        metrics = sentinel.get_metrics()
        self.assertEqual((metrics["security_alerts"], metrics["security_critical"], metrics["security_penalty"], metrics["security_repos_checked"]), (1, 1, 25, 1))
        again = ss.SentinelSecurity(sentinel.ctx, {"sentinels": {"security": {"enabled": True}}})
        self.assertEqual([a["code"] for a in again.get_alerts()], ["security.secret"])
        self.assertTrue((folder / "security_state.json").is_file())

    def test_a_damaged_state_file_is_read_as_empty(self):
        folder = Path(tempfile.mkdtemp(prefix="security_state_"))
        path = folder / "security_state.json"
        for text in ("not json", "[]", json.dumps({"alerts": {"x": {"repo": 3}}, "per_repo": []}), json.dumps({"alerts": {"k": {"repo": "r", "code": "nope"}}, "per_repo": {}})):
            path.write_text(text, encoding="utf-8")
            self.assertEqual(ss.load_state(path)["alerts"], {}, text)


class Contract(unittest.TestCase):
    def test_it_is_registered_off_by_default_and_the_others_are_unchanged(self):
        registry = sentinel_registry.SentinelRegistry.build({"gh": lambda *a, **k: {}, "repos_fn": lambda: [], "eco_fn": lambda r: "x"}, {})
        self.assertEqual(registry.names(), ["ci", "collab", "delivery", "security", "supply"])
        self.assertFalse(registry.get("security").enabled)
        self.assertFalse(sentinel_registry.is_enabled({}, "security"))
        self.assertTrue(sentinel_registry.is_enabled({"sentinels": {"security": {"enabled": True}}}, "security"))

    def test_every_title_and_event_text_exists_in_the_eight_languages(self):
        alert = {"repo": "r", "detail": {"n": 3, "critical": 1, "high": 2, "branch": "main"}}
        for lang in i18n.LANGS:
            for code, key in ss.TITLE_KEYS.items():
                text = i18n.tl(lang, key)
                self.assertNotEqual(text, key, (lang, key))
                filled = text.format(repo="r", n=3, critical=1, high=2, branch="main", workflow="CI", actor="ana")
                self.assertIn("r", filled)
            for key in ("evt.security_new", "evt.security_fixed"):
                self.assertNotEqual(i18n.tl(lang, key), key, (lang, key))
                self.assertIn("X", i18n.tl(lang, key).format(title="X"))
        self.assertTrue(alert)

    def test_the_alerts_have_the_shape_of_the_panel_and_a_stable_id(self):
        sentinel, fake, _ = build(self)
        quiet_repo(fake)
        fake.set("secret-scanning/alerts", 200, [{}])
        sentinel.tick(NOW)
        alert = sentinel.get_alerts()[0]
        for key in ("id", "code", "level", "sentinel", "account_id", "repo", "title", "details", "created_at"):
            self.assertIn(key, alert)
        self.assertEqual((alert["id"], alert["sentinel"], alert["details"]["signal"]), ("security.secret:r", "security", "secret"))
        self.assertIn("r", alert["title"])

    def test_the_schema_lists_every_setting(self):
        sentinel, _, _ = build(self)
        keys = sentinel.get_config_schema()["keys"]
        for name in ("enabled", "refresh_seconds", "max_repos_per_tick", "min_rate_remaining", "signals.dependabot.min_severity", "signals.codeowners.enabled"):
            self.assertIn(name, keys)


class Lifecycle(unittest.TestCase):
    def test_the_five_states_from_a_status(self):
        life = ss.sentinel_base.lifecycle
        self.assertEqual(life({"enabled": False, "level": "off"}), "off")
        self.assertEqual(life({"enabled": True, "level": "ok", "paused": True}), "paused")
        self.assertEqual(life({"enabled": True, "level": "unknown", "errors": [{"section": "r"}], "repos_checked": 0}), "error")
        self.assertEqual(life({"enabled": True, "level": "ok", "errors": [{"section": "r"}], "repos_checked": 2}), "degraded")
        self.assertEqual(life({"enabled": True, "level": "ok", "unavailable": {"dependabot": 1}, "repos_checked": 2}), "degraded")
        self.assertEqual(life({"enabled": True, "level": "unknown", "loading": "starting"}), "degraded")
        self.assertEqual(life({"enabled": True, "level": "ok", "repos_checked": 2, "errors": [], "unavailable": {}}), "healthy")
        self.assertEqual(life(None), "off")

    def test_no_alerts_is_not_the_same_as_could_not_look(self):
        sentinel, fake, _ = build(self)
        self.assertEqual(sentinel.get_status()["lifecycle"], "degraded")       # nothing read yet: no alerts, but not healthy
        quiet_repo(fake)
        sentinel.tick(NOW)
        self.assertEqual(sentinel.get_status()["lifecycle"], "healthy")
        fake.set("dependabot/alerts", 403)
        sentinel.tick(NOW + 2000)
        self.assertEqual(sentinel.get_status()["lifecycle"], "degraded")

    def test_a_failing_first_round_is_an_error_and_the_others_have_it_too(self):
        sentinel, _, _ = build(self)           # nothing answers: every call fails
        sentinel.tick(NOW)
        self.assertEqual(sentinel.get_status()["lifecycle"], "error")
        off, _, _ = build(self, {"enabled": False})
        self.assertEqual(off.get_status()["lifecycle"], "off")
        from github_actions_monitor.sentinels import sentinel_collab
        self.assertTrue(hasattr(sentinel_collab.SentinelCollab, "_status"))
        registry = sentinel_registry.SentinelRegistry.build({"gh": lambda *a, **k: {}, "repos_fn": lambda: [], "eco_fn": lambda r: "x"}, {})
        self.assertEqual(registry.get("collab").get_status()["lifecycle"], "off")


class Agreement(unittest.TestCase):
    def test_the_example_file_holds_the_defaults_of_the_sentinel(self):
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["sentinels"]["security"], {k: v for k, v in ss.DEFAULTS.items()})

    def test_the_page_has_every_setting_that_is_not_a_weight(self):
        from github_actions_monitor.app import settings_api
        keys = {k for k in settings_api.FIELDS if k.startswith("sentinels.security.")}
        expected = {"sentinels.security." + k for k in ("enabled", "refresh_seconds", "max_repos_per_tick", "deadline_s", "min_rate_remaining", "repos", "plan_na")}
        expected |= {f"sentinels.security.signals.{s}.enabled" for s in ss.SIGNALS} | {"sentinels.security.signals.dependabot.min_severity", "sentinels.security.signals.code_scanning.min_severity", "sentinels.security.signals.runs_deleted.check_window_days", "sentinels.security.signals.runs_deleted.max_checks"}
        self.assertEqual(keys, expected)

    def test_every_default_is_inside_what_the_page_accepts(self):
        from github_actions_monitor.app import settings_api
        for key in (k for k in settings_api.FIELDS if k.startswith("sentinels.security.") and k != "sentinels.security.repos"):
            value = ss.DEFAULTS
            for part in key[len("sentinels.security."):].split("."):
                value = value[part]
            ok, clean = settings_api.check_value(key, value)
            self.assertTrue(ok, (key, clean))

    def test_the_guide_exists_in_the_eight_languages_and_names_every_setting(self):
        from github_actions_monitor.app import settings_api
        for suffix in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho"):
            text = (HERE / "docs" / f"SENTINEL_SECURITY{suffix}.md").read_text(encoding="utf-8")
            for key in (k for k in settings_api.FIELDS if k.startswith("sentinels.security.")):
                self.assertIn(f"`{key}`", text, (suffix, key))
            for code in ss.TITLE_KEYS:
                self.assertIn(f"`{code}`", text, (suffix, code))

    def test_the_new_events_are_known_to_the_notifications(self):
        from github_actions_monitor.integrations import dispatcher, notifiers
        for kind in ("security_new", "security_fixed"):
            self.assertIn(kind, notifiers.KNOWN_EVENTS)
            self.assertEqual(dispatcher.family_of(kind), "ci")
            self.assertEqual(dispatcher.sentinel_of(kind), "security")
        self.assertIn("security", dispatcher.SENTINELS)


if __name__ == "__main__":
    unittest.main()
