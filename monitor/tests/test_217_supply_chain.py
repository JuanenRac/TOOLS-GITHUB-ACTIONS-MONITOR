# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The Supply chain sentinel (2.1.1): the five signals come from the one linter of workflows, a repository whose workflows cannot be read is never a clean bill of health, nothing is announced at the first
look or after a restart, the cost is bounded, the value of a secret is never read, and it is registered but off by default."""
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
from github_actions_monitor.cli import lint_workflows  # noqa: E402
from github_actions_monitor.data_pipeline import events  # noqa: E402
from github_actions_monitor.delivery import supply  # noqa: E402
from github_actions_monitor.sentinels import alert_center, sentinel_registry, sentinel_supply as ss  # noqa: E402

NOW = 1_800_000_000
SHA = "a" * 40
CLEAN = f"name: ci\non: push\npermissions:\n  contents: read\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@{SHA}\n"
LOOSE = "name: ci\non: push\npermissions:\n  contents: read\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: acme-tools/lint@main\n"
WIDE = "name: ci\non: push\npermissions: write-all\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n"
PRT = ("name: pr\non:\n  pull_request_target:\njobs:\n  t:\n    permissions:\n      contents: read\n    runs-on: ubuntu-latest\n    steps:\n"
       "      - uses: actions/checkout@" + SHA + "\n        with:\n          ref: ${{ github.event.pull_request.head.sha }}\n")
FAKE_TOKEN = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
SECRETY = f"name: s\non: push\npermissions:\n  contents: read\nenv:\n  GITHUB_TOKEN: {FAKE_TOKEN}\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@{SHA}\n"


def signals_of(text, repo="r", owner="acme", config=None):
    return sorted(f["signal"] for f in supply.findings(repo, {"x.yml": text}, config, owner))


class Fake:
    """`gh api` for the sentinel: {repo: {file name: text}}; a repository set to an exception message fails like `gh` does."""

    def __init__(self):
        self.repos, self.calls = {}, []

    def gh(self, *args, **kwargs):
        endpoint = args[-1]
        self.calls.append(endpoint)
        parts = endpoint.split("/")      # repos/acme/<repo>/contents/.github/workflows[/<file>]
        repo = parts[2]
        answer = self.repos.get(repo)
        if isinstance(answer, str):
            raise RuntimeError(answer)
        if answer is None or not answer:
            raise RuntimeError("HTTP 404: Not Found")
        if endpoint.endswith("/workflows"):
            return [{"type": "file", "name": n, "sha": str(hash(t))[:12], "size": len(t)} for n, t in sorted(answer.items())]
        name = parts[-1]
        return {"encoding": "base64", "content": base64.b64encode(answer[name].encode()).decode()}


def build(case, config=None, repos=("r",), rate=None, fake=None, folder=None):
    fake = fake or Fake()
    folder = folder or Path(tempfile.mkdtemp(prefix="supply_test_"))
    saved = (ss.STATE_FILE, events.EVENTS_FILE, events.STATE_FILE)
    ss.STATE_FILE, events.EVENTS_FILE, events.STATE_FILE = folder / "supply_state.json", folder / "events.jsonl", folder / "events_state.json"
    case.addCleanup(lambda: (setattr(ss, "STATE_FILE", saved[0]), setattr(events, "EVENTS_FILE", saved[1]), setattr(events, "STATE_FILE", saved[2])))
    old_owner = toolconfig.github_owner()
    toolconfig.set_owner("acme")
    case.addCleanup(lambda: toolconfig.set_owner(old_owner))
    settings = {"sentinels": {"supply": {"enabled": True, **(config or {})}}}
    ctx = {"gh": fake.gh, "repos_fn": lambda: list(repos), "eco_fn": lambda r: "web" if r.startswith("w") else "other", "data_fn": lambda: {"rate": rate} if rate else None, "account_id": ""}
    sentinel = ss.SentinelSupply(ctx, settings)
    sentinel.listened = []
    sentinel.feed.listeners.append(sentinel.listened.append)
    return sentinel, fake, folder


class Settings(unittest.TestCase):
    def test_off_by_default_with_the_documented_defaults(self):
        cfg = ss.settings({})
        self.assertFalse(cfg["enabled"])
        self.assertEqual((cfg["refresh_seconds"], cfg["max_repos_per_tick"], cfg["max_calls_per_tick"], cfg["min_rate_remaining"]), (3600, 10, 60, 1000))
        self.assertEqual({n: cfg["signals"][n]["level"] for n in supply.SIGNALS}, {"unpinned": "warning", "mutable_ref": "warning", "permissions_wide": "warning", "permissions_missing": "warning", "pr_target_checkout": "error"})

    def test_bad_values_keep_the_default_and_good_ones_are_taken(self):
        base = ss.settings({})
        bad = ss.settings({"sentinels": {"supply": {"enabled": "yes", "refresh_seconds": 5, "max_repos_per_tick": 0, "repos": 3, "signals": {"unpinned": {"level": "huge", "enabled": 1}, "x": {}}, "penalty": {"cap_per_repo": -1}}}})
        self.assertEqual(bad, base)
        good = ss.settings({"sentinels": {"supply": {"enabled": True, "refresh_seconds": 600, "signals": {"unpinned": {"level": "info"}, "mutable_ref": {"enabled": False}}}}})
        self.assertEqual((good["enabled"], good["refresh_seconds"], good["signals"]["unpinned"]["level"], good["signals"]["mutable_ref"]["enabled"]), (True, 600, "info", False))

    def test_the_settings_page_knows_every_key_and_refuses_a_bad_level_or_pattern(self):
        keys = {row[2] for row in settings_api.ROWS}
        for name in supply.SIGNALS:
            self.assertIn(f"sentinels.supply.signals.{name}.enabled", keys)
            self.assertIn(f"sentinels.supply.signals.{name}.level", keys)
        for key in ("enabled", "refresh_seconds", "max_repos_per_tick", "max_calls_per_tick", "max_files_per_repo", "min_rate_remaining", "repos", "ignore"):
            self.assertIn("sentinels.supply." + key, keys)


class Signals(unittest.TestCase):
    def test_each_signal_has_a_case_that_raises_it_and_a_clean_one_that_does_not(self):
        self.assertEqual(signals_of(CLEAN), [])
        self.assertEqual(signals_of(LOOSE), ["mutable_ref", "unpinned"])      # @v4 is a tag, @main a branch that moves
        self.assertEqual(signals_of(WIDE), ["permissions_wide"])
        self.assertEqual(signals_of("name: x\non: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo\n"), ["permissions_missing"])
        self.assertEqual(signals_of(PRT), ["pr_target_checkout"])

    def test_a_moving_branch_is_not_also_counted_as_a_tag(self):
        found = supply.findings("r", {"x.yml": LOOSE}, None, "acme")
        self.assertEqual({(f["signal"], f["detail"]) for f in found}, {("unpinned", "actions/checkout@v4"), ("mutable_ref", "acme-tools/lint@main")})

    def test_a_workflow_of_the_same_repository_is_not_a_third_party(self):
        text = CLEAN + "  c:\n    uses: acme/r/.github/workflows/other.yml@main\n"
        self.assertEqual(signals_of(text, repo="r", owner="acme"), [])
        self.assertEqual(signals_of(text, repo="other", owner="acme"), ["mutable_ref"])

    def test_the_same_findings_as_the_linter_for_the_same_text(self):
        """One source of truth: the lines of the findings are exactly those of `lint_text` for the rules this module uses."""
        for text in (LOOSE, WIDE, PRT, CLEAN):
            ours = sorted(f["line"] for f in supply.findings("r", {"x.yml": text}, None, "acme"))
            rules = {name: {"enabled": name in supply.USED_RULES, "severity": "warn"} for name in lint_workflows.RULES}
            theirs = sorted(f["line"] for f in lint_workflows.lint_text(text, "x.yml", rules) if f["rule"] in supply.USED_RULES)
            self.assertEqual(ours, theirs)

    def test_the_value_of_a_secret_is_never_read_or_reported(self):
        found = supply.findings("r", {"x.yml": SECRETY}, None, "acme")
        self.assertEqual(found, [])      # the secrets rule of the linter is off here
        self.assertNotIn(FAKE_TOKEN, json.dumps(supply.evaluate("r", supply.findings("r", {"x.yml": SECRETY + LOOSE}, None, "acme"), ss.DEFAULTS["signals"])))

    def test_the_comment_that_silences_a_rule_and_the_ignore_patterns_work(self):
        text = "name: ci\non: push\npermissions:\n  contents: read\njobs:\n  t:\n    runs-on: x\n    steps:\n      # monitor-lint: ignore unpinned_uses because it is our own mirror\n      - uses: actions/checkout@v4\n"
        self.assertEqual(signals_of(text), [])
        silenced = supply.findings("r", {"x.yml": LOOSE}, None, "acme", ["r:x.yml:unpinned_uses"])
        self.assertEqual(silenced, [])      # the pattern names the rule of the linter, and `unpinned_uses` is the rule behind both unpinned and mutable_ref
        other = supply.findings("r", {"x.yml": LOOSE}, None, "acme", ["r:y.yml:unpinned_uses", "s:x.yml:unpinned_uses"])
        self.assertEqual(sorted(f["signal"] for f in other), ["mutable_ref", "unpinned"])      # a pattern for another file or repository silences nothing

    def test_the_lint_settings_of_the_user_do_not_switch_the_sentinel_off(self):
        config = {"lint": {"rules": {"unpinned_uses": {"enabled": False}, "permissions": {"enabled": False}}}}
        self.assertEqual(signals_of(LOOSE, config=config), ["mutable_ref", "unpinned"])

    def test_one_alert_per_repository_and_signal_with_counts_and_a_level_that_can_be_changed(self):
        found = supply.findings("r", {"a.yml": LOOSE, "b.yml": LOOSE}, None, "acme")
        alerts = supply.evaluate("r", found, ss.settings({"sentinels": {"supply": {"signals": {"unpinned": {"level": "error"}, "mutable_ref": {"enabled": False}}}}})["signals"], stamp="t")
        self.assertEqual(sorted(alerts), ["actions.supply.unpinned:r"])
        a = alerts["actions.supply.unpinned:r"]
        self.assertEqual((a["level"], a["detail"]["n"], a["detail"]["files"], a["detail"]["examples"]), ("error", 2, ["a.yml", "b.yml"], ["actions/checkout@v4"]))

    def test_the_penalty_is_capped_per_repository(self):
        alerts = [{"repo": "r", "detail": {"n": 4}}, {"repo": "s", "detail": {"n": 1}}, {"repo": "r", "detail": {"n": 3}}]
        self.assertEqual(supply.penalty(alerts, 2, 10), 10 + 2)
        self.assertEqual(supply.penalty([], 2, 10), 0)


class Frontier(unittest.TestCase):
    def test_write_all_in_a_file_is_only_a_supply_signal_never_the_security_one(self):
        sentinel, fake, _ = build(self)
        fake.repos["r"] = {"w.yml": WIDE}
        sentinel.tick(NOW)
        codes = [a["code"] for a in sentinel.get_alerts()]
        self.assertEqual(codes, ["actions.supply.permissions_wide"])
        self.assertTrue(all(c.startswith("actions.supply.") for c in codes))
        self.assertNotIn("security.workflow_write", codes)


class Scanning(unittest.TestCase):
    def test_a_clean_repository_is_ok_and_one_without_workflows_has_nothing_to_report(self):
        sentinel, fake, _ = build(self, repos=("r", "s"))
        fake.repos["r"] = {"ci.yml": CLEAN}
        fake.repos["s"] = {}      # no .github/workflows folder at all: GitHub answers 404
        sentinel.tick(NOW)
        status = sentinel.get_status()
        self.assertEqual((status["level"], status["repos_checked"], status["unavailable"], status["lifecycle"]), ("ok", 2, {}, "healthy"))
        self.assertEqual(sentinel.get_alerts(), [])

    def test_the_first_look_finds_alerts_but_announces_nothing_and_a_change_does(self):
        sentinel, fake, _ = build(self)
        fake.repos["r"] = {"ci.yml": LOOSE}
        sentinel.tick(NOW)
        self.assertEqual([a["code"] for a in sentinel.get_alerts()], ["actions.supply.mutable_ref", "actions.supply.unpinned"])
        self.assertEqual(sentinel.listened, [])
        fake.repos["r"] = {"ci.yml": WIDE}
        sentinel.tick(NOW + 4000)
        events_seen = sorted((e["kind"], e["code"]) for batch in sentinel.listened for e in batch)
        self.assertEqual(events_seen, [("security_fixed", "actions.supply.mutable_ref"), ("security_fixed", "actions.supply.unpinned"), ("security_new", "actions.supply.permissions_wide")])
        self.assertTrue(all(e["sentinel"] == "supply" for batch in sentinel.listened for e in batch))

    def test_a_restart_announces_nothing_again(self):
        sentinel, fake, folder = build(self)
        fake.repos["r"] = {"ci.yml": LOOSE}
        sentinel.tick(NOW)
        again = ss.SentinelSupply(sentinel.ctx, {"sentinels": {"supply": {"enabled": True}}})
        again.listened = []
        again.feed.listeners.append(again.listened.append)
        self.assertEqual(len(again.get_alerts()), 2)
        again.tick(NOW + 4000)
        self.assertEqual(again.listened, [])
        self.assertEqual(len(again.get_alerts()), 2)

    def test_an_alert_keeps_the_time_it_was_first_seen(self):
        sentinel, fake, _ = build(self)
        fake.repos["r"] = {"ci.yml": LOOSE}
        sentinel.tick(NOW)
        first = {a["id"]: a["created_at"] for a in sentinel.get_alerts()}
        sentinel.tick(NOW + 4000)
        self.assertEqual({a["id"]: a["created_at"] for a in sentinel.get_alerts()}, first)

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
        fake.repos["r"] = {"ci.yml": LOOSE}
        sentinel.tick(NOW)
        fake.repos["r"] = "HTTP 403: Resource not accessible"
        sentinel.tick(NOW + 4000)
        self.assertEqual(len(sentinel.get_alerts()), 2)
        self.assertIn("unread_since", sentinel.get_alerts()[0]["details"])
        self.assertEqual([e for batch in sentinel.listened for e in batch if e["kind"] == "security_fixed"], [])
        sentinel.tick(NOW + 4000 + ss.UNREAD_KEEP + 10)      # a week without a reading: dropped without an event
        self.assertEqual(sentinel.get_alerts(), [])
        self.assertEqual([e for batch in sentinel.listened for e in batch if e["kind"] == "security_fixed"], [])

    def test_the_cost_of_a_round_is_bounded_by_the_repositories_and_the_calls(self):
        repos = tuple(f"r{i}" for i in range(8))
        sentinel, fake, _ = build(self, config={"max_repos_per_tick": 3}, repos=repos)
        for r in repos:
            fake.repos[r] = {"ci.yml": CLEAN}
        sentinel.tick(NOW)
        self.assertEqual(sentinel.get_status()["repos_checked"], 3)
        self.assertEqual(len(fake.calls), 3 * 2)      # one to list and one for the file, for each of the three
        sentinel.tick(NOW + 4000)
        self.assertEqual(sentinel.get_status()["repos_checked"], 6)      # the ones read longest ago come first
        budget, fake2 = None, Fake()
        sentinel2, fake2, _ = build(self, config={"max_calls_per_tick": 3}, repos=repos, fake=fake2)
        for r in repos:
            fake2.repos[r] = {"ci.yml": CLEAN}
        sentinel2.tick(NOW)
        self.assertLessEqual(len(fake2.calls), 4)      # the budget is spent after the second repository (2 + 2 calls at most)

    def test_an_unchanged_file_is_not_read_again(self):
        sentinel, fake, _ = build(self)
        fake.repos["r"] = {"ci.yml": CLEAN}
        sentinel.tick(NOW)
        before = len(fake.calls)
        sentinel.tick(NOW + 4000)
        self.assertEqual(len(fake.calls) - before, 1)      # only the list: the SHA of the file did not change

    def test_it_pauses_below_the_allowance_and_off_it_reads_nothing(self):
        sentinel, fake, _ = build(self, rate={"remaining": 10})
        fake.repos["r"] = {"ci.yml": LOOSE}
        self.assertFalse(sentinel.tick(NOW))
        self.assertEqual(fake.calls, [])
        self.assertEqual(sentinel.get_status()["lifecycle"], "paused")
        off = ss.SentinelSupply({"gh": fake.gh, "repos_fn": lambda: ["r"], "eco_fn": lambda r: "x"}, {})
        self.assertFalse(off.tick(NOW))
        self.assertEqual((off.get_alerts(), off.get_metrics(), off.get_status()["lifecycle"]), ([], {}, "off"))

    def test_a_failing_repository_waits_for_its_retry_and_does_not_starve_the_rest(self):
        class Boom(Fake):
            def gh(self, *a, **k):
                if "/bad/" in a[-1]:
                    raise ValueError("boom")
                return super().gh(*a, **k)
        sentinel, fake, _ = build(self, repos=("bad", "ok"), fake=Boom())
        fake.repos["ok"] = {"ci.yml": LOOSE}
        fake.repos["bad"] = {"ci.yml": LOOSE}
        sentinel.tick(NOW)
        self.assertEqual({a["repo"] for a in sentinel.get_alerts()}, {"ok"})
        self.assertEqual(sentinel.get_status()["unavailable"], {"error": 1})
        before = len([c for c in fake.calls if "/bad/" in c])
        sentinel.tick(NOW + 60)      # inside its retry time: it goes to the end of the line, the other one is read first
        self.assertEqual(sentinel.get_status()["repos_checked"], 2)

    def test_the_metrics_and_the_snapshot(self):
        sentinel, fake, _ = build(self)
        fake.repos["r"] = {"ci.yml": LOOSE + "      - uses: x/y@v1\n"}
        sentinel.tick(NOW)
        metrics = sentinel.get_metrics()
        self.assertEqual((metrics["supply_alerts"], metrics["supply_findings"], metrics["supply_repos_checked"]), (2, 3, 1))
        self.assertEqual(metrics["supply_penalty"], 6)
        snapshot = sentinel.snapshot()
        self.assertEqual((snapshot["enabled"], snapshot["level"], len(snapshot["alerts"])), (True, "warn", 2))
        self.assertEqual(sentinel.get_config_schema()["keys"]["enabled"]["default"], False)

    def test_the_state_file_never_carries_a_secret(self):
        sentinel, fake, folder = build(self)
        fake.repos["r"] = {"ci.yml": SECRETY + "      - uses: a/b@v1\n"}
        sentinel.tick(NOW)
        self.assertNotIn(FAKE_TOKEN, (folder / "supply_state.json").read_text(encoding="utf-8"))
        self.assertNotIn(FAKE_TOKEN, json.dumps(sentinel.snapshot()))


class Wiring(unittest.TestCase):
    def test_it_is_registered_off_by_default_and_starts_no_thread(self):
        self.assertIn("supply", sentinel_registry._registry())
        ctx = {"gh": lambda *a, **k: [], "repos_fn": lambda: [], "eco_fn": lambda r: "x", "data_fn": lambda: None, "account_id": ""}
        registry = sentinel_registry.SentinelRegistry.build(ctx, {})
        self.assertIn("supply", registry.names())
        self.assertFalse(registry.get("supply").enabled)
        self.assertEqual(registry.get("supply").get_status()["lifecycle"], "off")
        on = sentinel_registry.SentinelRegistry.build(ctx, {"sentinels": {"supply": {"enabled": True}}})
        self.assertTrue(on.get("supply").enabled)

    def test_its_alerts_reach_the_alerts_tab_and_can_be_filtered_by_sentinel(self):
        sentinel, fake, _ = build(self)
        fake.repos["r"] = {"ci.yml": LOOSE}
        sentinel.tick(NOW)

        class Registry:
            def alerts(self):
                return sentinel.get_alerts()
        listed = alert_center.collect(Registry())
        self.assertEqual({a["sentinel"] for a in listed}, {"supply"})
        self.assertEqual(len(alert_center.select(listed, sentinel="supply")), 2)
        self.assertEqual(alert_center.select(listed, sentinel="security"), [])

    def test_the_state_file_follows_the_account_and_the_storage(self):
        from github_actions_monitor.accounts import accounts
        from github_actions_monitor.storage import file_storage, state_io
        self.assertIn(("github_actions_monitor.sentinels.sentinel_supply", "STATE_FILE", "sentinel_state/supply_state.json"), accounts.STATE_FILES)
        self.assertIn("supply_state.json", [old for old, _new in accounts.LEGACY])
        self.assertIn("supply_state", file_storage.FLAT_SENTINELS)
        self.assertIn(("github_actions_monitor.sentinels.sentinel_supply", "STATE_FILE", "sentinel", "supply_state"), state_io.ROUTES)
        self.assertIn("supply_state.json", _testenv.WATCHED)
        ignore = HERE.parent / ".gitignore"
        if ignore.is_file():      # not in a package extracted without the repository
            self.assertIn("monitor/supply_state.json", ignore.read_text(encoding="utf-8"))

    def test_notifications_treat_its_events_as_security_ones(self):
        from github_actions_monitor.integrations import dispatcher
        self.assertEqual(dispatcher.sentinel_of("security_new"), "security")
        self.assertIn("security_new", dispatcher.FAMILIES["ci"])

    def test_the_cli_filter_and_the_contract_know_the_new_sentinel(self):
        text = (HERE / "src" / "github_actions_monitor" / "cli" / "monitor_cli.py").read_text(encoding="utf-8")
        self.assertIn('"security", "supply", "system"', text)
        contract = json.loads((HERE / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8"))
        self.assertIn("/api/sentinel/supply", [e["path"] for e in contract["fed_endpoints"]])


class Lite(unittest.TestCase):
    def test_the_lite_edition_loads_neither_the_sentinel_nor_the_package(self):
        code = ("import sys; sys.path.insert(0, %r); import github_actions_monitor.lite; "
                "bad = [m for m in sys.modules if m.startswith(('github_actions_monitor.delivery', 'github_actions_monitor.sentinels.sentinel_supply'))]; print(bad); sys.exit(1 if bad else 0)" % str(HERE / "src"))
        done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
