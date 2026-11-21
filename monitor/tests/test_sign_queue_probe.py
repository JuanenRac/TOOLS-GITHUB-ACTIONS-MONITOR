# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The signing queue only offers what really has to be signed: a dry run never, a version already published with its signature never, and a row nobody looked at yet says so. Also the cause of a read
that timed out."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.integrations import remote_workflows  # noqa: E402
from github_actions_monitor.sentinels import signstate  # noqa: E402


def row(name, run_id, repo=None):
    return {"name": name, "repo": repo or name, "run_id": run_id, "step": "sign", "hours": 3.0, "ecosystem": "hydra"}


def jobs(draft_conclusion):
    return {"jobs": [{"steps": [{"name": "Build", "conclusion": "success"}, {"name": "Prepare the draft", "conclusion": draft_conclusion}]}]}


def releases(*items):
    return [{"tag_name": t, "draft": d} for t, d in items]


NOW = 1_800_000_000
SIGNED = {"asset_flags": {"sig": True, "sig2": False, "sha256": True, "imgsig": False, "assets": 3}}


class DryRun(unittest.TestCase):
    def test_the_step_prepare_the_draft_tells_a_dry_run(self):
        self.assertIs(signstate.dry_run_of(jobs("skipped")), True)
        self.assertIs(signstate.dry_run_of(jobs("success")), False)
        self.assertIsNone(signstate.dry_run_of({"jobs": [{"steps": [{"name": "Build", "conclusion": "success"}]}]}))
        self.assertIsNone(signstate.dry_run_of(None))


class Queue(unittest.TestCase):
    def test_the_five_false_rows_of_the_panel_leave_and_a_real_draft_stays(self):
        queue = [row("HYDRA-UMC-JOB-DISPATCHER", 1), row("HYDRA-UMC-ORCHESTRATOR", 2), row("ARMOR-ANDROID-CONTROL", 4), row("HYDRA-UMC", 5), row("REAL", 6), row("NEW", 7)]
        probe = {
            "HYDRA-UMC-JOB-DISPATCHER|1": signstate.probe_of(jobs("success"), releases(("v0.3.1", False)), NOW),      # a manual build whose version is already published and signed
            "HYDRA-UMC-ORCHESTRATOR|2": signstate.probe_of(jobs("success"), releases(("v0.2.7", False)), NOW),
            "ARMOR-ANDROID-CONTROL|4": signstate.probe_of(jobs("success"), releases(("v0.8.0.9", False)), NOW),
            "HYDRA-UMC|5": signstate.probe_of(jobs("skipped"), releases(("v0.3.0", False)), NOW),      # a dry run
            "REAL|6": signstate.probe_of(jobs("success"), releases(("v1.0.0", True), ("v0.9.0", False)), NOW),      # a draft is waiting
        }
        rel = {r: SIGNED for r in ("HYDRA-UMC-JOB-DISPATCHER", "HYDRA-UMC-ORCHESTRATOR", "ARMOR-ANDROID-CONTROL", "HYDRA-UMC", "REAL")}
        kept, cleared = signstate.apply_probe(queue, probe, rel)
        self.assertEqual([(k["name"], k["checked"]) for k in kept], [("REAL", True), ("NEW", False)], "the draft stays; the row nobody looked at stays as not checked")
        self.assertEqual(kept[0]["draft"], "v1.0.0")
        self.assertEqual({c["name"]: (c["reason"], c["tag"]) for c in cleared}, {"HYDRA-UMC-JOB-DISPATCHER": ("published", "v0.3.1"), "HYDRA-UMC-ORCHESTRATOR": ("published", "v0.2.7"),
                                                                                  "ARMOR-ANDROID-CONTROL": ("published", "v0.8.0.9"), "HYDRA-UMC": ("dry_run", "")})

    def test_a_published_version_without_signature_or_with_no_release_at_all_stays(self):
        queue = [row("A", 1), row("B", 2)]
        probe = {"A|1": signstate.probe_of(jobs("success"), releases(("v1", False)), NOW), "B|2": signstate.probe_of(jobs("success"), [], NOW)}
        kept, cleared = signstate.apply_probe(queue, probe, {"A": {"asset_flags": {"sig": False, "sig2": False, "sha256": False, "imgsig": False, "assets": 1}}, "B": SIGNED})
        self.assertEqual(([k["name"] for k in kept], cleared), (["A", "B"], []))


class Reasons(unittest.TestCase):
    def test_a_read_that_timed_out_says_timeout_in_the_eight_languages(self):
        self.assertEqual((remote_workflows.reason_of("timeout"), remote_workflows.reason_of("rate limit exceeded"), remote_workflows.reason_of("boom")), ("timeout", "rate_limited", "error"))
        for lang in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
            for key in ("lint.reason.timeout", "ui.a5_cleared_h", "ui.a5_cleared_dry", "ui.a5_cleared_pub", "security.t.branch_weak", "cfg.h.sentinels.security.signals.branch.require"):
                self.assertNotEqual(i18n.tl(lang, key), key, f"{lang} {key}")


if __name__ == "__main__":
    unittest.main()
