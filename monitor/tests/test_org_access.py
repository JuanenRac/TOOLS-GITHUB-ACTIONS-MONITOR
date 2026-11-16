# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Organizations: why a read comes back empty (SSO not authorised, missing scope, private repositories the login cannot see, allowance spent) and what the account will cost in reads an hour.
Fake `gh` answers with real header layouts, no network."""
import json
import unittest
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.cli import doctor  # noqa: E402
from github_actions_monitor.integrations import access_diag as ad  # noqa: E402


def answer(status, headers=None, body=None):
    lines = [f"HTTP/2.0 {status} X"] + [f"{k}: {v}" for k, v in (headers or {}).items()]
    return (0 if status < 400 else 1), "\n".join(lines) + "\n\n" + json.dumps(body if body is not None else {}), ""


def gh(table):
    """A fake runner: `table` maps the endpoint (the last argument) to (code, stdout, stderr)."""
    def runner(args, timeout=20):
        return table.get(args[-1], (1, "", "gh: Not Found (HTTP 404)"))
    return runner


CLASSIC = {"X-OAuth-Scopes": "repo, read:org"}


class Diagnose(unittest.TestCase):
    def test_the_text_of_a_failed_read_gives_its_cause(self):
        cases = {"gh: Resource protected by organization SAML enforcement. You must grant your Personal Access token access to this organization. (HTTP 403)": "sso",
                 "gh: API rate limit exceeded for user ID 1. (HTTP 403)": "rate_limited", "gh: Bad credentials (HTTP 401)": "auth", "gh: Resource not accessible by personal access token (HTTP 403)": "scope",
                 "gh: Not Found (HTTP 404)": "not_found", "gh: Forbidden (HTTP 403)": "forbidden", "dial tcp: i/o timeout": "network", "": "unknown"}
        for text, cause in cases.items():
            self.assertEqual(ad.diagnose(text), cause, text)
            self.assertIn(cause, ad.CAUSES)

    def test_the_headers_of_an_answer_are_read_and_a_missing_header_is_not_guessed(self):
        status, headers, body = ad.parse_response("HTTP/2.0 200 OK\r\nX-OAuth-Scopes: repo, read:org\r\nX-GitHub-SSO: partial-results; organizations=123\r\n\r\n{\"a\": 1}")
        self.assertEqual((status, ad.scopes_of(headers), ad.sso_partial(headers), json.loads(body)), (200, ["read:org", "repo"], True, {"a": 1}))
        self.assertIsNone(ad.scopes_of({}))
        self.assertEqual(ad.parse_response("{\"a\": 1}")[0], None)


class Probe(unittest.TestCase):
    ME = answer(200, CLASSIC, {"login": "alice"})

    def test_a_complete_login_is_ok_and_says_its_scopes(self):
        found = ad.probe(gh({"user": self.ME, "orgs/acme": answer(200, {}, {"public_repos": 10, "total_private_repos": 90}), "orgs/acme/repos?type=all&per_page=1": answer(200, {}, [])}), "acme")
        self.assertEqual((found["cause"], found["owner_kind"], found["repos"]), ("", "organization", 100))
        self.assertEqual(ad.result(found), ("ok", "alice: read:org, repo"))

    def test_sso_that_is_not_authorised_is_named_on_the_organization(self):
        sso = (1, "", "gh: Resource protected by organization SAML enforcement. You must grant your Personal Access token access to this organization. (HTTP 403)")
        found = ad.probe(gh({"user": self.ME, "orgs/acme": sso}), "acme")
        self.assertEqual(found["cause"], "sso")
        self.assertEqual(ad.result(found)[0], "warn")
        self.assertIn("sso", ad.result(found)[1])

    def test_partial_results_say_that_private_repositories_are_hidden_instead_of_a_silent_short_list(self):
        listing = answer(200, {"X-GitHub-SSO": "partial-results; organizations=1"}, [])
        found = ad.probe(gh({"user": self.ME, "orgs/acme": answer(200, {}, {"public_repos": 5}), "orgs/acme/repos?type=all&per_page=1": listing}), "acme")
        status, detail = ad.result(found)
        self.assertEqual((found["cause"], found["partial"], status), ("sso", True, "warn"))
        self.assertIn("private repositories", detail)

    def test_a_missing_scope_is_named(self):
        me = answer(200, {"X-OAuth-Scopes": "public_repo"}, {"login": "alice"})
        found = ad.probe(gh({"user": me, "orgs/acme": answer(200, {}, {}), "orgs/acme/repos?type=all&per_page=1": answer(200, {}, [])}), "acme")
        self.assertEqual(ad.result(found), ("warn", "alice: missing scope repo, read:org"))

    def test_a_fine_grained_token_has_no_scopes_to_read_and_the_result_says_so(self):
        found = ad.probe(gh({"user": answer(200, {}, {"login": "alice"}), "users/alice": answer(200, {}, {"public_repos": 3}), "users/alice/repos?per_page=1": answer(200, {}, [])}), "")
        self.assertEqual(found["owner_kind"], "user")
        self.assertIn("fine-grained", ad.result(found)[1])

    def test_a_refused_login_fails_and_an_unknown_account_is_not_found(self):
        self.assertEqual(ad.result(ad.probe(gh({"user": (1, "", "gh: Bad credentials (HTTP 401)")}), "acme")), ("fail", "auth"))
        found = ad.probe(gh({"user": self.ME}), "ghost")
        self.assertEqual((found["cause"], ad.result(found)[0]), ("not_found", "warn"))

    def test_an_answer_without_headers_is_not_judged(self):
        found = ad.probe(lambda args, timeout=20: (0, json.dumps({"resources": {}}), ""), "acme")
        self.assertEqual(ad.result(found), ("ok", "not checked"))


class Estimate(unittest.TestCase):
    def test_it_grows_with_the_repositories_and_names_its_terms(self):
        small, big = ad.estimate({}, 10), ad.estimate({}, 500)
        self.assertLess(small["calls_per_hour"], big["calls_per_hour"])
        self.assertEqual([label for label, _ in big["terms"]], ["runs", "sentinel"])
        self.assertEqual(big["limit"], 5000)

    def test_a_big_account_is_tight_or_over_and_a_small_one_is_fine(self):
        self.assertEqual(ad.estimate({}, 5)["level"], "ok")
        self.assertIn(ad.estimate({}, 2000)["level"], ("tight", "over"))

    def test_the_settings_move_the_estimate(self):
        slow = ad.estimate({"refresh_seconds": 600, "cold_refresh_seconds": 7200}, 300)["calls_per_hour"]
        self.assertLess(slow, ad.estimate({}, 300)["calls_per_hour"])

    def test_reading_workflow_files_without_a_clone_adds_a_capped_term_only_when_asked(self):
        self.assertNotIn("workflow files", [label for label, _ in ad.estimate({}, 300)["terms"]])
        terms = dict(ad.estimate({"lint": {"source": "auto"}}, 300)["terms"])
        self.assertIn("workflow files", terms)
        self.assertLessEqual(terms["workflow files"], 20 * 3600 / 30)

    def test_other_parts_can_add_a_term_and_a_broken_one_is_ignored(self):
        def bad(config, repos, workflows):
            raise RuntimeError("x")
        with mock.patch.object(ad, "ESTIMATE_TERMS", [lambda c, r, w: ("extra", 7), bad]):
            self.assertEqual(dict(ad.estimate({}, 10)["terms"])["extra"], 7)

    def test_the_doctor_line_says_the_figures_or_that_the_count_is_unknown(self):
        self.assertEqual(ad.estimate_result({"repos": None}, {}), ("ok", "repositories unknown"))
        status, detail = ad.estimate_result({"repos": 2000}, {})
        self.assertEqual(status, "warn")
        self.assertIn("2000 repositories", detail)


class InTheDoctor(unittest.TestCase):
    def run_doctor(self, table):
        def runner(args, timeout=20):
            if args[:3] == ["gh", "auth", "status"]:
                return 0, "", ""
            if args[-1] == "rate_limit":
                return 0, json.dumps({"resources": {"core": {"remaining": 4000, "limit": 5000}}}), ""
            return table.get(args[-1], (1, "", "gh: Not Found (HTTP 404)"))
        with mock.patch.object(doctor.shutil, "which", return_value="/usr/bin/gh"):
            return {c["id"]: c for c in doctor.run(runner, ports=(0,), config={"github_owner": "acme"})}

    def test_the_doctor_explains_an_sso_refusal_in_every_language_instead_of_staying_silent(self):
        sso = (1, "", "gh: Resource protected by organization SAML enforcement (HTTP 403)")
        checks = self.run_doctor({"user": answer(200, CLASSIC, {"login": "alice"}), "orgs/acme": sso})
        self.assertEqual((checks["access"]["status"], checks["access"]["detail"]), ("warn", "sso (owner)"))
        self.assertIn("Configure SSO", checks["access"]["fix"])
        for lang in i18n.LANGS:
            text = doctor.text(list(checks.values()), lambda k, lang=lang, **v: i18n.tl(lang, k, **v))
            self.assertIn("sso (owner)", text)
            self.assertNotIn("doctor.f.access", text)
            self.assertNotIn("doctor.t.estimate", text)

    def test_a_healthy_organization_passes_both_new_checks(self):
        checks = self.run_doctor({"user": answer(200, CLASSIC, {"login": "alice"}), "orgs/acme": answer(200, {}, {"public_repos": 4, "total_private_repos": 6}),
                                  "orgs/acme/repos?type=all&per_page=1": answer(200, {}, [])})
        self.assertEqual((checks["access"]["status"], checks["estimate"]["status"]), ("ok", "ok"))
        self.assertIn("10 repositories", checks["estimate"]["detail"])

    def test_the_two_checks_are_in_the_order_and_in_the_json(self):
        self.assertEqual(doctor.ORDER[doctor.ORDER.index("quota") + 1:doctor.ORDER.index("quota") + 3], ("access", "estimate"))
        for check in ("access", "estimate"):
            self.assertIn(check, doctor.FIX)


if __name__ == "__main__":
    unittest.main()
