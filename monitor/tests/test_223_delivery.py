# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Delivery sentinel (2.1.1): the six signals of tags, releases, CHANGELOG and version files, a repository that cannot be read is never a clean bill of health, nothing is announced at the first
look or after a restart, the cost is bounded, and it is registered but off by default."""
import base64
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import settings_api, toolconfig  # noqa: E402
from github_actions_monitor.cli import release_candidates  # noqa: E402
from github_actions_monitor.data_pipeline import events  # noqa: E402
from github_actions_monitor.delivery import reader, rules  # noqa: E402
from github_actions_monitor.sentinels import alert_center, sentinel_delivery as sd, sentinel_registry  # noqa: E402

NOW = 1_800_000_000
DAY = 86400


def when(days_ago):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(NOW - days_ago * DAY, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def release(tag, days_ago=30, body="notes", assets=(), draft=False, prerelease=False):
    return {"tag_name": tag, "published_at": when(days_ago), "body": body, "draft": draft, "prerelease": prerelease, "assets": [{"name": n} for n in assets]}


def changelog(entries, version="1.2.0"):
    return "# Changes\n\n## [Unreleased]\n\n" + "".join(f"- entry {i}\n" for i in range(entries)) + f"\n## [{version}]\n\n- old\n"


CFG = sd.settings({})
CFG["expected_assets"] = []


def findings(facts, **over):
    cfg = {**CFG, **over}
    return rules.repo_findings({"releases": None, "tags": None, "changelog": None, "versions": {}, **facts}, cfg, NOW)


class Fake:
    """`gh api` for the sentinel: {repo: {"releases": [...], "tags": [...], "files": {path: text}}}; a repository set to a string fails like `gh` does."""

    def __init__(self):
        self.repos, self.calls, self.pins = {}, [], {}

    def gh(self, *args, **kwargs):
        endpoint = args[-1]
        self.calls.append(endpoint)
        parts = endpoint.split("?")[0].split("/")      # repos/acme/<repo>/(releases|tags|contents/<path>)
        repo = parts[2]
        answer = self.repos.get(repo)
        if isinstance(answer, str):
            raise RuntimeError(answer)
        if answer is None:
            raise RuntimeError("HTTP 404: Not Found")
        if parts[3] == "releases" and len(parts) > 4 and parts[4] == "latest":
            if not answer.get("releases"):
                raise RuntimeError("HTTP 404: Not Found")
            return answer["releases"][0]
        if parts[3] == "releases":
            return answer.get("releases", [])
        if parts[3] == "tags":
            return [{"name": t} for t in answer.get("tags", [])]
        path = "/".join(parts[4:])
        if path not in answer.get("files", {}):
            raise RuntimeError("HTTP 404: Not Found")
        return {"encoding": "base64", "content": base64.b64encode(answer["files"][path].encode()).decode()}


def build(case, config=None, repos=("r",), rate=None, fake=None, readiness=None):
    fake = fake or Fake()
    folder = Path(tempfile.mkdtemp(prefix="delivery_test_"))
    saved = (sd.STATE_FILE, events.EVENTS_FILE, events.STATE_FILE)
    sd.STATE_FILE, events.EVENTS_FILE, events.STATE_FILE = folder / "delivery_state.json", folder / "events.jsonl", folder / "events_state.json"
    case.addCleanup(lambda: (setattr(sd, "STATE_FILE", saved[0]), setattr(events, "EVENTS_FILE", saved[1]), setattr(events, "STATE_FILE", saved[2])))
    old_owner = toolconfig.github_owner()
    toolconfig.set_owner("acme")
    case.addCleanup(lambda: toolconfig.set_owner(old_owner))
    settings = {"sentinels": {"delivery": {"enabled": True, **(config or {})}}}
    if readiness:
        settings["sentinel"] = {"readiness": readiness}
    ctx = {"gh": fake.gh, "repos_fn": lambda: list(repos), "eco_fn": lambda r: "web" if r.startswith("w") else "other", "data_fn": lambda: {"rate": rate} if rate else None, "account_id": ""}
    sentinel = sd.SentinelDelivery(ctx, settings)
    sentinel.listened = []
    sentinel.feed.listeners.append(sentinel.listened.append)
    return sentinel, fake, folder


def codes(sentinel):
    return sorted(a["code"] for a in sentinel.get_alerts())


class Settings(unittest.TestCase):
    def test_off_by_default_with_the_documented_defaults(self):
        cfg = sd.settings({})
        self.assertFalse(cfg["enabled"])
        self.assertEqual((cfg["refresh_seconds"], cfg["max_repos_per_tick"], cfg["max_calls_per_tick"], cfg["min_rate_remaining"]), (3600, 10, 60, 1000))
        self.assertEqual((cfg["unreleased_days"], cfg["unreleased_min_entries"], cfg["changelog_paths"], cfg["version_files"], cfg["expected_assets"]), (14, 1, ["CHANGELOG.md"], [], []))
        self.assertEqual({n: cfg["signals"][n]["level"] for n in rules.SIGNALS}, {"unreleased_pending": "info", "tag_without_release": "warning", "release_without_notes": "info",
                                                                                  "version_mismatch": "warning", "ecosystem_drift": "warning", "assets_missing": "warning"})

    def test_bad_values_keep_the_default_and_good_ones_are_taken(self):
        base = sd.settings({})
        bad = sd.settings({"sentinels": {"delivery": {"enabled": "yes", "refresh_seconds": 5, "unreleased_days": 0, "repos": 3, "version_files": ["../x", "/etc/passwd", 4], "expected_assets": ["a;b"],
                                                      "signals": {"tag_without_release": {"level": "huge", "enabled": 1}, "x": {}}}}})
        self.assertEqual(bad, base)
        good = sd.settings({"sentinels": {"delivery": {"enabled": True, "unreleased_days": 30, "version_files": ["package.json", "src/v.py"], "expected_assets": ["*.zip"], "changelog_paths": [],
                                                       "signals": {"tag_without_release": {"level": "error"}, "assets_missing": {"enabled": False}}}}})
        self.assertEqual((good["enabled"], good["unreleased_days"], good["version_files"], good["expected_assets"], good["changelog_paths"]), (True, 30, ["package.json", "src/v.py"], ["*.zip"], ["CHANGELOG.md"]))
        self.assertEqual((good["signals"]["tag_without_release"]["level"], good["signals"]["assets_missing"]["enabled"]), ("error", False))

    def test_the_settings_page_knows_every_key_and_refuses_a_path_outside_the_repository(self):
        keys = {row[2] for row in settings_api.ROWS}
        for name in rules.SIGNALS:
            self.assertIn(f"sentinels.delivery.signals.{name}.enabled", keys)
            self.assertIn(f"sentinels.delivery.signals.{name}.level", keys)
        for key in ("enabled", "refresh_seconds", "max_repos_per_tick", "max_calls_per_tick", "min_rate_remaining", "repos", "unreleased_days", "unreleased_min_entries", "changelog_paths", "version_files", "expected_assets"):
            self.assertIn("sentinels.delivery." + key, keys)
        self.assertEqual(settings_api.check_value("sentinels.delivery.version_files", ["sub/package.json"]), (True, ["sub/package.json"]))
        for bad in (["../x"], ["/abs"], ["a b"]):
            self.assertFalse(settings_api.check_value("sentinels.delivery.version_files", bad)[0])
        self.assertTrue(settings_api.check_value("sentinels.delivery.expected_assets", ["*.zip", "SHA256SUMS*"])[0])


class Rules(unittest.TestCase):
    def test_the_count_of_unreleased_entries_is_the_one_of_the_release_candidates_tool(self):
        for text in (changelog(0), changelog(3), "## [Unreleased]\r\n- a\r\n* b\r\n## [1.0.0]\r\n- c\r\n", "no heading\n- a\n", ""):
            self.assertEqual(rules.unreleased_count(text), release_candidates.unreleased_count(text))

    def test_unreleased_pending_needs_entries_and_an_old_release(self):
        old = [release("v1.2.0", 30)]
        self.assertEqual(list(findings({"releases": old, "changelog": changelog(3)})), ["unreleased_pending"])
        self.assertEqual(findings({"releases": old, "changelog": changelog(3)})["unreleased_pending"], {"entries": 3, "days": 30, "tag": "v1.2.0"})
        self.assertEqual(findings({"releases": [release("v1.2.0", 3)], "changelog": changelog(3)}), {})      # released a few days ago: nothing waits too long
        self.assertEqual(findings({"releases": old, "changelog": changelog(0)}), {})
        self.assertEqual(findings({"releases": old, "changelog": changelog(2)}, unreleased_min_entries=3), {})
        self.assertEqual(findings({"releases": [], "changelog": changelog(5)}), {})      # a repository with no release does not use releases
        self.assertEqual(findings({"releases": old, "changelog": None}), {})      # a CHANGELOG that was not read says nothing
        self.assertEqual(findings({"releases": [release("v1.3.0", 40, draft=True), release("v1.2.0", 2)], "changelog": changelog(3)}), {})      # a draft is not a release

    def test_tag_without_release_only_counts_version_tags_newer_than_the_latest_release(self):
        facts = {"releases": [release("v1.2.0", 1)], "tags": ["v1.3.0", "v1.2.1", "v1.2.0", "v0.9.0", "latest", "nightly-2"]}
        self.assertEqual(findings(facts)["tag_without_release"], {"n": 2, "tags": ["v1.3.0", "v1.2.1"]})
        self.assertEqual(findings({"releases": [release("v1.2.0", 1)], "tags": ["v1.2.0", "v1.0.0"]}), {})
        self.assertEqual(findings({"releases": [release("v1.2.0", 1)], "tags": None}), {})
        self.assertEqual(findings({"releases": [], "tags": ["v1.0.0"]}), {})
        self.assertIn("tag_without_release", findings({"releases": [release("v1.2.0", 1), release("v1.3.0", 0, draft=True)], "tags": ["v1.3.0"]}))      # only a draft: not delivered yet

    def test_release_without_notes_looks_at_the_latest_published_release_only(self):
        self.assertEqual(findings({"releases": [release("v2", 1, body="  \n"), release("v1", 9)]})["release_without_notes"], {"tag": "v2"})
        self.assertEqual(findings({"releases": [release("v2", 1), release("v1", 9, body="")]}), {})
        self.assertEqual(findings({"releases": [release("v2", 1, body=None)]}).get("release_without_notes"), {"tag": "v2"})

    def test_assets_missing_matches_the_patterns_without_caring_for_case(self):
        facts = {"releases": [release("v1", 1, assets=("tool-1.zip", "SHA256SUMS"))]}
        self.assertEqual(findings(facts, expected_assets=["*.zip", "sha256sums*"]), {})
        self.assertEqual(findings(facts, expected_assets=["*.zip", "*.sig", "*.sbom"])["assets_missing"], {"tag": "v1", "n": 2, "missing": ["*.sig", "*.sbom"]})
        self.assertEqual(findings(facts, expected_assets=[]), {})
        self.assertEqual(findings({"releases": [release("v1", 1, assets=())]}, expected_assets=["*.zip"])["assets_missing"]["n"], 1)

    def test_version_mismatch_compares_the_files_and_the_changelog(self):
        facts = {"changelog": changelog(0, "1.2.0"), "versions": {"package.json": json.dumps({"version": "1.2.0"}), "pyproject.toml": 'version = "1.2"\n'}}
        self.assertEqual(findings(facts), {})      # 1.2 and 1.2.0 are the same version
        facts["versions"]["src/v.py"] = '__version__ = "1.3.0"\n'
        self.assertEqual(findings(facts)["version_mismatch"], {"n": 2, "versions": {"CHANGELOG": "1.2.0", "package.json": "1.2.0", "pyproject.toml": "1.2", "src/v.py": "1.3.0"}})
        self.assertEqual(findings({"changelog": changelog(0, "1.2.0"), "versions": {}}), {})      # one place alone cannot disagree
        self.assertEqual(findings({"changelog": None, "versions": {"a.json": json.dumps({"version": "2.0.0"}), "b.txt": "version: 2.0.0"}}), {})
        self.assertEqual(findings({"changelog": None, "versions": {"a.json": "not json", "b.txt": "nothing here"}}), {})

    def test_version_helpers(self):
        self.assertEqual(rules.version_key("v0.8.0.7"), (0, 8, 0, 7))
        self.assertEqual(rules.version_key("1.2.0"), rules.version_key("1.2"))
        self.assertTrue(rules.older("1.9", "1.10"))
        self.assertFalse(rules.older("x", "1.0"))
        self.assertEqual(rules.file_version("p.toml", '[tool]\nname = "x"\nversion = "3.4.5"\n'), "3.4.5")
        self.assertEqual(rules.file_version("p.json", '{"version": "3.4"}'), "3.4")
        self.assertEqual(rules.file_version("p.json", '{"version": 3}'), "")

    def test_drift_rows_and_alerts(self):
        source = {"provider": "contract", "file": "pins.json", "key": "consumers"}
        rows = rules.drift_rows(source, "v1.4.0", {"a": "v1.3.0", "b": "v1.4.0", "c": "1.4", "gone": "v0.1", "d": 7}, {"a", "b", "c", "d"})
        self.assertEqual([r["repo"] for r in rows], ["a"])
        alerts = rules.drift_alerts(rows, {"enabled": True, "level": "error"}, stamp="t")
        self.assertEqual(alerts["release.ecosystem_drift:a"]["level"], "error")
        self.assertEqual(alerts["release.ecosystem_drift:a"]["detail"]["behind"], ["contract v1.3.0 -> v1.4.0"])
        self.assertEqual(rules.drift_alerts(rows, {"enabled": False}), {})

    def test_one_alert_per_repository_and_signal_with_the_level_of_the_setting_and_the_first_time_kept(self):
        found = {"tag_without_release": {"n": 1, "tags": ["v2"]}, "release_without_notes": {"tag": "v1"}}
        signals = sd.settings({"sentinels": {"delivery": {"signals": {"tag_without_release": {"level": "error"}, "release_without_notes": {"enabled": False}}}}})["signals"]
        first = rules.evaluate("r", found, signals, stamp="t1")
        self.assertEqual(sorted(first), ["release.tag_without_release:r"])
        self.assertEqual(first["release.tag_without_release:r"]["level"], "error")
        again = rules.evaluate("r", found, signals, first, stamp="t2")
        self.assertEqual(again["release.tag_without_release:r"]["created_at"], "t1")


class Scanning(unittest.TestCase):
    def test_a_release_ready_repository_is_ok_and_one_without_releases_has_nothing_to_report(self):
        sentinel, fake, _ = build(self, repos=("r", "s"))
        fake.repos["r"] = {"releases": [release("v1.2.0", 2)], "tags": ["v1.2.0"], "files": {"CHANGELOG.md": changelog(4)}}
        fake.repos["s"] = {"releases": [], "tags": ["v0.1"], "files": {}}
        sentinel.tick(NOW)
        status = sentinel.get_status()
        self.assertEqual((status["level"], status["repos_checked"], status["unavailable"], status["lifecycle"]), ("ok", 2, {}, "healthy"))
        self.assertEqual(sentinel.get_alerts(), [])

    def test_the_first_look_finds_alerts_but_announces_nothing_and_a_change_does(self):
        sentinel, fake, _ = build(self)
        fake.repos["r"] = {"releases": [release("v1.2.0", 40, body="")], "tags": ["v1.3.0", "v1.2.0"], "files": {"CHANGELOG.md": changelog(3)}}
        sentinel.tick(NOW)
        self.assertEqual(codes(sentinel), ["release.release_without_notes", "release.tag_without_release", "release.unreleased_pending"])
        self.assertEqual(sentinel.listened, [])
        fake.repos["r"] = {"releases": [release("v1.3.0", 0, body="x"), release("v1.2.0", 40, body="")], "tags": ["v1.3.0", "v1.2.0"], "files": {"CHANGELOG.md": changelog(0)}}
        sentinel.tick(NOW + 4000)
        seen = sorted((e["kind"], e["code"]) for batch in sentinel.listened for e in batch)
        self.assertEqual(seen, [("delivery_fixed", "release.release_without_notes"), ("delivery_fixed", "release.tag_without_release"), ("delivery_fixed", "release.unreleased_pending")])
        self.assertTrue(all(e["sentinel"] == "delivery" and e["level"] == "ok" for batch in sentinel.listened for e in batch))
        self.assertEqual(sentinel.get_alerts(), [])

    def test_a_restart_announces_nothing_again_and_an_alert_keeps_the_time_it_was_first_seen(self):
        sentinel, fake, _ = build(self)
        fake.repos["r"] = {"releases": [release("v1", 5, body="")], "tags": [], "files": {}}
        sentinel.tick(NOW)
        first = {a["id"]: a["created_at"] for a in sentinel.get_alerts()}
        again = sd.SentinelDelivery(sentinel.ctx, {"sentinels": {"delivery": {"enabled": True}}})
        again.listened = []
        again.feed.listeners.append(again.listened.append)
        self.assertEqual({a["id"]: a["created_at"] for a in again.get_alerts()}, first)
        again.tick(NOW + 4000)
        self.assertEqual(again.listened, [])
        self.assertEqual({a["id"]: a["created_at"] for a in again.get_alerts()}, first)

    def test_a_switched_off_signal_is_not_read_and_costs_nothing(self):
        off = {n: {"enabled": False} for n in rules.SIGNALS}
        off["release_without_notes"] = {"enabled": True}
        sentinel, fake, _ = build(self, config={"signals": off})
        fake.repos["r"] = {"releases": [release("v1", 5, body="")], "tags": ["v2"], "files": {"CHANGELOG.md": changelog(9)}}
        sentinel.tick(NOW)
        self.assertEqual(codes(sentinel), ["release.release_without_notes"])
        self.assertEqual(fake.calls, ["repos/acme/r/releases?per_page=10"])      # no tags, no CHANGELOG
        none, fake2, _ = build(self, config={"signals": {n: {"enabled": False} for n in rules.SIGNALS}})
        none.tick(NOW)
        self.assertEqual(fake2.calls, [])

    def test_the_changelog_is_looked_for_in_each_path_until_one_exists(self):
        sentinel, fake, _ = build(self, config={"changelog_paths": ["CHANGELOG.md", "docs/CHANGELOG.md"]})
        fake.repos["r"] = {"releases": [release("v1", 40)], "tags": [], "files": {"docs/CHANGELOG.md": changelog(2)}}
        sentinel.tick(NOW)
        self.assertEqual(codes(sentinel), ["release.unreleased_pending"])
        self.assertIn("repos/acme/r/contents/CHANGELOG.md", fake.calls)
        self.assertIn("repos/acme/r/contents/docs/CHANGELOG.md", fake.calls)

    def test_version_files_are_read_and_a_missing_one_is_simply_absent(self):
        sentinel, fake, _ = build(self, config={"version_files": ["package.json", "VERSION.txt"]})
        fake.repos["r"] = {"releases": [], "tags": [], "files": {"CHANGELOG.md": changelog(0, "1.0.0"), "package.json": json.dumps({"version": "1.1.0"})}}
        sentinel.tick(NOW)
        self.assertEqual(codes(sentinel), ["release.version_mismatch"])
        self.assertEqual(sentinel.get_alerts()[0]["details"]["versions"], {"CHANGELOG": "1.0.0", "package.json": "1.1.0"})

    def test_a_repository_that_cannot_be_read_is_not_an_alert_and_not_a_clean_bill_of_health(self):
        sentinel, fake, _ = build(self, repos=("r", "s"))
        fake.repos["r"] = "HTTP 403: Resource protected by organization SAML enforcement"
        fake.repos["s"] = "HTTP 403: Resource protected by organization SAML enforcement"
        sentinel.tick(NOW)
        status = sentinel.get_status()
        self.assertEqual(sentinel.get_alerts(), [])
        self.assertEqual(status["unavailable"], {"sso": 2})
        self.assertNotEqual(status["level"], "ok")
        self.assertEqual(status["lifecycle"], "degraded")

    def test_an_alert_whose_repository_stops_answering_is_kept_and_not_closed_as_fixed(self):
        sentinel, fake, _ = build(self)
        fake.repos["r"] = {"releases": [release("v1", 5, body="")], "tags": [], "files": {}}
        sentinel.tick(NOW)
        fake.repos["r"] = "HTTP 403: Resource not accessible"
        sentinel.tick(NOW + 4000)
        self.assertEqual(codes(sentinel), ["release.release_without_notes"])
        self.assertIn("unread_since", sentinel.get_alerts()[0]["details"])
        self.assertEqual([e for batch in sentinel.listened for e in batch if e["kind"] == "delivery_fixed"], [])
        sentinel.tick(NOW + 4000 + sd.UNREAD_KEEP + 10)      # a week without a reading: dropped without an event
        self.assertEqual(sentinel.get_alerts(), [])
        self.assertEqual(sentinel.listened, [])

    def test_a_round_that_runs_out_of_calls_in_the_middle_keeps_what_was_known(self):
        sentinel, fake, _ = build(self, config={"max_calls_per_tick": 3})      # releases + tags + changelog need three; a version file would be the fourth
        fake.repos["r"] = {"releases": [release("v1", 5, body="")], "tags": [], "files": {"CHANGELOG.md": changelog(0)}}
        sentinel.tick(NOW)
        self.assertEqual(len(sentinel.get_alerts()), 1)
        sentinel.cfg["version_files"] = ["package.json"]
        sentinel.tick(NOW + 4000)
        self.assertEqual(sentinel.get_status()["unavailable"], {"budget": 1})
        self.assertEqual(len(sentinel.get_alerts()), 1)      # still there, marked unread, not closed as fixed

    def test_the_cost_of_a_round_is_bounded_by_the_repositories_and_the_calls(self):
        repos = tuple(f"r{i}" for i in range(8))
        sentinel, fake, _ = build(self, config={"max_repos_per_tick": 3}, repos=repos)
        for r in repos:
            fake.repos[r] = {"releases": [release("v1", 1)], "tags": ["v1"], "files": {"CHANGELOG.md": changelog(0)}}
        sentinel.tick(NOW)
        self.assertEqual(sentinel.get_status()["repos_checked"], 3)
        self.assertEqual(len(fake.calls), 3 * 3)      # releases, tags and the CHANGELOG, for each of the three
        sentinel.tick(NOW + 4000)
        self.assertEqual(sentinel.get_status()["repos_checked"], 6)      # the ones read longest ago come first
        sentinel2, fake2, _ = build(self, config={"max_calls_per_tick": 5}, repos=repos)
        for r in repos:
            fake2.repos[r] = {"releases": [release("v1", 1)], "tags": ["v1"], "files": {"CHANGELOG.md": changelog(0)}}
        sentinel2.tick(NOW)
        self.assertLessEqual(len(fake2.calls), 5)

    def test_it_pauses_below_the_allowance_and_off_it_reads_nothing(self):
        sentinel, fake, _ = build(self, rate={"remaining": 10})
        fake.repos["r"] = {"releases": [release("v1", 1, body="")], "tags": [], "files": {}}
        self.assertFalse(sentinel.tick(NOW))
        self.assertEqual(fake.calls, [])
        self.assertEqual(sentinel.get_status()["lifecycle"], "paused")
        off = sd.SentinelDelivery({"gh": fake.gh, "repos_fn": lambda: ["r"], "eco_fn": lambda r: "x"}, {})
        self.assertFalse(off.tick(NOW))
        self.assertEqual((off.get_alerts(), off.get_metrics(), off.get_status()["lifecycle"]), ([], {}, "off"))

    def test_a_failing_repository_waits_for_its_retry_and_does_not_starve_the_rest(self):
        class Boom(Fake):
            def gh(self, *a, **k):
                if "/bad/" in a[-1]:
                    raise ValueError("boom")
                return super().gh(*a, **k)
        sentinel, fake, _ = build(self, repos=("bad", "ok"), fake=Boom())
        fake.repos["ok"] = {"releases": [release("v1", 1, body="")], "tags": [], "files": {}}
        fake.repos["bad"] = {"releases": [release("v1", 1, body="")], "tags": [], "files": {}}
        sentinel.tick(NOW)
        self.assertEqual({a["repo"] for a in sentinel.get_alerts()}, {"ok"})
        self.assertEqual(sentinel.get_status()["unavailable"], {"error": 1})

    def test_the_pin_tables_of_the_readiness_settings_raise_the_drift_signal_once_per_cycle(self):
        pins = {"sources": [{"ecosystem": "web", "kind": "pin_table", "provider": "contract", "file": "pins.json", "key": "consumers"}, {"ecosystem": "x", "kind": "lock_files", "provider": "lib", "lock_name": "a", "version_key": "v"}]}
        sentinel, fake, _ = build(self, repos=("web1", "web2"), readiness={"pins": pins})
        for r in ("web1", "web2"):
            fake.repos[r] = {"releases": [], "tags": [], "files": {"CHANGELOG.md": changelog(0)}}
        fake.repos["contract"] = {"releases": [release("v2.0.0", 3)], "files": {"pins.json": json.dumps({"consumers": {"web1": "v1.0.0", "web2": "v2.0.0", "other": "v0.1"}})}}
        sentinel.tick(NOW)
        self.assertEqual([(a["repo"], a["code"]) for a in sentinel.get_alerts()], [("web1", "release.ecosystem_drift")])
        self.assertEqual(sentinel.listened, [])      # the first look announces nothing
        calls = len(fake.calls)
        sentinel.tick(NOW + 100)
        self.assertEqual([c for c in fake.calls[calls:] if "/contract/" in c], [])      # once per cycle
        fake.repos["contract"]["files"]["pins.json"] = json.dumps({"consumers": {"web1": "v2.0.0", "web2": "v1.0.0"}})
        sentinel.tick(NOW + 4000)
        self.assertEqual([(a["repo"], a["code"]) for a in sentinel.get_alerts()], [("web2", "release.ecosystem_drift")])
        self.assertEqual(sorted((e["kind"], e["repo"]) for b in sentinel.listened for e in b), [("delivery_fixed", "web1"), ("delivery_new", "web2")])

    def test_a_pin_table_that_cannot_be_read_keeps_its_alerts_and_is_listed(self):
        pins = {"sources": [{"ecosystem": "web", "kind": "pin_table", "provider": "contract", "file": "pins.json", "key": "consumers"}]}
        sentinel, fake, _ = build(self, repos=("web1",), readiness={"pins": pins})
        fake.repos["web1"] = {"releases": [], "tags": [], "files": {"CHANGELOG.md": changelog(0)}}
        fake.repos["contract"] = {"releases": [release("v2.0.0", 3)], "files": {"pins.json": json.dumps({"consumers": {"web1": "v1.0.0"}})}}
        sentinel.tick(NOW)
        fake.repos["contract"] = "HTTP 403: Resource protected by organization SAML enforcement"
        sentinel.tick(NOW + 4000)
        self.assertEqual(codes(sentinel), ["release.ecosystem_drift"])
        self.assertEqual(sentinel.get_status()["unavailable"], {"sso": 1})
        self.assertEqual(sentinel.listened, [])

    def test_switching_the_drift_signal_off_drops_its_alerts_without_an_event(self):
        pins = {"sources": [{"ecosystem": "web", "kind": "pin_table", "provider": "contract", "file": "pins.json", "key": "consumers"}]}
        sentinel, fake, _ = build(self, repos=("web1",), readiness={"pins": pins})
        fake.repos["web1"] = {"releases": [], "tags": [], "files": {"CHANGELOG.md": changelog(0)}}
        fake.repos["contract"] = {"releases": [release("v2.0.0", 3)], "files": {"pins.json": json.dumps({"consumers": {"web1": "v1.0.0"}})}}
        sentinel.tick(NOW)
        sentinel.cfg["signals"]["ecosystem_drift"]["enabled"] = False
        sentinel.tick(NOW + 4000)
        self.assertEqual(sentinel.get_alerts(), [])
        self.assertEqual(sentinel.listened, [])

    def test_the_metrics_and_the_snapshot(self):
        sentinel, fake, _ = build(self)
        fake.repos["r"] = {"releases": [release("v1", 40)], "tags": [], "files": {"CHANGELOG.md": changelog(2)}}
        sentinel.tick(NOW)
        metrics = sentinel.get_metrics()
        self.assertEqual((metrics["delivery_alerts"], metrics["delivery_unreleased_repos"], metrics["delivery_unreleased_days_max"], metrics["delivery_repos_checked"]), (1, 1, 40, 1))
        snapshot = sentinel.snapshot()
        self.assertEqual((snapshot["enabled"], snapshot["level"], len(snapshot["alerts"])), (True, "warn", 1))
        self.assertEqual(sentinel.get_config_schema()["keys"]["enabled"]["default"], False)

    def test_the_text_of_an_alert_is_translated_in_every_language(self):
        from github_actions_monitor import i18n
        for name in rules.SIGNALS:
            for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
                text = i18n.tl(lang, sd.TITLE_KEYS[rules.CODES[name]], repo="R", n=2, days=9, tag="T", current="C")
                self.assertNotIn("{", text)


class Reader(unittest.TestCase):
    NEED = {"releases": True, "tags": True, "changelog_paths": ["CHANGELOG.md"], "version_files": ["a.json"]}

    def test_the_plan_follows_the_signals_that_are_on(self):
        cfg = sd.settings({})
        self.assertEqual(reader.plan(cfg), {"releases": True, "tags": True, "changelog_paths": ["CHANGELOG.md"], "version_files": ["a.json"] if cfg["version_files"] else []})
        for s in cfg["signals"].values():
            s["enabled"] = False
        self.assertEqual(reader.minimum_calls(reader.plan(cfg)), 0)
        self.assertEqual(reader.minimum_calls(self.NEED), 4)

    def test_a_read_that_is_not_a_missing_file_raises_so_the_repository_is_listed_as_unreadable(self):
        def read(endpoint):
            if "contents" in endpoint:
                raise RuntimeError("HTTP 500: server error")
            return []
        with self.assertRaises(RuntimeError):
            reader.fetch(read, "acme", "r", self.NEED, 10)

    def test_a_file_too_big_for_the_api_has_no_content_and_reads_as_empty(self):
        facts, calls, complete = reader.fetch(lambda e: {"encoding": "none", "content": ""} if "contents" in e else [], "acme", "r", {**self.NEED, "version_files": []}, 10)
        self.assertEqual((facts["changelog"], calls, complete), ("", 3, True))


class Wiring(unittest.TestCase):
    def test_it_is_registered_off_by_default_and_starts_no_thread(self):
        self.assertIn("delivery", sentinel_registry._registry())
        ctx = {"gh": lambda *a, **k: [], "repos_fn": lambda: [], "eco_fn": lambda r: "x", "data_fn": lambda: None, "account_id": ""}
        registry = sentinel_registry.SentinelRegistry.build(ctx, {})
        self.assertIn("delivery", registry.names())
        self.assertFalse(registry.get("delivery").enabled)
        self.assertEqual(registry.get("delivery").get_status()["lifecycle"], "off")
        on = sentinel_registry.SentinelRegistry.build(ctx, {"sentinels": {"delivery": {"enabled": True}}})
        self.assertTrue(on.get("delivery").enabled)

    def test_its_alerts_reach_the_alerts_tab_and_can_be_filtered_by_sentinel(self):
        sentinel, fake, _ = build(self)
        fake.repos["r"] = {"releases": [release("v1", 1, body="")], "tags": [], "files": {}}
        sentinel.tick(NOW)

        class Registry:
            def alerts(self):
                return sentinel.get_alerts()
        listed = alert_center.collect(Registry())
        self.assertEqual({a["sentinel"] for a in listed}, {"delivery"})
        self.assertEqual(len(alert_center.select(listed, sentinel="delivery")), 1)
        self.assertEqual(alert_center.select(listed, sentinel="supply"), [])

    def test_the_state_file_follows_the_account_and_the_storage(self):
        from github_actions_monitor.accounts import accounts
        from github_actions_monitor.storage import file_storage, state_io
        self.assertIn(("github_actions_monitor.sentinels.sentinel_delivery", "STATE_FILE", "sentinel_state/delivery_state.json"), accounts.STATE_FILES)
        self.assertIn("delivery_state.json", [old for old, _new in accounts.LEGACY])
        self.assertIn("delivery_state", file_storage.FLAT_SENTINELS)
        self.assertIn(("github_actions_monitor.sentinels.sentinel_delivery", "STATE_FILE", "sentinel", "delivery_state"), state_io.ROUTES)
        self.assertIn("delivery_state.json", _testenv.WATCHED)
        ignore = HERE.parent / ".gitignore"
        if ignore.is_file():      # not in a package extracted without the repository
            self.assertIn("monitor/delivery_state.json", ignore.read_text(encoding="utf-8"))

    def test_notifications_know_the_two_new_kinds_and_give_them_to_the_release_family(self):
        from github_actions_monitor.integrations import dispatcher, notifiers
        for kind in ("delivery_new", "delivery_fixed"):
            self.assertIn(kind, notifiers.KNOWN_EVENTS)
            self.assertEqual(dispatcher.family_of(kind), "release")
            self.assertEqual(dispatcher.sentinel_of(kind), "ci")
        self.assertNotIn("delivery_new", notifiers.DEFAULT_EVENTS)      # nobody gets them until the owner asks

    def test_the_cli_filter_and_the_contract_know_the_new_sentinel(self):
        text = (HERE / "src" / "github_actions_monitor" / "cli" / "monitor_cli.py").read_text(encoding="utf-8")
        self.assertIn('"supply", "delivery", "system"', text)
        contract = json.loads((HERE / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8"))
        self.assertIn("/api/sentinel/delivery", [e["path"] for e in contract["fed_endpoints"]])


class Lite(unittest.TestCase):
    def test_the_lite_edition_loads_neither_the_sentinel_nor_the_package(self):
        code = ("import sys; sys.path.insert(0, %r); import github_actions_monitor.lite; "
                "bad = [m for m in sys.modules if m.startswith(('github_actions_monitor.delivery', 'github_actions_monitor.sentinels.sentinel_delivery'))]; print(bad); sys.exit(1 if bad else 0)" % str(HERE / "src"))
        done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
