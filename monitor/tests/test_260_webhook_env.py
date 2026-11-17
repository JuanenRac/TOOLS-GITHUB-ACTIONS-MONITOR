# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The incoming webhook: the shared secret only travels in the environment, every refusal of the receiver (bad signature, replay, huge body, event outside the closed list), and the coverage indicator."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _testenv  # noqa: F401
from github_actions_monitor.app import actions_monitor as am
from github_actions_monitor.app import settings_api
from github_actions_monitor.security import envguard, webhook

SECRET = "k" * 40
CONFIG = {"webhook": {"enabled": True}}
BODY = {"repository": {"name": "R", "full_name": "JuanenRac/R"}}


def send(config=None, body=None, event="workflow_run", delivery="11111111-2222-3333-4444-555555555555", signature=None, secret=SECRET, raw=None):
    raw = raw if raw is not None else json.dumps(body or BODY).encode()
    headers = {"X-GitHub-Event": event, "X-Hub-Signature-256": signature or webhook.sign(secret, raw)}
    if delivery:
        headers["X-GitHub-Delivery"] = delivery
    return webhook.handle(config or CONFIG, raw, headers, ["R"])


class SecretOnlyInTheEnvironment(unittest.TestCase):
    def setUp(self):
        webhook.reset()
        patch = mock.patch.dict(os.environ, {}, clear=False)
        patch.start()
        self.addCleanup(patch.stop)
        os.environ.pop(webhook.SECRET_ENV, None)
        self.addCleanup(envguard.HELD.pop, webhook.SECRET_ENV, None)

    def test_without_the_variable_the_receiver_is_closed_even_if_the_file_has_a_secret(self):
        config = {"webhook": {"enabled": True, "secret": SECRET}}
        self.assertFalse(webhook.active(config))
        self.assertEqual(webhook.secret_source(config), "none")
        self.assertEqual(send(config)[0], 404)

    def test_the_variable_opens_it_and_a_short_one_does_not(self):
        os.environ[webhook.SECRET_ENV] = SECRET
        self.assertTrue(webhook.active(CONFIG))
        self.assertEqual(webhook.secret_source(CONFIG), "env")
        os.environ[webhook.SECRET_ENV] = "short"
        self.assertFalse(webhook.active(CONFIG))
        self.assertEqual(webhook.status_text(CONFIG), webhook.text("bad_secret"))

    def test_another_name_can_be_chosen_and_a_wrong_name_falls_back_to_the_default(self):
        os.environ["MY_HOOK_SECRET"] = SECRET
        self.addCleanup(os.environ.pop, "MY_HOOK_SECRET", None)
        self.assertTrue(webhook.active({"webhook": {"enabled": True, "secret_env": "MY_HOOK_SECRET"}}))
        self.assertEqual(webhook.secret_env_name({"webhook": {"secret_env": "bad name; rm"}}), webhook.SECRET_ENV)
        self.assertEqual(webhook.secret_env_name({"webhook": {"secret_env": 7}}), webhook.SECRET_ENV)
        self.assertEqual(webhook.secret_env_name({}), webhook.SECRET_ENV)

    def test_a_secret_handed_over_in_a_file_works_like_the_variable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hook.secret"
            path.write_text(SECRET + "\nsecond line is never read\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {webhook.SECRET_ENV + "_FILE": str(path)}):
                self.assertTrue(webhook.active(CONFIG))
                self.assertEqual(webhook.settings(CONFIG)["secret"], SECRET)
            with mock.patch.dict(os.environ, {webhook.SECRET_ENV + "_FILE": str(Path(tmp) / "missing")}):
                self.assertFalse(webhook.active(CONFIG))

    def test_the_old_way_needs_an_explicit_switch_and_is_flagged(self):
        config = {"webhook": {"enabled": True, "secret": SECRET, "allow_config_secret": True}}
        self.assertTrue(webhook.active(config))
        self.assertEqual(webhook.secret_source(config), "config")
        os.environ[webhook.SECRET_ENV] = "e" * 40
        self.assertEqual(webhook.secret_source(config), "env", "the variable wins over the file")

    def test_a_held_variable_still_reaches_the_receiver_but_not_the_programs_the_monitor_starts(self):
        os.environ[webhook.SECRET_ENV] = SECRET
        envguard.hold(webhook.secret_env_name(CONFIG))
        self.assertNotIn(webhook.SECRET_ENV, os.environ)
        self.assertNotIn(webhook.SECRET_ENV, envguard.clean_environment())
        self.assertTrue(webhook.active(CONFIG))

    def test_the_secret_is_in_no_status_no_setting_and_no_settings_page(self):
        os.environ[webhook.SECRET_ENV] = SECRET
        status = am.webhook_status(CONFIG)
        self.assertNotIn(SECRET, json.dumps(status))
        self.assertEqual((status["secret_source"], status["secret_ok"]), ("env", True))
        self.assertNotIn(SECRET, json.dumps(settings_api.describe(Path(tempfile.gettempdir()) / "does_not_exist_hook.json")))
        self.assertEqual(settings_api.webhook_state(CONFIG), "defined")
        self.assertNotIn("webhook.secret", settings_api.FIELDS)
        self.assertNotIn("secret", am.DEFAULTS["webhook"])


class EveryRefusal(unittest.TestCase):
    def setUp(self):
        webhook.reset()
        patch = mock.patch.dict(os.environ, {webhook.SECRET_ENV: SECRET})
        patch.start()
        self.addCleanup(patch.stop)

    def test_an_invalid_signature_is_refused_and_nothing_else_is_looked_at(self):
        code, answer, repo = send(signature="sha256=" + "0" * 64)
        self.assertEqual((code, repo), (401, None))
        self.assertNotIn(SECRET, json.dumps(answer))
        for header in (None, "", "sha256=", "md5=abc", "sha256=" + "z" * 64, "SHA256=" + "0" * 64):
            raw = json.dumps(BODY).encode()
            headers = {"X-GitHub-Event": "workflow_run", "X-GitHub-Delivery": "aaaaaaaa-0000"}
            if header is not None:
                headers["X-Hub-Signature-256"] = header
            self.assertEqual(webhook.handle(CONFIG, raw, headers, ["R"])[0], 401, header)

    def test_the_signature_of_another_secret_or_of_another_body_does_not_pass(self):
        self.assertEqual(send(secret="x" * 40)[0], 401)
        raw = json.dumps(BODY).encode()
        signed_other = webhook.sign(SECRET, raw + b" ")
        self.assertEqual(send(signature=signed_other, raw=raw)[0], 401)

    def test_a_replay_is_answered_and_not_acted_on(self):
        first, second = send(), send()
        self.assertEqual((first[0], first[2]), (200, "R"))
        self.assertEqual((second[0], second[2], second[1].get("duplicate")), (202, None, True))
        self.assertEqual(send(delivery=None)[0], 400, "no delivery id")

    def test_a_giant_body_is_refused_before_the_signature_is_computed(self):
        raw = b"{" + b" " * webhook.MAX_BODY + b"}"
        with mock.patch.object(webhook, "verify", side_effect=AssertionError("verified a huge body")):
            self.assertEqual(webhook.handle(CONFIG, raw, {"X-Hub-Signature-256": "sha256=" + "0" * 64}, ["R"])[0], 413)

    def test_an_event_outside_the_closed_list_is_ignored_and_the_list_is_closed(self):
        self.assertEqual(send(event="issues")[:2], (202, {"ok": True, "ignored": True}))
        self.assertEqual(send(event="repository_dispatch", delivery="bbbbbbbb-0001")[0], 202)
        self.assertEqual(send(event="workflow_run", delivery="bbbbbbbb-0002")[0], 200)
        self.assertEqual(set(webhook.EVENTS), {"workflow_run", "workflow_job", "check_run", "push", "release", "check_suite", "ping"})

    def test_check_run_refreshes_the_repository_like_the_other_events_but_keeps_no_text(self):
        code, _answer, repo = send(event="check_run", delivery="cccccccc-0001", body={"repository": {"name": "R", "full_name": "JuanenRac/R"}, "check_run": {"name": "do not keep", "output": {"summary": "free text"}}})
        self.assertEqual((code, repo), (200, "R"))
        self.assertIsNone(webhook.parse_event("check_run", json.dumps(BODY).encode()), "only workflow_run and workflow_job leave a record")

    def test_a_repository_that_is_not_watched_or_another_owner_is_ignored(self):
        self.assertEqual(send(body={"repository": {"name": "Other", "full_name": "JuanenRac/Other"}})[:2], (202, {"ok": True, "ignored": True}))
        self.assertEqual(send(delivery="dddddddd-0001", body={"repository": {"name": "R", "full_name": "Stranger/R"}}, config={"webhook": {"enabled": True}, "github_owner": "JuanenRac"})[0], 202)

    def test_the_flood_of_one_repository_is_cut(self):
        config = {"webhook": {"enabled": True, "max_per_minute": 2}}
        codes = [send(config, delivery=f"eeeeeeee-{i:04d}")[1].get("throttled", False) for i in range(4)]
        self.assertEqual(codes, [False, False, True, True])


class Coverage(unittest.TestCase):
    def setUp(self):
        webhook.reset()
        patch = mock.patch.dict(os.environ, {webhook.SECRET_ENV: SECRET})
        patch.start()
        self.addCleanup(patch.stop)

    def test_off_waiting_live_and_quiet(self):
        self.assertEqual(webhook.coverage({"webhook": {"enabled": False}}, now=1000)["state"], "off")
        self.assertEqual(webhook.coverage(CONFIG, now=1000)["state"], "waiting")
        webhook.note_accepted(now=1000)
        live = webhook.coverage(CONFIG, now=1000 + 120)
        self.assertEqual((live["state"], live["last_age_seconds"], live["last_hour"], live["fallback"]), ("live", 120, 1, "poll"))
        quiet = webhook.coverage(CONFIG, now=1000 + 2 * 3600)
        self.assertEqual((quiet["state"], quiet["last_hour"]), ("quiet", 0))

    def test_the_window_is_the_one_of_the_savings_block_and_the_memory_is_bounded(self):
        config = {"webhook": {"enabled": True}, "savings": {"webhook_window_minutes": 5}}
        webhook.note_accepted(now=1000)
        self.assertEqual(webhook.coverage(config, now=1000 + 200)["state"], "live")
        self.assertEqual(webhook.coverage(config, now=1000 + 400)["state"], "quiet")
        for i in range(6000):
            webhook.note_accepted(now=2000 + i)
        self.assertLessEqual(len(webhook._accepted), 5000)

    def test_the_status_of_the_page_carries_it_and_never_the_secret(self):
        status = am.webhook_status(CONFIG)
        self.assertEqual(status["coverage"]["state"], "waiting")
        self.assertNotIn(SECRET, json.dumps(status))


if __name__ == "__main__":
    unittest.main()
