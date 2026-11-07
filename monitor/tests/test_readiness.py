# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Layer A11 (readiness.py): release readiness, ecosystem health, dependency pins. Offline; the pins are read from a temporary tree."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import _testenv  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import actions_monitor  # noqa: E402
import i18n  # noqa: E402
import readiness  # noqa: E402
import sentinel_local as sl  # noqa: E402
import toolconfig  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc)


def run(repo, name, conclusion, started, path="ci.yml", rid=1, sha="abc1234def"):
    return {"repo": repo, "id": rid, "name": name, "path": path, "branch": "main", "status": "completed", "conclusion": conclusion, "started": started,
            "url": f"https://github.com/JuanenRac/{repo}/actions/runs/{rid}", "seconds": 60, "actor": "JuanenRac", "sha": sha}


def info(tag="v0.1.0"):
    return {"branch": "main", "pushed": "2026-11-04T10:00:00Z", "release": {"tagName": tag, "publishedAt": "2026-10-01T00:00:00Z"}, "vuln_total": 0, "vuln_sev": {},
            "prs": [], "rulesets": [{"name": "protect-main", "enforcement": "ACTIVE"}], "label_dependencies": True,
            "files": {"README.md": True, "LICENSE.md": True, "CHANGELOG.md": True, "SECURITY.md": True}}


def snapshot(**over):
    repos = over.pop("repos", ["ARMOR-A", "ARMOR-B", "URTC-C"])
    inp = {"now": NOW, "today": "2026-11-04", "cfg": sl.DEFAULTS, "repos": repos, "eco": {r: toolconfig.ecosystem_of(r) for r in repos},
           "repo_info": {r: info() for r in repos}, "alerts": {r: {"at": 1, "codeql": [], "secret": 0} for r in repos}, "perms": {},
           "runs": {r: [run(r, "CI", "success", "2026-11-04T09:00:00Z")] for r in repos},
           "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}}, "history": {"days": {}}, "unreleased": {}, "targets": {}, "errors": {}, "loading": "",
           "audits": None}
    inp.update(over)
    return sl.compute_snapshot(inp)


class Rules(unittest.TestCase):
    def test_versions_compare_by_number_and_ignore_trailing_zeros(self):
        self.assertTrue(readiness.older("0.8.0.7", "0.8.0.8"))
        self.assertTrue(readiness.older("v0.9.0", "0.10.0"))
        self.assertFalse(readiness.older("1.2", "1.2.0"))
        self.assertFalse(readiness.older("abc", "1.0.0"))   # unreadable: never "behind"
        self.assertFalse(readiness.older("1.0.0", ""))

    def test_a_ready_repository_goes_through_the_steps(self):
        base = {"unreleased": {"ARMOR-A": 3}, "min_entries": 1, "eco_of": toolconfig.ecosystem_of, "releases": {"ARMOR-A": {"tagName": "v0.1.0"}},
                "runs": {"ARMOR-A": [run("ARMOR-A", "CI", "success", "2026-11-04T09:00:00Z")]}, "local_versions": {"ARMOR-A": "0.1.0"}}
        row = readiness.release_rows(base)[0]
        self.assertEqual((row["ci"], row["ci_sha"], row["bumped"], row["next"]), ("green", "abc1234", False, "bump"))
        row = readiness.release_rows({**base, "local_versions": {"ARMOR-A": "0.1.1"}})[0]
        self.assertEqual((row["bumped"], row["build"], row["next"]), (True, "no_build", "cut"))
        state = lambda st, **kw: [{"repo": "ARMOR-A", "state": st, **kw}]  # noqa: E731
        up = {**base, "local_versions": {"ARMOR-A": "0.1.1"}}
        self.assertEqual(readiness.release_rows({**up, "states": state("published")})[0]["next"], "build")
        self.assertEqual(readiness.release_rows({**up, "states": state("built_on_gha")})[0]["next"], "sign")
        row = readiness.release_rows({**up, "states": state("signed_local", trusted=True)})[0]
        self.assertEqual((row["signing"], row["next"]), ("signed", "publish"))
        row = readiness.release_rows({**up, "states": state("signed_local", trusted=False)})[0]
        self.assertEqual((row["signing"], row["next"]), ("unsigned", "sign"))

    def test_red_ci_blocks_and_missing_data_is_unknown_not_green(self):
        base = {"unreleased": {"ARMOR-A": 2, "ARMOR-B": 2}, "min_entries": 1, "eco_of": toolconfig.ecosystem_of, "releases": {}, "local_versions": {"ARMOR-A": "1.0.0", "ARMOR-B": "1.0.0"},
                "runs": {"ARMOR-A": [run("ARMOR-A", "CI", "failure", "2026-11-04T09:00:00Z", sha="deadbee1234")], "ARMOR-B": []},
                "red": [{"repo": "ARMOR-A", "sha": "deadbee1234"}], "unchecked": ["ARMOR-B"]}
        rows = {r["repo"]: r for r in readiness.release_rows(base)}
        self.assertEqual((rows["ARMOR-A"]["ci"], rows["ARMOR-A"]["ci_sha"], rows["ARMOR-A"]["next"], rows["ARMOR-A"]["ready"]), ("red", "deadbee", "fix_ci", False))
        self.assertEqual((rows["ARMOR-B"]["ci"], rows["ARMOR-B"]["next"], rows["ARMOR-B"]["ready"]), ("unknown", "wait_data", False))

    def test_entries_threshold_and_external_ecosystems(self):
        base = {"unreleased": {"ARMOR-A": 1, "ARMOR-B": 3, "EH3D-X": 9}, "min_entries": 2, "eco_of": toolconfig.ecosystem_of, "releases": {}, "runs": {}}
        self.assertEqual([r["repo"] for r in readiness.release_rows(base)], ["ARMOR-B"])   # EH3D is external: reported elsewhere

    def test_a_full_sample_is_said_to_be_partial(self):
        state, sha, partial = readiness.ci_state("R", [run("R", "CI", "success", "2026-11-04T09:00:00Z")], "main", {}, set(), {"R"})
        self.assertEqual((state, sha, partial), ("green", "abc1234def", True))


