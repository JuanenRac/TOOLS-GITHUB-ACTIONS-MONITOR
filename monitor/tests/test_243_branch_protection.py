# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The protection of the default branch from the three public sources (the rules of the rulesets, `protected` and the classic `protection` of the branch), in the shapes measured on public repositories:
a branch protected only in the classic way shows no rule at all in `rules/branches`, the classic protection itself answers 403 without admin rights, and a big list can time out (504)."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402

GOOD_FILES = {"README.md": True, "LICENSE": True, "CHANGELOG.md": True, "SECURITY.md": True}
ADMIN = {"sha_pinning_required": True, "allowed_actions": "selected", "wf_disabled": []}
REQ = sl.DEFAULTS["required_files"]
EFFECTIVE = sl.hygiene_settings({"sentinel": {"hygiene": {"ruleset_mode": "effective"}}})

# shapes of the answer of GET branches/{default}: (repository, protected, classic protection object or None, rules of GET rules/branches/{default})
MEASURED = [
    ("curl/curl", True, {"enabled": True, "required_status_checks": {"enforcement_level": "non_admins", "contexts": ["build"]}}, []),
    ("openssl/openssl", True, {"enabled": True, "required_status_checks": {"enforcement_level": "everyone", "contexts": []}}, []),
    ("redis/redis", True, {"enabled": True, "required_status_checks": {"enforcement_level": "off", "contexts": []}}, []),
    ("tauri-apps/tauri", False, None, [{"type": "pull_request"}, {"type": "deletion"}]),
    ("bevyengine/bevy", True, {"enabled": True, "required_status_checks": {"enforcement_level": "non_admins"}}, [{"type": "merge_queue"}, {"type": "pull_request"}]),
    ("ripgrep/ripgrep", False, {"enabled": False, "required_status_checks": {"enforcement_level": "off", "contexts": []}}, []),
]


def info():
    return {"rulesets": [], "label_dependencies": True, "files": dict(GOOD_FILES), "license": "mit"}


def codes(items):
    return sorted({c for c, _ in items})


class Fetching(unittest.TestCase):
    def make(self, tmp, answers):
        def gh(*args, **kw):
            value = answers.get(args[1].split("?")[0], RuntimeError("HTTP 404: Not Found"))
            if isinstance(value, Exception):
                raise value
            return value

        ctx = {"gh": gh, "repos_fn": lambda: ["R"], "runs_fn": lambda: {}, "data_fn": lambda: {"rate": {"remaining": 4000, "limit": 5000}}, "eco_fn": lambda r: "main"}
        with mock.patch.object(sl, "CACHE_FILE", Path(tmp) / "c.json"), mock.patch.object(sl, "HISTORY_FILE", Path(tmp) / "h.json"):
            s = sl.Sentinel(ctx, {"sentinel": {"hygiene": {"ruleset_mode": "effective"}}})
        s.repo_info = {"R": {"branch": "main"}}
        return s

    def fetch(self, branch_answer, rules_answer):
        owner = sl.toolconfig.github_owner()
        with tempfile.TemporaryDirectory() as tmp:
            s = self.make(tmp, {f"repos/{owner}/R/branches/main": branch_answer, f"repos/{owner}/R/rules/branches/main": rules_answer})
            return s._fetch_branch_rules(owner, "R", "main")

    def test_the_classic_protection_is_read_from_the_same_answer_of_the_branch(self):
        for repo, protected, classic, rules in MEASURED:
            body = {"protected": protected}
            if classic is not None:
                body["protection"] = classic
            found = self.fetch(body, rules)
            self.assertEqual(found["protected"], protected, repo)
            self.assertEqual(found["rules"], [r["type"] for r in rules], repo)
            level = (classic or {}).get("required_status_checks", {}).get("enforcement_level")
            expected = bool((classic or {}).get("enabled")) or level not in (None, "", "off")
            if classic is None:
                self.assertNotIn("classic", found, repo)
            else:
                self.assertEqual(found["classic"], expected, repo)

    def test_an_answer_without_the_field_says_nothing(self):
        self.assertIsNone(self.fetch({}, [])["protected"])

    def test_a_timeout_or_a_refusal_leaves_the_source_unknown(self):
        found = self.fetch(RuntimeError("HTTP 504: Gateway Timeout"), RuntimeError("HTTP 403: Forbidden"))
        self.assertEqual(found, {"protected": None, "rules": None})


