# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Conditional requests for the GitHub API: a read that did not change answers `304 Not Modified` and costs no quota.

The monitor keeps, for each endpoint it reads, the `ETag` and the body of the last answer. The next read sends `If-None-Match`; a `304` means "the same as before", so the stored
body is used and the allowance is not touched. Only the answers of GET reads are stored; nothing is sent to GitHub except the ETag GitHub itself gave.

  cache.etag.enabled   on by default; off = every read is a plain read
  cache.etag.ttl_hours an entry older than this is read again in full (default 24)

The cache lives in `etag_cache.json` next to the monitor (a local file, never published; a broken or missing file is simply an empty cache). `saved` counts the reads
answered with 304 since the cache was created, so the page and /metrics can say how much quota was saved.
"""
import json
import os
import re
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE_FILE = HERE / "etag_cache.json"
MAX_ENTRIES = 600
ETAG_RE = re.compile(r'^(?:W/)?"[A-Za-z0-9._+/=-]{1,200}"$')
STATUS_RE = re.compile(r"^HTTP/\S+\s+(\d{3})")


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
    def __init__(self, path=CACHE_FILE, ttl_hours=24, enabled=True):
        self.path, self.ttl, self.enabled = Path(path), max(1, ttl_hours) * 3600, enabled
        self.lock = threading.Lock()
        self.entries = {}
        self.saved = 0
        self.calls = 0
        self.invalid = 0       # entries thrown away because their body was not what the API sent (a damaged file)
        self.dirty = False
        self._load()

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("entries"), dict):
                self.entries = {k: v for k, v in data["entries"].items() if isinstance(v, dict) and ETAG_RE.match(str(v.get("etag", ""))) and isinstance(v.get("data"), (dict, list))}
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
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False

    def etag_for(self, endpoint, now=None):
        """The stored ETag of an endpoint that is still fresh, else None."""
        if not self.enabled:
            return None
        entry = self.entries.get(endpoint)
        if not entry or (now or time.time()) - entry.get("at", 0) > self.ttl:
            return None
        return entry["etag"]

    def fetch(self, endpoint, run, now=None):
        """(data, status) where status is "304" (answered from the cache), "200" (read in full) or "plain" (cache off / no ETag).
        `run(args)` runs `gh` and returns (returncode, stdout, stderr); an error that is not a 304 is raised as RuntimeError."""
        etag = self.etag_for(endpoint, now)
        args = ["api", "-i"] + (["-H", f"If-None-Match: {etag}"] if etag else []) + [endpoint]
        code, out, err = run(args)
        status, headers, body = split_response(out)
        with self.lock:
            self.calls += 1
            damaged = status == 304 and etag and not isinstance(self.entries.get(endpoint, {}).get("data"), (dict, list))
            if damaged:
                self.entries.pop(endpoint, None)      # a damaged entry is a cache miss: read it again in full
                self.invalid += 1
                self.dirty = True
                etag = None
        if damaged:
            code, out, err = run(["api", "-i", endpoint])
            status, headers, body = split_response(out)
        with self.lock:
            if status == 304 and etag:
                entry = self.entries[endpoint]
                entry["at"] = now or time.time()
                self.saved += 1
                self.dirty = True
                return entry["data"], "304"
        if code != 0 or status not in (200, 0):
            raise RuntimeError((err or out or "gh failed").strip()[:300])
        try:
            data = json.loads(body) if body.strip() else None
        except ValueError:
            raise RuntimeError("the answer of the API is not valid JSON") from None
        new_tag = headers.get("etag", "")
        if self.enabled and status == 200 and ETAG_RE.match(new_tag):
            with self.lock:
                self.entries[endpoint] = {"etag": new_tag, "at": now or time.time(), "data": data}
                self.dirty = True
            return data, "200"
        return data, "plain"

    def stats(self):
        return {"enabled": self.enabled, "entries": len(self.entries), "saved": self.saved, "calls": self.calls, "invalid": self.invalid}
