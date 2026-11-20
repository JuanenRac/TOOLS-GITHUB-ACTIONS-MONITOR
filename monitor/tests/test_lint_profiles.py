# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Renovate counts like Dependabot (A4 and coverage), the linter tells an own action from a third-party one, and three optional rules (no timeout, secrets: inherit, an own action on @main)
are off until switched on. Synthetic workflow files and pull requests, no network."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import _testenv  # noqa: F401
from github_actions_monitor.app import settings_api as sa  # noqa: E402
from github_actions_monitor.app import surface  # noqa: E402
from github_actions_monitor.cli import lint_workflows as lw  # noqa: E402
from github_actions_monitor.integrations import reports  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402

NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
SHA = "0123456789abcdef0123456789abcdef01234567"

WORKFLOW = f"""name: CI
on: push
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: acme-org/shared-action@main
      - uses: acme-org/other-action@v2
      - uses: thirdparty/tool@{SHA}
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: thirdparty/lint@main
  call:
    uses: acme-org/workflows/.github/workflows/release.yml@v1
    secrets: inherit
"""


def settings(**lint):
    return lw.settings({"lint": {"own_owners": ["acme-org"], **lint}})


def found(text, cfg):
    return [(f["rule"], f["line"], f.get("kind", ""), f["severity"]) for f in lw.lint_text(text, "ci.yml", cfg["rules"])]


class Pr:
    @staticmethod
    def make(author, title, number=1):
        return {"number": number, "title": title, "url": f"https://x/{number}", "author": {"login": author}, "createdAt": "2026-11-01T00:00:00Z", "isDraft": False,
                "mergeable": "MERGEABLE", "files": {"nodes": [{"path": "package.json"}]}}


