# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Accounts of the complete edition: several GitHub accounts (a person or an organisation) watched by one installation, each one isolated from the others.

The lite edition never imports this module: it watches one account and has no folder of accounts.

Layout (next to the monitor, or where MONITOR_ACCOUNTS_DIR points; `MONITOR_ROOT` is the folder of the clones of the repositories and is not touched):

    accounts/
      global.json                 optional: {"default_account": "personal", "enabled_accounts": ["personal", "org-acme"] or "all"}
      personal/                   one folder per account, the id is [a-z0-9_-]
        actions_monitor.json      the configuration of this account (its github_owner, repos, sentinel...)
        config_backups/  cache/  events/  analytics/  sentinel_state/  and the logs

Without an `accounts/` folder the monitor runs exactly as before, one account, with its files next to the code. `--migrate-accounts` shows what would move into `accounts/default/` and
`--migrate-accounts --apply` copies it (the originals stay where they are until you delete them yourself).
"""
import json
import os
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACCOUNT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
DEFAULT_ID = "default"
GLOBAL_NAME = "global.json"
CONFIG_NAME = "actions_monitor.json"
MARKER = ".migrated_from_root"
#: (module, attribute, path inside the folder of an account): where each state file of the monitor lives for one account
STATE_FILES = (
    ("actions_monitor", "LOG_FILE", "actions_monitor_log.txt"),
    ("etagcache", "CACHE_FILE", "cache/etag_cache.json"),
    ("events", "EVENTS_FILE", "events/events_monitor.jsonl"),
    ("events", "STATE_FILE", "events/events_state.json"),
    ("analytics", "HISTORY_FILE", "analytics/analytics_history.json"),
    ("ai_actions", "LOG_FILE", "ai_actions_log.jsonl"),
    ("ghactions", "LOG_FILE", "github_actions_log.jsonl"),
    ("sentinel_local", "CACHE_FILE", "sentinel_state/sentinel_cache.json"),
    ("sentinel_local", "HISTORY_FILE", "sentinel_state/sentinel_history.json"),
    ("sentinel_ai", "CACHE_FILE", "sentinel_state/sentinel_ai_cache.json"),
    ("sentinel_collab", "STATE_FILE", "sentinel_state/collab_state.json"),
    ("alert_center", "STATE_FILE", "alert_mutes.json"),
    ("updatecheck", "STATE_FILE", "update_check.json"),
)
#: files of the old layout (name next to the code) and where each one goes in the folder of an account; the lite edition's own files are not part of this
LEGACY = (
    ("actions_monitor.json", CONFIG_NAME), ("actions_monitor_log.txt", "actions_monitor_log.txt"), ("etag_cache.json", "cache/etag_cache.json"),
    ("events_monitor.jsonl", "events/events_monitor.jsonl"), ("events_state.json", "events/events_state.json"), ("analytics_history.json", "analytics/analytics_history.json"),
    ("ai_actions_log.jsonl", "ai_actions_log.jsonl"), ("github_actions_log.jsonl", "github_actions_log.jsonl"), ("sentinel_cache.json", "sentinel_state/sentinel_cache.json"),
    ("sentinel_history.json", "sentinel_state/sentinel_history.json"), ("sentinel_ai_cache.json", "sentinel_state/sentinel_ai_cache.json"), ("collab_state.json", "sentinel_state/collab_state.json"), ("alert_mutes.json", "alert_mutes.json"), ("update_check.json", "update_check.json"),
    ("degraded.json", "degraded.json"), ("welcome_state.json", "welcome_state.json"), ("orgs_state.json", "orgs_state.json"), ("config_backups", "config_backups"),
)


def valid_id(value):
    """True for an account id that is safe as a folder name: lower case letters, digits, `_` and `-`, up to 40 characters, never starting with a separator."""
    return isinstance(value, str) and bool(ACCOUNT_ID_RE.match(value))


def clean_id(value, fallback=DEFAULT_ID):
    """A valid id made from free text (an organisation name): lower case, anything else becomes `-`; `fallback` when nothing usable is left."""
    text = re.sub(r"[^a-z0-9_-]+", "-", str(value or "").strip().lower()).strip("-_")[:40].strip("-_")
    return text if valid_id(text) else fallback


def root_dir(base=None):
    """The folder `accounts/`: MONITOR_ACCOUNTS_DIR when it is set, else next to the monitor (`base`)."""
    env = os.environ.get("MONITOR_ACCOUNTS_DIR", "").strip()
    return Path(env) if env else Path(base or HERE) / "accounts"


def account_dir(account_id, base=None):
    """The folder of one account; raises ValueError for an id that is not safe, so a path can never leave `accounts/`."""
    if not valid_id(account_id):
        raise ValueError("account id")
    return root_dir(base) / account_id


def config_path(account_id, base=None):
    return account_dir(account_id, base) / CONFIG_NAME


def load_global(base=None):
    """{"default_account": str, "enabled_accounts": "all" | [ids]} from accounts/global.json, with the conservative default when it is missing or damaged."""
    out = {"default_account": "", "enabled_accounts": "all"}
    try:
        data = json.loads((root_dir(base) / GLOBAL_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return out
    if not isinstance(data, dict):
        return out
    if valid_id(data.get("default_account")):
        out["default_account"] = data["default_account"]
    wanted = data.get("enabled_accounts")
    if isinstance(wanted, list):
        out["enabled_accounts"] = [a for a in wanted if valid_id(a)][:100]
    return out


def list_accounts(base=None):
    """The ids of the accounts that exist: a valid folder name with a configuration file inside, sorted."""
    root = root_dir(base)
    try:
        names = [p.name for p in root.iterdir() if p.is_dir() and valid_id(p.name) and (p / CONFIG_NAME).is_file()]
    except OSError:
        return []
    return sorted(names)


def enabled_accounts(base=None):
    """The accounts that are switched on (`enabled_accounts` of global.json, default all), in order, keeping only those that exist."""
    existing, wanted = list_accounts(base), load_global(base)["enabled_accounts"]
    return existing if wanted == "all" else [a for a in wanted if a in existing]


def default_account(base=None):
    """The account used when none is asked for: `default_account` of global.json when it is enabled, else the first enabled one, else ''."""
    on, chosen = enabled_accounts(base), load_global(base)["default_account"]
    return chosen if chosen in on else (on[0] if on else "")


def layout(base=None):
    """'accounts' when the folder of accounts holds at least one account (the supervisor starts), else 'single' (the old layout, nothing changes)."""
    return "accounts" if list_accounts(base) else "single"


def create_account(account_id, owner="", base=None, example=None):
    """Creates accounts/<id>/ with a configuration made from the template of the package and `github_owner` set. Refuses an id that is not safe and never overwrites. Returns the path."""
    path = config_path(account_id, base)
    if path.exists():
        raise FileExistsError(account_id)
    template = Path(example) if example else HERE / "actions_monitor.example.json"
    try:
        data = json.loads(template.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data["github_owner"] = str(owner or "")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def migration_plan(base=None, source=None, account_id=DEFAULT_ID):
    """What `--migrate-accounts` would do: [(from, to, kind)] for every file of the old layout that exists next to the code, copied into accounts/<id>/. Nothing is written.
    Refuses (returns []) when that account already exists, so a second run never mixes two states."""
    source = Path(source or base or HERE)
    target = account_dir(account_id, base)
    if (target / CONFIG_NAME).exists() or (target / MARKER).exists():
        return []
    return [(source / old, target / new, "folder" if (source / old).is_dir() else "file") for old, new in LEGACY if (source / old).exists()]


def migrate(base=None, source=None, account_id=DEFAULT_ID, apply=False):
    """Copies the old layout into accounts/<id>/ (a dry run unless `apply`). The originals are never moved or deleted: whoever runs this deletes them after checking. A marker file records
    where the copy came from. Returns {"applied", "items": [(from, to, kind)], "copied": n, "problems": [..]}; each copy is checked by size before it counts."""
    items = migration_plan(base, source, account_id)
    out = {"applied": bool(apply and items), "items": [(str(a), str(b), kind) for a, b, kind in items], "copied": 0, "problems": []}
    if not apply or not items:
        return out
    target = account_dir(account_id, base)
    for src, dst, kind in items:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if kind == "folder":
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
                if dst.stat().st_size != src.stat().st_size:
                    raise OSError("size differs")
            out["copied"] += 1
        except OSError as error:
            out["problems"].append(f"{src.name}: {str(error)[:80]}")
    (target / MARKER).write_text(json.dumps({"from": str(Path(source or base or HERE)), "copied": out["copied"]}), encoding="utf-8")
    return out
