<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](CLI_spa.md) | [🇫🇷 Français](CLI_fra.md) | [🇮🇹 Italiano](CLI_ita.md) | [🇩🇪 Deutsch](CLI_deu.md) | [🇨🇳 简体中文](CLI_zho.md) | [🇯🇵 日本語](CLI_jpn.md) | [🇵🇹 Português](CLI_por.md)

# The command line as a client of the monitor

`python bin/monitor_cli.py COMMAND` asks the running monitor what it knows (a `GET` on `127.0.0.1`, or on the address of `--url` / `MONITOR_URL`) and prints it. It does not repeat the work of the page against GitHub, it never writes to GitHub and it changes no setting. The older tools (`bin/read_report.py`, `--doctor`, `bin/gha_dispatch_all.py`) keep working as they were.

## Commands

| Command | What it shows | Lite |
|---|---|---|
| `status` | version, edition, account, repositories, what runs and fails, the allowance | yes |
| `health` (or `check`) | a quick check before reading anything heavy: is the monitor reachable, does it accept this client, does the GitHub login of the account answer | yes |
| `doctor` | the checks of `--doctor` for this installation (the monitor need not be running) | yes |
| `backup` | the complete backup of the installation (the monitor need not be running): `backup create [FILE] [--account ID]`, `verify FILE [--deep]`, `restore FILE [--account ID] [--to-dir DIR] [--force]`, `status`, `list`; `--encrypt` with `--key-env NAME` seals it (optional library); see [OPS.md](OPS.md) | no |
| `accounts` | the accounts of the supervisor (several accounts only) | no |
| `alerts` | the alerts of every sentinel in one list: `--sentinel ci\|collab\|security\|supply\|delivery`, `--level info\|warning\|error`, `--muted show\|hide\|only`; `--since 90m|24h|7d|2w` lists the ones that were open at some moment of that time, the closed ones too (from the history the monitor keeps while it runs; an alert counts as closed after ten minutes of absence) | no |
| `proposals` | the actions the AI proposed (`ai.actions.enabled`): `proposals list`, `show ID`, `approve ID`, `reject ID`, `execute ID` (an id may be shortened). `approve` and `reject` only record the decision; `execute` runs it through the same door as the page and needs `ai.actions.execute`, and with `ai.actions.require_approval` an approval first. Approve, reject and execute are for this computer only | no |
| `score` | the score of the account: number, letter, trend, parts, coverage and the breakdown by repository; `--compare` sets it against the history of the window | no |
| `compare` | this period against the one before: the figures with their change and direction, who got worse or better; `--window 7\|30d`, `--days all\|workdays\|weekend`, `--baseline previous\|year_ago`, `--format table\|json\|ndjson\|csv`; exit 4 when a figure has too little data, 5 with `--fail-on` when one got worse; `--format csv` with any other command is a wrong use (exit 1) | no |
| `api` | the read API for clients: `api openapi` prints the OpenAPI document of every frozen route (redirect it to a file), `api me` says who the monitor takes this client for (mode, user, role, what the session may do, version of the contract); a monitor whose `api.v1_enabled` is closed says so; `api contract-check` runs the contract suite for clients against it (exit 4 when a check fails) | no |
| `team` | the health of the repositories ranked with the ones that need a person first; `--severity warn\|bad` keeps the worse ones and `--repo owner/name` gives the detail of one | no |
| `live` | the state of the webhook receiver and the last events | no |
| `ai` | `ai models [--refresh]` lists the models of the AI provider with the data of each one; `ai test --provider NAME --model NAME` tries one with a synthetic text (latency, tokens, estimated cost); `ai doctor` says why an AI does not answer, without printing a key | no |
| `lessons` | what the failures of this CI have taught: `lessons list`, `lessons brief --repo NAME` (read it before a push), `lessons failures`, `lessons close` | no |
| `briefs` | the briefs of the tabs that AI tools read: `briefs index`, `briefs show TAB`, `briefs all` | yes |
| `docs` | the guides of this version, read from the installation (no monitor needed): `docs list` names them with their title, `docs show NAME` prints one in the language of `--lang` | no |
| `screens` | the Screens menu of the page: `screens list` (every kind of screen and whether it can be opened) and `screens urls` (the full addresses, ready for a kiosk command) | no |
| `keyring` | the public keys that may sign: `keyring list`, `add` (`--key-id`, `--public-key`, `--key-scope`, `--expires`), `revoke --key-id`, `verify --document FILE`; no monitor needed, private keys are refused | no |
| `verify-release` | a folder of downloaded release files checked without network against SHA256SUMS and its signature: `verify-release --folder DIR`; exit 4 when they cannot be trusted | no |
| `toolbox` | the small tools of the operator that work on this computer, with no monitor running: `toolbox limits [N]` (the setup against its ceilings), `toolbox workspaces` (the workspaces and the one in use), `toolbox ledger [--force]` (the ledger of notifications already sent; `--force` forgets it), `toolbox summary` (the events by kind, repository and day) and `toolbox export-events FILE` (the events as jsonl, csv, parquet or duckdb by the end of the name; parquet and duckdb need their package, the file must be new) | no |
| `credential` | another GitHub login for one account while everything runs: `credential replace\|reload [--account ID] [--new-token-file FILE\|-]`; it never prints a token | no |
| `install-skill` | copies a skill of the monitor (`internal` or `external`) to the folder an AI tool reads its skills from: `install-skill external --dest FOLDER`; the monitor need not be running | no |
| `gh-token` | prints a one-hour installation token of the GitHub App so that the reads of a tool spend the allowance of the App (only with `github_app.share_reads` on); run it without `--json` | no |
| `watch` | the same read again and again (`watch status\|alerts`, `--interval`, `--once`, `--exit-on-change`); see [CLI_OPERATOR.md](CLI_OPERATOR.md) | no |
| `completions` | the completion script for `bash`, `zsh`, `fish` or `powershell`, written from the real parser (it only prints) | no |
| `kiosk` | the address of the monitor for a TV or a wall (`ops`, `team`, `release`, `quiet`); see [KIOSK.md](KIOSK.md) | no |
| `metrics` | the figures as `name=value` lines for cron and mail; with `--if-problem` it writes nothing when all is well; see [CLI_OPERATOR.md](CLI_OPERATOR.md) | no |

