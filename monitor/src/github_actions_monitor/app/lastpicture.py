# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The last picture of the monitor, kept on disk, so that a restart shows data at once instead of an empty page while the first cycle reads GitHub.

  * After every complete cycle the picture that the page shows is written to `last_picture.json` in the state folder (private file, replaced whole, never half written).
  * When the monitor starts it reads that file back, once, and publishes it marked `resumed` with its age ("data from 7 minutes ago"); the first cycle starts at the same moment and replaces it.
  * `startup.resume_max_age_hours` = the oldest picture that is shown (default 12; 0 = the picture is neither kept nor shown, and an old file is deleted). A picture older than that, a file
    that does not read as a picture, or one written by another version of the format is ignored: the page waits for the first cycle as before.
  * Nothing about the picture is sent anywhere; it holds what the page already shows (repository names, run states), in a file only the person that runs the monitor can read.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

FILE_NAME = "last_picture.json"
FORMAT = 1
DEFAULT_MAX_AGE_HOURS = 12
MAX_BYTES = 40 * 1024 * 1024      # a picture bigger than this is not kept: reading it back would cost more than waiting for the cycle


def max_age_hours(config):
    """The setting `startup.resume_max_age_hours` as a whole number of hours between 0 and 168."""
    section = (config or {}).get("startup")
    value = section.get("resume_max_age_hours", DEFAULT_MAX_AGE_HOURS) if isinstance(section, dict) else DEFAULT_MAX_AGE_HOURS
    if isinstance(value, bool) or not isinstance(value, int):
        return DEFAULT_MAX_AGE_HOURS
    return max(0, min(168, value))


def _parse(stamp):
    try:
        return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def save(folder, data, config):
    """Writes the picture. Returns True when it was written; a picture of an incomplete cycle (`loading`) or with the feature off is not written (and the old file is deleted when off)."""
    path = Path(folder) / FILE_NAME
    if max_age_hours(config) == 0:
        try:
            path.unlink()
        except OSError:
            pass
        return False
    if not isinstance(data, dict) or data.get("loading") or not data.get("updated") or data.get("resumed"):
        return False
    from github_actions_monitor.storage import file_storage
    text = json.dumps({"format": FORMAT, "saved": data["updated"], "data": data}, ensure_ascii=False, separators=(",", ":"))
    if len(text) > MAX_BYTES:
        return False
    file_storage.atomic_write(path, text)
    return True


def load(folder, config, now=None):
    """The picture of the file, marked `resumed` = {"updated", "age_seconds"}; None when the feature is off, the file is missing, unreadable, of another format or too old."""
    limit = max_age_hours(config)
    if limit == 0:
        return None
    path = Path(folder) / FILE_NAME
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(document, dict) or document.get("format") != FORMAT or not isinstance(document.get("data"), dict):
        return None
    data = document["data"]
    when = _parse(data.get("updated"))
    now = time.time() if now is None else now
    if when is None or when > now + 300 or now - when > limit * 3600:
        return None
    data["resumed"] = {"updated": data["updated"], "age_seconds": max(0, int(now - when))}
    data["loading"] = 0
    return data
