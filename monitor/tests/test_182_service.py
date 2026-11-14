# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The monitor as a service: the first start from the environment, the access token of the service, the deep health command, and the command line against a monitor on another computer."""
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import service  # noqa: E402
from github_actions_monitor.accounts import accounts  # noqa: E402
from github_actions_monitor.cli import healthcheck, monitor_cli  # noqa: E402


class Folder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.env = {"MONITOR_CONFIG": str(self.dir / "config" / "actions_monitor.json"), "MONITOR_ACCOUNTS_DIR": str(self.dir / "accounts"), "MONITOR_STATE_DIR": str(self.dir / "state")}
        patcher = mock.patch.dict(os.environ, self.env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def lines(self, env=None):
        out = []
        code = service.prepare(env if env is not None else os.environ, out.append)
        return code, out


class FirstStart(Folder):
    def test_the_first_start_makes_the_configuration_the_first_account_and_says_so(self):
        os.environ.update({"MONITOR_GITHUB_OWNER": "my-org", "MONITOR_LANG": "es"})
        code, out = self.lines()
        self.assertEqual(code, 0)
        config = json.loads(Path(self.env["MONITOR_CONFIG"]).read_text(encoding="utf-8"))
        self.assertEqual((config["open_browser"], config["language"], config["retention"]["mode"]), (False, "es", "archive"))
        self.assertNotIn("listen", config, "the conservative default: nothing listens beyond this computer unless the environment says so")
        self.assertEqual(accounts.list_accounts(), ["default"])
        self.assertEqual(json.loads(accounts.config_path("default").read_text(encoding="utf-8"))["github_owner"], "my-org")
        self.assertEqual(os.environ["MONITOR_SERVICE"], "1")
        self.assertEqual(len(out), 2)

    def test_what_you_edited_is_never_overwritten_and_a_second_start_is_silent(self):
        self.lines()
        path = Path(self.env["MONITOR_CONFIG"])
        data = json.loads(path.read_text(encoding="utf-8"))
        data["refresh_seconds"] = 77
        path.write_text(json.dumps(data), encoding="utf-8")
        code, out = self.lines()
        self.assertEqual((code, out), (0, []))
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["refresh_seconds"], 77)

    def test_the_variables_of_the_environment_are_written_into_the_listen_block_at_every_start(self):
        os.environ.update({"MONITOR_LISTEN_NETWORK": "1", "MONITOR_LISTEN_HOST": "0.0.0.0", "MONITOR_PROXY_PUBLIC_HOST": "monitor.example.org", "MONITOR_SECURE_COOKIE": "true",
                           "MONITOR_ALLOWED_HOSTS": "a.lan, b.lan", "MONITOR_LOCAL_PORT": "8766", "MONITOR_TEAM_MODE": "1"})
        self.lines()
        config = json.loads(Path(self.env["MONITOR_CONFIG"]).read_text(encoding="utf-8"))
        self.assertEqual(config["listen"], {"network": True, "host": "0.0.0.0", "proxy_public_host": "monitor.example.org", "secure_cookie": True, "allowed_hosts": ["a.lan", "b.lan"], "local_port": 8766})
        self.assertEqual(config["auth"], {"enabled": True})
        os.environ["MONITOR_LISTEN_NETWORK"] = "0"
        code, out = self.lines()
        self.assertEqual(json.loads(Path(self.env["MONITOR_CONFIG"]).read_text(encoding="utf-8"))["listen"]["network"], False, "the environment stays the authority for the keys it names")
        self.assertTrue(any("actions_monitor.json" in line for line in out))

    def test_a_variable_that_cannot_be_read_is_ignored_with_a_notice_and_changes_nothing(self):
        os.environ.update({"MONITOR_LISTEN_NETWORK": "maybe", "MONITOR_LOCAL_PORT": "port"})
        code, out = self.lines()
        self.assertEqual(code, 0)
        self.assertTrue(any("MONITOR_LISTEN_NETWORK" in line for line in out) and any("MONITOR_LOCAL_PORT" in line for line in out))
        self.assertNotIn("listen", json.loads(Path(self.env["MONITOR_CONFIG"]).read_text(encoding="utf-8")))

    def test_a_configuration_that_is_not_json_is_the_owners_to_fix_and_is_never_replaced(self):
        path = Path(self.env["MONITOR_CONFIG"])
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")
        code, out = self.lines()
        self.assertEqual(code, 78)
        self.assertEqual(path.read_text(encoding="utf-8"), "{not json")

    def test_several_accounts_from_one_variable_and_nothing_made_when_there_already_are(self):
        os.environ["MONITOR_ACCOUNTS"] = "Personal:me, work:my-org, bad id:x"
        self.assertEqual(service.parse_accounts(), [("personal", "me"), ("work", "my-org")])
        self.lines()
        self.assertEqual(accounts.list_accounts(), ["personal", "work"])
        os.environ["MONITOR_ACCOUNTS"] = "other:z"
        self.assertEqual(service.prepare_accounts(), [])
        self.assertEqual(accounts.list_accounts(), ["personal", "work"])

    def test_without_the_configuration_variable_the_service_leaves_the_files_of_the_product_alone(self):
        env = {k: v for k, v in os.environ.items() if k != "MONITOR_CONFIG"}
        self.assertEqual(service.prepare_config(env), (None, False, False, []))


