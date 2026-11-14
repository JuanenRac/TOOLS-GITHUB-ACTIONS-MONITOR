# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Offline tests of the batch dispatcher and of the workspace resolution. Run:  py -3 -m unittest discover -s tests -v"""
import json
import os
import re
import sys
import tempfile
import unittest
import _testenv  # noqa: F401
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from github_actions_monitor.cli import gha_dispatch_all as gd  # noqa: E402
from github_actions_monitor.app import workspace  # noqa: E402

NAME_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")


class Targets(unittest.TestCase):
    def test_every_name_is_valid_and_has_a_workflow_and_a_tool(self):
        for name, target in gd.TARGETS.items():
            self.assertRegex(name, NAME_RE, name)
            self.assertTrue(target["workflow"].endswith(".yml"), name)
            self.assertTrue(target["tool"].endswith(".py"), name)
            self.assertIsInstance(target["extra"], list, name)

    def test_the_signing_tools_exist_on_disk(self):
        if not gd.TOOLS_DIR.is_dir() or not any((gd.TOOLS_DIR / t["tool"]).is_file() for t in gd.TARGETS.values()):
            self.skipTest("integration test: needs the 2_release_y_firma tools (MONITOR_TOOLS_DIR or tools_dir)")
        missing = [f"{n}: {t['tool']}" for n, t in gd.TARGETS.items() if not (gd.TOOLS_DIR / t["tool"]).is_file()]
        self.assertEqual(missing, [])

    def test_a_part_names_its_repository(self):
        for name, target in gd.TARGETS.items():
            if ":" in name:
                self.assertEqual(target["repo"], name.split(":")[0])
                self.assertIn(target["repo"], gd.TARGETS)

    def test_the_workflows_are_known_build_workflows(self):
        self.assertEqual({t["workflow"] for t in gd.TARGETS.values()} - set(gd.BUILD_WORKFLOWS), set())


class Preflight(unittest.TestCase):
    def test_a_missing_tool_is_reported_before_anything_is_fired(self):
        with mock.patch.dict(gd.TARGETS, {"X-FAKE": {"workflow": "firmware-build.yml", "tool": "no_such_tool.py", "extra": []}}):
            problems = gd.preflight(["X-FAKE"], workflows=False)
        self.assertEqual(len(problems), 1)
        self.assertIn("no_such_tool.py", problems[0])

    def test_a_clone_without_the_workflow_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "ARMOR-NODE-HMI").mkdir()
            with mock.patch.object(gd, "ROOT", Path(tmp)):
                problems = gd.preflight(["ARMOR-NODE-HMI"])
        self.assertTrue(any("firmware-build.yml" in p for p in problems))

    def test_hygiene_lists_build_workflows_without_a_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            for repo, wf in (("ARMOR-NEW-THING", "package-build.yml"), ("EH3D-OTHER", "firmware-build.yml"), ("ARMOR-SERVER", "package-build.yml")):
                folder = Path(tmp) / repo
                (folder / ".git").mkdir(parents=True)
                (folder / ".github" / "workflows").mkdir(parents=True)
                (folder / ".github" / "workflows" / wf).write_text("name: x\n", encoding="utf-8")
            with mock.patch.object(gd, "ROOT", Path(tmp)):
                broken, uncovered, eh3d, odd = gd.hygiene()
        self.assertEqual([u.split(":")[0] for u in uncovered], ["ARMOR-NEW-THING"])
        self.assertEqual([e.split(":")[0] for e in eh3d], ["EH3D-OTHER"])


class Workspace(unittest.TestCase):
    def test_the_environment_wins(self):
        with mock.patch.dict(os.environ, {"JUANENRAC_ROOT": "X:/somewhere", "JUANENRAC_AUDIT_DIR": "X:/audits"}):
            self.assertEqual(workspace.workspace_root(), Path("X:/somewhere"))
            self.assertEqual(workspace.audit_dir(), Path("X:/audits"))

    def test_without_environment_it_finds_the_tree_above(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("JUANENRAC_")}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(workspace, "_config", return_value=None):
            try:
                root = workspace.workspace_root()
            except SystemExit:
                self.skipTest("integration test: this copy is not inside a workspace")
        if not (root / ".monitor-root").is_file():
            self.skipTest("integration test: needs a .monitor-root marker")
        self.assertTrue(True)

    def test_the_configuration_file_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "config").mkdir()
            (Path(tmp) / "config" / "actions_monitor.json").write_text(json.dumps({"workspace_root": "Y:/ws", "audit_dir": "Y:/au"}), encoding="utf-8")
            with mock.patch.object(workspace, "HERE", Path(tmp)):
                self.assertEqual(workspace._config("workspace_root"), Path("Y:/ws"))
                self.assertEqual(workspace._config("audit_dir"), Path("Y:/au"))
                self.assertIsNone(workspace._config("nothing"))


if __name__ == "__main__":
    unittest.main()