class Health(unittest.TestCase):
    def test_the_score_is_100_minus_the_weighted_counts_and_lists_the_parts(self):
        s = snapshot(runs={"ARMOR-A": [run("ARMOR-A", "CI", "failure", "2026-11-04T09:00:00Z")], "ARMOR-B": [run("ARMOR-B", "CI", "success", "2026-11-04T09:00:00Z")],
                           "URTC-C": [run("URTC-C", "CI", "success", "2026-11-04T09:00:00Z")]})
        rows = {h["ecosystem"]: h for h in s["a11"]["health"]}
        self.assertEqual(rows["armor"]["score"], 100 - 15)
        self.assertEqual([p["name"] for p in rows["armor"]["parts"]], ["red"])
        self.assertEqual(rows["urtc"]["score"], 100)
        self.assertEqual(rows["armor"]["coverage"], 1.0)

    def test_no_score_when_too_few_repositories_have_data(self):
        s = snapshot(alerts={}, runs={})
        self.assertTrue(all(h["score"] is None for h in s["a11"]["health"]))
        self.assertEqual(s["a11"]["low_health"], [])
        self.assertEqual(s["a11"]["sections"][1]["level"], "unknown")

    def test_a_low_score_warns_in_the_report_and_the_weights_come_from_the_configuration(self):
        runs = {r: [run(r, "CI", "failure", "2026-11-04T09:00:00Z"), run(r, "Build", "failure", "2026-11-04T09:00:00Z", path="b.yml", rid=2)] for r in ("ARMOR-A", "ARMOR-B")}
        s = snapshot(runs={**runs, "URTC-C": [run("URTC-C", "CI", "success", "2026-11-04T09:00:00Z")]})
        armor = next(h for h in s["a11"]["health"] if h["ecosystem"] == "armor")
        self.assertEqual(armor["score"], 100 - 4 * 15)
        self.assertEqual(s["a11"]["low_health"], [{"ecosystem": "armor", "score": 40}])
        self.assertTrue(any("40" in p["text"] and p["level"] == "warn" for p in s["parte"]))
        cfg = readiness.settings({"sentinel": {"readiness": {"health": {"weights": {"red": 5, "bogus": 9, "stuck": -1}}, "warn_below": 30}}})
        self.assertEqual((cfg["health"]["weights"]["red"], cfg["health"]["weights"]["stuck"], cfg["warn_below"]), (5, 10, 30))
        self.assertNotIn("bogus", cfg["health"]["weights"])

    def test_the_snapshot_carries_a_release_row_and_the_ready_count(self):
        s = snapshot(unreleased={"ARMOR-A": 2}, local_versions={"ARMOR-A": "0.2.0"})
        self.assertEqual((s["a11"]["ready"], s["a11"]["rows"][0]["next"]), (1, "cut"))
        self.assertEqual(s["a11"]["sections"][0]["rows"][0][0], "ARMOR-A")
        self.assertIn("a11", s)

    def test_the_layer_can_be_switched_off(self):
        cfg = {**sl.DEFAULTS, "readiness": {**readiness.DEFAULTS, "enabled": False}}
        s = snapshot(cfg=cfg)
        self.assertFalse(s["a11"]["enabled"])
        self.assertEqual(s["a11"]["level"], "unknown")