Options of every command: `--json` (the answer as one JSON document: `{"ok", "exit", "data"}`), `--account ID`, `--url URL`, `--lite` (port 8766), `--timeout SECONDS` (1 to 60), `--lang CODE`. In the network mode put the access token in the environment variable `MONITOR_ACCESS_TOKEN`, the one the monitor itself reads (`MONITOR_TOKEN` is accepted as an alias; `--token TOKEN` is the last resort, because a flag shows in the list of processes). The order is: `MONITOR_ACCESS_TOKEN`, then `MONITOR_TOKEN`, then `--token`. It travels in the header `X-Monitor-Access`, never in the address and never on screen. A `--url` with plain `http` to another computer prints a warning on stderr (the token and the answers would travel unencrypted): use `https` outside a network you control.

Every command also takes `--format text|table|plain|json|ndjson` (`--json` is `--format json`); see [CLI_OPERATOR.md](CLI_OPERATOR.md).

The command line is a client of the read API for clients: the routes the contract freezes (`docs/schemas/api_contract.json`) are asked under `/api/v1/` first, and when the monitor answers 404 there (the API is closed, `api.v1_enabled`) the old route is asked and the prefix is not tried again. The document is the same by both ways, so the output of no command changes. `cli.prefer_v1` (on by default) turns it off, and the variable `MONITOR_CLI_PREFER_V1` (`0` or `1`) wins over it. The routes the contract does not freeze are always asked the old way.

Times written for people (the `Last read` line, the silences, the log, the reports, the notifications) use the zone of this computer and name it, with the UTC time next to it (`11:43:07 CET (10:43:07 UTC)`). Choose another zone with `display.timezone` (`local`, `utc` or a name such as `Europe/Madrid`; the environment variable `MONITOR_TIMEZONE` wins over the file). `--json` keeps UTC and adds `updated_local`.

