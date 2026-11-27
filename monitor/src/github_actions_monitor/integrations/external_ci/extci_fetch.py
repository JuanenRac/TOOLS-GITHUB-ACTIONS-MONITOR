# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The only way out to an external CI service: GET, through netguard (the address that is judged is the one that is used), no redirect, a limit of size and of time, the expected content type."""
import base64
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request

from github_actions_monitor.security import netguard

AGENT = "github-actions-monitor"
CHUNK = 65536


class Failed(Exception):
    """A read that did not give an answer. `reason` is a stable code: private_target, redirect, http_<n>, rate_limited, too_big, not_json, timeout, unreachable, bad_url, token_missing, token_clear."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class Reader:
    def __init__(self, source, cfg, use_proxy=False, opener=None):
        self.source, self.cfg, self.use_proxy = source, cfg, use_proxy
        self.opener = opener or netguard.open_url
        self.cache = {}      # {url: (etag, last_modified, parsed)}, kept by the engine between reads

    def url(self, path):
        base = self.source["url"].rstrip("/")
        parts = urllib.parse.urlsplit(base)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise Failed("bad_url")
        return base + path

    def _headers(self, url):
        headers = {"User-Agent": AGENT, "Accept": "application/json"}
        name = self.source.get("token_env")
        if not name:
            return headers
        value = os.environ.get(name, "").strip()      # only the NAME of the variable is in the configuration file
        if not value:
            raise Failed("token_missing")
        if not url.startswith("https://") and not (self.cfg["allow_private_targets"] and netguard.only_private(url)):
            raise Failed("token_clear")      # without TLS a token only goes to this computer or to the local network, and only when that is allowed
        kind = self.source["kind"]
        if kind == "gitlab":
            headers["PRIVATE-TOKEN"] = value
        elif kind in ("jenkins", "azure"):
            pair = value if kind == "jenkins" else ":" + value
            headers["Authorization"] = "Basic " + base64.b64encode(pair.encode("utf-8")).decode("ascii")
        else:
            headers["Authorization"] = "Bearer " + value
        return headers

    def _open(self, url, extra=None):
        headers = self._headers(url)
        headers.update(extra or {})
        try:
            return self.opener(urllib.request.Request(url, headers=headers, method="GET"), timeout=self.cfg["timeout_s"], allow_private=self.cfg["allow_private_targets"],
                               use_proxy=self.use_proxy, follow_redirects=False)
        except urllib.error.HTTPError as error:
            if error.code == 304:
                raise
            if 300 <= error.code < 400:
                raise Failed("redirect") from None
            raise Failed("rate_limited" if error.code == 429 else f"http_{error.code}") from None
        except (urllib.error.URLError, OSError, ValueError) as error:
            cause = getattr(error, "reason", error)
            if isinstance(cause, netguard.Refused):
                raise Failed("private_target") from None
            raise Failed("timeout" if isinstance(cause, (socket.timeout, TimeoutError)) else "unreachable") from None

    def json(self, path):
        url = self.url(path)
        kept = self.cache.get(url)
        extra = {}
        if kept and kept[0]:
            extra["If-None-Match"] = kept[0]
        if kept and kept[1]:
            extra["If-Modified-Since"] = kept[1]
        try:
            with self._open(url, extra) as answer:
                kind = str(answer.headers.get("Content-Type") or "").lower()
                raw = answer.read(self.cfg["max_bytes"] + 1)
                etag, modified = answer.headers.get("ETag"), answer.headers.get("Last-Modified")
        except urllib.error.HTTPError:      # 304: what was read before still stands
            if kept:
                return kept[2]
            raise Failed("http_304") from None
        except OSError:
            raise Failed("unreachable") from None
        if len(raw) > self.cfg["max_bytes"]:
            raise Failed("too_big")
        if "json" not in kind:
            raise Failed("not_json")
        try:
            data = json.loads(raw.decode("utf-8", "replace"))
        except (ValueError, RecursionError):
            raise Failed("not_json") from None
        if etag or modified:
            self.cache[url] = (etag, modified, data)
        return data

    def tail(self, path, keep, total=None):
        """The END of a text (a log): at most `keep` bytes, reading at most `total` (external_ci.max_bytes). (text, cut)."""
        total = total or self.cfg["max_bytes"]
        seen, kept, cut = 0, b"", False
        try:
            with self._open(self.url(path), {"Accept": "text/plain", "Range": f"bytes=-{keep}"}) as answer:
                kind = str(answer.headers.get("Content-Type") or "text/plain").lower()
                if not (kind.startswith("text/") or "json" in kind or "octet-stream" in kind):
                    raise Failed("not_json")
                while seen < total:
                    piece = answer.read(min(CHUNK, total - seen))
                    if not piece:
                        break
                    seen += len(piece)
                    kept += piece
                    if len(kept) > keep:
                        kept, cut = kept[-keep:], True
                cut = cut or seen >= total or getattr(answer, "status", 200) == 206
        except urllib.error.HTTPError:
            raise Failed("http_304") from None
        except OSError:
            raise Failed("unreachable") from None
        return kept.decode("utf-8", "replace"), cut
