# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`updates.systemd_helper`: a monitor that runs as a systemd USER service may be updated from the page. The helper only ever runs `systemctl --user stop|start|is-active <plain unit name>`, never
sudo, never a system service; it stops the unit before applying and starts it after, and when the new version does not come up the previous one is put back and the unit started again. Off by default.
systemctl is a double here: nothing of the computer is touched."""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_66_updater_engine as base  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.ops import updates  # noqa: E402

mu = base.mu
UNIT = "github-actions-monitor.service"
USER_CGROUP = "0::/user.slice/user-1000.slice/user@1000.service/app.slice/" + UNIT + "\n"
SYSTEM_CGROUP = "0::/system.slice/" + UNIT + "\n"
ENV = {"INVOCATION_ID": "abc"}


class Systemctl:
    """Records what the helper asks of systemctl; `fail` = the actions that answer an error."""

    def __init__(self, fail=()):
        self.calls, self.fail = [], set(fail)

    def __call__(self, args, **kw):
        self.calls.append(tuple(args))
        bad = args[2] in self.fail
        return mock.Mock(returncode=1 if bad else 0, stdout="", stderr="Failed to " + args[2] if bad else "")


class WhichUnit(unittest.TestCase):
    def test_a_user_unit_is_named(self):
        with mock.patch.object(mu.os, "name", "posix"):
            self.assertEqual(mu.user_unit(ENV, USER_CGROUP), UNIT)

    def test_a_system_unit_or_no_systemd_is_not_a_helper_case(self):
        with mock.patch.object(mu.os, "name", "posix"):
            self.assertEqual(mu.user_unit(ENV, SYSTEM_CGROUP), "")
            self.assertEqual(mu.user_unit({}, USER_CGROUP), "")
            self.assertEqual(mu.user_unit(ENV, "0::/user.slice/user@1000.service/app.slice/not a unit.service\n"), "")
            self.assertEqual(mu.user_unit(ENV, "0::/user.slice/user@1000.service/app.slice/x;rm -rf.service\n"), "")
            self.assertEqual(mu.user_unit(ENV, ""), "")
        with mock.patch.object(mu.os, "name", "nt"):
            self.assertEqual(mu.user_unit(ENV, USER_CGROUP), "")

    def test_systemctl_is_only_asked_three_things_about_a_plain_unit_and_never_with_sudo(self):
        double = Systemctl()
        with mock.patch.dict(mu.SYSTEMCTL, {"run": double}):
            self.assertEqual(mu.systemctl_user("stop", UNIT)[0], 0)
            self.assertEqual(mu.systemctl_user("start", UNIT)[0], 0)
            self.assertEqual(mu.systemctl_user("is-active", UNIT)[0], 0)
            for action, unit in (("restart", UNIT), ("disable", UNIT), ("stop", "a b.service"), ("stop", "x;y.service"), ("stop", "../x.service"), ("stop", "plain"), ("stop", "")):
                self.assertEqual(mu.systemctl_user(action, unit), (1, "refused"), (action, unit))
        self.assertEqual(double.calls, [("systemctl", "--user", "stop", UNIT), ("systemctl", "--user", "start", UNIT), ("systemctl", "--user", "is-active", UNIT)])
        self.assertTrue(all("sudo" not in " ".join(c) for c in double.calls))

    def test_a_missing_systemctl_is_an_answer_not_an_exception(self):
        def boom(*a, **k):
            raise FileNotFoundError("systemctl")
        with mock.patch.dict(mu.SYSTEMCTL, {"run": boom}):
            self.assertEqual(mu.systemctl_user("stop", UNIT)[0], 1)


class TheUpdateAroundTheUnit(base.Base):
    def setUp(self):
        super().setUp()
        self.root = base.make_install(self.tmp / "i", "2.0.1", base.config_from_defaults("2.0.1"))
        self.before = base.tree_hash(self.root)
        self.running = {"on": True}

    def probe(self, port):
        return {"port": port, "open": self.running["on"], "ours": self.running["on"], "version": self.version}

    def run_update(self, double, opts, version="2.0.8"):
        self.version = version
        up = self.updater(self.root, probe=self.probe)
        real = Systemctl.__call__

        def call(args, **kw):
            answer = real(double, args, **kw)
            if args[2] == "stop" and answer.returncode == 0:
                self.running["on"] = False      # the service stopped: the monitor no longer answers
            elif args[2] == "start" and answer.returncode == 0:
                self.running["on"] = True
            return answer
        with mock.patch.dict(mu.SYSTEMCTL, {"run": call}), mock.patch.object(mu.time, "sleep", lambda s: None):
            return up.apply("2.0.8", dict({"systemd_unit": UNIT, "start": True, "handover": True, "start_timeout": 5}, **opts))

    def test_it_stops_the_unit_applies_and_starts_it(self):
        double = Systemctl()
        report = self.run_update(double, {})
        self.assertTrue(report["ok"], report)
        self.assertEqual([c[2] for c in double.calls], ["stop", "start"])
        self.assertEqual(mu.read_tool_version(self.root), "2.0.8")
        self.assertTrue(any(c["code"] == "systemd" for c in report["plan"]["checks"]))

    def test_if_the_unit_cannot_be_stopped_nothing_is_touched(self):
        double = Systemctl(fail=("stop",))
        report = self.run_update(double, {})
        self.assertEqual(report["code"], mu.BLOCKED)
        self.assertEqual([c[2] for c in double.calls], ["stop"])
        self.assertEqual(base.tree_hash(self.root), self.before)

    def test_if_the_new_version_does_not_come_up_the_previous_one_is_put_back_and_the_unit_started_again(self):
        double = Systemctl(fail=())
        self.version = "2.0.8"
        up = self.updater(self.root, probe=self.probe)
        calls = []

        def call(args, **kw):
            calls.append(args[2])
            if args[2] == "stop":
                self.running["on"] = False
            elif args[2] == "start":
                self.running["on"] = True
                self.version = "2.0.1" if calls.count("start") > 1 else "9.9.9"      # the first start answers a version that is not the one asked for
            return mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.dict(mu.SYSTEMCTL, {"run": call}), mock.patch.object(mu.time, "sleep", lambda s: None):
            report = up.apply("2.0.8", {"systemd_unit": UNIT, "start": True, "handover": True, "start_timeout": 5})
        self.assertEqual(report["code"], mu.ROLLED_BACK, report)
        self.assertEqual(calls, ["stop", "start", "start"])
        self.assertEqual(mu.read_tool_version(self.root), "2.0.1")
        self.assertEqual(base.tree_hash(self.root), self.before)
        del double

    def test_the_way_back_stops_and_starts_the_unit_too(self):
        self.running["on"] = False
        self.version = "2.0.8"
        up = self.updater(self.root, probe=self.probe)
        self.assertTrue(up.apply("2.0.8", {})["ok"])
        double = Systemctl()

        def call(args, **kw):
            answer = double(args, **kw)
            self.running["on"] = args[2] == "start"
            self.version = "2.0.1"
            return answer
        self.running["on"] = True
        with mock.patch.dict(mu.SYSTEMCTL, {"run": call}), mock.patch.object(mu.time, "sleep", lambda s: None):
            report = up.go_back(confirm=lambda entry: True, systemd_unit=UNIT)
        self.assertTrue(report["ok"], report)
        self.assertEqual([c[2] for c in double.calls], ["stop", "start"])
        self.assertEqual(mu.read_tool_version(self.root), "2.0.1")


class ThePageSide(unittest.TestCase):
    def setUp(self):
        self.mod = updates.module()
        if self.mod is None:
            self.skipTest("no updater in this copy")

    def test_the_switch_is_off_by_default_and_only_a_real_true_turns_it_on(self):
        self.assertFalse(updates.helper_on({}))
        self.assertFalse(updates.helper_on({"updates": {"systemd_helper": "yes"}}))
        self.assertTrue(updates.helper_on({"updates": {"systemd_helper": True}}))
        from github_actions_monitor.app import actions_monitor as am
        self.assertFalse(am.DEFAULTS["updates"]["systemd_helper"])
        self.assertIn("updates.systemd_helper", settings_api.FIELDS)

    def test_under_a_service_the_page_refuses_unless_the_helper_is_on_and_the_service_is_a_user_one(self):
        with mock.patch.object(self.mod, "in_container", return_value=False), mock.patch.object(self.mod, "under_service", return_value=True):
            with mock.patch.object(self.mod, "user_unit", return_value=UNIT):
                self.assertEqual(updates.reason_blocked(env=ENV), "service")
                self.assertEqual(updates.reason_blocked(env=ENV, helper=True), "")
            with mock.patch.object(self.mod, "user_unit", return_value=""):
                self.assertEqual(updates.reason_blocked(env=ENV, helper=True), "service", "a system service stays a job for the command line")

    def test_a_container_and_the_demo_and_lite_stay_refused_whatever_the_helper_says(self):
        with mock.patch.object(self.mod, "in_container", return_value=True), mock.patch.object(self.mod, "user_unit", return_value=UNIT):
            self.assertEqual(updates.reason_blocked(env=ENV, helper=True), "container")
        self.assertEqual(updates.reason_blocked(demo=True, helper=True), "demo")
        self.assertEqual(updates.reason_blocked(lite=True, helper=True), "lite")

    def test_the_child_gets_the_unit_only_with_the_helper_on_a_user_service(self):
        with mock.patch.object(self.mod, "under_service", return_value=True), mock.patch.object(self.mod, "user_unit", return_value=UNIT):
            self.assertEqual(updates.unit_args(self.mod, True, ENV), ["--systemd-unit", UNIT])
            self.assertEqual(updates.unit_args(self.mod, False, ENV), [])
        with mock.patch.object(self.mod, "under_service", return_value=False):
            self.assertEqual(updates.unit_args(self.mod, True, ENV), [])

    def test_the_command_line_takes_a_plain_unit_only(self):
        parser = mu.build_parser() if hasattr(mu, "build_parser") else None
        if parser is None:
            self.skipTest("no parser builder")
        good = mu.options_of(parser.parse_args(["apply", "--systemd-unit", UNIT]))
        self.assertEqual(good["systemd_unit"], UNIT)
        bad = mu.options_of(parser.parse_args(["apply", "--systemd-unit", "x y;z.service"]))
        self.assertIsNone(bad["systemd_unit"])
        self.assertIsNone(mu.options_of(parser.parse_args(["apply"]))["systemd_unit"])


if __name__ == "__main__":
    unittest.main()
