# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A local copy of the artifacts of finished runs (`mirror.enabled`, OFF by default), for the days GitHub deletes them.

  * Folder: `mirror.folder`, on this computer (never a network path, never the D: drive); empty = nothing is done. Layout: FOLDER/REPOSITORY/RUN/NAME.zip and an index `.mirror_index.json`.
  * Limits: `mirror.max_per_cycle` artifacts per cycle, `mirror.max_mb` for the whole folder (an artifact that would not fit is skipped, and the oldest copies go first), `mirror.keep_days`.
  * An artifact is downloaded once; expired artifacts are skipped; names are cleaned to letters, digits and `._-`; the files are written inside the folder only.
  Read only on GitHub's side: the monitor lists the artifacts of a run and downloads them, nothing else.
"""
import json
import os
import re
import time
from pathlib import Path

NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
INDEX = ".mirror_index.json"
FOREIGN = re.compile(r"^(?:[Dd]:|/mnt/[dD](?:/|$)|/[dD](?:/|$))")


def settings(config):
    cfg = config.get("mirror") if isinstance(config, dict) and isinstance(config.get("mirror"), dict) else {}

    def number(key, low, high, default):
        value = cfg.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else default
    folder = cfg.get("folder") if isinstance(cfg.get("folder"), str) else ""
    return {"enabled": cfg.get("enabled") is True and safe_folder(folder), "folder": folder.strip(), "max_mb": number("max_mb", 10, 100000, 500), "keep_days": number("keep_days", 1, 365, 14),
            "max_per_cycle": number("max_per_cycle", 1, 20, 3)}


def safe_folder(text):
    text = str(text or "").strip()
    return bool(text) and len(text) <= 260 and not any(ord(c) < 32 for c in text) and not text.startswith(("\\\\", "//")) and not FOREIGN.match(text)


def clean_name(text):
    cleaned = re.sub(r"\.{2,}", "_", NAME_RE.sub("_", str(text)))
    return (cleaned[:80] or "artifact").strip(".") or "artifact"


def _load(folder):
    try:
        value = json.loads((Path(folder) / INDEX).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(folder, index):
    Path(folder).mkdir(parents=True, exist_ok=True)
    tmp = Path(folder) / (INDEX + ".tmp")
    tmp.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, Path(folder) / INDEX)


def folder_size(folder):
    total = 0
    for path in Path(folder).rglob("*.zip"):
        try:
            total += path.stat().st_size
        except OSError:
            pass
    return total


def prune(folder, index, cfg, now=None):
    """Deletes the copies older than keep_days, then the oldest ones until the folder fits max_mb. Returns the number removed."""
    now = time.time() if now is None else now
    removed = 0
    entries = sorted(index.items(), key=lambda kv: kv[1].get("at", 0))
    limit = cfg["max_mb"] * 1024 * 1024
    total = sum(v.get("bytes", 0) for _k, v in entries)
    for key, value in entries:
        if now - value.get("at", 0) > cfg["keep_days"] * 86400 or total > limit:
            try:
                (Path(folder) / value["path"]).unlink()
            except FileNotFoundError:
                pass
            except OSError:
                continue
            total -= value.get("bytes", 0)
            index.pop(key, None)
            removed += 1
    return removed


def cycle(config, runs, owner, lister, downloader, now=None):
    """One cycle: `lister(endpoint) -> json`, `downloader(endpoint, destination)` writes a file. Returns {"copied", "skipped", "removed"}."""
    cfg = settings(config)
    result = {"copied": 0, "skipped": 0, "removed": 0}
    if not cfg["enabled"]:
        return result
    now = time.time() if now is None else now
    folder = Path(cfg["folder"])
    index = _load(folder)
    budget = cfg["max_per_cycle"]
    size = sum(v.get("bytes", 0) for v in index.values())
    for run in runs:
        if budget <= 0:
            break
        if run.get("status") != "completed" or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", str(run.get("repo", ""))):
            continue
        key_prefix = f"{run['repo']}/{run['id']}/"
        if any(k.startswith(key_prefix) for k in index) or str(run.get("id")) in index.get("_seen", {}):
            continue
        try:
            body = lister(f"repos/{owner}/{run['repo']}/actions/runs/{run['id']}/artifacts?per_page=30")
        except Exception:   # noqa: BLE001 - the list can not be read: the run is tried again in a later cycle
            continue
        index.setdefault("_seen", {})[str(run["id"])] = int(now)
        for art in (body or {}).get("artifacts") or []:
            if budget <= 0 or art.get("expired") or not isinstance(art.get("id"), int):
                result["skipped"] += 1
                continue
            weight = art.get("size_in_bytes") if isinstance(art.get("size_in_bytes"), int) else 0
            if size + weight > cfg["max_mb"] * 1024 * 1024:
                result["skipped"] += 1
                continue
            relative = f"{run['repo']}/{run['id']}/{clean_name(art.get('name'))}.zip"
            destination = (folder / relative).resolve()
            if folder.resolve() not in destination.parents:
                result["skipped"] += 1
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                downloader(f"repos/{owner}/{run['repo']}/actions/artifacts/{art['id']}/zip", destination)
            except Exception:   # noqa: BLE001
                result["skipped"] += 1
                continue
            real = destination.stat().st_size if destination.is_file() else 0
            index[f"{run['repo']}/{run['id']}/{art['id']}"] = {"path": relative, "bytes": real, "at": int(now)}
            size += real
            budget -= 1
            result["copied"] += 1
    seen = index.get("_seen", {})
    index["_seen"] = {k: v for k, v in seen.items() if now - v < 30 * 86400}
    meta = index.pop("_seen")
    result["removed"] = prune(folder, index, cfg, now)
    index["_seen"] = meta
    _save(folder, index)
    return result


def status(config):
    cfg = settings(config)
    out = {"enabled": cfg["enabled"], "folder_set": bool(cfg["folder"]), "max_mb": cfg["max_mb"], "keep_days": cfg["keep_days"], "count": 0, "mb": 0.0}
    if cfg["enabled"]:
        index = _load(cfg["folder"])
        out["count"] = sum(1 for k in index if k != "_seen")
        out["mb"] = round(sum(v.get("bytes", 0) for k, v in index.items() if k != "_seen") / 1048576, 1)
    return out
