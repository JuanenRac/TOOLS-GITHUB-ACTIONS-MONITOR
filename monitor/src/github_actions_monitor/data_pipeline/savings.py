# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Ways to read less from the allowance of GitHub. Standard library only, everything OFF by default (block `savings`).

A COLD repository is one whose last runs are all finished and green; the monitor reads it only on its slow turn (`cold_refresh_seconds`). Two opt-in ways let that slow turn pass without a call:

  webhook first   `savings.webhook_first`: while the incoming webhook is alive (it delivered an event in the last `savings.webhook_window_minutes`) a cold repository is not polled, GitHub tells
                  when something happens; it is still read in full every `savings.webhook_full_minutes` as a safety net. With no webhook alive, nothing changes.
  free sources    `savings.feeds.enabled`: before a cold repository is read with the API, the newest commit of its default branch is asked from a source that costs no allowance - the public
                  Atom feed of the commits (`method` atom), `git ls-remote` (git) or either (auto) - and when it is the one of the last full read the repository is left as it is. A full
                  read is still made every `savings.feeds.max_age_minutes`. A private repository, a refused or odd answer or an error means "unknown": the repository is read with the API as always.

Neither way is used for a repository that is hot (running, red, or touched by an event): those are read as always. A run that starts without a push (a schedule, a re-run) on a cold repository is
seen at the next full read - that is the price of these switches, said in docs/QUOTA.md. The counters (`stats`) say how many reads each way spared; one spared read is about one call of the API.
Nothing here writes anything or sends anything but a GET to github.com (through netguard) or `git ls-remote` of a public address.
"""
import re
import subprocess
import time
import xml.etree.ElementTree as ElementTree

from github_actions_monitor.security import envguard, netguard

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}\Z")
OWNER_RE = re.compile(r"^[A-Za-z0-9-]{1,39}\Z")
SHA_RE = re.compile(r"\b[0-9a-f]{40}\b")
METHODS = ("atom", "git", "auto")
MAX_FEED = 400_000
STATS = {"webhook": 0, "feed": 0, "git": 0, "unknown": 0, "since": time.time()}
LAST_WEBHOOK = {"at": 0.0}


def _int(block, key, low, high, default):
    value = block.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    block = config.get("savings") if isinstance(config, dict) and isinstance(config.get("savings"), dict) else {}
    feeds = block.get("feeds") if isinstance(block.get("feeds"), dict) else {}
    method = feeds.get("method")
    return {"webhook_first": block.get("webhook_first") is True, "webhook_window_minutes": _int(block, "webhook_window_minutes", 5, 1440, 60),
            "webhook_full_minutes": _int(block, "webhook_full_minutes", 30, 10080, 360),
            "feeds": {"enabled": feeds.get("enabled") is True and not (isinstance(config, dict) and config.get("airgapped") is True), "method": method if method in METHODS else "atom",
                      "max_age_minutes": _int(feeds, "max_age_minutes", 15, 10080, 240)}}


def note_webhook(now=None):
    """The webhook delivered an event (a signed one that was accepted): while it keeps doing so, `webhook_first` may stretch the slow turn of the cold repositories."""
    LAST_WEBHOOK["at"] = time.time() if now is None else now


def webhook_alive(config, now=None):
    cfg = settings(config)
    now = time.time() if now is None else now
    from github_actions_monitor.util import clock
    return cfg["webhook_first"] and LAST_WEBHOOK["at"] > 0 and not clock.in_future(LAST_WEBHOOK["at"], now) and now - LAST_WEBHOOK["at"] <= cfg["webhook_window_minutes"] * 60


def quiet_by_webhook(config, entry, now=None):
    """True when the slow turn of a cold repository (with the cached `entry`) may pass because the webhook is alive and the last full read is not older than the safety net."""
    now = time.time() if now is None else now
    if not entry or not webhook_alive(config, now):
        return False
    return now - entry.get("full_at", entry.get("at", 0)) < settings(config)["webhook_full_minutes"] * 60


def head_from_atom(text):
    """The sha of the newest commit in the Atom feed of the commits, or "" when the text is not that feed."""
    try:
        root = ElementTree.fromstring(text)      # a feed of GitHub: no external entities are resolved by the parser
    except ElementTree.ParseError:
        return ""
    for node in root.iter():
        if node.tag.endswith("}id") or node.tag == "id":
            found = re.search(r"Commit/([0-9a-f]{40})\b", node.text or "")
            if found:
                return found.group(1)
    return ""


def head_atom(owner, repo, opener=None, timeout=10):
    if not OWNER_RE.match(str(owner)) or not NAME_RE.match(str(repo)):
        return ""
    import urllib.request
    request = urllib.request.Request(f"https://github.com/{owner}/{repo}/commits.atom", headers={"User-Agent": "github-actions-monitor", "Accept": "application/atom+xml"})
    try:
        with (opener or netguard.open_url)(request, timeout=timeout) as answer:
            if getattr(answer, "status", 200) != 200 or "xml" not in (answer.headers.get("Content-Type") or "xml"):
                return ""
            return head_from_atom(answer.read(MAX_FEED).decode("utf-8", "replace"))
    except (OSError, ValueError):
        return ""


def head_git(owner, repo, runner=None, timeout=20):
    """The sha `HEAD` points to at the public address of the repository, from `git ls-remote` (no password is ever asked)."""
    if not OWNER_RE.match(str(owner)) or not NAME_RE.match(str(repo)):
        return ""
    args = ["git", "-c", "credential.helper=", "ls-remote", f"https://github.com/{owner}/{repo}.git", "HEAD"]      # no helper: a password prompt never opens
    try:
        if runner is not None:
            code, out = runner(args)
        else:
            done = subprocess.run(args, capture_output=True, timeout=timeout, env={**envguard.clean_environment(), "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "", "GCM_INTERACTIVE": "never"})
            code, out = done.returncode, done.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError):
        return ""
    found = SHA_RE.search(out or "") if code == 0 else None
    return found.group(0) if found else ""


def head(config, owner, repo, opener=None, runner=None):
    """(sha, way): the newest commit of the default branch from a source that costs no allowance, or ("", "")."""
    method = settings(config)["feeds"]["method"]
    if method in ("atom", "auto"):
        sha = head_atom(owner, repo, opener)
        if sha:
            return sha, "feed"
    if method in ("git", "auto"):
        sha = head_git(owner, repo, runner)
        if sha:
            return sha, "git"
    return "", ""


def feed_quiet(config, owner, repo, entry, now=None, opener=None, runner=None):
    """True when the repository can stay as it is: the free sources are on, the cached `entry` is quiet (no run that is not finished, none red) and is younger than `max_age_minutes`, and the
    newest commit is the one of the last full read (`entry["head"]`). Counts the spared read. False for anything else (including 'unknown')."""
    cfg = settings(config)["feeds"]
    now = time.time() if now is None else now
    if not cfg["enabled"] or not entry or not entry.get("head"):
        return False
    if now - entry.get("full_at", entry.get("at", 0)) >= cfg["max_age_minutes"] * 60:
        return False
    runs = entry.get("runs") or []
    if any(r.get("status") != "completed" or r.get("conclusion") in ("failure", "timed_out", "startup_failure", "cancelled", "action_required") for r in runs):
        return False
    sha, way = head(config, owner, repo, opener, runner)
    if not sha:
        STATS["unknown"] += 1
        return False
    if sha != entry["head"]:
        return False
    STATS["feed" if way == "feed" else "git"] += 1
    return True


def remember_head(config, owner, repo, opener=None, runner=None):
    """The newest commit to store with a full read (only when the free sources are on); "" otherwise."""
    if not settings(config)["feeds"]["enabled"]:
        return ""
    return head(config, owner, repo, opener, runner)[0]


def count_webhook(n=1):
    STATS["webhook"] += n


def stats(config=None):
    """What each way spared since the monitor started: {webhook, feed, git, unknown, total, since}; `total` is the number of reads (about one call each) that were not made."""
    out = dict(STATS)
    out["total"] = STATS["webhook"] + STATS["feed"] + STATS["git"]
    out["settings"] = settings(config or {})
    return out
