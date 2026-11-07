# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Offline tests with FIXED gh answers (no network): states built_on_gha -> signed_local -> published, pending_sign, the cross with local
batch records, the signing queue, the minutes budget, ci_red.json, the batch tools (retry, ecosystem, json) and the release gate.
Run:  py -3 -I -m unittest discover -s tests"""
import json
import sys
import tempfile
import unittest
import _testenv  # noqa: F401
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ci_red  # noqa: E402
import events as event_feed  # noqa: E402
import platform_compat
import gha_dispatch_all as gd  # noqa: E402
import make_release as mr  # noqa: E402
import sentinel_local as sl  # noqa: E402
import signstate  # noqa: E402
import tool_version  # noqa: E402

NOW = datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc)
BUILD_AT = "2026-11-03T10:00:00Z"   # 26 h before NOW

# a node of the GraphQL answer of `gh api graphql` (fixed): latest release with its assets
GRAPHQL_NODE = json.loads("""
{"name": "R", "pushedAt": "2026-11-04T10:00:00Z", "hasVulnerabilityAlertsEnabled": true, "defaultBranchRef": {"name": "main"},
 "latestRelease": {"tagName": "v1.0.0", "publishedAt": "2026-10-01T00:00:00Z", "isDraft": false,
   "releaseAssets": {"nodes": [{"name": "app.bin"}, {"name": "app.bin.sig"}, {"name": "app.bin.sha256"}, {"name": "app.bin.imgsig"}]}},
 "vulnerabilityAlerts": {"totalCount": 0, "nodes": []}, "pullRequests": {"nodes": []}, "rulesets": {"nodes": []}, "labels": {"nodes": []}}
