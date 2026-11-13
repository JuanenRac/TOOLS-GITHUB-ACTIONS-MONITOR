<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](STORAGE_spa.md) | [🇫🇷 Français](STORAGE_fra.md) | [🇮🇹 Italiano](STORAGE_ita.md) | [🇩🇪 Deutsch](STORAGE_deu.md) | [🇨🇳 简体中文](STORAGE_zho.md) | [🇯🇵 日本語](STORAGE_jpn.md) | [🇵🇹 Português](STORAGE_por.md)

# Storage and retention

Where the complete edition keeps what it learns, how to change that, and what it removes by itself. The lite edition always keeps plain files, has no database and no retention job, and shows none of this.

## What is kept

For each account: the configuration (`actions_monitor.json`), the state of the sentinels, the event feed, what the feed has already announced, the analytics samples, the silences and the update notice. For the whole installation: users, the accounts they may see and their sessions (the team mode uses them). The caches of conditional reads and the logs are always plain files.

## The two backends

|  | `file` (default) | `sqlite` |
|---|---|---|
| Where | `accounts/<id>/` (next to the launchers when there is no `accounts/`) | `accounts/<id>/storage.sqlite3`, one database per account |
| Writes | a temporary file, flushed, then renamed | one short transaction, WAL journal |
| Choose it for | one person; files you can read and edit | a service that runs for months; many events |

Choose in the configuration of the account (or of the monitor): `"storage": {"backend": "sqlite"}`. The configuration itself always stays a JSON file, because it is what names the backend. With SQLite the event feed is in the database, not in `events_monitor.jsonl`. A database that cannot be opened stops the start: the monitor never writes its state somewhere else behind your back.

## Decision: one storage per account (model A)

*Context.* The complete edition runs one process per account. *Decision.* Each process has its own storage: its own files, or its own database `storage.sqlite3` inside `accounts/<id>/`. Two processes never write the same file, so there is nothing to lock between them and a problem in one account cannot damage another. *Cost.* A question across accounts means reading several databases.

*Kept ready: model B, one shared database.* Put the same path in the `storage` block of every account (`"path": "/data/monitor.sqlite3"`). It works because every table carries the account, WAL lets the page read while the sentinels write, transactions are short and a busy database is waited for up to 5 seconds. It is tested (two processes ticking at once; a page that answers over HTTP while they write) but it is not the default: it is more fragile than A and only worth it if you need SQL across accounts.

## What is guaranteed

- A write is atomic: a reader sees the old value or the new one. A process killed in the middle (`kill -9`) leaves the old value; on SQLite the next start recovers by itself.
- The schema is versioned (`schema_version`). Every migration runs in one transaction together with the bump of the version, so an interrupted one leaves the database as it was and runs again at the next start. A database written by a newer version is refused, never downgraded.
- A damaged or missing item reads as empty: the monitor starts with whatever is on the disk.

## Moving data and backups

```
python tools/migrate_storage.py --from file --to sqlite              # a dry run: shows what it would copy
python tools/migrate_storage.py --from file --to sqlite --apply      # copies, then compares every item and every event
python tools/backup_storage.py backup backup.zip --backend sqlite    # one .zip with a manifest and a SHA-256
python tools/backup_storage.py verify backup.zip
python tools/backup_storage.py restore backup.zip --backend file     # into an empty storage (--force over existing accounts)
```

The migration never changes or deletes your files, resumes after an interruption (an account is copied whole or not at all) and ends with a failure if the two sides differ; only then set the backend and restart. A backup made from files restores into SQLite and the other way round. `--db FILE` selects the shared database of model B; `--flat` is the installation without `accounts/`. `--doctor` checks the database (present, integrity, schema) without changing it.

## Retention

A monitor left running for months would grow without a ceiling, so a short pass at the end of a refresh (every `retention.interval_hours`, 24 by default) removes what is old:

| Setting | Default | Meaning |
|---|---|---|
| `retention.enabled` | on | the switch |
| `retention.events_days` | 90 | events older than this are removed |
| `retention.analytics_days` | 180 | days of the analytics history older than this are removed |
| `retention.mode` | `delete` | `archive` writes the old events to a `.gz` in `events/archive/` first |
| `retention.events_max_kb` | 512 | ceiling in size of the feed file with the file backend (as always) |
| `retention.warn_events_mb` | 20 | `--doctor` warns above this size |

The purge only touches events and analytics days that are older than their limit; it never touches the configuration, the state of the sentinels, the silences or an event with no time. Each pass leaves a line in the audit document (when, how many events removed and kept, the archive file, how many analytics days, any error). `--doctor` warns about the size of the events and, for a monitor that runs as a service (network mode, no browser, a container or `MONITOR_SERVICE=1`), when its configuration has no `retention` block. Make a backup before you shorten the limits.
