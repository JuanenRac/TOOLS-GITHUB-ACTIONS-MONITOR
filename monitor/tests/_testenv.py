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
# The four folders of the whole run (configuration, data, logs and AI) are a temporary folder: a test that writes the log of actions, the lessons of the AI, the key of a screen or the settings (the real paths) leaves nothing next to the code. A test that wants a place of its own
# sets its own variable (tests/test_183_root_layout.py).
import atexit  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402

if not any(os.environ.get(name) for name in ("MONITOR_LOGS_DIR", "MONITOR_AI_DIR", "MONITOR_DATA_DIR", "MONITOR_CONFIG_DIR")):
    _SUITE_DIR = tempfile.mkdtemp(prefix="ghamon_suite_")
    atexit.register(shutil.rmtree, _SUITE_DIR, True)
    os.environ["MONITOR_LOGS_DIR"] = os.path.join(_SUITE_DIR, "logs")
    os.environ["MONITOR_AI_DIR"] = os.path.join(_SUITE_DIR, "ai")
    os.environ["MONITOR_DATA_DIR"] = os.path.join(_SUITE_DIR, "data")
    os.environ["MONITOR_CONFIG_DIR"] = os.path.join(_SUITE_DIR, "config")
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
from github_actions_monitor.data_pipeline import redrule as _redrule  # noqa: E402

_redrule.DEFAULT_RED_AGE_DAYS = 0      # the same for the aging of a red (ci.red_age_days): a test asks for it when it wants it
_redrule.DEFAULT_INACTIVE_DAYS = 0      # the fixtures of the tests carry fixed dates of the past: no workflow of a test is "abandoned" unless the test asks for it (ci.inactive_days)
_redrule.POLICY["inactive_days"] = 0
_redrule.POLICY["red_age_days"] = 0
toolconfig.set_owner("JuanenRac")


WATCHED = ("actions_monitor.json", "actions_monitor_lite.json", "update_check.json", "update_check_lite.json", "actions_monitor_log.txt", "actions_monitor_log_lite.txt",
           "github_actions_log.jsonl", "ai_actions_log.jsonl", "collab_state.json", "security_state.json", "supply_state.json", "alert_mutes.json")


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


def isolated_env(case, **extra):
    """The environment for a process a test starts: its configuration, data, logs and AI folders are a temporary folder of its own (removed when the test is over), so that the process neither reads what an
    earlier run or a person left next to the code (a first start that says what it copied) nor writes anything there. `extra` adds or replaces variables."""
    import tempfile
    tmp = tempfile.TemporaryDirectory(prefix="ghamon_env_")
    case.addCleanup(tmp.cleanup)
    base = Path(tmp.name)
    env = dict(os.environ)
    for name in ("MONITOR_CONFIG", "MONITOR_PATHS_FILE"):
        env.pop(name, None)
    env.update({"MONITOR_CONFIG_DIR": str(base / "config"), "MONITOR_DATA_DIR": str(base / "data"), "MONITOR_LOGS_DIR": str(base / "logs"), "MONITOR_AI_DIR": str(base / "ai")})
    env.update(extra)
    return env


def files_next_to_the_code():
    """Every file under the product folder (the folders of bytecode and of git left out): what the suite must not add to."""
    found = set()
    for folder, dirs, names in os.walk(Path(__file__).resolve().parent.parent):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        found.update(os.path.relpath(os.path.join(folder, n), Path(__file__).resolve().parent.parent) for n in names if not n.endswith(".pyc"))
    return found


FILES_AT_START = files_next_to_the_code()      # taken when the first test module is imported: the files that were there before any test ran


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
