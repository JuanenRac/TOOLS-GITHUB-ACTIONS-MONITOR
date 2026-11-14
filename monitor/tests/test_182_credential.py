# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A login of GitHub that GitHub revokes or lets expire: only that account turns blind, a critical system alert opens once, and another login can be put in its place without a restart."""
import json
import os
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.security import credential, secretstore  # noqa: E402
from github_actions_monitor.sentinels import alert_center  # noqa: E402

GOOD = "ghp_" + "A" * 36
OTHER = "ghp_" + "B" * 36
BAD401 = "gh: Bad credentials (HTTP 401)"


class Base(unittest.TestCase):
    def setUp(self):
        credential.reset()
        secretstore.APPLIED["token"] = ""
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.folder = Path(self.dir.name)
        self.addCleanup(credential.reset)
        self.addCleanup(lambda: secretstore.APPLIED.update(token=""))


class Detection(Base):
    def test_a_login_that_is_no_good_is_told_from_a_missing_permission(self):
        for text in (BAD401, "HTTP 401", "Bad credentials", "The token has expired", "token revoked", "gh auth login", "set the GH_TOKEN environment variable"):
            self.assertTrue(credential.is_dead_login(text), text)
        for text in ("HTTP 403: Resource not accessible by integration", "HTTP 404", "timeout", ""):
            self.assertFalse(credential.is_dead_login(text), text)

    def test_the_reason_is_expired_missing_or_revoked(self):
        self.assertEqual(credential.classify("Personal access token has expired (HTTP 401)"), "expired")
        self.assertEqual(credential.classify("gh: To use GitHub CLI in automation, set the GH_TOKEN environment variable"), "missing")
        self.assertEqual(credential.classify(BAD401), "revoked")

    def test_one_stray_refusal_is_not_a_lost_login_two_in_a_row_are(self):
        self.assertEqual(credential.note_refusal(BAD401), "strike")
        self.assertFalse(credential.is_blind())
        self.assertEqual(credential.note_refusal(BAD401), "blind")
        self.assertTrue(credential.is_blind())
        self.assertEqual(credential.note_refusal(BAD401), "", "the alert opens once, not at every cycle")

    def test_a_refusal_of_one_permission_never_makes_the_account_blind(self):
        for _ in range(5):
            self.assertEqual(credential.note_refusal("HTTP 403: Resource not accessible by integration"), "")
        self.assertFalse(credential.is_blind())

    def test_a_good_cycle_in_between_resets_the_count_and_a_good_cycle_ends_blindness(self):
        credential.note_refusal(BAD401)
        self.assertEqual(credential.note_success(), "")
        self.assertEqual(credential.note_refusal(BAD401), "strike", "the count started again")
        credential.note_refusal(BAD401)
        self.assertEqual(credential.note_success(), "back")
        self.assertFalse(credential.is_blind())
        self.assertEqual(credential.snapshot()["state"], "ok")

    def test_blind_from_the_start(self):
        self.assertTrue(credential.mark_blind(BAD401))
        self.assertTrue(credential.is_blind())
        self.assertFalse(credential.mark_blind("timeout"), "a network failure is not a lost login")

    def test_the_critical_system_alert_has_the_shape_of_the_alerts_of_the_sentinels(self):
        self.assertEqual(credential.system_alerts("alpha", "t"), [])
        credential.mark_blind(BAD401, now=1_700_000_000)
        alert, = credential.system_alerts("alpha", "title")
        self.assertEqual((alert["level"], alert["sentinel"], alert["code"], alert["account_id"], alert["id"]), ("critical", "system", "system.credential_blind", "alpha", "system.credential:alpha"))
        for key in ("id", "code", "level", "sentinel", "account_id", "repo", "title", "details", "created_at"):
            self.assertIn(key, alert)

    def test_the_alert_centre_lists_it_first_and_it_can_be_silenced_like_any_other(self):
        credential.mark_blind(BAD401)
        extra = credential.system_alerts("alpha", "title")
        listed = alert_center.collect(None, extra=extra)
        self.assertEqual([a["code"] for a in listed], ["system.credential_blind"])
        warning = {"id": "w", "code": "x", "level": "warning", "sentinel": "ci", "details": {}, "created_at": "2026-01-01T00:00:00Z"}
        error = dict(warning, id="e", level="error")
        ordered = alert_center.select(listed + [warning, error], "", "", "show")
        self.assertEqual([a["level"] for a in ordered], ["critical", "error", "warning"])
        self.assertEqual(alert_center.summary(listed)["by_sentinel"], {"system": 1})


