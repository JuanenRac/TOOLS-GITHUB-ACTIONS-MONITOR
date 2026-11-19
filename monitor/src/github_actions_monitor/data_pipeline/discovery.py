# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Automatic discovery and self-tuning, as small pure functions (the monitor calls them after each listing of the account; nothing here reads GitHub or writes a file).

  diff(previous, current)            events for a repository that appeared, vanished, was archived or unarchived: [{"code", "repo"}]
  lifecycle(items, rules)            drops archived / fork / empty / private repositories when the rules say so
  suggest_groups(unclassified, ...)  a prefix shared by three or more repositories that no group claims -> a suggested group; NEVER applied without a confirmation
  auto_frequency(...)                the hot / cold intervals the real activity asks for, inside the quota budget
  box(...)                           the "owner / watched / hidden" figures of the Basic tab
Settings (all in the `discovery` block of the configuration): events (on), suggest_groups (on), auto_frequency (off), hide (a list of fork, empty, private, public: repositories of that kind are left out),
skip_archived (on: archived repositories are left out), fork_policy (what to do with forks: show = all of them, skip = none, skip_unless_ci = only the ones that have a CI of their own,
auto = skip_unless_ci with a window that depends on the kind of account), fork_ci_days (a fork counts as maintained when its CI ran this many days ago; 0 = an enabled workflow is enough),
fork_checks_per_pass (how many forks are asked about in one listing), min_keep_pct (a listing that comes back empty, or with fewer than this percentage of the repositories of the last good one,
is not believed: see listing_verdict; 0 = every listing is believed).

A fork has "a CI of its own" when it has an enabled workflow (a fork starts with its workflows disabled, so an enabled one was switched on by someone) and, if fork_ci_days is not 0, a run in that window.
"""
import re
import time
from datetime import datetime, timezone
from github_actions_monitor.security import private_io

DEFAULTS = {"events": True, "suggest_groups": True, "auto_frequency": False, "hide": [], "skip_archived": True, "fork_policy": "show", "fork_ci_days": 90, "fork_checks_per_pass": 30, "min_keep_pct": 50}
EVENT_CODES = ("repo_new", "repo_gone", "repo_archived", "repo_unarchived")
FORK_POLICIES = ("show", "skip", "skip_unless_ci", "auto")
FORK_TTL = 7 * 86400      # how long the answer about one fork is kept
ORG_WINDOW = 2            # on an organisation (policy auto) the window of fork_ci_days is this many times longer


def settings(config):
    block = config.get("discovery") if isinstance(config, dict) and isinstance(config.get("discovery"), dict) else {}
    out = {key: block.get(key, default) is True for key, default in DEFAULTS.items() if isinstance(default, bool)}
    hide = block.get("hide")
    out["hide"] = [w for w in hide if w in ("fork", "empty", "private", "public")] if isinstance(hide, list) else []
    out["fork_policy"] = block.get("fork_policy") if block.get("fork_policy") in FORK_POLICIES else DEFAULTS["fork_policy"]
    for key, low, high in (("fork_ci_days", 0, 365), ("fork_checks_per_pass", 1, 500), ("min_keep_pct", 0, 100)):
        value = block.get(key)
        out[key] = value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else DEFAULTS[key]
    if "fork" in out["hide"]:
        out["fork_policy"] = "skip"      # the older way of leaving every fork out
    return out


def listing_verdict(before, now, min_keep_pct):
    """"ok", "empty" or "dropped": whether a new listing of the account may replace the last good one. An empty listing is never a success (it would read as "everything is green" with nothing watched) and, with
    `min_keep_pct` above 0, neither is one that keeps fewer than that share of the repositories of the last good listing. With no earlier listing a listing with names is believed."""
    if now <= 0 and min_keep_pct > 0:
        return "empty"
    if min_keep_pct > 0 and before > 0 and now * 100 < before * min_keep_pct:
        return "dropped"
    return "ok"


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


def _reason(item, cfg, fork_ci):
    """Why a repository of the listing is left out of the watch (archived, empty, private, public, fork) or None when it stays. A visibility that was not read (no `isPrivate` field) is never a reason."""
    hide, policy = cfg["hide"], cfg["fork_policy"]
    if item.get("isArchived") and cfg["skip_archived"]:
        return "archived"
    if "empty" in hide and item.get("isEmpty"):
        return "empty"
    if "private" in hide and item.get("isPrivate") is True:
        return "private"
    if "public" in hide and item.get("isPrivate") is False:
        return "public"
    if item.get("isFork") and (policy == "skip" or (policy in ("skip_unless_ci", "auto") and fork_ci.get(item["name"]) is not True)):
        return "fork"
    return None


def lifecycle(items, rules, fork_ci=None):
    """`items` is [{"name", "isArchived", "isFork", "isEmpty", "isPrivate"}]; returns the names that stay. `fork_ci` is {name: True | False | None} (a fork with a CI of its own, without,
    not known yet): with the policy skip_unless_ci or auto only the forks answered True stay."""
    cfg = settings({"discovery": rules})
    fork_ci = fork_ci or {}
    return [item["name"] for item in items if _reason(item, cfg, fork_ci) is None]


def exclusions(items, rules, fork_ci=None):
    """{reason: how many} for the repositories the lifecycle rules leave out (archived, empty, private, public, fork): the figure the Basic tab shows, so a repository left out by a filter is counted and never read as clean."""
    cfg = settings({"discovery": rules})
    fork_ci = fork_ci or {}
    out = {}
    for item in items:
        why = _reason(item, cfg, fork_ci)
        if why:
            out[why] = out.get(why, 0) + 1
    return out


def owner_kind(reader, owner):
    """"user", "organization" or None (not known): one read of `users/<owner>`."""
    try:
        kind = str((reader(f"users/{owner}") or {}).get("type", "")).lower()
    except Exception:   # noqa: BLE001 - offline or refused: the policy then uses the plain window
        return None
    return {"user": "user", "organization": "organization"}.get(kind)


def fork_window(cfg, kind):
    """The days a fork's CI may be silent and still count as maintained (0 = no window)."""
    days = cfg["fork_ci_days"]
    return days * ORG_WINDOW if (cfg["fork_policy"] == "auto" and kind == "organization") else days


