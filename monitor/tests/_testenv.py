# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Imported first by every test module: the tests run in English and as the same GitHub owner whatever the system language and the logged-in account are.
A test that checks another language switches it with `with i18n.use_language("es"):` (see tests/test_i18n.py)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))      # the importable package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))     # make_release.py and migrate_layout.py are scripts of the product folder, not part of the package
os.environ["MONITOR_TARGETS_FILE"] = str(Path(__file__).resolve().parent / "fixtures" / "fixture_targets.json")          # the maintainer's catalogue, whatever the configuration says
os.environ["MONITOR_ECOSYSTEMS_FILE"] = str(Path(__file__).resolve().parent / "fixtures" / "fixture_ecosystems.json")
os.environ["MONITOR_PROFILES_FILE"] = str(Path(__file__).resolve().parent / "fixtures" / "fixture_profiles.json")
os.environ["MONITOR_TIMEZONE"] = "utc"      # texts for people in UTC unless a test asks for another zone (tests/test_timezone.py)
from github_actions_monitor import i18n  # noqa: E402
from github_actions_monitor.app import toolconfig  # noqa: E402

# HERMETIC: no test may depend on a `gh` that is installed and logged in (the runners of the CI have none, or one without a login that takes tens of seconds to answer). Every `gh` this process starts
# is replaced by a program that fails at once with a controlled message; a test that needs another answer mocks `subprocess.run` or the reader itself, which wins over this. The token variables are emptied.
import subprocess  # noqa: E402

os.environ.pop("GH_TOKEN", None)
os.environ.pop("GITHUB_TOKEN", None)
_RealPopen = subprocess.Popen


class _NoGhPopen(_RealPopen):
    def __init__(self, args, *more, **kwargs):
        first = args[0] if isinstance(args, (list, tuple)) and args else None
        if first == "gh" or (isinstance(first, str) and os.path.basename(first).lower() in ("gh", "gh.exe")):
            args = [sys.executable, "-c", "import sys; sys.stderr.write('gh: not logged in (hermetic test)'); sys.exit(4)"]
        super().__init__(args, *more, **kwargs)


subprocess.Popen = _NoGhPopen

i18n.set_language("en")
toolconfig.set_owner("JuanenRac")


WATCHED = ("actions_monitor.json", "actions_monitor_lite.json", "update_check.json", "update_check_lite.json", "actions_monitor_log.txt", "actions_monitor_log_lite.txt",
           "github_actions_log.jsonl", "ai_actions_log.jsonl", "collab_state.json", "alert_mutes.json")


def guard(case):
    """Registers a cleanup on a TestCase: the files of the monitor that this test creates in its folders (config/, data/, logs/) (the template of a first start, the update notice) are removed afterwards. Only
    what did not exist before is removed."""
    from github_actions_monitor.util import paths
    before = {name for name in WATCHED if paths.place(name).exists()}

    def remove_new():
        for name in WATCHED:
            if name not in before:
                try:
                    paths.place(name).unlink()
                except OSError:
                    pass
    case.addCleanup(remove_new)
    return remove_new


import unittest  # noqa: E402


class Spanish:
    """Mixin for the test classes whose expectations are the Spanish texts: `class X(_testenv.Spanish, unittest.TestCase)`."""

    def setUp(self):
        super().setUp()
        i18n.set_language("es")

    def tearDown(self):
        i18n.set_language("en")
        super().tearDown()


PRODUCT = Path(__file__).resolve().parent.parent          # the product folder (launchers, src/, assets/, docs/, tests/, tools/)
PACKAGE = PRODUCT / "src" / "github_actions_monitor"


def source_files():
    """Every .py of the package (src/github_actions_monitor/**) plus tools/make_release.py: what the static checks of the tests read."""
    return sorted(p for p in PACKAGE.rglob("*.py") if "__pycache__" not in p.parts) + [PRODUCT / "tools" / "make_release.py"]


def module_file(name):
    """The file of a module by its old flat name ("sentinel_local" or "sentinel_local.py")."""
    stem = name[:-3] if name.endswith(".py") else name
    found = [p for p in source_files() if p.stem == stem or (stem == "i18n" and p.parent.name == "i18n" and p.name == "__init__.py")]
    if not found:
        raise FileNotFoundError(name)
    return found[0]
