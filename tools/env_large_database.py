#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Checks that need a machine more than a test needs: a large database. Run by the workflow cross-cutting.yml; data is invented and everything lives in a temporary folder.

  py -3 tools/env_large_database.py sqlite [--events N]"""
import argparse
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "monitor" / "src"))


def sqlite(count):
    from github_actions_monitor.storage.sqlite_storage import SqliteStorage
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        store = SqliteStorage(Path(folder) / "storage.sqlite3")
        text = "x" * 600
        started = time.time()
        for start in range(0, count, 5000):
            store.append_events("default", [{"at": f"2020-01-01T00:00:{n % 60:02d}Z" if n % 2 else "2099-01-01T00:00:00Z", "kind": "red_new", "repo": f"r{n % 250}", "text": text, "n": n}
                                            for n in range(start, min(count, start + 5000))])
        written = time.time() - started
        size = (Path(folder) / "storage.sqlite3").stat().st_size
        before = store.event_stats("default")["count"]
        out = store.purge_events("default", "2021-01-01T00:00:00Z")
        after = store.event_stats("default")["count"]
        print(f"events {before}, {size / 1e6:.0f} MB, written in {written:.0f} s, purged {out['removed']}, kept {after}")
        return 0 if before == count and out["removed"] == count // 2 and after == count - count // 2 else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("what", choices=("sqlite",))
    ap.add_argument("--events", type=int, default=1_500_000)
    args = ap.parse_args()
    return sqlite(args.events)


if __name__ == "__main__":
    sys.exit(main())
