# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The information rule of the workflow linter about actions whose repository is archived or has had no push for years (`archived_action`): off by default, information only, one read of GitHub per action with a
cache and a budget, and nothing said about an action that could not be read. GitHub is replaced by a double; nothing here reaches the network."""
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
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.cli import lint_workflows as lw  # noqa: E402
from github_actions_monitor.integrations import action_health as ah  # noqa: E402

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
NOW = 1_800_000_000      # a fixed clock: the tests never look at the real time
DAY = 86400


def stamp(seconds_ago):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(NOW - seconds_ago, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Api:
    """A double of GitHub: {"owner/repo": {"archived", "pushed_at"} | Exception}."""

    def __init__(self, table):
        self.table, self.calls = table, []

    def __call__(self, endpoint):
        self.calls.append(endpoint)
        key = endpoint.split("/", 1)[1].lower()
        item = self.table.get(key, OSError("404 Not Found"))
        if isinstance(item, Exception):
            raise item
        return item


TABLE = {
    "old/dead": {"archived": True, "pushed_at": stamp(5 * 365 * DAY)},
    "old/quiet": {"archived": False, "pushed_at": stamp(3 * 365 * DAY)},
    "new/alive": {"archived": False, "pushed_at": stamp(10 * DAY)},
}
WORKFLOW = """name: ci
on: push
permissions: {}
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: old/dead@v1
      - uses: old/quiet/sub/dir@v2
      - uses: new/alive@v3
      - uses: ./local-action
      - uses: docker://alpine:3
