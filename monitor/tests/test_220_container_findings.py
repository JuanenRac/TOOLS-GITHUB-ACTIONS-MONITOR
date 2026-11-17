# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""What the checks in real containers showed: a variable that declares a proxy and is left empty switches the key off, the webhook rate limit counts the visitor and not the proxy, a request
without any token is not counted as a wrong guess, the shallow health of the supervisor has the keys of the contract and the guide gives the login file to the user of the container."""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))
sys.path.insert(0, str(HERE / "tools"))

import _testenv  # noqa: F401,E402
import check_api_contract  # noqa: E402
from github_actions_monitor import service  # noqa: E402
from github_actions_monitor.security import localguard  # noqa: E402

ROOT = HERE.parent
SOURCE = HERE / "src" / "github_actions_monitor"


class EmptyVariable(unittest.TestCase):
    def test_an_empty_proxy_variable_switches_its_key_off(self):
        env = {"MONITOR_TRUSTED_PROXY": "", "MONITOR_TRUSTED_PROXIES": " ", "MONITOR_SECURE_COOKIE": "", "MONITOR_PROXY_PUBLIC_HOST": "", "MONITOR_ALLOWED_HOSTS": ""}
        changes, bad = service.environment_changes(env)
        self.assertEqual(bad, [])
        self.assertEqual(changes["listen"], {"trusted_proxy": False, "trusted_proxies": [], "secure_cookie": False, "proxy_public_host": "", "allowed_hosts": []})

    def test_an_empty_variable_of_another_key_changes_nothing_and_a_missing_one_neither(self):
        changes, _ = service.environment_changes({"MONITOR_TEAM_MODE": "", "MONITOR_LISTEN_NETWORK": "", "MONITOR_LOCAL_PORT": ""})
        self.assertEqual(changes, {})
        self.assertEqual(service.environment_changes({})[0], {})

    def test_the_file_of_an_earlier_start_is_corrected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "actions_monitor.json"
            path.write_text(json.dumps({"listen": {"trusted_proxy": True, "trusted_proxies": ["172.29.77.0/24"], "host": "0.0.0.0"}}), encoding="utf-8")
            service.prepare_config({"MONITOR_CONFIG": str(path), "MONITOR_TRUSTED_PROXY": "", "MONITOR_TRUSTED_PROXIES": ""})
            listen = json.loads(path.read_text(encoding="utf-8"))["listen"]
            self.assertIs(listen["trusted_proxy"], False)
            self.assertEqual(listen["trusted_proxies"], [])
            self.assertEqual(listen["host"], "0.0.0.0")


class WebhookRate(unittest.TestCase):
    def test_the_limit_is_counted_against_the_visitor_behind_a_trusted_proxy(self):
        for name in ("accounts/accounts_supervisor.py", "app/actions_monitor.py"):
            text = (SOURCE / name).read_text(encoding="utf-8")
            self.assertIn("localguard.client_key(self.client_address, self.headers)", text, name)      # the limits of the webhook (counted inside webhook.handle) are told who the visitor is by the key behind a trusted proxy
            self.assertNotIn('over_rate("webhook", str(self.client_address[0])', text, name)

    def test_two_visitors_behind_the_proxy_have_two_budgets(self):
        saved = dict(localguard.STATE)
        try:
            localguard.reset_limits()
            localguard.STATE.update({"trusted_proxy": True, "proxy_nets": []})
            first = localguard.client_key(("127.0.0.1", 1), {"X-Forwarded-For": "203.0.113.5"})
            second = localguard.client_key(("127.0.0.1", 2), {"X-Forwarded-For": "198.51.100.7"})
            self.assertNotEqual(first, second)
            for _ in range(120):
                self.assertFalse(localguard.over_rate("webhook", first, 120))
            self.assertTrue(localguard.over_rate("webhook", first, 120))
            self.assertFalse(localguard.over_rate("webhook", second, 120))
        finally:
            localguard.STATE.clear()
            localguard.STATE.update(saved)
            localguard.reset_limits()


class NoTokenIsNoGuess(unittest.TestCase):
    def test_both_gates_count_a_failure_only_when_something_was_presented(self):
        for name in ("accounts/accounts_supervisor.py", "app/actions_monitor.py"):
            text = (SOURCE / name).read_text(encoding="utf-8")
            self.assertIn("if localguard.presented(self.headers) or query_token:", text, name)


class Contract(unittest.TestCase):
    def test_the_supervisor_health_has_every_key_of_the_contract(self):
        from github_actions_monitor.accounts import accounts_supervisor as sup
        contract = json.loads((HERE / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8"))
        row = next(r for r in contract["endpoints"] if r["path"] == "/api/health")
        holder = type("Holder", (), {"children": {}, "base": None, "started_at": 0.0, "child": lambda self, _id: None})()
        from unittest import mock
        with mock.patch.object(sup.accounts, "default_account", return_value="default"):
            document = sup.Supervisor.shallow_health(holder)
        self.assertEqual(check_api_contract.keys_problems("GET /api/health", document, row["complete"]), [])
        self.assertIs(document["ok"], True)
        self.assertIs(document["supervisor"], True)

    def test_a_local_only_route_refused_from_the_network_is_the_right_answer(self):
        contract = {"endpoints": [{"path": "/api/quota-pool/status", "local_only": True, "complete": {"total": "any"}, "lite": "same"}], "errors": []}
        self.assertEqual(check_api_contract.check(lambda m, p, host=None, body=None: (403, {"error": "local_only"}), "complete", contract), [])
        self.assertTrue(check_api_contract.check(lambda m, p, host=None, body=None: (500, None), "complete", contract))
        stored = json.loads((HERE / "docs" / "schemas" / "api_contract.json").read_text(encoding="utf-8"))
        self.assertTrue(next(r for r in stored["endpoints"] if r["path"] == "/api/quota-pool/status").get("local_only"))


class Guide(unittest.TestCase):
    def test_the_login_file_is_given_to_the_user_of_the_container_in_the_compose_file_and_the_eight_guides(self):
        compose = ROOT / "deploy" / "compose.yaml"
        if not compose.is_file():
            raise unittest.SkipTest("deploy/ lives in the repository, not in the zip of the monitor")
        self.assertIn("chown 10001:10001 deploy/gh_token.txt", compose.read_text(encoding="utf-8"))
        for suffix in ("", "_spa", "_deu", "_fra", "_ita", "_jpn", "_zho", "_por"):
            text = (HERE / "docs" / f"DEPLOYMENT{suffix}.md").read_text(encoding="utf-8")
            self.assertRegex(text, re.compile(r"chown 10001:10001 deploy/gh_token\.txt && chmod 600"), suffix)


if __name__ == "__main__":
    unittest.main()
