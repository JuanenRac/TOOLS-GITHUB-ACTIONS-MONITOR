# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The container checks are one list in four places (the plan, the script that runs them all, the text that explains them and the workflow that keeps their evidence): they cannot drift apart, and the
check of the locks between processes inside the container (E9) is in all of them. A real Docker is not needed here: it is the lists that are compared."""
import importlib.util
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT = ROOT / "tools" / "docker_audit"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _testenv  # noqa: F401,E402


def load_plan():
    spec = importlib.util.spec_from_file_location("docker_audit_plan", AUDIT / "plan.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(AUDIT.is_dir() and (ROOT / ".github" / "workflows").is_dir(), "needs the repository root (tools/docker_audit, .github/workflows), not part of the installed zip")
class OneList(unittest.TestCase):
    def test_every_check_has_its_script_and_is_run_and_explained(self):
        plan = load_plan()
        runner = (AUDIT / "run_all.sh").read_text(encoding="utf-8")
        text = (AUDIT / "LEEME.txt").read_text(encoding="utf-8")
        for code, (script, minutes, title) in plan.SCENARIOS.items():
            self.assertTrue((AUDIT / script).is_file(), script)
            self.assertIn(f"[{code}]={script}", runner, code)
            self.assertRegex(text, rf"(?m)^{code} {re.escape(script)}", code)
            self.assertGreater(minutes, 0)
        only = re.search(r'ONLY="([^"]+)"', runner).group(1).split(",")
        self.assertEqual(only, list(plan.SCENARIOS))

    def test_the_locks_between_processes_are_checked_in_the_container_and_kept_as_evidence(self):
        plan = load_plan()
        self.assertIn("E9", plan.SCENARIOS)
        self.assertEqual(plan.plan(str(ROOT), "v1.0.0", "all", "none")["codes"].split(",")[-1], "E9")
        evidence = (ROOT / ".github" / "workflows" / "evidence.yml").read_text(encoding="utf-8")
        self.assertRegex(evidence, r"--only E3,E6,E9")
        script = (AUDIT / "e9_shared_files.py").read_text(encoding="utf-8")
        for needle in ("os_lock", "process_lock", "== 160", "killed"):
            self.assertIn(needle, script)

    def test_the_script_of_the_locks_compiles(self):
        compile((AUDIT / "e9_shared_files.py").read_text(encoding="utf-8"), "e9_shared_files.py", "exec")


if __name__ == "__main__":
    unittest.main()
