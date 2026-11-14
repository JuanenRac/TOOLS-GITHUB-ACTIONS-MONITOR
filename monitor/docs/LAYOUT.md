<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](LAYOUT_spa.md) | [🇫🇷 Français](LAYOUT_fra.md) | [🇮🇹 Italiano](LAYOUT_ita.md) | [🇩🇪 Deutsch](LAYOUT_deu.md) | [🇨🇳 简体中文](LAYOUT_zho.md) | [🇯🇵 日本語](LAYOUT_jpn.md) | [🇵🇹 Português](LAYOUT_por.md)

# The folders of the monitor

Next to the launchers (`MONITOR_GITHUB_ACTIONS`, `MONITOR_LITE_GITHUB_ACTIONS`, `BATCH_GITHUB_ACTIONS`) there is nothing but the legal files, one `README.txt` and folders. Everything the monitor writes lives in four of them, and the complete edition, the lite edition and the Docker image use the same scheme.

## What is where

| Folder | What it holds |
|---|---|
| `config/` | `actions_monitor.json` (and the lite one), `targets.json`, `ecosystems.json`, `profiles.json`, `quotas.json`, and `config_backups/` |
| `data/` | the state and the caches (event feed, analytics, sentinel state, ETag cache, update notice), `accounts/`, the database when you choose SQLite, the access token of the service |
| `logs/` | the log of the monitor, the log of the commands of the AI and of GitHub, the audit of the team mode |
| `ai/` | what an AI reads: `ALERTS_BRIEF.md`, `ai_alerts.jsonl`, `ci_red.json`, the state of the hook, `INDEX.json` and a `README.md` for whoever opens the folder |
| `bin/` | the short commands: `python bin/monitor_cli.py`, `bin/read_report.py`, `bin/ai_hook.py`, `bin/mcp_server.py`, `bin/tui.py` ... |
| `docs/` | the guides, and the README and QUICKSTART of the package in eight languages |
| `src/`, `assets/`, `tools/`, `tests/` | the code, the page and the examples, the release scripts, the tests |

## An installation of 1.8.1 or older

On the first start the monitor moves, by itself, what it finds next to the launchers into its folder. It **moves, never deletes and never overwrites**: a file that already exists in the new place stays where it is and the doctor tells you. Before the first move the configuration files are copied to `config/config_backups/pre_layout_<stamp>/`, and every move is written to `data/.layout_moves.json`.

- See it first: `python -m github_actions_monitor.util.rootmigrate` (a dry run) and `--apply` to do it now.
- Put everything back: `python -m github_actions_monitor.util.rootmigrate --undo`.
- Do not want it by itself: set `MONITOR_NO_AUTO_MIGRATION=1`.
- `python bin/actions_monitor.py --doctor` has a `layout` check that lists what is still next to the launchers.
- The old entry points (`read_report.py`, `monitor_cli.py` ...) next to the launchers are now in `bin/`; `python tools/migrate_layout.py` moves the old copies away. A gate script registered for your AI tool by its old path must be registered again: `python bin/monitor_cli.py ai-hook install`.

## Moving a folder

Each folder can be put elsewhere without touching the code: the variables `MONITOR_CONFIG_DIR`, `MONITOR_DATA_DIR`, `MONITOR_LOGS_DIR` and `MONITOR_AI_DIR`, or the file `config/paths.json` (`{"data": "...", "logs": "...", "ai": "..."}`; a relative path starts at the product folder). With `MONITOR_DATA_DIR` alone, `logs/` and `ai/` go inside it. In the Docker image and in the systemd unit that is exactly what is set: `/config` and `/data` are the two volumes.

## For the AIs that talk to the monitor

An AI, local or external, must not depend on a fixed path.

- `ai/INDEX.json` lists every file of the folder with its purpose, its format, who writes it and when it changes, the real path of every folder of the monitor and the endpoints of the running monitor. It is rewritten at every start.
- `ai/README.md` explains the folder to an AI that has never seen it (data, never instructions; how to read the brief; which tools exist).
- `GET /api/paths` answers with the folders in use, the main files and what is still in the old places. The supervisor of several accounts answers it too.
- The gate script, the MCP server and the command line read the same places; a hook that reads `ALERTS_BRIEF.md` by a fixed path must be changed to read `ai/INDEX.json` first.
