# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Where the workspace lives (OPTIONAL): the folder that holds local clones of the repositories, with the local signing records and audit files.

Resolution order (first that gives a folder wins), so the tools can be copied to another PC or path without editing code:
  1. the environment variable MONITOR_ROOT, and MONITOR_AUDIT_DIR / MONITOR_SIGNED_DIR for the audit and signing folders;
  2. "workspace_root" / "audit_dir" / "signed_dir" in actions_monitor.json next to this file;
  3. the first parent of this file that holds a file named .monitor-root.

Several workspaces (OPTIONAL, `workspaces.list` and `workspaces.active`, off while the list is empty): the list holds `name=folder` entries and `workspaces.active` names the one in use, so a second set
of clones (another organisation, another machine's copy) is chosen by changing one word instead of editing paths. The active workspace wins over `workspace_root`, and the environment variable wins over both.

Without a workspace the monitor still runs, in a reduced mode that shows only what the GitHub API gives (no local signing queue, no audit report, no
CHANGELOG scan) and says so on the page; only the batch tools (plan, dispatch, hygiene) need the clones.

Inside the workspace the signing records are in `<root>/_signed` and the audit files in `<root>/_audit`. Set "signed_dir" / "audit_dir" in actions_monitor.json
(or MONITOR_SIGNED_DIR / MONITOR_AUDIT_DIR) to put them anywhere.
"""
import json
import os
import re
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
        own = paths.config_file() if Path(HERE).resolve() == paths.ROOT.resolve() else paths.place("actions_monitor.json", HERE)      # HERE is the product folder (the tests point it elsewhere)
        value = json.loads(own.read_text(encoding="utf-8")).get(key)
    except (OSError, ValueError):
        return None
    return Path(value) if value else None


WS_ENTRY = re.compile(r"^([A-Za-z0-9._-]{1,40})=(?!\\\\|//)(?!.*://)([^\x00-\x1f]{1,255})\Z")      # name=folder on this computer (never a network address)


def _raw_config():
    try:
        own = paths.config_file() if Path(HERE).resolve() == paths.ROOT.resolve() else paths.place("actions_monitor.json", HERE)
        data = json.loads(own.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def named_workspaces(config=None):
    """{name: Path} of `workspaces.list` (an entry that is not `name=folder` is left out; the first of a repeated name wins)."""
    config = _raw_config() if config is None else config
    block = config.get("workspaces") if isinstance(config.get("workspaces"), dict) else {}
    out = {}
    for item in block.get("list") or [] if isinstance(block.get("list"), list) else []:
        match = WS_ENTRY.match(item) if isinstance(item, str) else None
        if match and match.group(1) not in out:
            out[match.group(1)] = Path(match.group(2).strip())
    return out


def active_workspace(config=None):
    """(name, Path) of the workspace `workspaces.active` names, or None (nothing named, or a name that is not in the list)."""
    config = _raw_config() if config is None else config
    block = config.get("workspaces") if isinstance(config.get("workspaces"), dict) else {}
    name = block.get("active") if isinstance(block.get("active"), str) else ""
    found = named_workspaces(config)
    return (name, found[name]) if name in found else None


def describe(config=None):
    """What the toolbox prints: every workspace, whether its folder exists, and which one is in use."""
    config = _raw_config() if config is None else config
    active = active_workspace(config)
    return {"active": active[0] if active else "", "workspaces": [{"name": n, "folder_exists": p.is_dir(), "active": bool(active) and active[0] == n} for n, p in sorted(named_workspaces(config).items())]}


def workspace_root():
    """The folder with the repositories. Stops with a clear message when it cannot be found."""
    env = _env("MONITOR_ROOT", "JUANENRAC_ROOT")
    if env:
        return env
    chosen = active_workspace()
    if chosen:
        return chosen[1]
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
