# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The posture checks against a made-up GitHub: each weakness is found, what GitHub refuses is "not checked" and never fine, the releases are compared with what was seen before, the profiles and the
kinds of project narrow the list, nothing but GET exists, and nothing is read while the feature is off. Invented names, no real calls."""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.families.posture import catalogue, checks, engine  # noqa: E402
from github_actions_monitor.families.posture.checks import Unread  # noqa: E402

NOW = 1_800_000_000.0
OLD = "2020-01-01T00:00:00Z"


class FakeGitHub:
    """{endpoint without the query: answer}; an endpoint that is not here is a 404, a string answer is the reason of a refusal."""

    def __init__(self, answers):
        self.answers, self.asked = dict(answers), []

    def __call__(self, endpoint):
        self.asked.append(endpoint)
        key = endpoint.partition("?")[0]
        if key not in self.answers:
            raise Unread("missing")
        value = self.answers[key]
        if isinstance(value, str):
            raise Unread(value)
        return value


def weak_repo(base="repos/acme/app"):
    return {
        base: {"default_branch": "main", "private": False, "security_and_analysis": {"secret_scanning": {"status": "disabled"}, "secret_scanning_push_protection": {"status": "disabled"}}},
        f"{base}/hooks": [{"active": True, "config": {"url": "http://hooks.example.org/path?k=abc", "insecure_ssl": "1"}}],
        f"{base}/actions/permissions": {"enabled": True, "allowed_actions": "all", "sha_pinning_required": False},
        f"{base}/actions/permissions/workflow": {"default_workflow_permissions": "write", "can_approve_pull_request_reviews": True},
        f"{base}/actions/permissions/fork-pr-contributor-approval": {"approval_policy": "first_time_contributors_new_to_github"},
        f"{base}/branches": [{"name": "main"}, {"name": "release/1.0"}, {"name": "topic"}],
        f"{base}/keys": [{"title": "ci", "read_only": False, "created_at": OLD}],
        f"{base}/actions/secrets": {"secrets": [{"name": "OLD_ONE", "updated_at": OLD}]},
        f"{base}/releases": [],
    }


def org(base="orgs/acme"):
    return {base: {"two_factor_requirement_enabled": False, "default_repository_permission": "write", "members_can_create_public_repositories": True},
            f"{base}/hooks": [], f"{base}/actions/secrets": {"secrets": []},
            f"{base}/installations": {"installations": [{"app_slug": "helper", "repository_selection": "all", "permissions": {"contents": "write", "metadata": "read"}}]}}


def config(**extra):
    return {"posture": dict({"enabled": True, "profile": "strict"}, **extra)}


class Checks(unittest.TestCase):
    def setUp(self):
        engine.state_file().unlink(missing_ok=True)
        self.addCleanup(lambda: engine.state_file().unlink(missing_ok=True))

    def found(self, report, repo="app"):
        return {f["check"] for r in report["repos"] if r["repo"] == repo for f in r["findings"]}

    def test_a_weak_repository_and_organization_are_found(self):
        github = FakeGitHub({**weak_repo(), **org()})
        self.assertEqual(engine.refresh(config(), "acme", ["app"], get=github, now=NOW), 1)
        report = engine.report(config())
        self.assertEqual(self.found(report), {"webhook.no_secret", "webhook.plain_http", "webhook.tls_off", "actions.all_allowed", "actions.sha_not_required", "actions.token_write", "actions.approves_prs",
                                              "actions.fork_approval", "scan.no_credentials", "scan.no_push_protection", "scan.no_dependency_alerts", "scan.no_code", "repo.no_policy", "repo.no_update_tool",
                                              "branch.unprotected", "branch.release_unprotected", "deploy.write", "deploy.old", "stored.old"})
        self.assertEqual({f["check"] for f in report["org"]["findings"]}, {"org.no_two_factor", "org.default_write", "org.public_creation", "org.app_broad"})
        self.assertNotIn("k=abc", str(report), "the address of a hook is never kept")
        self.assertEqual(report["repos"][0]["maturity"]["passed"], 0)
        self.assertTrue(report["owasp"] and all(r["id"].startswith("CICD-SEC-") for r in report["owasp"]))
        self.assertEqual(len(report["history"]), 1)
        self.assertTrue(engine.text_lines(report))

    def test_what_github_refuses_is_not_checked_and_never_fine(self):
        answers = weak_repo()
        answers["repos/acme/app/hooks"] = "forbidden"
        answers["repos/acme/app/keys"] = "forbidden"
        answers["repos/acme/app"] = {"default_branch": "main", "private": True}      # no security_and_analysis without admin rights
        engine.refresh(config(org_checks=False), "acme", ["app"], get=FakeGitHub(answers), now=NOW)
        report = engine.report(config())
        self.assertEqual(report["repos"][0]["unread"], {"hooks": "forbidden", "scan": "forbidden", "deploy": "forbidden"})
        self.assertIsNotNone(report["repos"][0]["maturity"])
        self.assertTrue([p for p in report["permissions"] if p["group"] == "hooks"][0]["refused"])
        self.assertEqual(report["not_checked"], 3)

    def test_a_finding_that_cannot_be_read_again_is_not_taken_as_solved(self):
        github = FakeGitHub(weak_repo())
        engine.refresh(config(org_checks=False), "acme", ["app"], get=github, now=NOW)
        github.answers["repos/acme/app/keys"] = "failed"
        engine.refresh(config(org_checks=False), "acme", ["app"], get=github, now=NOW + 200000)
        self.assertIn("deploy.write", self.found(engine.report(config())))

    def test_the_protected_branch_that_somebody_can_skip(self):
        base = "repos/acme/app"
        answers = {base: {"default_branch": "main"}, f"{base}/rules/branches/main": [{"type": "pull_request", "ruleset_id": 7, "parameters": {"required_approving_review_count": 1}}],
                   f"{base}/rulesets/7": {"name": "main", "bypass_actors": [{"actor_type": "RepositoryRole"}]},
                   f"{base}/pulls": [{"number": 4, "merged_at": OLD}, {"number": 3, "merged_at": None}], f"{base}/pulls/4/reviews": [{"state": "COMMENTED"}]}
        cfg = engine.settings(config(review_sample=5, release_branches=[]))
        ctx = {"cfg": cfg, "now": NOW, "repo_info": answers[base], "memory": {}}
        self.assertEqual([f["check"] for f in checks.branch(FakeGitHub(answers), base, ctx)], ["branch.bypass"])
        self.assertEqual([f["item"] for f in checks.reviews(FakeGitHub(answers), base, ctx)], ["#4"])

    def test_releases_are_compared_with_what_was_seen(self):
        base = "repos/acme/app"
        release = {"tag_name": "v1", "published_at": "2027-01-09T23:00:00Z", "assets": [{"id": 1, "name": "a.zip", "size": 5}, {"id": 2, "name": "b.zip", "size": 6}]}
        github = FakeGitHub({f"{base}/releases": [release], f"{base}/git/ref/tags/v1": {"object": {"sha": "a" * 40}}})
        ctx = {"cfg": engine.settings(config(release_window="1-5 07-19")), "now": NOW, "repo_info": {}, "memory": {}}
        self.assertEqual(checks.releases(github, base, ctx), [], "the first read only remembers")
        github.answers[f"{base}/git/ref/tags/v1"] = {"object": {"sha": "b" * 40}}
        github.answers[f"{base}/releases"] = [dict(release, assets=[{"id": 9, "name": "a.zip", "size": 5}]), {"tag_name": "v2", "published_at": "2027-01-09T23:00:00Z", "assets": []}]
        found = sorted(f["check"] for f in checks.releases(github, base, ctx))
        self.assertEqual(found, ["release.asset_removed", "release.asset_replaced", "release.outside_window", "release.tag_moved"])
        self.assertEqual(sorted(f["check"] for f in checks.releases(github, base, ctx)), found, "it stays until someone looks")
        self.assertTrue(checks.in_window("", 0) and checks.in_window("nonsense", NOW))

    def test_hardening_is_what_ran(self):
        base = "repos/acme/app"
        run = {f"{base}/actions/runs": {"workflow_runs": [{"id": 5, "name": "ci"}]}, f"{base}/actions/runs/5/jobs": {"jobs": [{"steps": [{"name": "Harden Runner"}]}]}}
        ctx = {"cfg": engine.settings(config(runner_runs=3)), "now": NOW, "repo_info": {}, "memory": {}}
        self.assertEqual(checks.runner(FakeGitHub(run), base, ctx), [])
        run[f"{base}/actions/runs/5/jobs"] = {"jobs": [{"steps": [{"name": "Build"}]}]}
        self.assertEqual([f["check"] for f in checks.runner(FakeGitHub(run), base, ctx)], ["runner.coverage_lost"])

    def test_the_audit_log_is_only_read_when_asked(self):
        github = FakeGitHub({"orgs/acme/audit-log": [{"action": "org.disable_two_factor_requirement", "@timestamp": (NOW - 60) * 1000, "actor": "someone"}, {"action": "repo.create", "@timestamp": NOW * 1000}]})
        ctx = {"cfg": engine.settings(config()), "now": NOW, "repo_info": {}, "memory": {}}
        self.assertEqual(checks.audit(github, "orgs/acme", ctx), [])
        self.assertEqual(github.asked, [])
        ctx["cfg"] = engine.settings(config(audit_log=True))
        self.assertEqual([f["check"] for f in checks.audit(github, "orgs/acme", ctx)], ["org.settings_changed"])

    def test_profiles_kinds_and_skips_narrow_the_list(self):
        self.assertFalse(catalogue.wanted("scan.no_code", "basic"))
        self.assertTrue(catalogue.wanted("scan.no_code", "strict"))
        self.assertFalse(catalogue.wanted("scan.no_code", "strict", "internal"))
        self.assertFalse(catalogue.wanted("deploy.write", skip=["deploy.write"]))
        self.assertEqual(engine.kind_of("demo-x", engine.settings(config(types=["demo-*=sandbox"]))), "sandbox")
        engine.refresh(config(profile="basic", org_checks=False, skip=["deploy.write"]), "acme", ["app"], get=FakeGitHub(weak_repo()), now=NOW)
        found = self.found(engine.report(config()))
        self.assertNotIn("deploy.write", found)
        self.assertNotIn("actions.sha_not_required", found)
        self.assertIn("actions.token_write", found)

    def test_a_few_repositories_per_cycle_and_not_again_too_soon(self):
        github = FakeGitHub({f"repos/acme/r{i}": {"default_branch": "main", "archived": True} for i in range(5)})
        cfg = config(repos_per_cycle=2, org_checks=False)
        names = [f"r{i}" for i in range(5)]
        self.assertEqual([engine.refresh(cfg, "acme", names, get=github, now=NOW + n) for n in range(4)], [2, 2, 1, 0])
        self.assertEqual({r["skipped"] for r in engine.report(cfg)["repos"]}, {"archived"})

    def test_the_allowance_running_out_stops_without_inventing(self):
        engine.refresh(config(org_checks=False), "acme", ["app"], get=FakeGitHub({"repos/acme/app": "rate_limited"}), now=NOW)
        self.assertEqual(engine.report(config())["repos"], [])

    def test_off_means_no_read_and_alerts_group_by_check(self):
        github = FakeGitHub(weak_repo())
        for off in ({}, {"posture": {"enabled": False}}, dict(config(), airgapped=True)):
            self.assertEqual(engine.refresh(off, "acme", ["app"], get=github, now=NOW), 0)
            self.assertIsNone(engine.tick(off, {"repos": ["app"]}))
            self.assertEqual(engine.alerts(off), [])
        self.assertEqual(github.asked, [])
        engine.refresh(config(org_checks=False), "acme", ["app"], get=github, now=NOW)
        alerts = engine.alerts(config())
        self.assertEqual(len(alerts), len({a["id"] for a in alerts}))
        self.assertTrue(all(a["code"].startswith("posture.") and a["sentinel"] == "security" and a["repo"] == "app" for a in alerts))
        self.assertEqual(engine.alerts(config(alerts=False)), [])
        self.assertEqual(engine.names_of({"repos": ["acme/app", {"name": "lib"}, "..", "a b"]}), ["app", "lib"])

    def test_every_check_has_a_text_a_reference_and_a_permission(self):
        for check, (level, profile, group, owasp, cis) in catalogue.CHECKS.items():
            self.assertIn(level, ("info", "warning", "error"), check)
            self.assertIn(group, catalogue.PERMISSIONS, check)
            self.assertIn(owasp, catalogue.OWASP, check)
            key = "ui.posture.c." + check.replace(".", "_")
            self.assertNotEqual(i18n.t(key), key, check)

    def test_the_reader_turns_every_refusal_into_not_checked(self):
        from github_actions_monitor.app import actions_monitor
        for message, reason in (("HTTP 404: Not Found", "missing"), ("HTTP 403: Forbidden", "forbidden"), ("API rate limit exceeded (403)", "rate_limited"), ("boom", "failed")):
            with mock.patch.object(actions_monitor, "gh_read", side_effect=RuntimeError(message)):
                with self.assertRaises(Unread) as caught:
                    engine.reader()("repos/acme/app")
                self.assertEqual(caught.exception.reason, reason)


if __name__ == "__main__":
    unittest.main()
