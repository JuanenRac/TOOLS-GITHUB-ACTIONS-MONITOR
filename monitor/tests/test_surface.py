# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Tests of version 1.2.0: hydra-sign / imgsig checks, the A10 surface layer (rules, collector with a fake gh, snapshot, events), exports, webhook,
batch profiles with canary and quota gate, build-only targets, release notes. Offline, no secrets (throw-away keys made in the test).
Run:  py -3 -I -m unittest discover -s tests"""
import base64
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
import _testenv  # noqa: F401
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import events as event_feed  # noqa: E402
import export_status  # noqa: E402
import gha_dispatch_all as gd  # noqa: E402
import make_release as mr  # noqa: E402
import monitor_link  # noqa: E402
import release_notes  # noqa: E402
import sentinel_local as sl  # noqa: E402
import sigverify  # noqa: E402
import surface  # noqa: E402
import webhook  # noqa: E402
from test_next_level import OTHER_SIGN, PUB, SIGN  # noqa: E402
from test_signstate import NOW, run, snapshot  # noqa: E402


def cfg(**checks):
    c = surface.settings({})
    for name, values in checks.items():
        c["checks"][name].update(values)
    return c


def stamp(days):
    return (NOW - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


class SignatureFormats(unittest.TestCase):
    def hydra_sign(self, folder, name, data, sign=SIGN):
        (folder / name).write_bytes(data)
        (folder / (name + ".sig")).write_text(base64.b64encode(sign(data)).decode() + "\n", encoding="ascii")

    def test_hydra_sign_is_checked_over_the_bytes_of_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.hydra_sign(folder, "tool-cli-linux", b"binary" * 1000)
            keys = {"hydra": PUB.hex()}
            self.assertIs(sigverify.verify_dir(folder, "hydra", keys), True)
            (folder / "tool-cli-linux").write_bytes(b"binary!")
            self.assertIs(sigverify.verify_dir(folder, "hydra", keys), False)       # definitive: it IS a hydra-sign line and it does not verify
            self.hydra_sign(folder, "tool-cli-linux", b"binary", sign=OTHER_SIGN)
            self.assertIs(sigverify.verify_dir(folder, "hydra", keys), False)
            self.assertEqual(sigverify.verify_dir(folder, "hydra", {}), "unknown")

    def test_shapes(self):
        good = base64.b64encode(b"\x01" * 64).decode()
        self.assertTrue(sigverify.is_hydra_sign(good))
        self.assertFalse(sigverify.is_hydra_sign("ab" * 64))                      # the hex package line is not a hydra-sign line
        self.assertFalse(sigverify.is_hydra_sign(good[:-4]))
        self.assertFalse(sigverify.is_hydra_sign(base64.b64encode(b"\x01" * 48).decode()))

    def test_file_verification_matches_memory_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f"
            path.write_bytes(b"hello")
            self.assertTrue(sigverify.ed25519_verify_file(PUB, path, SIGN(b"hello")))
            self.assertFalse(sigverify.ed25519_verify_file(PUB, path, SIGN(b"other")))
            self.assertFalse(sigverify.ed25519_verify_file(PUB, Path(tmp) / "missing", SIGN(b"hello")))

    def test_imgsig_only_its_format_is_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            put = lambda text: (folder / "fw.bin.imgsig").write_bytes(text)  # noqa: E731
            (folder / "fw.bin").write_bytes(b"x")
            put(b"ab" * 76 + b"\n")
            self.assertTrue(sigverify.imgsig_format(folder / "fw.bin.imgsig"))
            self.assertEqual(sigverify.verify_dir(folder, "urtc", {"urtc": PUB.hex()}), "unknown")   # well formed: the message needs the header, so unknown
            put(b"ab" * 76 + b"\r\n")
            self.assertFalse(sigverify.imgsig_format(folder / "fw.bin.imgsig"))
            self.assertIs(sigverify.verify_dir(folder, "urtc", {"urtc": PUB.hex()}), False)           # malformed: the bootloader would refuse it
            self.assertIsNone(sigverify.imgsig_format(folder / "nope"))

    def test_apk_stays_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.apk").write_bytes(b"PK")
            self.assertEqual(sigverify.verify_dir(Path(tmp), "armor", {"armor": PUB.hex()}), "unknown")


class WorkflowText(unittest.TestCase):
    YAML = """name: x
on:
  pull_request_target:
  schedule:
    - cron: '0 3 * * 1'
permissions: write-all
jobs:
  a:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - uses: actions/setup-python@%s
      - uses: ./local
      - uses: docker://alpine:3
  b:
    uses: owner/repo/.github/workflows/r.yml@main