class Replacing(Base):
    def test_a_token_that_is_not_one_of_github_is_refused_before_anything_is_asked(self):
        asked = []
        self.assertEqual(credential.replace(self.folder, "not a token", lambda: asked.append(1) or (True, "")), (False, "format"))
        self.assertEqual(asked, [])

    def test_a_token_that_github_refuses_changes_nothing(self):
        secretstore.APPLIED["token"] = GOOD
        self.assertEqual(credential.replace(self.folder, OTHER, lambda: (False, "rejected")), (False, "rejected"))
        self.assertEqual(secretstore.APPLIED["token"], GOOD, "the old login is back")
        self.assertFalse((self.folder / credential.FILE_NAME).exists(), "nothing was written")

    def test_the_token_is_checked_with_the_new_login_and_then_kept_in_a_private_file(self):
        credential.mark_blind(BAD401)
        seen = []
        ok = credential.replace(self.folder, OTHER, lambda: seen.append(secretstore.APPLIED["token"]) or (True, ""))
        self.assertEqual(ok, (True, "saved"))
        self.assertEqual(seen, [OTHER], "GitHub was asked with the NEW token")
        self.assertEqual(secretstore.APPLIED["token"], OTHER)
        path = credential.path_in(self.folder)
        self.assertEqual(path.read_text(encoding="utf-8").strip(), OTHER)
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertFalse(credential.is_blind())
        self.assertEqual(credential.snapshot()["source"], "account")

    def test_a_check_that_cannot_run_keeps_the_old_login(self):
        secretstore.APPLIED["token"] = GOOD

        def boom():
            raise OSError("no network")
        self.assertEqual(credential.replace(self.folder, OTHER, boom), (False, "unreachable"))
        self.assertEqual(secretstore.APPLIED["token"], GOOD)

    def test_the_token_is_nowhere_in_what_the_page_and_the_alert_may_say(self):
        credential.replace(self.folder, OTHER, lambda: (True, ""))
        credential.note_refusal(BAD401 + " " + OTHER)
        credential.note_refusal(BAD401 + " " + OTHER)
        text = json.dumps([credential.snapshot(), credential.system_alerts("a", "t"), credential.STATE])
        self.assertNotIn(OTHER, text)
        self.assertNotIn("ghp_", text)


class Reading(Base):
    def test_the_account_file_wins_over_the_file_of_the_platform_and_both_win_over_gh(self):
        named = self.folder / "platform_secret"
        named.write_text(GOOD + "\n", encoding="utf-8")
        env = {"GH_TOKEN_FILE": str(named)}
        self.assertEqual(credential.stored(self.folder, env), (GOOD, "file"))
        credential.path_in(self.folder).write_text(OTHER + "\n", encoding="utf-8")
        self.assertEqual(credential.stored(self.folder, env), (OTHER, "account"))
        credential.path_in(self.folder).unlink()
        named.unlink()
        self.assertEqual(credential.stored(self.folder, env), ("", ""))

    def test_a_file_that_does_not_hold_a_token_is_ignored(self):
        credential.path_in(self.folder).write_text("hello\n", encoding="utf-8")
        self.assertEqual(credential.stored(self.folder, {}), ("", ""))

    def test_reload_uses_the_new_file_and_a_refused_token_is_not_kept(self):
        secretstore.APPLIED["token"] = GOOD
        credential.path_in(self.folder).write_text(OTHER + "\n", encoding="utf-8")
        self.assertEqual(credential.reload(self.folder, lambda: (False, "rejected"), env={}), "rejected")
        self.assertEqual(secretstore.APPLIED["token"], GOOD)
        credential.mark_blind(BAD401)
        self.assertEqual(credential.reload(self.folder, lambda: (True, ""), env={}), "reloaded")
        self.assertEqual(secretstore.APPLIED["token"], OTHER)
        self.assertFalse(credential.is_blind())
        self.assertEqual(credential.reload(self.folder, lambda: (True, ""), env={}), "unchanged")

    def test_without_a_file_reload_says_none_and_gh_keeps_what_it_used(self):
        self.assertEqual(credential.reload(self.folder, None, env={}), "none")
        self.assertEqual(secretstore.gh_kwargs(), {})

    def test_apply_stored_hands_the_token_to_gh_only_through_its_environment(self):
        credential.path_in(self.folder).write_text(GOOD + "\n", encoding="utf-8")
        self.assertEqual(credential.apply_stored(self.folder, {}), "account")
        self.assertEqual(secretstore.gh_kwargs()["env"]["GH_TOKEN"], GOOD)
        self.assertNotEqual(os.environ.get("GH_TOKEN"), GOOD, "never put in the environment of this process")


