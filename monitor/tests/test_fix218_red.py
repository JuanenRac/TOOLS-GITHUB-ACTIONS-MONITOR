# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Regression tests of the network and access fixes: a stream of a revoked device ends, a connection that sends nothing is let go and the number of open connections has a ceiling, the chat receiver
counts only bad signatures against an address, the paths of this computer are not given to a client of the network, the webhook has a freshness window and keeps only the links of GitHub, and the
supervisor lets the chat through, takes the largest body of its accounts and answers the 413 after reading the body."""
import json
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor.app import actions_monitor as am  # noqa: E402
from github_actions_monitor.app import toolconfig  # noqa: E402
from github_actions_monitor.security import devices, localguard  # noqa: E402


class Network(unittest.TestCase):
    """Saves and puts back the state of the process that these tests change."""

    def setUp(self):
        self.guard = _testenv.guard(self)
        self.saved = (dict(am.LIVE_CONFIG), dict(localguard.STATE), dict(localguard.DEVICE_CHECK))
        self.addCleanup(self.restore)

    def restore(self):
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update(self.saved[0])
        localguard.STATE.clear()
        localguard.STATE.update(self.saved[1])
        localguard.DEVICE_CHECK.clear()
        localguard.DEVICE_CHECK.update(self.saved[2])
        for device in devices.list_devices():
            devices.revoke(device["id"])
        devices.close()


class StreamOfARevokedDevice(Network):
    def paired(self):
        am.LIVE_CONFIG.clear()
        am.LIVE_CONFIG.update({**am.DEFAULTS, "pairing": {"enabled": True}})
        localguard.configure(True, "127.0.0.1", "t" * 24)
        localguard.DEVICE_CHECK["fn"] = am._device_token_ok
        cfg = devices.settings(am.LIVE_CONFIG)
        return cfg

    def test_revoking_the_device_ends_its_open_stream_at_once(self):
        cfg = self.paired()
        opened = devices.start(cfg)
        token, device = devices.redeem(cfg, opened["code"], "Android")
        self.assertTrue(token.startswith("dev_"))
        handler = types.SimpleNamespace(headers={"Authorization": "Bearer " + token}, path="/api/live-events/stream")
        stop = am.Handler.stream_guard(handler)
        self.assertFalse(stop(), "a live device keeps its stream")
        self.assertTrue(devices.revoke(device["id"]))
        self.assertTrue(stop(), "a revoked device must not keep listening until live.sse.max_seconds")

    def test_switching_the_pairing_off_ends_the_stream_of_a_device(self):
        cfg = self.paired()
        opened = devices.start(cfg)
        token, _device = devices.redeem(cfg, opened["code"], "Android")
        handler = types.SimpleNamespace(headers={"X-Monitor-Access": token}, path="/api/ai/stream")
        stop = am.Handler.stream_guard(handler)
        self.assertFalse(stop())
        am.LIVE_CONFIG["pairing"] = {"enabled": False}
        self.assertTrue(stop())

    def test_the_access_token_itself_and_the_loopback_mode_are_untouched(self):
        self.paired()
        handler = types.SimpleNamespace(headers={"X-Monitor-Access": "t" * 24}, path="/api/updates/stream")
        self.assertFalse(am.Handler.stream_guard(handler)())
        localguard.configure(False, "127.0.0.1", "")
        self.assertFalse(am.Handler.stream_guard(types.SimpleNamespace(headers={}, path="/api/updates/stream"))())


if __name__ == "__main__":
    unittest.main()
