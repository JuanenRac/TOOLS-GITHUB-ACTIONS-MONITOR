# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Archives of purged events: a .jsonl.gz written completely (temporary name, flushed, renamed) before the purge removes anything from the hot path."""
import gzip
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


def unique_tmp(path):
    """A temporary name next to `path` that no other process or thread uses."""
    path = Path(path)
    return path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")


def write_archive(archive_dir, prefix, lines):
    """Writes `lines` (text lines without the newline) to a new <archive_dir>/<prefix>-<UTC stamp>.jsonl.gz and returns its path. The file is complete (written to a temporary name,
    flushed, then renamed) before the function returns; a name already taken gets a number."""
    folder = Path(archive_dir)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target, n = folder / f"{prefix}-{stamp}.jsonl.gz", 1
    while target.exists():
        n += 1
        target = folder / f"{prefix}-{stamp}-{n}.jsonl.gz"
    tmp = unique_tmp(target)
    try:
        with open(tmp, "wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as handle:
                handle.write("".join(line + "\n" for line in lines).encode("utf-8"))
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(tmp, target)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    return target
