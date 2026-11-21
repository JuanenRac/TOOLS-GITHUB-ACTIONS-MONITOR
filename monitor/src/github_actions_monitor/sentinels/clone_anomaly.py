# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Abnormal clones by user: one person who clones many DIFFERENT repositories of the organization in a short time (a stolen personal credential used to take the whole organization).

It reads the audit log of the organization for the event `git.clone` (GitHub offers it only to some plans: when the plan does not give it, the answer says so and nothing else happens), counts the
repositories that each user cloned inside a window and names the users above a threshold. People and tools that clone a lot on purpose (a deploy robot, a guardian) are left out by name patterns.
Read only: one GET of the audit log per check (at most every `check_minutes`), never a write, and what is kept in memory has no address (IP) of anybody: the finding names the user and the repositories.

  settings(config)               `audit_feed.clone_alert`: enabled (off), threshold (5), window_hours (24), bot_patterns, check_minutes (30)
  parse(entries)                 the clone events of an audit log answer: [{"user", "repo", "at"}]
  analyze(events, cfg, now)      [{"user", "repos", "count"}] of the users above the threshold, most repositories first
  check(read, org, cfg, now)     reads, parses and analyzes; the answer keeps its last result for `check_minutes`
"""
import time
from datetime import datetime, timezone

DEFAULTS = {"enabled": False, "threshold": 5, "window_hours": 24, "bot_patterns": ["-bot", "_bot", "deploy", "guardian"], "check_minutes": 30}
BOUNDS = {"threshold": (1, 1000), "window_hours": (1, 168), "check_minutes": (5, 1440)}
CODE = "audit.clone_anomaly"
MAX_EVENTS = 1000
MAX_FINDINGS = 50
_CACHE = {"at": 0.0, "answer": None}


def settings(config):
    block = (((config or {}).get("audit_feed") or {}).get("clone_alert")) if isinstance((config or {}).get("audit_feed"), dict) else None
    block = block if isinstance(block, dict) else {}
    merged = {key: (list(value) if isinstance(value, list) else value) for key, value in DEFAULTS.items()}
    merged["enabled"] = block.get("enabled") is True
    for key, (low, high) in BOUNDS.items():
        value = block.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
            merged[key] = value
    patterns = block.get("bot_patterns")
    if isinstance(patterns, list) and all(isinstance(p, str) and 0 < len(p) <= 60 for p in patterns):
        merged["bot_patterns"] = [p.lower() for p in patterns[:50]]
    return merged


def is_bot(user, patterns):
    name = str(user or "").lower()
    return name.endswith("[bot]") or any(p and p in name for p in patterns)      # a GitHub app is always a bot, whatever the patterns say


def parse(entries):
    """The clone events of an audit log answer (a list of entries). An entry without a user, a repository or a time is left out; the address of the visitor is never read."""
    out = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or str(entry.get("action") or "") != "git.clone":
            continue
        user, repo, stamp = entry.get("actor") or entry.get("user"), entry.get("repo"), entry.get("@timestamp") or entry.get("created_at")
        if not (isinstance(user, str) and isinstance(repo, str) and user and repo and isinstance(stamp, (int, float))):
            continue
        out.append({"user": user[:60], "repo": repo[:140], "at": stamp / 1000.0 if stamp > 10 ** 11 else float(stamp)})
        if len(out) >= MAX_EVENTS:
            break
    return out


def analyze(events, cfg, now=None):
    """Users above `threshold` different repositories inside `window_hours`; bots by name pattern are skipped. Most repositories first, then by name."""
    now = time.time() if now is None else now
    since = now - cfg["window_hours"] * 3600
    seen = {}
    for event in events:
        if event["at"] < since or event["at"] > now + 300 or is_bot(event["user"], cfg["bot_patterns"]):
            continue
        seen.setdefault(event["user"], set()).add(event["repo"])
    found = [{"user": user, "repos": sorted(repos)[:20], "count": len(repos)} for user, repos in seen.items() if len(repos) > cfg["threshold"]]
    found.sort(key=lambda f: (-f["count"], f["user"].lower()))
    return found[:MAX_FINDINGS]


def check(read, org, cfg, now=None):
    """{"enabled", "available", "window_hours", "threshold", "checked", "findings"}. `read(endpoint)` is a GET of the API. When the audit log is not available (404, 403, a plan without the git events)
    `available` is False and there is no finding; the result is kept `check_minutes` so a page that asks often does not read again."""
    now = time.time() if now is None else now
    base = {"enabled": cfg["enabled"], "available": False, "window_hours": cfg["window_hours"], "threshold": cfg["threshold"], "checked": 0, "findings": []}
    if not cfg["enabled"] or not org:
        return base
    if _CACHE["answer"] is not None and now - _CACHE["at"] < cfg["check_minutes"] * 60 and _CACHE["answer"].get("org") == org:
        return {k: v for k, v in _CACHE["answer"].items() if k != "org"}
    since = datetime.fromtimestamp(now - cfg["window_hours"] * 3600, timezone.utc).strftime("%Y-%m-%d")
    endpoint = f"orgs/{org}/audit-log?include=git&phrase=action:git.clone+created:%3E%3D{since}&per_page=100"
    try:
        entries = read(endpoint)
    except Exception:   # noqa: BLE001 - a plan without the git events, a missing permission or no network: unavailable, never an error on the page
        entries = None
    answer = dict(base)
    answer["checked"] = int(now)
    if isinstance(entries, list):
        answer["available"] = True
        answer["findings"] = analyze(parse(entries), cfg, now)
    _CACHE["at"], _CACHE["answer"] = now, {**answer, "org": org}
    return answer


def forget():
    _CACHE["at"], _CACHE["answer"] = 0.0, None


def due(cfg, now=None):
    """True when the audit log may be read again (`check_minutes` have passed since the last check)."""
    now = time.time() if now is None else now
    return _CACHE["answer"] is None or now - _CACHE["at"] >= cfg["check_minutes"] * 60


def alerts(account="", now=None):
    """One alert for each user above the threshold in the LAST answer (memory only, nothing is read here); it names the user and the repositories, never an address."""
    answer = _CACHE["answer"]
    if not answer or not answer.get("enabled") or not answer.get("findings"):
        return []
    from github_actions_monitor import i18n
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(answer.get("checked") or (time.time() if now is None else now)))
    return [{"id": f"{CODE}:{f['user']}", "code": CODE, "level": "warning", "sentinel": "system", "account_id": account, "repo": None,
             "title": i18n.t("clones.alert", user=f["user"], n=f["count"], hours=answer["window_hours"]),
             "details": {"user": f["user"], "repos": f["repos"], "count": f["count"], "window_hours": answer["window_hours"], "threshold": answer["threshold"]}, "created_at": stamp}
            for f in answer["findings"]]
