# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The operator side of the command line: the exit codes of `status` that say healthy / nothing serving / needs attention (with the classic codes kept by default), `watch branch` for the commit of the
folder you are in, the code on the disk newer than the process, and the settings that cannot work together (in the doctor and at the start)."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_190_cli as base  # noqa: E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import actions_monitor as am, codestale, configcheck, settings_api  # noqa: E402
from github_actions_monitor.cli import branchwatch, doctor, monitor_cli as cli, watch  # noqa: E402


def data(**extra):
    document = {"repos": ["widgets"], "figures": {"active": 1, "queued": 0, "fail24": 0, "ok24": 9, "red": 0}, "rate": {"remaining": 4000, "limit": 5000}, "updated": "2026-01-05T12:00:00Z", "offline": {"offline": False}}
    document.update(extra)
    return {"data": document}


def run_of(workflow, status="completed", conclusion="success", sha="abc1234", branch="main", repo="widgets", number=1):
    return {"repo": repo, "name": workflow, "branch": branch, "sha": sha, "status": status, "conclusion": conclusion, "number": number, "seconds": 30}


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), base.Fake)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        base.ANSWERS.clear()
        base.SEEN.clear()
        base.ANSWERS["/api/health"] = {"ok": True, "version": "2.1.5", "uptime_seconds": 10, "lite": False, "account": "acme", "code_stale": False}
        base.ANSWERS["/api/data"] = data()

    def status(self, *flags, config=None):
        with mock.patch.object(cli, "_config", return_value=config or {}):
            return base.run("status", "--url", self.url, "--lang", "en", *flags)


class TheExitCodesOfStatus(Server):
    def test_the_classic_codes_are_the_default_and_do_not_change(self):
        self.assertEqual(self.status()[0], 0)
        base.ANSWERS["/api/data"] = data(offline={"offline": True})
        self.assertEqual(self.status()[0], 4)      # degraded, as it always was
        base.ANSWERS["/api/data"] = data()
        self.assertEqual(cli.main(["status", "--url", "http://127.0.0.1:1", "--lang", "en"]), 2)      # unreachable

    def test_operator_says_healthy_as_zero(self):
        code, out, _ = self.status("--status-codes", "operator")
        self.assertEqual(code, 0)
        self.assertNotIn("code on the disk", out)

    def test_operator_says_up_but_needs_attention_as_two(self):
        cases = {"offline": data(offline={"offline": True}), "quota_paused": data(paused_quota=True), "no_data": {"data": {}}, "error": {"data": {"repos": []}, "error": "boom"}}
        for reason, answer in cases.items():
            base.ANSWERS["/api/data"] = answer
            code, out, _ = self.status("--status-codes", "operator", "--json")
            self.assertEqual(code, 2, reason)
            self.assertIn(reason, json.loads(out)["data"]["attention"], reason)
        base.ANSWERS["/api/data"] = data()
        base.ANSWERS["/api/health"]["code_stale"] = True
        code, out, _ = self.status("--status-codes", "operator")
        self.assertEqual(code, 2)
        self.assertIn("restart the monitor", out)

    def test_a_blind_credential_needs_attention(self):
        base.ANSWERS["/api/health"]["credential"] = {"state": "blind"}
        self.assertEqual(self.status("--status-codes", "operator")[0], 2)

    def test_nothing_serving_is_one_and_an_answer_that_is_not_a_monitor_is_two(self):
        with mock.patch.object(cli, "_config", return_value={}):
            self.assertEqual(cli.main(["status", "--url", "http://127.0.0.1:1", "--status-codes", "operator", "--lang", "en"]), 1)
        del base.ANSWERS["/api/data"]      # the port answers but it is not a monitor (404)
        self.assertEqual(self.status("--status-codes", "operator")[0], 2)

    def test_the_setting_chooses_the_scheme_and_the_flag_wins(self):
        base.ANSWERS["/api/data"] = data(paused_quota=True)
        self.assertEqual(self.status(config={"cli": {"status_codes": "operator"}})[0], 2)
        self.assertEqual(self.status("--status-codes", "classic", config={"cli": {"status_codes": "operator"}})[0], 0)
        self.assertEqual(self.status(config={"cli": {"status_codes": "nonsense"}})[0], 0)
        self.assertEqual(settings_api.SCHEMA and next(row[3] for row in settings_api.SCHEMA if row[1] == "cli.status_codes"), ("classic", "operator"))
        self.assertEqual(am.DEFAULTS["cli"]["status_codes"], "classic")

    def test_the_json_document_carries_the_code_of_the_scheme(self):
        base.ANSWERS["/api/data"] = data(paused_quota=True)
        code, out, _ = self.status("--status-codes", "operator", "--json")
        self.assertEqual((code, json.loads(out)["exit"]), (2, 2))