class Renovate(unittest.TestCase):
    def test_every_form_of_the_login_of_a_dependency_bot(self):
        for login in ("dependabot", "app/dependabot", "dependabot[bot]", "renovate", "app/renovate", "renovate[bot]", "Renovate-Bot"):
            self.assertTrue(sl.is_dependency_bot(login), login)
        for login in ("octocat", "", "github-actions[bot]", "renovated-by-hand", "someone-bot"):
            self.assertFalse(sl.is_dependency_bot(login), login)

    def test_the_accounts_are_a_setting(self):
        self.assertFalse(sl.is_dependency_bot("renovate[bot]", ["dependabot"]))
        self.assertTrue(sl.is_dependency_bot("my-updater", ["my-updater"]))
        self.assertEqual(sl.DEFAULTS["dependency_bots"], ["dependabot", "renovate"])

    def test_a_renovate_pull_request_is_an_update_with_a_package_and_an_unknown_jump(self):
        pr = sl.classify_pr("R", Pr.make("app/renovate", "Update dependency left-pad to v2.1.0"), NOW)
        self.assertTrue(pr["dependabot"])
        self.assertEqual((pr["pkg"], pr["major"]), ("left-pad", None))      # the title does not say from which version: the jump is not guessed
        action = sl.classify_pr("R", Pr.make("renovate[bot]", "Update actions/checkout action to v4"), NOW)
        self.assertEqual(action["pkg"], "actions/checkout")
        dep = sl.classify_pr("R", Pr.make("dependabot[bot]", "Bump left-pad from 1.3.0 to 2.0.0"), NOW)
        self.assertEqual((dep["pkg"], dep["major"]), ("left-pad", True))

    def test_a4_lists_them_and_other_people_are_only_counted(self):
        info = {"R": {"branch": "main", "pushed": None, "release": None, "vuln_total": 0, "vuln_sev": {}, "rulesets": [], "label_dependencies": True, "files": {},
                      "prs": [Pr.make("renovate[bot]", "Update dependency a to v2", 1), Pr.make("dependabot[bot]", "Bump b from 1 to 2", 2), Pr.make("octocat", "Fix typo", 3)]}}
        inp = {"now": NOW, "today": "2026-11-04", "cfg": sl.DEFAULTS, "repos": ["R"], "eco": {"R": "main"}, "repo_info": info, "alerts": {}, "perms": {}, "runs": {"R": []},
               "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}}, "history": {"days": {}}, "unreleased": {}, "targets": {}, "errors": {}, "loading": "", "audits": None}
        a4 = sl.compute_snapshot(inp)["a4"]
        self.assertEqual(sorted(p["number"] for p in a4["dependabot"]), [1, 2])
        self.assertEqual(a4["other"], 1)
        only = sl.compute_snapshot({**inp, "cfg": {**sl.DEFAULTS, "dependency_bots": ["dependabot"]}})["a4"]
        self.assertEqual([p["number"] for p in only["dependabot"]], [2])

    def test_a_renovate_configuration_covers_the_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            for where in (".github/renovate.json", "renovate.json5", ".renovaterc"):
                base = Path(tmp) / where.replace("/", "_").replace(".", "_")
                (base / ".git").mkdir(parents=True)
                path = base / where
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
                scan = surface.scan_clone(base)
                self.assertFalse(scan["dependabot_yml"], where)
                self.assertTrue(scan["renovate_cfg"], where)
            bare = Path(tmp) / "bare"
            (bare / ".git").mkdir(parents=True)
            self.assertFalse(surface.scan_clone(bare)["renovate_cfg"])

    def test_the_coverage_row_does_not_name_a_bot_that_is_configured(self):
        import test_surface
        case = test_surface.SurfaceInTheSnapshot("test_every_section_finds_its_case")
        for key, expected in (({"dependabot_yml": False}, "Dependabot, CodeQL"), ({"dependabot_yml": False, "renovate_cfg": True}, "CodeQL"), ({"dependabot_yml": True}, "CodeQL")):
            inp = case.inp()
            inp["scans"]["R"].update(key)
            rows = {s["key"]: s["rows"] for s in surface.build(inp)["sections"]}
            self.assertEqual(rows["coverage"][0][2], expected, key)


class Linter(unittest.TestCase):
    def test_unpinned_uses_names_own_and_third_party_and_the_default_is_unchanged(self):
        got = found(WORKFLOW, settings())
        unpinned = [(line, kind, severity) for rule, line, kind, severity in got if rule == "unpinned_uses"]
        self.assertEqual(unpinned, [(9, "third_party", "warn"), (10, "own", "warn"), (11, "own", "warn"), (17, "third_party", "warn"), (19, "own", "warn")])

    def test_own_actions_can_be_lowered_or_hidden(self):
        info = [(l, k, s) for r, l, k, s in found(WORKFLOW, settings(unpinned_own="info")) if r == "unpinned_uses"]
        self.assertEqual(info, [(9, "third_party", "warn"), (10, "own", "info"), (11, "own", "info"), (17, "third_party", "warn"), (19, "own", "info")])
        gone = [(l, k) for r, l, k, s in found(WORKFLOW, settings(unpinned_own="ignore")) if r == "unpinned_uses"]
        self.assertEqual(gone, [(9, "third_party"), (17, "third_party")])

    def test_other_accounts_can_be_own(self):
        got = [(l, k) for r, l, k, s in found(WORKFLOW, settings(own_owners=["acme-org", "thirdparty"])) if r == "unpinned_uses"]
        self.assertIn((17, "own"), got)

    def test_without_a_configuration_nobody_is_own(self):
        cfg = lw.settings(None)
        self.assertEqual(cfg["rules"]["_own"], {"owners": [], "unpinned": "same"})
        self.assertTrue(all(k != "own" for r, l, k, s in found(WORKFLOW, cfg)))

    def test_the_optional_rules_are_off_by_default(self):
        names = {r for r, *_ in found(WORKFLOW, settings())}
        self.assertFalse(names & set(lw.OPTIONAL))
        self.assertTrue(all(not lw.settings(None)["rules"][r]["enabled"] for r in lw.OPTIONAL))

    def test_the_optional_rules_when_switched_on(self):
        cfg = settings(rules={r: {"enabled": True} for r in lw.OPTIONAL})
        got = found(WORKFLOW, cfg)
        self.assertIn(("no_timeout", 6, "", "warn"), got)      # build has no limit; test has one; call is a reusable workflow
        self.assertEqual([x for x in got if x[0] == "no_timeout"], [("no_timeout", 6, "", "warn")])
        self.assertEqual([x[1] for x in got if x[0] == "secrets_inherit"], [20])
        self.assertEqual([x[1] for x in got if x[0] == "own_action_main"], [10])      # thirdparty/lint@main is not an own action

    def test_permissions_top_is_about_the_top_of_the_file_only(self):
        per_job = WORKFLOW.replace("permissions:\n  contents: read\n", "").replace("  test:\n", "  test:\n    permissions:\n      contents: read\n")
        self.assertNotIn("permissions_top", {r for r, *_ in found(per_job, settings())})      # off by default
        on = settings(rules={"permissions_top": {"enabled": True}})
        self.assertEqual([x for x in found(per_job, on) if x[0] == "permissions_top"], [("permissions_top", 1, "", "info")])
        self.assertEqual([x for x in found(WORKFLOW, on) if x[0] == "permissions_top"], [])      # a block at the top: nothing to say
        none_at_all = WORKFLOW.replace("permissions:\n  contents: read\n", "")
        names = [x[0] for x in found(none_at_all, on)]
        self.assertIn("permissions", names)      # nothing anywhere is the older rule's finding
        self.assertNotIn("permissions_top", names)
        silenced = per_job.replace("name: CI", "# monitor-lint: ignore permissions_top because the jobs say it\nname: CI")
        self.assertEqual([x for x in found(silenced, on) if x[0] == "permissions_top"], [])
        sev = settings(rules={"permissions_top": {"enabled": True, "severity": "warn"}})
        self.assertEqual([x[3] for x in found(per_job, sev) if x[0] == "permissions_top"], ["warn"])

    def test_severity_and_silencing_follow_the_usual_rules(self):
        cfg = settings(rules={"secrets_inherit": {"enabled": True, "severity": "bad"}})
        self.assertEqual([x[3] for x in found(WORKFLOW, cfg) if x[0] == "secrets_inherit"], ["bad"])
        text = WORKFLOW.replace("    secrets: inherit", "    # monitor-lint: ignore secrets_inherit because the called workflow is ours\n    secrets: inherit")
        self.assertEqual([x for x in found(text, cfg) if x[0] == "secrets_inherit"], [])

    def test_the_report_of_workflow_hygiene_does_not_repeat_the_optional_rules(self):
        rules = [f["rule"] for f in reports.hygiene_findings(WORKFLOW, "ci.yml")]
        self.assertEqual(rules.count("no_timeout"), 1)      # its own rule, once
        self.assertNotIn("secrets_inherit", rules)

    def test_the_settings_page_knows_the_new_rules(self):
        for rule in lw.OPTIONAL:
            self.assertIn(f"lint.rules.{rule}.enabled", sa.FIELDS)
            if rule != "archived_action":      # that one only informs: it has no severity to choose
                self.assertIn(f"lint.rules.{rule}.severity", sa.FIELDS)
        self.assertTrue(sa.check_value("lint.unpinned_own", "ignore")[0])
        self.assertFalse(sa.check_value("lint.unpinned_own", "never")[0])
        self.assertTrue(sa.check_value("lint.own_owners", ["acme-org"])[0])
        self.assertTrue(sa.check_value("sentinel.dependency_bots", ["dependabot", "renovate"])[0])
        self.assertFalse(sa.check_value("sentinel.dependency_bots", ["a b"])[0])


if __name__ == "__main__":
    unittest.main()