class AccessToken(Folder):
    CONFIG = {"listen": {"network": True}}

    def test_nothing_is_made_without_the_network_mode(self):
        env = dict(os.environ)
        self.assertEqual(service.ensure_access_token({}, env), "")
        self.assertFalse(service.token_file(env).exists())

    def test_a_token_from_the_environment_is_used_as_it_is(self):
        env = dict(os.environ, MONITOR_ACCESS_TOKEN="x" * 20)
        self.assertEqual(service.ensure_access_token(self.CONFIG, env), "env")
        self.assertFalse(service.token_file(env).exists())

    def test_a_token_from_a_file_of_the_platform(self):
        secret = self.dir / "token"
        secret.write_text("y" * 24 + "\n", encoding="utf-8")
        env = dict(os.environ, MONITOR_ACCESS_TOKEN_FILE=str(secret))
        self.assertEqual(service.ensure_access_token(self.CONFIG, env), "file")
        self.assertEqual(env["MONITOR_ACCESS_TOKEN"], "y" * 24)

    def test_otherwise_one_is_made_once_kept_private_and_never_printed(self):
        env = dict(os.environ)
        self.assertEqual(service.ensure_access_token(self.CONFIG, env), "created")
        made = env["MONITOR_ACCESS_TOKEN"]
        self.assertGreaterEqual(len(made), 16)
        path = service.token_file(env)
        self.assertEqual(path.read_text(encoding="utf-8").strip(), made)
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        again = dict(os.environ)
        self.assertEqual(service.ensure_access_token(self.CONFIG, again), "file")
        self.assertEqual(again["MONITOR_ACCESS_TOKEN"], made, "the same volume asks for the same token at every start")
        code, out = self.lines(dict(os.environ, MONITOR_LISTEN_NETWORK="1"))
        self.assertNotIn(made, "\n".join(out))

    def test_the_health_command_reads_the_same_token_the_service_made(self):
        env = dict(os.environ)
        service.ensure_access_token(self.CONFIG, env)
        self.assertEqual(healthcheck.token({"MONITOR_STATE_DIR": env["MONITOR_STATE_DIR"]}), env["MONITOR_ACCESS_TOKEN"])
        self.assertEqual(healthcheck.token({}), "")
        self.assertEqual(healthcheck.token({"MONITOR_TOKEN": "z" * 20}), "z" * 20)


