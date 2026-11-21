<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Command line: `python bin/monitor_cli.py`

Generated from the code. It reads what the running monitor says (and never writes to GitHub). `--json` prints one JSON document; the exit codes are stable.

Commands: `status`, `accounts`, `alerts`, `live`, `doctor`, `health`, `check`, `score`, `team`, `ai-hook`, `credential`, `lessons`, `briefs`, `api`, `install-skill`, `gh-token`, `ai`, `backup`, `update`, `compare`, `screens`, `toolbox`, `watch`, `completions`, `kiosk`, `metrics`, `proposals`.

| flag | what |
| --- | --- |
| `-h --help` | show this help message and exit |
| `--json` | print the answer as one JSON document |
| `--assistant` | ai-hook: the default assistant tool (default) |
| `--cursor` | ai-hook: Cursor (best effort) |
| `--generic` | ai-hook: any other tool (prints the commands, writes nothing) |
| `--scope` | ai-hook: project (the settings of the folder, default) or user (all your projects) |
| `--project-dir` | ai-hook: the project folder (default: the current one) |
| `--dry-run` | ai-hook: show what would change without writing |
| `--account` | the account to ask (several accounts only) |
| `--url` | address of the monitor (default: MONITOR_URL, else this computer) |
| `--lite` | talk to the lite edition (port 8766) |
| `--token-file` | file whose first line is the access token of the network mode (keep it readable by you only) |
| `--token` | access token of the network mode (last resort: it shows in the list of processes; prefer MONITOR_ACCESS_TOKEN) |
| `--deep` | health: also ask the deep check (the supervisor and the refresh cycle of every account) |
| `--user` | team mode: sign in as this user (with --password-file or MONITOR_PASSWORD_FILE) |
| `--password-file` | team mode: a file with the password of --user on its first line |
| `--ca-file` | HTTPS: trust this certificate authority (a PEM file), for a monitor with a certificate of your own |
| `--new-token-file` | credential replace: a file with the new token on its first line (- for the standard input) |
| `--timeout` | seconds to wait for each answer (1 to 60) |
| `--sentinel` | alerts: only this sentinel |
| `--level` | alerts: only this level |
| `--muted` | alerts: show, hide (default) or list only the silenced ones |
| `--since` | alerts: the alerts that were open at some moment of this time, closed ones too (90m, 24h, 7d, 2w; at most 90 days) |
| `--fail-on` | alerts: exit with 5 when an alert of this level or worse is open |
| `--strict` | doctor: a warning also makes the exit code 3 (without it, warnings still exit 0) |
| `--force` | backup restore: write over accounts and files that already exist (without it a storage that holds accounts is refused) |
| `--encrypt` | backup create: seal the copy with the key of the variable named by --key-env or ops.backup.key_env (needs the optional library cryptography; refused without it) |
| `--key-env` | backup: the NAME of the environment variable that holds the key of a sealed copy (the key itself is never given on the command line) |
| `--to-dir` | backup restore: restore into this empty folder (files backend) instead of the installation |
| `--dest` | install-skill: the folder the skill is copied into (a subfolder github-actions-monitor-<name> is made) |
| `--read-only` | gh-token: required, prints a one-hour read-only token of the GitHub App (only with github_app.share_reads on) |
| `--repo` | lessons and watch branch: only this repository (OWNER/NAME for watch branch) |
| `--severity` | team: only the repositories in this state or a worse one |
| `--compare` | score: also compare with the history of the window |
| `--window` | compare: length of the period, in days (7, 30d...) |
| `--days` | compare: which days count (all, workdays or weekend) |
| `--baseline` | compare: what to compare against (previous or year_ago) |
| `--lang` | language of the texts (en, es, de, fr, it, ja, zh, pt) |
| `--provider` | ai models/test/doctor: provider or preset to use instead of the configured one |
| `--model` | ai models/test/doctor: model to use instead of the configured one |
| `--refresh` | ai models: read the list from the provider first (one request) |
| `--format` | The way the answer is written: text (the default), table, plain (separated by tabs), json or ndjson (one object per line); csv (compare only) |
| `--interval` | watch: seconds between two reads (never below cli.watch.min_interval_seconds) |
| `--once` | watch: read once and finish |
| `--exit-on-change` | watch: finish with exit code 6 when what is watched changes |
| `--no-clear` | watch: do not clear the screen between two reads |
| `--single-pass` | watch: read once and finish (the same as --once) |
| `--branch` | watch branch: the branch to follow (default: the one of the current folder) |
| `--wait` | watch branch: seconds to wait for the runs to finish (10 to 86400; default cli.watch.branch_timeout_seconds) |
| `--status-codes` | status: exit codes, classic (0 to 5, the usual ones) or operator (0 healthy, 1 nothing serving, 2 up but needs attention) |
| `--if-problem` | metrics: write nothing and exit 0 when there is no red workflow and no alert at --fail-on (error by default) or worse; otherwise write the figures and exit 5 (for cron, which mails any output) |
| `--color` | Colour of the answer: auto (only on a terminal, never with NO_COLOR), always or never (no escape sequence at all) |
| `--egress` | doctor: list every host this configuration can call, why, and what fails if it is blocked (nothing is called) |
| `--version` | print the version |

Other entry points: `bin/mcp_server.py` (MCP over standard input and output; `--allow-ack`, `--allow-lessons`), `bin/ai_hook.py` (gate script of an AI tool), `bin/read_report.py`, `bin/actions_monitor.py --doctor`.