def fork_has_ci(reader, owner, name, days, now=None):
    """True when the fork has a workflow switched on and (days > 0) a run inside the window; False when it has none; None when GitHub did not answer."""
    try:
        listing = reader(f"repos/{owner}/{name}/actions/workflows?per_page=100") or {}
        active = [w for w in listing.get("workflows") or [] if isinstance(w, dict) and w.get("state") == "active" and str(w.get("path", "")).startswith(".github/workflows/")]
        if not active:
            return False
        if days <= 0:
            return True
        runs = (reader(f"repos/{owner}/{name}/actions/runs?per_page=1") or {}).get("workflow_runs") or []
        if not runs or not isinstance(runs[0], dict):
            return False
        made = datetime.strptime(str(runs[0].get("created_at", ""))[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        return ((now or time.time()) - made.timestamp()) <= days * 86400
    except Exception:   # noqa: BLE001
        return None


def check_forks(forks, known, reader, owner, days, limit, now=None):
    """`known` is {name: {"ci": bool, "at": ts, "days": n}} (updated here). Asks about at most `limit` forks whose answer is missing, old or made with another window, the oldest first;
    returns {name: True | False | None}."""
    now = time.time() if now is None else now
    due = sorted((n for n in forks if n not in known or now - known[n].get("at", 0) > FORK_TTL or known[n].get("days") != days), key=lambda n: known.get(n, {}).get("at", 0))
    for name in due[:max(0, limit)]:
        answer = fork_has_ci(reader, owner, name, days, now)
        if answer is not None:
            known[name] = {"ci": answer, "at": now, "days": days}
    for gone in [n for n in known if n not in forks]:
        known.pop(gone)
    return {n: (known[n]["ci"] if n in known else None) for n in forks}


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


def box(owner, watched, discovered, hidden_names, reasons=None):
    return {"owner": owner, "watched": watched, "discovered": discovered, "hidden": len(hidden_names), "hidden_names": list(hidden_names)[:50], "excluded": {k: int(v) for k, v in sorted((reasons or {}).items())}}


KEY_RE = re.compile(r"^[a-z0-9_]{1,40}\Z")
PREFIX_RE = re.compile(r"^[A-Za-z0-9._-]{2,60}\Z")


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
        private_io.write_tmp(tmp, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        os.replace(tmp, path)
        return {"ok": True, "file": path.name}
    except OSError:
        return {"ok": False, "error": "io"}
