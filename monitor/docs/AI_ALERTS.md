<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Alerts for AIs

A red workflow is useless if nobody who works on the repository hears about it. The monitor writes a small feed that any AI tool (Codex, Gemini CLI, Copilot) or script can read.

## What it writes (local, read only, no network)
- `ai_alerts.jsonl`: one line per event (opened, acknowledged, resolved) with a stable id, severity, repository, workflow, conclusion, since when, streak, link, a probable cause (**real** or **transient**), a suggested action and the state.
- `ALERTS_BRIEF.md`: rewritten at every cycle, short (`ai_alerts.brief_max_bytes`, 2 KB by default). Real alerts come first.
- Transient causes (502/503/504, time-outs, rate limits, download failures, a run that never started) are told apart from real failures with rules you can edit in `ai_alerts.transient_patterns`. An alert is resolved by itself when the workflow turns green, and you can acknowledge it (`ack`), which only changes this local state.
- Everything goes through a cleaner first: tokens, keys, e-mail addresses, IP addresses and your home folder never reach the files, the endpoints or the hook.
- The folder is `ai_alerts.folder` (default: next to the monitor); choose one that your AI sessions read. `ci_red.json` carries an optional `ai_hint` (class, cause, action) in each red workflow.

## How an AI reads it
- Put this in the instructions of your project or skill: *"At the start, read ALERTS_BRIEF.md (path) and say which real alerts are open."*
- Or ask the running monitor: `GET /api/ai/brief` (Markdown, or `?fmt=json`) and `GET /api/ai/alerts?since=SECONDS`. They follow the same rules as the rest of the page (this computer; with the network mode, the access token).
- Or add the MCP server (read only): `python mcp_server.py`, tools `get_alerts`, `get_red_repos`, `get_run_failure`, `get_quota`; `--allow-ack` adds `ack_alert` (local state only). Gemini CLI, Codex and VS Code (Copilot): add the same command as a stdio server in their MCP settings.

## Warnings that reach you
- A NEW real alert goes to the notification channels you already configured (Settings > Notifications).
- Optional, off by default: `ai_alerts.hook` POSTs the new real alert (a closed list of cleaned fields) to an address on this computer, at most `max_per_hour` times an hour, so a script of yours can wake an AI session.
- Nothing here sends data to an AI provider, runs a command or writes to GitHub.

## The MCP server is local

`mcp_server.py` speaks JSON over standard input and output with the AI tool that starts it: it has no network port and must never be put behind one. A malformed message gets an error for that message only, a line longer than 64 KB is refused, and `ack_alert` (only with `--allow-ack`) changes nothing but the local state of the feed. The feed can hold repository names and short error messages of the CI; everything is cleaned of tokens, keys, e-mail addresses, IP addresses and the folder of a person before it leaves.
