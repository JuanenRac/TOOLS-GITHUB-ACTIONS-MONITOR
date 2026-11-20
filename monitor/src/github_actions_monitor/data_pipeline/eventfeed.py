# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A change detector that costs almost nothing: the events of the account, read with an ETag.

GitHub keeps a short list of what happened in an organization (`GET /orgs/OWNER/events`) or to a user (`GET /users/OWNER/events`): pushes, pull requests, tags, releases. A read that carries the
ETag of the last answer gets `304 Not Modified` when nothing happened, and a `304` costs no allowance. So one cheap read every minute says WHEN something changed and WHICH repository it was, and
only that repository is read again, instead of waiting for the next slow turn of the cold repositories.

  events_feed.enabled           off by default
  events_feed.interval_seconds  60 by default (30 to 3600); GitHub may ask for more with `X-Poll-Interval`, and that wins
  events_feed.owner_kind        auto (the default: the organization first, else the user), org or user
  events_feed.max_per_tick      at most this many repositories are marked per read (20 by default)

The first read only learns where the list stands (it marks nothing). Only a short list of event types counts (the ones that can start or change a workflow); only repositories the monitor already
watches are marked; nothing is written to GitHub and nothing of an event is kept but its number. Pure functions and one small class: the read itself is given by the caller (no network here).
"""
import json
import re
import threading
import time

from github_actions_monitor.data_pipeline import etagcache

DEFAULTS = {"enabled": False, "interval_seconds": 60, "owner_kind": "auto", "max_per_tick": 20}
KINDS = ("auto", "org", "user")
TYPES = ("PushEvent", "PullRequestEvent", "CreateEvent", "DeleteEvent", "ReleaseEvent")      # the events that can start or change a run: stars, forks and comments are left out
OWNER_RE = re.compile(r"^[A-Za-z0-9-]{1,39}\Z")
FULL_RE = re.compile(r"^[A-Za-z0-9-]{1,39}/([A-Za-z0-9._-]{1,100})\Z")


def _int(value, low, high, default):
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    block = (config or {}).get("events_feed")
    block = block if isinstance(block, dict) else {}
    return {"enabled": block.get("enabled") is True, "interval_seconds": _int(block.get("interval_seconds"), 30, 3600, DEFAULTS["interval_seconds"]),
            "owner_kind": block.get("owner_kind") if block.get("owner_kind") in KINDS else "auto", "max_per_tick": _int(block.get("max_per_tick"), 1, 200, DEFAULTS["max_per_tick"])}


def endpoints(owner, kind):
    """The addresses to try, in order, for an owner: [] when the name is not a plain GitHub name."""
    if not isinstance(owner, str) or not OWNER_RE.match(owner):
        return []
    org, user = f"orgs/{owner}/events?per_page=30", f"users/{owner}/events?per_page=30"
    return [org] if kind == "org" else [user] if kind == "user" else [org, user]


def read(run, endpoint, etag=""):
    """One conditional read. `run(args)` runs `gh` and returns (returncode, stdout, stderr). Returns (status, etag, body, poll): status 304 (nothing new, `body` None) or 200 (`body` the parsed list), the
    new ETag, and the seconds GitHub asks to wait (0 when it says nothing). Anything else raises RuntimeError with the short message of `gh`."""
    args = ["api", "-i"] + (["-H", f"If-None-Match: {etag}"] if etag else []) + [endpoint]
    code, out, err = run(args)
    status, headers, body = etagcache.split_response(out)
    try:
        poll = max(0, min(int(headers.get("x-poll-interval", "0")), 3600))
    except ValueError:
        poll = 0
    if status == 304:
        return 304, etag, None, poll
    if code != 0 or status not in (200, 0):
        raise RuntimeError((err or out or "gh failed").strip()[:200])
    try:
        data = json.loads(body) if body.strip() else []
    except ValueError:
        raise RuntimeError("the answer of the API is not valid JSON") from None
    new_tag = headers.get("etag", "")
    return 200, new_tag if etagcache.ETAG_RE.match(new_tag) else "", data if isinstance(data, list) else [], poll


def fresh_repos(events, seen, watched, limit):
    """([repositories], newest number): the repositories of the events newer than `seen` that count and that the monitor watches, most recent first, each once, at most `limit`."""
    watched = set(watched)
    newest, out = seen, []
    for event in events if isinstance(events, list) else []:
        if not isinstance(event, dict):
            continue
        try:
            number = int(str(event.get("id")))
        except ValueError:
            continue
        newest = max(newest, number)
        if number <= seen or event.get("type") not in TYPES:
            continue
        found = FULL_RE.match(str((event.get("repo") or {}).get("name") if isinstance(event.get("repo"), dict) else ""))
        name = found.group(1) if found else ""
        if name and name in watched and name not in out and len(out) < limit:
            out.append(name)
    return out, newest


class Feed:
    """What one detector remembers: the ETag and the newest event number of the address it reads, and the counters the page and the API show."""

    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.endpoint = ""
        self.etag = ""
        self.seen = 0
        self.learned = False      # the first answer of an address only says where its list stands
        self.next_at = 0.0
        self.stats = {"polls": 0, "unchanged": 0, "changed": 0, "marked": 0, "errors": 0, "last_at": None, "last_error": ""}

    def tick(self, run, owner, config, watched, now=None):
        """One turn: returns the repositories to read again (possibly none). Never raises: a failure is counted and the next turn tries again. Called at most once per interval by the loop; it does
        nothing before `next_at`."""
        now = time.time() if now is None else now
        cfg = settings(config)
        with self.lock:
            if not cfg["enabled"] or now < self.next_at:
                return []
            tried = [self.endpoint] if self.endpoint else endpoints(owner, cfg["owner_kind"])
            etag, seen = self.etag, self.seen
        if not tried:
            return []
        status, new_tag, body, poll, used, last_error = 0, "", None, 0, "", ""
        for endpoint in tried:
            try:
                status, new_tag, body, poll = read(run, endpoint, etag if endpoint == self.endpoint else "")
                used = endpoint
                break
            except RuntimeError as error:
                last_error = str(error)[:120]
        with self.lock:
            self.stats["polls"] += 1
            self.stats["last_at"] = now
            self.next_at = now + max(cfg["interval_seconds"], poll if used else 0)
            if not used:
                self.stats["errors"] += 1
                self.stats["last_error"] = last_error
                if self.endpoint:      # the address that worked is not trusted blindly after a failure: the next turn tries the list again
                    self.endpoint, self.etag = "", ""
                return []
            self.stats["last_error"] = ""
            if used != self.endpoint:
                self.endpoint, seen, self.learned = used, 0, False
            if status == 304:
                self.stats["unchanged"] += 1
                return []
            self.etag = new_tag
            repos, newest = fresh_repos(body, seen, watched, cfg["max_per_tick"])
            first = not self.learned
            self.learned = True
            self.seen = max(seen, newest)
            if first:      # the first read only learns where the list stands
                return []
            self.stats["changed"] += 1
            self.stats["marked"] += len(repos)
            return repos

    def snapshot(self, config=None):
        cfg = settings(config)
        with self.lock:
            return {"enabled": cfg["enabled"], "interval_seconds": cfg["interval_seconds"], "endpoint": self.endpoint.split("?")[0], "newest": self.seen or None, **self.stats}


FEED = Feed()
