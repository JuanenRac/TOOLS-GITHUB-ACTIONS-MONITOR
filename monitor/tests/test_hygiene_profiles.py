# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A6 hygiene without the conventions of one owner: the name of the ruleset, the licence file and the community files are settings, the default branch can be judged by the rules
GitHub reports as in force, and what a token cannot know is "not evaluable" (never green, never a warning). Synthetic repositories, a fake gh, no network."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import settings_api as sa  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402

GOOD_FILES = {"README.md": True, "LICENSE": True, "CHANGELOG.md": True, "SECURITY.md": True}
ADMIN = {"sha_pinning_required": True, "allowed_actions": "selected", "wf_disabled": []}


def info(**over):
    base = {"rulesets": [{"name": "protect-main", "enforcement": "ACTIVE"}], "label_dependencies": True, "files": dict(GOOD_FILES), "license": "mit"}
    base.update(over)
    return base


def codes(problems):
    return sorted({c for c, _ in problems})


def hyg(**over):
    return sl.hygiene_settings({"sentinel": {"hygiene": over}})


REQ = sl.DEFAULTS["required_files"]


class Defaults(unittest.TestCase):
    def test_the_default_judges_the_rules_in_force_and_the_old_rule_is_the_name_mode(self):
        self.assertEqual(sl.hygiene_settings({}), {"ruleset_mode": "effective", "ruleset_names": ["protect-main"], "skip": [], "community_fallback": False})
        problems, unknown = sl.hygiene_review(info(rulesets=[{"name": "Main protection", "enforcement": "ACTIVE"}]), ADMIN, REQ, hyg(ruleset_mode="name"))
        self.assertEqual((codes(problems), unknown), (["ruleset"], []))
        # by default the name of the ruleset does not matter: a branch protected in any way is protected, and nothing is said before the rules were read
        self.assertEqual(sl.hygiene_review(info(rulesets=[]), ADMIN, REQ), ([], []))
        found = {"protected": True, "rules": [], "classic": True}
        self.assertEqual(sl.hygiene_review(info(rulesets=[]), {**ADMIN, "branch_rules": found}, REQ), ([], []))

    def test_a_bad_value_falls_back_to_the_default_of_that_key_only(self):
        got = sl.hygiene_settings({"sentinel": {"hygiene": {"ruleset_mode": "banana", "ruleset_names": [], "skip": ["file", "nonsense"], "community_fallback": "yes"}}})
        self.assertEqual(got, {"ruleset_mode": "effective", "ruleset_names": ["protect-main"], "skip": ["file"], "community_fallback": False})

    def test_sentinel_config_carries_the_block(self):
        self.assertEqual(sl.sentinel_config({"sentinel": {"hygiene": {"ruleset_mode": "effective"}}})["hygiene"]["ruleset_mode"], "effective")
        self.assertEqual(sl.sentinel_config({})["hygiene"]["ruleset_mode"], "effective")


