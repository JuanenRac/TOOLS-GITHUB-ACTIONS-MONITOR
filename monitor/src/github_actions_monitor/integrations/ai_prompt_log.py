# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The optional local record of what the AI of the monitor was asked and what it answered (OFF by default: `ai.prompt_log.enabled`).

What is guaranteed here (each point has its test, tests/test_mon107_prompt_log.py):
  * off by default; with it off nothing is written and the file is not even created;
  * only the text that ALREADY went to the model is kept (the cleaned one: secrets, the words and patterns of `ai.redact`), cleaned once more, cut to a fixed size, with the answer cleaned and cut too; the
    system prompt is not kept (it is the same text every time: only its length), and never a key, a header or an address of the provider;
  * a call that is answered from the cache is not a prompt and is not written; a call that failed is written without a reply, with the reason class;
  * it lives in the folder of the logs, it is a file of its own, it is NOT part of the backup of the installation, of the zip or of the files the AI tools read, and only an administrator reads it
    (`GET /api/ai/prompts`) or empties it (`POST /api/ai/prompts/clear`);
  * it keeps the newest `ai.prompt_log.keep` lines: when the file grows past a quarter more it is rewritten with the last ones (the retention of this log)."""
import json
import os
import re
import time
from pathlib import Path

from github_actions_monitor.security import glob_patterns, private_io, redactor
from github_actions_monitor.storage import locks
from github_actions_monitor.util import paths

LOG_FILE = paths.place("ai_prompts.jsonl")
DEFAULTS = {"enabled": False, "keep": 200}
KEEP_BOUNDS = (10, 5000)
PROMPT_CHARS = 4000
REPLY_CHARS = 1500
FIELDS = ("at", "kind", "provider", "model", "ok", "reason", "system_chars", "prompt", "reply")


def settings(ai):
    """The block `prompt_log` of a normalised `ai` configuration with safe values: a broken value gives the default (so a damaged file never turns the record on)."""
    block = ai.get("prompt_log") if isinstance(ai, dict) and isinstance(ai.get("prompt_log"), dict) else {}
    keep = block.get("keep")
    return {"enabled": block.get("enabled") is True, "keep": keep if isinstance(keep, int) and not isinstance(keep, bool) and KEEP_BOUNDS[0] <= keep <= KEEP_BOUNDS[1] else DEFAULTS["keep"]}


def _clean(ai, text, limit):
    redact = ai.get("redact") if isinstance(ai.get("redact"), dict) else {}
    out = redactor.redact(str(text or ""))
    for term in redact.get("extra_terms") or ():
        out = re.sub(re.escape(term), "[hidden]", out, flags=re.IGNORECASE)
    return glob_patterns.hide(out, redact.get("extra_patterns"))[:limit]


def record(ai, kind, used, system, user, reply="", reason="", now=None):
    """Writes one line when the record is on. Never raises: a record that cannot be written never stops an explanation."""
    cfg = settings(ai)
    if not cfg["enabled"]:
        return False
    try:
        line = {"at": int(time.time() if now is None else now), "kind": str(kind)[:30], "provider": str(used.get("provider", ""))[:40], "model": str(used.get("model") or "")[:80],
                "ok": bool(reply), "reason": str(reason)[:40], "system_chars": len(system or ""), "prompt": _clean(ai, user, PROMPT_CHARS), "reply": _clean(ai, reply, REPLY_CHARS)}
        path = Path(LOG_FILE)
        with locks.os_lock(path, 5.0):
            with private_io.open_append(path) as handle:
                handle.write(json.dumps(line, ensure_ascii=False) + "\n")
            _trim(path, cfg["keep"])
        return True
    except (OSError, TimeoutError, ValueError):
        return False


def _trim(path, keep):
    """Keeps the last `keep` lines once the file has a quarter more than that (all of them under a legal hold)."""
    from github_actions_monitor.storage import retention
    if retention.held():
        return
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    if len(lines) <= keep + max(5, keep // 4):
        return
    tmp = Path(str(path) + ".tmp")
    private_io.write_tmp(tmp, "\n".join(lines[-keep:]) + "\n")
    os.replace(tmp, path)


def read(ai, limit=50):
    """{enabled, keep, entries}: the newest lines first, with the closed list of fields; a damaged line is skipped."""
    cfg = settings(ai)
    entries = []
    try:
        for raw in Path(LOG_FILE).read_text(encoding="utf-8").splitlines()[-max(1, min(int(limit), 500)):]:
            try:
                data = json.loads(raw)
            except ValueError:
                continue
            if isinstance(data, dict):
                entries.append({key: data.get(key) for key in FIELDS})
    except (OSError, ValueError):
        pass
    entries.reverse()
    return {"enabled": cfg["enabled"], "keep": cfg["keep"], "entries": entries}


def clear():
    """Empties the record (the file goes; the next line creates it again). Returns how many lines it had."""
    from github_actions_monitor.storage import retention
    path = Path(LOG_FILE)
    if retention.held():
        return 0
    try:
        with locks.os_lock(path, 5.0):
            count = len(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else 0
            if path.is_file():
                path.unlink()
        return count
    except (OSError, TimeoutError):
        return 0
