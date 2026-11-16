# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The optional, cheap rules of the workflow linter: a job without timeout-minutes, `secrets: inherit`, no permissions at the top of the file, and an action of your own that follows a branch. Synthetic
workflow texts, no network and no `gh`."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.cli import lint_workflows as lw  # noqa: E402
from github_actions_monitor.integrations import reports  # noqa: E402

SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
HEAD = "name: CI\non: [push]\npermissions:\n  contents: read\n"


def rules(**on):
    cfg = lw.settings({"lint": {"rules": {name: {"enabled": True} for name in on}}})
    return cfg["rules"]


def kinds(text, rule_set=None, own=()):
    return [(f["rule"], f["line"], f["detail"]) for f in lw.lint_text(text, "ci.yml", rule_set, own)]


class Optional(unittest.TestCase):
    TIMEOUTLESS = HEAD + "jobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n  safe:\n    runs-on: ubuntu-latest\n    timeout-minutes: 10\n    steps:\n      - run: echo hi\n  call:\n    uses: ./.github/workflows/other.yml\n"

    def test_the_optional_rules_are_off_until_they_are_switched_on(self):
        text = self.TIMEOUTLESS + "    secrets: inherit\n"
        self.assertEqual([k for k in kinds(text) if k[0] in ("no_timeout", "secrets_inherit", "permissions_top")], [])
        cfg = lw.settings({})
        for name in ("no_timeout", "secrets_inherit", "permissions_top"):
            self.assertFalse(cfg["rules"][name]["enabled"], name)
        self.assertTrue(cfg["rules"]["own_action_ref"]["enabled"])

    def test_a_job_without_a_time_limit_is_named_and_a_call_of_a_reusable_workflow_is_left_out(self):
        self.assertEqual([k for k in kinds(self.TIMEOUTLESS, rules(no_timeout=1)) if k[0] == "no_timeout"], [("no_timeout", 6, "build")])

    def test_the_hygiene_report_keeps_one_finding_per_job(self):
        found = [f for f in reports.hygiene_findings(self.TIMEOUTLESS) if f["rule"] == "no_timeout"]
        self.assertEqual([(f["line"], f["detail"]) for f in found], [(6, "build")])

    def test_secrets_inherit_is_found_and_can_be_silenced_where_it_is(self):
        text = HEAD + "jobs:\n  call:\n    uses: acme/shared/.github/workflows/x.yml@" + SHA + "\n    secrets: inherit\n"
        self.assertEqual([k for k in kinds(text, rules(secrets_inherit=1)) if k[0] == "secrets_inherit"], [("secrets_inherit", 8, "")])
        quiet = text.replace("    secrets: inherit", "    # monitor-lint: ignore secrets_inherit because the called workflow needs them all\n    secrets: inherit")
        self.assertEqual([k for k in kinds(quiet, rules(secrets_inherit=1)) if k[0] == "secrets_inherit"], [])
        explicit = text.replace("secrets: inherit", "secrets:\n      token: ${{ secrets.TOKEN }}")
        self.assertEqual([k for k in kinds(explicit, rules(secrets_inherit=1)) if k[0] == "secrets_inherit"], [])

    def test_permissions_at_the_top_are_asked_only_when_the_jobs_have_their_own(self):
        job_level = "name: CI\non: [push]\njobs:\n  t:\n    permissions:\n      contents: read\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo\n"
        self.assertEqual([k[0] for k in kinds(job_level, rules(permissions_top=1)) if k[0].startswith("permissions")], ["permissions_top"])
        self.assertEqual([k[0] for k in kinds(HEAD + job_level.split("[push]\n", 1)[1], rules(permissions_top=1)) if k[0].startswith("permissions")], [])
        none = "name: CI\non: [push]\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo\n"
        self.assertEqual([k[0] for k in kinds(none, rules(permissions_top=1)) if k[0].startswith("permissions")], ["permissions"])      # the old rule speaks, not both


class Own(unittest.TestCase):
    def uses(self, *specs):
        return HEAD + "jobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n" + "".join(f"      - uses: {s}\n" for s in specs)

    def test_without_own_owners_nothing_changes(self):
        self.assertEqual([k[0] for k in kinds(self.uses("acme/tools@main", "other/x@v4"))], ["unpinned_uses", "unpinned_uses"])

    def test_an_action_of_your_own_on_a_branch_is_reported_a_version_tag_is_not_and_a_third_party_still_needs_a_sha(self):
        text = self.uses("acme/tools@main", "acme/tools@v2", "Acme/tools@v2.1.0", "acme/tools@" + SHA, "other/x@v4", "other/x@" + SHA, "./local", "docker://img:1")
        self.assertEqual(kinds(text, own=("acme",)), [("own_action_ref", 9, "acme/tools@main"), ("unpinned_uses", 13, "other/x@v4")])

    def test_a_reusable_workflow_of_your_own_follows_the_same_rule(self):
        text = HEAD + "jobs:\n  c:\n    uses: acme/shared/.github/workflows/x.yml@main\n"
        self.assertEqual([k[0] for k in kinds(text, own=("acme",))], ["own_action_ref"])

    def test_the_setting_keeps_only_valid_account_names(self):
        cfg = lw.settings({"lint": {"own_owners": ["Acme", "bad name", "../x", 5, "ok-1"]}})
        self.assertEqual(cfg["own_owners"], ["acme", "ok-1"])
        self.assertEqual(lw.settings({"lint": {"own_owners": "acme"}})["own_owners"], [])

    def test_the_clone_scan_and_the_command_line_know_the_owners(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "r" / ".github" / "workflows"
            folder.mkdir(parents=True)
            (folder / "ci.yml").write_text(self.uses("acme/tools@main"), encoding="utf-8")
            self.assertEqual([f["rule"] for f in lw.scan_clones(tmp, ["r"], own=("acme",))["r"]], ["own_action_ref"])
            self.assertEqual([f["rule"] for f in lw.scan_clones(tmp, ["r"])["r"]], ["unpinned_uses"])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                lw.main([str(Path(tmp) / "r"), "--own", "acme", "--json"])
            self.assertEqual([f["rule"] for f in json.loads(out.getvalue())], ["own_action_ref"])


class Texts(unittest.TestCase):
    def test_every_rule_has_its_text_in_the_eight_languages_and_its_switch_on_the_page(self):
        from github_actions_monitor.app import settings_api
        for lang in i18n.LANGS:
            cat = i18n.catalogue(lang)
            for rule in lw.RULES:
                self.assertIn("lint.rule." + rule, cat, (lang, rule))
            self.assertTrue(cat.get("cfg.f.lint.own_owners") and cat.get("cfg.h.lint.own_owners") and cat.get("lint.help_own"), lang)
        for rule in lw.RULES:
            self.assertIn(f"lint.rules.{rule}.enabled", settings_api.FIELDS)
            self.assertIn(f"lint.rules.{rule}.severity", settings_api.FIELDS)
        self.assertIn("lint.own_owners", settings_api.FIELDS)


if __name__ == "__main__":
    unittest.main()
