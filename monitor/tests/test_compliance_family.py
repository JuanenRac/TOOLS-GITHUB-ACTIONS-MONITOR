# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The compliance report, the doctor, the command line, the guides generated from the lists (controls, tools, editions, supported versions), the runner of the cross-cutting areas and two leftovers (the
ceiling of the step names, the launchers without `py`)."""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import families, i18n  # noqa: E402
from github_actions_monitor.cli import monitor_cli  # noqa: E402
from github_actions_monitor.data_pipeline import analytics  # noqa: E402
from github_actions_monitor.reporting import compliance_report  # noqa: E402

TAILS = ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_por", "_zho")
NOW = 1_800_000_000.0
SOURCES = {"chain": {"ok": True, "entries": 3}, "guard": {"read_only_strict": False, "egress_policy": "default"}, "backups": {"age_days": 2, "sealed": False}, "latest": "", "container": False,
           "root": False, "schema": "files", "edition": "complete"}


def values(config, **changed):
    return {row["id"]: (row["value"], row["evidence"]) for row in compliance_report.report(config, NOW, dict(SOURCES, **changed))["lines"]}


def family():
    return next(f for f in families.all_families() if f.name == "compliance")


class Report(unittest.TestCase):
    def test_the_same_installation_and_clock_give_the_same_report_with_every_line_named_in_eight_languages(self):
        first = compliance_report.report({}, NOW, SOURCES)
        self.assertEqual(first, compliance_report.report({}, NOW, SOURCES))
        self.assertEqual([row["id"] for row in first["lines"]], list(compliance_report.LINE_IDS))
        for row in first["lines"]:
            self.assertIn(row["evidence"], ("checked", "declared"))
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, "ui.compliance.line_" + row["id"]), "ui.compliance.line_" + row["id"])
        self.assertIn("not a certification", first["notice"])

    def test_it_changes_with_each_switch(self):
        plain = values({})
        for config, ident in (({"auth": {"enabled": True}}, "authentication"), ({"listen": {"network": True}}, "network_mode"), ({"security": {"read_only_strict": True}}, "read_only_strict"),
                              ({"security": {"egress_policy": "none"}}, "egress_policy"), ({"retention": {"legal_hold": True}}, "legal_hold"),
                              ({"audit_checkpoints": {"enabled": True}}, "audit_checkpoints"), ({"audit_export": {"enabled": True, "target": "syslog"}}, "audit_export"),
                              ({"ops": {"backup": {"encrypt": True}}}, "backup_encryption"), ({"plugins": {"enabled": True, "third_party": {"enabled": True}}}, "third_party_plugins")):
            self.assertNotEqual(values(config)[ident][0], plain[ident][0], ident)

    def test_a_restriction_that_is_set_but_not_in_force_is_only_declared(self):
        self.assertEqual(values({"security": {"read_only_strict": True}})["read_only_strict"], ("on", "declared"))
        self.assertEqual(values({"security": {"read_only_strict": True}}, guard={"read_only_strict": True, "egress_policy": "default"})["read_only_strict"], ("on", "checked"))
        self.assertEqual(values({}, chain={"ok": False, "entries": 3})["audit_chain"], ("broken", "checked"))
        self.assertEqual(values({}, latest="99.0.0")["support"][0], "newer_published:99.0.0")

    def test_it_holds_no_secret_no_path_and_no_name(self):
        config = {"github_owner": "SomebodyPrivate", "repos": ["secret-repo"], "audit_export": {"enabled": True, "target": "http", "url": "https://u.example/s3cr3t", "path": "C:/Users/person/x"},
                  "github_token": {"enabled": True}, "listen": {"tls_cert": "/home/person/cert.pem"}, "notify": {"channels": {"ntfy": {"enabled": True, "topic": "private-topic"}}}}
        text = json.dumps(compliance_report.report(config, NOW, SOURCES))
        for needle in ("SomebodyPrivate", "secret-repo", "s3cr3t", "person", "private-topic", "u.example"):
            self.assertNotIn(needle, text, needle)


class Doctor(unittest.TestCase):
    def checks(self):
        return {check.id: check for check in family().checks}

    def test_a_destination_outside_the_policy_makes_the_doctor_fail(self):
        run = self.checks()["compliance_egress"].run
        self.assertEqual(run({})[0], "ok")
        state, detail = run({"security": {"egress_policy": "github_only"}, "notify": {"channels": {"ntfy": {"enabled": True}}}})
        self.assertEqual(state, "fail")
        self.assertIn("ntfy.sh", detail)

    def test_the_others_answer_with_the_defaults_and_have_their_texts(self):
        for check in family().checks:
            state, detail = check.run({})
            self.assertIn(state, ("ok", "warn", "fail"), check.id)
            for lang in i18n.LANGS:
                for kind in "tf":
                    self.assertNotEqual(i18n.tl(lang, f"doctor.{kind}.{check.id}"), f"doctor.{kind}.{check.id}")
        self.assertEqual(self.checks()["compliance_strict"].run({})[1], "off")
        self.assertIn("audit", self.checks()["compliance_retention"].run({})[1])

    def test_a_newer_release_says_this_one_is_not_supported(self):
        from unittest import mock
        from github_actions_monitor.app import updatecheck
        with mock.patch.object(updatecheck, "_load", return_value={"release": {"tag": "v99.0.0"}}):
            self.assertEqual(self.checks()["compliance_support"].run({})[0], "warn")

    def test_an_export_that_lags_is_an_alert(self):
        from unittest import mock
        from github_actions_monitor.integrations import compliance_audit_export as export
        config = {"audit_export": {"enabled": True, "path": "x"}}
        state = {"cursor": "", "sent": 0, "lost": 1, "backlog_bytes": 0, "last_error": "", "at": NOW}
        with mock.patch.object(export, "load_state", return_value=state):
            alerts = family().alerts(config, "")
            self.assertEqual([a["code"] for a in alerts], ["system.audit_export_lag"])
            self.assertEqual(family().alerts({}, ""), [])

    def test_the_commands_are_there(self):
        self.assertTrue({"compliance", "audit"} <= set(monitor_cli.COMMANDS))


class StrictRoutes(unittest.TestCase):
    def setUp(self):
        import threading
        from unittest import mock
        from github_actions_monitor.app import actions_monitor
        self.monitor, self.config = actions_monitor, {"security": {"read_only_strict": True}}
        server = actions_monitor.QuietServer(("127.0.0.1", 0), actions_monitor.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        for patch in (mock.patch.object(actions_monitor.toolconfig, "raw_config", side_effect=lambda: self.config), mock.patch.object(actions_monitor, "audit_action")):
            patch.start()
            self.addCleanup(patch.stop)
        self.base = f"http://127.0.0.1:{server.server_address[1]}"

    def post(self, path):
        import urllib.error
        import urllib.request
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base + path, data=b"{}", headers={"Content-Type": "application/json"}), timeout=10) as answer:
                return answer.status, json.loads(answer.read() or b"{}")
        except urllib.error.HTTPError as error:
            raw = error.read()
            return error.code, json.loads(raw) if raw else {}

    def test_every_route_that_writes_answers_403_with_the_reason(self):
        from github_actions_monitor.security import audited_posts, compliance_guard
        for route in compliance_guard.WRITE_ROUTES:
            self.assertIn(route, audited_posts.AUDITED, route)
            status, answer = self.post(route)
            self.assertEqual((status, answer.get("code")), (403, "read_only_strict"), route)

    def test_without_the_mode_the_route_is_not_refused_for_that_reason(self):
        self.config = {}
        for route in ("/api/gh-action/confirm", "/api/webhook/redeliver"):
            self.assertNotEqual(self.post(route)[1].get("code"), "read_only_strict", route)


class ListsAndGuides(unittest.TestCase):
    def read(self, *parts):
        return ROOT.joinpath(*parts).read_text(encoding="utf-8")

    def test_every_control_names_tests_that_exist_and_every_guide_has_its_row(self):
        controls = json.loads((HERE / "docs" / "schemas" / "controls.json").read_text(encoding="utf-8"))["controls"]
        self.assertGreaterEqual(len(controls), 8)
        for control in controls:
            self.assertIn(control["status"], ("IMP", "PAR"))
            self.assertTrue(control["tests"], control["id"])
            for name in control["tests"]:
                self.assertTrue((HERE / "tests" / f"{name}.py").is_file(), name)
        for tail in TAILS:
            text = (HERE / "docs" / f"COMPLIANCE{tail}.md").read_text(encoding="utf-8")
            self.assertEqual(re.findall(r"^\| `([a-z_]+)` \| \[(IMP|PAR)\]", text, re.M), [(c["id"], c["status"]) for c in controls], tail)

    def test_every_tool_of_the_table_has_one_level_and_every_script_has_a_row(self):
        data = json.loads((HERE / "docs" / "schemas" / "ecosystem_tools.json").read_text(encoding="utf-8"))
        if (HERE / "tools").is_dir():
            self.assertEqual(sorted(data["scripts"]), sorted(p.stem for p in (HERE / "tools").glob("*.py")))
        for row in data["tools"]:
            self.assertIn(row["level"], data["levels"])
            self.assertTrue((HERE / "docs" / row["doc"]).is_file(), row["doc"])
        for tail in TAILS:
            text = (HERE / "docs" / f"ECOSYSTEM_TOOLS{tail}.md").read_text(encoding="utf-8")
            self.assertEqual(re.findall(r"^\| `([a-z_]+)` \|", text, re.M), [row["id"] for row in data["tools"]], tail)
            for name in data["scripts"]:
                self.assertIn(f"tools/{name}.py", text)

    def test_the_guide_of_the_editions_lists_every_module_switch_with_its_default(self):
        switches = {s.key for f in families.all_families() for s in f.settings if s.kind == "bool" and s.key.endswith(".enabled") and f.name in ("plugins", "assistant", "extci", "compliance", "posture")}
        defaults = families.defaults()
        for tail in TAILS:
            text = (HERE / "docs" / f"EDITIONS{tail}.md").read_text(encoding="utf-8")
            listed = set(re.findall(r"^\| `([a-z_.]+)` \|", text, re.M))
            self.assertEqual(switches - listed, set(), tail)
        english = (HERE / "docs" / "EDITIONS.md").read_text(encoding="utf-8")
        for key, word in re.findall(r"^\| `([a-z_.]+)` \| (on|off) \|", english, re.M):
            node = defaults
            for part in key.split("."):
                node = node[part] if isinstance(node, dict) and part in node else None
            if node is not None:
                self.assertEqual(node, word == "on", key)

    def test_the_security_policy_says_that_only_the_latest_version_is_supported(self):
        if not (ROOT / "SECURITY.md").is_file():
            self.skipTest("not in the package: files of the repository root")
        self.assertIn("Only the latest published version is supported", self.read("SECURITY.md"))
        for tail in TAILS:
            self.assertGreaterEqual(self.read(f"SECURITY{tail}.md").count("\n## "), 3, tail)

    def test_every_area_of_the_cross_cutting_runner_has_its_tests_and_its_job(self):
        runner, workflow = ROOT / "tools" / "cross_cutting.py", ROOT / ".github" / "workflows" / "cross-cutting.yml"
        if not (runner.is_file() and workflow.is_file()):
            self.skipTest("not in the package: files of the repository root")
        areas = {}
        exec(compile(re.search(r"^AREAS = \{.*?^\}", runner.read_text(encoding="utf-8"), re.M | re.S).group(0), "areas", "exec"), areas)
        for area, modules in areas["AREAS"].items():
            for name in modules:
                self.assertTrue((HERE / "tests" / f"{name}.py").is_file(), f"{area}: {name}")
        listed = re.search(r"area: \[([^\]]+)\]", workflow.read_text(encoding="utf-8")).group(1)
        self.assertEqual([a.strip() for a in listed.split(",")], list(areas["AREAS"]))


class Leftovers(unittest.TestCase):
    def test_the_step_names_of_a_workflow_have_a_ceiling_and_the_recent_ones_stay(self):
        book = analytics.Store.__new__(analytics.Store)
        import threading
        book.lock, book.max_samples, book.dirty, book.data = threading.Lock(), 5, False, {"seen": [], "queue": {}, "steps": {}, "daily": {}}
        from unittest import mock
        with mock.patch.object(analytics, "job_sample", lambda job: (None, {job: 1})):
            book.add_jobs("r", "w", 1, [f"step {i}" for i in range(analytics.MAX_STEP_NAMES + 50)])
        names = list(book.data["steps"]["r|w"])
        self.assertEqual(len(names), analytics.MAX_STEP_NAMES)
        self.assertEqual((names[0], names[-1]), ("step 50", f"step {analytics.MAX_STEP_NAMES + 49}"))

    def test_the_launchers_of_windows_fall_back_to_python(self):
        for name in ("MONITOR_GITHUB_ACTIONS.bat", "MONITOR_LITE_GITHUB_ACTIONS.bat", "BATCH_GITHUB_ACTIONS.bat"):
            text = (HERE / name).read_text(encoding="utf-8")
            self.assertIn('if errorlevel 1 set "PY=python"', text, name)
            self.assertNotRegex(text, r"(?m)^\s*py -3 -m", name)


if __name__ == "__main__":
    unittest.main()
