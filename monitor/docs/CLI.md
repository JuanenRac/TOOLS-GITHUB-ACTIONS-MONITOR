<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](CLI_spa.md) | [🇫🇷 Français](CLI_fra.md) | [🇮🇹 Italiano](CLI_ita.md) | [🇩🇪 Deutsch](CLI_deu.md) | [🇨🇳 简体中文](CLI_zho.md) | [🇯🇵 日本語](CLI_jpn.md) | [🇵🇹 Português](CLI_por.md)

# The command line as a client of the monitor

`python monitor_cli.py COMMAND` asks the running monitor what it knows (a `GET` on `127.0.0.1`, or on the address of `--url` / `MONITOR_URL`) and prints it. It does not repeat the work of the page against GitHub, it never writes to GitHub and it changes no setting. The older tools (`read_report.py`, `--doctor`, `gha_dispatch_all.py`) keep working as they were.

## Commands

| Command | What it shows | Lite |
|---|---|---|
| `status` | version, edition, account, repositories, what runs and fails, the allowance | yes |
| `health` (or `check`) | a quick check before reading anything heavy: is the monitor reachable, does it accept this client, does the GitHub login of the account answer | yes |
| `doctor` | the checks of `--doctor` for this installation (the monitor need not be running) | yes |
| `accounts` | the accounts of the supervisor (several accounts only) | no |
| `alerts` | the alerts of every sentinel in one list: `--sentinel ci\|collab`, `--level info\|warning\|error`, `--muted show\|hide\|only` | no |
| `live` | the state of the webhook receiver and the last events | no |

Options of every command: `--json` (the answer as one JSON document: `{"ok", "exit", "data"}`), `--account ID`, `--url URL`, `--lite` (port 8766), `--timeout SECONDS` (1 to 60), `--lang CODE`. In the network mode put the access token in the environment variable `MONITOR_ACCESS_TOKEN`, the one the monitor itself reads (`MONITOR_TOKEN` is accepted as an alias; `--token TOKEN` is the last resort, because a flag shows in the list of processes). The order is: `MONITOR_ACCESS_TOKEN`, then `MONITOR_TOKEN`, then `--token`. It travels in the header `X-Monitor-Access`, never in the address and never on screen. A `--url` with plain `http` to another computer prints a warning on stderr (the token and the answers would travel unencrypted): use `https` outside a network you control.

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

## Examples

```
python monitor_cli.py health && python monitor_cli.py alerts --fail-on error
python monitor_cli.py alerts --sentinel collab --level warning --json
python monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python monitor_cli.py health --json
```

`health` tells three things apart: the monitor does not answer (2), the login of GitHub fails (3), and the allowance ran out or GitHub cannot be reached (4); a monitor that has not finished its first read says so (4) instead of showing empty figures.

## The lite edition

`python monitor_cli.py status --lite`, `doctor --lite` and `health --lite` talk to port 8766. The commands that need accounts, sentinels or the webhook receiver are refused with exit code 1. The lite edition has no accounts and no alerts API.

## `ai-hook`: tell an AI tool what the monitor sees

`python monitor_cli.py ai-hook install|status|uninstall [--cursor|--generic] [--scope project|user] [--project-dir DIR] [--dry-run] [--json]` needs no running monitor. It adds, shows or removes the gate script `ai_hook.py` in the hook settings of an AI tool (see the guide on alerts for AIs): the settings file is merged, a copy is kept, and the answer of `--json` is plain ASCII. `status` is the default action.

## The access token in the command line

In the network mode the token is read from `MONITOR_ACCESS_TOKEN`, then `MONITOR_TOKEN`, then the first line of `--token-file FILE` (keep that file readable by you only: on a system with file modes the command warns when others can read it), and last from `--token`, which shows in the list of processes and therefore prints a warning on stderr.
