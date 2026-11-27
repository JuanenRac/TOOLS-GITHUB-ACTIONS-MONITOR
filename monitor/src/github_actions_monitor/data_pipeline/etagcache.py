# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Conditional requests for the GitHub API: a read that did not change answers `304 Not Modified` and costs no quota.

The monitor keeps, for each endpoint it reads, the `ETag` and the body of the last answer. The next read sends `If-None-Match`; a `304` means "the same as before", so the stored
body is used and the allowance is not touched. Only the answers of GET reads are stored; nothing is sent to GitHub except the ETag GitHub itself gave.

  cache.etag.enabled            on by default; off = every read is a plain read
  cache.etag.ttl_hours          an entry older than this is read again in full (default 24)
  cache.etag.skip_stateful      on by default; the endpoints that describe a state in motion (jobs of a run, check suites, one run) are always read in full
  cache.etag.revalidate_active  on by default; a list of runs whose last body still had a run that was not finished is read in full, never with `If-None-Match`
  cache.negative_ttl_s          seconds a refusal (403 that is not a rate limit, 404) is remembered so it is not asked again every cycle (default 300; 0 = never remembered)

Every entry is kept under the identity of the credential that read it (a short fingerprint, never the credential): the same endpoint read with another token has its own entry, so a `304` can never
hand back the body of another identity. A file written before this (entries without an identity) is read as an empty cache once.

The cache lives in `etag_cache.json` next to the monitor (a local file, never published; a broken or missing file is simply an empty cache). `saved` counts the reads
answered with 304 since the cache was created, so the page and /metrics can say how much quota was saved.
"""
import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path
from github_actions_monitor.security import private_io

from github_actions_monitor.util import paths
CACHE_FILE = paths.place("etag_cache.json")
MAX_ENTRIES = 600
ETAG_RE = re.compile(r'^(?:W/)?"[A-Za-z0-9._+/=-]{1,200}"$')
STATUS_RE = re.compile(r"^HTTP/\S+\s+(\d{3})")
KEY_RE = re.compile(r"^[0-9a-f]{8}\|")
ACTIVE_STATES = {"queued", "in_progress", "waiting", "requested", "pending"}
# endpoints that describe a state which changes while it is read: the jobs of a run, one run, its attempts, check suites and check runs, the combined status of a commit
STATEFUL_RE = re.compile(r"/actions/runs/\d+|/actions/jobs/\d+|/check-suites|/check-runs|/commits/[^/?]+/status")
NEGATIVE_MAX = 500


def fingerprint(secret):
    """A short fingerprint of a credential (8 hex characters of its SHA-256), or "00000000" when the monitor uses the own login of `gh`. The credential itself is never kept."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:8] if secret else "00000000"


def is_stateful(endpoint):
    return bool(STATEFUL_RE.search(endpoint or ""))


def has_active(data):
    """True when a stored body lists something that was not finished (a run queued or in progress, a job, a check run): its next answer may differ even when GitHub says 304."""
    if not isinstance(data, dict):
        return False
    for key in ("workflow_runs", "jobs", "check_runs", "check_suites"):
        items = data.get(key)
        if isinstance(items, list) and any(isinstance(i, dict) and (i.get("status") in ACTIVE_STATES) for i in items):
            return True
    return False


def split_response(text):
    """(status code, {lower-case header: value}, body text) of the output of `gh api -i`. (0, {}, text) when it does not look like a response."""
    text = text or ""
    head, sep, body = text.replace("\r\n", "\n").partition("\n\n")
    lines = head.split("\n")
    match = STATUS_RE.match(lines[0]) if lines else None
    if not match:
        return 0, {}, text
    headers = {}
    for line in lines[1:]:
        key, colon, value = line.partition(":")
        if colon:
            headers[key.strip().lower()] = value.strip()
    return int(match.group(1)), headers, body


