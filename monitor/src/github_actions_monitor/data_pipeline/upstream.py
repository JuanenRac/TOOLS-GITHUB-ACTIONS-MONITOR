# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Follow the original repository (the upstream) of each fork. Off by default.

For an account that collects forks the useful question is not "is my CI green" but "what happens in the projects I follow": is the main branch of the original red, did it publish a release. The
fork knows its parent, so the answer is one GraphQL read: the status of the last commit of the default branch of the parent and its latest release. Several forks go in one request.

Nothing here is on unless `upstream.enabled` is on. The cost is bounded by the settings: at most `upstream.requests_per_hour` requests an hour, each one with at most `upstream.forks_per_request`
forks, and a fork is read again only after `upstream.refresh_hours`. The forks are taken in turn (the least recently read first), so a very large account is covered slowly instead of at once.
`upstream.repos` limits the follow to the forks named there (empty: every fork). Pure functions: no network and no clock of their own; the caller gives the reader and the time."""
import math
import re

NAME = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")
ROLLUP = {"SUCCESS": "success", "FAILURE": "failure", "ERROR": "failure", "PENDING": "pending", "EXPECTED": "pending"}
DEFAULTS = {"enabled": False, "refresh_hours": 12, "requests_per_hour": 6, "forks_per_request": 8, "news_days": 7, "notify": False, "repos": []}
BOUNDS = {"refresh_hours": (1, 720), "requests_per_hour": (1, 120), "forks_per_request": (1, 25), "news_days": (1, 90)}


def settings(config):
    """The `upstream` block of the configuration over DEFAULTS; a value of the wrong type or out of its bounds keeps the default."""
    block = (config or {}).get("upstream")
    block = block if isinstance(block, dict) else {}
    out = dict(DEFAULTS, repos=[])
    for key in ("enabled", "notify"):
        if isinstance(block.get(key), bool):
            out[key] = block[key]
    for key, (low, high) in BOUNDS.items():
        value = block.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
            out[key] = value
    if isinstance(block.get("repos"), list):
        out["repos"] = [str(n) for n in block["repos"] if isinstance(n, str) and NAME.match(n)][:1000]
    return out


def query(owner, names):
    """The GraphQL text that reads the parent of each fork in `names` (names that are not plain repository names are left out)."""
    if not NAME.match(str(owner or "")):
        return ""
    parts = []
    for number, name in enumerate(n for n in names if NAME.match(str(n))):
        parts.append('r%d:repository(owner:"%s",name:"%s"){name parent{nameWithOwner url isArchived defaultBranchRef{name target{... on Commit{oid committedDate statusCheckRollup{state}}}} '
                     'latestRelease{tagName publishedAt isDraft isPrerelease url}}}' % (number, owner, name))
    return "query{rateLimit{remaining cost} " + " ".join(parts) + "}" if parts else ""


def parse_parent(node):
    """The facts kept about one parent, or None when the fork has none (the original was deleted or the repository is not a fork)."""
    parent = (node or {}).get("parent")
    if not isinstance(parent, dict):
        return None
    branch = parent.get("defaultBranchRef") or {}
    commit = branch.get("target") or {}
    release = parent.get("latestRelease")
    release = release if isinstance(release, dict) and not release.get("isDraft") else None
    return {
        "parent": str(parent.get("nameWithOwner") or "")[:140], "url": str(parent.get("url") or "")[:300], "archived": parent.get("isArchived") is True,
        "branch": str(branch.get("name") or "")[:100], "sha": str(commit.get("oid") or "")[:40], "committed": commit.get("committedDate"),
        "state": ROLLUP.get(str((commit.get("statusCheckRollup") or {}).get("state") or "").upper(), "none"),
        "release": {"tag": str(release.get("tagName") or "")[:100], "published": release.get("publishedAt"), "pre": release.get("isPrerelease") is True, "url": str(release.get("url") or "")[:300]} if release else None,
    }


def merge(previous, fresh, now):
    """The entry to keep: `fresh` with the moments the state or the release changed (the first reading is not a change)."""
    entry = dict(fresh or {"parent": None}, at=now)
    old = previous if isinstance(previous, dict) else None
    entry["state_since"] = (old or {}).get("state_since") or now
    entry["release_changed"] = (old or {}).get("release_changed")
    if old and fresh:
        if old.get("state") != fresh.get("state"):
            entry["state_since"] = now
        old_tag = (old.get("release") or {}).get("tag")
        new_tag = (fresh.get("release") or {}).get("tag")
        if new_tag and old_tag != new_tag and old.get("parent"):
            entry["release_changed"] = now
    return entry


def followed(forks, cfg):
    """The forks to follow: the named ones that are forks, or all of them when no name is given."""
    forks = sorted(set(forks or ()))
    named = set(cfg.get("repos") or ())
    return [f for f in forks if f in named] if named else forks


def pick_due(forks, store, now, cfg, requests_last_hour=0):
    """The forks to read now: none while the hourly limit of requests is used or the feature is off; otherwise the least recently read among those older than the refresh period, at most one request."""
    if not cfg.get("enabled") or requests_last_hour >= cfg["requests_per_hour"]:
        return []
    limit = cfg["refresh_hours"] * 3600
    due = [(float((store.get(f) or {}).get("at") or 0.0), f) for f in followed(forks, cfg) if now - float((store.get(f) or {}).get("at") or 0.0) >= limit]
    return [f for _at, f in sorted(due)][: cfg["forks_per_request"]]


def read(fetch, owner, names, now, store):
    """Reads `names` with one request and updates `store` in place. `fetch(text)` gives the parsed data of the GraphQL answer; returns the number of forks updated."""
    text = query(owner, names)
    if not text:
        return 0
    data = fetch(text) or {}
    done = 0
    for number, name in enumerate(n for n in names if NAME.match(str(n))):
        node = data.get("r%d" % number)
        if not isinstance(node, dict):      # a fork that GitHub did not give back (deleted, renamed or not visible): written down as read, or it would be the first of every turn for ever
            store[name] = dict(merge(store.get(name), None, now), unreadable=True)
            continue
        store[name] = merge(store.get(name), parse_parent(node), now)
        done += 1
    return done


def mark_tried(store, names, now):
    """The request for `names` failed as a whole: write down that they were tried now, so that the next turn takes other forks (the data already read is kept; the ones never read are marked unreadable)."""
    for name in names:
        entry = store.get(name)
        if isinstance(entry, dict):
            entry["at"] = now
        elif NAME.match(str(name)):
            store[name] = {"parent": None, "at": now, "unreadable": True}


def build(store, forks, cfg, now, requests_last_hour=0):
    """The picture for the snapshot: {"enabled": False} while off; else the rows (red first, then news, then the rest), the counts and what is still unread."""
    if not cfg.get("enabled"):
        return {"enabled": False}
    news = cfg["news_days"] * 86400
    rows, unread, unreadable = [], 0, 0
    for fork in followed(forks, cfg):
        entry = store.get(fork)
        if not isinstance(entry, dict) or not entry.get("at"):
            unread += 1
            continue
        if not entry.get("parent"):
            if entry.get("unreadable") is True:      # tried and not given back (or the request failed): not "unread", and not a row either
                unreadable += 1
                continue
            rows.append({"repo": fork, "parent": None, "state": "detached", "release": None, "news": False, "red": False, "at": entry["at"]})
            continue
        fresh_release = bool(entry.get("release_changed")) and now - entry["release_changed"] <= news
        rows.append({"repo": fork, "parent": entry["parent"], "url": entry.get("url"), "branch": entry.get("branch"), "state": entry.get("state"), "state_since": entry.get("state_since"),
                     "archived": entry.get("archived", False), "release": entry.get("release"), "news": fresh_release, "red": entry.get("state") == "failure", "committed": entry.get("committed"),
                     "at": entry["at"]})
    rows.sort(key=lambda r: (not r["red"], not r["news"], r["repo"].lower()))
    per_request = max(1, cfg["forks_per_request"])
    round_hours = math.ceil(len(followed(forks, cfg)) / per_request / max(1, cfg["requests_per_hour"]) * 10) / 10      # how long one pass over all the followed forks takes at the pace the settings allow
    return {"enabled": True, "followed": len(followed(forks, cfg)), "round_hours": round_hours, "refresh_hours": cfg["refresh_hours"], "continuous": round_hours > cfg["refresh_hours"], "tracked": len(rows), "unread": unread, "unreadable": unreadable, "red": sum(1 for r in rows if r["red"]), "news": sum(1 for r in rows if r["news"]), "detached": sum(1 for r in rows if r["state"] == "detached"),
            "requests_last_hour": requests_last_hour, "requests_per_hour": cfg["requests_per_hour"], "notify": cfg["notify"], "rows": rows[:200]}