class InTheMonitor(Base):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(am, "announce_credential")
        self.announce = patcher.start()
        self.addCleanup(patcher.stop)

    def test_two_refusals_make_the_account_blind_and_the_alert_is_raised_once(self):
        self.assertEqual(am.credential_refusal(am.AuthError(BAD401), {}), "strike")
        self.assertEqual(am.credential_refusal(am.AuthError(BAD401), {}), "blind")
        self.assertEqual(am.credential_refusal(am.AuthError(BAD401), {}), "")
        self.announce.assert_called_once_with("credential_blind", {})

    def test_the_first_refusal_is_confirmed_soon_not_after_a_whole_minute(self):
        self.assertLess(am.CONFIRM_DELAY, 60)

    def test_a_missing_login_in_the_generic_error_counts_too(self):
        am.credential_refusal(RuntimeError("gh: To use GitHub CLI in automation, set the GH_TOKEN environment variable."), {})
        am.credential_refusal(RuntimeError("gh: To use GitHub CLI in automation, set the GH_TOKEN environment variable."), {})
        self.assertEqual(credential.snapshot()["reason"], "missing")

    def test_a_good_cycle_announces_the_return_once(self):
        credential.mark_blind(BAD401)
        am.credential_ok({})
        am.credential_ok({})
        self.announce.assert_called_once_with("credential_back", {})

    def test_the_lite_edition_does_nothing(self):
        with mock.patch.dict(am.LITE, {"on": True}):
            self.assertEqual(am.credential_refusal(am.AuthError(BAD401), {}), "")
            self.assertEqual(am.credential_alerts(), [])
            payload = am.health_payload(True)
        self.assertNotIn("credential", payload)
        self.assertNotIn("cycle", payload)
        self.assertTrue(payload["ok"])

    def test_the_health_answer_says_the_state_of_the_login_and_the_alert_is_in_the_alerts(self):
        credential.mark_blind(BAD401)
        health = am.health_payload()
        self.assertEqual(health["credential"]["state"], "blind")
        self.assertTrue(health["ok"], "a lost login is not a reason to restart the service")
        with mock.patch.object(am, "cycle_verdict", return_value=""):
            payload, code = am.health_reply(True)
        self.assertEqual(code, 200)
        self.assertEqual(payload["credential"]["reason"], "revoked")
        alerts = am.alerts_payload({})
        self.assertIn("system", alerts["sentinels"])
        self.assertEqual([a["code"] for a in alerts["alerts"] if a["sentinel"] == "system"], ["system.credential_blind"])

    def test_the_deep_health_check_fails_when_the_cycle_is_stuck_or_gone_and_the_shallow_one_does_not(self):
        for verdict in ("stuck", "dead"):
            with mock.patch.object(am, "cycle_verdict", return_value=verdict):
                payload, code = am.health_reply(True)
                self.assertEqual((code, payload["ok"], payload["cycle"][verdict]), (503, False, True), verdict)
                self.assertEqual(am.health_reply(False)[1], 200)

    def test_replace_through_the_monitor_checks_keeps_and_restarts_the_loop(self):
        credential.mark_blind(BAD401)
        with mock.patch.object(am, "state_dir", return_value=self.folder), mock.patch.object(am, "verify_credential", return_value=(True, "")), mock.patch.object(am, "start_loop") as loop:
            ok, status, info = am.credential_change("replace", OTHER)
        self.assertEqual((ok, status, info["state"]), (True, "saved", "ok"))
        loop.assert_called_once()
        self.announce.assert_called_once_with("credential_back", mock.ANY)
        self.assertNotIn(OTHER, json.dumps(info))

    def test_a_refused_replacement_does_not_restart_anything_nor_announce(self):
        credential.mark_blind(BAD401)
        with mock.patch.object(am, "state_dir", return_value=self.folder), mock.patch.object(am, "verify_credential", return_value=(False, "rejected")), mock.patch.object(am, "start_loop") as loop:
            ok, status, info = am.credential_change("replace", OTHER)
        self.assertEqual((ok, status, info["state"]), (False, "rejected", "blind"))
        loop.assert_not_called()
        self.announce.assert_not_called()

    def test_an_unknown_action_is_a_bad_request(self):
        self.assertEqual(am.credential_change("delete")[:2], (False, "request"))

    def test_sighup_reads_the_files_again_in_a_thread(self):
        called = threading.Event()
        with mock.patch.object(am, "credential_change", side_effect=lambda action, token="": called.set() or (True, "reloaded", {})) as change:
            am.reload_on_signal()
            self.assertTrue(called.wait(5))
        change.assert_called_once_with("reload")

    def test_a_service_does_not_give_up_on_a_login_that_is_no_good_a_plain_monitor_does(self):
        with mock.patch.dict(os.environ, {"MONITOR_SERVICE": "1"}):
            self.assertTrue(am.service_mode())
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MONITOR_SERVICE", None)
            self.assertFalse(am.service_mode())
        with mock.patch.dict(am.CHILD, {"account": "alpha"}):
            self.assertTrue(am.service_mode())

    def test_the_credential_endpoint_exists_only_for_the_complete_edition(self):
        text = (HERE / "src" / "github_actions_monitor" / "app" / "actions_monitor.py").read_text(encoding="utf-8")
        self.assertIn('path == "/api/credential"', text)


class Doctor(Base):
    def test_accounts_that_each_got_their_own_login_do_not_share_one_token(self):
        from github_actions_monitor.accounts import accounts
        from github_actions_monitor.cli import doctor
        with mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": str(self.folder / "accounts")}):
            for name in ("a", "b"):
                accounts.create_account(name, name + "-owner")
            env = {"GH_TOKEN": GOOD}
            self.assertEqual(doctor.shared_credential(self.folder, env)[0], "warn", "both inherit the same GH_TOKEN")
            credential.path_in(accounts.account_dir("a")).write_text(OTHER + chr(10), encoding="utf-8")
            self.assertEqual(doctor.shared_credential(self.folder, env)[0], "ok", "one of them has a login of its own")


if __name__ == "__main__":
    unittest.main()