class RulesetByNameOrByRules(unittest.TestCase):
    def test_a_configurable_name_or_pattern(self):
        repo = info(rulesets=[{"name": "Main-Branch Protection", "enforcement": "ACTIVE"}])
        self.assertEqual(codes(sl.hygiene_problems(repo, ADMIN, REQ, hyg(ruleset_mode="name", ruleset_names=["main-*"]))), [])
        self.assertEqual(codes(sl.hygiene_problems(repo, ADMIN, REQ, hyg(ruleset_mode="name", ruleset_names=["release-*"]))), ["ruleset"])
        evaluate = info(rulesets=[{"name": "protect-main", "enforcement": "EVALUATE"}])
        self.assertEqual(codes(sl.hygiene_problems(evaluate, ADMIN, REQ, hyg(ruleset_mode="name"))), ["ruleset"])      # only an ACTIVE ruleset counts

    def test_effective_rules_do_not_depend_on_the_name(self):
        repo = info(rulesets=[])
        for found, expected in (({"protected": None, "rules": ["pull_request", "deletion"]}, ([], [])),
                                ({"protected": True, "rules": None}, ([], [])),
                                ({"protected": False, "rules": []}, (["ruleset"], [])),
                                ({"protected": False, "rules": ["creation"]}, (["ruleset"], [])),      # a rule that only restricts creating the branch does not protect it
                                ({"protected": None, "rules": None}, ([], ["ruleset"]))):      # GitHub did not answer: not evaluable
            problems, unknown = sl.hygiene_review(repo, {**ADMIN, "branch_rules": found}, REQ, hyg(ruleset_mode="effective"))
            self.assertEqual((codes(problems), codes(unknown)), expected, found)

    def test_effective_mode_waits_for_the_first_read_and_off_skips(self):
        self.assertEqual(sl.hygiene_review(info(rulesets=[]), ADMIN, REQ, hyg(ruleset_mode="effective")), ([], []))
        self.assertEqual(codes(sl.hygiene_problems(info(rulesets=[]), ADMIN, REQ, hyg(ruleset_mode="off"))), [])

    def test_skip_leaves_a_check_out(self):
        bad = info(rulesets=[], label_dependencies=False, files={})
        full = codes(sl.hygiene_problems(bad, {"sha_pinning_required": False, "allowed_actions": "all", "wf_disabled": ["Nightly"]}, REQ, hyg(ruleset_mode="name")))
        self.assertEqual(full, ["allowed", "file", "label", "ruleset", "schedule", "sha"])
        left = codes(sl.hygiene_problems(bad, {"sha_pinning_required": False, "allowed_actions": "all", "wf_disabled": ["Nightly"]}, REQ, hyg(ruleset_mode="name", skip=["label", "sha", "schedule"])))
        self.assertEqual(left, ["allowed", "file", "ruleset"])


class Files(unittest.TestCase):
    def test_other_licence_names_and_the_licence_github_recognised(self):
        for name in ("LICENSE-MIT", "LICENSE-APACHE", "COPYING", "LICENSE.txt"):
            repo = info(files={"README.md": True, "CHANGELOG.md": True, "SECURITY.md": True, name: True}, license=None)
            self.assertEqual(codes(sl.hygiene_problems(repo, ADMIN, REQ)), [], name)
        odd = info(files={"README.md": True, "CHANGELOG.md": True, "SECURITY.md": True}, license="apache-2.0")      # a file with any name that GitHub detects as the licence
        self.assertEqual(codes(sl.hygiene_problems(odd, ADMIN, REQ)), [])
        none = info(files={"README.md": True, "CHANGELOG.md": True, "SECURITY.md": True}, license=None)
        self.assertEqual(codes(sl.hygiene_problems(none, ADMIN, REQ)), ["file"])

    def test_the_licence_alternatives_are_asked_to_github(self):
        query = sl.repo_query(sorted({n for g in REQ for n in g}))
        self.assertIn("licenseInfo{key}", query)
        node = {"name": "R", "licenseInfo": {"key": "mit"}, "f0": None}
        self.assertEqual(sl.parse_repo_node(node, ["README.md"])["license"], "mit")
        self.assertIsNone(sl.parse_repo_node({"name": "R", "licenseInfo": None}, [])["license"])

    def test_community_profile_and_organisation_defaults_only_when_asked(self):
        repo = info(files={"README.md": True, "CHANGELOG.md": True}, license=None)
        perms = {**ADMIN, "community": {"readme": True, "license": True, "contributing": False, "code_of_conduct": False}}
        self.assertEqual(codes(sl.hygiene_problems(repo, perms, REQ, hyg(), ["SECURITY.md"])), ["file"])      # off: nothing is borrowed
        problems, unknown = sl.hygiene_review(repo, perms, REQ, hyg(community_fallback=True), ["SECURITY.md"])
        self.assertEqual((problems, unknown), ([], []))      # licence from the profile, SECURITY.md from the .github repository

    def test_a_source_that_failed_is_not_evaluable_not_missing(self):
        repo = info(files={"README.md": True, "CHANGELOG.md": True}, license=None)
        problems, unknown = sl.hygiene_review(repo, {**ADMIN, "community": None}, REQ, hyg(community_fallback=True), [])
        self.assertEqual(problems, [])
        self.assertEqual(len(unknown), 2)      # LICENSE and SECURITY.md may come from a source that could not be read
        problems, unknown = sl.hygiene_review(repo, {**ADMIN, "community": {"license": False}}, REQ, hyg(community_fallback=True), None)
        self.assertEqual(unknown and codes(unknown), ["file"])


