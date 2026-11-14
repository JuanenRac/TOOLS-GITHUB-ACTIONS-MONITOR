# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Where things are, in one place (standard library only).

  ROOT      the product folder: the one that holds the launchers, README, docs/, tests/ and src/. Next to the launchers there is NOTHING else but the folders below.
  SRC       ROOT/src, the folder that holds the importable package.
  PACKAGE   the package itself.
  ASSETS    ROOT/assets: what travels with the product and is not code: examples/ (the neutral *.example.json and quotas.json), static/ (the page) and locales/ (the 8 languages).
  DOCS      ROOT/docs.
  BIN       ROOT/bin: the short command-line entry points (read_report.py, monitor_cli.py, ai_hook.py ...).

The files of the person who runs the monitor live in four folders (never inside src/ and never under assets/); `kind_of(name)` says which one a file belongs to and `place(name)` gives its path:

  config/    actions_monitor.json, actions_monitor_lite.json, targets.json, ecosystems.json, profiles.json, quotas.json and config_backups/
  data/      the state and the caches (events, analytics, sentinel state, ETag cache, update check, ...), the folder of the accounts (accounts/) and the keys of the service
  logs/      the log of the monitor, the log of the commands of the AI and of GitHub, the audit of the team mode
  ai/        what an AI reads: ALERTS_BRIEF.md, ai_alerts.jsonl, the state of the hook, ci_red.json, INDEX.json and a README that explains each file

Each folder can be placed elsewhere without touching the code: the environment variables MONITOR_CONFIG_DIR, MONITOR_DATA_DIR, MONITOR_LOGS_DIR and MONITOR_AI_DIR, or the file
`config/paths.json` ({"data": "...", "logs": "...", "ai": "..."}; a relative path starts at the product folder). With MONITOR_DATA_DIR alone, logs and ai become
<data>/logs and <data>/ai (a container with two volumes: /config and /data).
"""
import json
import os
import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SRC = PACKAGE.parent
ROOT = SRC.parent
ASSETS = ROOT / "assets"
EXAMPLES = ASSETS / "examples"
STATIC = ASSETS / "static"
LOCALES = ASSETS / "locales"
DOCS = ROOT / "docs"
BIN = ROOT / "bin"

KINDS = ("config", "data", "logs", "ai")
PATHS_FILE_NAME = "paths.json"
#: (kind, regular expression of the name without the `_lite` / `_demo` mark): the first line that matches wins. The same table drives the code, the migration and the doctor.
_RULES = (
    ("config", r"actions_monitor\.json|targets\.json|ecosystems\.json|profiles\.json|quotas\.json|config_backups|paths\.json"),
    ("ai", r"ALERTS_BRIEF\.md|ai_alerts\.jsonl|ai_alerts_state\.json|ai_heartbeat\.json|ai_hook_state\.json|ai_notify\.jsonl|ai_notify_state\.json|ci_red\.json|INDEX\.json"),
    ("logs", r"actions_monitor_log\.txt|ai_actions_log\.jsonl|github_actions_log\.jsonl|auth_audit\.jsonl|loop\.log"),
    ("data", r"etag_cache\.json|events_monitor\.jsonl|events_state\.json|eventos_monitor\.jsonl|eventos_estado\.json|analytics_history\.json|sentinel_cache\.json|sentinel_history\.json|"
             r"sentinel_ai_cache\.json|collab_state\.json|alert_mutes\.json|update_check\.json|welcome_state\.json|orgs_state\.json|degraded\.json|targets\.candidates\.json|"
             r"storage\.sqlite3|access_token|credential|accounts|state|secrets|_global|_no_workspace"),
)
_COMPILED = tuple((kind, re.compile(r"^(?:" + body + r")\Z")) for kind, body in _RULES)
_VARIANT = re.compile(r"_(lite|demo)(?=\.|$)")


def _bootstrap():
    """{kind: text} from config/paths.json (next to the code, or MONITOR_PATHS_FILE); {} when there is none or it is damaged."""
    chosen = os.environ.get("MONITOR_PATHS_FILE", "").strip()
    try:
        data = json.loads((Path(chosen) if chosen else _own("config") / PATHS_FILE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v.strip() for k, v in data.items() if k in KINDS and isinstance(v, str) and v.strip()}


def _own(kind, base=None):
    """The folder of `kind` in the product folder (or in `base`) with no override."""
    return Path(base or ROOT) / kind


def folder(kind, base=None):
    """The folder of one of the KINDS. `base` (tests, a second installation) always gives <base>/<kind>; without it the environment and config/paths.json can place it elsewhere."""
    if kind not in KINDS:
        raise ValueError(kind)
    if base and Path(base).resolve() != ROOT.resolve():
        return _own(kind, base)
    chosen = os.environ.get(f"MONITOR_{kind.upper()}_DIR", "").strip()
    if not chosen and kind != "config":
        chosen = _bootstrap().get(kind, "")
        data = os.environ.get("MONITOR_DATA_DIR", "").strip()
        if not chosen and data and kind != "data":
            return Path(data) / kind
    if not chosen:
        return _own(kind)
    path = Path(chosen)
    return path if path.is_absolute() else ROOT / path


def kind_of(name):
    """'config', 'data', 'logs' or 'ai' for the NAME of a file or folder of the monitor (the `_lite` and `_demo` variants count as the file they vary); None when it is not one of its own."""
    plain = _VARIANT.sub("", str(name))
    for kind, rule in _COMPILED:
        if rule.match(plain):
            return kind
    return None


def place(name, base=None):
    """Where the file or folder called `name` lives now. A name the monitor does not know goes to data/."""
    return folder(kind_of(name) or "data", base) / name


def config_file():
    """The configuration file of the monitor: `MONITOR_CONFIG` when it is set (a container keeps it in a volume of its own, apart from the code), else config/actions_monitor.json."""
    chosen = os.environ.get("MONITOR_CONFIG", "").strip()
    return Path(chosen) if chosen else place("actions_monitor.json")


def describe(base=None):
    """The folders in use, for the page, `/api/paths`, the doctor and ai/INDEX.json: {kind: absolute path}, the product folder and the configuration file."""
    out = {kind: str(folder(kind, base).resolve()) for kind in KINDS}
    out["root"] = str(Path(base or ROOT).resolve())
    out["config_file"] = str((place("actions_monitor.json", base) if base else config_file()).resolve())
    return out


def is_own(path):
    """True when `path` lies inside config/, data/, logs/ or ai/ of this installation: the monitor may make the folders on the way to it (a fresh install has none yet)."""
    try:
        target = Path(path).resolve()
        return any(target.is_relative_to(folder(kind).resolve()) for kind in KINDS)
    except (OSError, ValueError):
        return False


def ensure(base=None):
    """Creates the folders config/, data/, logs/ and ai/ when they are missing (a fresh install has none). Returns the list of folders that exist afterwards; a folder that cannot be made is skipped."""
    made = []
    for kind in KINDS:
        target = folder(kind, base)
        try:
            target.mkdir(parents=True, exist_ok=True)
            made.append(target)
        except OSError:
            continue
    return made
