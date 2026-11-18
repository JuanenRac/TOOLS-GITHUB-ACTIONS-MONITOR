<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Update the monitor (the updater)

**English** · [Español](UPDATE_spa.md) · [Français](UPDATE_fra.md) · [Italiano](UPDATE_ita.md) · [Deutsch](UPDATE_deu.md) · [简体中文](UPDATE_zho.md) · [日本語](UPDATE_jpn.md) · [Português](UPDATE_por.md)

The updater moves an installation from any published version to any other (up or down), migrates your configuration with it and keeps a way back. It is ONE file, `monitor_updater.py`, that needs only Python and works on whatever version you have installed; it also lives inside the product (`tools/monitor_updater.py`) and as the command `monitor_cli.py update`. It never updates by itself: only when you ask, and it never deletes anything (what is replaced goes to the folder of copies).

## Three ways to open it

- `py -3 monitor_updater.py` opens a page in your browser. It is served on 127.0.0.1 only while the updater runs, with a one-time token in the address; nothing else can use it.
- `py -3 monitor_updater.py --tk` opens the same in a window (needs Tkinter).
- `py -3 monitor_updater.py --console` is a text menu for servers, SSH and containers.
- `py -3 bin/monitor_cli.py update` is the same file run from the product; `update plan`, `update apply` and the other commands below take the options of the table.

## The Updates menu inside the monitor

The Complete edition has the same updater inside its page: **System > Updates**. It shows the installed version and the one the check found (setting `updates.check`; nothing is asked of GitHub while it is off or the monitor is offline), the notes of each release and, with the button "Look for versions", the list of published ones. Nothing is downloaded or applied unless you press a button. Applying needs an administrator at the computer where the monitor runs (the routes `/api/updates/*` answer 403 from the network) and a confirmation that says what will happen: the SHA-256 of the zip against SHA256SUMS, the copy made first (with its folder), the migration of the configuration and the restart. The update runs in a process of its own: the monitor stops by itself, the update is applied, the monitor starts again with the new version and the page reconnects; if the new version does not start, the previous one is put back and started. "Go back to the version before" does the same in reverse. The steps, the history and the result are shown on the page and written in the log of actions. It is not offered in the Lite edition, in a container or under a service manager (they restart the process on their own: use the command line), and only one update runs at a time. Your configuration, data, keys and logs are not replaced. The stand-alone file stays as the way back when the monitor does not start.

## What it does, step by step

1. Detects the installation: folder, version, edition (Complete or Lite), configuration, data, ports, whether the monitor is running, container or service.
2. Lists every version published on GitHub (no token needed) with its date and notes, and marks the installed one and the latest. Without a connection, give it a zip with `--zip`.
3. You choose the target version. A lower one is a downgrade: it asks for `--allow-downgrade`.
4. Shows the PLAN as a dry run: the chain of steps between the two versions (read from the registry of migrations), what changes in YOUR configuration, the changes of behaviour you will notice and every incoherence found.
5. Applies it: a copy first, the SHA-256 checked against SHA256SUMS, the zip unpacked into a new folder and inspected (paths with `..`, links, size), the product copied, your own lines of the launchers put back, the configuration migrated, the layout migrated, and optionally the monitor started and `/api/health` checked.
6. If anything fails it returns to the previous state by itself and writes a report. Every update is added to the history (`update_history.jsonl`) and the last one can be undone with the command `rollback`.

## Commands

Without a command the page opens. The commands answer once (add `--json` for a document):

| Command | Meaning |
|---|---|
| `status` | what is installed and what the checks find |
| `releases` | every published version |
| `plan` | the dry run for a target |
| `apply` | do it (`--dry-run` only shows the plan) |
| `migrate` | only migrate a configuration file, see below |
| `rollback` | go back to the version before the last update |
| `history` | the updates made on this installation |

## Options

| Option | Meaning |
|---|---|
| `--dir` | the installation (default: where the file lives, looking upwards) |
| `--to` | target version (default: the latest) |
| `--from` | migrate: the version the file comes from |
| `--config` | migrate: a configuration file |
| `--zip` | use this zip instead of GitHub |
| `--sha256` | expected SHA-256 of the zip |
| `--dry-run` | only show the plan |
| `--apply` | migrate: write the result |
| `--yes` | do not ask for confirmation |
| `--json` | the answer as one JSON document |
| `--keep-old-defaults` | write the old default of every setting you never set, so the behaviour does not change |
| `--adopt-new-defaults` | also move the settings that still hold the old default to the new one |
| `--start` | start the monitor afterwards and check it |
| `--handover` | the monitor that started this process stops by itself: wait for it, apply, start it again (a failed start brings the previous version back) |
| `--status-file` | write the progress to this JSON file (the Updates menu reads it) |
| `--edition` | complete or lite, when it cannot be told |
| `--allow-downgrade` | permit a lower version |
| `--allow-container` | work inside a container anyway (the image is not replaced) |
| `--no-gh` | do not use the `gh` program, only the public API |
| `--backups` | folder of copies (default: update_backups in the installation) |
| `--restore-data` | yes, no or auto: what the return does with the data |
| `--port` | port of the page |
| `--no-browser` | do not open the browser |
| `--tk` | the window |
| `--console` | the text menu |
| `--lang` | language: en es de fr it ja zh pt |

## Your configuration and the changed defaults

- The registry of migrations (JSON files versioned in every release, `assets/migrations/`) says for each version what changed: settings renamed, removed or added, new defaults, files moved, changes of behaviour. The updater applies the chain of the versions you jump over.
- By default it keeps what you set explicitly and adopts a new default only where you never defined the setting. A change of behaviour (for example a feature that is now off by default) is told in the report; `--keep-old-defaults` pins the old behaviour, `--adopt-new-defaults` moves everything to the new one.
- `migrate` works on a file alone: `monitor_updater.py migrate --from 2.0.1 --to 2.0.8 --config my.json` shows the result, `--apply` writes it (after a copy). Secrets are masked in every report.

## Checks before applying

- Blocking: the monitor is running, the SHA-256 does not match, the zip is unsafe, not enough disk space, data from a newer schema than the target, a container, an update already pending.
- Warnings: settings that no longer exist or changed type or range, values out of range, duplicated keys, a port taken by another program, a launcher you changed, a step that needs another one first. Each warning has a suggested action.

## Safety and the way back

- It listens only on 127.0.0.1 with an ephemeral token, refuses cross-site requests, runs nothing from the zip, uses no shell and writes only inside the installation and the folder of copies.
- Before changing anything it makes a copy of the package, the configuration and the data; if a step fails the copy is restored and a report written. If even the return fails, the copy is intact and the report says how to restore it by hand.
- Offline: `--zip FILE` with `--sha256` (or a SHA256SUMS next to it). Docker: the volume is updated, the image is not replaced from inside (`--allow-container` to force).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | done, or nothing to do |
| 2 | wrong use |
| 3 | blocked by a check, nothing changed |
| 4 | download, SHA-256 or zip failed, nothing changed |
| 5 | failed and the previous state was restored |
| 6 | failed and the return failed too: restore the copy by hand |
| 7 | no connection to GitHub and no zip given |
| 8 | not confirmed |
