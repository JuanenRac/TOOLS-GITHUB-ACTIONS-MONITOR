# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The doctor of an installation that lives for months: its stable exit codes (0 / 1 / 3 with --strict / 4), the checks of the operation (volumes, supervisor, limits, SQLite in hot, age of the
copy, disk, /metrics), that the secret of the webhook is only ever compared by length, and that the lite edition neither runs them nor loads them."""
import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.cli import doctor, monitor_cli  # noqa: E402
from github_actions_monitor.ops import checks, schedule  # noqa: E402
from github_actions_monitor.storage import sqlite_storage  # noqa: E402

SECRET = "hook-secret-" + "Z" * 20


def row(status, name="x"):
    return {"id": name, "status": status, "detail": "", "fix": ""}


class ExitCodes(unittest.TestCase):
    def test_the_table_is_fixed(self):
        self.assertEqual((doctor.EXIT_OK, doctor.EXIT_FAIL, doctor.EXIT_WARN, doctor.EXIT_DOCTOR_ERROR), (0, 1, 3, 4))
        self.assertEqual(doctor.exit_code([row("ok"), row("ok")]), 0)
        self.assertEqual(doctor.exit_code([row("ok"), row("warn")]), 0, "a warning is still 0 without --strict")
        self.assertEqual(doctor.exit_code([row("ok"), row("warn")], strict=True), 3)
        self.assertEqual(doctor.exit_code([row("warn"), row("fail")], strict=True), 1, "a failure wins over a warning")
        self.assertEqual(doctor.exit_code([row("fail")]), 1)

    def test_the_setting_makes_a_warning_exit_three_like_the_flag(self):
        self.assertFalse(doctor.strict_from({}))
        self.assertTrue(doctor.strict_from({"ops": {"doctor": {"strict_exit": True}}}))
        self.assertFalse(doctor.strict_from({"ops": {"doctor": {"strict_exit": "yes"}}}))

    def run_cli(self, *argv):
        self.addCleanup(i18n.set_language, "en")      # the command pins the language of the process: put it back for the tests that follow
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = monitor_cli.main(list(argv) + ["--lang", "en"])
        return code, out.getvalue()

    def test_the_command_gives_each_code(self):
        warn_only = [row("ok", "a"), row("warn", "b")]
        with mock.patch.object(doctor, "run", return_value=warn_only), mock.patch("github_actions_monitor.app.toolconfig.raw_config", return_value={}):
            self.assertEqual(self.run_cli("doctor")[0], 0)
            self.assertEqual(self.run_cli("doctor", "--strict")[0], 3)
        with mock.patch.object(doctor, "run", return_value=warn_only), mock.patch("github_actions_monitor.app.toolconfig.raw_config", return_value={"ops": {"doctor": {"strict_exit": True}}}):
            self.assertEqual(self.run_cli("doctor")[0], 3)
        with mock.patch.object(doctor, "run", return_value=[row("fail")]), mock.patch("github_actions_monitor.app.toolconfig.raw_config", return_value={}):
            self.assertEqual(self.run_cli("doctor", "--strict")[0], 1)
        with mock.patch.object(doctor, "run", side_effect=RuntimeError("boom")), mock.patch("github_actions_monitor.app.toolconfig.raw_config", return_value={}):
            code, text = self.run_cli("doctor", "--json")
            self.assertEqual(code, 4)
            self.assertNotIn("boom", text)

    def test_the_document_carries_the_code_in_the_complete_edition_only(self):
        self.assertEqual(doctor.as_json([row("warn")], "complete", True)["exit"], 3)
        self.assertEqual(doctor.as_json([row("warn")], "complete")["warnings"], 1)
        self.assertNotIn("exit", doctor.as_json([row("warn")], "lite"))


class TheChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        for kind in ("config", "data", "logs", "ai"):
            (self.base / kind).mkdir()

    def test_the_complete_edition_adds_its_checks_after_the_others_and_the_lite_one_does_not(self):
        runner = lambda *a, **k: (1, "", "")      # noqa: E731
        complete = doctor.run(runner=runner, folder=self.base, ports=(), config={}, edition="complete")
        self.assertEqual([c["id"] for c in complete], list(doctor.ORDER + doctor.ORDER_OPS))
        for edition in (None, "lite"):
            self.assertEqual([c["id"] for c in doctor.run(runner=runner, folder=self.base, ports=(), config={}, edition=edition)], list(doctor.ORDER))
        for name in doctor.ORDER_OPS:
            text = i18n.t("doctor.t." + name)
            self.assertNotEqual(text, "doctor.t." + name)
            self.assertNotEqual(i18n.t("doctor.f." + name), "doctor.f." + name)

    def test_volumes_write_and_read_a_real_file_and_clean_up(self):
        with mock.patch.object(checks.paths, "folder", side_effect=lambda kind, base=None: self.base / kind):
            status, detail = checks.volumes({}, self.base)
        self.assertEqual(status, "ok", detail)
        self.assertEqual([p.name for p in (self.base / "data").iterdir()], [])
        self.assertIsNone(checks.probe(self.base / "data"))

    def test_a_read_only_volume_fails_and_the_probe_file_never_stays(self):
        with mock.patch.object(checks.paths, "folder", side_effect=lambda kind, base=None: self.base / kind):
            with mock.patch("builtins.open", side_effect=PermissionError(13, "Permission denied")):
                status, detail = checks.volumes({}, self.base)
        self.assertEqual(status, "fail")
        self.assertIn("read-only", detail)
        self.assertEqual([p.name for p in (self.base / "data").iterdir()], [])
        self.assertIsNotNone(checks.probe(self.base / "missing"))

    def test_the_webhook_secret_is_compared_by_length_and_never_shown(self):
        config = {"webhook": {"enabled": True}}
        status, detail = checks.limits(config, self.base, secret_reader=lambda name: SECRET)
        self.assertEqual(status, "ok")
        status, detail = checks.limits(config, self.base, secret_reader=lambda name: "short")
        self.assertEqual(status, "warn")
        self.assertIn("5 < 16", detail)
        self.assertEqual(checks.limits(config, self.base, secret_reader=lambda name: "")[0], "warn")
        self.assertEqual(checks.limits({"ops": {"doctor": {"webhook_min_length": 40}}, "webhook": {"enabled": True}}, self.base, secret_reader=lambda name: SECRET)[0], "warn")
        self.assertEqual(checks.limits({}, self.base, secret_reader=lambda name: SECRET)[0], "ok", "a webhook that is off has nothing to compare")
        with mock.patch.dict(os.environ, {"MONITOR_WEBHOOK_SECRET": SECRET}):
            checked = doctor.run(runner=lambda *a, **k: (1, "", ""), folder=self.base, ports=(), config=config, edition="complete")
        self.assertNotIn(SECRET, json.dumps(doctor.as_json(checked)))
        self.assertNotIn(SECRET, doctor.text(checked, i18n.t))

    def test_the_age_of_the_last_copy(self):
        folder = self.base
        with mock.patch.object(schedule.opsconf.paths, "folder", side_effect=lambda kind, base=None: self.base / kind):
            self.assertEqual(checks.backup_age({}, folder)[0], "ok")
            on = {"ops": {"backup": {"enabled": True}}}
            self.assertEqual(checks.backup_age(on, folder), ("warn", "none yet"))
            schedule._save(folder, {"ok": True, "last_ok_epoch": 1000.0, "last_attempt_epoch": 1000.0, "last_ok": "x"})
            day = 86400.0
            self.assertEqual(checks.backup_age(on, folder, now=1000.0 + 2 * day)[0], "ok")
            self.assertEqual(checks.backup_age(on, folder, now=1000.0 + 9 * day)[0], "warn")
            self.assertEqual(checks.backup_age({}, folder, now=1000.0 + 9 * day)[0], "warn", "a copy that exists and is old is told even when the schedule is off")
            schedule._save(folder, {"ok": False, "error": "failed", "last_ok_epoch": 1000.0, "last_attempt_epoch": 1500.0})
            self.assertEqual(checks.backup_age(on, folder, now=1500.0)[0], "warn")

    def test_the_free_disk(self):
        Usage = type("Usage", (), {})
        def usage(free_mb):
            item = Usage()
            item.free = free_mb * 1048576
            return lambda path: item
        with mock.patch.object(checks.paths, "folder", side_effect=lambda kind, base=None: self.base / kind):
            self.assertEqual(checks.disk({}, self.base, usage(10000))[0], "ok")
            self.assertEqual(checks.disk({}, self.base, usage(300))[0], "warn")
            self.assertEqual(checks.disk({}, self.base, usage(20))[0], "fail")
            self.assertEqual(checks.disk({"ops": {"doctor": {"min_free_mb": 100}}}, self.base, usage(300))[0], "ok")

    def test_the_metrics_output_and_the_supervisor_only_look_when_a_monitor_runs(self):
        on = {"outputs": {"prometheus": {"enabled": True}}}
        self.assertEqual(checks.metrics({}, self.base), ("ok", "off"))
        self.assertEqual(checks.metrics(on, self.base, alive=lambda port: False), ("ok", "not running"))
        self.assertEqual(checks.metrics(on, self.base, alive=lambda port: True, fetch=lambda url: 200), ("ok", "answering"))
        self.assertEqual(checks.metrics(on, self.base, alive=lambda port: True, fetch=lambda url: 404)[0], "warn")
        self.assertEqual(checks.supervisor({}, self.base, alive=lambda port: False), ("ok", "not running"))
        self.assertEqual(checks.supervisor({}, self.base, alive=lambda port: True, ask=lambda *a: (200, {"ok": True, "supervisor": False, "cycle": {}}))[0], "ok")
        self.assertEqual(checks.supervisor({}, self.base, alive=lambda port: True, ask=lambda *a: (0, None))[0], "warn")
        self.assertEqual(checks.supervisor({}, self.base, alive=lambda port: True, ask=lambda *a: (503, {"ok": False, "cycle": {"stuck": True}}))[0], "fail")

    def test_one_check_that_breaks_does_not_hide_the_others(self):
        with mock.patch.object(checks, "disk", side_effect=RuntimeError("x")):
            found = checks.run_all({}, self.base)
        self.assertEqual(found["disk"][0], "warn")
        self.assertEqual(sorted(found), sorted(doctor.ORDER_OPS))


class SqliteInHot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.path = self.base / "storage.sqlite3"
        store = sqlite_storage.SqliteStorage(self.path)
        store.append_events("default", [{"at": f"2026-01-01T00:00:{i % 60:02d}Z", "kind": "k", "n": i} for i in range(3000)])
        store.close()
        self.config = {"storage": {"backend": "sqlite", "path": str(self.path)}}

    def hot(self, config=None, **options):
        return checks.sqlite_hot({**self.config, **(config or {})}, self.base, **options)

    def test_a_healthy_database_is_ok_in_each_mode_and_nothing_is_changed(self):
        before = self.path.read_bytes()
        self.assertEqual(self.hot()[0], "ok")
        self.assertEqual(self.hot({"ops": {"doctor": {"sqlite_check": "deep"}}})[0], "ok")
        self.assertEqual(self.hot({"ops": {"doctor": {"sqlite_check": "off"}}}), ("ok", "off"))
        self.assertEqual(self.path.read_bytes(), before, "opened read only")

    def test_a_damaged_database_fails(self):
        data = bytearray(self.path.read_bytes())
        for offset in range(4096 * 2, min(len(data), 4096 * 6), 7):
            data[offset] ^= 0xFF
        self.path.write_bytes(bytes(data))
        status, detail = self.hot({"ops": {"doctor": {"sqlite_check": "deep"}}})
        self.assertEqual(status, "fail", detail)

    def test_a_check_that_runs_out_of_time_is_a_warning_not_a_failure_and_does_not_block(self):
        moments = iter([0.0] + [10 ** 9] * 100000)
        status, detail = self.hot({"ops": {"doctor": {"sqlite_timeout_s": 1}}}, clock=lambda: next(moments))
        self.assertEqual(status, "warn", detail)
        self.assertIn("stopped", detail)

    def test_the_inspect_modes(self):
        self.assertEqual(sqlite_storage.inspect(self.path)["problems"], [])
        self.assertEqual(sqlite_storage.inspect(self.path, mode="quick")["problems"], [])
        self.assertFalse(sqlite_storage.inspect(self.path, mode="off")["timed_out"])
        self.assertIn("schema_version", sqlite_storage.inspect(self.path, mode="off"))
        with contextlib.closing(sqlite3.connect(str(self.path))) as conn:
            self.assertEqual(conn.execute("PRAGMA quick_check").fetchone()[0], "ok")


class LiteStaysAlone(unittest.TestCase):
    def test_the_lite_doctor_does_not_import_the_operation(self):
        import subprocess
        code = ("import sys; sys.path.insert(0, %r); import github_actions_monitor.cli.doctor as d; "
                "d.run(runner=lambda *a, **k: (1, '', ''), config={}, ports=(), edition='lite'); "
                "bad = [m for m in sys.modules if m.startswith('github_actions_monitor.ops')]; sys.exit(1 if bad else 0)") % str(HERE / "src")
        flags = {"creationflags": 0x08000000} if os.name == "nt" else {}
        done = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=120, **flags)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
