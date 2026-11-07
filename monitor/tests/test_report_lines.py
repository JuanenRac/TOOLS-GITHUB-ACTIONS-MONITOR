# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Version 1.4.5: the report says when the snapshot is incomplete (stable code), summarises signing (waiting / verified / build-only) and says when A10 is paused for the quota."""
import sys
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import i18n  # noqa: E402
import sentinel_local as sl  # noqa: E402
from test_sentinel import NOW, run  # noqa: E402


def snapshot(**over):
    info = {"R": {"branch": "main", "pushed": "2026-11-04T10:00:00Z", "release": {"tagName": "v1", "publishedAt": "2026-10-01T00:00:00Z"}, "vuln_total": 0, "vuln_sev": {},
                  "prs": [], "rulesets": [], "label_dependencies": True, "files": {}}}
    inp = {"now": NOW, "today": "2026-11-04", "cfg": sl.DEFAULTS, "repos": ["R"], "eco": {"R": "armor"}, "repo_info": info,
           "alerts": {"R": {"at": 1, "codeql": [], "secret": 0}}, "perms": {}, "runs": {"R": [run("R", "CI", "success", "2026-11-04T09:00:00Z")]},
           "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}}, "history": {"days": {}}, "unreleased": {}, "targets": {}, "errors": {}, "loading": "", "audits": None}
    inp.update(over)
    return sl.compute_snapshot(inp)


def codes(s):
    return [line.get("code") for line in s["parte"] if line.get("code")]


class IncompleteSnapshot(unittest.TestCase):
    def test_a_complete_snapshot_has_no_incomplete_line(self):
        self.assertNotIn("incomplete", codes(snapshot()))

    def test_loading_makes_the_snapshot_incomplete_and_the_line_comes_first_after_the_headline(self):
        s = snapshot(loading="30/129")
        self.assertIn("incomplete", codes(s))
        self.assertTrue(s["parte"][0].get("head"))
        self.assertEqual(s["parte"][1].get("code"), "incomplete")

    def test_errors_make_it_incomplete(self):
        self.assertIn("incomplete", codes(snapshot(errors={"graphql": {"message": "boom", "at": "12:00:00"}})))

    def test_every_language_has_the_texts(self):
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                for key in ("parte.incomplete", "parte.sign_summary", "parte.a10_paused"):
                    self.assertNotEqual(i18n.t(key, why="x", pending=1, verified=1, unchecked=0, bad=0, build_only=2, remaining=5, needed=9), key, (lang, key))


class A10Paused(unittest.TestCase):
    def test_a_paused_cold_scan_is_said(self):
        s = snapshot(surface_paused={"remaining": 900, "needed": 1600})
        self.assertIn("a10_paused", codes(s))
        text = next(line["text"] for line in s["parte"] if line.get("code") == "a10_paused")
        self.assertIn("900", text)
        self.assertIn("1600", text)

    def test_no_pause_no_line(self):
        self.assertNotIn("a10_paused", codes(snapshot()))


if __name__ == "__main__":
    unittest.main()


class TagAheadOfManifest(unittest.TestCase):
    """1.5.0: a release tag that is ahead of the version of the manifest has its own line in the report (stable code tag_vs_manifest)."""

    def with_rows(self, rows):
        import surface
        real = surface.build

        def fake(inp):
            block = real(inp)
            block["sections"] = [dict(sec, rows=rows, count=len(rows)) if sec["key"] == "tag_vs_version" else sec for sec in block["sections"]]
            return block

        with unittest.mock.patch.object(surface, "build", fake):
            return snapshot()

    def test_the_line_names_the_repositories(self):
        ahead = i18n.t("surf.tag_after")
        s = self.with_rows([["R-ONE", "v2", "1.0", "1.0", ahead], ["R-TWO", "v1", "2.0", "2.0", i18n.t("surf.tag_before")]])
        line = next(l for l in s["parte"] if l.get("code") == "tag_vs_manifest")
        self.assertEqual(line["level"], "warn")
        self.assertIn("R-ONE", line["text"])
        self.assertNotIn("R-TWO", line["text"])

    def test_no_line_when_no_tag_is_ahead(self):
        self.assertNotIn("tag_vs_manifest", codes(self.with_rows([])))
        self.assertNotIn("tag_vs_manifest", codes(self.with_rows([["R", "v1", "2.0", "2.0", i18n.t("surf.tag_before")]])))

    def test_every_language_has_the_text(self):
        for lang in i18n.LANGS:
            with i18n.use_language(lang):
                self.assertNotEqual(i18n.t("parte.tag_vs_manifest", n=1, list="R"), "parte.tag_vs_manifest")