class TheCodeOnTheDisk(unittest.TestCase):
    def test_a_version_on_the_disk_that_is_not_the_running_one_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tool_version.py"
            path.write_text('"""x"""\nTOOL_VERSION = "9.9.9"\n', encoding="utf-8")
            self.assertEqual(codestale.disk_version(path), "9.9.9")
            self.assertTrue(codestale.stale("2.1.5", path))
            self.assertFalse(codestale.stale("9.9.9", path))
            self.assertFalse(codestale.stale("2.1.5", Path(tmp) / "missing.py"))      # nothing is claimed that is not known
            path.write_text("no version here", encoding="utf-8")
            self.assertFalse(codestale.stale("2.1.5", path))

    def test_the_real_file_agrees_with_the_running_code(self):
        self.assertFalse(codestale.stale())
        self.assertIs(am.health_payload()["code_stale"], False)
        with mock.patch.object(codestale, "disk_version", return_value="0.0.1"):
            self.assertIs(am.health_payload()["code_stale"], True)

    def test_the_doctor_warns_about_a_running_monitor_with_old_code_only(self):
        self.assertEqual(doctor.running_code([], reader=lambda port: {"version": "2.1.4", "code_stale": True}), ("ok", "not running"))
        self.assertEqual(doctor.running_code([8765], reader=lambda port: None), ("ok", "not running"))
        self.assertEqual(doctor.running_code([8765], reader=lambda port: {"server": "other"}), ("ok", "not running"))
        self.assertEqual(doctor.running_code([8765], reader=lambda port: {"version": "2.1.5", "code_stale": False}), ("ok", "running 2.1.5"))
        status, detail = doctor.running_code([8765], reader=lambda port: {"version": "2.1.4", "code_stale": True})
        self.assertEqual(status, "warn")
        self.assertIn("running 2.1.4", detail)
        self.assertIn("running", doctor.ORDER)
        for lang in i18n.LANGS:
            self.assertTrue(i18n.tl(lang, "doctor.t.running") and i18n.tl(lang, "doctor.f.running"))