"""


def rules(enabled=True, severity=None):
    out = lw.settings(None)["rules"]
    out["archived_action"]["enabled"] = enabled
    if severity:
        out["archived_action"]["severity"] = severity
    return out


class Defaults(unittest.TestCase):
    def test_the_rule_exists_is_optional_and_off_and_is_information(self):
        self.assertIn("archived_action", lw.RULES)
        self.assertIn("archived_action", lw.OPTIONAL)
        cfg = lw.settings(None)
        self.assertIs(cfg["rules"]["archived_action"]["enabled"], False)
        self.assertEqual(cfg["rules"]["archived_action"]["severity"], "info")
        self.assertEqual(cfg["maintenance"], {"inactive": False, "inactive_years": 2, "refresh_seconds": 604800, "max_calls_per_tick": 10})

    def test_a_severity_in_the_file_is_ignored_for_this_rule(self):
        cfg = lw.settings({"lint": {"rules": {"archived_action": {"enabled": True, "severity": "bad"}}}})
        self.assertIs(cfg["rules"]["archived_action"]["enabled"], True)
        self.assertEqual(cfg["rules"]["archived_action"]["severity"], "info")

    def test_the_settings_keep_to_their_ranges(self):
        cfg = lw.settings({"lint": {"maintenance": {"inactive": True, "inactive_years": 4, "refresh_seconds": 7200, "max_calls_per_tick": 30}}})["maintenance"]
        self.assertEqual(cfg, {"inactive": True, "inactive_years": 4, "refresh_seconds": 7200, "max_calls_per_tick": 30})
        odd = lw.settings({"lint": {"maintenance": {"inactive": "yes", "inactive_years": 0, "refresh_seconds": 5, "max_calls_per_tick": True}}})["maintenance"]
        self.assertEqual(odd, ah.settings(None))

    def test_the_settings_page_offers_the_switch_and_the_numbers_but_no_severity(self):
        for key in ("lint.rules.archived_action.enabled", "lint.maintenance.inactive", "lint.maintenance.inactive_years", "lint.maintenance.refresh_seconds", "lint.maintenance.max_calls_per_tick"):
            self.assertIn(key, settings_api.FIELDS, key)
        self.assertNotIn("lint.rules.archived_action.severity", settings_api.FIELDS)
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["lint"]["rules"]["archived_action"], {"enabled": False})
        self.assertEqual(example["lint"]["maintenance"], {"inactive": False, "inactive_years": 2, "refresh_seconds": 604800, "max_calls_per_tick": 10})


class Reading(unittest.TestCase):
    def health(self, table=None, **kw):
        api = Api(TABLE if table is None else table)
        clock = [NOW]
        health = ah.Health(api, clock=lambda: clock[0], **kw)
        health.begin(20)
        return health, api, clock

    def test_owner_and_repository_come_from_any_form_of_uses(self):
        self.assertEqual(ah.owner_repo("old/dead@v1"), ("old", "dead"))
        self.assertEqual(ah.owner_repo("old/quiet/sub/dir@v2"), ("old", "quiet"))
        self.assertEqual(ah.owner_repo("org/repo/.github/workflows/x.yml@abc"), ("org", "repo"))
        for odd in ("./local", "docker://alpine:3", "no-slash@v1", "a/b", "", None, "../x/y@v1", "a b/c@v1"):
            self.assertIsNone(ah.owner_repo(odd), odd)

    def test_an_archived_action_is_reported_and_a_live_one_is_not(self):
        health, _, _ = self.health()
        self.assertEqual(health.verdict("old/dead@v1"), ("archived", "old/dead"))
        self.assertIsNone(health.verdict("new/alive@v3"))

    def test_an_action_without_activity_is_reported_only_when_asked_and_after_n_years(self):
        quiet, _, _ = self.health()
        self.assertIsNone(quiet.verdict("old/quiet@v2"))      # off by default
        asked, _, _ = self.health(inactive=True)
        self.assertEqual(asked.verdict("old/quiet@v2"), ("inactive", "old/quiet"))
        five, _, _ = self.health(inactive=True, inactive_years=5)
        self.assertIsNone(five.verdict("old/quiet@v2"))      # three years is under five
        self.assertIsNone(asked.verdict("new/alive@v3"))

    def test_one_read_per_action_and_the_answer_is_kept_until_it_is_old(self):
        health, api, clock = self.health(refresh_seconds=3600)
        for _ in range(5):
            health.verdict("old/dead@v1")
            health.verdict("Old/Dead/x@v9")      # the same repository in another spelling
        self.assertEqual(len(api.calls), 1)
        clock[0] += 3601
        health.verdict("old/dead@v1")
        self.assertEqual(len(api.calls), 2)

    def test_no_budget_means_no_call_and_no_judgement(self):
        health, api, _ = self.health()
        health.begin(0)
        self.assertIsNone(health.verdict("old/dead@v1"))
        self.assertEqual(api.calls, [])
        self.assertEqual(health.summary()["skipped"], 1)
        health.begin(1)
        self.assertEqual(health.verdict("old/dead@v1"), ("archived", "old/dead"))

    def test_the_budget_of_a_pass_is_never_exceeded(self):
        health, api, _ = self.health()
        health.begin(2)
        for name in ("old/dead", "old/quiet", "new/alive"):
            health.verdict(f"{name}@v1")
        self.assertEqual(len(api.calls), 2)
        self.assertEqual(health.summary()["skipped"], 1)

    def test_without_a_network_nothing_is_said_and_the_summary_says_why(self):
        health, api, clock = self.health({"old/dead": OSError("could not resolve host")})
        self.assertIsNone(health.verdict("old/dead@v1"))
        self.assertEqual(health.summary(), {"checked": 0, "archived": 0, "inactive": 0, "unread": 1, "skipped": 0})
        health.verdict("old/dead@v1")
        self.assertEqual(len(api.calls), 1)      # a failed read is not repeated at once
        clock[0] += ah.FAILURE_PAUSE + 1
        health.verdict("old/dead@v1")
        self.assertEqual(len(api.calls), 2)

    def test_a_repository_that_is_not_there_is_not_a_failure_of_the_network(self):
        health, _, _ = self.health({})
        self.assertIsNone(health.verdict("gone/action@v1"))
        self.assertEqual(health.summary()["unread"], 0)

    def test_an_answer_that_is_not_an_object_is_not_trusted(self):
        health, _, _ = self.health({"old/dead": ["archived"]})
        self.assertIsNone(health.verdict("old/dead@v1"))
        self.assertEqual(health.summary()["unread"], 1)

    def test_changing_the_question_forgets_the_old_answers(self):
        health, api, _ = self.health()
        health.verdict("old/quiet@v2")
        health.configure(True, 2, 604800)
        self.assertEqual(health.verdict("old/quiet@v2"), ("inactive", "old/quiet"))
        self.assertEqual(len(api.calls), 2)


class InTheLinter(unittest.TestCase):
    def lint(self, text=WORKFLOW, rule_set=None, health=None):
        return [f for f in lw.lint_text(text, "ci.yml", rule_set or rules(), health) if f["rule"] == "archived_action"]

    def health(self, **kw):
        api = Api(TABLE)
        health = ah.Health(api, clock=lambda: NOW, **kw)
        health.begin(50)
        return health, api

    def test_the_rule_names_the_archived_action_on_its_line_as_information(self):
        health, _ = self.health()
        found = self.lint(health=health)
        self.assertEqual([(f["line"], f["detail"], f["kind"], f["severity"]) for f in found], [(8, "old/dead", "archived", "info")])

    def test_the_inactive_ones_join_when_asked(self):
        health, _ = self.health(inactive=True)
        self.assertEqual([(f["line"], f["kind"]) for f in self.lint(health=health)], [(8, "archived"), (9, "inactive")])

    def test_off_means_no_finding_and_not_a_single_read(self):
        health, api = self.health()
        self.assertEqual(self.lint(rule_set=rules(enabled=False), health=health), [])
        self.assertEqual(api.calls, [])

    def test_without_the_helper_the_linter_never_goes_to_the_network(self):
        self.assertEqual(self.lint(health=None), [])

    def test_a_severity_put_in_the_rules_cannot_make_it_more_serious(self):
        health, _ = self.health()
        got = self.lint(rule_set=rules(severity="bad"), health=health)
        self.assertEqual({f["severity"] for f in got}, {"info"})

    def test_it_can_be_silenced_where_it_is(self):
        text = WORKFLOW.replace("      - uses: old/dead@v1", "      # monitor-lint: ignore archived_action because we mirror it\n      - uses: old/dead@v1")
        health, _ = self.health()
        self.assertEqual(self.lint(text, health=health), [])

    def test_local_and_image_actions_are_never_asked(self):
        health, api = self.health()
        self.lint("jobs:\n  a:\n    steps:\n      - uses: ./x\n      - uses: docker://alpine:3\n", health=health)
        self.assertEqual(api.calls, [])

    def test_scan_of_clones_and_ignore_patterns_pass_the_helper_on(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "repo" / ".github" / "workflows"
            folder.mkdir(parents=True)
            (folder / "ci.yml").write_text(WORKFLOW, encoding="utf-8")
            health, _ = self.health()
            by_repo = lw.scan_clones(tmp, ["repo"], rules(), None, health)
            self.assertEqual([f["rule"] for f in by_repo["repo"] if f["rule"] == "archived_action"], ["archived_action"])
            health.begin(50)
            quiet = lw.scan_clones(tmp, ["repo"], rules(), ["repo:ci.yml:archived_action"], health)
            self.assertFalse([f for f in quiet.get("repo", []) if f["rule"] == "archived_action"])


class CommandLine(unittest.TestCase):
    def run_cli(self, args, api, text=WORKFLOW):
        out, err = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "ci.yml").write_text(text, encoding="utf-8")
            with mock.patch.object(lw, "_gh_json", api), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = lw.main([str(Path(tmp) / "ci.yml")] + args)
        return code, out.getvalue(), err.getvalue()

    def test_without_the_flag_nothing_is_asked(self):
        api = Api(TABLE)
        code, out, _ = self.run_cli([], api)
        self.assertEqual(api.calls, [])
        self.assertNotIn("archived", out)

    def test_the_flag_lists_the_archived_action_and_the_exit_code_stays_clean_even_at_info(self):
        api = Api(TABLE)
        pinned = WORKFLOW.replace("@v1", "@" + "a" * 40).replace("@v2", "@" + "b" * 40).replace("@v3", "@" + "c" * 40)
        code, out, err = self.run_cli(["--check-actions", "--fail-on", "info"], api, pinned)
        self.assertIn("ci.yml:8: [info]", out)
        self.assertIn("old/dead", out)
        self.assertIn("Actions checked: 3; archived: 1; without activity: 0.", err)
        self.assertEqual(code, 0)      # a finding of this rule never fails the run, not even with --fail-on info
        code, _, _ = self.run_cli(["--fail-on", "info"], api, WORKFLOW)
        self.assertEqual(code, 1)      # the others still do

    def test_inactive_years_also_asks_for_the_quiet_ones(self):
        api = Api(TABLE)
        _, out, err = self.run_cli(["--inactive-years", "2"], api)
        self.assertIn("old/quiet", out)
        self.assertIn("without activity: 1", err)

    def test_without_a_network_it_says_so_and_does_not_fail(self):
        api = Api({k: OSError("network is unreachable") for k in ("old/dead", "old/quiet", "new/alive")})
        code, out, err = self.run_cli(["--check-actions"], api)
        self.assertNotIn("archived_action", out)
        self.assertIn("Could not read 3 action(s) from GitHub", err)
        self.assertEqual(code, 0)


class Sentinel(unittest.TestCase):
    """The scan of the monitor builds the helper with its allowance gate and its budget."""

    def make(self, remaining=5000, budget=7, enabled=True, cfg=None):
        from github_actions_monitor.sentinels import sentinel_local as sl
        sent = object.__new__(sl.Sentinel)
        sent.action_health = None
        sent.cfg = {"min_rate_remaining": 1500, "surface": {"min_rate_factor": 1.5}}
        sent.ctx = {"data_fn": lambda: {"rate": {"remaining": remaining}}}
        sent._budget = lambda: budget
        sent._gh = lambda *a, **k: {}
        return sent, lw.settings({"lint": {"rules": {"archived_action": {"enabled": enabled}}, **(cfg or {})}})

    def test_off_gives_no_helper(self):
        sent, cfg = self.make(enabled=False)
        self.assertIsNone(sent._action_health(cfg))

    def test_the_budget_is_the_smaller_of_the_setting_and_the_hourly_budget(self):
        sent, cfg = self.make(budget=7)
        health = sent._action_health(cfg)
        self.assertEqual(health.left, 7)
        sent, cfg = self.make(budget=70, cfg={"maintenance": {"max_calls_per_tick": 3}})
        self.assertEqual(sent._action_health(cfg).left, 3)

    def test_a_low_allowance_spends_nothing(self):
        sent, cfg = self.make(remaining=100)
        self.assertEqual(sent._action_health(cfg).left, 0)

    def test_the_same_helper_is_reused_so_its_cache_lives_on(self):
        sent, cfg = self.make()
        self.assertIs(sent._action_health(cfg), sent._action_health(cfg))


class Words(unittest.TestCase):
    KEYS = ("lint.rule.archived_action", "lint.help_check_actions", "lint.help_inactive_years", "lint.maintenance_offline", "lint.maintenance_summary", "lint.kind.archived", "lint.kind.inactive",
            "ui.cfg_b_lint_maintenance", "ui.a13_maint", "ui.a13_maint_off", "cfg.f.lint.maintenance.inactive", "cfg.h.lint.maintenance.inactive", "cfg.f.lint.maintenance.inactive_years",
            "cfg.h.lint.maintenance.inactive_years", "cfg.f.lint.maintenance.refresh_seconds", "cfg.h.lint.maintenance.refresh_seconds", "cfg.f.lint.maintenance.max_calls_per_tick",
            "cfg.h.lint.maintenance.max_calls_per_tick")

    def test_every_word_exists_in_the_eight_languages_with_the_same_placeholders(self):
        import re
        cats = {lang: json.loads((HERE / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}
        for key in self.KEYS:
            holes = set(re.findall(r"\{(\w+)\}", cats["en"][key]))
            for lang in LANGS:
                self.assertTrue(cats[lang].get(key), (lang, key))
                self.assertEqual(set(re.findall(r"\{(\w+)\}", cats[lang][key])), holes, (lang, key))
            for lang in LANGS[1:]:
                self.assertNotEqual(cats[lang][key], cats["en"][key], (lang, key))

    def test_the_guide_and_the_help_of_the_command_name_the_rule_and_the_flags(self):
        for suffix in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por"):
            text = (HERE / "docs" / f"CONSOLE_TOOLS{suffix}.md").read_text(encoding="utf-8")
            for token in ("archived_action", "--check-actions", "--inactive-years N", "lint.maintenance.inactive", "lint.maintenance.max_calls_per_tick"):
                self.assertIn(token, text, (suffix, token))
        self.assertIn("archived_action", lw.__doc__)
        self.assertIn("--check-actions", lw.__doc__.split("Optional rules")[0] + lw.__doc__)


if __name__ == "__main__":
    unittest.main()