""")

TARGETS = {"R": {"workflow": "firmware-build.yml", "tool": "t.py", "extra": []}}


def run(repo, name, conclusion, started, path="firmware-build.yml", rid=1, branch="main"):
    return {"repo": repo, "id": rid, "name": name, "path": path, "branch": branch, "status": "completed", "conclusion": conclusion,
            "started": started, "url": f"https://github.com/JuanenRac/{repo}/actions/runs/{rid}", "seconds": 120, "actor": "JuanenRac", "sha": "abc1234"}


def finalize(name, run_id):
    return ["py", "-3", f"tools/{name}.py", name, "--run", str(run_id), "--sign", "--publish"]


def snapshot(local=None, repos=("R",), eco=None, targets=None, runs=None, cfg=None, releases=None):
    eco = eco or {r: "armor" for r in repos}
    info = {r: {"branch": "main", "pushed": "2026-11-01T10:00:00Z", "release": (releases or {}).get(r, {"tagName": "v1", "publishedAt": "2026-10-01T00:00:00Z"}),
                "vuln_total": 0, "vuln_sev": {}, "prs": [], "rulesets": [], "label_dependencies": True, "files": {}} for r in repos}
    runs = runs if runs is not None else {r: [run(r, "Build", "success", BUILD_AT, rid=7)] for r in repos}
    inp = {"now": NOW, "today": "2026-11-04", "cfg": {**sl.DEFAULTS, **(cfg or {})}, "repos": list(repos), "eco": eco, "repo_info": info,
           "alerts": {r: {"at": 1, "codeql": [], "secret": 0} for r in repos}, "perms": {}, "runs": runs,
           "data": {"active": [], "issues": [], "rate": {"remaining": 4000, "limit": 5000}}, "history": {"days": {}}, "unreleased": {},
           "targets": targets or {r: {**TARGETS["R"]} for r in repos}, "errors": {}, "loading": "", "audits": None,
           "local": local, "finalize_fn": finalize}
    return sl.compute_snapshot(inp)


class GraphqlFixture(unittest.TestCase):
    def test_release_assets_become_signature_flags(self):
        info = sl.parse_repo_node(GRAPHQL_NODE, ["README.md"])
        self.assertEqual(info["release"]["tagName"], "v1.0.0")
        flags = info["release"]["asset_flags"]
        self.assertTrue(flags["sig"] and flags["sha256"] and flags["imgsig"])
        self.assertFalse(flags["sig2"])
        self.assertEqual(flags["assets"], 4)

    def test_a_draft_or_no_assets(self):
        draft = json.loads(json.dumps(GRAPHQL_NODE))
        draft["latestRelease"]["isDraft"] = True
        self.assertIsNone(sl.parse_repo_node(draft, [])["release"])
        draft["latestRelease"] = {"tagName": "v2", "publishedAt": "2026-10-02T00:00:00Z", "isDraft": False}
        self.assertIsNone(sl.parse_repo_node(draft, [])["release"]["asset_flags"])


class PendingSignAndGreen(_testenv.Spanish, unittest.TestCase):
    def test_red_workflows_fixed_runs(self):
        runs = {"R": [run("R", "Build", "success", "2026-11-02T10:00:00Z", rid=1), run("R", "Build", "failure", "2026-11-03T10:00:00Z", rid=2),
                      run("R", "Build", "failure", "2026-11-03T11:00:00Z", rid=3)]}
        red = sl.red_workflows(runs)
        self.assertEqual([(r["repo"], r["workflow"], r["streak"]) for r in red], [("R", "Build", 2)])

    def test_green_without_release_and_pending_hours(self):
        runs = {"R": [run("R", "Build", "success", BUILD_AT)]}
        rel = {"R": {"publishedAt": "2026-10-01T00:00:00Z", "tagName": "v1"}}
        green = sl.green_without_release(TARGETS, runs, rel)
        self.assertEqual([g["repo"] for g in green], ["R"])
        pend = sl.pending_sign(green, NOW, 24)
        self.assertEqual(pend[0]["hours"], 26.0)
        self.assertEqual(sl.pending_sign(green, NOW, 30), [])   # not yet over the limit
        self.assertEqual(sl.green_without_release(TARGETS, runs, {"R": {"publishedAt": "2026-11-03T12:00:00Z", "tagName": "v2"}}), [])

    def test_snapshot_without_local_records_is_pending(self):
        s = snapshot(local={"signed": {}, "batches": {}})
        a5 = s["a5"]
        self.assertEqual([g["repo"] for g in a5["pending_sign"]], ["R"])
        row = a5["pending_sign"][0]
        self.assertEqual((row["state"], row["signature_kind"], row["last_build_at"], row["pending_sign_hours"]), ("built_on_gha", "none", BUILD_AT, 26.0))
        self.assertEqual(a5["states"][0]["state"], "built_on_gha")
        self.assertEqual(s["tool_version"], tool_version.TOOL_VERSION)
        self.assertTrue(any("Verde sin firmar" in p["text"] for p in s["parte"]))


class LoteCross(_testenv.Spanish, unittest.TestCase):
    def test_a_batch_that_says_published_lowers_the_alert(self):
        local = {"signed": {}, "batches": {"R": {"run": 7, "dispatched_at": BUILD_AT, "signed_at": "2026-11-04T08:00:00Z", "published_at": "2026-11-04T09:00:00Z"}}}
        s = snapshot(local=local)
        self.assertEqual(s["a5"]["pending_sign"], [])
        self.assertEqual(s["a5"]["green_unreleased"], [])
        self.assertEqual((s["a5"]["states"][0]["state"], s["a5"]["states"][0]["published_by"]), ("published", "batch"))
        self.assertEqual(s["a5"]["sign_queue"], [])

    def test_signed_with_the_release_key_waits_only_for_publication(self):
        local = {"signed": {}, "batches": {"R": {"signed_at": "2026-11-04T08:00:00Z", "published_at": None}}}
        s = snapshot(local=local, cfg={"require_verified_signature": False})   # the old rule; the default now asks for a verified signature (test_next_level)
        self.assertEqual(s["a5"]["pending_sign"], [])
        self.assertEqual([g["repo"] for g in s["a5"]["signed_unpublished"]], ["R"])
        st = s["a5"]["states"][0]
        self.assertEqual((st["state"], st["signature_kind"], st["last_signed_at"]), ("signed_local", "release", "2026-11-04T08:00:00Z"))
        self.assertEqual(s["a5"]["sign_queue"][0]["step"], "publish")
        self.assertTrue(any("Firmado en el PC y pendiente de publicar" in p["text"] for p in s["parte"]))

    def test_an_old_signature_or_a_dev_one_does_not_lower_it(self):
        old = {"signed": {}, "batches": {"R": {"signed_at": "2026-11-02T08:00:00Z", "published_at": "2026-11-02T09:00:00Z"}}}   # of the previous build
        self.assertEqual([g["repo"] for g in snapshot(local=old)["a5"]["pending_sign"]], ["R"])
        dev = {"signed": {"R": {"version": "1", "kind": "dev", "signed_at": "2026-11-04T08:00:00Z"}}, "batches": {}}
        s = snapshot(local=dev)
        self.assertEqual([g["repo"] for g in s["a5"]["pending_sign"]], ["R"])
        self.assertEqual((s["a5"]["states"][0]["state"], s["a5"]["states"][0]["signature_kind"]), ("signed_local", "dev"))
        self.assertEqual(s["a5"]["sign_queue"][0]["step"], "sign")

    def test_the_github_release_still_wins(self):
        s = snapshot(local={"signed": {}, "batches": {}}, releases={"R": {"tagName": "v2", "publishedAt": "2026-11-03T12:00:00Z"}})
        self.assertEqual((s["a5"]["states"][0]["state"], s["a5"]["states"][0]["published_by"]), ("published", "github"))
        self.assertEqual(s["a5"]["pending_sign"], [])


class SignQueue(unittest.TestCase):
    def test_order_hours_then_ecosystem_with_the_command(self):
        repos = ("ARMOR-X", "URTC-Y", "HYDRA-UMC-Z", "URTC-W")
        eco = {"ARMOR-X": "armor", "URTC-Y": "urtc", "HYDRA-UMC-Z": "hydra", "URTC-W": "urtc"}
        starts = {"ARMOR-X": "2026-11-03T10:00:00Z", "URTC-Y": "2026-11-02T10:00:00Z", "HYDRA-UMC-Z": "2026-11-02T10:00:00Z", "URTC-W": "2026-11-03T10:00:00Z"}
        runs = {r: [run(r, "B", "success", starts[r], rid=i + 1)] for i, r in enumerate(repos)}
        s = snapshot(repos=repos, eco=eco, runs=runs, local={"signed": {}, "batches": {}})
        q = s["a5"]["sign_queue"]
        self.assertEqual([x["name"] for x in q], ["URTC-Y", "HYDRA-UMC-Z", "ARMOR-X", "URTC-W"])   # 50 h (urtc, hydra), 26 h (armor, urtc)
        self.assertEqual(q[0]["hours"], 50.0)
        self.assertTrue(q[0]["command"].endswith("--run 2 --sign --publish") or "--run 2" in q[0]["command"])
        self.assertEqual(q[0]["argv"][-2:], ["--sign", "--publish"])

    def test_queue_command_matches_what_finalize_prints(self):
        argv = gd.finalize_command("URTC", 99)
        self.assertEqual(argv[-3:], ["--sign", "--publish", "--bench"])
        self.assertEqual(gd.finalize_command("ARMOR-NODE-HMI", 5)[-1], "--publish")
        self.assertIn("--sign", gd.finalize_command("ARMOR-SERVER", 5))
        q = signstate.sign_queue([{"name": "URTC", "repo": "URTC", "ecosystem": "urtc", "state": "built_on_gha", "signature_kind": "none", "hours": 3.0,
                                   "run_id": 99, "last_build_at": BUILD_AT, "url": "u"}], gd.finalize_command)
        self.assertEqual(q[0]["command"], gd.command_text(argv))


class LocalFiles(unittest.TestCase):
    def test_signed_folder_and_batches_are_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel = root / "URTC" / "release-0.4.5"
            rel.mkdir(parents=True)
            (rel / "fw.bin").write_bytes(b"x")
            (rel / "fw.bin.sig").write_bytes(b"s")
            (rel / "fw.bin.manifest.json").write_text(json.dumps({"signing_key_kind": "release"}), encoding="utf-8")
            old = root / "URTC" / "release-0.4.4"
            old.mkdir()
            (old / "a.bin").write_bytes(b"x")
            dev = root / "URTC-TESTER" / "release-0.5.1"
            dev.mkdir(parents=True)
            (dev / "t.zip").write_bytes(b"x")
            (dev / "t.zip.manifest.json").write_text(json.dumps({"signing_key_kind": "dev"}), encoding="utf-8")
            (dev / "t.zip.sig").write_bytes(b"s")
            apk = root / "ARMOR-ANDROID-CONTROL" / "release-0.8.0.4"
            apk.mkdir(parents=True)
            (apk / "a.apk").write_bytes(b"x")
            (root / "batches").mkdir()
            (root / "batches" / "batch_1.json").write_text(json.dumps({"targets": {"URTC": {"run": 5, "dispatched_at": "2026-11-03T10:00:00Z"}, "X": {"skipped": "r"}}}), encoding="utf-8")
            (root / "batches" / "batch_2.json").write_text(json.dumps({"targets": {"URTC": {"run": 6, "dispatched_at": "2026-11-04T10:00:00Z", "signed_at": "2026-11-04T11:00:00Z"}}}), encoding="utf-8")
            (root / "batches" / "batch_3.json").write_text("not json", encoding="utf-8")
            got = signstate.local_records(root)
        self.assertEqual((got["signed"]["URTC"]["version"], got["signed"]["URTC"]["kind"]), ("0.4.5", "release"))
        self.assertEqual(got["signed"]["URTC-TESTER"]["kind"], "dev")
        self.assertEqual(got["signed"]["ARMOR-ANDROID-CONTROL"]["kind"], "release")
        self.assertNotIn("batches", got["signed"])
        self.assertEqual((got["batches"]["URTC"]["run"], got["batches"]["URTC"]["signed_at"]), (6, "2026-11-04T11:00:00Z"))
        self.assertEqual(signstate.local_records(Path(tmp) / "nowhere"), {"signed": {}, "batches": {}})   # no workspace: no failure

    def test_signature_kind_rules(self):
        self.assertEqual(signstate.signature_kind(["a.bin"]), "none")
        self.assertEqual(signstate.signature_kind(["a.bin", "a.bin.sig2"]), "release")
        self.assertEqual(signstate.signature_kind(["a.bin.sig"], ["dev"]), "dev")
        self.assertEqual(signstate.signature_kind(["a.bin.sig"], ["dev", "release"]), "release")


class Budget(_testenv.Spanish, unittest.TestCase):
    MINS = {"H1": {"min24": 10, "min7d": 450}, "H2": {"min24": 5, "min7d": 100}, "A1": {"min24": 1, "min7d": 20}}
    ECO = {"H1": "hydra", "H2": "hydra", "A1": "armor"}

    def test_levels_and_defaults(self):
        self.assertEqual(sl.minutes_budget(self.MINS, self.ECO, sl.DEFAULTS), [])   # empty by default
        rows = sl.minutes_budget(self.MINS, self.ECO, {"minutes_budget": {"hydra": 650, "armor": 20, "urtc": 0, "bad": 5}})
        by = {r["ecosystem"]: r for r in rows}
        self.assertEqual((by["hydra"]["used"], by["hydra"]["level"]), (550, "warn"))   # 550/650 = 84.6 %
        self.assertEqual(by["armor"]["level"], "over")
        self.assertNotIn("urtc", by)
        self.assertEqual(sl.minutes_budget(self.MINS, self.ECO, {"minutes_budget": {"hydra": 100}, "minutes_budget_period": "24h"})[0]["used"], 15)

    def test_warning_in_the_parte_and_as_an_event(self):
        s = snapshot(cfg={"minutes_budget": {"armor": 100}})   # 120 s run in 24 h -> tiny: ok
        self.assertEqual(s["a7"]["budget"][0]["level"], "ok")
        runs = {"R": [run("R", "Build", "success", "2026-11-04T01:00:00Z") | {"seconds": 4800}]}   # 80 min in the last 24 h
        s = snapshot(runs=runs, cfg={"minutes_budget": {"armor": 100}})
        self.assertEqual(s["a7"]["budget"][0]["level"], "warn")
        self.assertEqual(s["a7"]["level"], "warn")
        self.assertTrue(any("Presupuesto de minutos de armor" in p["text"] for p in s["parte"]))
        old, new = event_feed.summarize(snapshot()), event_feed.summarize(s)
        self.assertEqual([e["kind"] for e in event_feed.diff(old, new, True)].count("budget_warn"), 1)
        self.assertEqual([e for e in event_feed.diff(new, new, True) if e["kind"].startswith("budget")], [])   # announced once
        over = json.loads(json.dumps(new))
        over["budget"]["armor"]["level"] = "over"
        self.assertIn("budget_over", [e["kind"] for e in event_feed.diff(new, over, True)])


class CiRedExport(unittest.TestCase):
    def snap(self):
        s = snapshot(runs={"R": [run("R", "Build", "failure", "2026-11-04T05:00:00Z")]}, local={"signed": {}, "batches": {}})
        return s

    def test_content_and_atomic_write(self):
        s = self.snap()
        with tempfile.TemporaryDirectory() as tmp:
            written = ci_red.export(s, {"ci_red_file": ""}, audit_dir=None, base=Path(tmp))
            self.assertEqual(written, [Path(tmp) / "ci_red.json"])
            data = json.loads((Path(tmp) / "ci_red.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["ci_red.json"])   # no .tmp left behind
        self.assertEqual(data["repos"]["R"]["red"][0]["workflow"], "Build")
        self.assertTrue(data["complete"])
        self.assertEqual(data["tool_version"], tool_version.TOOL_VERSION)

    def test_pending_sign_is_in_the_file(self):
        s = snapshot(local={"signed": {}, "batches": {}})
        self.assertEqual(ci_red.build(s)["repos"]["R"]["pending_sign_hours"], 26.0)

    def test_off_loading_forbidden_drive_and_missing_audit_folder(self):
        s = self.snap()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ci_red.export(s, {"ci_red_file": "off"}, base=Path(tmp)), [])
            self.assertEqual(ci_red.export({**s, "loading": "3/10"}, {}, base=Path(tmp)), [])
            self.assertIsNone(ci_red.target_path("D:/x/ci_red.json"))
            got = ci_red.export(s, {"ci_red_file": "sub_not_there/x.json", "ci_red_audit_copy": True}, audit_dir=Path(tmp) / "no_such_dir", base=Path(tmp))
            self.assertEqual(got, [])   # the folder does not exist: no exception
            got = ci_red.export(s, {"ci_red_audit_copy": True}, audit_dir=Path(tmp) / "no_such_dir", base=Path(tmp))
            self.assertEqual(got, [Path(tmp) / "ci_red.json"])
            (Path(tmp) / "audits").mkdir()
            got = ci_red.export(s, {"ci_red_audit_copy": True}, audit_dir=Path(tmp) / "audits", base=Path(tmp))
            self.assertEqual(len(got), 2)


class DispatchTools(unittest.TestCase):
    HEAD = staticmethod(lambda repo: ("a" * 40, ""))
    GREEN = staticmethod(lambda repo, sha: (True, [], 0))

    def test_a_failed_dispatch_is_retried_once_and_the_rest_goes_on(self):
        calls = []

        def fire(name, repo, sha, real):
            calls.append(name)
            if name == "ARMOR-NODE-HMI" and calls.count(name) == 1:
                raise RuntimeError("HTTP 502")
            if name == "ARMOR-NODE-RADAR":
                raise RuntimeError("HTTP 422 always")
            return {"workflow": "firmware-build.yml", "run": 100 + len(calls), "sha": sha}

        names = ["ARMOR-NODE-HMI", "ARMOR-NODE-ALARM", "ARMOR-NODE-RADAR"]
        batch = gd.run_batch(names, real=False, go=True, fire_fn=fire, head_fn=self.HEAD, green_fn=self.GREEN, sleep_fn=lambda s: None)
        t = batch["targets"]
        self.assertEqual(calls, ["ARMOR-NODE-HMI", "ARMOR-NODE-ALARM", "ARMOR-NODE-RADAR", "ARMOR-NODE-HMI", "ARMOR-NODE-RADAR"])   # ALARM was not aborted
        self.assertTrue(t["ARMOR-NODE-HMI"]["retried"] and t["ARMOR-NODE-HMI"]["run"])
        self.assertNotIn("retried", t["ARMOR-NODE-ALARM"])
        self.assertIn("HTTP 422", t["ARMOR-NODE-RADAR"]["failed"])

    def test_without_go_nothing_is_fired(self):
        def boom(*a):
            raise AssertionError("fired")
        batch = gd.run_batch(["ARMOR-NODE-HMI"], real=False, go=False, fire_fn=boom, head_fn=self.HEAD, green_fn=self.GREEN)
        self.assertEqual(batch["targets"], {})

    def test_skips_are_recorded(self):
        batch = gd.run_batch(["ARMOR-NODE-HMI"], real=False, go=True, fire_fn=None, head_fn=lambda r: ("b" * 40, "local HEAD is not origin/main"), green_fn=self.GREEN)
        self.assertIn("skipped", batch["targets"]["ARMOR-NODE-HMI"])

    def test_ecosystem_selection(self):
        self.assertEqual(gd.ecosystem_of("HYDRA-UMC-SUITE"), "hydra")
        names = gd.pick(None, "urtc")
        self.assertTrue(names and all(gd.repo_of(n).startswith("URTC") for n in names))
        self.assertEqual(sorted(gd.pick(None, "armor") + gd.pick(None, "urtc") + gd.pick(None, "hydra")), sorted(gd.TARGETS))
        with self.assertRaises(SystemExit):
            gd.pick(None, "eh3d")
        self.assertEqual(gd.pick(["URTC", "ARMOR-SERVER"], "urtc"), ["URTC"])

    def test_plan_json_is_machine_readable(self):
        rows = gd.plan_rows(["URTC", "HYDRA-UMC-SUITE:exe"], head=lambda repo: ("c" * 40, ""))
        text = json.dumps({"targets": rows})
        got = json.loads(text)["targets"]
        self.assertEqual([r["name"] for r in got], ["URTC", "HYDRA-UMC-SUITE:exe"])
        self.assertEqual((got[1]["repo"], got[1]["ecosystem"], got[1]["workflow"]), ("HYDRA-UMC-SUITE", "hydra", "exe-build.yml"))

    def test_finalize_lists_exact_commands_and_marks_the_batch(self):
        batch = {"dry_run": True, "targets": {"URTC": {"run": 11}, "HYDRA-UMC-SUITE:exe": {"run": 12}, "ARMOR-SERVER": {"run": 13}, "X": {"skipped": "r"},
                                              "URTC-TESTER": {"failed": "e"}}}

        def state(repo, run_id):
            return ("completed", "success" if run_id != 13 else "failure", f"https://x/{run_id}", [])

        rows = gd.finalize_rows(batch, state_fn=state)
        self.assertEqual([r["name"] for r in rows], ["URTC", "ARMOR-SERVER", "HYDRA-UMC-SUITE:exe"])   # parts after the packages
        self.assertEqual([r["state"] for r in rows], ["ready", "not_ready", "ready"])
        self.assertTrue(rows[0]["command"].startswith(platform_compat.command_text(platform_compat.python_argv()) + " ") and "--run 11" in rows[0]["command"] and rows[0]["command"].endswith("--bench"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "batch_1.json"
            path.write_text(json.dumps(batch), encoding="utf-8")
            gd.mark_batch(path, batch, "URTC", signed_at="2026-11-04T11:00:00Z", published_at="2026-11-04T11:00:00Z")
            again = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(again["targets"]["URTC"]["published_at"], "2026-11-04T11:00:00Z")
        self.assertEqual(signstate.batch_index.__name__, "batch_index")


class TargetsFile(unittest.TestCase):
    def test_the_file_is_valid_and_has_the_known_targets(self):
        data = json.loads(gd.TARGETS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(gd.validate_targets(data), [])
        self.assertEqual(len([k for k in data if not k.startswith("_")]), 40)
        self.assertEqual(data["URTC"]["finalize_flags"], ["--bench"])
        self.assertEqual(data["HYDRA-UMC-STUDIO:dist"]["repo"], "HYDRA-UMC-STUDIO")

    def test_validation_catches_mistakes(self):
        good = {"A": {"workflow": "firmware-build.yml", "tool": "t.py", "extra": []}}
        self.assertEqual(gd.validate_targets(good), [])
        self.assertTrue(gd.validate_targets({}))
        self.assertTrue(gd.validate_targets({"A": {**good["A"], "workflow": "nope.yml"}}))
        self.assertTrue(gd.validate_targets({"A": {**good["A"], "tool": "t.sh"}}))
        self.assertTrue(gd.validate_targets({"A": {**good["A"], "extra": "x"}}))
        self.assertTrue(gd.validate_targets({"A": {**good["A"], "colour": "red"}}))
        self.assertTrue(gd.validate_targets({"A:p": {**good["A"], "repo": "A"}}))   # base repo is not a target
        self.assertTrue(gd.validate_targets({"A": good["A"], "A:p": good["A"]}))   # a part without its repo key
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "t.json"
            bad.write_text("{not json", encoding="utf-8")
            with self.assertRaises(SystemExit):
                gd.load_targets(bad)


class ReleaseGate(unittest.TestCase):
    def test_entries_that_must_not_travel(self):
        clean = ["github_actions_monitor/a.py", "github_actions_monitor/tests/test_a.py", "github_actions_monitor/targets.example.json", "github_actions_monitor/tests/fixtures/fixture_targets.json", "github_actions_monitor/CHANGELOG.md"]
        self.assertEqual(mr.check_entries(clean), [])
        dirty = clean + ["github_actions_monitor/__pycache__/a.cpython-314.pyc", "github_actions_monitor/actions_monitor_log.txt", "github_actions_monitor/sentinel_cache.json",
                         "github_actions_monitor/sentinel_history.json", "github_actions_monitor/events_monitor.jsonl", "github_actions_monitor/actions_monitor.json",
                         "github_actions_monitor/x.log", "github_actions_monitor/ci_red.json"]
        self.assertEqual(len(mr.check_entries(dirty)), 8)

    def test_example_must_show_every_sentinel_option(self):
        example = json.loads(mr.template())
        self.assertEqual(mr.example_problems(example, sl.DEFAULTS), [])
        example["sentinel"].pop("minutes_budget")
        example["sentinel"]["invented"] = 1
        problems = mr.example_problems(example, sl.DEFAULTS)
        self.assertTrue(any("minutes_budget" in p for p in problems) and any("invented" in p for p in problems))
        self.assertEqual(example_repos(mr.template()), "all")

    def test_version_and_changelog_agree(self):
        self.assertEqual(mr.changelog_version("# Changelog\n\n## [1.2.3]\n\n## [1.0.0]\n"), "1.2.3")
        self.assertIsNone(mr.changelog_version("nothing"))
        self.assertEqual(mr.gate_static(), tool_version.TOOL_VERSION)   # the real files of this folder pass the static gate

    def test_gate_failure_stops(self):
        with self.assertRaises(SystemExit):
            mr.fail("x")


def example_repos(text):
    return json.loads(text)["repos"]


if __name__ == "__main__":
    unittest.main()
