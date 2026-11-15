<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Command line: `python bin/monitor_cli.py`

Generated from the code. It reads what the running monitor says (and never writes to GitHub). `--json` prints one JSON document; the exit codes are stable.

Commands: `status`, `accounts`, `alerts`, `live`, `doctor`, `health`, `check`, `score`, `ai-hook`, `credential`, `lessons`, `install-skill`, `gh-token`.

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
| `--fail-on` | alerts: exit with 5 when an alert of this level or worse is open |
| `--dest` | install-skill: the folder the skill is copied into (a subfolder github-actions-monitor-<name> is made) |
| `--read-only` | gh-token: required, prints a one-hour read-only token of the GitHub App (only with github_app.share_reads on) |
| `--repo` | lessons: only this repository |
| `--compare` | score: also compare with the history of the window |
| `--lang` | language of the texts (en, es, de, fr, it, ja, zh, pt) |
| `--version` | print the version |

Other entry points: `bin/mcp_server.py` (MCP over standard input and output; `--allow-ack`, `--allow-lessons`), `bin/ai_hook.py` (gate script of an AI tool), `bin/read_report.py`, `bin/actions_monitor.py --doctor`.
