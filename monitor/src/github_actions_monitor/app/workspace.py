# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Where the workspace lives (OPTIONAL): the folder that holds local clones of the repositories, with the local signing records and audit files.

Resolution order (first that gives a folder wins), so the tools can be copied to another PC or path without editing code:
  1. the environment variable MONITOR_ROOT, and MONITOR_AUDIT_DIR / MONITOR_SIGNED_DIR for the audit and signing folders;
  2. "workspace_root" / "audit_dir" / "signed_dir" in actions_monitor.json next to this file;
  3. the first parent of this file that holds a file named .monitor-root.

Without a workspace the monitor still runs, in a reduced mode that shows only what the GitHub API gives (no local signing queue, no audit report, no
CHANGELOG scan) and says so on the page; only the batch tools (plan, dispatch, hygiene) need the clones.

Inside the workspace the signing records are in `<root>/_signed` and the audit files in `<root>/_audit`. Set "signed_dir" / "audit_dir" in actions_monitor.json
(or MONITOR_SIGNED_DIR / MONITOR_AUDIT_DIR) to put them anywhere.
"""
import json
import os
from pathlib import Path

from github_actions_monitor import i18n
from github_actions_monitor.util import paths

from github_actions_monitor.util.paths import ROOT as HERE   # the product folder: the data of the person who runs the monitor stays there
MARKERS = (".monitor-root",)


def _env(*names):
    for name in names:
        value = os.environ.get(name)
        if value:
            return Path(value)
    return None


def _config(key):
    try:
        value = json.loads(paths.config_file().read_text(encoding="utf-8")).get(key)
    except (OSError, ValueError):
        return None
    return Path(value) if value else None


def workspace_root():
    """The folder with the repositories. Stops with a clear message when it cannot be found."""
    env = _env("MONITOR_ROOT", "JUANENRAC_ROOT")
    if env:
        return env
    configured = _config("workspace_root")
    if configured:
        return configured
    for parent in HERE.parents:
        if any((parent / marker).is_file() for marker in MARKERS):
            return parent
    raise SystemExit(i18n.t("ws.not_found"))


def audit_dir():
    """The folder with the audit files (it may not exist yet; callers check)."""
    env = _env("MONITOR_AUDIT_DIR", "JUANENRAC_AUDIT_DIR")
    if env:
        return env
    configured = _config("audit_dir")
    if configured:
        return configured
    root = workspace_root()
    return root / "_audit"


def signed_dir():
    """The folder with the local signing records (batches/*.json and <REPO>/release-<version>/). May not exist."""
    env = _env("MONITOR_SIGNED_DIR", "JUANENRAC_SIGNED_DIR")
    if env:
        return env
    configured = _config("signed_dir")
    if configured:
        return configured
    root = workspace_root()
    return root / "_signed"


def signed_dir_soft():
    try:
        return signed_dir()
    except SystemExit:
        return HERE / "_no_workspace" / "_signed"


def tools_dir():
    """The folder with the local signing tools that the targets name (`tool` in the targets file). MONITOR_TOOLS_DIR > "tools_dir" in actions_monitor.json > <this folder>/tools.
    It may not exist: a target whose tool is missing is reported by the validation, never run."""
    env = _env("MONITOR_TOOLS_DIR")
    if env:
        return Path(env)
    configured = _config("tools_dir")
    if configured:
        return Path(configured)
    return HERE / "tools"


def has_workspace():
    """True when a workspace folder exists. False = the monitor runs in reduced mode (GitHub API data only)."""
    return workspace_root_soft().is_dir()


def workspace_root_soft():
    """Like workspace_root() but never stops: when the workspace cannot be found it returns a folder that does not exist
    (HERE/_no_workspace), so a module can be imported (and its pure functions tested) anywhere. The entry points call
    workspace_root() once at start to fail with the clear message."""
    try:
        return workspace_root()
    except SystemExit:
        return HERE / "_no_workspace"


def audit_dir_soft():
    try:
        return audit_dir()
    except SystemExit:
        return HERE / "_no_workspace" / "_audit"


def available():
    """True when the workspace can be found (integration tests skip themselves otherwise)."""
    try:
        workspace_root()
        return True
    except SystemExit:
        return False