class TheBranchOfTheFolder(Server):
    def test_the_address_of_a_remote_is_read_in_every_form_and_never_kept(self):
        for url in ("https://github.com/acme/widgets.git", "https://github.com/acme/widgets", "git@github.com:acme/widgets.git", "ssh://git@github.com/acme/widgets.git",
                    "https://user:secret@github.com/acme/widgets.git", "https://ghe.example.com:8443/acme/widgets/"):
            self.assertEqual(branchwatch.parse_remote(url), ("acme", "widgets"), url)
        for url in ("", "not a url", "/tmp/local/repo", "https://github.com/onlyowner", None):
            self.assertIsNone(branchwatch.parse_remote(url), url)

    def test_git_says_the_repository_the_branch_and_the_commit(self):
        calls = []

        def fake(args, **kwargs):
            calls.append(args)
            answers = {("remote", "get-url", "origin"): "git@github.com:acme/widgets.git", ("rev-parse", "--abbrev-ref", "HEAD"): "feature/x", ("rev-parse", "HEAD"): "a" * 40}
            return subprocess.CompletedProcess(args, 0, stdout=answers[tuple(args[1:])] + "\n", stderr="")
        context = branchwatch.git_context(None, runner=fake)
        self.assertEqual(context, {"owner": "acme", "name": "widgets", "branch": "feature/x", "sha": "a" * 40})
        self.assertTrue(all(call[0] == "git" and isinstance(call, list) for call in calls))      # a fixed list of arguments, never a shell
        detached = branchwatch.git_context(None, runner=lambda args, **k: subprocess.CompletedProcess(args, 0, stdout="HEAD\n", stderr=""))
        self.assertEqual(detached["branch"], "")
        broken = branchwatch.git_context(None, runner=lambda args, **k: (_ for _ in ()).throw(OSError("no git")))
        self.assertEqual(broken, {"owner": "", "name": "", "branch": "", "sha": ""})

    def test_the_states_of_the_runs(self):
        ev = branchwatch.evaluate
        self.assertEqual(ev([], "acme", "widgets", "main", "abc1234")["state"], "waiting")
        self.assertEqual(ev([run_of("CI", sha="other")], "acme", "widgets", "main", "abc1234")["state"], "waiting")      # another commit
        self.assertEqual(ev([run_of("CI", branch="dev")], "acme", "widgets", "main", "abc1234")["state"], "waiting")      # another branch
        self.assertEqual(ev([run_of("CI", repo="other")], "acme", "widgets", "main", "abc1234")["state"], "waiting")      # another repository
        self.assertEqual(ev([run_of("CI", repo="acme/widgets")], "acme", "widgets", "main", "abc1234")["state"], "passed")      # the full name works too
        self.assertEqual(ev([run_of("CI"), run_of("Lint", "in_progress", None)], "acme", "widgets", "main", "abc1234")["state"], "running")
        self.assertEqual(ev([run_of("CI"), run_of("Lint", conclusion="failure")], "acme", "widgets", "main", "abc1234")["state"], "failed")
        self.assertEqual(ev([run_of("CI", conclusion="cancelled")], "acme", "widgets", "main", "abc1234")["state"], "failed")
        self.assertEqual(ev([run_of("CI", conclusion="skipped")], "acme", "widgets", "main", "abc1234")["state"], "passed")
        newest = ev([run_of("CI", conclusion="failure", number=1), run_of("CI", conclusion="success", number=2)], "acme", "widgets", "main", "abc1234")
        self.assertEqual((newest["state"], len(newest["runs"])), ("passed", 1))      # a re-run replaces the failed one
        no_sha = ev([run_of("CI", sha="x"), run_of("Lint", sha="y")], "acme", "widgets", "main", "")
        self.assertEqual((no_sha["state"], len(no_sha["runs"])), ("passed", 2))      # without a commit, the newest run of each workflow
        self.assertEqual([branchwatch.exit_code(s) for s in branchwatch.STATES], [1, 1, 0, 1])

    def test_a_single_pass_says_zero_only_when_everything_passed(self):
        cases = ((["CI"], 0), (["CI", "Lint"], 0))
        base.ANSWERS["/api/data"] = data(runs=[run_of("CI"), run_of("Lint")])
        code, out, _ = base.run("watch", "branch", "--single-pass", "--repo", "acme/widgets", "--branch", "main", "--url", self.url, "--lang", "en")
        self.assertEqual(code, 0, cases)
        self.assertIn("all passed", out)
        base.ANSWERS["/api/data"] = data(runs=[run_of("CI"), run_of("Lint", conclusion="failure")])
        code, out, _ = base.run("watch", "branch", "--once", "--repo", "acme/widgets", "--branch", "main", "--url", self.url, "--lang", "en")
        self.assertEqual(code, 1)
        self.assertIn("failed", out)
        base.ANSWERS["/api/data"] = data(runs=[run_of("CI", "in_progress", None)])
        self.assertEqual(base.run("watch", "branch", "--once", "--repo", "acme/widgets", "--branch", "main", "--url", self.url, "--lang", "en")[0], 1)
        base.ANSWERS["/api/data"] = data(runs=[])
        code, out, _ = base.run("watch", "branch", "--once", "--repo", "acme/widgets", "--branch", "main", "--url", self.url, "--lang", "en")
        self.assertEqual(code, 1)
        self.assertIn("waiting", out)

    def test_the_folder_is_read_with_git_and_the_remote_never_appears(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
            git = lambda *a: subprocess.run(["git", *a], cwd=tmp, env=env, capture_output=True, text=True, check=True)      # noqa: E731
            try:
                git("init", "-q", "-b", "trunk")
                git("remote", "add", "origin", "https://user:SECRETTOKEN@github.com/acme/widgets.git")
                git("commit", "-q", "--allow-empty", "-m", "first")
            except (OSError, subprocess.CalledProcessError):
                self.skipTest("git is not available")
            sha = git("rev-parse", "HEAD").stdout.strip()
            base.ANSWERS["/api/data"] = data(runs=[run_of("CI", sha=sha[:7], branch="trunk")])
            before = os.getcwd()
            os.chdir(tmp)
            try:
                code, out, err = base.run("watch", "branch", "--single-pass", "--json", "--url", self.url, "--lang", "en")
            finally:
                os.chdir(before)
            self.assertEqual(code, 0, out + err)
            document = json.loads(out)["data"]
            self.assertEqual((document["repo"], document["branch"], document["sha"], document["state"]), ("acme/widgets", "trunk", sha[:7], "passed"))
            self.assertNotIn("SECRETTOKEN", out + err)
            self.assertNotIn("user:", out + err)

    def test_a_folder_without_a_remote_or_bad_arguments_are_a_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = os.getcwd()
            os.chdir(tmp)
            try:
                code, _, err = base.run("watch", "branch", "--once", "--url", self.url, "--lang", "en")
            finally:
                os.chdir(before)
        self.assertEqual(code, 1)
        self.assertIn("--repo", err)
        code, _, err = base.run("watch", "branch", "--once", "--repo", "bad repo!", "--url", self.url, "--lang", "en")
        self.assertEqual(code, 1)
        self.assertTrue(err.strip())
        code, _, err = base.run("watch", "branch", "--once", "--repo", "acme/widgets", "--branch", "../x", "--url", self.url, "--lang", "en")
        self.assertEqual(code, 1)

    def test_a_monitor_that_is_down_is_exit_two_as_in_every_watch(self):
        code, _, _ = base.run("watch", "branch", "--once", "--repo", "acme/widgets", "--branch", "main", "--url", "http://127.0.0.1:1", "--lang", "en")
        self.assertEqual(code, 2)


class TheLoopOfTheBranch(unittest.TestCase):
    def play(self, payloads, timeout=None, ticks=None):
        shown, pauses, notes = [], [], []
        queue = list(payloads)
        clock = iter(ticks or [0] * 200)

        def read():
            return queue.pop(0), ["line"], 0
        code = watch.run("branch", read, lambda p, l, c: shown.append(p), 5, sleep=pauses.append, stop=lambda p: p.get("exit") if p.get("done") else None, timeout=timeout,
                         clock=lambda: next(clock), on_timeout=lambda: notes.append("timeout"))
        return code, shown, pauses, notes

    def test_it_waits_until_the_runs_finish_and_ends_with_their_code(self):
        wait, run, ok, bad = {"state": "waiting", "done": False, "exit": 1}, {"state": "running", "done": False, "exit": 1}, {"state": "passed", "done": True, "exit": 0}, {"state": "failed", "done": True, "exit": 1}
        self.assertEqual(self.play([wait, run, ok])[:3], (0, [wait, run, ok], [5, 5]))
        self.assertEqual(self.play([wait, bad])[0], 1)

    def test_it_gives_up_with_one_after_the_time_it_was_given(self):
        wait = {"state": "waiting", "done": False, "exit": 1}
        code, shown, pauses, notes = self.play([wait] * 20, timeout=100, ticks=[0, 10, 50, 99, 100, 101])
        self.assertEqual((code, notes), (1, ["timeout"]))
        self.assertLess(len(shown), 20)

    def test_the_wait_comes_from_the_flag_then_the_setting_then_fifteen_minutes(self):
        self.assertEqual(watch.branch_timeout({}), 900)
        self.assertEqual(watch.branch_timeout({"cli": {"watch": {"branch_timeout_seconds": 60}}}), 60)
        self.assertEqual(watch.branch_timeout({"cli": {"watch": {"branch_timeout_seconds": 60}}}, 120), 120)
        self.assertEqual(watch.branch_timeout({"cli": {"watch": {"branch_timeout_seconds": 5}}}), 900)      # out of range: the default
        self.assertEqual(watch.branch_timeout({}, 999999), 900)
        self.assertEqual(am.DEFAULTS["cli"]["watch"]["branch_timeout_seconds"], 900)

    def test_a_change_of_state_is_a_change_for_exit_on_change(self):
        a = watch.signature("branch", {"state": "running", "runs": [{"workflow": "CI", "status": "in_progress", "conclusion": None}]})
        b = watch.signature("branch", {"state": "passed", "runs": [{"workflow": "CI", "status": "completed", "conclusion": "success"}]})
        self.assertNotEqual(a, b)
        self.assertIn("branch", watch.WATCHABLE)


class TheSettingsThatCannotWorkTogether(unittest.TestCase):
    def ids(self, config):
        return [item["id"] for item in configcheck.conflicts(config)]

    def test_what_the_monitor_holds_by_default_and_the_example_have_no_conflict(self):
        self.assertEqual(configcheck.conflicts(json.loads(json.dumps(am.DEFAULTS))), [])
        self.assertEqual(configcheck.conflicts(json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))), [])
        self.assertEqual(configcheck.conflicts({}), [])
        self.assertEqual(configcheck.conflicts("not a dict"), [])

    def test_each_combination_is_named_with_the_settings_that_disagree(self):
        cases = {
            "repos_exclude": {"repos": ["a", "b"], "exclude": ["b"]},
            "repos_ecosystems": {"repos": ["a"], "ecosystems": ["armor"]},
            "airgapped_updates": {"airgapped": True, "updates": {"check": True}},
            "sound_server_off": {"sound": {"enabled": False, "server_beep": True}},
            "sound_background_off": {"sound": {"enabled": False, "ambient": True}},
            "quiet_same_hours": {"sound": {"quiet_enabled": True, "quiet_from_hour": 5, "quiet_to_hour": 5}},
            "ai_execute_off": {"ai": {"actions": {"execute": True}}},
            "kiosk_rotate_off": {"kiosk": {"rotate_views": True}},
        }
        self.assertEqual(sorted(cases), sorted(configcheck.CONFLICT_IDS))
        for rule, config in cases.items():
            found = configcheck.conflicts(config)
            self.assertEqual([item["id"] for item in found], [rule], rule)
            self.assertGreaterEqual(len(found[0]["paths"]), 2, rule)

    def test_the_same_settings_in_agreement_are_not_a_conflict(self):
        for config in ({"repos": "all", "ecosystems": ["armor"]}, {"repos": ["a"], "exclude": ["b"]}, {"airgapped": True, "updates": {"check": False}}, {"sound": {"enabled": True, "server_beep": True}},
                       {"sound": {"enabled": False, "server_beep": False, "ambient": False, "tick": False}}, {"sound": {"quiet_enabled": True, "quiet_from_hour": 22, "quiet_to_hour": 7}},
                       {"sound": {"quiet_enabled": False, "quiet_from_hour": 5, "quiet_to_hour": 5}}, {"ai": {"actions": {"enabled": True, "execute": True}}}, {"kiosk": {"enabled": True, "rotate_views": True}}):
            self.assertEqual(configcheck.conflicts(config), [], config)

    def test_the_wall_screens_sound_needs_the_sounds_on(self):
        found = configcheck.conflicts({"sound": {"enabled": False, "tick": True}, "screens": {"sound": True}})
        self.assertEqual(found[0]["paths"], ["sound.enabled", "screens.sound", "sound.tick"])

    def test_the_doctor_lists_them_and_every_rule_has_its_text_in_the_eight_languages(self):
        self.assertIn("conflicts", doctor.ORDER)
        self.assertEqual(doctor.conflicts({}), ("ok", ""))
        status, detail = doctor.conflicts({"sound": {"enabled": False, "server_beep": True}})
        self.assertEqual(status, "warn")
        self.assertIn("sound_server_off (sound.enabled, sound.server_beep)", detail)
        for lang in i18n.LANGS:
            for rule in configcheck.CONFLICT_IDS:
                text = i18n.tl(lang, "mon.conflict_" + rule)
                self.assertIn("{paths}", text, (lang, rule))
            self.assertTrue(i18n.tl(lang, "doctor.t.conflicts") and i18n.tl(lang, "doctor.f.conflicts"))

    def run_report(self, raw):
        out = io.StringIO()
        with mock.patch.object(am.toolconfig, "raw_config", return_value=raw), contextlib.redirect_stdout(out):
            return am.report_config_problems(am.DEFAULTS), out.getvalue()

    def test_the_start_prints_them_and_the_strict_switch_refuses_to_start(self):
        ok, text = self.run_report({"sound": {"enabled": False, "server_beep": True}})
        self.assertTrue(ok)
        self.assertIn("sound.server_beep", text)
        ok, text = self.run_report({"sound": {"enabled": False, "server_beep": True}, "config_check": {"strict": True}})
        self.assertFalse(ok)
        self.assertIn("config_check.strict", text)
        ok, text = self.run_report({"config_check": {"strict": True}})
        self.assertTrue(ok)
        self.assertEqual(text, "")


if __name__ == "__main__":
    unittest.main()
