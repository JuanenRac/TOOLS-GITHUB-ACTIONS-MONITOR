<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](OPS_spa.md) | [🇫🇷 Français](OPS_fra.md) | [🇮🇹 Italiano](OPS_ita.md) | [🇩🇪 Deutsch](OPS_deu.md) | [🇨🇳 简体中文](OPS_zho.md) | [🇯🇵 日本語](OPS_jpn.md) | [🇵🇹 Português](OPS_por.md)

# Operating the installation

For a monitor that is left running for months (Complete edition). It covers the complete backup, the restore, the scheduled copy, the doctor with exit codes a cron job can rely on, and how to set it up as an appliance (systemd or Docker). The Lite edition has none of this.

## The backup package

`python bin/monitor_cli.py backup create [FILE]` writes ONE `.zip` (format 2) and verifies it before putting it in place. With no `FILE` it goes to the folder `backups` of the data folder (`ops.backup.dir`) with the name `ghamon-backup-<UTC time>.zip`. The monitor does not have to be stopped: the data are read with the atomic reads of the storage (files or SQLite), never by copying a database that is being written.

| Member | What it holds |
|---|---|
| `dump.jsonl` | every account (its settings, the state of the sentinels, the small documents, the events, the analytics, the score snapshots) and the global records (users and the accounts they may see; never the sessions) |
| `files.json` | the settings of the page and the lists of the installation (`targets.json`, `ecosystems.json`, `profiles.json`, the silences), cleaned; also the stores of the optional modules when they exist (`proposals.json`, `devices.json`) |
| `manifest.json` | the format, the version of the product, the schema, the counts and the size and SHA-256 of every member |

**What never travels:** tokens and keys of GitHub or of an App, passwords, the value of any `*_env` variable (only its name), the secret of the webhook, the keys of the AI providers, the sessions and the content of the secret store. The settings go through a white list (the same keys the Settings page can show) and then through a scrub that drops any key that looks like a secret and any text that looks like a token or a private key. `ops.backup.include_config` off leaves the settings and the lists out altogether. A restore does not bring a credential back: put the login of GitHub in place again (its checklist says so).

The backup is only readable by its owner (mode 600) and the package is not encrypted unless you ask: see below.

### A package of one account

`backup create --account ID [FILE]` writes the package of ONE account: its dump (with its settings, cleaned in the same way) and nothing else. It carries no user and no session, and not the settings or lists of the installation; the manifest says `scope: account`. `backup verify` checks that it holds that account alone, and `backup restore FILE` restores that account (no `--account` is needed) without touching the other accounts, the users or the files of the destination; it is refused only when that account already exists there and there is no `--force`. It is the way to move or recover a single account.

### Sealing the copy (optional)

`ops.backup.encrypt` (or `--encrypt` for one copy) seals the package with AES-256-GCM using a key taken from the environment variable named by `ops.backup.key_env` (`--key-env NAME`). The key is never a setting, is never written down and is never on a command line. It needs the optional library `cryptography` (`pip install cryptography`; the core of the monitor stays standard library only). Without the library, or without a key of 12 characters or more, the copy is **refused** with a clear message and nothing is written: a copy is never made in the clear when you asked for a sealed one, and never sealed with something weaker. A sealed file ends in `.enc`; `verify` and `restore` open it with the same variable. Keep the key apart from the file: without it the copy cannot be opened.

## Verify, list and status

- `backup verify FILE` re-reads the package and checks every size and SHA-256 and the counts. A changed byte, a missing member or one the manifest does not list is reported. `--deep` also restores it into a temporary folder and checks the result.
- `backup list` shows the copies in the folder; `backup status` shows the last good copy, how old it is, the schedule and the last failure.
- A package of the first format (made before 2.1.0) still verifies and restores.

## Restore

`python bin/monitor_cli.py backup restore FILE`: stop the monitor first (a restore is refused while one answers on its port). It verifies the package, then writes the accounts and the files.

- A storage that already holds accounts is refused unless you add `--force` (the accounts of the package are then written over them; the settings are **merged**: a key the package does not carry is never removed).
- `--account ID` restores that account alone and leaves the others and the global files as they are (it is refused only when that account exists and there is no `--force`).
- `--to-dir DIR` restores into an empty folder (files backend) without touching the installation: the way to look at a copy, or to move to another machine.
- It writes `ops/restore_report.json` in the data folder and prints what is left to do: put the login of GitHub in place, set again the settings the package left out, restart the monitor so the supervisor starts every account, run the doctor.

## The scheduled copy

Two ways, use one:

1. Inside the monitor: `ops.backup.enabled` (off by default) makes a copy every `ops.backup.interval_hours` in a thread of its own, keeps the newest `ops.backup.keep` (only files with the name of a copy are ever removed) and records the result in `ops/backup_status.json`. A failure (a full disk, a missing key) is written down and shown in the About panel and the doctor; it never stops the monitor.
2. With systemd: `deploy/github-actions-monitor-backup.service` and `deploy/github-actions-monitor-backup.timer` (see below).

The About panel has a card **Operation** with the mode (service or local), the last good copy, the schedule, the retention in force and the button **Back up now** (an administrator, from this computer). `GET /api/ops/status` gives the same data; `POST /api/ops/backup` makes a copy.

## Purge on demand

The retention purge runs by itself every `retention.interval_hours`. To run it now there is a button (and `POST /api/ops/purge`) that **does not exist** until `ops.purge.enabled` is on (it is off by default). A request is a dry run (the policy in force and how many events would go) unless it says `dry_run` false, and a real purge is refused without a good backup newer than `ops.purge.require_backup_hours` (24 by default; 0 does not ask). It leaves its line in the audit of the retention and in the log of actions.

## The doctor and its exit codes

`python bin/monitor_cli.py doctor [--strict] [--json]` (or `python bin/actions_monitor.py --doctor`) checks the installation, changes nothing and prints no secret. The Complete edition adds these checks after the usual ones:

| Check | What it looks at |
|---|---|
| `volumes` | a file is really written, read and removed in the data, logs and backup folders (a Docker volume mounted as root or read only fails here) |
| `supervisor` | a running monitor: the deep health of the supervisor and of every refresh cycle (nothing is started) |
| `limits` | the webhook secret is set and at least `ops.doctor.webhook_min_length` characters (only the length is compared) and the retention policy |
| `sqlite_hot` | each SQLite database opened read only: `quick_check` (the default) or `integrity_check` (`ops.doctor.sqlite_check` deep), stopped at `ops.doctor.sqlite_timeout_s`; a corrupt file after a power cut fails |
| `backup_age` | the last good copy against `ops.doctor.backup_max_age_days` |
| `disk` | free space of the data volume against `ops.doctor.min_free_mb` |
| `metrics` | `/metrics` answers when the Prometheus output is on and a monitor runs |

**Exit codes (stable, for cron):** `0` all is well (warnings too, without `--strict`); `1` at least one check failed; `3` only warnings and `--strict` (or `ops.doctor.strict_exit`); `4` the doctor itself could not run. These are the codes of the doctor; the other commands of `monitor_cli.py` keep theirs. Example: `0 * * * * python3 bin/monitor_cli.py doctor --strict --json > /var/lib/github-actions-monitor/doctor.json || true` and alert on any code other than 0.

## As an appliance

**systemd** (no container): follow the comments of `deploy/github-actions-monitor.service`, then install the backup unit and its timer:

```
install -m 644 deploy/github-actions-monitor-backup.service deploy/github-actions-monitor-backup.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor-backup.timer
systemctl list-timers github-actions-monitor-backup.timer
```

For a sealed copy put the variable named by `ops.backup.key_env` in `/etc/github-actions-monitor/env` (mode 600). The timer runs `backup create` every day; its exit code is 1 when the copy could not be made.

**Docker:** `deploy/compose.yaml` keeps the copies in a volume of their own (`monitor-backups` at `/data/backups`) so that losing the data volume does not lose them. Copy a file out with `docker compose exec monitor python bin/monitor_cli.py backup list` and `docker cp`, and restore into a stopped container or with `--to-dir`. TLS is renewed by the Caddy of `deploy/Caddyfile`.

**Upgrading without losing the accounts:** `backup create` → `backup verify FILE` → stop the monitor → replace the product folder (the `config/`, `data/`, `logs/` and `ai/` folders are yours and are kept) → `doctor` → start. If something goes wrong, `backup restore FILE`. **Removing it cleanly:** stop and disable the units, remove the timer, then the product folder and, only if you want to lose the data, the `config/`, `data/` folders or the Docker volumes.

## Settings

All of them are in the Settings tab (Folders and files) and in [SETTINGS.md](SETTINGS.md): `ops.backup.*` (enabled, dir, interval_hours, keep, include_config, compress_level, encrypt, key_env), `ops.purge.*` (enabled, require_backup_hours) and `ops.doctor.*` (strict_exit, backup_max_age_days, min_free_mb, sqlite_check, sqlite_timeout_s, webhook_min_length). Every switch starts off or conservative, and the security ones (the scheduled copy, including the settings, sealing, the purge) are marked as such.

See also [STORAGE.md](STORAGE.md) (the backends and the retention), [DEPLOYMENT.md](DEPLOYMENT.md) (service, container, TLS) and [CLI.md](CLI.md).
