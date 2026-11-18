# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The routes that only the computer itself may call (the updater, the backup, the keys) stay closed behind a reverse proxy on the same machine: a request that arrives over loopback but carries any
forwarding header, or that comes through a declared proxy, is never "this computer". A mutation test shows that the check below really notices when a route stops asking.
Nothing here reaches GitHub."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor  # noqa: E402
from github_actions_monitor.security import localguard  # noqa: E402

SOURCE = Path(actions_monitor.__file__).read_text(encoding="utf-8")


def branches_that_ask(source):
    """The `if path in THIS_COMPUTER_...:` blocks of the handler that do NOT call self.this_computer() in their first three lines (empty when every one asks)."""
    lines = source.splitlines()
    bad = []
    for i, line in enumerate(lines):
        if re.match(r"\s+if path in THIS_COMPUTER_(ACTIONS|ADVANCED):", line):
            if not any("self.this_computer()" in later for later in lines[i + 1:i + 4]):
                bad.append(line.strip())
    return bad


class ProxyOnTheSameMachine(unittest.TestCase):
    def setUp(self):
        self.saved = dict(localguard.STATE)
        self.addCleanup(lambda: (localguard.STATE.clear(), localguard.STATE.update(self.saved)))

    def test_loopback_without_any_header_is_this_computer(self):
        localguard.STATE["behind_proxy"] = False
        localguard.STATE["proxy_host"] = ""
        self.assertTrue(localguard.is_this_computer(("127.0.0.1", 5000), {}))

    def test_every_forwarding_header_over_loopback_is_refused(self):
        localguard.STATE["behind_proxy"] = False
        localguard.STATE["proxy_host"] = ""
        for name in localguard.FORWARD_HEADERS:
            self.assertFalse(localguard.is_this_computer(("127.0.0.1", 5000), {name: "203.0.113.9"}), name)

    def test_a_forged_loopback_address_in_the_header_does_not_help(self):
        localguard.STATE["behind_proxy"] = False
        for value in ("127.0.0.1", "::1", "127.0.0.1, 203.0.113.9"):
            self.assertFalse(localguard.is_this_computer(("127.0.0.1", 5000), {"X-Forwarded-For": value}), value)

    def test_a_declared_proxy_closes_the_main_door_whatever_the_headers_say(self):
        localguard.STATE["behind_proxy"] = True
        self.assertFalse(localguard.is_this_computer(("127.0.0.1", 5000), {}))
        self.assertTrue(localguard.is_this_computer(("127.0.0.1", 5000), {}, door=True))

    def test_a_peer_that_is_not_loopback_is_never_this_computer(self):
        localguard.STATE["behind_proxy"] = False
        self.assertFalse(localguard.is_this_computer(("203.0.113.9", 5000), {}))

    def test_the_public_name_of_the_proxy_is_not_this_computer(self):
        localguard.STATE["behind_proxy"] = False
        localguard.STATE["proxy_host"] = "monitor.example.org"
        self.assertFalse(localguard.is_this_computer(("127.0.0.1", 5000), {"Host": "Monitor.Example.org"}))


class EveryRouteAsks(unittest.TestCase):
    def test_every_this_computer_branch_of_the_handler_calls_the_check(self):
        self.assertEqual(branches_that_ask(SOURCE), [])

    def test_the_check_notices_a_route_that_stopped_asking(self):
        block = "if path in THIS_COMPUTER_ADVANCED:\n            if not self.guard() or not self.this_computer():"
        mutated = SOURCE.replace(block, block.replace(" or not self.this_computer()", ""), 1)
        self.assertNotEqual(mutated, SOURCE)
        self.assertTrue(branches_that_ask(mutated))

    def test_the_updater_routes_are_in_the_list_that_asks(self):
        for route in ("/api/updates/check", "/api/updates/plan", "/api/updates/apply", "/api/updates/rollback"):
            self.assertIn(route, actions_monitor.THIS_COMPUTER_ADVANCED)


if __name__ == "__main__":
    unittest.main()