class NotEvaluable(unittest.TestCase):
    def test_a_token_without_admin_rights_is_not_a_warning(self):
        problems, unknown = sl.hygiene_review(info(), {"denied": True, "wf_disabled": [], "at": 1}, REQ)
        self.assertEqual((problems, codes(unknown)), ([], ["allowed", "sha"]))

    def test_an_answer_without_the_field_is_not_evaluable(self):
        problems, unknown = sl.hygiene_review(info(), {"allowed_actions": "selected", "sha_pinning_required": None, "wf_disabled": []}, REQ)
        self.assertEqual((problems, codes(unknown)), ([], ["sha"]))
        self.assertEqual(codes(sl.hygiene_review(info(), {**ADMIN, "wf_error": True}, REQ)[1]), ["schedule"])

    def test_the_panel_is_neither_green_nor_a_warning(self):
        now = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
        repo = {"branch": "main", "pushed": None, "release": None, "vuln_total": 0, "vuln_sev": {}, "prs": [], **info()}
        inp = {"now": now, "today": "2026-11-04", "cfg": sl.DEFAULTS, "repos": ["R"], "eco": {"R": "main"}, "repo_info": {"R": repo}, "alerts": {}, "perms": {"R": {"denied": True, "at": 1}},
               "runs": {"R": []}, "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}}, "history": {"days": {}}, "unreleased": {}, "targets": {}, "errors": {},
               "loading": "", "audits": None}
        a6 = sl.compute_snapshot(inp)["a6"]
        self.assertEqual((a6["level"], a6["unknown"], a6["pending"]), ("unknown", 1, 0))
        self.assertEqual(a6["rows"][0]["problems"], [])
        self.assertEqual(sorted(u["code"] for u in a6["rows"][0]["unknown"]), ["allowed", "sha"])


