<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# How to connect, by kind of tool

This skill does not depend on one assistant or one model. A tool that talks to the monitor does it in one of five ways; look at what YOUR tool can do and take that row.

| Your tool can | Way | How | Needs |
| --- | --- | --- | --- |
| read files | files | read `ai/INDEX.json` first (it says where everything is), then `ai/ALERTS_BRIEF.md`, `ai/ai_alerts.jsonl` and `ai/LESSONS.md` | `ai_alerts.enabled` |
| make HTTP requests | HTTP | `GET /api/ai/brief`, `/api/ai/state`, `/api/ai/lessons?fmt=brief&repo=NAME` | the access token in the network mode |
| write a typed client | HTTP | `GET /api/v1/me`, `GET /api/v1/openapi.json` (every frozen route with its keys and types; the same data as `monitor_cli.py api openapi`; `monitor_cli.py api contract-check` verifies the server; the MCP tools `api_me`, `api_openapi` and `api_contract_check` give the same three) | `api.v1_enabled` (`auto` answers when the monitor runs as a service) |
| speak MCP | MCP | `python bin/mcp_server.py` (read only; `--allow-ack` and `--allow-lessons` for the little it may write) | the MCP configuration of the tool pointing at that command |
| keep a connection open | stream | `GET /api/ai/stream?only=real` (server-sent events; it ends after `ai_alerts.stream.max_seconds`, arm it again) | `ai_alerts.stream.enabled` |
| run commands | command line | `python bin/monitor_cli.py alerts`, `lessons brief --repo NAME`, `ai models`, `ai doctor`, and `ai-hook install` to be told at the start of a session | Python on the same computer as the monitor |

If your tool can do several, prefer the cheapest for the quota: files or the brief first, the stream second, a command or a request last. Never poll faster than every 60 seconds.

## The tools of the MCP server

`python bin/mcp_server.py` answers `tools/list` with these tools; all of them only read, apart from the two that change the local state of the feed or of the library and need a flag.

- Alerts: `get_alerts` (the open alerts of the feed), `alerts_open` (the same with age, failing step and the red repository they fall together under), `get_red_repos`, `get_run_failure` (the failed steps of one run), `alert_diagnose` and `diagnose` (the failing step and the last lines of the log of one alert), `alert_ack`, `ack_alert` and `act` (acknowledge an alert; only with `--allow-ack`, the local state of the feed and nothing else).
- State: `monitor_state` and `signals` (everything the monitor says, as signals), `sentinel_panels` (the panels of the Sentinel tab as data), `get_quota` (the allowance and the minutes), `get_score` (the score with its parts).
- Lessons: `lessons_brief` (read it before a push), `lessons_apply`, `lessons_recurring`, `lesson_propose` (checks a lesson and writes nothing; it is written only with `--allow-lessons` and `lessons.allow_write`).
- Briefs: `briefs_index` (one catalogued brief per tab) and `brief_tab` (the brief of one tab, or `all`).
- The read API for clients: `api_me` (who the monitor takes you for), `api_openapi` (the document of every frozen route, or one with `path`) and `api_contract_check` (the contract suite).

## Installing the instructions

`python bin/monitor_cli.py install-skill external --dest FOLDER` copies this skill into the folder where your tool reads its skills or rules. Any tool that reads Markdown files can use it, and nothing in it names an assistant. `GET /api/skills` and `GET /api/skills?name=external&all=1` give the same text over HTTP.

## Version and compatibility

The skills travel with the monitor and have its version: `GET /api/skills` answers `monitor_version` (and a `version` for each skill) and `monitor_cli.py --version` prints it. A copy that you installed earlier may describe an older monitor: after updating the monitor install again into an empty folder, or remove the old copy first (an edited file is never overwritten). The generated references (`api.md`, `cli.md`, `settings.md`...) are built from the code of that version, so a route or a command that is not in your copy may exist in a newer monitor and the other way round.

## When an AI of the monitor does not answer

`python bin/monitor_cli.py ai doctor` checks in order the provider, its address, whether the variable of the key is set (it only says yes or no), the name of the model against the list of the provider, the network, the daily cap and the last test of the model, and says the first thing that is wrong. `ai models` lists the models and their data (unknown stays unknown) and `ai test --provider NAME --model NAME` tries one with a made-up failure, never with data of a repository.
