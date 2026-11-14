# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Guards that turn two lessons of the monitor's own CI into tests: a test that talks to the real server must not pin the first item of a list that the server also fills (the server writes by its own
account and the first item changes with the order), and the name of a setting must not end in a word that the schema reserves for secrets."""
import re
import unittest
from pathlib import Path

import _testenv  # noqa: F401

HERE = Path(__file__).resolve().parent
RESERVED = re.compile(r"secret|token|password|pubkey|command|key$")
PINNED = re.compile(r"""\[\s*["'](?:categories|failures|library|apply_now)["']\s*\]\s*\[\s*0\s*\]""")
SERVER_TESTS = [p for p in sorted(HERE.glob("test_*.py")) if "LiveServer" in p.read_text(encoding="utf-8") and p.name != Path(__file__).name]


class WhatTheCiAlreadyTaughtUs(unittest.TestCase):
    def test_a_test_with_the_real_server_does_not_pin_the_first_item_of_a_list_the_server_fills(self):
        found = []
        for path in SERVER_TESTS:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if PINNED.search(line) and "assertIn" not in line:
                    found.append(f"{path.name}:{number}")
        self.assertEqual(found, [], "search the item you expect (assertIn over the list) instead of taking [0]")

    def test_the_guard_sees_the_mistake_it_exists_for(self):
        self.assertTrue(PINNED.search('self.assertEqual(body["categories"][0]["category"], "test")'))
        self.assertFalse(PINNED.search('self.assertIn("test", [c["category"] for c in body["categories"]])'))

    def test_a_test_never_starts_its_ports_at_the_port_the_system_gave_plus_a_margin_without_a_cap(self):
        """A port near the top of the range left a stretch of ports without room and a Windows runner failed with 'no free port'."""
        found = []
        for path in sorted(HERE.glob("test_*.py")):
            if path.name == Path(__file__).name:
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"getsockname\(\)\[1\]\s*\+\s*\d", line) and "min(" not in line:
                    found.append(f"{path.name}:{number}")
        self.assertEqual(found, [], "cap it: min(port + margin, 64000), and check that the stretch has a free port")

    def test_no_setting_ends_in_a_word_reserved_for_secrets(self):
        from github_actions_monitor.app import settings_api
        bad = [k for k in settings_api.FIELDS if RESERVED.search(k.split(".")[-1]) and not k.startswith("sentinel.readiness.health.weights.") and not k.endswith(("token_env", "github_token.enabled", "github_token.store"))]
        self.assertEqual(bad, [], "name the setting without token, secret, password, key or command in its last part (for example share_reads)")


if __name__ == "__main__":
    unittest.main()
