# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The allowance of GitHub by account and by bucket, and the tightest bucket (the chip of the header).

GitHub does not have one allowance: the free `rate_limit` call answers with several buckets (core, search, graphql, code_search, ...) for each token. Every source the monitor reads with (the login of
the user, the GitHub App of an installation, a second read-only account) has its own set. This module keeps the last answer of each source, in memory, and says:

  * `view()`      the breakdown by source and bucket, with the share used and the renewal time (the Quota tab and /api/quota);
  * `tightest()`  the bucket with the least allowance left (by share), with how many other buckets are in use, so the chip shows the one that is going to stop the monitor first.

Nothing is read from GitHub here: `note()` is given what the cycle already read.
"""
import threading

BUCKETS = ("core", "graphql", "search", "code_search", "integration_manifest", "code_scanning_upload", "actions_runner_registration", "scim", "dependency_snapshots", "audit_log", "source_import")
HELD = {}
LOCK = threading.Lock()


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def parse_resources(resources):
    """[{"bucket", "limit", "remaining", "used", "used_percent", "reset"}] from the `resources` of `rate_limit`; a bucket that is not a plain word with numbers is left out."""
    out = []
    if not isinstance(resources, dict):
        return out
    for name, row in resources.items():
        if not isinstance(name, str) or not name.replace("_", "").isalnum() or not isinstance(row, dict):
            continue
        limit, left = _int(row.get("limit")), _int(row.get("remaining"))
        if not limit or left is None:
            continue
        used = max(0, limit - left)
        out.append({"bucket": name[:40], "limit": limit, "remaining": left, "used": used, "used_percent": round(100.0 * used / limit, 1), "reset": row.get("reset")})
    return sorted(out, key=lambda r: (BUCKETS.index(r["bucket"]) if r["bucket"] in BUCKETS else 99, r["bucket"]))


def note(source, resources):
    """Keeps the buckets of one source (`user`, `app`, `extra`) as the last `rate_limit` call gave them."""
    rows = parse_resources(resources)
    if rows and isinstance(source, str):
        with LOCK:
            HELD[source[:20]] = rows
    return rows


def reset():
    with LOCK:
        HELD.clear()


def tightest(held=None, ignore_idle=True):
    """The bucket with the biggest share used among every source: {"source", "bucket", "limit", "remaining", "used_percent", "reset", "others": n of the other buckets that have been used}, or None.
    A bucket nobody has used (nothing spent) never wins over one that was used, so an unused `search` of 30 calls does not hide `core`."""
    held = HELD if held is None else held
    with LOCK:
        rows = [dict(r, source=src) for src, buckets in held.items() for r in buckets]
    if not rows:
        return None
    used = [r for r in rows if r["used"] > 0] if ignore_idle else rows
    pool = used or rows
    best = max(pool, key=lambda r: (r["used_percent"], -r["remaining"]))
    return {"source": best["source"], "bucket": best["bucket"], "limit": best["limit"], "remaining": best["remaining"], "used_percent": best["used_percent"], "reset": best.get("reset"),
            "others": max(0, len(used) - 1)}


def view(held=None, trend=None, ignore_idle=True):
    """{"sources": [{"source", "buckets": [...], "worst": {...}}], "tightest": {...} or None, "trend": {...}}: the breakdown for the Quota tab."""
    held = HELD if held is None else held
    with LOCK:
        snap = {src: list(rows) for src, rows in held.items()}
    sources = []
    for src in sorted(snap):
        rows = snap[src]
        worst = max(rows, key=lambda r: (r["used_percent"], -r["remaining"])) if rows else None
        sources.append({"source": src, "buckets": rows, "worst": worst})
    return {"sources": sources, "tightest": tightest(snap, ignore_idle), "trend": trend or {}}


def chip(held=None, ignore_idle=True):
    """What the header chip writes: the tightest bucket as plain data (the page makes the text in its own language) and the lines of the breakdown for the tooltip."""
    best = tightest(held, ignore_idle)
    if not best:
        return None
    with LOCK:
        source = {src: rows for src, rows in (HELD if held is None else held).items()}
    lines = [{"source": src, "bucket": r["bucket"], "remaining": r["remaining"], "limit": r["limit"], "used_percent": r["used_percent"]} for src, rows in sorted(source.items()) for r in rows if r["used"] > 0][:12]
    return dict(best, breakdown=lines)
