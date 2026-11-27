# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Posture checks, the compliance report, the restrictions, the approval of a deployment and the external CI adapters, each against the case that used to give a wrong answer. Invented names, no real calls."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE / "tools"))

import _testenv  # noqa: F401,E402
import extci_fake_servers as fake  # noqa: E402
from github_actions_monitor import families  # noqa: E402
from github_actions_monitor.data_pipeline import etagcache  # noqa: E402
from github_actions_monitor.families.posture import posture_checks as checks, posture_engine as engine  # noqa: E402
from github_actions_monitor.families.posture.posture_checks import Unread  # noqa: E402
from github_actions_monitor.integrations.external_ci import extci_adapters as adapters, extci_engine  # noqa: E402
from github_actions_monitor.integrations.external_ci.extci_fetch import Failed, Reader  # noqa: E402
from github_actions_monitor.reporting import compliance_report  # noqa: E402
from github_actions_monitor.security import compliance_guard as guard  # noqa: E402

NOW = 1_800_000_000.0
BASE = "repos/acme/app"


class Fake:
    """{endpoint without the query: answer}; an endpoint that is not here is a 404, a string answer is the reason of a refusal, a function receives the whole endpoint."""

    def __init__(self, answers):
        self.answers, self.asked = dict(answers), []

    def __call__(self, endpoint):
        self.asked.append(endpoint)
        key = endpoint.partition("?")[0]
        if key not in self.answers:
            raise Unread("missing")
        value = self.answers[key]
        if callable(value):
            return value(endpoint)
        if isinstance(value, str):
            raise Unread(value)
        return value


def quiet_repo(**extra):
    info = {"default_branch": "main", "private": False, "security_and_analysis": {"secret_scanning": {"status": "enabled"}, "secret_scanning_push_protection": {"status": "enabled"}}}
    return dict({BASE: info, f"{BASE}/hooks": [], f"{BASE}/actions/permissions": {"enabled": False}, f"{BASE}/keys": [], f"{BASE}/actions/secrets": {"secrets": []}, f"{BASE}/releases": [],
                 f"{BASE}/vulnerability-alerts": None, f"{BASE}/code-scanning/default-setup": {"state": "configured"}, f"{BASE}/rules/branches/main": [{"type": "deletion"}],
                 f"{BASE}/contents/SECURITY.md": {}, f"{BASE}/contents/renovate.json": {}}, **extra)


def cfg(**extra):
    return {"posture": dict({"enabled": True, "profile": "basic", "org_checks": False}, **extra)}


