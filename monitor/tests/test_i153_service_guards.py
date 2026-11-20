# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The guards of the service helper: it refuses to stop or start a unit that belongs to ANOTHER installation, refuses to start a unit while something else answers on its port, does not take a restart
for done while the process is still the old one, and `status` lists only the errors since the last start. systemctl and journalctl are doubles: nothing of the computer is touched."""
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_66_updater_engine as base  # noqa: E402
import test_mon214_systemd_helper as sd  # noqa: E402

mu = base.mu
UNIT = sd.UNIT


def reader(props, errors=""):
    """A double of the read-only questions: `show` answers the properties, `journalctl` the errors."""
    seen = []

    def run(argv, **kw):
        seen.append(tuple(argv))
        if argv[0] == "journalctl":
            return mock.Mock(returncode=0, stdout=errors, stderr="")
        wanted = [a.split("=", 1)[1] for a in argv if a.startswith("--property=")]
        text = "".join(f"{k}={props[k]}\n" for k in wanted if k in props)
        return mock.Mock(returncode=0, stdout=text, stderr="")
    run.seen = seen
    return run


class Ownership(unittest.TestCase):
    def test_a_unit_of_this_folder_is_not_foreign_and_one_of_another_folder_is(self):
        mine = {"WorkingDirectory": "/opt/monitor-a", "ExecStart": "{ path=/usr/bin/python3 ; argv[]=/usr/bin/python3 -m github_actions_monitor ; }"}
        self.assertEqual(mu.unit_foreign(UNIT, "/opt/monitor-a", mine), "")
        self.assertEqual(mu.unit_foreign(UNIT, "/opt/monitor-b", mine), "/opt/monitor-a")
        self.assertEqual(mu.unit_foreign(UNIT, "C:\\Tools\\Monitor", {"WorkingDirectory": "c:/tools/monitor/"}), "")      # case and slashes do not matter
        self.assertEqual(mu.unit_foreign(UNIT, "/opt/x", {}), "")      # what cannot be read blocks nothing

    def test_the_properties_come_only_from_a_plain_unit_name(self):
        double = reader({"MainPID": "42"})
        with mock.patch.dict(mu.SYSTEMD_READ, {"run": double}):
            self.assertEqual(mu.unit_pid(UNIT), 42)
            self.assertEqual(mu.unit_properties("x;y.service"), {})
        self.assertTrue(all(c[:3] == ("systemctl", "--user", "show") for c in double.seen))
        self.assertTrue(all("sudo" not in " ".join(c) for c in double.seen))


class RestartAndStatus(unittest.TestCase):
    def test_a_restart_that_kept_the_old_process_is_not_a_restart(self):
        pids = iter(["7", "7", "7"])

        def run(argv, **kw):
            return mock.Mock(returncode=0, stdout="MainPID=" + next(pids, "7") + "\n", stderr="")
        clock = {"t": 0.0}
        with mock.patch.dict(mu.SYSTEMD_READ, {"run": run}), mock.patch.object(mu.time, "sleep", lambda s: clock.update(t=clock["t"] + 1)), mock.patch.object(mu.time, "time", lambda: clock["t"]):
            self.assertEqual(mu.wait_new_pid(UNIT, 7, timeout=3), 0)

    def test_a_new_process_is_waited_for_and_found(self):
        pids = iter(["0", "0", "99"])

        def run(argv, **kw):
            return mock.Mock(returncode=0, stdout="MainPID=" + next(pids, "99") + "\n", stderr="")
        with mock.patch.dict(mu.SYSTEMD_READ, {"run": run}), mock.patch.object(mu.time, "sleep", lambda s: None):
            self.assertEqual(mu.wait_new_pid(UNIT, 7, timeout=30), 99)

    def test_status_lists_only_the_errors_since_the_last_start(self):
        double = reader({"ActiveEnterTimestamp": "Fri 2026-11-20 10:00:00 UTC"}, errors="boom one\n\nboom two\n")
        with mock.patch.dict(mu.SYSTEMD_READ, {"run": double}):
            self.assertEqual(mu.unit_errors(UNIT), ["boom one", "boom two"])
        journal = next(c for c in double.seen if c[0] == "journalctl")
        self.assertIn("--since", journal)
        self.assertEqual(journal[journal.index("--since") + 1], "Fri 2026-11-20 10:00:00 UTC")
        self.assertIn("err", journal)
        with mock.patch.dict(mu.SYSTEMD_READ, {"run": reader({})}):
            self.assertEqual(mu.unit_errors(UNIT), [])      # a unit that never started has no start to count from


class TheUpdateRefuses(base.Base):
    def setUp(self):
        super().setUp()
        self.root = base.make_install(self.tmp / "i", "2.0.1", base.config_from_defaults("2.0.1"))
        self.running = {"on": True}

    def probe(self, port):
        return {"port": port, "open": self.running["on"], "ours": self.running["on"], "version": "2.0.1"}

    def apply(self, props, systemctl):
        up = self.updater(self.root, probe=self.probe)

        def call(args, **kw):
            self.running["on"] = args[2] == "start"
            return systemctl(args, **kw)
        with mock.patch.dict(mu.SYSTEMD_READ, {"run": reader(props)}), mock.patch.dict(mu.SYSTEMCTL, {"run": call}), mock.patch.object(mu.time, "sleep", lambda s: None):
            return up.apply("2.0.8", {"systemd_unit": UNIT, "start": True, "handover": True, "start_timeout": 5, "pid_timeout": 0})

    def test_a_unit_of_another_installation_is_not_stopped_and_nothing_changes(self):
        before = base.tree_hash(self.root)
        double = sd.Systemctl()
        report = self.apply({"WorkingDirectory": "/somewhere/else", "ExecStart": "{ path=/usr/bin/python3 }"}, double)
        self.assertEqual(report["code"], mu.BLOCKED, report)
        self.assertEqual(double.calls, [])
        self.assertIn("/somewhere/else", report["error"])
        self.assertEqual(base.tree_hash(self.root), before)

    def test_a_restart_that_does_not_change_the_process_puts_the_previous_version_back(self):
        double = sd.Systemctl()
        report = self.apply({"MainPID": "55"}, double)      # the PID before the stop and after the start is the same one
        self.assertEqual(report["code"], mu.ROLLED_BACK, report)

    def test_the_messages_exist_in_the_eight_languages(self):
        for key in ("c.systemd_foreign", "c.systemd_port", "c.systemd_samepid", "c.systemd_errors"):
            for lang in mu.LANGS:
                self.assertTrue(mu._CAT[lang].get(key), (key, lang))


if __name__ == "__main__":
    unittest.main()
