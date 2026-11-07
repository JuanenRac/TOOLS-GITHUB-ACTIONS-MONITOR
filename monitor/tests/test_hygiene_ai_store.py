# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
import json
import tempfile
import unittest
import _testenv  # noqa: F401
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sentinel_ai
import sentinel_local


class LabelAndStore(unittest.TestCase):
    def node(self, labels):
        return {"name": "R", "labels": {"nodes": [{"name": n} for n in labels]}}

    def test_only_the_exact_label_counts(self):
        self.assertFalse(sentinel_local.parse_repo_node(self.node([]), [])["label_dependencies"])
        self.assertFalse(sentinel_local.parse_repo_node(self.node(["bug", "dependencies-js"]), [])["label_dependencies"])
        self.assertTrue(sentinel_local.parse_repo_node(self.node(["bug", "Dependencies"]), [])["label_dependencies"])

    def test_store_survives_a_corrupt_file_and_saves_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            path.write_text("{not json", encoding="utf-8")
            store = sentinel_ai.Store(path)
            self.assertEqual(store.used_today(), 0)
            store.add_call()
            store.save()
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["count"], 1)
            self.assertFalse((Path(tmp) / "cache.json.tmp").exists())
            path.write_text("[1,2]", encoding="utf-8")
            self.assertEqual(sentinel_ai.Store(path).data["entries"], {})


if __name__ == "__main__":
    unittest.main()


class A2Coverage(unittest.TestCase):
    def test_no_data_is_unchecked_and_full_samples_are_flagged(self):
        runs = {"A": [], "B": [{"x": 1}] * 10, "C": [{"x": 1}] * 3}
        self.assertEqual(sentinel_local.a2_unchecked(runs), ["A"])
        self.assertEqual(sentinel_local.a2_full_sample(runs, {"cold_runs_per_repo": 10, "runs_per_repo": 20}), ["B"])


class PendingSign(unittest.TestCase):
    def test_only_builds_that_waited_longer_than_the_limit_count(self):
        from datetime import datetime, timezone
        now = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
        green = [{"repo": "A", "since": "2026-11-03T12:00:00Z", "workflow": "w", "url": "u"},
                 {"repo": "B", "since": "2026-11-05T11:00:00Z", "workflow": "w", "url": "u"}]
        rows = sentinel_local.pending_sign(green, now, 24)
        self.assertEqual([r["repo"] for r in rows], ["A"])
        self.assertEqual(rows[0]["hours"], 48.0)


class ReleaseRules(unittest.TestCase):
    def test_green_without_release_needs_a_newer_green_run_than_the_release(self):
        targets = {"R": {"repo": "R", "workflow": "build.yml"}}
        run = lambda started, ok="success", branch="main": {"path": "build.yml", "branch": branch, "status": "completed", "conclusion": ok, "started": started, "url": "u"}
        releases = {"R": {"tagName": "v1", "publishedAt": "2026-11-05T10:00:00Z"}}
        newer = sentinel_local.green_without_release(targets, {"R": [run("2026-11-05T11:00:00Z")]}, releases)
        self.assertEqual([g["repo"] for g in newer], ["R"])
        self.assertEqual(sentinel_local.green_without_release(targets, {"R": [run("2026-11-05T09:00:00Z")]}, releases), [])
        self.assertEqual(sentinel_local.green_without_release(targets, {"R": [run("2026-11-05T11:00:00Z", ok="failure")]}, releases), [])
        self.assertEqual(sentinel_local.green_without_release(targets, {"R": [run("2026-11-05T11:00:00Z", branch="feature")]}, releases), [])
        self.assertEqual([g["repo"] for g in sentinel_local.green_without_release(targets, {"R": [run("2026-11-05T11:00:00Z")]}, {})], ["R"])

    def test_release_candidates_rule_counts_entries_age_and_skips_prefixes(self):
        rows = sentinel_local.release_candidates_rule({"A": 5, "B": 2, "C": 4, "EH3D-X": 9, "D": 3},
                                                      {"A": 3.0, "B": 9.0, "C": 0.5, "D": None}, 2.0, 3, ("EH3D-",))
        self.assertEqual([r["repo"] for r in rows], ["A", "D"])   # B too few, C too recent, EH3D skipped; D never released

    def test_config_template_is_copied_when_the_json_is_missing(self):
        import actions_monitor
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "actions_monitor.example.json").write_text(json.dumps({"refresh_seconds": 77}), encoding="utf-8")
            old_file, old_here = actions_monitor.CONFIG_FILE, actions_monitor.HERE
            actions_monitor.CONFIG_FILE, actions_monitor.HERE = tmp / "actions_monitor.json", tmp
            try:
                config = actions_monitor.load_config()
            finally:
                actions_monitor.CONFIG_FILE, actions_monitor.HERE = old_file, old_here
            self.assertEqual(config["refresh_seconds"], 77)
            self.assertTrue((tmp / "actions_monitor.json").is_file())


class RedCriterion(unittest.TestCase):
    def test_same_red_set_as_the_public_dashboard(self):
        import re
        import workspace
        if not workspace.available():
            self.skipTest("integration test: needs the workspace of the repositories")
        scripts = workspace.workspace_root() / "JuanenRac" / "scripts"
        rules, watch = scripts / "ci_rules.py", scripts / "ci_watch.py"
        if rules.is_file():   # the dashboard keeps ONE definition of red in ci_rules.py
            match = re.search(r"^RED_CONCLUSIONS = \(([^)]*)\)", rules.read_text(encoding="utf-8"), re.M)
        elif watch.is_file():
            match = re.search(r"^RED = \{([^}]*)\}", watch.read_text(encoding="utf-8"), re.M)
        else:
            self.skipTest("the profile repository is not next to this one")
        if match is None:
            self.skipTest("the profile repository keeps its definition of red in a form this test does not read")
        dashboard = set(re.findall(r'"([a-z_]+)"', match.group(1)))
        self.assertEqual(dashboard, set(sentinel_local.BAD))
        self.assertFalse(set(sentinel_local.BAD) & set(sentinel_local.IGNORED))


class ByEcosystem(unittest.TestCase):
    def test_every_ecosystem_has_a_row_even_with_nothing_to_report(self):
        s = {"a1": {"stuck": []}, "a2": {"red": [{"repo": "EH3D-X"}]}, "a3": {"rows": [{"repo": "ARMOR-A", "codeql": 2, "dependabot": 1, "secret": 0}]},
             "a4": {"dependabot": [{"repo": "URTC-B"}]}, "a5": {"candidates": [{"repo": "EH3D-X"}], "pending_sign": []}, "a6": {"rows": [{"repo": "HYDRA-UMC-H", "problems": [("x", "y")]}]}}
        eco = {"EH3D-X": "eh3d", "ARMOR-A": "armor", "URTC-B": "urtc", "HYDRA-UMC-H": "hydra", "URTC-C": "urtc"}
        rows = sentinel_local.ecosystem_summary(s, eco)
        self.assertEqual(sorted(rows), ["armor", "eh3d", "hydra", "urtc"])
        self.assertEqual((rows["eh3d"]["red"], rows["eh3d"]["candidates"], rows["eh3d"]["repos"]), (1, 1, 1))
        self.assertEqual((rows["armor"]["alerts"], rows["urtc"]["prs"], rows["urtc"]["repos"], rows["hydra"]["hygiene"]), (3, 1, 2, 1))
