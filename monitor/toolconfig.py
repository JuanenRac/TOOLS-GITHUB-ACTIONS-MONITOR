# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Settings shared by every tool of the package, read from actions_monitor.json (next to this file) and from the data files it names.

One place for what used to be constants scattered over the modules:

  github_owner     the GitHub account whose repositories are watched. Default: the login of `gh api user` (asked once, only when a tool
                   needs it; never in the hot cycle).
  language         one of i18n.LANGS; default: the language of the system, English when that one is not supported (see i18n.py).
  ecosystems_file  JSON with the ecosystems (repository prefixes, label, signing tool): default ecosystems.json; ecosystems.example.json is neutral.
  targets_file     JSON with the catalogue of build targets: default targets.json; targets.example.json is neutral.
  profiles_file    JSON with the batch profiles: default profiles.json; profiles.example.json is neutral.
                   (A default file that does not exist is replaced by its neutral .example.json.)
                   (MONITOR_ECOSYSTEMS_FILE / MONITOR_TARGETS_FILE in the environment win over the configuration.)

Nothing here talks to the network except the single `gh api user` lookup, and nothing is written. The tests (or a caller) can pin a value with
set_owner() / set_ecosystems().
"""
import json
import os
import subprocess
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG_FILE = HERE / "actions_monitor.json"
DEFAULT_ECOSYSTEMS_FILE = "ecosystems.json"
DEFAULT_TARGETS_FILE = "targets.json"
DEFAULT_PROFILES_FILE = "profiles.json"

_lock = threading.Lock()
_owner = {"pinned": None, "lookup": None}
_ecosystems_override = {"value": None}
_raw_cache = {"at": 0.0, "value": {}}


def raw_config():
    """The content of actions_monitor.json as a dict ({} when it is missing or broken), cached for a few seconds."""
    now = time.time()
    with _lock:
        if now - _raw_cache["at"] < 5 and _raw_cache["at"]:
            return _raw_cache["value"]
    value = {}
    for path in (CONFIG_FILE, HERE / "actions_monitor.example.json"):   # before the first start the template is what counts
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            value = value if isinstance(value, dict) else {}
            break
        except (OSError, ValueError):
            continue
    with _lock:
        _raw_cache.update({"at": now, "value": value})
    return value


def forget():
    """Drops the cached configuration and the owner lookup (used by the tests and after a configuration change). A pinned owner (set_owner) stays pinned."""
    with _lock:
        _raw_cache.update({"at": 0.0, "value": {}})
        _owner.update({"lookup": None})
        _ecosystems_override["value"] = None


def set_owner(name):
    """Pins the owner (None releases the pin)."""
    _owner["pinned"] = name or None


def github_owner(config=None):
    """The GitHub account being watched: set_owner() > config `github_owner` > the login of `gh api user` (looked up once) > "" if unknown."""
    if _owner["pinned"]:
        return _owner["pinned"]
    value = (config if config is not None else raw_config()).get("github_owner")
    if isinstance(value, str) and value.strip():
        return value.strip()
    if _owner["lookup"] is None:
        login = ""
        try:
            import secretstore
            done = subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True, encoding="utf-8", timeout=30, **secretstore.gh_kwargs())
            if done.returncode == 0:
                login = done.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        _owner["lookup"] = login
    return _owner["lookup"]


def language(config=None):
    value = (config if config is not None else raw_config()).get("language")
    return value if isinstance(value, str) else ""


def _read_json(name, default):
    path = Path(name)
    if not path.is_absolute():
        path = HERE / path
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else default
    except (OSError, ValueError):
        return default


def _data_path(env_name, key, default, config=None):
    """The data file named by the environment (wins; the tests use it), else by `key` in actions_monitor.json, else `default` next to this file.
    When the default does not exist the neutral <name>.example.json of the package is used, so a fresh install works without any file of its own."""
    value = os.environ.get(env_name) or (config if config is not None else raw_config()).get(key)
    explicit = isinstance(value, str) and bool(value.strip())
    path = Path(value if explicit else default)
    path = path if path.is_absolute() else HERE / path
    if not explicit and not path.is_file():
        example = path.with_name(path.stem + ".example" + path.suffix)
        if example.is_file():
            return example
    return path


CATALOG_FILES = (("ecosystems_file", DEFAULT_ECOSYSTEMS_FILE), ("targets_file", DEFAULT_TARGETS_FILE), ("profiles_file", DEFAULT_PROFILES_FILE))


def catalog_in_example(config=None):
    """The default catalogue files that do not exist (and are not replaced by a file named in the configuration): those run on their neutral .example.json."""
    cfg = config if config is not None else raw_config()
    return [name for key, name in CATALOG_FILES if not cfg.get(key) and not (HERE / name).is_file() and (HERE / name.replace(".json", ".example.json")).is_file()]


def init_catalog():
    """Copies each neutral .example.json to the default name when that file is missing. Returns [(name, created)]."""
    out = []
    for _key, name in CATALOG_FILES:
        target, example = HERE / name, HERE / name.replace(".json", ".example.json")
        if target.is_file():
            out.append((name, False))
        elif example.is_file():
            target.write_bytes(example.read_bytes())
            out.append((name, True))
    return out


def targets_path(config=None):
    return _data_path("MONITOR_TARGETS_FILE", "targets_file", DEFAULT_TARGETS_FILE, config)


def profiles_path(config=None):
    """The batch profiles: MONITOR_PROFILES_FILE > "profiles_file" in actions_monitor.json > profiles.json (or the neutral profiles.example.json)."""
    return _data_path("MONITOR_PROFILES_FILE", "profiles_file", DEFAULT_PROFILES_FILE, config)


def set_ecosystems(value):
    """Pins the ecosystem table (a dict like the "ecosystems" block of ecosystems.json); None releases it."""
    _ecosystems_override["value"] = value


def ecosystems(config=None):
    """{name: {"label", "prefixes": [..], "tool", "firmware_tool", "firmware_extra", "external"}} in file order. {} when there is no file.

    `external` marks an ecosystem that is only reported (never dispatched, signed or counted as a release candidate by this tool)."""
    if _ecosystems_override["value"] is not None:
        data = _ecosystems_override["value"]
    else:
        data = _read_json(_data_path("MONITOR_ECOSYSTEMS_FILE", "ecosystems_file", DEFAULT_ECOSYSTEMS_FILE, config), {}).get("ecosystems")
    out = {}
    for key, item in (data if isinstance(data, dict) else {}).items():
        if not isinstance(item, dict) or not isinstance(item.get("prefixes"), list):
            continue
        out[str(key)] = {"label": str(item.get("label") or key), "prefixes": [str(p) for p in item["prefixes"] if isinstance(p, str) and p],
                         "tool": item.get("tool") if isinstance(item.get("tool"), str) else "",
                         "firmware_tool": item.get("firmware_tool") if isinstance(item.get("firmware_tool"), str) else "",
                         "firmware_extra": [str(x) for x in item.get("firmware_extra") or [] if isinstance(x, str)],
                         "external": item.get("external") is True}
    return out


def ecosystem_names(config=None):
    return list(ecosystems(config))


def ecosystem_of(repo, config=None):
    """The ecosystem key of a repository name by prefix, or "other"."""
    for key, item in ecosystems(config).items():
        if any(p == "*" or str(repo).startswith(p) for p in item["prefixes"]):   # "*" = every repository
            return key
    return "other"


def is_ours(repo, config=None):
    """True when the repository belongs to an ecosystem of the file (external ones included)."""
    return ecosystem_of(repo, config) != "other"


def is_internal(repo, config=None):
    """True when the repository belongs to an ecosystem this tool dispatches, signs and counts as a release candidate (not an external one)."""
    key = ecosystem_of(repo, config)
    return key != "other" and not is_external(key, config)


def prime_owner(login):
    """Remembers the login that `gh api user` already gave at start, so no second lookup is made."""
    if login and _owner["lookup"] is None:
        _owner["lookup"] = str(login)


def is_external(key, config=None):
    return bool((ecosystems(config).get(key) or {}).get("external"))


def prefixes(config=None, internal_only=False):
    """All repository prefixes of the ecosystems (without the external ones when internal_only)."""
    return tuple(p for item in ecosystems(config).values() if not (internal_only and item["external"]) for p in item["prefixes"])


def label_of(key, config=None):
    return (ecosystems(config).get(key) or {}).get("label") or str(key)