""" % ("a" * 40)

    def test_scan(self):
        wf = surface.scan_workflow(self.YAML, "x.yml")
        self.assertEqual(wf["unpinned"], ["actions/checkout@v4"])
        self.assertEqual(wf["reusable_unpinned"], ["owner/repo/.github/workflows/r.yml@main"])
        self.assertTrue(wf["write_all"] and wf["prt"] and wf["prt_danger"])
        self.assertEqual(wf["cron"], ["0 3 * * 1"])

    def test_pull_request_target_without_the_pr_checkout_is_not_dangerous(self):
        wf = surface.scan_workflow("on:\n  pull_request_target:\njobs:\n  a:\n    steps:\n      - uses: actions/checkout@" + "b" * 40 + "\n", "y.yml")
        self.assertTrue(wf["prt"])
        self.assertFalse(wf["prt_danger"] or wf["write_all"] or wf["unpinned"] or wf["cron"])

    def test_scan_clone_reads_files_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "R"
            (repo / ".git").mkdir(parents=True)
            (repo / ".github" / "workflows").mkdir(parents=True)
            (repo / ".github" / "workflows" / "ci.yml").write_text(self.YAML, encoding="utf-8")
            (repo / "package.json").write_text("{}", encoding="utf-8")
            (repo / "r.project.json").write_text(json.dumps({"version": "1.2.3", "maturity": "established", "evidence": "none"}), encoding="utf-8")
            (repo / "CHANGELOG.md").write_text("# c\n## [Unreleased]\n- x\n## [1.2.3]\n- y\n", encoding="utf-8")
            scan = surface.scan_clone(repo)
            self.assertEqual(scan["stacks"], ["node"])
            self.assertFalse(scan["dependabot_yml"])
            self.assertEqual(scan["manifest"]["version"], "1.2.3")
            self.assertEqual(scan["changelog_top"], "1.2.3")
            self.assertIsNone(surface.scan_clone(Path(tmp) / "nope"))


class Rules(unittest.TestCase):
    def test_settings_merge_and_bad_types(self):
        c = surface.settings({"sentinel": {"surface": {"enabled": True, "refresh_seconds": "x", "checks": {"dead_schedule": {"days": 3, "bogus": 1}, "artifacts": "no"}}}})
        self.assertEqual(c["checks"]["dead_schedule"], {"enabled": True, "days": 3})
        self.assertEqual(c["refresh_seconds"], 86400)
        self.assertEqual(c["checks"]["artifacts"]["max_mb"], 500)
        self.assertFalse(surface.settings({"sentinel": {"surface": {"enabled": False}}})["enabled"])
        self.assertIsInstance(sl.sentinel_config({"sentinel": {"surface": {"checks": {"pr_human": {"days": 2}}}}})["surface"]["checks"]["pr_human"]["days"], int)

    def test_dead_schedule_needs_a_sample_that_covers_the_window(self):
        scan = {"workflows": [{"file": "n.yml", "cron": ["0 1 * * *"]}]}
        short = [run("R", "n", "success", stamp(2), path="n.yml")]
        rows, hidden = surface.dead_schedules(scan, short, 14, NOW)
        self.assertEqual((rows, hidden), ([], 1))                                  # cannot tell: the sample is only 2 days long
        wide = short + [run("R", "ci", "success", stamp(40), path="ci.yml", rid=2)]
        rows, hidden = surface.dead_schedules(scan, wide, 14, NOW)
        self.assertEqual(len(rows), 1)
        alive = wide + [{**run("R", "n", "success", stamp(3), path="n.yml", rid=3), "event": "schedule"}]
        self.assertEqual(surface.dead_schedules(scan, alive, 14, NOW), ([], 0))

    def test_stuck_concurrency(self):
        queued = [{**run("R", "w", None, stamp(0.2), path="w.yml", rid=i), "status": "queued"} for i in (1, 2)]
        self.assertEqual(surface.stuck_groups(queued, 60, NOW), [("w.yml", 2, 288)])
        self.assertEqual(surface.stuck_groups(queued[:1], 60, NOW), [])
        self.assertEqual(surface.stuck_groups(queued, 600, NOW), [])

    def test_matrix_os(self):
        jobs = [{"name": "build (windows-latest, 3.12)", "conclusion": "failure", "steps": [{"name": "README parity", "conclusion": "failure"}]},
                {"name": "build (ubuntu-latest, 3.12)", "conclusion": "success"}, {"name": "lint", "conclusion": "success"}]
        summary = surface.summarize_jobs(jobs)
        self.assertEqual((summary["failed_os"], summary["ok_os"]), (["windows"], ["linux"]))
        self.assertIn("README parity", summary["failed"])
        self.assertEqual(surface.os_of("build (macos-14)"), "macos")
        self.assertIsNone(surface.os_of("lint"))

    def test_artifacts(self):
        items = [{"size_in_bytes": 3 << 20, "expired": False, "created_at": stamp(5), "expires_at": stamp(-85)}, {"size_in_bytes": 9 << 20, "expired": True}]
        s = surface.artifacts_summary(items, NOW)
        self.assertEqual((s["count"], s["bytes"], s["retention_days"]), (1, 3 << 20, 90))

    def test_required_checks(self):
        runs = [{"name": "ci", "status": "completed", "conclusion": "failure"}, {"name": "lint", "status": "completed", "conclusion": "success"}]
        self.assertEqual(surface.required_check_problems(["ci", "lint", "docs"], runs), [("ci", "red"), ("docs", "missing")])

    def test_release_asset_template(self):
        c = surface.settings({})
        self.assertEqual(surface.asset_template("apk-build.yml", c), ["sha256"])
        self.assertEqual(surface.asset_template("firmware-build.yml", c), ["sha256", "sig"])
        self.assertEqual(surface.missing_assets({"sig": True, "sha256": False}, ["sha256", "sig"]), ["sha256"])
        self.assertEqual(surface.missing_assets(None, ["sig"]), ["assets"])

    def test_versions(self):
        self.assertEqual(surface.compare_versions("v1.2.0", "1.2"), 0)
        self.assertEqual(surface.compare_versions("0.8.0.1", "0.8.0"), 1)
        self.assertIsNone(surface.compare_versions("x", "1"))

    def test_dependabot_priority(self):
        prs = [{"repo": "A", "major": False, "ci_only": True, "age_days": 1}, {"repo": "B", "major": True, "ci_only": False, "age_days": 1},
               {"repo": "C", "major": True, "ci_only": True, "age_days": 1}, {"repo": "D", "major": False, "ci_only": False, "age_days": 9}]
        self.assertEqual([p["repo"] for p in surface.dependabot_priority(prs)], ["B", "D", "C", "A"])

    def issues(self, **kw):
        return [{"repo": "R", "number": 5, "title": kw.get("title", "Build failed: Build"), "url": "https://github.com/JuanenRac/R/issues/5", "created": stamp(2)}]

    def test_issue_suggestion_is_only_text(self):
        green = {"R": [run("R", "Build", "success", stamp(1), rid=9)]}
        rows = surface.issue_close_suggestions(self.issues(), green, set(), {}, NOW)
        self.assertEqual(len(rows), 1)
        self.assertIn("gh issue close 5", rows[0]["command"])
        self.assertIn("JuanenRac/R", rows[0]["command"])
        self.assertEqual(surface.issue_close_suggestions(self.issues(title="Something broke"), green, {("R", "Other")}, {}, NOW), [])   # nothing ties it: the repository still has a red one
        old = {"R": [run("R", "Build", "success", stamp(3), rid=9)]}
        self.assertEqual(surface.issue_close_suggestions(self.issues(), old, set(), {}, NOW), [])               # green BEFORE the issue
        red = {"R": [run("R", "Build", "failure", stamp(1), rid=9)]}
        self.assertEqual(surface.issue_close_suggestions(self.issues(), red, set(), {}, NOW), [])

    def test_issue_linked_to_a_run_by_its_title(self):
        runs = {"R": [run("R", "Release", "success", stamp(1), path="r.yml", rid=222222), run("R", "Build", "failure", stamp(1), path="b.yml", rid=3)]}
        rows = surface.issue_close_suggestions(self.issues(title="failed https://github.com/JuanenRac/R/actions/runs/222222"), runs, {("R", "Build")}, {}, NOW)
        self.assertTrue(rows and rows[0]["linked_run"])

    def test_graphql_node(self):
        node = {"branchProtectionRules": {"nodes": [{"requiredStatusChecks": [{"context": "ci"}]}]},
                "rulesets": {"nodes": [{"enforcement": "ACTIVE", "rules": {"nodes": [{"type": "REQUIRED_STATUS_CHECKS", "parameters": {"requiredStatusChecks": [{"context": "lint"}]}},
                                                                                 {"type": "DELETION"}]}},
                                       {"enforcement": "DISABLED", "rules": {"nodes": [{"type": "REQUIRED_STATUS_CHECKS", "parameters": {"requiredStatusChecks": [{"context": "x"}]}}]}}]},
                "releases": {"nodes": [{"tagName": "v1", "isDraft": True, "createdAt": "t"}, {"tagName": "v0", "isDraft": False, "isPrerelease": False}]},
                "milestones": {"nodes": [{"title": "M", "dueOn": "2020-01-01T00:00:00Z"}]}}
        out = surface.summarize_graphql_node(node)
        self.assertEqual(out["required"], ["ci", "lint"])
        self.assertEqual([d["tag"] for d in out["drafts"]], ["v1"])
        self.assertIn("RequiredStatusChecksParameters", surface.graphql_query())


class CollectorWithFakeGh(unittest.TestCase):
    def collector(self, answers, **over):
        calls = []

        def gh(*args, **kw):
            calls.append(args)
            for key, value in answers.items():
                if key in " ".join(args):
                    if isinstance(value, Exception):
                        raise value
                    return value
            return {}

        c = cfg(**over)
        with tempfile.TemporaryDirectory() as tmp:
            pass
        return surface.Collector(gh, tempfile.gettempdir(), c), calls

    def test_cold_work_is_bounded_and_skipped_without_quota(self):
        c, calls = self.collector({"artifacts?": {"artifacts": [{"size_in_bytes": 5, "expired": False}]}, "secret-scanning": [{}, {}]})
        c.cfg["max_repos_per_tick"] = 2
        used = c.tick(["A", "B", "C"], {}, 100, [], [], lambda r: [], rate_ok=False)
        self.assertEqual((used, calls), (0, []))
        used = c.tick(["A", "B", "C"], {}, 100, [], [], lambda r: [])
        self.assertTrue(any("graphql" in " ".join(a) for a in calls))
        self.assertEqual(sum(1 for a in calls if "artifacts?" in " ".join(a)), 2)    # 2 repositories per tick, not all
        self.assertEqual(c.raw["A"]["secret_resolved"], 2)
        self.assertEqual(c.raw["A"]["artifacts"]["bytes"], 5)
        again = len(calls)
        c.tick(["A", "B", "C"], {}, 100, [], [], lambda r: [])
        self.assertEqual(sum(1 for a in calls[again:] if "artifacts?" in " ".join(a)), 1)   # the third one; the first two are not asked again for a day

    def test_budget_zero_makes_no_network_call(self):
        c, calls = self.collector({})
        c.tick(["A"], {}, 0, [{"repo": "A", "url": "https://github.com/JuanenRac/A/actions/runs/5"}], [], lambda r: [])
        self.assertEqual(calls, [])

    def test_switched_off_checks_make_no_calls(self):
        c, calls = self.collector({}, artifacts={"enabled": False}, secret_resolved={"enabled": False}, required_checks={"enabled": False}, drafts={"enabled": False},
                                  milestones={"enabled": False}, packages={"enabled": False})
        c.tick(["A"], {}, 50, [], [], lambda r: [])
        self.assertEqual(calls, [])
        c.cfg["enabled"] = False
        self.assertEqual(c.tick(["A"], {}, 50, [], [], lambda r: []), 0)

    def test_jobs_of_red_runs_are_read_once_and_forgotten(self):
        jobs = {"jobs": [{"name": "b (windows-latest)", "conclusion": "failure"}, {"name": "b (ubuntu-latest)", "conclusion": "success"}]}
        c, calls = self.collector({"/jobs": jobs})
        red = [{"repo": "A", "url": "https://github.com/JuanenRac/A/actions/runs/77"}]
        self.assertEqual(c.fetch_jobs(red, 4), 1)
        self.assertEqual(c.fetch_jobs(red, 4), 0)
        self.assertEqual(c.glob["jobs"]["77"]["failed_os"], ["windows"])
        c.fetch_jobs([], 4)
        self.assertEqual(c.glob["jobs"], {})

    def test_attestation_existence_by_digest(self):
        c, calls = self.collector({"sha256:aa": {"attestations": [{"x": 1}]}, "sha256:bb": RuntimeError("HTTP 404: Not Found")})
        queue = [{"repo": "A", "run_id": 1}, {"repo": "B", "run_id": 2}]
        files = lambda repo: [("f", "aa" if repo == "A" else "bb")]  # noqa: E731
        c.fetch_attestation(queue, files, 5)
        self.assertEqual(c.glob["attestation"], {"A|1": True, "B|2": False})
        c2, _ = self.collector({"sha256": RuntimeError("HTTP 500")})
        c2.fetch_attestation(queue[:1], files, 5)
        self.assertEqual(c2.glob["attestation"]["A|1"], "unknown")                   # an error is not "no attestation"
        c3, _ = self.collector({}, attestation={"enabled": False})
        self.assertEqual(c3.fetch_attestation(queue, files, 5), 0)

    def test_forget_and_persistence(self):
        c, _ = self.collector({})
        c.raw["A"] = {"at": 99}
        c.forget(["A"])
        self.assertEqual(c.raw["A"]["at"], 0)
        d, _ = self.collector({})
        d.load(json.loads(json.dumps(c.dump())))
        self.assertEqual(d.raw["A"]["at"], 0)
        d.load("garbage")

    def test_packages_failure_is_a_note_not_an_error(self):
        c, _ = self.collector({"packages": RuntimeError("HTTP 403")})
        c.refresh_packages()
        self.assertEqual(c.glob["packages"]["items"], [])
        self.assertTrue(c.glob["packages"]["error"])


class SurfaceInTheSnapshot(_testenv.Spanish, unittest.TestCase):
    def inp(self, **over):
        scans = {"R": {"workflows": [surface.scan_workflow(WorkflowText.YAML, "ci.yml")], "stacks": ["node"], "dependabot_yml": False, "codeql_yml": False,
                       "manifest": {"version": "1.0.0", "maturity": "established", "evidence": "none", "role": ""}, "changelog_top": "1.0.1"}}
        base = {"now": NOW, "cfg": surface.settings({}), "repos": ["R"], "eco": {"R": "armor"}, "repo_info": {"R": {"release": {"tagName": "v1.0.0", "publishedAt": stamp(2),
                "asset_flags": {"sig": False, "sha256": True}}, "vuln_hi": [{"sev": "high", "created": stamp(40)}]}}, "alerts": {"R": {"codeql": None, "secret": 1}},
                "perms": {"R": {"wf_manual": ["old.yml"]}}, "runs": {"R": []}, "branches": {}, "scans": scans,
                "raw": {"R": {"at": 1, "required": ["ci"], "check_runs": [], "artifacts": {"count": 1, "bytes": 900 << 20, "retention_days": 90}, "secret_resolved": 3,
                              "drafts": [{"tag": "v9", "draft": True, "created": stamp(30)}], "milestones": [{"title": "M", "due": "2020-01-01T00:00:00Z"}]}},
                "globals": {"jobs": {"5": {"repo": "R", "failed_os": ["windows"], "ok_os": ["linux"], "failed": ["README parity"]}}, "packages": None},
                "red": [], "issues": [], "prs": [{"repo": "R", "number": 3, "title": "t", "dependabot": False, "draft": False, "age_days": 30, "touches_workflows": True,
                                                  "touches_codeowners": False, "review": "APPROVED", "checks": "SUCCESS", "mergeable": "MERGEABLE", "url": "u"}],
                "states": [{"repo": "R", "workflow": "firmware-build.yml", "published": False, "trusted": False}], "queue": []}
        base.update(over)
        return base

    def test_every_section_finds_its_case(self):
        a10 = surface.build(self.inp())
        rows = {s["key"]: s["rows"] for s in a10["sections"]}
        self.assertEqual(rows["workflows_disabled"], [["R", "old.yml"]])
        self.assertTrue(rows["unpinned_uses"] and rows["broad_permissions"] and rows["pr_target"])
        self.assertEqual(rows["matrix_os"][0][2:], ["windows", "linux"])
        self.assertTrue(rows["artifacts"] and "ausente" in rows["required_checks"][0])
        self.assertEqual(rows["release_assets"], [["R", "v1.0.0", "sig"]])
        self.assertTrue(rows["tag_vs_version"] and rows["drafts"] and rows["security_aged"][0][4] == 1)
        self.assertEqual(rows["coverage"][0][2], "Dependabot, CodeQL")
        self.assertEqual(rows["secret_resolved"], [["R", 1, 3]])
        self.assertTrue(rows["milestones"] and rows["pr_workflow_touch"] and rows["merge_queue"] and rows["pr_human"])
        self.assertEqual(len(rows["maturity"][0][3].split("; ")), 2)
        self.assertTrue(rows["parity"])
        self.assertEqual(a10["level"], "bad")
        kinds = {e["kind"] for e in a10["events"].values()}
        self.assertTrue({"workflow_risk", "release_incomplete", "security_aged", "pr_workflow_touch"} <= kinds)

    def test_a_switch_removes_its_section_and_its_events(self):
        c = cfg(pr_target={"enabled": False}, release_assets={"enabled": False})
        a10 = surface.build(self.inp(cfg=c))
        keys = {s["key"] for s in a10["sections"]}
        self.assertNotIn("pr_target", keys)
        self.assertIn("pr_target", a10["disabled"])
        self.assertNotIn("release_incomplete", {e["kind"] for e in a10["events"].values()})
        self.assertEqual(surface.build(self.inp(cfg=surface.settings({"sentinel": {"surface": {"enabled": False}}})))["enabled"], False)

    def test_a_new_repo_with_nothing_collected_is_quiet(self):
        a10 = surface.build({**self.inp(), "scans": {}, "raw": {}, "globals": {}, "perms": {}, "alerts": {}, "prs": [], "repo_info": {"R": {}}, "states": []})
        self.assertEqual(a10["events"], {})
        self.assertIn("unknown" if False else a10["level"], ("ok", "info"))

    def test_snapshot_carries_a10_attestation_and_minutes(self):
        s = snapshot()
        self.assertIn("a10", s)
        self.assertEqual([m["ecosystem"] for m in s["a7"]["by_ecosystem"]], ["armor", "urtc", "hydra", "eh3d"])
        self.assertIn("level", s["a10"])

    def test_events_do_not_flood_without_a_baseline_and_announce_once(self):
        snap = {"a10": {"events": {"k|1": {"kind": "issue_close_suggest", "level": "info", "repo": "R", "text": "close it", "url": None}}}}
        new = event_feed.summarize(snap)
        old_state = event_feed.summarize({})
        old_state.pop("a10ev")                                                       # a state written by 1.1.x
        self.assertEqual(event_feed.diff(old_state, new, True), [])
        old = event_feed.summarize({})
        events = event_feed.diff(old, new, True)
        self.assertEqual([e["kind"] for e in events], ["issue_close_suggest"])
        self.assertEqual(event_feed.diff(new, new, True), [])

    def test_example_config_matches_the_defaults(self):
        example = json.loads((Path(__file__).resolve().parents[1] / "actions_monitor.example.json").read_text(encoding="utf-8"))
        self.assertEqual(mr.nested_problems(example["sentinel"]["surface"], surface.DEFAULTS), [])
        broken = json.loads(json.dumps(example["sentinel"]["surface"]))
        del broken["checks"]["pr_human"]["days"]
        broken["checks"]["new_one"] = {}
        self.assertEqual(len(mr.nested_problems(broken, surface.DEFAULTS)), 2)
        self.assertEqual(webhook.settings(example), {"enabled": False, "secret": ""})

    def test_a_pr_is_classified_for_the_new_fields(self):
        pr = {"number": 1, "title": "Bump x from 1.0 to 2.0", "author": {"login": "dependabot"}, "createdAt": stamp(1), "mergeable": "MERGEABLE", "reviewDecision": "APPROVED",
              "commits": {"nodes": [{"commit": {"statusCheckRollup": {"state": "SUCCESS"}}}]}, "files": {"nodes": [{"path": ".github/workflows/ci.yml"}, {"path": ".github/CODEOWNERS"}]}}
        c = sl.classify_pr("R", pr, NOW)
        self.assertTrue(c["ci_only"] and c["touches_codeowners"] and c["major"])
        self.assertEqual((c["review"], c["checks"]), ("APPROVED", "SUCCESS"))
        self.assertTrue("createdAt" in sl.repo_query([]) and "reviewDecision" in sl.repo_query([]))

    def test_dependabot_ages_come_from_the_hot_query(self):
        node = {"name": "R", "vulnerabilityAlerts": {"totalCount": 2, "nodes": [{"createdAt": "2026-01-01T00:00:00Z", "securityVulnerability": {"severity": "HIGH"}},
                                                                                  {"createdAt": "x", "securityVulnerability": {"severity": "LOW"}}]}}
        self.assertEqual(sl.parse_repo_node(node, [])["vuln_hi"], [{"sev": "high", "created": "2026-01-01T00:00:00Z"}])

    def test_the_page_has_the_new_panel(self):
        html = (Path(__file__).resolve().parents[1] / "actions_monitor.html").read_text(encoding="utf-8")
        for needle in ('"a10"', "ui.a10_title", "ui.th_attestation", "by_ecosystem"):
            self.assertIn(needle, html)
        import json
        self.assertIn("Superficie", json.loads((Path(__file__).resolve().parents[1] / "locales" / "es.json").read_text(encoding="utf-8"))["ui.a10_title"])


class Exports(unittest.TestCase):
    def snap(self):
        s = snapshot()
        s["a2"]["red"] = [{"repo": "R", "workflow": "CI", "conclusion": "failure", "since": "t", "streak": 2, "url": "https://github.com/JuanenRac/R/actions/runs/1"}]
        s["a5"]["sign_queue"] = [{"name": "R", "repo": "R", "ecosystem": "armor", "hours": 30.0, "step": "sign", "signature_kind": "none", "signature_verified": "unknown",
                                  "attestation": True, "last_build_at": "t", "run_id": 7, "url": "u", "command": "py -3 tool R --run 7"}]
        return s

    def test_public_export_has_only_the_red_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = export_status.write_public_status(self.snap(), tmp)
            self.assertEqual(sorted(p.name for p in written), ["ci_status_public.json", "ci_status_public.md"])
            text = "".join(p.read_text(encoding="utf-8") for p in written)
            self.assertIn("failure", text)
            self.assertFalse(export_status.contains_sensitive(text))
            self.assertNotIn("py -3", text)

    def test_refusals(self):
        self.assertEqual(export_status.write_public_status(self.snap(), "D:/out"), [])
        self.assertEqual(export_status.write_public_status(self.snap(), "//server/share"), [])
        self.assertEqual(export_status.write_public_status({**self.snap(), "loading": "3/9"}, tempfile.gettempdir()), [])
        self.assertIsNone(export_status.write_sign_queue(self.snap(), "D:/q.json"))

    def test_sign_queue_json_and_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            j = export_status.write_sign_queue(self.snap(), Path(tmp) / "q.json")
            data = json.loads(j.read_text(encoding="utf-8"))
            self.assertTrue(data["local_only"] and data["queue"][0]["command"])
            c = export_status.write_sign_queue(self.snap(), Path(tmp) / "q.csv")
            self.assertIn("command", c.read_text(encoding="utf-8").splitlines()[0])
            self.assertIsNone(export_status.write_sign_queue(self.snap(), tmp))


class Webhook(unittest.TestCase):
    SECRET = "s" * 40
    CONFIG = {"webhook": {"enabled": True, "secret": SECRET}}

    def call(self, body, signature=True, event="workflow_run", config=None):
        raw = json.dumps(body).encode()
        headers = {"X-GitHub-Event": event}
        if signature:
            headers["X-Hub-Signature-256"] = webhook.sign(self.SECRET, raw)
        return webhook.handle(config or self.CONFIG, raw, headers, ["R"])

    def test_off_by_default_and_with_a_short_secret(self):
        self.assertEqual(webhook.handle({}, b"{}", {}, ["R"])[0], 404)
        self.assertEqual(self.call({}, config={"webhook": {"enabled": True, "secret": "short"}})[0], 404)
        self.assertFalse(webhook.active({"webhook": {"enabled": "yes", "secret": self.SECRET}}))

    def test_signature_required(self):
        self.assertEqual(self.call({"repository": {"name": "R"}}, signature=False)[0], 401)
        raw = b'{"repository": {"name": "R"}}'
        self.assertEqual(webhook.handle(self.CONFIG, raw, {"X-Hub-Signature-256": "sha256=" + "0" * 64, "X-GitHub-Event": "push"}, ["R"])[0], 401)

    def test_accepted_events(self):
        code, answer, repo = self.call({"repository": {"name": "R"}})
        self.assertEqual((code, repo), (200, "R"))
        self.assertEqual(self.call({"repository": {"name": "Other"}})[2], None)
        self.assertEqual(self.call({"repository": {"name": "../x"}})[2], None)
        self.assertEqual(self.call({}, event="ping")[0], 200)
        self.assertEqual(self.call({}, event="issues")[0], 202)
        self.assertEqual(self.call({"nope": 1})[0], 400)
        self.assertEqual(webhook.handle(self.CONFIG, b"x" * (webhook.MAX_BODY + 1), {}, ["R"])[0], 413)

    def test_the_server_never_binds_to_all_interfaces(self):
        source = (Path(__file__).resolve().parents[1] / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertNotIn("0.0.0.0", source.replace("never bind it to 0.0.0.0", ""))
        self.assertIn('QuietServer(("127.0.0.1", port)', source)
        self.assertIn("class QuietServer(ThreadingHTTPServer)", source)


class MonitorLink(unittest.TestCase):
    def test_notify_finds_the_monitor_and_is_silent_otherwise(self):
        seen = []

        class Answer(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def opener(request, timeout=0):
            seen.append(request.full_url)
            if ":8766" not in request.full_url:
                raise OSError("closed")
            return Answer(b'{"ok": true}')

        self.assertEqual(monitor_link.notify_refresh(["R", "R", ""], opener=opener), 8766)
        self.assertTrue(all(u.startswith("http://127.0.0.1:") for u in seen))
        self.assertIsNone(monitor_link.notify_refresh(["R"], opener=lambda *a, **k: (_ for _ in ()).throw(OSError("x"))))
        self.assertIsNone(monitor_link.notify_refresh([]))

    def test_the_sentinel_refreshes_just_those_repos_and_rewrites_ci_red(self):
        with mock.patch.object(sl.Sentinel, "_load_dispatch", return_value=None), mock.patch.object(sl, "CACHE_FILE", Path(tempfile.gettempdir()) / "nope_cache.json"), \
                mock.patch.object(sl, "HISTORY_FILE", Path(tempfile.gettempdir()) / "nope_hist.json"), mock.patch.object(sl.events, "Feed"):
            s = sl.Sentinel({"gh": lambda *a, **k: {}, "repos_fn": lambda: ["A", "B"], "runs_fn": lambda: {}, "data_fn": lambda: None, "eco_fn": lambda r: "armor"}, {})
        s.repo_info = {"A": {}, "B": {}}
        s.alerts = {"A": {"at": 1}, "B": {"at": 1}}
        s.perms = {"A": {"at": 1}, "B": {"at": 1}}
        s.local_cache["at"] = 123.0
        with mock.patch.object(s, "_export_ci_red") as export, mock.patch.object(s, "snapshot", return_value={}):
            self.assertEqual(s.refresh_repos(["A", "zzz"]), ["A"])
        self.assertTrue(export.called and s.dirty and s.local_cache["at"] == 0.0)
        self.assertEqual((sorted(s.alerts), sorted(s.perms)), (["B"], ["B"]))


class Batch(unittest.TestCase):
    def test_build_only_is_validated_and_never_dispatched(self):
        self.assertIn("HYDRA-UMC-OS", gd.BUILD_ONLY)
        self.assertNotIn("HYDRA-UMC-OS", gd.TARGETS)
        ok = {"X": {"workflow": "package-build.yml", "build_only": True, "reason": "because"}}
        self.assertEqual(gd.validate_targets(ok), [])
        self.assertTrue(gd.validate_targets({"X": {"workflow": "package-build.yml", "build_only": True}}))
        self.assertTrue(gd.validate_targets({"X": {"workflow": "package-build.yml", "build_only": True, "reason": "r", "tool": "t.py"}}))
        self.assertTrue(gd.validate_targets({"X": {"workflow": "package-build.yml", "tool": "t.py", "extra": [], "reason": "r"}}))

    def test_the_plan_labels_it_and_it_is_no_orphan(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), mock.patch.object(gd, "orphan_rows", return_value=[]), mock.patch.object(gd, "plan_rows", return_value=[]), \
                mock.patch.object(gd, "preflight", return_value=[]):
            gd.cmd_plan(mock.Mock(only=None, ecosystem=None, json=False, profile=None))
        text = buffer.getvalue()
        self.assertIn("BUILD ONLY", text)
        self.assertIn("HYDRA-UMC-OS", text)
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "HYDRA-UMC-OS"
            (clone / ".git").mkdir(parents=True)
            (clone / ".github" / "workflows").mkdir(parents=True)
            (clone / ".github" / "workflows" / "package-build.yml").write_text("x", encoding="utf-8")
            self.assertEqual(gd.uncovered_builds(tmp), [])

    def test_the_shipped_profiles_are_valid_and_select_what_they_say(self):
        data = gd.load_profiles()
        self.assertEqual(gd.validate_profiles(data), [])
        self.assertEqual(set(data["profiles"]), {"release", "nightly", "hil"})
        release = gd.profile_names("release", data)
        self.assertEqual(release[0].split("-")[0], "ARMOR")                                  # armor first: the canary is the first of the first ecosystem
        self.assertNotIn("HYDRA-UMC-OS", release)
        self.assertTrue(all(":" not in n or release.index(n) > release.index(n.split(":")[0]) for n in release))
        self.assertEqual(gd.profile_names("hil", data), ["HYDRA-UMC", "HYDRA-UMC-HIL-BRIDGE"])
        self.assertTrue(all(gd.TARGETS[n]["workflow"] != "firmware-build.yml" for n in gd.profile_names("nightly", data)))
        self.assertTrue(gd.validate_profiles({"profiles": {"p": {"workflows": ["nope.yml"]}}}))
        self.assertTrue(gd.validate_profiles({"profiles": {"p": {"names": ["nope"]}}}))
        with self.assertRaises(SystemExit):
            gd.profile_names("unknown", data)
        self.assertEqual(gd.load_profiles(Path(tempfile.gettempdir()) / "no_profiles.json"), {"profiles": {}})

    def test_quota_gate_fails_closed(self):
        self.assertEqual(gd.quota_gate(1500, lambda: 4000)[0], True)
        self.assertEqual(gd.quota_gate(1500, lambda: 100)[0], False)
        self.assertEqual(gd.quota_gate(1500, lambda: None)[0], False)
        self.assertEqual(gd.quota_gate(0, lambda: None)[0], True)

    def fakes(self, results):
        fired = []

        def fire(name, repo, sha, real):
            fired.append(name)
            return {"run": 100 + len(fired), "workflow": "w", "sha": sha}
        return fired, dict(fire_fn=fire, head_fn=lambda repo: ("a" * 40, ""), green_fn=lambda repo, sha: (True, [], 0), sleep_fn=lambda s: None)

    def test_canary_goes_first_and_alone(self):
        names = ["ARMOR-SERVER", "ARMOR-STUDIO", "URTC"]
        fired, fns = self.fakes(None)
        batch, note = gd.run_with_canary(names, False, True, True, wait_fn=lambda repo, run: "success", **fns)
        self.assertEqual((fired, note), (names, ""))
        fired, fns = self.fakes(None)
        batch, note = gd.run_with_canary(names, False, True, True, wait_fn=lambda repo, run: "failure", **fns)
        self.assertEqual(fired, ["ARMOR-SERVER"])
        self.assertIn("NOT dispatched", note)
        self.assertEqual(list(batch["targets"]), ["ARMOR-SERVER"])
        fired, fns = self.fakes(None)
        gd.run_with_canary(names, False, True, False, **fns)
        self.assertEqual(fired, names)                                                      # no canary: all at once
        fired, fns = self.fakes(None)
        gd.run_with_canary(names, False, False, True, **fns)
        self.assertEqual(fired, [])                                                         # plan only: nothing fired, nothing waited

    def test_wait_canary_polls_and_times_out(self):
        states = iter([("in_progress", None, "u", []), ("completed", "success", "u", [])])
        sleeps = []
        self.assertEqual(gd.wait_canary("R", 1, 100, state_fn=lambda r, i: next(states), sleep_fn=sleeps.append, clock=lambda: 0), "success")
        self.assertEqual(sleeps, [30])
        t = iter(range(0, 1000, 60))
        self.assertEqual(gd.wait_canary("R", 1, 100, state_fn=lambda r, i: ("queued", None, "u", []), sleep_fn=lambda s: None, clock=lambda: next(t)), "timeout")

    def test_dispatch_refuses_when_the_quota_is_low(self):
        args = mock.Mock(only=["ARMOR-SERVER"], ecosystem=None, profile=None, go=True, real=False, min_rate=None, no_canary=False)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), mock.patch.object(gd, "preflight", return_value=[]), mock.patch.object(gd, "rate_remaining", return_value=10), \
                mock.patch.object(gd, "run_batch") as batch:
            self.assertEqual(gd.cmd_dispatch(args), 3)
        self.assertFalse(batch.called)
        self.assertIn("only 10", buffer.getvalue())


class ReleaseNotes(unittest.TestCase):
    def test_draft_groups_and_leaves_out_what_is_private(self):
        text = release_notes.draft(["feat(ui): add a panel", "fix: stop a crash", "docs: update readme", "Audit round 4 fixes", "chore: bump", "plain subject",
                                    "feat: thing by assistant"], "v1.0.0")
        self.assertIn("### Added", text)
        self.assertIn("- Add a panel", text)
        self.assertIn("### Fixed", text)
        self.assertIn("### Other", text)
        self.assertNotIn("Audit round", text)
        self.assertIn("2 subject(s) left out", text)
        self.assertIn("nothing was published", text)
        self.assertIn(release_notes.TEXT["no_commits"], release_notes.draft([], None))

    def test_it_reads_a_real_local_repository(self):
        import shutil
        import subprocess
        if not shutil.which("git"):
            self.skipTest("git is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "R"
            repo.mkdir()
            env = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]
            run_git = lambda *a: subprocess.run(["git", "-C", str(repo), *env, *a], capture_output=True, text=True)  # noqa: E731
            run_git("init", "-q")
            (repo / "a").write_text("1", encoding="utf-8")
            run_git("add", "a")
            run_git("commit", "-q", "-m", "feat: first")
            run_git("tag", "v0.1.0")
            (repo / "a").write_text("2", encoding="utf-8")
            run_git("commit", "-qam", "fix: second")
            self.assertEqual(release_notes.last_tag(tmp, "R"), "v0.1.0")
            self.assertEqual(release_notes.subjects(tmp, "R", "v0.1.0"), ["fix: second"])


class GateAndVersion(unittest.TestCase):
    def test_version_is_1_5_0_and_the_changelog_agrees(self):
        import tool_version
        self.assertEqual(tool_version.TOOL_VERSION, "1.6.0")
        self.assertEqual(mr.gate_static(), "1.6.0")

    def test_new_files_travel_and_state_files_do_not(self):
        names = {p.relative_to(mr.HERE).as_posix() for p in mr.members()}
        for needed in ("surface.py", "webhook.py", "export_status.py", "monitor_link.py", "release_notes.py", "profiles.example.json", "docs/CI_RED_SCHEMA.md"):
            self.assertIn(needed, names)
        self.assertEqual(mr.check_entries(["github_actions_monitor/profiles.example.json", "github_actions_monitor/docs/CI_RED_SCHEMA.md"]), [])


if __name__ == "__main__":
    unittest.main()
