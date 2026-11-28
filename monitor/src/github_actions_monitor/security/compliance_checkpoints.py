# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Signed checkpoints of the chain of the log of actions (`audit_checkpoints.enabled`, off by default) and the purge of its old parts. Standard library only.

The chain of the log shows a line that was changed, but whoever can write the file can rewrite it all with new hashes. A checkpoint is the hash of one line signed with a key of the installation
(HMAC-SHA256): one at the first line, then one at least every hour and every 1000 lines of a running monitor. The key lives in config/audit_checkpoint.key, apart from the log; the variable
MONITOR_AUDIT_KEY_FILE puts it elsewhere (another volume, a mounted secret). With checkpoints on, the anchor of the log is signed too and a cut of the tail that is followed by a new line is
written into that line (`gap_after`). What is proved is bounded by the key: whoever can read it can sign.

`verify` walks the chain and then asks that every checkpoint still be in it, with a valid signature. `purge` removes whole rotated files that are older than the limit and signs the hash the chain
goes on from, so what is left still verifies as the continuation of what was removed."""
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from github_actions_monitor.security import private_io
from github_actions_monitor.storage import locks

KEY_ENV = "MONITOR_AUDIT_KEY_FILE"
KEY_NAME = "audit_checkpoint.key"
EVERY_SECONDS = 3600
EVERY_LINES = 1000
_SINCE = {}      # path of the log -> lines written by this process since its last checkpoint


def enabled(config):
    block = config.get("audit_checkpoints") if isinstance(config, dict) else None
    return isinstance(block, dict) and block.get("enabled") is True


def key_path():
    chosen = os.environ.get(KEY_ENV, "").strip()
    if chosen:
        return Path(chosen)
    from github_actions_monitor.util import paths
    return paths.folder("config") / KEY_NAME


def load_key(create=False):
    """The key of the installation as bytes, or None. With `create` it is made when there is none (never over a file that is there but cannot be understood)."""
    where = key_path()
    try:
        text = where.read_text(encoding="ascii").strip()
        return bytes.fromhex(text) if len(text) == 64 else None
    except FileNotFoundError:
        if not create:
            return None
    except (OSError, ValueError):
        return None
    try:
        private_io.private_dir(where.parent)
        text = secrets.token_hex(32)
        private_io.write_private(where, text + "\n")
        return bytes.fromhex(text)
    except OSError:
        return None


def _sign(key, body):
    return hmac.new(key, json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"), hashlib.sha256).hexdigest()


def anchor_mac(last_hash):
    key = load_key(create=True)
    return _sign(key, {"anchor": last_hash}) if key else ""


def marks_path(where):
    return Path(where).with_name(Path(where).name + ".checkpoints")


def read_marks(where):
    try:
        lines = marks_path(where).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            item = json.loads(line)
        except ValueError:
            item = None
        out.append(item if isinstance(item, dict) else {"damaged": True})
    return out


def mark(where, line_hash, now=None, kind="mark"):
    """Signs the hash of a line. Returns the checkpoint, or None when it could not be signed or written."""
    key = load_key(create=True)
    if key is None or not line_hash:
        return None
    body = {"at": int(time.time() if now is None else now), "hash": line_hash, "kind": kind}
    body["mac"] = _sign(key, body)
    try:
        with private_io.open_append(marks_path(where)) as handle:
            handle.write(json.dumps(body, separators=(",", ":")) + "\n")
    except OSError:
        return None
    _SINCE[str(where)] = 0
    return body


def after_write(where, line_hash, now=None):
    """Called after each line of the log, under its lock: a checkpoint when there is none yet, when an hour passed since the last one or after 1000 lines of this process."""
    now = time.time() if now is None else now
    name = str(where)
    _SINCE[name] = _SINCE.get(name, 0) + 1
    marks = read_marks(where)
    last = marks[-1].get("at") if marks else None
    if not isinstance(last, int) or now - last >= EVERY_SECONDS or now < last - EVERY_SECONDS or _SINCE[name] >= EVERY_LINES:
        mark(where, line_hash, now)


def _segments(where):
    """[(name, lines)] of the log, the oldest first."""
    from github_actions_monitor.security import audit_log
    where = Path(where)
    files = [(f"rotated-{n}", audit_log._read_lines(audit_log.generation(where, n))) for n in range(21, 0, -1)] + [("active", audit_log._read_lines(where))]
    return [(name, lines) for name, lines in files if lines]


def entries(where):
    """Every readable line of the log as a dictionary, the oldest first."""
    out = []
    for _name, lines in _segments(where):
        for line in lines:
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict):
                out.append(item)
    return out


def verify(target=None, from_entry=1):
    """The answer of `audit_log.verify` plus {"checkpoints", "bad_checkpoints", "gaps", "key", "purged"}. `from_entry` (1 = the first line kept) checks the chain from that line on."""
    from github_actions_monitor.security import audit_log
    where = Path(target) if target else audit_log.path()
    found = audit_log.verify(where)
    kept = entries(where)
    if from_entry > 1:
        lines = [json.dumps(e, ensure_ascii=False) for e in kept[from_entry - 1:]]
        broken, count, last, _first = audit_log._walk(lines, None)
        anchor = audit_log._read_anchor(where)
        ok = broken is None and (anchor is None or anchor == last)
        found = {"ok": ok, "entries": count, "broken_at": None if broken is None else broken + from_entry - 1, "segments": found["segments"], "complete": found["complete"], "from": from_entry}
    key = load_key()
    marks = read_marks(where)
    hashes = {e.get("hash") for e in kept}
    first_prev = kept[0].get("prev") if kept else ""
    bad, purged = [], False
    for number, item in enumerate(marks, 1):
        if key is None:
            break
        body = {k: v for k, v in item.items() if k != "mac"}
        if item.get("damaged") or not hmac.compare_digest(str(item.get("mac", "")), _sign(key, body)):
            bad.append({"checkpoint": number, "why": "signature"})
        elif item.get("kind") == "purge":
            purged = purged or item.get("hash") == first_prev
        elif item.get("hash") not in hashes:
            bad.append({"checkpoint": number, "why": "missing_line"})
    gaps = sum(1 for e in kept if "gap_after" in e)
    try:
        anchor = json.loads(audit_log.anchor_path(where).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        anchor = {}
    if key is not None and isinstance(anchor, dict) and anchor.get("mac") and not hmac.compare_digest(str(anchor["mac"]), _sign(key, {"anchor": anchor.get("hash")})):
        bad.append({"checkpoint": 0, "why": "anchor_signature"})
    out = dict(found, checkpoints=len(marks), bad_checkpoints=bad, gaps=gaps, key="none" if not marks else "ok" if key is not None else "missing", purged=purged)
    if purged:
        out["complete"] = True      # the chain goes on from the signed end of what was purged
    if bad or gaps or out["key"] == "missing":
        out["ok"] = False
    return out


def purge(config, before, target=None, now=None, dry_run=False):
    """Removes the rotated files whose newest line is older than `before` (epoch seconds), the oldest first, signs where the chain goes on and writes the purge in the log. Returns
    {"files", "entries", "reason"}; nothing is removed under a legal hold, with a broken chain or when it cannot be signed."""
    from github_actions_monitor.security import audit_log
    from github_actions_monitor.storage import retention
    where = Path(target) if target else audit_log.path()
    out = {"files": 0, "entries": 0, "reason": ""}
    if retention.held(config):
        return dict(out, reason="legal_hold")
    limit = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(before))
    with locks.os_lock(where):
        if not verify(where)["ok"]:
            return dict(out, reason="chain_broken")
        old, tail, count = [], "", 0
        for number in range(21, 0, -1):
            part = audit_log.generation(where, number)
            lines = audit_log._read_lines(part)
            if not lines:
                continue
            try:
                last = json.loads(lines[-1])
                newest, last_hash = str(last["at"]), str(last["hash"])
            except (ValueError, KeyError, TypeError):
                break
            if newest >= limit:
                break
            old.append(part)
            tail, count = last_hash, count + len(lines)
        out.update(files=len(old), entries=count)
        if not old or dry_run:
            return out
        if load_key(create=True) is None:
            return dict(out, files=0, entries=0, reason="no_key")
        for part in old:
            part.unlink()
        remaining = {e.get("hash") for e in entries(where)}
        marks = [m for m in read_marks(where) if m.get("hash") in remaining and m.get("kind") != "purge"]
        private_io.write_private(marks_path(where), "".join(json.dumps(m, separators=(",", ":")) + "\n" for m in marks))
        mark(where, tail, now, kind="purge")
    audit_log.record(config, "audit_purge", target="log_of_actions", details={"files": out["files"], "entries": out["entries"], "before": limit}, now=now)
    return out
