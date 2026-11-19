<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](CLI_OPERATOR_spa.md) | [🇫🇷 Français](CLI_OPERATOR_fra.md) | [🇮🇹 Italiano](CLI_OPERATOR_ita.md) | [🇩🇪 Deutsch](CLI_OPERATOR_deu.md) | [🇨🇳 简体中文](CLI_OPERATOR_zho.md) | [🇯🇵 日本語](CLI_OPERATOR_jpn.md) | [🇵🇹 Português](CLI_OPERATOR_por.md)

# The command line for the operator

The basics of `monitor_cli.py` are in [CLI.md](CLI.md). This page is for the person who lives in a terminal: how the answers are written (`--format`), how to watch (`watch`), how to complete the commands (`completions`), the exit codes, and the address for a TV (`kiosk`). Everything here reads the API of the monitor on this computer (or the one of `--url`); nothing writes to GitHub and nothing here spends the allowance.

## Formats: `--format`

| Format | What you get |
|---|---|
| `text` | what each command has always written. It is the default. |
| `table` | the records as columns that fit the width of the terminal (Japanese and Chinese characters count as two cells). There is no colour, so `NO_COLOR` is respected. |
| `plain` | one record per line, the fields separated by a tab, no header: for `grep`, `cut` and `awk`. A tab or a line break inside a text becomes a space. |
| `json` | the document `{"ok", "exit", "data"}`. `--json` is the same thing. |
| `ndjson` | one JSON object per line, one per record (an alert, an account, a repository, an event). A command that answers with one thing (`status`, `health`) gives one line. |

`--format` wins over `--json`, and both win over the setting `cli.default_format` (default `text`). The three structured formats are made from the same document as `--json`, so they never disagree. A list that is empty prints nothing in `ndjson` and `plain`.

## `watch`: the same read again and again

```
python bin/monitor_cli.py watch status
python bin/monitor_cli.py watch alerts --interval 10 --format table
python bin/monitor_cli.py watch alerts --exit-on-change --format ndjson
```

`watch status|alerts` repeats the read of the command. It reads the API of the monitor, not GitHub, so a short interval does not spend the allowance. The options:

- `--interval SECONDS`: the pause between two reads. The floor is the setting `cli.watch.min_interval_seconds` (2 by default): a shorter interval is raised to it. Without `--interval` the pause is `cli.watch.default_interval_seconds` (5).
- `--once`: one read and out (the exit code is the one of the command).
- `--exit-on-change`: the loop ends with exit code **6** when what it watches is not what it was at the first read (the set of alerts, or the figures of the status). A clock that ticks is not a change. Without the flag the exit code 6 never appears.
- `--no-clear`: do not clear the screen between two reads (the screen is cleared only on a terminal and only in `text` and `table`).
- A monitor that cannot be read is retried with a longer pause each time (the interval doubled, at most a minute) and the error goes to the standard error. **Ctrl-C** ends the loop with exit code 0.

## `completions`: complete the commands

```
python bin/monitor_cli.py completions bash > ~/.local/share/bash-completion/completions/monitor_cli.py
python bin/monitor_cli.py completions zsh  > "${fpath[1]}/_monitor_cli"
python bin/monitor_cli.py completions fish > ~/.config/fish/completions/monitor_cli.py.fish
python bin/monitor_cli.py completions powershell | Out-String | Invoke-Expression
```

The script is written from the real parser of the command line, so it offers exactly the commands, words and options that exist: a new option cannot be forgotten, and a test compares both. The command only **prints**; it does not edit any file of yours and needs no monitor. Put the output where your shell reads completions, as above.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | all right (also Ctrl-C in `watch`) |
| 1 | wrong use of the command |
| 2 | the monitor cannot be reached |
| 3 | the monitor or GitHub refuses the credential |
| 4 | the monitor answers but is degraded (offline, allowance exhausted, no data yet) or the answer cannot be read |
| 5 | `alerts --fail-on LEVEL` found alerts of that level or worse |
| 6 | `watch --exit-on-change` saw a change (only when that flag is given) |

The codes 0 to 5 are the ones of [CLI.md](CLI.md); a test keeps this table and the code in agreement.

## Examples with `jq`

These examples use only fields that are part of the stable shape of the answers, and they are run by a test against a fake monitor (when `jq` is installed).

```
monitor_cli.py alerts --json | jq -r '.data.alerts[] | select(.level=="critical") | .repo'
monitor_cli.py alerts --format ndjson | jq -r '.code'
monitor_cli.py status --json | jq '.data.red_workflows'
monitor_cli.py team --json | jq -r '.data.ranking[] | .repo'
```

## `kiosk`: the address for a TV or a wall

`monitor_cli.py kiosk [ops|team|release|quiet]` prints the address of the monitor for a screen nobody touches. See [KIOSK.md](KIOSK.md).

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `cli.default_format` | `text` | the format when no `--format` or `--json` is given: `text`, `table`, `plain`, `json` or `ndjson` |
| `cli.watch.min_interval_seconds` | 2 | the shortest pause of `watch` (1 to 3600) |
| `cli.watch.default_interval_seconds` | 5 | the pause of `watch` when `--interval` is not given (1 to 3600) |

## What this version does not do

- `completions` has no `--install`: it never writes in the files of a user.
- There is no `proposals` command: the monitor has no route for proposals to act on yet.