class Posture(unittest.TestCase):
    def setUp(self):
        engine.state_file().unlink(missing_ok=True)
        self.addCleanup(lambda: engine.state_file().unlink(missing_ok=True))

    def read(self, answers, config=None, repos=("app",)):
        config = config or cfg()
        engine.refresh(config, "acme", list(repos), get=Fake(answers), now=NOW)
        return engine.report(config)

    def found(self, report):
        return {f["check"] for r in report["repos"] for f in r["findings"]}

    def test_an_answer_without_a_body_is_an_answer_with_the_cache_on(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = etagcache.EtagCache(path=Path(folder) / "c.json")
            data, how = cache.fetch(f"{BASE}/vulnerability-alerts", lambda args: (0, "HTTP/2.0 204 No Content\r\nX-Github-Request-Id: A404:403\r\n\r\n", ""))
        self.assertEqual((data, how), (None, "plain"))

    def test_a_protection_that_cannot_be_read_is_not_unprotected(self):
        answers = quiet_repo(**{f"{BASE}/rules/branches/main": [], f"{BASE}/branches/main": {"name": "main", "protected": True}})
        report = self.read(answers)
        self.assertNotIn("branch.unprotected", self.found(report))
        self.assertEqual(report["repos"][0]["unread"].get("branch"), "forbidden")

    def test_refused_code_scanning_keeps_what_was_seen_of_the_secrets(self):
        answers = quiet_repo(**{f"{BASE}/code-scanning/default-setup": "forbidden"})
        answers[BASE]["security_and_analysis"]["secret_scanning"]["status"] = "disabled"
        report = self.read(answers)
        self.assertIn("scan.no_credentials", self.found(report))
        self.assertEqual(report["repos"][0]["unread"].get("scan"), "forbidden")
        report = self.read(answers, cfg(refresh_hours=0))
        self.assertEqual(sum(1 for f in report["repos"][0]["findings"] if f["check"] == "scan.no_credentials"), 1)

    def test_a_security_policy_of_the_account_counts(self):
        answers = quiet_repo()
        del answers[f"{BASE}/contents/SECURITY.md"]
        answers.update({"repos/acme/.github": {"private": False}, "repos/acme/.github/contents/SECURITY.md": {}})
        self.assertNotIn("repo.no_policy", self.found(self.read(answers)))
        engine.state_file().unlink()
        answers["repos/acme/.github"] = {"private": True}
        self.assertIn("repo.no_policy", self.found(self.read(answers)))

    def test_what_is_switched_off_or_filtered_out_is_never_without_findings(self):
        report = self.read(quiet_repo())
        rows = {r["id"]: r for r in report["compliance"]["cis"]}
        self.assertEqual(rows["2.2"]["status"], "not_checked")      # runner_runs = 0: no run was read
        self.assertEqual(rows["1.5"]["status"], "partly")      # scan.no_code is of the strict profile
        self.assertEqual(report["repos"][0]["maturity"]["checked"], 5)

    def test_one_repository_that_could_not_be_read_makes_the_row_partly(self):
        data = {"repos": {"a": {"checked": ["hooks"], "unread": {}, "findings": []}, "b": {"checked": [], "unread": {"hooks": "forbidden"}, "findings": []}}, "org": {}}
        rows = {r["id"]: r for r in engine.compliance(data)["cis"]}
        self.assertEqual(rows["2.4"]["status"], "partly")
        data = {"repos": {"a": {"checked": ["deploy"], "findings": []}}, "org": {}, "pending": 3}
        self.assertEqual({r["id"]: r for r in engine.compliance(data)["cis"]}["5.1"]["status"], "partly")

    def test_a_refused_organization_does_not_stop_the_repositories(self):
        answers = quiet_repo()
        answers["orgs/acme"] = "forbidden"
        report = self.read(answers, cfg(org_checks=True))
        self.assertEqual([r["repo"] for r in report["repos"]], ["app"])
        self.assertEqual(report["org"]["unread"], {"organization": "forbidden"})

    def test_a_setting_of_the_organization_that_is_not_told_is_not_fine(self):
        info = {"two_factor_requirement_enabled": None}
        with self.assertRaises(Unread):
            checks.org_settings(lambda endpoint: info, "orgs/acme", {})

    def test_every_page_of_the_secrets_and_release_branches_is_read(self):
        def page_of(rows, key=None):
            def get(endpoint):
                number = int(endpoint.partition("&page=")[2] or 1)
                part = rows[(number - 1) * 100:number * 100]
                return {key: part} if key else part
            return get
        old = [{"name": f"N{i}", "updated_at": "2026-12-31T00:00:00Z"} for i in range(100)] + [{"name": "OLD", "updated_at": "2020-01-01T00:00:00Z"}]
        found = checks.stored(Fake({f"{BASE}/actions/secrets": page_of(old, "secrets")}), BASE, {"cfg": {"stored_max_days": 365}, "now": NOW})
        self.assertEqual([f["item"] for f in found], ["OLD"])
        names = [{"name": f"topic{i}"} for i in range(100)] + [{"name": "release/9"}]
        found = checks.branch(Fake({f"{BASE}/rules/branches/main": [{"type": "deletion"}], f"{BASE}/branches": page_of(names)}), BASE,
                              {"cfg": {"release_branches": ["release/*"]}, "repo_info": {"default_branch": "main"}})
        self.assertIn(("branch.release_unprotected", "release/9"), {(f["check"], f["item"]) for f in found})

    def test_a_digest_that_appears_later_is_not_a_replaced_file_and_a_late_tag_is_followed(self):
        memory = {}
        release = {"tag_name": "v1", "assets": [{"name": "a.zip", "id": 1, "size": 5, "digest": None}]}
        answers = {f"{BASE}/releases": [release]}
        ctx = {"cfg": {}, "memory": memory}
        self.assertEqual(checks.releases(Fake(answers), BASE, ctx), [])
        release["assets"][0]["digest"] = "sha256:aa"
        answers[f"{BASE}/git/ref/tags/v1"] = {"object": {"sha": "1" * 40}}
        self.assertEqual(checks.releases(Fake(answers), BASE, ctx), [])
        release["assets"][0]["digest"] = "sha256:bb"
        answers[f"{BASE}/git/ref/tags/v1"] = {"object": {"sha": "2" * 40}}
        self.assertEqual({f["check"] for f in checks.releases(Fake(answers), BASE, ctx)}, {"release.asset_replaced", "release.tag_moved"})

    def test_a_workflow_that_did_not_run_lately_is_still_remembered_as_hardened(self):
        def runs(name, steps):
            return {f"{BASE}/actions/runs": {"workflow_runs": [{"id": 1, "name": name}]}, f"{BASE}/actions/runs/1/jobs": {"jobs": [{"steps": [{"name": s} for s in steps]}]}}
        ctx = {"cfg": {"runner_runs": 1}, "memory": {}}
        checks.runner(Fake(runs("ci", ["Harden Runner"])), BASE, ctx)
        checks.runner(Fake(runs("docs", ["Build"])), BASE, ctx)
        self.assertEqual([f["check"] for f in checks.runner(Fake(runs("ci", ["Build"])), BASE, ctx)], ["runner.coverage_lost"])


def report_lines(config, **sources):
    base = {"guard": {"read_only_strict": False, "egress_policy": "default"}, "chain": {"ok": True, "entries": 3}, "backups": {"age_days": 1, "sealed": False}, "latest": "", "edition": "complete",
            "container": False, "root": None, "schema": "files"}
    base.update(sources)
    return {row["id"]: (row["value"], row["evidence"]) for row in compliance_report.lines(config, NOW, base)}


class Report(unittest.TestCase):
    def test_a_certificate_is_seen(self):
        self.assertEqual(report_lines({"listen": {"tls_cert_file": "c.pem", "tls_key_file": "k.pem"}})["tls"][0], "certificate_set")

    def test_an_older_published_version_is_not_a_newer_one(self):
        self.assertEqual(report_lines({}, latest="0.0.1")["support"][0], "latest_only")
        self.assertEqual(report_lines({}, latest="99.0.0")["support"][0], "newer_published:99.0.0")

    def test_the_log_of_actions_is_broken_or_unknown_never_empty(self):
        self.assertEqual(report_lines({}, chain={"ok": False, "entries": 0})["audit_chain"], ("broken", "checked"))
        self.assertEqual(report_lines({}, chain={"ok": False, "entries": -1})["audit_chain"], ("unknown", "declared"))

    def test_what_could_not_be_looked_at_is_not_marked_checked(self):
        lines = report_lines({"ops": {"backup": {"encrypt": False}}}, backups={"age_days": None, "sealed": True, "unknown": True}, schema="unknown")
        self.assertEqual(lines["last_backup_days"], ("unknown", "declared"))
        self.assertEqual(lines["storage_schema"], ("unknown", "declared"))
        self.assertEqual(lines["backup_encryption"], ("off", "declared"))
        self.assertEqual(lines["egress_violations"][1], "declared")
        self.assertEqual(lines["deployment"][1], "declared")

    def test_a_restriction_in_force_is_reported_even_when_the_file_no_longer_asks_for_it(self):
        lines = report_lines({}, guard={"read_only_strict": True, "egress_policy": "none"})
        self.assertEqual((lines["read_only_strict"], lines["egress_policy"]), (("on", "checked"), ("none", "checked")))

    def test_an_export_without_a_destination_says_so(self):
        self.assertEqual(report_lines({"audit_export": {"enabled": True, "target": "http"}})["audit_export"][0], "http:no_destination")


class Restrictions(unittest.TestCase):
    def setUp(self):
        guard.reset()
        self.addCleanup(guard.reset)

    def test_the_tools_of_the_secret_stores_do_not_start_under_a_network_policy(self):
        guard.configure({"security": {"egress_policy": "github_only"}})
        for argv in (["sops", "--decrypt", "f"], ["bws", "secret", "get", "x"], ["curl", "http://example.org", "version"], ["docker", "push", "version"]):
            self.assertEqual(guard.command_refusal(argv), "egress_policy", argv)
        for argv in (["sops", "--version"], ["docker", "version"]):
            self.assertEqual(guard.command_refusal(argv), "", argv)

    def arm(self, content):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        path = folder / "c.json"
        if content is not None:
            path.write_bytes(content)
        guard.reset()
        with mock.patch.object(guard, "install"):
            guard.arm_from_file(path)
        return guard.STATE["strict"], guard.STATE["policy"]

    def test_a_configuration_that_cannot_be_read_restricts(self):
        self.assertEqual(self.arm(None), (False, "default"))      # no file: a first start
        self.assertEqual(self.arm(b'{"language": "en",'), (True, "github_only"))
        self.assertEqual(self.arm(b'{"security": {"egress_policy": "none"},'), (True, "none"))
        self.assertEqual(self.arm(b'[1, 2]'), (True, "github_only"))
        self.assertEqual(self.arm(b'{"security": "strict"}'), (True, "github_only"))
        self.assertEqual(self.arm('{"security": {"egress_policy": "none"}}'.encode("utf-16")), (True, "none"))
        self.assertTrue(guard.status()["config_unreadable"])
        self.assertEqual(self.arm(b'{}'), (False, "default"))

    def test_the_file_of_the_lite_edition_restricts_the_lite_product(self):
        from github_actions_monitor.app import actions_monitor, settings_api, toolconfig
        from github_actions_monitor.util import paths
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        (folder / "actions_monitor_lite.json").write_text(json.dumps({"security": {"read_only_strict": True}}), encoding="utf-8")
        real = paths.place
        keep = [(actions_monitor, "CONFIG_FILE"), (actions_monitor, "LOG_FILE"), (settings_api, "CONFIG_FILE"), (toolconfig, "CONFIG_FILE"), (settings_api, "BACKUP_DIR"), (etagcache, "CACHE_FILE")]
        patches = [mock.patch.object(module, name, getattr(module, name)) for module, name in keep]
        patches += [mock.patch.dict(actions_monitor.LITE), mock.patch.object(guard, "install"), mock.patch.object(paths, "place", lambda name, base=None: folder / name if name.endswith("_lite.json") else real(name, base))]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        actions_monitor.enable_lite()
        self.assertTrue(guard.STATE["strict"])


class Approval(unittest.TestCase):
    ENVS = {"ok": True, "environments": [{"id": 7, "name": "staging", "can_approve": True}, {"id": 8, "name": "production", "can_approve": True}, {"id": 9, "name": "other", "can_approve": False}]}

    def plan(self, body, envs=None):
        from github_actions_monitor.families import actions as family
        from github_actions_monitor.integrations import ghactions
        seen = []

        def planned(config, owner, action, repo, number, **kw):
            seen.append(kw["fields"])
            return {"id": "p", "fields": kw["fields"]}, "ok"
        engine_ = mock.Mock()
        engine_.environments_of.return_value = envs or self.ENVS
        request = mock.Mock(body=dict({"action": "approve_deployment", "repo": "app", "number": 5}, **body), config={}, user="me")
        with mock.patch.object(family, "_engine", return_value=engine_), mock.patch.object(family, "_owner", return_value="me"), mock.patch.object(family, "_monitor"), \
                mock.patch.object(ghactions, "plan", planned):
            return family._plan(request), seen

    def test_with_several_environments_one_has_to_be_chosen_by_name(self):
        out, seen = self.plan({})
        self.assertEqual((out[0], out[1]["status"], out[1]["environments"], seen), (400, "choose_environment", ["staging", "production"], []))

    def test_only_the_chosen_environment_is_approved_and_the_plan_names_it(self):
        out, seen = self.plan({"environment": "production"})
        self.assertEqual(seen[0]["environment_ids[]"], [8])
        self.assertEqual(out["plan"]["environments"], ["production"])
        for wrong in ("other", "nope", 8, ["staging"]):
            self.assertEqual(self.plan({"environment": wrong})[0][1]["status"], "environment", wrong)

    def test_one_environment_needs_no_choice_and_is_named(self):
        out, seen = self.plan({}, {"ok": True, "environments": [self.ENVS["environments"][0]]})
        self.assertEqual((seen[0]["environment_ids[]"], out["plan"]["environments"]), ([7], ["staging"]))


class ExternalCI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = fake.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def settings(self, **extra):
        return extci_engine.settings({"external_ci": dict({"allow_private_targets": True, "jenkins": {"enabled": True}}, **extra)})

    def reader(self, kind, **extra):
        return Reader(dict({"kind": kind, "url": self.base, "repo": "m"}, **extra), self.settings())

    def test_the_log_of_azure_is_the_one_of_the_step_that_failed(self):
        text, _cut = adapters.log_tail(self.reader("azure", project="proj"), {"kind": "azure", "url": self.base, "project": "proj"}, {"ref": 55}, 4096)
        self.assertIn("FAILED", text)
        self.assertIn("/proj/_apis/build/builds/55/logs/1", [p for p, _h in self.server.seen])

    def test_the_channel_letters_of_a_buildbot_stdio_log_are_taken_off(self):
        text, _cut = adapters.log_tail(self.reader("buildbot"), {"kind": "buildbot", "url": self.base}, {"ref": 902}, 4096)
        self.assertTrue(text.startswith("\x1b[31mstep one"), repr(text[:20]))
        self.assertIn("\nstep two\n", text)

    def test_the_log_of_gitlab_is_not_the_one_of_a_job_that_may_fail(self):
        adapters.log_tail(self.reader("gitlab", project="group/app"), {"kind": "gitlab", "url": self.base, "project": "group/app"}, {"ref": 31}, 4096)
        self.assertIn("/api/v4/projects/group%2Fapp/jobs/77/trace", [p for p, _h in self.server.seen])

    def test_a_pipeline_being_cancelled_still_runs(self):
        reader = mock.Mock()
        reader.json.return_value = [{"id": 1, "status": "canceling", "ref": "main", "source": "push"}, {"id": 2, "status": "waiting_for_callback", "ref": "main", "source": "push"}]
        reader.url.return_value = ""
        runs, _missing = adapters.gitlab(reader, {"kind": "gitlab", "repo": "m", "project": "g/a"}, self.settings())
        self.assertEqual([r["status"] for r in runs], ["in_progress", "in_progress"])

    def test_a_log_whose_end_was_never_reached_is_not_given_as_its_end(self):
        with self.assertRaises(Failed) as caught:
            self.reader("jenkins").tail("/job/folder/job/app/12/consoleText", 10, total=20)
        self.assertEqual(caught.exception.reason, "too_big")

    def test_a_sign_in_page_with_203_is_refused(self):
        with self.assertRaises(Failed) as caught:
            self.reader("azure").json("/signin")
        self.assertEqual(caught.exception.reason, "http_203")


if __name__ == "__main__":
    unittest.main()
