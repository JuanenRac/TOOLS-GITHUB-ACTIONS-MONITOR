# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The manual inputs of a workflow (`on: workflow_dispatch: inputs:`) listed by `plan --inputs` of the batch dispatcher: the reader, the plan rows, the text and the promise that nothing is fired."""
import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.cli import gha_dispatch_all as gd  # noqa: E402
from github_actions_monitor.integrations import dispatch_inputs as di  # noqa: E402

WORKFLOW = """name: Build
on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      dry_run:
        description: 'Build but do not publish'
        required: true
        default: true
        type: boolean
      target:
        description: Which board
        type: choice
        default: alpha
        options:
          - alpha
          - beta
      note:
        description: Free text # a comment
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo ${{ inputs.note }}
"""


class Reader(unittest.TestCase):
    def test_the_inputs_of_a_workflow_are_listed_with_type_default_and_options(self):
        items = di.parse(WORKFLOW)
        self.assertEqual([i["name"] for i in items], ["dry_run", "target", "note"])
        self.assertEqual((items[0]["type"], items[0]["required"], items[0]["default"]), ("boolean", True, "true"))
        self.assertEqual((items[1]["type"], items[1]["options"], items[1]["default"]), ("choice", ["alpha", "beta"], "alpha"))
        self.assertEqual((items[2]["type"], items[2]["required"], items[2]["description"]), ("string", False, "Free text"))

    def test_no_inputs_is_an_empty_list_and_a_form_it_cannot_read_is_none(self):
        self.assertEqual(di.parse("on: push\njobs: {}\n"), [])
        self.assertEqual(di.parse("on: [push, workflow_dispatch]\n"), [])
        self.assertEqual(di.parse("on:\n  workflow_dispatch:\njobs: {}\n"), [])
        self.assertEqual(di.parse("on:\n  pull_request:\n    branches: [main]\n"), [])
        self.assertEqual(di.parse(""), [])
        self.assertIsNone(di.parse("on:\n  workflow_dispatch: {inputs: {a: {}}}\n"))

    def test_a_file_with_windows_line_ends_and_more_than_the_limit_is_bounded(self):
        self.assertEqual(len(di.parse(WORKFLOW.replace("\n", "\r\n"))), 3)
        many = "on:\n  workflow_dispatch:\n    inputs:\n" + "".join(f"      i{n}:\n        type: string\n" for n in range(40))
        self.assertEqual(len(di.parse(many)), di.MAX_INPUTS)

    def test_one_line_per_input_with_the_words_passed_in(self):
        line = di.describe(di.parse(WORKFLOW)[1], "obligatoria", "opcional")
        self.assertEqual(line, "target (choice, opcional) default=alpha [alpha, beta] - Which board")


class Plan(unittest.TestCase):
    TARGETS = {"demo-build": {"repo": "DEMO", "workflow": "build.yml", "tool": "t.py", "extra": []}}

    def patches(self, git_output):
        return (mock.patch.object(gd, "TARGETS", self.TARGETS), mock.patch.object(gd, "repo_of", lambda name: "DEMO"), mock.patch.object(gd, "git_run", git_output),
                mock.patch.object(gd, "local_head", lambda repo: ("a" * 40, "")))

    def test_the_rows_carry_the_inputs_only_when_asked(self):
        shown = []

        def git(path, *args, **kw):
            shown.append(args)
            return 0, WORKFLOW, ""
        with contextlib.ExitStack() as stack:
            for p in self.patches(git):
                stack.enter_context(p)
            self.assertNotIn("inputs", gd.plan_rows(["demo-build"])[0])
            row = gd.plan_rows(["demo-build"], inputs=True)[0]
        self.assertEqual([i["name"] for i in row["inputs"]], ["dry_run", "target", "note"])
        self.assertEqual(shown, [("show", "origin/main:.github/workflows/build.yml")])      # a read of a file, nothing else

    def test_a_workflow_that_is_not_there_is_unknown_not_an_error(self):
        with contextlib.ExitStack() as stack:
            for p in self.patches(lambda *a, **k: (128, "", "fatal: path does not exist")):
                stack.enter_context(p)
            self.assertIsNone(gd.plan_rows(["demo-build"], inputs=True)[0]["inputs"])

    def test_the_plan_prints_the_inputs_in_the_language_and_fires_nothing(self):
        args = mock.Mock(only=["demo-build"], ecosystem=None, profile=None, json=False, inputs=True)
        out = io.StringIO()
        with contextlib.ExitStack() as stack:
            for p in self.patches(lambda *a, **k: (0, WORKFLOW, "")):
                stack.enter_context(p)
            stack.enter_context(mock.patch.object(gd, "pick", lambda *a, **k: ["demo-build"]))
            stack.enter_context(mock.patch.object(gd, "preflight", lambda *a, **k: []))
            fired = stack.enter_context(mock.patch.object(gd, "fire"))
            run = stack.enter_context(mock.patch.object(gd.subprocess, "run"))
            stack.enter_context(contextlib.redirect_stdout(out))
            with i18n.use_language("es"):
                code = gd.cmd_plan(args)
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("- dry_run (boolean, obligatoria) default=true - Build but do not publish", text)
        self.assertIn("- target (choice, opcional) default=alpha [alpha, beta] - Which board", text)
        fired.assert_not_called()
        run.assert_not_called()

    def test_the_option_and_its_texts_exist_in_the_eight_languages(self):
        for key in ("gd.help_plan_inputs", "gd.inputs_none", "gd.inputs_unknown", "gd.word_required", "gd.word_optional"):
            for lang in i18n.LANGS:
                self.assertNotEqual(i18n.tl(lang, key), key, f"{lang}:{key}")
        self.assertIn("--inputs", Path(gd.__file__).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
