# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The zizmor job of the repository calls the shared reusable workflow pinned by a full commit SHA, with no permission beyond reading and failing only from high."""
import re
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "zizmor.yml"


class ZizmorJob(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_calls_the_shared_workflow_by_full_sha(self):
        self.assertRegex(self.text, r"uses: JuanenRac/JuanenRac/\.github/workflows/zizmor\.yml@[0-9a-f]{40}\b")
        self.assertNotRegex(self.text, r"zizmor\.yml@(main|master|v\d)")

    def test_least_privilege_and_threshold(self):
        self.assertRegex(self.text, r"(?m)^permissions: \{\}")
        self.assertRegex(self.text, r"(?m)^      contents: read$")
        self.assertEqual(re.findall(r"min-severity: (\w+)", self.text), ["high"])
        self.assertNotRegex(self.text, r"secrets\.")

    def test_runs_on_pull_requests_and_main_without_a_path_filter(self):
        self.assertIn("pull_request:", self.text)
        self.assertRegex(self.text, r"branches: \[main\]")
        self.assertNotIn("paths:", self.text)

    def test_config_file_exists(self):
        self.assertTrue((WORKFLOW.parent.parent / "zizmor.yml").is_file())


if __name__ == "__main__":
    unittest.main()
