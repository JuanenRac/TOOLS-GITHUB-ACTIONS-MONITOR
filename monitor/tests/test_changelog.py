# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The history: every version has its section, grouped under the usual headings and in English, every guide is mentioned, and the copy at the root of the repository is the generated one."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import tool_version  # noqa: E402

TEXT = (HERE / "CHANGELOG.md").read_text(encoding="utf-8").replace("\r\n", "\n")
GROUPED_SINCE = (1, 5, 1)


def version_key(v):
    return tuple(int(x) for x in v.split("."))


class History(unittest.TestCase):
    def test_the_top_version_is_the_version_of_the_tool_and_none_is_missing_or_repeated(self):
        found = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", TEXT, re.M)
        self.assertEqual(found[0], tool_version.TOOL_VERSION)
        self.assertEqual(len(found), len(set(found)))
        self.assertEqual(found, sorted(found, key=version_key, reverse=True))
        self.assertEqual(found[-1], "1.0.0")

    def test_the_manifest_and_the_tag_have_their_section(self):
        manifest = REPO / "electro-hobby-3d.project.json"
        if not manifest.is_file():
            self.skipTest("the manifest lives in the repository")
        version = json.loads(manifest.read_text(encoding="utf-8"))["version"]
        self.assertIn("## [%s]" % version, TEXT)
        done = subprocess.run(["git", "tag", "--list", "v*"], cwd=REPO, capture_output=True, text=True)
        if done.returncode == 0:
            for tag in done.stdout.split():
                if re.fullmatch(r"v\d+\.\d+\.\d+", tag):
                    self.assertIn("## [%s]" % tag[1:], TEXT, tag)

    def test_the_manifest_version_is_the_version_of_the_tool(self):
        manifest = REPO / "electro-hobby-3d.project.json"
        if not manifest.is_file():
            self.skipTest("the manifest lives in the repository")
        self.assertEqual(json.loads(manifest.read_text(encoding="utf-8"))["version"], tool_version.TOOL_VERSION)

    def test_the_dashboard_notice_waits_for_a_green_ci_and_an_optional_secret(self):
        flow = REPO / ".github" / "workflows" / "dashboard-dispatch.yml"
        if not flow.is_file():
            self.skipTest("the workflows live in the repository")
        text = flow.read_text(encoding="utf-8")
        for needle in ("      - CI", "permissions: {}", "conclusion == 'success'", "event == 'push'", "ECOSYSTEM_DASHBOARD_DISPATCH_TOKEN", "exit 0"):
            self.assertIn(needle, text, needle)

    def test_recent_versions_are_grouped_and_every_section_has_content(self):
        for match in re.finditer(r"^## \[(\d+\.\d+\.\d+)\]\n(.*?)(?=^## \[|\Z)", TEXT, re.S | re.M):
            version, body = match.group(1), match.group(2)
            self.assertTrue(re.search(r"^\s*(- |\||\S)", body.strip() or " ", re.M) and body.strip(), version)
            if version_key(version) >= GROUPED_SINCE:
                heads = re.findall(r"^### (\w+)", body, re.M)
                self.assertTrue(heads and set(heads) <= {"Added", "Changed", "Fixed", "Security", "Removed", "Deprecated"}, (version, heads))

    def test_the_whole_history_is_in_english(self):
        letters = [line[:80] for line in TEXT.split("\n") if re.search("[áéíóúñ¿¡«»぀-ヿ一-鿿]", line)]
        self.assertEqual(letters, [])

    def test_every_guide_is_mentioned(self):
        for guide in sorted({re.sub(r"_(deu|fra|ita|jpn|por|spa|zho)$", "", p.stem) for p in (HERE / "docs").glob("*.md")}):
            words = re.escape(guide).replace("_", r"[_ ]")
            self.assertRegex(TEXT, re.compile(words, re.I), guide)

    def test_the_root_changelog_is_the_generated_copy_and_a_release_can_take_its_notes(self):
        if not (REPO / "tools" / "sync_changelog.py").is_file():
            self.skipTest("the tools live in the repository")
        done = subprocess.run([sys.executable, str(REPO / "tools" / "sync_changelog.py"), "--check"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        notes = subprocess.run([sys.executable, str(REPO / "tools" / "sync_changelog.py"), "--notes", tool_version.TOOL_VERSION], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(notes.returncode, 0)
        self.assertIn("### Added", notes.stdout)
        self.assertNotIn("## [", notes.stdout)


if __name__ == "__main__":
    unittest.main()