class HealthCommand(unittest.TestCase):
    def test_exit_codes_and_lines(self):
        ok = healthcheck.judge(200, {"ok": True, "version": "1.8.2", "credential": {"state": "ok"}})
        self.assertEqual(ok[0], 0)
        blind = healthcheck.judge(200, {"ok": True, "version": "1.8.2", "account": "alpha", "credential": {"state": "blind"}})
        self.assertEqual(blind[0], 0, "a lost login is not a failure of the service")
        self.assertIn("alpha", blind[1])
        self.assertEqual(healthcheck.judge(503, {"ok": False, "cycle": {"stuck": True, "running_seconds": 700}})[0], 1)
        self.assertEqual(healthcheck.judge(503, {"ok": False, "cycle": {"dead": True}})[0], 1)
        self.assertEqual(healthcheck.judge(0, None)[0], 2)
        self.assertEqual(healthcheck.judge(401, None)[0], 3)
        self.assertEqual(healthcheck.judge(200, None)[0], 1)

    def test_the_supervisor_document(self):
        good = {"ok": True, "supervisor": True, "accounts": 2, "states": {"a": "ok", "b": "blind"}, "blind": ["b"], "problems": [], "stale": False}
        code, text = healthcheck.judge(200, good)
        self.assertEqual(code, 0)
        self.assertIn("b", text)
        bad = dict(good, ok=False, problems=[{"id": "a", "state": "stuck"}])
        self.assertEqual(healthcheck.judge(503, bad)[0], 1)
        self.assertEqual(healthcheck.judge(503, dict(bad, stale=True, problems=[]))[0], 1)

    def test_nothing_listening_is_exit_code_2(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = healthcheck.main(["--url", "http://127.0.0.1:9", "--timeout", "1"])
        self.assertEqual(code, 2)

    def test_the_text_is_the_catalogue_not_a_literal(self):
        self.assertNotEqual(healthcheck.judge(0, None)[1], "healthcheck.unreachable")


class RemoteCommandLine(unittest.TestCase):
    def setUp(self):
        monitor_cli.CLIENT.update({"session": "", "ca": ""})
        self.addCleanup(monitor_cli.CLIENT.update, {"session": "", "ca": ""})

    def run_cli(self, argv, env=None, **patches):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env or {}), redirect_stdout(out), redirect_stderr(err):
            code = monitor_cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_the_session_of_the_team_mode_travels_as_a_bearer_token_beside_the_access_token(self):
        monitor_cli.CLIENT["session"] = "msn_abc"
        headers = monitor_cli.request_headers("T" * 20)
        self.assertEqual((headers["Authorization"], headers["X-Monitor-Access"]), ("Bearer msn_abc", "T" * 20))
        monitor_cli.CLIENT["session"] = ""
        self.assertNotIn("Authorization", monitor_cli.request_headers(""))

    def test_sign_in_keeps_the_token_and_a_refusal_is_exit_code_3(self):
        with mock.patch.object(monitor_cli, "post_json", return_value=(200, {"ok": True, "token": "msn_zzz"})) as post:
            monitor_cli.sign_in("https://monitor.example.org", "ann", "pw", 5, "")
        self.assertEqual(monitor_cli.CLIENT["session"], "msn_zzz")
        self.assertEqual(post.call_args[0][2], {"username": "ann", "password": "pw", "client": "api"})
        with mock.patch.object(monitor_cli, "post_json", return_value=(401, {"code": "invalid_credentials"})):
            with self.assertRaises(monitor_cli.CliError) as caught:
                monitor_cli.sign_in("https://x", "ann", "bad", 5, "")
        self.assertEqual(caught.exception.code, monitor_cli.EXIT_AUTH)

    def test_user_and_password_file_sign_in_before_the_command(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        secret = Path(folder.name) / "pw"
        secret.write_text("hunter2-hunter2\n", encoding="utf-8")
        signed = []
        with mock.patch.object(monitor_cli, "sign_in", side_effect=lambda *a: signed.append(a)), mock.patch.object(monitor_cli, "fetch", side_effect=monitor_cli.CliError(2, "down")):
            code, _, _ = self.run_cli(["status", "--url", "https://monitor.example.org", "--user", "ann", "--password-file", str(secret)])
        self.assertEqual(code, 2)
        self.assertEqual(signed[0][1:3], ("ann", "hunter2-hunter2"))

    def test_a_user_without_a_password_is_a_wrong_use(self):
        code, _, err = self.run_cli(["status", "--user", "ann"], env={"MONITOR_PASSWORD": "", "MONITOR_PASSWORD_FILE": ""})
        self.assertEqual(code, 1)
        self.assertTrue(err)

    def test_a_certificate_authority_that_does_not_exist_is_a_wrong_use(self):
        code, _, _ = self.run_cli(["status", "--ca-file", str(HERE / "nope.pem")])
        self.assertEqual(code, 1)

    def test_the_monitor_of_another_computer_is_named_by_the_url_or_the_variable(self):
        self.assertEqual(monitor_cli.base_url("https://monitor.example.org:8443/x?y"), "https://monitor.example.org:8443")
        self.assertEqual(monitor_cli.base_url(None, env={"MONITOR_URL": "monitor.lan:8765"}), "http://monitor.lan:8765")

    def test_credential_replace_reads_the_token_from_a_file_and_never_from_a_flag_and_never_prints_it(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        token = "ghp_" + "Q" * 36
        secret = Path(folder.name) / "t"
        secret.write_text(token + "\n", encoding="utf-8")
        sent = []
        with mock.patch.object(monitor_cli, "fetch", return_value={"ok": True, "supervisor": True}), \
                mock.patch.object(monitor_cli, "post_json", side_effect=lambda base, path, payload, *a: sent.append((path, payload)) or (200, {"ok": True, "status": "saved", "token": token})):
            code, out, err = self.run_cli(["credential", "replace", "--account", "alpha", "--new-token-file", str(secret), "--url", "http://127.0.0.1:8765", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(sent, [("/api/accounts/alpha/credential", {"action": "replace", "token": token})])
        self.assertNotIn(token, out + err, "not even an answer that carried it is repeated")

    def test_credential_needs_the_file_the_account_and_a_known_action(self):
        self.assertEqual(self.run_cli(["credential", "replace", "--account", "a"])[0], 1)
        self.assertEqual(self.run_cli(["credential"])[0], 1)
        with mock.patch.object(monitor_cli, "fetch", return_value={"ok": True, "supervisor": True}):
            self.assertEqual(self.run_cli(["credential", "reload"])[0], 1, "with several accounts the account must be named")

    def test_credential_exit_codes(self):
        with mock.patch.object(monitor_cli, "fetch", return_value={"ok": True, "supervisor": True}):
            for status, answer, expected in ((200, {"ok": True, "status": "reloaded"}, 0), (422, {"ok": False, "status": "rejected"}, 4), (403, {"ok": False, "status": "local_only"}, 3), (404, {}, 4)):
                with mock.patch.object(monitor_cli, "post_json", return_value=(status, answer)):
                    self.assertEqual(self.run_cli(["credential", "reload", "--account", "alpha"])[0], expected, status)

    def test_health_deep_maps_the_exit_codes(self):
        base = {"ok": True, "version": "1", "uptime_seconds": 1}
        with mock.patch.object(monitor_cli, "deep_health", return_value=(monitor_cli.EXIT_DEGRADED, "stuck", {"ok": False})):
            code, out, _ = self.run_cli(["health", "--deep", "--json"])
        self.assertEqual(code, monitor_cli.EXIT_DEGRADED)
        with mock.patch.object(monitor_cli, "deep_health", return_value=(monitor_cli.EXIT_DOWN, "down", None)):
            self.assertEqual(self.run_cli(["health", "--deep"])[0], monitor_cli.EXIT_DOWN)

    def test_health_deep_of_a_supervisor_is_all_it_asks(self):
        document = {"ok": True, "supervisor": True, "accounts": 2, "states": {"a": "ok", "b": "ok"}}
        with mock.patch.object(monitor_cli, "deep_health", return_value=(monitor_cli.EXIT_OK, "Healthy", document)), mock.patch.object(monitor_cli, "fetch", side_effect=AssertionError("nothing else is read")):
            code, out, _ = self.run_cli(["health", "--deep"])
        self.assertEqual(code, monitor_cli.EXIT_OK)
        self.assertIn("Healthy", out)

    def test_the_alerts_command_knows_the_system_sentinel_and_the_critical_level(self):
        parser = monitor_cli.build_parser()
        args = parser.parse_args(["alerts", "--sentinel", "system", "--level", "critical", "--fail-on", "critical"])
        self.assertEqual((args.sentinel, args.level, args.fail_on), ("system", "critical", "critical"))
        payload = {"alerts": [{"level": "critical", "sentinel": "system", "code": "system.credential_blind", "title": "t"}]}
        with mock.patch.object(monitor_cli, "fetch", return_value=payload):
            code, _, _ = self.run_cli(["alerts", "--fail-on", "critical"])
        self.assertEqual(code, monitor_cli.EXIT_ALERTS)

    def test_accounts_says_which_are_blind_and_where_it_listens(self):
        payload = {"accounts": [{"id": "alpha", "state": "blind"}, {"id": "beta", "state": "ok"}], "listening": "proxy"}
        with mock.patch.object(monitor_cli, "fetch", return_value=payload):
            code, out, _ = self.run_cli(["accounts"])
        self.assertEqual(code, monitor_cli.EXIT_AUTH)
        self.assertIn("alpha", out)


if __name__ == "__main__":
    unittest.main()
