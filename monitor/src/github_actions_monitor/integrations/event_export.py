# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Local analysis of the events of the monitor and their export (OPTIONAL, nothing runs unless you ask: `monitor_cli.py toolbox export-events`).

The events file (`events_monitor.jsonl`, one JSON object a line: new reds, solved, stuck, offline...) is read from disk and written as

  jsonl    a copy of the lines (always possible)           csv      one row a line, the same columns for every row (always possible)
  parquet  needs the package `pyarrow` (pip install pyarrow); without it the command says so and writes nothing
  duckdb   needs the package `duckdb` (pip install duckdb): a database file with the table `events` that you open with the DuckDB shell or any client

`summary()` answers the usual questions without any package: events by kind, by repository and by day. No SQL is accepted from anywhere (a query language that can read other files would be a way out
of the folder); you open the exported file with your own tool for that. Only the short columns the file already holds are written: no token, no text of a log. The destination must be a new file in a
folder you name, never an existing one (nothing is overwritten) and never a network path.
"""
import csv
import json
import re
from collections import Counter
from pathlib import Path

FORMATS = ("jsonl", "csv", "parquet", "duckdb")
COLUMNS = ("at", "kind", "owner", "repo", "workflow", "level", "text", "url", "sentinel", "code")
MAX_ROWS = 200000
NAME_RE = re.compile(r"^[A-Za-z0-9._ -]{1,80}\Z")


class ExportError(Exception):
    """A refusal with a short reason the command prints."""


def read_events(path, since="", limit=MAX_ROWS):
    """The events of the file as dictionaries (the newest `limit`), skipping a line that is not an object. `since` = ISO date or time: older events are left out."""
    rows = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if isinstance(item, dict) and (not since or str(item.get("at") or "") >= since):
                    rows.append(item)
    except OSError:
        return []
    return rows[-max(1, int(limit)):]


def flat(row):
    """One row with the columns of COLUMNS, as text (a column the event does not have is empty)."""
    return {c: ("" if row.get(c) is None else str(row.get(c))[:2000]) for c in COLUMNS}


def summary(rows):
    """{"events": n, "first", "last", "by_kind": {...}, "by_repo": {top 20}, "by_day": {...}} with no package."""
    days = Counter(str(r.get("at") or "")[:10] for r in rows if r.get("at"))
    stamps = sorted(str(r.get("at")) for r in rows if r.get("at"))
    return {"events": len(rows), "first": stamps[0] if stamps else None, "last": stamps[-1] if stamps else None, "by_kind": dict(Counter(str(r.get("kind") or "") for r in rows).most_common()),
            "by_repo": dict(Counter(str(r.get("repo") or "") for r in rows if r.get("repo")).most_common(20)), "by_day": dict(sorted(days.items())[-60:])}


def check_destination(path):
    """The destination as a Path, or an ExportError: a new file, with a known suffix, in a folder that exists on this computer (not a network path)."""
    text = str(path)
    if text.startswith(("\\\\", "//")) or "://" in text:
        raise ExportError("network_path")
    target = Path(text)
    if not target.parent.is_dir():
        raise ExportError("no_folder")
    if target.exists():
        raise ExportError("exists")
    return target


def write(rows, path, fmt):
    """Writes `rows` to `path` in `fmt`. Returns {"format", "rows", "file"}; raises ExportError("missing_package:NAME") when parquet or duckdb is asked for without its package."""
    if fmt not in FORMATS:
        raise ExportError("format")
    target = check_destination(path)
    table = [flat(r) for r in rows]
    if fmt == "jsonl":
        with open(target, "x", encoding="utf-8") as handle:
            for row in table:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    elif fmt == "csv":
        with open(target, "x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(table)
    elif fmt == "parquet":
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            raise ExportError("missing_package:pyarrow") from None
        pq.write_table(pa.table({c: [r[c] for r in table] for c in COLUMNS}), str(target))
    else:
        try:
            import duckdb
        except ImportError:
            raise ExportError("missing_package:duckdb") from None
        connection = duckdb.connect(str(target))
        try:
            connection.execute("CREATE TABLE events (" + ", ".join(f"{c} VARCHAR" for c in COLUMNS) + ")")
            if table:
                connection.executemany("INSERT INTO events VALUES (" + ", ".join("?" for _ in COLUMNS) + ")", [[r[c] for c in COLUMNS] for r in table])
        finally:
            connection.close()
    return {"format": fmt, "rows": len(table), "file": target.name}
