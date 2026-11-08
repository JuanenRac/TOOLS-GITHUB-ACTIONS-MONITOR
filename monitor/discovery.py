# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Automatic discovery and self-tuning, as small pure functions (the monitor calls them after each listing of the account; nothing here reads GitHub or writes a file).

  diff(previous, current)            events for a repository that appeared, vanished, was archived or unarchived: [{"code", "repo"}]
  lifecycle(items, rules)            drops archived / fork / empty / private repositories when the rules say so
  suggest_groups(unclassified, ...)  a prefix shared by three or more repositories that no group claims -> a suggested group; NEVER applied without a confirmation
  auto_frequency(...)                the hot / cold intervals the real activity asks for, inside the quota budget
  box(...)                           the "owner / watched / hidden" figures of the Basic tab
Settings (all in the `discovery` block of the configuration): events (on), suggest_groups (on), auto_frequency (off), hide (a list of fork, empty, private: repositories of that kind are left out;
archived repositories are always left out).
"""
import re

DEFAULTS = {"events": True, "suggest_groups": True, "auto_frequency": False, "hide": []}
EVENT_CODES = ("repo_new", "repo_gone", "repo_archived", "repo_unarchived")


def settings(config):
    block = config.get("discovery") if isinstance(config, dict) and isinstance(config.get("discovery"), dict) else {}
    out = {key: block.get(key, default) is True for key, default in DEFAULTS.items() if isinstance(default, bool)}
    hide = block.get("hide")
    out["hide"] = [w for w in hide if w in ("fork", "empty", "private")] if isinstance(hide, list) else []
    return out


def diff(previous, current):
    """`previous` and `current` are {name: {"archived": bool}} (or a plain list of names, taken as not archived). No previous listing means no news (the first look is not an event)."""
    def norm(value):
        if isinstance(value, dict):
            return {k: bool((v or {}).get("archived")) if isinstance(v, dict) else bool(v) for k, v in value.items()}
        return {name: False for name in (value or [])}
    before, now = norm(previous), norm(current)
    if not before:
        return []
    events = []
    for name in sorted(now.keys() - before.keys()):
        events.append({"code": "repo_archived" if now[name] else "repo_new", "repo": name})
    for name in sorted(before.keys() - now.keys()):
        events.append({"code": "repo_gone", "repo": name})
    for name in sorted(now.keys() & before.keys()):
        if now[name] != before[name]:
            events.append({"code": "repo_archived" if now[name] else "repo_unarchived", "repo": name})
    return events


def lifecycle(items, rules):
    """`items` is [{"name", "isArchived", "isFork", "isEmpty", "isPrivate"}]; returns the names that stay."""
    hide = settings({"discovery": rules})["hide"]
    keep = []
    for item in items:
        if item.get("isArchived") or ("fork" in hide and item.get("isFork")) or ("empty" in hide and item.get("isEmpty")) or ("private" in hide and item.get("isPrivate")):
            continue
        keep.append(item["name"])
    return keep


def suggest_groups(unclassified, minimum=3, taken=()):
    """[{"key", "prefix", "repos"}]: for each prefix (up to the 2nd or 3rd dash) shared by at least `minimum` repositories. The prefix 'xxx-' becomes the group 'xxx'."""
    found = {}
    for name in unclassified:
        parts = name.split("-")
        for size in (1, 2):
            if len(parts) > size:
                found.setdefault("-".join(parts[:size]) + "-", set()).add(name)
    out = []
    for prefix, names in sorted(found.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(names) < minimum or len(prefix) < 3:
            continue
        if any(prefix.startswith(other) and other != prefix and len(found.get(other, ())) == len(names) for other in found):
            continue        # the shorter prefix covers the same repositories
        key = re.sub(r"[^a-z0-9]+", "_", prefix.lower()).strip("_")
        if key and key not in taken:
            out.append({"key": key, "prefix": prefix, "repos": sorted(names)})
    return out[:5]


def auto_frequency(config, runs_last_24h, repos, calls_per_hour_budget):
    """(hot_seconds, cold_seconds): faster when the account is busy, slower when it is quiet, never above what the budget of calls per hour allows (the user's own values are the base and the floor)."""
    hot = int(config.get("refresh_seconds", 45))
    cold = int(config.get("cold_refresh_seconds", 600))
    busy = runs_last_24h / max(1, repos)
    if busy < 0.2:
        hot, cold = hot * 2, cold * 2
    elif busy > 3:
        hot = max(10, hot // 2)
    per_hour = 3600 / max(1, hot) * max(1, repos * 0.1) + 3600 / max(1, cold) * repos
    while per_hour > calls_per_hour_budget and cold < 86400:
        cold *= 2
        hot = hot * 2 if hot < 3600 else hot
        per_hour = 3600 / max(1, hot) * max(1, repos * 0.1) + 3600 / max(1, cold) * repos
    return max(10, min(3600, hot)), max(60, min(86400, cold))


def box(owner, watched, discovered, hidden_names):
    return {"owner": owner, "watched": watched, "discovered": discovered, "hidden": len(hidden_names), "hidden_names": list(hidden_names)[:50]}


KEY_RE = re.compile(r"^[a-z0-9_]{1,40}$")
PREFIX_RE = re.compile(r"^[A-Za-z0-9._-]{2,60}$")


def add_group(path, key, prefix, label=None, example=None, keep=5):
    """Adds the suggested group to the ecosystems file after a copy of it (config_backups next to it). Called only after the user's confirmation. `example` is the neutral
    template that is copied first when the user has no file of their own. Returns {"ok", "error", "file"}; the group goes before the catch-all one."""
    import json
    import os
    import shutil
    import time
    from pathlib import Path
    if not KEY_RE.match(str(key)) or not PREFIX_RE.match(str(prefix)):
        return {"ok": False, "error": "invalid"}
    path = Path(path)
    try:
        if not path.is_file() and example is not None and Path(example).is_file():
            shutil.copyfile(example, path)
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        if not isinstance(data, dict):
            return {"ok": False, "error": "unreadable"}
        groups = data.get("ecosystems") if isinstance(data.get("ecosystems"), dict) else {}
        if key in groups:
            return {"ok": False, "error": "exists"}
        if path.is_file():
            backup = path.parent / "config_backups"
            backup.mkdir(exist_ok=True)
            shutil.copy2(path, backup / (path.stem + "-" + time.strftime("%Y%m%d-%H%M%S") + path.suffix))
            for extra in sorted(backup.glob(path.stem + "-*" + path.suffix))[:-keep]:
                extra.unlink()
        new = {"label": str(label or key.replace("_", " ").title()), "prefixes": [prefix]}
        ordered = {k: v for k, v in groups.items() if k != "rest"}
        ordered[key] = new
        if "rest" in groups:
            ordered["rest"] = groups["rest"]
        data["ecosystems"] = ordered
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        os.replace(tmp, path)
        return {"ok": True, "file": path.name}
    except OSError:
        return {"ok": False, "error": "io"}