class EtagCache:
    def __init__(self, path=CACHE_FILE, ttl_hours=24, enabled=True, negative_ttl=300, skip_stateful=True, revalidate_active=True, identity=None):
        self.path, self.ttl, self.enabled = Path(path), max(1, ttl_hours) * 3600, enabled
        self.negative_ttl = max(0, int(negative_ttl))
        self.skip_stateful, self.revalidate_active = bool(skip_stateful), bool(revalidate_active)
        self.identity = identity or (lambda: "00000000")      # the fingerprint of the credential in use now
        self.denied = {}             # key -> (until, message): refusals remembered for a short time
        self.lock = threading.Lock()
        self.entries = {}
        self.saved = 0
        self.calls = 0
        self.invalid = 0       # entries thrown away because their body was not what the API sent (a damaged file)
        self.no_etag = 0       # full answers that carried no ETag (a proxy that strips it turns the cache into plain reads without a word)
        self.misses = 0        # reads answered in full (200) that could have been 304
        self.skipped_stateful = 0    # reads sent without If-None-Match because the endpoint describes a state in motion
        self.skipped_active = 0      # reads sent without If-None-Match because the last body still had something running
        self.denied_hits = 0         # reads not made because the refusal was remembered
        self._mark = (0, 0, 0, 0)    # calls, saved, misses and no_etag at the end of the previous cycle (what `end_cycle` subtracts)
        self.recent = []             # the last cycles, newest last: {"calls", "saved", "misses", "no_etag", "hit_pct"}; memory only
        self.dirty = False
        self._load()

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("entries"), dict):
                self.entries = {k: v for k, v in data["entries"].items() if isinstance(v, dict) and KEY_RE.match(str(k)) and ETAG_RE.match(str(v.get("etag", ""))) and isinstance(v.get("data"), (dict, list))}
                self.saved = int(data.get("saved") or 0)
        except (OSError, ValueError, TypeError):
            self.entries = {}

    def save(self):
        """Writes the file when something changed (atomic); never raises."""
        with self.lock:
            if not self.dirty:
                return False
            oldest = sorted(self.entries.items(), key=lambda kv: kv[1].get("at", 0))
            for key, _ in oldest[:max(0, len(oldest) - MAX_ENTRIES)]:
                del self.entries[key]
            payload = {"saved": self.saved, "entries": self.entries}
            self.dirty = False
        try:
            tmp = self.path.with_name(self.path.name + ".tmp")
            private_io.write_tmp(tmp, json.dumps(payload))
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False

    def key_of(self, endpoint):
        return f"{self.identity()}|{endpoint}"

    def etag_for(self, endpoint, now=None, key=None):
        """The stored ETag of an endpoint that is still fresh, else None (also None when the read must be made in full: a state in motion)."""
        if not self.enabled:
            return None
        entry = self.entries.get(key or self.key_of(endpoint))
        if not entry or (now or time.time()) - entry.get("at", 0) > self.ttl:
            return None
        if self.skip_stateful and is_stateful(endpoint):
            self.skipped_stateful += 1
            return None
        if self.revalidate_active and has_active(entry.get("data")):
            self.skipped_active += 1
            return None
        return entry["etag"]

    def refused(self, key, now=None):
        """The remembered message of a refusal that is still fresh, else None."""
        hit = self.denied.get(key)
        if not hit:
            return None
        if (now or time.time()) >= hit[0]:
            self.denied.pop(key, None)
            return None
        return hit[1]

    def remember_refusal(self, key, message, now=None):
        """A 404, or a 403 that is not a rate limit, is remembered for `negative_ttl` seconds; anything else (a network error, a 5xx, a rate limit) is never remembered."""
        text = (message or "").lower()
        refusal = ("404" in text or "not found" in text or "403" in text or "forbidden" in text or "disabled" in text) and "rate limit" not in text and "abuse" not in text and "retry-after" not in text
        if not self.negative_ttl or not refusal:
            return
        if len(self.denied) >= NEGATIVE_MAX:
            self.denied.clear()
        self.denied[key] = ((now or time.time()) + self.negative_ttl, message)

    def fetch(self, endpoint, run, now=None):
        """(data, status) where status is "304" (answered from the cache), "200" (read in full) or "plain" (cache off / no ETag).
        `run(args)` runs `gh` and returns (returncode, stdout, stderr); an error that is not a 304 is raised as RuntimeError."""
        key = self.key_of(endpoint)
        with self.lock:
            remembered = self.refused(key, now)
            if remembered is not None:
                self.denied_hits += 1
                raise RuntimeError(remembered)
            etag = self.etag_for(endpoint, now, key)
        args = ["api", "-i"] + (["-H", f"If-None-Match: {etag}"] if etag else []) + [endpoint]
        code, out, err = run(args)
        status, headers, body = split_response(out)
        with self.lock:
            self.calls += 1
            damaged = status == 304 and etag and not isinstance(self.entries.get(key, {}).get("data"), (dict, list))
            if damaged:
                self.entries.pop(key, None)      # a damaged entry is a cache miss: read it again in full
                self.invalid += 1
                self.dirty = True
                etag = None
        if damaged:
            code, out, err = run(["api", "-i", endpoint])
            status, headers, body = split_response(out)
        with self.lock:
            if status == 304 and etag:
                entry = self.entries[key]
                entry["at"] = now or time.time()
                self.saved += 1
                self.dirty = True
                return entry["data"], "304"
        if code == 0 and status == 204:      # an answer without a body ("yes, it is on")
            with self.lock:
                self.denied.pop(key, None)
            return None, "plain"
        if code != 0 or status not in (200, 0):
            message = (err or out or "gh failed").strip()[:300]
            with self.lock:
                self.remember_refusal(key, message, now)
            raise RuntimeError(message)
        try:
            data = json.loads(body) if body.strip() else None
        except ValueError:
            raise RuntimeError("the answer of the API is not valid JSON") from None
        new_tag = headers.get("etag", "")
        if self.enabled and status == 200 and ETAG_RE.match(new_tag):
            with self.lock:
                self.denied.pop(key, None)
                if self.entries.get(key, {}).get("etag") != new_tag and key in self.entries:
                    self.misses += 1
                self.entries[key] = {"etag": new_tag, "at": now or time.time(), "data": data}
                self.dirty = True
            return data, "200"
        if self.enabled and status == 200:
            with self.lock:
                self.no_etag += 1
        return data, "plain"

    def last_copy(self, endpoint):
        """(data, age_seconds) of the stored answer of an endpoint whatever its age (the caller decides how old is too old), or None."""
        with self.lock:
            entry = self.entries.get(self.key_of(endpoint))
            if not entry or not isinstance(entry.get("data"), (dict, list)):
                return None
            return entry["data"], max(0, int(time.time() - entry.get("at", 0)))

    def invalidate(self, repo):
        """Drops the stored answers of one repository (the endpoints of `/repos/<owner>/<repo>/`), whatever the identity. Returns how many were dropped."""
        marker = f"/{repo}/"
        with self.lock:
            gone = [k for k in self.entries if marker in k or k.endswith(f"/{repo}")]
            for key in gone:
                del self.entries[key]
            for key in [k for k in self.denied if marker in k or k.endswith(f"/{repo}")]:
                del self.denied[key]
            if gone:
                self.dirty = True
            return len(gone)

    def end_cycle(self, keep=30):
        """What the cycle that just ended did with the conditional reads: the difference of the counters since the previous call, kept for the last `keep` cycles and returned (the line of the log of the cycle and the doctor read it)."""
        with self.lock:
            now = (self.calls, self.saved, self.misses, self.no_etag)
            calls, saved, misses, no_etag = (max(0, a - b) for a, b in zip(now, self._mark))
            self._mark = now
            row = {"calls": calls, "saved": saved, "misses": misses, "no_etag": no_etag, "hit_pct": round(100.0 * saved / calls, 1) if calls else None}
            self.recent.append(row)
            del self.recent[:-max(1, int(keep))]
            return row

    def stats(self):
        """The counters of the cache. `hit_pct` is the share of conditional calls answered with 304; `no_etag` counts full answers without an ETag (something between here and GitHub strips it)."""
        calls = self.calls
        return {"enabled": self.enabled, "entries": len(self.entries), "saved": self.saved, "calls": calls, "invalid": self.invalid, "no_etag": self.no_etag, "misses": self.misses,
                "skipped_stateful": self.skipped_stateful, "skipped_active": self.skipped_active, "denied": len(self.denied), "denied_hits": self.denied_hits,
                "hit_pct": round(100.0 * self.saved / calls, 1) if calls else None, "recent_cycles": list(self.recent)}