## Exit codes (stable)

| Code | Meaning |
|---|---|
| 0 | all right |
| 1 | wrong use of the command (also `--lite` with a command that needs the complete edition) |
| 2 | the monitor cannot be reached |
| 3 | the monitor refuses this client, or the GitHub login of the account failed or expired (a credential problem, not an exhausted allowance) |
| 4 | the monitor answers but is degraded: offline, allowance exhausted, no data yet, an endpoint it does not have, or an answer that is not JSON |
| 5 | `alerts --fail-on LEVEL` found an open alert of that level or worse (a silenced alert does not count) |
| 6 | `watch --exit-on-change` saw a change (only when that flag is given); see [CLI_OPERATOR.md](CLI_OPERATOR.md) |

Every error carries a `help`: one sentence with the next step, often naming the guide to read (`docs show FIRST_STEPS`). In the text format it is the last line, which starts with `help:`; with `--json` it is the field `help` next to `error`: `{"ok": false, "exit": 2, "error": "...", "help": "..."}`.

## Examples

```
python bin/monitor_cli.py health && python bin/monitor_cli.py alerts --fail-on error
python bin/monitor_cli.py alerts --sentinel collab --level warning --json
python bin/monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python bin/monitor_cli.py health --json
```

`health` tells three things apart: the monitor does not answer (2), the login of GitHub fails (3), and the allowance ran out or GitHub cannot be reached (4); a monitor that has not finished its first read says so (4) instead of showing empty figures.

## The lite edition

`python bin/monitor_cli.py status --lite`, `doctor --lite` and `health --lite` talk to port 8766. The commands that need accounts, sentinels or the webhook receiver are refused with exit code 1. The lite edition has no accounts and no alerts API.

## `ai-hook`: tell an AI tool what the monitor sees

`python bin/monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--project-dir DIR] [--dry-run] [--json]` needs no running monitor. It adds, shows or removes the gate script `bin/ai_hook.py` in the hook settings of an AI tool (see the guide on alerts for AIs): the settings file is merged, a copy is kept, and the answer of `--json` is plain ASCII. `status` is the default action.

## The access token in the command line

In the network mode the token is read from `MONITOR_ACCESS_TOKEN`, then `MONITOR_TOKEN`, then the first line of `--token-file FILE` (keep that file readable by you only: on a system with file modes the command warns when others can read it), and last from `--token`, which shows in the list of processes and therefore prints a warning on stderr.

## The storage tools

`python tools/migrate_storage.py` moves the state between files and SQLite, and `python tools/backup_storage.py` makes, checks and restores backups of either (both are described in [STORAGE.md](STORAGE.md)). `--doctor` has two checks for them: the storage and the retention.

## The batch dispatcher: the inputs of a workflow

`python bin/gha_dispatch_all.py plan --inputs` also lists, under each target, the inputs its workflow asks for when it is fired by hand (name, type, required or optional, default, options of a choice and description). They are read from the workflow file at `origin/main` of the local clone with `git show`: nothing is fired, nothing is sent and `gh` is not called. `--json` adds an `inputs` list to every row; it is `null` when the file is not in `origin/main` or uses a form the reader does not know (the flow style `inputs: {…}`), and `[]` when the workflow takes no input.

## Backup and the doctor

`backup` and `doctor` work on the folders of the installation, so they need no running monitor. `doctor` exits `0` when all is well (warnings too), `1` when a check failed, `3` when there are only warnings and `--strict` (or `ops.doctor.strict_exit`) is on, and `4` when the doctor itself could not run; these are the codes of the doctor, the other commands keep the exit codes above. `backup` exits `0` when it is done and `1` when it is refused or the package does not verify. The guide [OPS.md](OPS.md) has the checks, the restore and the scheduled copy. The doctor also has `compare_window` (can the comparison of two periods look back two windows with the history it asks for and keeps) and `etag` (the share of conditional reads answered with 304 in the monitor that runs here, and whether GitHub answers come back without an ETag).
