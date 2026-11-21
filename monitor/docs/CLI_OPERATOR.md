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

## `watch branch`: the commit you just pushed

```
git push && python bin/monitor_cli.py watch branch
python bin/monitor_cli.py watch branch --repo acme/widgets --branch main --wait 300
python bin/monitor_cli.py watch branch --single-pass --format json
```

`watch branch` asks git which repository (`origin`), branch and commit the folder you are in is on, and follows the workflows of that commit in the monitor: it waits for them to appear, shows them while they run and ends by itself. The exit code is **0** when every workflow passed and **1** when one failed, was cancelled or did not finish in time (a failure is not told apart from a timeout, so `git push && monitor_cli.py watch branch` works in a script). It reads the runs that the monitor already holds, never GitHub, so it spends no allowance; the repository has to be one the monitor watches. The address of the remote is read only to find owner and name and is never printed (it may hold a token).

- `--repo OWNER/NAME` and `--branch NAME` replace what git says. With either of them (or without a commit) the newest run of each workflow of the branch is followed instead of the runs of one commit.
- `--single-pass` (or `--once`): one read and out, with the code of that moment (1 while the runs are not finished).
- `--wait SECONDS`: how long to wait for the runs to finish before giving up with 1 (10 to 86400). Without it the wait is the setting `cli.watch.branch_timeout_seconds` (900).
- A detached commit has no branch: give `--branch`. A folder without a remote called `origin` on GitHub needs `--repo`.

## `monitor N`: a screen that refreshes

`monitor_cli.py monitor [N]` is `watch status` that reads again every N seconds (a number from 1 to 9999, raised to `cli.watch.min_interval_seconds`; without N the default of `cli.watch.default_interval_seconds`). The other options work as in `watch` (`--format`, `--no-clear`, `--url`, `--status-codes operator` ...), and Ctrl-C ends it with 0.

## `doctor --latency`: how late the events are

`monitor_cli.py doctor --latency` adds one check to the doctor. It reads the events of the account (the same list the free change detector `events_feed` uses) and, for the latest pushes, the run of that very commit, and tells the round trip, the median and the worst delay between the start of the run and the event, and how long a change can wait in the worst case with your `events_feed.interval_seconds` (in the field `data` of `--json`). It only reads: nothing is created on GitHub, no test issue or run. A read that fails gives a warning "not evaluable" with its cause, never a failure of the monitor. Over 120 seconds of delay the check warns.

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

### The exit codes of `status` for an operator

By default `status` keeps the codes of the table above, so no script changes. With `--status-codes operator` (or the setting `cli.status_codes` set to `operator`) the command says only three things: **0** healthy, **1** nothing is serving (the monitor cannot be reached or refuses the credential) and **2** it is up but needs attention. Needs attention means: GitHub cannot be reached from the monitor, there is no data yet, the credential is blind, the refresh is paused because the allowance is under its floor, the answer carries an error, an answer that is not the one of a monitor, or **the code on the disk is of another version than the running process** (an update was applied and the monitor was not restarted; `/api/health` says it as `code_stale` and `--doctor` has the check `running`). A usage error is still 1. The reasons are in the field `attention` of `--json`. The failures of red workflows are not part of it: for those use `alerts --fail-on`. `watch status` follows the same codes also when a read fails: a monitor that cannot be reached or refuses the credential ends the loop with 1, an answer that cannot be read with 2.

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
| `cli.status_codes` | `classic` | the exit codes of `status`: `classic` (those of the table) or `operator` (0 healthy, 1 nothing serving, 2 up but needs attention) |
| `cli.watch.branch_timeout_seconds` | 900 | how long `watch branch` waits for the runs of the commit to finish (10 to 86400) |

## What this version does not do

- `completions` has no `--install`: it never writes in the files of a user.
- There is no `proposals` command: the monitor has no route for proposals to act on yet.

## Redirected output, colour and width

- With no terminal (a redirect, `tee`, a pipe, cron) the command writes no escape sequence, takes the width from `COLUMNS` when it is a number and uses 80 otherwise, and text that came from GitHub (a title, a name) is cleaned of the escape sequences it may carry.
- `--color auto|always|never` (default `auto`): `auto` writes colour only on a terminal and never when `NO_COLOR` is set (and not empty) or `TERM=dumb`; `always` writes it whatever the destination; `never` writes none. Only the header of `--format table` is coloured (bold); `json` and `ndjson` are never touched.
- A reader that closes early (`monitor_cli.py alerts --format plain | head -1`) ends the command quietly: no traceback and no error text.

## `metrics`: the figures for cron and for mail

`monitor_cli.py metrics` writes the figures of the monitor as one `name=value` line each, in a fixed order and with nothing else on the standard output: `repos`, `active`, `queued`, `failures_24h`, `successes_24h`, `red_workflows`, `alerts`, `alerts_info`, `alerts_warning`, `alerts_error`, `alerts_critical`, `allowance_remaining`, `allowance_limit` and `offline`. A figure that is not known is left out, never written as 0. It reads the monitor, never GitHub.

With `--if-problem` it writes nothing and exits 0 when there is no red workflow and no alert at `--fail-on` (error by default) or worse; otherwise it writes the figures and exits 5. cron mails any output, so this line mails only the day something is wrong: `*/15 * * * * py -3 /opt/monitor/bin/monitor_cli.py metrics --if-problem`. An unreachable monitor is never silence: the error goes to the standard error output and the exit code is 2.
