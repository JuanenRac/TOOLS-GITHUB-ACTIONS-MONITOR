# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Cross-platform behaviour: commands, launchers and packaging must not depend on the system the tests run on."""
import sys
import unittest
import _testenv  # noqa: F401
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import platform_compat  # noqa: E402


class CommandText(unittest.TestCase):
    def test_windows_quotes_like_cmd(self):
        text = platform_compat.command_text(["py", "-3", r"C:\Program Files\tool.py", "REPO"], windows=True)
        self.assertIn('"C:\\Program Files\\tool.py"', text)

    def test_posix_quotes_like_a_shell(self):
        text = platform_compat.command_text(["python3", "/home/a b/tool.py", "REPO"], windows=False)
        self.assertIn("'/home/a b/tool.py'", text)
        self.assertNotIn('"', text)


class PythonCommand(unittest.TestCase):
    def test_windows_with_launcher_uses_py(self):
        with mock.patch("platform_compat.shutil.which", return_value=r"C:\Windows\py.exe"):
            self.assertEqual(platform_compat.python_argv(windows=True), ["py", "-3"])

    def test_windows_without_launcher_uses_the_running_python(self):
        with mock.patch("platform_compat.shutil.which", return_value=None):
            self.assertEqual(platform_compat.python_argv(windows=True), [sys.executable])

    def test_posix_never_uses_py(self):
        self.assertEqual(platform_compat.python_argv(windows=False), [sys.executable])
        self.assertEqual(platform_compat.python_hint(windows=False), "python3")
        self.assertEqual(platform_compat.python_hint(windows=True), "py -3")


class GhHint(unittest.TestCase):
    def test_each_system_gets_its_own_installer(self):
        self.assertIn("winget", platform_compat.gh_install_hint("win32"))
        self.assertIn("brew install gh", platform_compat.gh_install_hint("darwin"))
        self.assertIn("apt", platform_compat.gh_install_hint("linux"))
        for system in ("win32", "darwin", "linux"):
            self.assertIn("gh auth login", platform_compat.gh_install_hint(system))


class Launchers(unittest.TestCase):
    NAMES = ("MONITOR_GITHUB_ACTIONS.sh", "BATCH_GITHUB_ACTIONS.sh", "MONITOR_GITHUB_ACTIONS.command", "BATCH_GITHUB_ACTIONS.command")

    def test_shell_launchers_exist_with_unix_line_endings(self):
        for name in self.NAMES:
            data = (HERE / name).read_bytes()
            self.assertTrue(data.startswith(b"#!/usr/bin/env bash\n"), name)
            self.assertNotIn(b"\r", data, name)

    def test_launchers_never_use_the_windows_python_launcher(self):
        for name in self.NAMES:
            self.assertNotIn("py -3", (HERE / name).read_text(encoding="utf-8"), name)

    def test_the_monitor_launcher_checks_gh_and_runs_the_monitor(self):
        text = (HERE / "MONITOR_GITHUB_ACTIONS.sh").read_text(encoding="utf-8")
        self.assertIn("command -v gh", text)
        self.assertIn("actions_monitor.py", text)

    def test_the_batch_launcher_offers_the_same_six_options_as_the_bat(self):
        sh = (HERE / "BATCH_GITHUB_ACTIONS.sh").read_text(encoding="utf-8")
        bat = (HERE / "BATCH_GITHUB_ACTIONS.bat").read_text(encoding="utf-8", errors="replace")
        for command in ("plan", "dispatch --go", "status", "finalize --execute", "hygiene"):
            self.assertIn(command, sh)
            self.assertIn(command, bat)


class Packaging(unittest.TestCase):
    def test_the_release_gate_ships_launchers_and_the_helper(self):
        import make_release
        names = {p.name for p in make_release.members()}
        for name in ("MONITOR_GITHUB_ACTIONS.sh", "BATCH_GITHUB_ACTIONS.command", "platform_compat.py", "MONITOR_GITHUB_ACTIONS.bat"):
            self.assertIn(name, names)


class SourcesStayPortable(unittest.TestCase):
    def test_no_tool_hardcodes_the_windows_python_launcher_for_children(self):
        text = (HERE / "gha_dispatch_all.py").read_text(encoding="utf-8")
        self.assertNotIn('cmd = ["py", "-3"', text)

    def test_finalize_command_starts_with_the_platform_python(self):
        import gha_dispatch_all
        name = next(iter(gha_dispatch_all.TARGETS))
        argv = gha_dispatch_all.finalize_command(name, 123)
        self.assertEqual(argv[:len(platform_compat.python_argv())], platform_compat.python_argv())


if __name__ == "__main__":
    unittest.main()
