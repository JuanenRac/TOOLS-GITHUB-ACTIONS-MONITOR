# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The harness for reviewers (tools/audit_harness.py): three accounts, four users and no GitHub; its own check passes and the table it prints names every user."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TOOL = ROOT / "tools" / "audit_harness.py"


@unittest.skipUnless(TOOL.is_file(), "the tools of the repository are not here")
class Harness(unittest.TestCase):
    def test_the_check_passes_and_names_the_four_users(self):
        with tempfile.TemporaryFile("w+", encoding="utf-8") as sink:      # a file, not a pipe: the stand-in monitors must not keep a pipe open
            done = subprocess.run([sys.executable, "-I", str(TOOL), "--check"], stdout=sink, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=120, cwd=str(ROOT))
            sink.seek(0)
            text = sink.read()
        self.assertEqual(done.returncode, 0, text)
        self.assertIn("AUDIT_HARNESS=PASS", text)
        for name in ("admin", "maintainer", "viewer", "inactive"):
            self.assertIn(name, text)
        self.assertNotIn("WRONG", text)


if __name__ == "__main__":
    unittest.main()
