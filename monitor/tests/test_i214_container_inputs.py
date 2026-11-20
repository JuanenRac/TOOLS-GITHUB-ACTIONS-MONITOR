# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The trap of the inputs with a hyphen in an action that runs in a container: GitHub writes INPUT_FAIL-ON-FINDINGS (hyphens kept); a script that reads INPUT_FAIL_ON_FINDINGS never sees the value."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.cli import lint_workflows as lw  # noqa: E402

ACTION = """name: Gate
inputs:
  fail-on-findings:
    description: stop the job
    default: "true"
  token:
    required: true
runs:
  using: docker
  image: Dockerfile
"""


class Trap(unittest.TestCase):
    def test_the_inputs_with_a_hyphen_of_a_container_action_are_found(self):
        self.assertEqual(lw.declared_inputs(ACTION), (["fail-on-findings", "token"], True))
        self.assertEqual(lw.declared_inputs(ACTION.replace("docker", "node20"))[1], False)

    def test_the_underscore_form_is_a_trap_and_so_is_the_hyphen_form_in_the_shell(self):
        bad = lw.container_action_traps(ACTION, {"entrypoint.sh": 'if [ "$INPUT_FAIL_ON_FINDINGS" = true ]; then exit 1; fi\n'})
        self.assertEqual(bad, [("entrypoint.sh", 1, "fail-on-findings")])
        shell = lw.container_action_traps(ACTION, {"run.sh": 'echo "${INPUT_FAIL-ON-FINDINGS}"\n'})
        self.assertEqual(len(shell), 1)

    def test_the_way_github_really_writes_it_is_fine_when_it_is_read_through_the_environment(self):
        good = {"e.sh": 'v="$(printenv "INPUT_FAIL-ON-FINDINGS")"\n', "e.py": 'import os\nos.environ.get("INPUT_FAIL-ON-FINDINGS")\nos.environ["INPUT_TOKEN"]\n'}
        self.assertEqual(lw.container_action_traps(ACTION, good), [])

    def test_a_name_without_a_hyphen_has_no_trap_and_an_action_that_is_not_a_container_is_left_alone(self):
        self.assertEqual(lw.container_action_traps(ACTION, {"a.sh": "echo $INPUT_TOKEN\n"}), [])
        self.assertEqual(lw.container_action_traps(ACTION.replace("docker", "composite"), {"a.sh": "echo $INPUT_FAIL_ON_FINDINGS\n"}), [])


class AsARule(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / ".github" / "workflows" / "ci.yml").write_text("name: ci\non: push\npermissions: {}\njobs:\n  a:\n    runs-on: x\n    timeout-minutes: 5\n    steps:\n      - run: echo\n", encoding="utf-8")
        (root / "action.yml").write_text(ACTION, encoding="utf-8")
        (root / "entrypoint.sh").write_text("#!/bin/sh\nexit ${INPUT_FAIL_ON_FINDINGS:+1}\n", encoding="utf-8")
        self.root = root

    def tearDown(self):
        self.tmp.cleanup()

    def rules(self, enabled):
        cfg = lw.settings({"lint": {"rules": {"container_input_name": {"enabled": enabled}}}})
        return cfg["rules"]

    def test_it_is_optional_off_by_default_and_a_warning(self):
        self.assertIn("container_input_name", lw.RULES)
        self.assertIn("container_input_name", lw.OPTIONAL)
        base = lw.settings(None)["rules"]["container_input_name"]
        self.assertEqual((base["enabled"], base["severity"]), (False, "warn"))
        self.assertEqual([f for f in lw.lint_path(self.root, base_rules(), self.root) if f["rule"] == "container_input_name"], [])

    def test_with_the_rule_on_the_finding_names_the_file_the_line_and_the_input(self):
        found = [f for f in lw.lint_path(self.root, self.rules(True), self.root) if f["rule"] == "container_input_name"]
        self.assertEqual([(f["file"], f["line"], f["detail"], f["severity"]) for f in found], [("entrypoint.sh", 2, "fail-on-findings", "warn")])

    def test_the_rule_has_its_text_in_the_eight_languages_and_its_settings(self):
        from github_actions_monitor.app import settings_api
        for lang in i18n.LANGS:
            self.assertNotEqual(i18n.tl(lang, "lint.rule.container_input_name"), "lint.rule.container_input_name", lang)
        self.assertIn("lint.rules.container_input_name.enabled", settings_api.FIELDS)
        self.assertIn("lint.rules.container_input_name.severity", settings_api.FIELDS)


def base_rules():
    return lw.settings(None)["rules"]


if __name__ == "__main__":
    unittest.main()
