# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Three small holes that an outside review found, closed and kept closed.

1. The lock of the configuration file never lets a save go on without it: when another process holds it for too long the save fails with a stable code, and nothing is written.
2. The command that the sentinel runs for a notification is accepted only when it is an absolute program that is not a shell, with no shell characters in any word.
3. The tokens for scripts (Authorization: Bearer) are off until somebody turns them on, and a token or password never reaches the audit.
"""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "tests"))

import _testenv  # noqa: F401,E402
import test_auth as ta  # noqa: E402
from github_actions_monitor.app import settings_api  # noqa: E402
from github_actions_monitor.data_pipeline import events  # noqa: E402
from github_actions_monitor.security import auth  # noqa: E402


def hold(path):
    """A second holder of the lock file, as another process would be (a separate handle conflicts with the first one on every system)."""
    handle = open(str(path) + ".lock", "a+b")
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    return handle


def release(handle):
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    handle.close()


class ConfigurationLock(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "actions_monitor.json"
        self.path.write_text(json.dumps({"refresh_seconds": 45}), encoding="utf-8")
        patcher = mock.patch.object(settings_api, "BACKUP_DIR", Path(self.tmp.name) / "backups")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_lock_that_stays_taken_fails_the_save_and_writes_nothing(self):
        other = hold(self.path)
        self.addCleanup(release, other)
        started = time.time()
        with self.assertRaises(settings_api.LockBusy), settings_api.file_lock(self.path, 0.3):
            self.fail("the body must not run without the lock")
        self.assertGreaterEqual(time.time() - started, 0.25, "it waited for the other process first")
        with mock.patch.object(settings_api, "LOCK_WAIT", 0.2):
            answer = settings_api.apply({"refresh_seconds": 90}, self.path)
        self.assertEqual(answer, {"ok": False, "errors": {"_": "busy"}})
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), {"refresh_seconds": 45})

    def test_a_lock_released_in_time_lets_the_save_through(self):
        other = hold(self.path)
        threading.Timer(0.3, release, [other]).start()
        with mock.patch.object(settings_api, "LOCK_WAIT", 5.0):
            answer = settings_api.apply({"refresh_seconds": 90}, self.path)
        self.assertTrue(answer["ok"], answer)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["refresh_seconds"], 90)

    def test_two_saves_of_this_process_wait_for_each_other(self):
        entered, leave, order = threading.Event(), threading.Event(), []

        def first():
            with settings_api.file_lock(self.path, 5):
                order.append("first in")
                entered.set()
                leave.wait(5)
                order.append("first out")

        def second():
            entered.wait(5)
            with settings_api.file_lock(self.path, 5):
                order.append("second in")
        threads = [threading.Thread(target=first), threading.Thread(target=second)]
        for thread in threads:
            thread.start()
        entered.wait(5)
        time.sleep(0.2)
        leave.set()
        for thread in threads:
            thread.join(10)
        self.assertEqual(order, ["first in", "first out", "second in"])

    def test_the_busy_error_has_a_text_in_every_language(self):
        from github_actions_monitor import i18n
        for lang in i18n.LANGS:
            self.assertNotEqual(i18n.tl(lang, "ui.cfg_err_busy"), "ui.cfg_err_busy", lang)


class NotifyCommand(unittest.TestCase):
    GOOD = [["/usr/local/bin/ping-me", "--level", "red"], ["C:\\Tools\\notify.exe", "--quiet"], ["/opt/tools/notify"]]
    BAD = [None, [], "notify", ["notify"], ["./notify"], ["/bin/sh", "-c", "x"], ["/usr/bin/bash"], ["C:\\Windows\\System32\\cmd.exe", "/c", "dir"],
           ["C:\\Windows\\System32\\WindowsPowerShell\\powershell.exe"], ["/usr/bin/env", "x"], ["/opt/n; rm -rf /"], ["/opt/n", "a&b"], ["/opt/n", "$(id)"],
           ["/opt/n", "`id`"], ["/opt/n", "a|b"], ["/opt/n", "two words"], ["/opt/n", "-c"], ["/opt/n", "-Command"], ["/opt/n", "line\nbreak"], ["/opt/n", ""],
           ["/opt/n", 5], ["/opt/n"] + ["a"] * 16, ["/opt/" + "x" * 300]]

    def test_only_safe_commands_are_accepted(self):
        for command in self.GOOD:
            self.assertEqual(events.valid_notify_command(command), command, command)
        for command in self.BAD:
            self.assertIsNone(events.valid_notify_command(command), command)

    def test_the_accepted_list_is_a_copy(self):
        command = ["/opt/n"]
        copy = events.valid_notify_command(command)
        copy.append("x")
        self.assertEqual(command, ["/opt/n"])

    def test_an_unsafe_command_is_never_run(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("subprocess.Popen") as popen:
            red = [{"kind": "red_new", "owner": "main", "text": "x"}]
            feed = events.Feed(Path(tmp) / "e.jsonl", Path(tmp) / "s.json", ["/bin/sh", "-c", "touch /tmp/pwned"])
            self.assertEqual((feed.notify_command, feed.notify_rejected), (None, True))
            feed._notify(red)
            popen.assert_not_called()
            good = events.Feed(Path(tmp) / "e2.jsonl", Path(tmp) / "s2.json", ["/opt/notify", "--quiet"])
            self.assertEqual((good.notify_command, good.notify_rejected), (["/opt/notify", "--quiet"], False))
            good._notify(red)
            self.assertEqual(popen.call_args[0][0], ["/opt/notify", "--quiet", "x"])
            nothing = events.Feed(Path(tmp) / "e3.jsonl", Path(tmp) / "s3.json", [])
            self.assertEqual((nothing.notify_command, nothing.notify_rejected), (None, False))


class ScriptTokens(unittest.TestCase):
    start = ta.LiveTeam.start
    call = ta.LiveTeam.call
    make_admin = ta.LiveTeam.make_admin
    sign_in = ta.LiveTeam.sign_in

    def test_off_by_default_the_login_for_scripts_is_refused(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()
        status, body, _ = self.call("/api/auth/login", {"username": "root", "password": ta.PASSWORD, "client": "api"})
        self.assertEqual((status, body["code"]), (403, "bearer_off"))
        self.assertEqual(self.call("/api/auth/login", {"username": "root", "password": ta.PASSWORD, "client": "web"})[0], 200, "the browser still signs in")

    def test_a_bearer_header_without_the_switch_is_not_a_session(self):
        self.start({"auth": {"enabled": True}, "session_guard": False})
        self.make_admin()
        self.assertEqual(self.call("/api/alerts", headers={"Authorization": "Bearer msn_" + "a" * 40})[0], 401)

    def test_neither_the_token_nor_the_password_reaches_the_audit(self):
        self.start({"auth": {"enabled": True, "allow_bearer": True}, "session_guard": False})
        self.make_admin()
        headers = self.sign_in("root", client="api")
        token = headers["Authorization"].split(" ", 1)[1]
        self.call("/api/alerts", headers=headers)
        self.call("/api/alerts", headers={"Authorization": "Bearer msn_" + "b" * 40})
        text = auth.audit_path().read_text(encoding="utf-8")
        for secret in (token, "msn_", "Bearer", "Authorization", ta.PASSWORD):
            self.assertNotIn(secret, text)

    def test_the_default_is_off_in_the_example_and_in_the_defaults(self):
        example = json.loads((HERE / "assets" / "examples" / "actions_monitor.example.json").read_text(encoding="utf-8"))
        from github_actions_monitor.app import actions_monitor as am
        self.assertIs(example["auth"]["allow_bearer"], False)
        self.assertIs(am.DEFAULTS["auth"]["allow_bearer"], False)
        self.assertIs(auth.DEFAULTS["allow_bearer"], False)


if __name__ == "__main__":
    unittest.main()
