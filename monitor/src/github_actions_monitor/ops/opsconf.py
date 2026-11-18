# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The `ops` block of the configuration, read the way every other block is: anything missing, of the wrong type or out of range reads as the (conservative) default, so a hand-edited value can never
switch a safeguard off by accident.

    ops.backup.enabled          false   the scheduled copy; a copy made by hand works whatever this says
    ops.backup.dir              backups the folder of the copies (relative to the data folder; an absolute path only when it is written on purpose)
    ops.backup.interval_hours   24      [1, 720]
    ops.backup.keep             7       [1, 365] copies kept; the older ones of the same kind are removed
    ops.backup.include_config   true    the settings and lists of the installation travel in the package, cleaned of every secret
    ops.backup.compress_level   6       [0, 9]
    ops.backup.encrypt          false   seal the package with a key taken from the variable named in ops.backup.key_env (refused, never faked, without the optional library)
    ops.backup.key_env          ""      the NAME of that variable (the key itself is never a setting)
    ops.purge.enabled           false   the "purge now" route exists only when this is on
    ops.purge.require_backup_hours 24   [0, 720] a purge on demand is refused without a good copy newer than this (0 = not asked)
    ops.doctor.strict_exit      false   warnings give exit code 3
    ops.doctor.backup_max_age_days 8    [1, 365]
    ops.doctor.min_free_mb      500     [50, 10000000]
    ops.doctor.sqlite_check     quick   quick | deep | off
    ops.doctor.sqlite_timeout_s 20      [1, 600]
    ops.doctor.webhook_min_length 16    [8, 128] (only the LENGTH of the secret is compared; the secret is never shown)
"""
import re

from github_actions_monitor.util import paths

DEFAULTS = {
    "backup": {"enabled": False, "dir": "backups", "interval_hours": 24, "keep": 7, "include_config": True, "compress_level": 6, "encrypt": False, "key_env": ""},
    "purge": {"enabled": False, "require_backup_hours": 24},
    "doctor": {"strict_exit": False, "backup_max_age_days": 8, "min_free_mb": 500, "sqlite_check": "quick", "sqlite_timeout_s": 20, "webhook_min_length": 16},
}
BOUNDS = {"interval_hours": (1, 720), "keep": (1, 365), "compress_level": (0, 9), "require_backup_hours": (0, 720), "backup_max_age_days": (1, 365), "min_free_mb": (50, 10000000),
          "sqlite_timeout_s": (1, 600), "webhook_min_length": (8, 128)}
SQLITE_CHECKS = ("quick", "deep", "off")
#: the name of the variable that holds the key of a sealed package: never one the monitor or GitHub itself reads
KEY_ENV_RE = re.compile(r"^(?!(?:GH_TOKEN|GITHUB_TOKEN|GITHUB_PAT|PATH|HOME|USERPROFILE|SYSTEMROOT|TEMP|TMP|APPDATA|LOCALAPPDATA|PYTHONPATH|MONITOR_[A-Z0-9_]*)\Z)([A-Z_][A-Z0-9_]{0,63})?\Z")
DIR_RE = re.compile(r"^[^\x00-\x1f]{1,300}\Z")


def clean_dir(value):
    """The folder as text, or '' when it cannot be trusted: control characters, a network (UNC) path, the D: drive of the owner, or a relative path that climbs out with `..`."""
    if not isinstance(value, str) or not DIR_RE.match(value.strip()):
        return ""
    text = value.strip()
    if text.startswith(("\\\\", "//")) or re.match(r"^(?:[Dd]:|/mnt/[dD](?:/|$))", text):
        return ""
    if not (text.startswith("/") or re.match(r"^[A-Za-z]:", text)) and ".." in re.split(r"[\\/]+", text):
        return ""
    return text


def settings(config):
    """The three blocks as clean values: {"backup": {...}, "purge": {...}, "doctor": {...}}."""
    block = config.get("ops") if isinstance(config, dict) and isinstance(config.get("ops"), dict) else {}
    out = {name: dict(values) for name, values in DEFAULTS.items()}
    for name, values in out.items():
        given = block.get(name) if isinstance(block.get(name), dict) else {}
        for key, default in DEFAULTS[name].items():
            value = given.get(key)
            if isinstance(default, bool):
                if isinstance(value, bool):
                    values[key] = value
            elif key in BOUNDS:
                if isinstance(value, (int, float)) and not isinstance(value, bool) and BOUNDS[key][0] <= value <= BOUNDS[key][1]:
                    values[key] = int(value)
            elif key == "sqlite_check":
                if value in SQLITE_CHECKS:
                    values[key] = value
            elif key == "key_env":
                if isinstance(value, str) and value and KEY_ENV_RE.match(value):
                    values[key] = value
            elif key == "dir":
                if clean_dir(value):
                    values[key] = clean_dir(value)
    return out


def ops_dir(folder=None):
    """Where the operations leave their small files (the state of the last copy, the report of the last restore): data/ops/."""
    return paths.folder("data", folder) / "ops"


def backup_dir(config, folder=None):
    """The folder of the copies: relative paths start at the data folder of the installation."""
    from pathlib import Path
    chosen = settings(config)["backup"]["dir"]
    path = Path(chosen)
    return path if path.is_absolute() or re.match(r"^[A-Za-z]:", chosen) else paths.folder("data", folder) / path
