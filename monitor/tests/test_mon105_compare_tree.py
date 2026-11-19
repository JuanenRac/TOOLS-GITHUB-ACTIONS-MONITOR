# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""tools/compare_tree.py: a package is compared with a git ref by content (line endings and JSON layout do not count; a real change, a missing file and an extra file do)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE.parent / "tools"))
try:
    import compare_tree  # noqa: E402
except ImportError:      # the tools folder does not travel in the zip of a release
    compare_tree = None


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], check=True, capture_output=True)


@unittest.skipIf(compare_tree is None, "tools/ is not in this package")
class CompareTree(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.repo = Path(self.tmp.name) / "repo"
        (self.repo / "monitor" / "sub").mkdir(parents=True)
        (self.repo / "monitor" / "a.py").write_bytes(b"x = 1\ny = 2\n")
        (self.repo / "monitor" / "sub" / "c.json").write_text(json.dumps({"b": 1, "a": [1, 2]}, indent=2), encoding="utf-8")
        git(self.repo, "init", "-q")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "x")
        self.ref = "HEAD"

    def tearDown(self):
        self.tmp.cleanup()

    def package(self, files):
        folder = Path(self.tmp.name) / "pkg"
        for name, data in files.items():
            target = folder / "github_actions_monitor" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return folder

    def run_compare(self, path):
        return compare_tree.compare(compare_tree.read_package(path, "github_actions_monitor"), compare_tree.read_ref(self.repo, self.ref, "monitor"))

    def test_same_content_with_other_line_endings_and_json_layout_is_the_same(self):
        folder = self.package({"a.py": b"x = 1\r\ny = 2\r\n", "sub/c.json": b'{"a":[1,2],"b":1}'})
        self.assertEqual(self.run_compare(folder), ([], [], []))

    def test_a_changed_a_missing_and_an_extra_file_are_found(self):
        folder = self.package({"a.py": b"x = 1\ny = 3\n", "extra.txt": b"hi"})
        self.assertEqual(self.run_compare(folder), (["extra.txt"], ["sub/c.json"], ["a.py"]))

    def test_a_json_with_other_data_is_different(self):
        folder = self.package({"a.py": b"x = 1\ny = 2\n", "sub/c.json": b'{"a":[1,2],"b":2}'})
        self.assertEqual(self.run_compare(folder)[2], ["sub/c.json"])

    def test_a_zip_is_read_like_a_folder_and_the_command_answers_with_the_exit_code(self):
        archive = Path(self.tmp.name) / "p.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("github_actions_monitor/a.py", "x = 1\r\ny = 2\r\n")
            z.writestr("github_actions_monitor/sub/c.json", '{"b": 1, "a": [1, 2]}')
        self.assertEqual(self.run_compare(archive), ([], [], []))
        env = {**os.environ, "PYTHONUTF8": "1"}
        done = subprocess.run([sys.executable, "-I", str(HERE.parent / "tools" / "compare_tree.py"), str(archive), "--repo", str(self.repo)], capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("COMPARE=SAME", done.stdout)
        done = subprocess.run([sys.executable, "-I", str(HERE.parent / "tools" / "compare_tree.py"), str(archive), "--ref", "nope", "--repo", str(self.repo)], capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 2)

    def test_ignore_skips_names(self):
        folder = self.package({"a.py": b"x = 1\ny = 2\n", "sub/c.json": b'{"a":[1,2],"b":1}', "extra.txt": b"hi"})
        got = compare_tree.compare(compare_tree.read_package(folder, "github_actions_monitor"), compare_tree.read_ref(self.repo, self.ref, "monitor"), ["extra.*"])
        self.assertEqual(got, ([], [], []))


if __name__ == "__main__":
    unittest.main()