class Judging(unittest.TestCase):
    def state(self, found):
        return sl.hygiene_review(info(), {**ADMIN, "branch_rules": found}, REQ, EFFECTIVE)

    def test_the_classic_protection_alone_protects(self):
        problems, unknown = self.state({"protected": True, "rules": [], "classic": True})
        self.assertEqual((problems, unknown), ([], []))
        problems, unknown = self.state({"protected": None, "rules": [], "classic": True})      # the flag of the branch did not come, the protection object did
        self.assertEqual((problems, unknown), ([], []))

    def test_an_empty_list_of_rules_is_not_no_protection_by_itself(self):
        problems, unknown = self.state({"protected": None, "rules": []})
        self.assertEqual((codes(problems), codes(unknown)), ([], ["ruleset"]))
        problems, unknown = self.state({"protected": True, "rules": []})
        self.assertEqual((problems, unknown), ([], []))

    def test_a_branch_is_unprotected_only_when_the_sources_answered_and_none_protects(self):
        for found in ({"protected": False, "rules": []}, {"protected": False, "rules": ["creation"], "classic": False}, {"protected": False, "rules": [], "classic": False}):
            problems, unknown = self.state(found)
            self.assertEqual((codes(problems), codes(unknown)), (["ruleset"], []), found)

    def test_the_source_of_the_protection_is_named(self):
        cases = [({"protected": True, "rules": [], "classic": True}, "classic"), ({"protected": False, "rules": ["pull_request"]}, "ruleset"),
                 ({"protected": True, "rules": ["merge_queue"], "classic": True}, "both"), ({"protected": False, "rules": [], "classic": False}, "none"),
                 ({"protected": None, "rules": None}, None), ({"protected": None, "rules": ["creation"]}, None), (None, None), ("x", None)]
        for found, expected in cases:
            self.assertEqual(sl.protection_source(found), expected, found)

    def test_the_measured_repositories_are_judged_right(self):
        verdicts = {}
        for repo, protected, classic, rules in MEASURED:
            level = (classic or {}).get("required_status_checks", {}).get("enforcement_level")
            found = {"protected": protected, "rules": [r["type"] for r in rules]}
            if classic is not None:
                found["classic"] = bool(classic.get("enabled")) or level not in (None, "", "off")
            problems, unknown = self.state(found)
            verdicts[repo] = (codes(problems), codes(unknown), sl.protection_source(found))
        self.assertEqual(verdicts["curl/curl"], ([], [], "classic"))
        self.assertEqual(verdicts["openssl/openssl"], ([], [], "classic"))
        self.assertEqual(verdicts["redis/redis"], ([], [], "classic"))
        self.assertEqual(verdicts["tauri-apps/tauri"], ([], [], "ruleset"))
        self.assertEqual(verdicts["bevyengine/bevy"], ([], [], "both"))
        self.assertEqual(verdicts["ripgrep/ripgrep"], (["ruleset"], [], "none"))

    def test_the_hygiene_row_carries_the_source(self):
        from datetime import datetime, timezone
        repo = {"branch": "main", "pushed": None, "release": None, "vuln_total": 0, "vuln_sev": {}, "prs": [], **info()}
        cfg = dict(sl.DEFAULTS, hygiene=EFFECTIVE)
        perms = {"R": {**ADMIN, "at": 1, "branch_rules": {"protected": True, "rules": [], "classic": True}}, "S": {**ADMIN, "at": 1}}
        inp = {"now": datetime(2026, 11, 4, 12, tzinfo=timezone.utc), "today": "2026-11-04", "cfg": cfg, "repos": ["R", "S"], "eco": {"R": "main", "S": "main"}, "repo_info": {"R": repo, "S": dict(repo)},
               "alerts": {}, "perms": perms, "runs": {"R": [], "S": []}, "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}}, "history": {"days": {}}, "unreleased": {},
               "targets": {}, "errors": {}, "loading": "", "audits": None}
        rows = {r["repo"]: r for r in sl.compute_snapshot(inp)["a6"]["rows"]}
        self.assertEqual((rows["R"]["protection"], rows["S"]["protection"]), ("classic", None))


if __name__ == "__main__":
    unittest.main()
