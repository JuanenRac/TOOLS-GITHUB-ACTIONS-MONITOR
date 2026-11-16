# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The batch launcher of Windows: an empty Enter at its menu must not repeat the last option (cmd keeps the old value of the variable when nothing is typed)."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
BAT = HERE / "BATCH_GITHUB_ACTIONS.bat"


class BatchMenu(unittest.TestCase):
    def test_the_variable_of_the_option_is_cleared_before_it_is_asked(self):
        lines = [x.strip() for x in BAT.read_text(encoding="utf-8").splitlines()]
        asks = [i for i, x in enumerate(lines) if x.lower().startswith("set /p op=")]
        self.assertTrue(asks)
        for i in asks:
            self.assertEqual(lines[i - 1].lower(), 'set "op="', "set /p keeps the old value on an empty Enter")

    @unittest.skipUnless(sys.platform == "win32" and shutil.which("py"), "runs the real launcher with cmd")
    def test_an_empty_enter_runs_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(BAT, root / BAT.name)
            pkg = root / "src" / "github_actions_monitor" / "cli"
            pkg.mkdir(parents=True)
            (root / "src" / "github_actions_monitor" / "__init__.py").write_text("", encoding="utf-8")
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (pkg / "launcher_msg.py").write_text("import sys\nprint('Choose:' if sys.argv[1] == 'choose' else 'MENU')\n", encoding="utf-8")
            (pkg / "gha_dispatch_all.py").write_text("import sys\nprint('CALL ' + ' '.join(sys.argv[1:]))\n", encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            proc = subprocess.Popen(["cmd", "/c", str(root / BAT.name)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=tmp)
            try:
                out, _ = proc.communicate("2\r\n\r\n6\r\n", timeout=15)      # the menu may go on asking after the input ends: only what it ran matters
            except subprocess.TimeoutExpired:
                proc.kill()
                out = proc.communicate()[0]
            self.assertEqual(out.count("CALL dispatch --go"), 1, out[:600])


if __name__ == "__main__":
    unittest.main()