class Fetching(unittest.TestCase):
    def make(self, tmp, answers, config):
        calls = []

        def gh(*args, **kw):
            calls.append(args[1])
            value = answers.get(args[1].split("?")[0], RuntimeError("HTTP 404: Not Found"))
            if isinstance(value, Exception):
                raise value
            return value

        ctx = {"gh": gh, "repos_fn": lambda: ["R"], "runs_fn": lambda: {}, "data_fn": lambda: {"rate": {"remaining": 4000, "limit": 5000}}, "eco_fn": lambda r: "main"}
        with mock.patch.object(sl, "CACHE_FILE", Path(tmp) / "c.json"), mock.patch.object(sl, "HISTORY_FILE", Path(tmp) / "h.json"):
            s = sl.Sentinel(ctx, {"sentinel": config})
        s.repo_info = {"R": {"branch": "release/1.x"}}
        return s, calls

    def test_a_refused_read_is_remembered_as_not_evaluable(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = sl.toolconfig.github_owner()
            s, _ = self.make(tmp, {f"repos/{owner}/R/actions/permissions": RuntimeError("HTTP 403: Must have admin rights to Repository."),
                                   f"repos/{owner}/R/actions/workflows": {"workflows": [{"name": "Nightly", "state": "disabled_inactivity"}]}}, {})
            repo, res = s._fetch_perms("R")
        self.assertTrue(res["denied"])
        self.assertEqual(res["wf_disabled"], ["Nightly"])
        self.assertNotIn("error", res)

    def test_a_network_error_is_still_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = sl.toolconfig.github_owner()
            s, _ = self.make(tmp, {f"repos/{owner}/R/actions/permissions": RuntimeError("connection reset")}, {})
            repo, res = s._fetch_perms("R")      # a failure is written down too (asked again in ten minutes, after the repositories never read), not forgotten
            self.assertEqual((repo, res["error"], "allowed_actions" in res), ("R", "connection reset", False))
            self.assertLess(res["at"], __import__("time").time() - s.cfg["hygiene_seconds"] + 700)

    def test_effective_rules_are_read_from_the_public_endpoints_with_the_branch_quoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = sl.toolconfig.github_owner()
            s, calls = self.make(tmp, {f"repos/{owner}/R/actions/permissions": {"allowed_actions": "all", "sha_pinning_required": False},
                                       f"repos/{owner}/R/actions/workflows": {"workflows": []},
                                       f"repos/{owner}/R/branches/release%2F1.x": {"protected": False},
                                       f"repos/{owner}/R/rules/branches/release%2F1.x": [{"type": "pull_request"}, {"type": "deletion"}]},
                                  {"hygiene": {"ruleset_mode": "effective"}})
            repo, res = s._fetch_perms("R")
        self.assertEqual(res["branch_rules"], {"protected": False, "rules": ["pull_request", "deletion"]})
        self.assertTrue(any("rules/branches/release%2F1.x" in c for c in calls))

    def test_the_community_files_cost_nothing_when_the_fallback_is_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = sl.toolconfig.github_owner()
            answers = {f"repos/{owner}/R/actions/permissions": {"allowed_actions": "selected", "sha_pinning_required": True}, f"repos/{owner}/R/actions/workflows": {"workflows": []},
                       f"repos/{owner}/R/community/profile": {"files": {"license": {"key": "mit"}, "readme": {"url": "x"}}}}
            s, calls = self.make(tmp, answers, {})
            self.assertNotIn("community", s._fetch_perms("R")[1])
            self.assertFalse(any("community" in c for c in calls))
            s2, _ = self.make(tmp, answers, {"hygiene": {"community_fallback": True}})
            self.assertEqual(s2._fetch_perms("R")[1]["community"], {"readme": True, "license": True, "contributing": False, "code_of_conduct": False})

    def test_the_account_defaults_repository_is_read_once_and_a_missing_one_means_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = sl.toolconfig.github_owner()
            s, calls = self.make(tmp, {f"repos/{owner}/.github/git/trees/HEAD": {"tree": [{"path": "SECURITY.md", "type": "blob"}, {"path": "docs", "type": "tree"}]}},
                                 {"hygiene": {"community_fallback": True}})
            self.assertTrue(s._org_files_tick())
            self.assertEqual(s.org_files["names"], ["SECURITY.md"])
            self.assertFalse(s._org_files_tick())      # inside the period: no second call
            self.assertEqual(len(calls), 1)
            off, _ = self.make(tmp, {}, {})
            self.assertFalse(off._org_files_tick())
            gone, _ = self.make(tmp, {}, {"hygiene": {"community_fallback": True}})
            gone._org_files_tick()
            self.assertEqual(gone.org_files["names"], [])      # 404: the account has no .github repository


class SettingsPage(unittest.TestCase):
    def test_the_new_settings_are_validated(self):
        self.assertTrue(sa.check_value("sentinel.hygiene.ruleset_mode", "effective")[0])
        self.assertFalse(sa.check_value("sentinel.hygiene.ruleset_mode", "anything")[0])
        self.assertTrue(sa.check_value("sentinel.hygiene.ruleset_names", ["Protect main", "main-*"])[0])
        self.assertFalse(sa.check_value("sentinel.hygiene.ruleset_names", [])[0])
        self.assertFalse(sa.check_value("sentinel.hygiene.ruleset_names", ["a;b"])[0])
        self.assertTrue(sa.check_value("sentinel.hygiene.skip", ["label", "sha"])[0])
        self.assertFalse(sa.check_value("sentinel.hygiene.skip", ["whatever"])[0])
        self.assertTrue(sa.check_value("sentinel.hygiene.community_fallback", True)[0])


if __name__ == "__main__":
    unittest.main()