class Pins(unittest.TestCase):
    def tree(self, root):
        def put(rel, data):
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        put("ARMOR-COMMON/armor.project.json", {"version": "0.8.0.8"})
        put("ARMOR-COMMON/registry/contract_pins.json", {"consumers": {"ARMOR-A": "0.8.0.7", "ARMOR-B": "0.8.0.8", "ARMOR-GONE": "0.1.0"}})
        put("URTC-COMMON/pyproject.toml", '[project]\nname = "x"\nversion = "0.2.3"\n')
        put("URTC-C/tools/x.lock.json", {"urtc_common_version": "0.2.3"})
        put("URTC-C/src/deep/x.lock.json", {"urtc_common_version": "0.1.9"})
        put("URTC-C/node_modules/pkg/x.lock.json", {"urtc_common_version": "0.0.1"})   # skipped folder
        put("URTC-D/x.lock.json", {"urtc_common_version": "0.2.3"})
        return {"sources": [{"ecosystem": "armor", "kind": "pin_table", "provider": "ARMOR-COMMON", "file": "registry/contract_pins.json", "key": "consumers"},
                            {"ecosystem": "urtc", "kind": "lock_files", "provider": "URTC-COMMON", "lock_name": "x.lock.json", "version_key": "urtc_common_version"}],
                "max_depth": 5, "skip_dirs": ["node_modules"], "refresh_seconds": 60}

    def test_pins_are_read_from_the_files_and_the_oldest_lock_counts(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = self.tree(Path(d))
            names = ["ARMOR-COMMON", "ARMOR-A", "ARMOR-B", "URTC-COMMON", "URTC-C", "URTC-D", "HYDRA-UMC-X"]
            out = readiness.read_pins(Path(d), names, toolconfig.ecosystem_of, cfg)
        by = {r["repo"]: r for r in out["rows"]}
        self.assertEqual(set(by), {"ARMOR-A", "ARMOR-B", "URTC-C", "URTC-D"})   # ARMOR-GONE is not a repository of the workspace
        self.assertTrue(by["ARMOR-A"]["behind"] and not by["ARMOR-B"]["behind"])
        self.assertEqual((by["URTC-C"]["pinned"], by["URTC-C"]["where"], by["URTC-C"]["behind"]), ("0.1.9", "src/deep/x.lock.json", True))
        self.assertFalse(by["URTC-D"]["behind"])
        self.assertEqual(out["no_source"], ["hydra"])   # honest: no pin source for HYDRA-UMC, nothing guessed
        self.assertEqual(out["missing"], [])

    def test_a_missing_provider_is_reported_not_invented(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = self.tree(Path(d))
            out = readiness.read_pins(Path(d) / "nowhere", ["ARMOR-A"], toolconfig.ecosystem_of, cfg)
        self.assertEqual((out["rows"], out["missing"]), ([], ["ARMOR-COMMON", "URTC-COMMON"]))

    def test_the_snapshot_lists_the_pins_that_are_behind(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = self.tree(Path(d))
            pins = readiness.read_pins(Path(d), ["ARMOR-COMMON", "ARMOR-A", "ARMOR-B", "URTC-COMMON", "URTC-C"], toolconfig.ecosystem_of, cfg)
        s = snapshot(pins=pins)
        self.assertEqual(s["a11"]["behind_repos"], ["ARMOR-A", "URTC-C"])
        self.assertEqual(s["a11"]["sections"][2]["rows"][0][:4], ["ARMOR-A", "ARMOR-COMMON", "0.8.0.7", "0.8.0.8"])
        self.assertTrue(any(p["level"] == "info" and "ARMOR-A" in p["text"] for p in s["parte"]))

    def test_local_version_reads_the_manifest_then_pyproject_then_the_changelog(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a").mkdir()
            (root / "a" / "x.project.json").write_text('{"version": "2.0.0"}', encoding="utf-8")
            (root / "a" / "CHANGELOG.md").write_text("## [Unreleased]\n- x\n## [1.0.0]\n", encoding="utf-8")
            (root / "b").mkdir()
            (root / "b" / "CHANGELOG.md").write_text("## [Unreleased]\n- x\n\n## [1.5.2] - text\n", encoding="utf-8")
            (root / "c").mkdir()
            self.assertEqual((readiness.local_version(root / "a"), readiness.local_version(root / "b"), readiness.local_version(root / "c")), ("2.0.0", "1.5.2", ""))

    def test_the_settings_keep_only_valid_sources(self):
        cfg = readiness.settings({"sentinel": {"readiness": {"pins": {"sources": [{"ecosystem": "a", "kind": "lock_files", "provider": "P"}, {"kind": "x"}, "junk"], "max_depth": 0}}}})
        self.assertEqual(len(cfg["pins"]["sources"]), 1)
        self.assertEqual(cfg["pins"]["max_depth"], 5)
        self.assertEqual(readiness.DEFAULTS["pins"]["sources"], [])   # the shipped default carries no source


class PageAndCatalogues(unittest.TestCase):
    KEYS = (["ui.a11", "ui.a11_title", "ui.a11_disabled", "ui.sc_a11", "parte.a11_health", "parte.a11_pins", "rd.off", "rd.note.readiness", "rd.note.health",
             "rd.note.pins_read", "rd.note.pins_missing", "rd.note.pins_none", "rd.note.no_workspace"]
            + [f"rd.t.{x}" for x in ("readiness", "health", "pins")]
            + [f"rd.c.{c}" for cols in readiness.COLUMNS.values() for c in cols]
            + [f"rd.v.{x}" for x in ("green", "green_partial", "red", "unknown", "bumped", "no_release", "not_bumped", "no_build", "built", "build_needed", "sign_na", "sign_signed", "sign_unsigned")]
            + [f"rd.n.{x}" for x in ("fix_ci", "wait_data", "bump", "build", "sign", "publish", "cut")]
            + [f"rd.p.{x}" for x in ("red", "stuck", "secret", "high_alert", "alert", "stale_pr", "unsigned", "hygiene", "none")])

    def test_every_text_exists_in_the_eight_languages(self):
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            data = json.loads((HERE / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for key in self.KEYS:
                self.assertTrue(data.get(key), f"{lang}:{key}")

    def test_every_dynamic_key_the_code_builds_is_in_the_catalogue(self):
        en = json.loads((HERE / "locales" / "en.json").read_text(encoding="utf-8"))
        for ci in ("green", "red", "unknown", "green_partial"):
            self.assertIn("rd.v." + ci, en)
        for nxt in set(readiness.NEXT_FOR_CI.values()) | {"bump", "build", "sign", "publish", "cut"}:
            self.assertIn("rd.n." + nxt, en)

    def test_the_page_renders_the_panel_and_the_version_is_shown_as_github_actions(self):
        page = actions_monitor.render_page()
        for needle in ('"ui.a11_title"', 'section("a11"', '["a11","ui.a11"'):
            self.assertIn(needle, page)
        self.assertIn('"version": "1.5.0"', page)
        self.assertEqual(i18n.t("mon.version", version="1.5.0"), "GitHub Actions v1.5.0")
        html = (HERE / "actions_monitor.html").read_text(encoding="utf-8")
        self.assertIn('<h1>GitHub Actions <small class="mut" id="ver">', html)

    def test_the_section_titles_are_translated(self):
        s = snapshot()
        with i18n.use_language("de"):
            s_de = snapshot()
        self.assertNotEqual(s["a11"]["sections"][0]["title"], s_de["a11"]["sections"][0]["title"])


if __name__ == "__main__":
    unittest.main()
