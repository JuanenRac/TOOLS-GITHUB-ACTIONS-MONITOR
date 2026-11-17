# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The incoming webhook and the secrets of the environment: a delivery captured and sent again with another delivery id, garbage that cannot use up the allowance of the real deliveries, the names a
secret may live under, the secrets of the other accounts that a process of an account must not receive, and that the processes take their secrets out of the environment when they start."""
import copy
import hashlib
import http.client
import json
import os
import subprocess
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
import _timing  # noqa: E402
from github_actions_monitor.accounts import accounts, accounts_supervisor as sup  # noqa: E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.security import envguard, localguard, webhook  # noqa: E402

SECRET = "s" * 40
CONFIG = {"webhook": {"enabled": True}}


def delivery(config=None, n=0, delivery_id=None, address=None, secret=SECRET, signature=None, event="workflow_run"):
    raw = json.dumps({"repository": {"name": "R", "full_name": "JuanenRac/R"}, "n": n}).encode()
    headers = {"X-GitHub-Event": event, "X-Hub-Signature-256": signature or webhook.sign(secret, raw), "X-GitHub-Delivery": delivery_id or f"{n:08d}-aaaa-bbbb"}
    return webhook.handle(config or CONFIG, raw, headers, ["R"], address)


class WithTheSecret(unittest.TestCase):
    def setUp(self):
        webhook.reset()
        localguard.reset_limits()
        patch = mock.patch.dict(os.environ, {webhook.SECRET_ENV: SECRET})
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(localguard.reset_limits)


class ACapturedDeliveryCannotBeRenewedByTheHeader(WithTheSecret):
    def test_the_same_signed_body_with_another_delivery_id_is_a_duplicate(self):
        self.assertEqual(delivery(n=1, delivery_id="aaaaaaaa-0001")[0], 200)
        answers = [delivery(n=1, delivery_id=f"bbbbbbbb-{i:04d}") for i in range(40)]
        self.assertEqual({(code, body.get("duplicate")) for code, body, _ in answers}, {(202, True)})
        self.assertEqual(delivery(n=2, delivery_id="aaaaaaaa-0001")[1].get("duplicate"), True, "the same id with another body is a duplicate too")
        self.assertEqual(delivery(n=3, delivery_id="aaaaaaaa-0003")[0], 200, "a new body with a new id is a new delivery")

    def test_the_memory_is_keyed_by_what_is_signed(self):
        raw = b'{"repository": {"name": "R"}}'
        webhook.replay("body:" + hashlib.sha256(raw).hexdigest(), 60, now=100)
        self.assertTrue(webhook.replay("body:" + hashlib.sha256(raw).hexdigest(), 60, now=101))


class GarbageDoesNotUseUpTheAllowanceOfTheRealDeliveries(WithTheSecret):
    def test_119_bad_signatures_from_one_address_leave_room_for_the_good_one(self):
        wrong = "sha256=" + "0" * 64
        codes = [delivery(n=i, address="tunnel", signature=wrong)[0] for i in range(119)]
        self.assertEqual(set(codes), {401})
        self.assertEqual(delivery(n=1000, address="tunnel")[0], 200)

    def test_bad_signatures_are_cut_after_the_limit_and_never_cut_the_good_ones(self):
        config = {"webhook": {"enabled": True, "max_bad_per_minute": 5}}
        wrong = "sha256=" + "0" * 64
        codes = [delivery(config, n=i, address="tunnel", signature=wrong)[0] for i in range(8)]
        self.assertEqual(codes, [401] * 5 + [429] * 3)
        self.assertEqual(delivery(config, n=1001, address="tunnel")[0], 200)
        self.assertEqual(delivery(config, n=1002, address="another")[0], 200)

    def test_the_good_ones_have_an_allowance_of_their_own(self):
        codes = [delivery(n=i, address="tunnel", event="ping")[0] for i in range(125)]
        self.assertEqual(codes[:webhook.MAX_VERIFIED_PER_MINUTE], [200] * webhook.MAX_VERIFIED_PER_MINUTE)
        self.assertEqual(codes[webhook.MAX_VERIFIED_PER_MINUTE:], [429] * 5)

    def test_the_address_is_the_one_behind_a_declared_trusted_proxy_only(self):
        headers = {"X-Forwarded-For": "203.0.113.9"}
        with mock.patch.dict(localguard.STATE, {"trusted_proxy": False}):
            self.assertEqual(localguard.client_key(("127.0.0.1", 5000), headers), "127.0.0.1")
        with mock.patch.dict(localguard.STATE, {"trusted_proxy": True, "proxy_nets": ()}):
            self.assertEqual(localguard.client_key(("127.0.0.1", 5000), headers), "fwd:203.0.113.9")

    def test_the_real_server_answers_the_good_delivery_after_119_garbage_ones_in_the_local_mode_too(self):
        config = {**copy.deepcopy(am.DEFAULTS), "webhook": {"enabled": True}}
        for patcher in (mock.patch.object(am, "LIVE_CONFIG", config), mock.patch.dict(am.STATE, {"data": {"repos": ["R"]}})):
            patcher.start()
            self.addCleanup(patcher.stop)
        server = am.QuietServer(("127.0.0.1", 0), am.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def post(n, signature=None):
            raw = json.dumps({"zen": n}).encode()
            connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=_timing.limit(15))
            try:
                connection.request("POST", "/api/webhook", raw, {"Host": f"127.0.0.1:{server.server_address[1]}", "X-GitHub-Event": "ping", "X-GitHub-Delivery": f"{n:08d}-aaaa",
                                                                 "X-Hub-Signature-256": signature or webhook.sign(SECRET, raw)})
                return connection.getresponse().status
            finally:
                connection.close()
        self.assertEqual({post(i, "sha256=" + "0" * 64) for i in range(119)}, {401})
        self.assertEqual(post(5000), 200)


class TheNameOfASecretIsNeverAVariableOfTheSystem(unittest.TestCase):
    def setUp(self):
        self.addCleanup(webhook._frozen_name.__setitem__, 0, None)
        webhook._frozen_name[0] = None

    def test_the_webhook_falls_back_to_its_default_name(self):
        for name in ("PATH", "GH_TOKEN", "GITHUB_TOKEN", "HOME", "USERPROFILE", "MONITOR_ACCESS_TOKEN", "MONITOR_SUPERVISOR_KEY", "PYTHONPATH"):
            self.assertEqual(webhook.secret_env_name({"webhook": {"secret_env": name}}), webhook.SECRET_ENV, name)
        self.assertEqual(webhook.secret_env_name({"webhook": {"secret_env": "ALPHA_HOOK_SECRET"}}), "ALPHA_HOOK_SECRET")
        self.assertEqual(webhook.secret_env_name({"webhook": {"secret_env": "MONITOR_WEBHOOK_SECRET"}}), "MONITOR_WEBHOOK_SECRET")

    def test_a_forbidden_name_does_not_make_a_variable_the_secret(self):
        with mock.patch.dict(os.environ, {"PATH": os.environ.get("PATH", "x") + "p" * 60}):
            self.assertFalse(webhook.active({"webhook": {"enabled": True, "secret_env": "PATH"}}))

    def test_the_settings_page_refuses_them_for_the_webhook_and_for_the_access_token(self):
        for key, bad, good in (("webhook.secret_env", ("PATH", "GH_TOKEN", "MONITOR_ACCESS_TOKEN"), ("ALPHA_HOOK_SECRET", "MONITOR_WEBHOOK_SECRET")),
                               ("listen.token_env", ("PATH", "GITHUB_TOKEN", "MONITOR_WEBHOOK_SECRET", "MONITOR_SUPERVISOR_KEY"), ("MY_ACCESS", "MONITOR_ACCESS_TOKEN"))):
            pattern = settings_api.FIELDS[key][3]
            for name in bad:
                self.assertFalse(pattern.match(name), (key, name))
            for name in good:
                self.assertTrue(pattern.match(name), (key, name))

    def test_the_access_token_is_never_read_from_a_variable_of_the_system(self):
        self.assertEqual(localguard.settings_from({"listen": {"token_env": "PATH"}})["token_env"], "MONITOR_ACCESS_TOKEN")
        self.assertEqual(localguard.settings_from({"listen": {"token_env": "MY_ACCESS"}})["token_env"], "MY_ACCESS")

    def test_the_name_is_read_once_when_the_process_starts(self):
        with mock.patch.dict(os.environ, {"FIRST_HOOK": SECRET, "SECOND_HOOK": SECRET}):
            self.addCleanup(envguard.HELD.pop, "FIRST_HOOK", None)
            self.addCleanup(envguard.NAMES.discard, "FIRST_HOOK")
            webhook.freeze_secret_name({"webhook": {"secret_env": "FIRST_HOOK"}})
            self.assertEqual(webhook.secret_env_name({"webhook": {"secret_env": "SECOND_HOOK"}}), "FIRST_HOOK", "a change of the setting waits for the next start")
            self.assertNotIn("FIRST_HOOK", os.environ)


class TheProcessOfAnAccountOnlyHoldsItsOwnSecret(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.dict(os.environ, {"MONITOR_ACCOUNTS_DIR": str(Path(self.tmp.name) / "accounts")})
        patch.start()
        self.addCleanup(patch.stop)
        for name in ("alpha", "beta"):
            accounts.create_account(name, name + "-owner")

    def write(self, account_id, secret_env):
        path = accounts.config_path(account_id)
        path.write_text(json.dumps({"webhook": {"secret_env": secret_env}} if secret_env else {}), encoding="utf-8")

    def environment_of(self, account_id, main_name=None):
        env = {"ALPHA_HOOK_SECRET": "a" * 40, "BETA_HOOK_SECRET": "b" * 40, "ROOT_HOOK_SECRET": "r" * 40, "OTHER": "kept"}
        with mock.patch.dict(os.environ, env), mock.patch.object(envguard, "HELD", {}), \
                mock.patch("github_actions_monitor.app.toolconfig.raw_config", return_value={"webhook": {"secret_env": main_name}} if main_name else {}), \
                mock.patch.object(sup.subprocess, "Popen") as popen:
            child = sup.Child(account_id, 18999, command=["x"], key="k")
            child.start()
            return popen.call_args.kwargs["env"]

    def test_one_secret_for_each_account(self):
        self.write("alpha", "ALPHA_HOOK_SECRET")
        self.write("beta", "BETA_HOOK_SECRET")
        alpha, beta = self.environment_of("alpha"), self.environment_of("beta")
        self.assertEqual((alpha.get("ALPHA_HOOK_SECRET") is not None, "BETA_HOOK_SECRET" in alpha, alpha["OTHER"]), (True, False, "kept"))
        self.assertEqual((beta.get("BETA_HOOK_SECRET") is not None, "ALPHA_HOOK_SECRET" in beta), (True, False))

    def test_the_secret_of_the_main_configuration_does_not_reach_an_account_that_names_another(self):
        self.write("alpha", None)
        self.write("beta", "BETA_HOOK_SECRET")
        env = self.environment_of("alpha", main_name="ROOT_HOOK_SECRET")
        self.assertEqual([n for n in ("ROOT_HOOK_SECRET", "BETA_HOOK_SECRET") if n in env], [])

    def test_accounts_that_share_the_default_name_keep_it(self):
        self.write("alpha", None)
        self.write("beta", None)
        with mock.patch.dict(os.environ, {webhook.SECRET_ENV: SECRET}), mock.patch.object(envguard, "HELD", {}), mock.patch.object(sup.subprocess, "Popen") as popen, \
                mock.patch("github_actions_monitor.app.toolconfig.raw_config", return_value={}):
            sup.Child("alpha", 18998, command=["x"], key="k").start()
            self.assertEqual(popen.call_args.kwargs["env"][webhook.SECRET_ENV], SECRET)

    def test_the_names_of_the_installation_are_all_known_to_the_supervisor(self):
        self.write("alpha", "ALPHA_HOOK_SECRET")
        self.write("beta", "BETA_HOOK_SECRET")
        with mock.patch("github_actions_monitor.app.toolconfig.raw_config", return_value={"webhook": {"secret_env": "ROOT_HOOK_SECRET"}}):
            self.assertEqual(sup.webhook_names(), ["ALPHA_HOOK_SECRET", "BETA_HOOK_SECRET", "ROOT_HOOK_SECRET"])
            self.assertEqual(sup.webhook_names("alpha"), ["ALPHA_HOOK_SECRET"])
            self.assertEqual(sup.webhook_names("alpha", others=True), ["BETA_HOOK_SECRET", "ROOT_HOOK_SECRET"])


class TheProcessesTakeTheirSecretsOutOfTheEnvironmentWhenTheyStart(unittest.TestCase):
    def test_main_leaves_no_secret_in_the_environment_of_the_programs_it_starts(self):
        """Starts the real main() up to the help text, with the three secrets in the environment, and asks what a program started afterwards would inherit."""
        code = ("import sys, os; sys.path.insert(0, %r); sys.argv = ['monitor', '--help']\n"
                "from github_actions_monitor.app import actions_monitor as am\n"
                "from github_actions_monitor.security import envguard\n"
                "try:\n    am.main()\nexcept SystemExit:\n    pass\n"
                "print('LEFT=' + ','.join(sorted(n for n in ('MONITOR_ACCESS_TOKEN', 'MONITOR_SUPERVISOR_KEY', 'MONITOR_WEBHOOK_SECRET', 'MY_HOOK') if n in os.environ)))\n"
                "print('HELD=' + ','.join(sorted(envguard.HELD)))\n") % str(HERE / "src")
        env = {**os.environ, "MONITOR_ACCESS_TOKEN": "t" * 30, "MONITOR_SUPERVISOR_KEY": "k" * 30, "MONITOR_WEBHOOK_SECRET": SECRET, "PYTHONIOENCODING": "utf-8"}
        with tempfile.TemporaryDirectory() as folder:
            done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=_timing.limit(120), cwd=folder, env=env, **({"creationflags": 0x08000000} if os.name == "nt" else {}))
        self.assertIn("LEFT=\n", done.stdout + "\n", done.stderr[-500:])
        self.assertIn("MONITOR_WEBHOOK_SECRET", done.stdout.split("HELD=")[-1])

    def test_the_supervisor_holds_the_secrets_of_the_whole_installation_before_it_serves(self):
        with tempfile.TemporaryDirectory() as folder:
            env = {"MONITOR_ACCOUNTS_DIR": str(Path(folder) / "accounts"), "ALPHA_HOOK_SECRET": "a" * 40, "ROOT_HOOK_SECRET": "r" * 40}
            with mock.patch.dict(os.environ, env):
                accounts.create_account("alpha", "alpha-owner")
                accounts.config_path("alpha").write_text(json.dumps({"webhook": {"secret_env": "ALPHA_HOOK_SECRET"}}), encoding="utf-8")
                held, names = {}, set(envguard.NAMES)
                self.addCleanup(lambda: (envguard.NAMES.clear(), envguard.NAMES.update(names)))
                with mock.patch.object(envguard, "HELD", held), mock.patch.object(sup, "serve", side_effect=OSError("busy")), \
                        mock.patch("github_actions_monitor.app.toolconfig.raw_config", return_value={"webhook": {"secret_env": "ROOT_HOOK_SECRET"}}):
                    self.assertEqual(am.supervisor_main(["--port", "18950"]), 1)
                    left = [n for n in ("ALPHA_HOOK_SECRET", "ROOT_HOOK_SECRET") if n in os.environ]
                self.assertEqual(left, [])
                self.assertEqual(sorted(held), ["ALPHA_HOOK_SECRET", "ROOT_HOOK_SECRET"])


class TheLiveEventIsAClosedList(unittest.TestCase):
    def test_nothing_but_the_closed_fields_reaches_the_live_list_and_the_stream(self):
        record = {"event": "workflow_job", "repo": "R", "run_id": 1, "status": "completed", "conclusion": "failure", "workflow": "CI", "job": "build", "queue": 3, "seconds": 9, "sha": "abc1234", "url": None,
                  "steps": {"free text of a third party": 4}, "title": "free text", "actor": "somebody"}
        with mock.patch.dict(am.RUN_CACHE, {}, clear=True), mock.patch.object(am, "LIVE_EVENTS", []), mock.patch.object(am, "LIVE_TOTAL", [0]), mock.patch.object(am, "HOT_FORCED", set()):
            am.apply_live_event(record, {"runs_per_repo": 20})
            kept = dict(am.LIVE_EVENTS[0])
            self.assertEqual(set(kept) - {"at"}, {k for k in record if k in webhook.LIVE_FIELDS})
            frames = list(webhook.sse_frames({"live": {"sse": {"enabled": True, "max_seconds": 60}}}, lambda: (1, [kept]), stop=iter([False, False, True, True]).__next__, sleep=lambda s: None, since=0))
        text = "".join(frames)
        self.assertNotIn("free text", text)
        self.assertIn('"conclusion": "failure"', text)


if __name__ == "__main__":
    unittest.main()
