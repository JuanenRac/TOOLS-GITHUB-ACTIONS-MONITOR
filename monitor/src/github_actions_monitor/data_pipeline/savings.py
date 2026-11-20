# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Ways to read less from the allowance of GitHub. Standard library only, everything OFF by default (block `savings`).

A COLD repository is one whose last runs are all finished and green; the monitor reads it only on its slow turn (`cold_refresh_seconds`). Two opt-in ways let that slow turn pass without a call:

  webhook first   `savings.webhook_first`: while the incoming webhook is alive (it delivered an event in the last `savings.webhook_window_minutes`) a cold repository is not polled, GitHub tells
                  when something happens; it is still read in full every `savings.webhook_full_minutes` as a safety net. With no webhook alive, nothing changes.
                  `savings.webhook_live_per_repo` (also off) makes "alive" a thing of each repository: only a repository whose OWN events arrived in the window is spared, so a repository
                  whose webhook was never set up, or broke, is read as always while the others are spared. It spares fewer reads: a repository that nobody touches is read as usual.
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
LAST_WEBHOOK_REPO = {}      # repository -> when an accepted event for it arrived (savings.webhook_live_per_repo); bounded
MAX_REPOS = 5000


def _int(block, key, low, high, default):
    value = block.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default


def settings(config):
    block = config.get("savings") if isinstance(config, dict) and isinstance(config.get("savings"), dict) else {}
    feeds = block.get("feeds") if isinstance(block.get("feeds"), dict) else {}
    method = feeds.get("method")
    return {"webhook_first": block.get("webhook_first") is True, "webhook_live_per_repo": block.get("webhook_live_per_repo") is True, "webhook_window_minutes": _int(block, "webhook_window_minutes", 5, 1440, 60),
            "webhook_full_minutes": _int(block, "webhook_full_minutes", 30, 10080, 360),
            "feeds": {"enabled": feeds.get("enabled") is True and not (isinstance(config, dict) and config.get("airgapped") is True), "method": method if method in METHODS else "atom",
                      "max_age_minutes": _int(feeds, "max_age_minutes", 15, 10080, 240)}}


def note_webhook(now=None, repo=None):
    """The webhook delivered an event (a signed one that was accepted): while it keeps doing so, `webhook_first` may stretch the slow turn of the cold repositories. `repo` = the repository the event
    was about (remembered for `savings.webhook_live_per_repo`)."""
    now = time.time() if now is None else now
    LAST_WEBHOOK["at"] = now
    if isinstance(repo, str) and NAME_RE.match(repo):
        if len(LAST_WEBHOOK_REPO) >= MAX_REPOS and repo not in LAST_WEBHOOK_REPO:
            for name in sorted(LAST_WEBHOOK_REPO, key=LAST_WEBHOOK_REPO.get)[:MAX_REPOS // 10]:      # the oldest tenth goes: the memory never grows with the number of repositories
                LAST_WEBHOOK_REPO.pop(name, None)
        LAST_WEBHOOK_REPO[repo] = now


def clock_skew(config):
    """`webhook.clock_skew_s` (300 by default, 0..3600): how far ahead of this computer's clock a moment may lie and still count as the same moment."""
    block = config.get("webhook") if isinstance(config, dict) and isinstance(config.get("webhook"), dict) else {}
    return _int(block, "clock_skew_s", 0, 3600, 300)


def settled(last, now, config):
    """The moment an event arrived, as it counts now. The clock is the one of this computer, never the one of the delivery: if it was set back after the event was marked (the mark lies ahead of it), the event still
    happened, so it counts as having arrived now and ages from here; a mark more than a day ahead is not believed (0.0)."""
    if last <= now + clock_skew(config):
        return last
    return now if last <= now + 24 * 3600.0 else 0.0


def webhook_alive(config, now=None, repo=None):
    """True when the webhook counts as alive. With `savings.webhook_live_per_repo` on and a `repo` given, it is the events of THAT repository that count; a repository without an event of its own in the
    window is not alive, whatever the others did (without a repo the answer is the general one)."""
    cfg = settings(config)
    now = time.time() if now is None else now
    if not cfg["webhook_first"]:
        return False
    per_repo = cfg["webhook_live_per_repo"] and repo is not None
    held = LAST_WEBHOOK_REPO.get(repo, 0.0) if per_repo else LAST_WEBHOOK["at"]
    last = settled(held, now, config)
    if last != held:      # the mark lay ahead of the clock: from now on it is the moment the event was seen, so it ages
        if per_repo:
            LAST_WEBHOOK_REPO[repo] = last
        else:
            LAST_WEBHOOK["at"] = last
    return last > 0 and now - last <= cfg["webhook_window_minutes"] * 60


def live_repos(config, now=None):
    """How many repositories had an event of their own in the window (what `savings.webhook_live_per_repo` judges by); 0 when the switch is off."""
    cfg = settings(config)
    if not cfg["webhook_live_per_repo"]:
        return 0
    return sum(1 for at in (settled(at, now, config) for at in list(LAST_WEBHOOK_REPO.values())) if at > 0 and now - at <= cfg["webhook_window_minutes"] * 60)


def quiet_by_webhook(config, entry, now=None, repo=None):
    """True when the slow turn of a cold repository (with the cached `entry`) may pass because the webhook is alive and the last full read is not older than the safety net."""
    now = time.time() if now is None else now
    if not entry or not webhook_alive(config, now, repo):
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
