# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The server side of the native app: screens, device tokens, the push planner and deep links. The sender is a fake; there is no network and no clock."""
import unittest

import _testenv  # noqa: F401
from github_actions_monitor.phase4 import mobile

T0 = 1_800_000_000 - (1_800_000_000 % 86400) + 10 * 3600           # 10:00 UTC
TOKEN = "d" * 40


def alert(i, level="critical", account="acc1", title="Build broke"):
    return {"id": "a%d" % i, "code": "ci.red", "level": level, "account_id": account, "title": title, "repo": "o/secret-repo"}


class Sender:
    def __init__(self, ok=True):
        self.sent, self.ok = [], ok

    def __call__(self, message):
        self.sent.append(message)
        return self.ok


def planner(settings=None, send=None, users=(("ana", TOKEN, "android"),)):
    registry = mobile.DeviceRegistry()
    for user, token, platform in users:
        registry.register(user, token, platform)
    send = send or Sender()
    return mobile.PushPlanner(dict({"enabled": True}, **(settings or {})), registry, send), send, registry


class Screens(unittest.TestCase):
    def test_every_screen_reads_the_api_v1_only(self):
        for name, paths in mobile.screens(("now", "alerts", "live", "score", "health", "nonsense")).items():
            self.assertTrue(paths and all(p.startswith("/api/v1/") for p in paths), name)
        self.assertNotIn("nonsense", mobile.screens(("nonsense",)))

    def test_mobile_screens_ask_for_the_compact_profile(self):
        for name in ("now", "alerts", "live"):
            self.assertTrue(any("profile=mobile" in p for p in mobile.screens()[name]), name)


class Devices(unittest.TestCase):
    def test_register_validates_and_never_exposes_the_token(self):
        reg = mobile.DeviceRegistry()
        fp = reg.register("ana", TOKEN, "android")
        self.assertEqual(len(fp), 12)
        self.assertNotIn(TOKEN, str(reg.listing("ana")))
        for bad in (("ana", "short", "android"), ("ana", TOKEN, "windows"), ("", TOKEN, "ios"), ("ana", TOKEN + "\n", "ios"), ("ana", None, "ios"), ("ana", "x y" * 20, "ios")):
            self.assertIsNone(reg.register(*bad), bad)

    def test_only_the_owner_removes_a_device(self):
        reg = mobile.DeviceRegistry()
        fp = reg.register("ana", TOKEN, "ios")
        self.assertFalse(reg.unregister("eve", fp))
        self.assertTrue(reg.unregister("ana", fp))
        self.assertEqual(reg.listing("ana"), [])


class Settings(unittest.TestCase):
    def test_defaults_are_conservative(self):
        s = mobile.push_settings(None)
        self.assertEqual((s["enabled"], s["min_level"]), (False, "critical"))

    def test_bad_values_are_ignored(self):
        s = mobile.push_settings({"enabled": "yes", "min_level": "fatal", "quiet_hours": "25:00-26:00", "max_per_device_per_hour": 0, "dedupe_seconds": True, "include_title": 1})
        self.assertEqual(s, mobile.PUSH_DEFAULTS)
        good = mobile.push_settings({"enabled": True, "min_level": "error", "quiet_hours": "22:00-07:00", "max_per_device_per_hour": 3})
        self.assertEqual((good["enabled"], good["min_level"], good["quiet_hours"], good["max_per_device_per_hour"]), (True, "error", "22:00-07:00", 3))


class Push(unittest.TestCase):
    def test_off_by_default_sends_nothing(self):
        p, send, _ = planner({"enabled": False})
        self.assertEqual(p.notify([alert(1)], T0), 0)
        self.assertEqual(send.sent, [])

    def test_only_critical_by_default_and_once(self):
        p, send, _ = planner()
        self.assertEqual(p.notify([alert(1, "error"), alert(2, "info"), alert(3)], T0), 1)
        self.assertEqual(p.notify([alert(3)], T0 + 60), 0)                  # the same alert is not repeated
        self.assertEqual(p.notify([alert(3)], T0 + 3601), 1)                # until the dedupe time passes
        self.assertEqual(len(send.sent), 2)

    def test_the_message_is_minimal_and_clean(self):
        p, send, _ = planner()
        p.notify([alert(1, title="failed with token ghp_" + "A1b2C3d4E5" * 3 + " in /srv/ci/work")], T0)
        message = send.sent[0]
        self.assertEqual(set(message), {"alert_id", "level", "code", "view", "title", "device", "platform"})
        self.assertNotIn("ghp_", message["title"])
        self.assertNotIn("/srv", message["title"])
        self.assertNotIn("secret-repo", str(message))
        self.assertEqual(message["view"], "alerts")

    def test_titles_can_be_left_out(self):
        p, send, _ = planner({"include_title": False})
        p.notify([alert(1)], T0)
        self.assertNotIn("title", send.sent[0])

    def test_quiet_hours(self):
        p, send, _ = planner({"quiet_hours": "09:00-11:00"})
        self.assertEqual(p.notify([alert(1)], T0), 0)
        self.assertEqual(p.notify([alert(1)], T0 + 2 * 3600), 1)

    def test_rate_per_device_per_hour(self):
        p, send, _ = planner({"max_per_device_per_hour": 2})
        self.assertEqual(p.notify([alert(i) for i in range(5)], T0), 2)
        self.assertEqual(p.notify([alert(i) for i in range(5, 8)], T0 + 3700), 2)

    def test_a_device_hears_only_of_the_accounts_its_user_may_see(self):
        p, send, _ = planner(users=(("ana", TOKEN, "android"), ("bob", "e" * 40, "ios")))
        sent = p.notify([alert(1, account="acc1")], T0, accounts_of={"ana": ["acc1"], "bob": ["acc2"]})
        self.assertEqual(sent, 1)
        self.assertEqual(send.sent[0]["device"], TOKEN)

    def test_an_alert_with_no_account_scope_reaches_nobody_when_scopes_are_given(self):
        p, send, _ = planner()
        self.assertEqual(p.notify([alert(1, account="")], T0, accounts_of={"ana": ["acc1"]}), 0)

    def test_a_failed_send_is_retried_next_time(self):
        send = Sender(ok=False)
        p, _, _ = planner(send=send)
        self.assertEqual(p.notify([alert(1)], T0), 0)
        send.ok = True
        self.assertEqual(p.notify([alert(1)], T0 + 5), 1)

    def test_malformed_alerts_are_skipped(self):
        p, send, _ = planner()
        self.assertEqual(p.notify([{"level": "critical"}, {"id": "x", "level": "weird"}, {}], T0), 0)


class DeepLinks(unittest.TestCase):
    def test_roundtrip(self):
        digest = "ab" * 32
        self.assertEqual(mobile.parse_deep_link(mobile.deep_link("p000001", digest)), ("p000001", digest))

    def test_anything_else_is_refused(self):
        digest = "ab" * 32
        for bad in (None, "", "https://evil.example/proposal/p1?hash=" + digest, "ghamon://proposal/P1?hash=" + digest, "ghamon://proposal/p000001?hash=zz", "ghamon://proposal/p000001?hash=" + digest + "\n",
                    "ghamon://proposal/p000001?hash=" + digest + "&approve=1", "ghamon://proposal/../x?hash=" + digest, "ghamon://approve/p000001?hash=" + digest):
            self.assertIsNone(mobile.parse_deep_link(bad), bad)


if __name__ == "__main__":
    unittest.main()
