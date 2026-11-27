# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The demo with the optional parts on (the pictures of their boxes are taken from it) answers every one of them with invented data, and the judge of the check of the static site accepts only a site
that drew, refused a write and ran the linter in the browser."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOOLS = HERE.parent / "tools"
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402

NO_TOOLS = "the tools of the repository are not in this copy"


def load(name):
    import importlib.util
    sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TheJudgeOfTheSite(unittest.TestCase):
    def setUp(self):
        if not (TOOLS / "check_demo_site.py").is_file():
            self.skipTest(NO_TOOLS)
        self.tool = load("check_demo_site")
        self.good = {"demo": {"errors": [], "text": 500, "shows_demo": True, "write": 403}, "lint": {"loaded": True, "errors": [], "rules": ["unpinned_uses", "injection"], "text": ""}}

    def test_a_site_that_works_has_no_mistake(self):
        self.assertEqual(self.tool.judge(self.good, []), [])

    def test_each_failure_is_named(self):
        for key, change in (("demo", {"write": 200}), ("demo", {"errors": ["error: x"]}), ("demo", {"shows_demo": False}), ("lint", {"loaded": False}), ("lint", {"rules": ["unpinned_uses"]})):
            reports = {**self.good, key: {**self.good[key], **change}}
            self.assertEqual(len(self.tool.judge(reports, [])), 1, change)
        self.assertEqual(len(self.tool.judge(self.good, ["/api/x"])), 1)
        self.assertEqual(len(self.tool.judge({}, [])), 2)

    def test_the_workflow_it_pastes_really_has_those_mistakes(self):
        from github_actions_monitor.cli import lint_workflows
        found = {row["rule"] for row in lint_workflows.lint_text(self.tool.WORKFLOW)}
        self.assertLessEqual(set(self.tool.EXPECTED_RULES), found)


class TheDemoWithTheParts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.child = None
        if not (TOOLS / "demo_parts.py").is_file():
            raise unittest.SkipTest(NO_TOOLS)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        cls.folder = tempfile.TemporaryDirectory(prefix="ghamon_parts_", ignore_cleanup_errors=True)
        env = {**os.environ, "MONITOR_DATA_DIR": cls.folder.name, "PYTHONDONTWRITEBYTECODE": "1"}
        cls.child = subprocess.Popen([sys.executable, str(TOOLS / "demo_monitor.py"), str(port), "--parts"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.base = f"http://127.0.0.1:{port}"
        limit = time.time() + 60
        while True:
            try:
                urllib.request.urlopen(cls.base + "/api/health", timeout=2).read()
                return
            except OSError:
                if time.time() > limit or cls.child.poll() is not None:
                    cls.tearDownClass()
                    raise AssertionError("the demo did not start")
                time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        if cls.child is not None:
            cls.child.terminate()
            cls.child.wait(timeout=20)
            cls.folder.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=15) as answer:
            return json.loads(answer.read())

    def test_every_box_has_something_to_show(self):
        actions = self.get("/api/actions/state")
        self.assertTrue(actions["enabled"] and actions["proposals"] and actions["waiting"]["person"] and actions["pulls"])
        self.assertIn("keep_alive", {p["why"] for p in actions["proposals"]})
        posture = self.get("/api/posture")
        self.assertTrue(posture["enabled"] and any(r["findings"] for r in posture["repos"]) and posture["history"])
        self.assertTrue(self.get("/api/ai/actions")["proposals"])
        extras = self.get("/api/assistant/extras")
        self.assertTrue(extras["chat"] and extras["actions"] and extras["copy_report"])
        self.assertIn("demo-badges", {p["name"] for p in self.get("/api/plugins/catalog")["plugins"]})
        self.assertTrue(self.get("/api/fleet/columns")["rows"])
        self.assertEqual(self.get("/api/fleet/group?slug=alpha")["state"], "red")


if __name__ == "__main__":
    unittest.main()
