# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Tests of version 1.1.0: signature trust (sigverify + signstate + sentinel), the ci_red.json bridge, orphans and conventions of the batch
tools, the single definition of "last run" and the history of the report. Offline, with throw-away keys made inside the test (no secret, no network).
Run:  py -3 -I -m unittest discover -s tests"""
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
import _testenv  # noqa: F401
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from github_actions_monitor.data_pipeline import ci_red  # noqa: E402
from github_actions_monitor.cli import gha_dispatch_all as gd  # noqa: E402
from github_actions_monitor.data_pipeline import report_history  # noqa: E402
from github_actions_monitor.sentinels import sentinel_local as sl  # noqa: E402
from github_actions_monitor.security import sigverify  # noqa: E402
from github_actions_monitor.sentinels import signstate  # noqa: E402
from test_signstate import BUILD_AT, NOW, run, snapshot  # noqa: E402

Q, B = sigverify._Q, sigverify.BASE


def keypair(seed):
    """(public bytes, signer) from a 32-byte seed, RFC 8032 (test helper: the monitor itself never signs)."""
    digest = hashlib.sha512(seed).digest()
    a = int.from_bytes(digest[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    public = sigverify._compress(sigverify._mul(a, B))

    def sign(message):
        r = int.from_bytes(hashlib.sha512(digest[32:] + message).digest(), "little") % Q
        rs = sigverify._compress(sigverify._mul(r, B))
        k = int.from_bytes(hashlib.sha512(rs + public + message).digest(), "little") % Q
        return rs + ((r + k * a) % Q).to_bytes(32, "little")
    return public, sign


PUB, SIGN = keypair(b"\x01" * 32)
OTHER_PUB, OTHER_SIGN = keypair(b"\x02" * 32)


def put_signed(folder, name, data, scheme_message, sign=SIGN):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    (folder / (name + ".sig")).write_text(sign(scheme_message(digest)).hex() + "\n", encoding="ascii")


class Ed25519(unittest.TestCase):
    def test_rfc8032_vector_1(self):
        seed = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        public, sign = keypair(seed)
        self.assertEqual(public.hex(), "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        signature = sign(b"")
        self.assertEqual(signature.hex(), "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
        self.assertTrue(sigverify.ed25519_verify(public, b"", signature))

    def test_rejects_tampering_wrong_key_and_garbage(self):
        sig = SIGN(b"msg")
        self.assertTrue(sigverify.ed25519_verify(PUB, b"msg", sig))
        self.assertFalse(sigverify.ed25519_verify(PUB, b"msh", sig))
        self.assertFalse(sigverify.ed25519_verify(OTHER_PUB, b"msg", sig))
        self.assertFalse(sigverify.ed25519_verify(PUB, b"msg", sig[:-1] + bytes([sig[-1] ^ 1])))
        self.assertFalse(sigverify.ed25519_verify(PUB, b"msg", b"short"))
        self.assertFalse(sigverify.ed25519_verify(b"\xff" * 32, b"msg", sig))


class VerifySets(unittest.TestCase):
    def keys(self, eco):
        return {eco: PUB.hex()}

    def test_urtc_valid_tampered_wrong_key_and_missing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            put_signed(folder, "fw.bin", b"image", lambda d: f"urtc-rel/1|fw.bin|{d}".encode())
            self.assertIs(sigverify.verify_dir(folder, "urtc", self.keys("urtc")), True)
            self.assertEqual(sigverify.verify_dir(folder, "urtc", {}), "unknown")          # no key pinned
            self.assertIs(sigverify.verify_dir(folder, "urtc", {"urtc": OTHER_PUB.hex()}), False)   # signed by another key
            (folder / "fw.bin").write_bytes(b"image!")                                      # the file changed after signing
            self.assertIs(sigverify.verify_dir(folder, "urtc", self.keys("urtc")), False)

    def test_one_bad_file_makes_the_set_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            put_signed(folder, "a.bin", b"a", lambda d: f"urtc-rel/1|a.bin|{d}".encode())
            put_signed(folder, "b.bin", b"b", lambda d: f"urtc-rel/1|b.bin|{d}".encode(), sign=OTHER_SIGN)
            self.assertIs(sigverify.verify_dir(folder, "urtc", self.keys("urtc")), False)

    def test_armor_package_and_unrecognised_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            put_signed(folder, "armor-studio-0.9.1.tgz", b"pkg", lambda d: f"armor-pkg/1|studio|0.9.1|{d}".encode())
            self.assertIs(sigverify.verify_dir(folder, "armor", self.keys("armor")), True)
            put_signed(folder, "odd.bin", b"x", lambda d: b"anything")
            self.assertEqual(sigverify.verify_dir(folder, "armor", self.keys("armor")), "unknown")   # a format this module does not check

    def test_hydra_never_says_false_for_a_format_it_does_not_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            put_signed(folder, "updater-0.3.6.tgz", b"pkg", lambda d: f"hydra-pc-pkg/1|updater|0.3.6|{d}".encode())
            self.assertIs(sigverify.verify_dir(folder, "hydra", self.keys("hydra")), True)
            (folder / "updater-0.3.6.tgz").write_bytes(b"other")   # hydra-sign binaries use another scheme: not provable here
            self.assertEqual(sigverify.verify_dir(folder, "hydra", self.keys("hydra")), "unknown")

    def test_no_signature_files_or_other_ecosystem(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.bin").write_bytes(b"x")
            (Path(tmp) / "a.bin.sig2").write_bytes(b"y")
            self.assertEqual(sigverify.verify_dir(Path(tmp), "urtc", self.keys("urtc")), "unknown")
        self.assertEqual(sigverify.verify_dir(Path(tmp) / "none", "urtc", self.keys("urtc")), "unknown")
        self.assertEqual(sigverify.ecosystem_of("EH3D-X"), "other")

    def test_pinned_keys_are_read_as_text_and_can_be_overridden(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "URTC" / "tools").mkdir(parents=True)
            (root / "URTC" / "tools" / "release_sign.py").write_text(f'SCHEME = "x"\nPUBLIC_KEY_HEX = "{PUB.hex()}"\n', encoding="utf-8")
            keys = sigverify.pinned_keys(root)
            self.assertEqual(keys, {"urtc": PUB.hex()})
            self.assertEqual(sigverify.pinned_keys(root, {"urtc": OTHER_PUB.hex(), "armor": "zz", "hydra": "ab" * 32})["urtc"], OTHER_PUB.hex())
            self.assertNotIn("armor", sigverify.pinned_keys(root, {"armor": "zz"}))
            self.assertEqual(sigverify.pinned_keys(root / "nowhere"), {})


class TrustInTheSnapshot(_testenv.Spanish, unittest.TestCase):
    """Only a release signature that VERIFIES lowers the pending-signature alert."""
    def local(self, tmp, sign=SIGN, key=PUB.hex(), build_name="R"):
        folder = Path(tmp) / "URTC-R" / "release-1.0.0"
        put_signed(folder, "fw.bin", b"image", lambda d: f"urtc-rel/1|fw.bin|{d}".encode(), sign=sign)
        stamp = datetime(2026, 11, 4, 8, 0, 0, tzinfo=timezone.utc).timestamp()   # after the build of the fixture, whatever the clock says
        for f in folder.iterdir():
            os.utime(f, (stamp, stamp))
        return signstate.local_records(tmp, {"urtc": key})

    def snap(self, local, cfg=None):
        return snapshot(repos=("URTC-R",), eco={"URTC-R": "urtc"}, local=local, cfg=cfg,
                        runs={"URTC-R": [run("URTC-R", "B", "success", "2000-01-01T00:00:00Z", rid=7)]})

    def test_local_index_carries_the_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            rec = self.local(tmp)["signed"]["URTC-R"]
            self.assertEqual((rec["kind"], rec["verified"]), ("release", True))
            bad = signstate.local_records(tmp, {"urtc": OTHER_PUB.hex()})["signed"]["URTC-R"]
            self.assertEqual((bad["kind"], bad["verified"]), ("release", False))
            self.assertEqual(signstate.local_records(tmp)["signed"]["URTC-R"]["verified"], "unknown")

    def test_verified_release_lowers_the_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = self.local(tmp)
            # the folder was just written: it is newer than the build of the fixture
            s = snapshot(repos=("URTC-R",), eco={"URTC-R": "urtc"}, local=local, runs={"URTC-R": [run("URTC-R", "B", "success", BUILD_AT, rid=7)]})
            st = s["a5"]["states"][0]
            self.assertEqual((st["state"], st["signature_kind"], st["signature_verified"], st["trusted"]), ("signed_local", "release", True, True))
            self.assertEqual(s["a5"]["pending_sign"], [])
            self.assertEqual([g["repo"] for g in s["a5"]["signed_unpublished"]], ["URTC-R"])
            self.assertEqual(s["a5"]["sign_queue"][0]["step"], "publish")
            self.assertTrue(s["a5"]["sign_queue"][0]["signature_verified"] is True)

    def test_a_signature_that_does_not_verify_keeps_the_alert_and_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = self.local(tmp, key=OTHER_PUB.hex())
            s = snapshot(repos=("URTC-R",), eco={"URTC-R": "urtc"}, local=local, runs={"URTC-R": [run("URTC-R", "B", "success", BUILD_AT, rid=7)]})
            self.assertEqual([g["repo"] for g in s["a5"]["pending_sign"]], ["URTC-R"])
            self.assertIs(s["a5"]["pending_sign"][0]["signature_verified"], False)
            self.assertEqual(s["a5"]["sign_queue"][0]["step"], "sign")
            self.assertTrue(any("sin verificar" in p["text"] and "no verifica" in p["text"] for p in s["parte"]))

    def test_unknown_keeps_the_alert_unless_the_owner_relaxes_the_rule(self):
        local = {"signed": {}, "batches": {"R": {"signed_at": "2026-11-04T08:00:00Z", "published_at": None}}}   # a batch said "signed", nothing to inspect
        strict = snapshot(local=local)
        self.assertEqual([g["repo"] for g in strict["a5"]["pending_sign"]], ["R"])
        self.assertEqual(strict["a5"]["states"][0]["signature_verified"], "unknown")
        relaxed = snapshot(local=local, cfg={"require_verified_signature": False})
        self.assertEqual(relaxed["a5"]["pending_sign"], [])
        self.assertTrue(relaxed["a5"]["states"][0]["trusted"] is True)

    def test_dev_signature_is_never_trusted_even_if_it_verifies(self):
        local = {"signed": {"R": {"version": "1", "kind": "dev", "verified": True, "signed_at": "2026-11-04T08:00:00Z"}}, "batches": {}}
        s = snapshot(local=local)
        self.assertEqual([g["repo"] for g in s["a5"]["pending_sign"]], ["R"])
        self.assertFalse(s["a5"]["states"][0]["trusted"])

    def test_a_published_release_still_wins_whatever_the_verdict(self):
        s = snapshot(local={"signed": {}, "batches": {}}, releases={"R": {"tagName": "v2", "publishedAt": "2026-11-03T12:00:00Z"}})
        self.assertEqual(s["a5"]["pending_sign"], [])

    def test_the_cache_does_not_hide_a_changed_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(self.local(tmp)["signed"]["URTC-R"]["verified"] is True)
            (Path(tmp) / "URTC-R" / "release-1.0.0" / "fw.bin").write_bytes(b"tampered, different size")
            self.assertIs(signstate.local_records(tmp, {"urtc": PUB.hex()})["signed"]["URTC-R"]["verified"], False)


class CiRedBridge(unittest.TestCase):
    def test_schema_2_has_pending_sign_per_repo(self):
        s = snapshot(local={"signed": {}, "batches": {}})
        data = ci_red.build(s)
        self.assertEqual((data["schema"], data["pending_sign_repos"], data["pending_sign_hours_threshold"]), (2, 1, 24))
        row = data["repos"]["R"]
        self.assertEqual(row["pending_sign_hours"], 26.0)   # kept from schema 1
        item = row["pending_sign"][0]
        self.assertEqual((item["workflow"], item["hours"], item["state"], item["signature_kind"], item["signature_verified"]),
                         ("firmware-build.yml", 26.0, "built_on_gha", "none", "unknown"))
        self.assertEqual(item["last_build_at"], BUILD_AT)
        json.dumps(data)   # serialisable

    def test_a_repo_with_only_red_has_an_empty_pending_list(self):
        s = snapshot(runs={"R": [run("R", "Build", "failure", "2026-11-04T05:00:00Z")]}, local={"signed": {}, "batches": {}})
        row = ci_red.build(s)["repos"]["R"]
        self.assertEqual((len(row["red"]), row["pending_sign"]), (1, []))

    def test_drive_paths_are_refused_whatever_the_system(self):
        for windows in (False, True):
            for text in ("D:/x/ci_red.json", "d:\\x\\a.json", "/mnt/d/x/a.json", "/d/x/a.json", "\\\\server\\share\\a.json"):
                self.assertIsNone(ci_red.target_path(text, windows=windows), (windows, text))

    def test_other_drive_letters_on_posix_are_refused_and_on_windows_allowed(self):
        self.assertIsNone(ci_red.target_path("C:/work/ci_red.json", windows=False))   # not a path on POSIX: it would create a folder named "C:"
        self.assertIsNone(ci_red.target_path("C:\\work\\ci_red.json", windows=False))
        if os.name == "nt":
            self.assertEqual(str(ci_red.target_path("C:/work/ci_red.json", windows=True)), str(Path("C:/work/ci_red.json")))
        else:
            self.assertIsNotNone(ci_red.target_path("C:/work/ci_red.json", windows=True))

    def test_relative_and_default_paths(self):
        base = Path(tempfile.gettempdir()) / "base"
        self.assertEqual(ci_red.target_path("", base, windows=False), base / "ci_red.json")
        self.assertEqual(ci_red.target_path("sub/x.json", base, windows=False), base / "sub" / "x.json")
        self.assertIsNone(ci_red.target_path("off", base))


class OneDefinitionOfLastRun(unittest.TestCase):
    def test_all_three_start_from_the_same_list(self):
        self.assertEqual(tuple(sl.IGNORED), tuple(signstate.IGNORED))
        runs = [run("R", "B", "success", "2026-11-04T01:00:00Z", rid=1), run("R", "B", "cancelled", "2026-11-04T02:00:00Z", rid=2),
                run("R", "B", "failure", "2026-11-04T03:00:00Z", branch="feature", rid=3), run("R", "B", "skipped", "2026-11-04T04:00:00Z", rid=4)]
        self.assertEqual([r["id"] for r in signstate.completed_runs(runs)], [1])
        self.assertEqual(sl.red_workflows({"R": runs}), [])
        self.assertEqual([g["repo"] for g in sl.green_without_release({"R": {"workflow": "firmware-build.yml"}}, {"R": runs}, {"R": {"publishedAt": "2026-10-01T00:00:00Z"}})], ["R"])
        rows = signstate.target_states({"R": {"workflow": "firmware-build.yml"}}, {"R": runs}, {}, {"R": "armor"}, {}, NOW)
        self.assertEqual((rows[0]["run_id"], rows[0]["built_on_gha"]), (1, True))
        runs.append(run("R", "B", "failure", "2026-11-04T05:00:00Z", rid=5))
        self.assertEqual(len(sl.red_workflows({"R": runs})), 1)   # a real failure on main turns it red...
        self.assertFalse(signstate.target_states({"R": {"workflow": "firmware-build.yml"}}, {"R": runs}, {}, {"R": "armor"}, {}, NOW)[0]["built_on_gha"])   # ...and it is no longer "built"


class Orphans(unittest.TestCase):
    def make_root(self, tmp, files):
        root = Path(tmp)
        for repo, workflows in files.items():
            (root / repo / ".git").mkdir(parents=True)
            (root / repo / ".github" / "workflows").mkdir(parents=True)
            for w in workflows:
                (root / repo / ".github" / "workflows" / w).write_text("name: x\n", encoding="utf-8")
        return root

    def test_coverage_is_by_repository_and_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp, {"URTC-NEW": ["firmware-build.yml"], "ARMOR-STUDIO": ["package-build.yml", "dist-build.yml"], "EH3D-X": ["apk-build.yml"],
                                        "HYDRA-UMC-SERVER": ["package-build.yml", "dist-build.yml"], "URTC": ["ci.yml"]})
            got = gd.uncovered_builds(root)
        self.assertIn(("URTC-NEW", "firmware-build.yml"), got)
        self.assertIn(("ARMOR-STUDIO", "dist-build.yml"), got)       # the repository is a target, but not this workflow
        self.assertNotIn(("ARMOR-STUDIO", "package-build.yml"), got)
        self.assertNotIn(("HYDRA-UMC-SERVER", "dist-build.yml"), got)   # covered by HYDRA-UMC-SERVER:dist
        self.assertIn(("EH3D-X", "apk-build.yml"), got)

    def test_orphan_rows_and_the_plan_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp, {"URTC-NEW": ["firmware-build.yml"], "EH3D-X": ["apk-build.yml"], "ARMOR-NODE-NEW": ["firmware-build.yml"]})
            head = lambda repo: ("a" * 40, "")
            with mock.patch.object(gd, "ROOT", root), mock.patch.object(gd, "local_head", head), \
                    mock.patch.object(gd, "ci_green", lambda repo, sha: (repo != "ARMOR-NODE-NEW", ["CI"], 0)):
                rows = gd.orphan_rows()
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = gd.cmd_plan(mock.Mock(only=None, ecosystem=None, json=False))
                text = out.getvalue()
                js = io.StringIO()
                with contextlib.redirect_stdout(js):
                    gd.cmd_plan(mock.Mock(only=None, ecosystem=None, json=True))
        by = {r["repo"]: r for r in rows}
        self.assertEqual(sorted(by), ["ARMOR-NODE-NEW", "URTC-NEW"])   # EH3D belongs to another session: never an orphan here
        self.assertTrue(by["URTC-NEW"]["ci_green"])
        self.assertFalse(by["ARMOR-NODE-NEW"]["ci_green"])
        self.assertEqual(by["ARMOR-NODE-NEW"]["proposed"]["tool"], "fetch_and_sign.py")
        self.assertIn("SIGNATURE ORPHANS (2)", text)
        self.assertIn("URTC-NEW: firmware-build.yml  CI green", text)
        self.assertIn("NOT green", text)
        self.assertEqual(len(json.loads(js.getvalue())["orphans"]), 2)

    def test_the_section_is_always_there_even_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp, {})
            with mock.patch.object(gd, "ROOT", root), mock.patch.object(gd, "local_head", lambda r: ("a" * 40, "")):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    gd.cmd_plan(mock.Mock(only=None, ecosystem=None, json=False))
        self.assertIn("SIGNATURE ORPHANS (0)", out.getvalue())
        self.assertIn("(none)", out.getvalue())

    def test_a_plan_of_some_targets_does_not_list_orphans(self):
        with mock.patch.object(gd, "local_head", lambda r: ("a" * 40, "")):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                gd.cmd_plan(mock.Mock(only=["URTC"], ecosystem=None, json=False))
        self.assertNotIn("ORPHANS", out.getvalue())


class Convention(unittest.TestCase):
    def test_default_tool_by_prefix(self):
        self.assertEqual(gd.candidate_target("URTC-NEW", "firmware-build.yml")["tool"], "urtc_fetch_and_sign.py")
        self.assertEqual(gd.candidate_target("HYDRA-UMC-NEW", "binaries-build.yml")["tool"], "hydra_fetch_and_sign.py")
        self.assertEqual(gd.candidate_target("ARMOR-NEW", "package-build.yml")["tool"], "armor_fetch_and_sign.py")
        fw = gd.candidate_target("ARMOR-NODE-NEW", "firmware-build.yml")
        self.assertEqual((fw["tool"], fw["extra"]), ("fetch_and_sign.py", ["-f", "idf_image=espressif/idf:v5.5.5"]))
        self.assertIsNone(gd.candidate_target("EH3D-X", "apk-build.yml"))
        self.assertIsNone(gd.candidate_target("URTC", "ci.yml"))
        self.assertEqual(gd.candidate_target("URTC", "firmware-build.yml", {"finalize_flags": ["--bench"], "repo": "x"})["finalize_flags"], ["--bench"])

    def test_targets_json_only_adds_overrides_to_the_convention(self):
        for name, target in gd.TARGETS.items():
            guess = gd.candidate_target(gd.repo_of(name), target["workflow"])
            self.assertIsNotNone(guess, name)
            self.assertEqual((guess["tool"], guess["extra"]), (target["tool"], target["extra"]), name)
            merged = gd.candidate_target(gd.repo_of(name), target["workflow"], target)
            self.assertEqual(merged, {k: v for k, v in target.items() if k != "repo"}, name)

    def test_names_of_parts(self):
        self.assertEqual(gd.candidate_name("URTC-NEW", "exe-build.yml", {}), "URTC-NEW")
        self.assertEqual(gd.candidate_name("URTC", "exe-build.yml", {"URTC": {}}), "URTC:exe")

    def test_proposals_are_valid_and_nothing_is_applied(self):
        builds = [("URTC-NEW", "firmware-build.yml"), ("URTC", "site-build.yml"), ("EH3D-X", "apk-build.yml")]
        proposals = gd.candidate_proposals(builds, targets=gd.TARGETS)
        self.assertEqual(sorted(proposals), ["URTC-NEW", "URTC:site"])
        self.assertEqual(proposals["URTC:site"]["repo"], "URTC")
        self.assertEqual(gd.validate_targets({**gd.TARGETS, **proposals}), [])
        before = gd.TARGETS_FILE.read_bytes()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(gd, "candidate_proposals", lambda: proposals):
            path = Path(tmp) / "targets.candidates.json"
            self.assertEqual(gd.write_candidates(path), proposals)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), proposals)
            with mock.patch.object(gd, "candidate_proposals", lambda: {}):
                other = Path(tmp) / "none.json"
                gd.write_candidates(other)
                self.assertFalse(other.exists())
        self.assertEqual(gd.TARGETS_FILE.read_bytes(), before)   # targets.json untouched

    def test_hygiene_only_writes_candidates_when_asked(self):
        with mock.patch.object(gd, "hygiene", lambda: ([], [], [], [])), mock.patch.object(gd, "write_candidates") as write:
            with contextlib.redirect_stdout(io.StringIO()):
                gd.cmd_hygiene(mock.Mock(write_candidates=False))
            write.assert_not_called()
            write.return_value = {}
            with contextlib.redirect_stdout(io.StringIO()):
                gd.cmd_hygiene(mock.Mock(write_candidates=True))
            write.assert_called_once()

    def test_the_candidates_file_never_travels(self):
        import make_release as mr
        self.assertEqual(mr.check_entries(["github_actions_monitor/targets.candidates.json"]), ["github_actions_monitor/targets.candidates.json"])
        self.assertIn("github_actions_monitor/sigverify.py", {f"github_actions_monitor/{p.name}" for p in mr.members()})


class ReportHistory(unittest.TestCase):
    def test_budget_and_report_lines_are_compared_without_the_numbers(self):
        today = snapshot(local={"signed": {}, "batches": {}}, cfg={"minutes_budget": {"armor": 100}},
                         runs={"R": [run("R", "Build", "success", "2026-11-04T01:00:00Z") | {"seconds": 4800}]})
        state = report_history.day_state(today)
        self.assertEqual(state["budget"], ["armor warn"])
        self.assertTrue(all(not any(ch.isdigit() for ch in line) for line in state["parte"]))
        yesterday = {"red": [], "pending_sign": [], "budget": [], "parte": ["old sentence"]}
        diff = report_history.compare(yesterday, state)
        self.assertEqual(diff["budget"]["appeared"], ["armor warn"])
        self.assertEqual(diff["parte"]["disappeared"], ["old sentence"])

    def test_a_day_saved_by_an_older_version_has_nothing_to_compare(self):
        diff = report_history.compare({"red": ["a"], "pending_sign": []}, {"red": [], "pending_sign": [], "budget": ["x warn"], "parte": ["l"]})
        self.assertTrue(diff["budget"]["no_base"] and diff["parte"]["no_base"])
        self.assertEqual((diff["budget"]["appeared"], diff["parte"]["appeared"]), ([], []))
        self.assertEqual(diff["red"]["disappeared"], ["a"])


class Page(unittest.TestCase):
    HTML = (Path(__file__).resolve().parents[1] / "assets" / "static" / "actions_monitor.html").read_text(encoding="utf-8")

    def test_kpis_queue_panel_and_budget_are_in_the_page(self):
        for needle in ('id="kp-red"', 'id="kp-sign"', 'id="k-budget"', "focusSignQueue", 'id="sign-queue"', "ui.rp_build_sign", "ui.rp_suggested", "ui.df_lines"):
            self.assertIn(needle, self.HTML, needle)

    def test_the_script_has_no_syntax_error_when_node_is_there(self):
        import re
        import shutil
        import subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        script = re.findall(r"<script>(.*?)</script>", self.HTML, re.S)[-1]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "page.js"
            path.write_text(script, encoding="utf-8")
            result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
