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

## The connection with an AI tool (read only)

- **Always fresh.** The feed and the brief are rewritten at every refresh of the Alerts tab, at every read of the feed and in every cycle, so they agree with the page (they used to follow it by one cycle). `ALERTS_BRIEF.md` carries `Updated:` (your time zone, with UTC) and a machine line `updated_epoch:`; `GET /api/ai/brief?fmt=json` adds `updated`, `updated_local` and `age_seconds`.
- **Why it is red.** With `ai_alerts.diagnose.enabled` (off by default: it reads the job list and the end of the log of a new red run from GitHub, with read-only calls that count in your allowance) each alert carries `diagnosis`: the first failing step and about ten relevant lines (`ai_alerts.diagnose.log_lines`), cleaned of secrets and kept under `ai_alerts.diagnose.max_bytes`. At most `max_per_cycle` runs are read per cycle, each run once. A log that shows an infrastructure error makes the alert transient.
- **Cascades.** With `ai_alerts.cascade.enabled` (on: it only changes how alerts are listed) an alert that is red because another repository is red - its log names it, or a rule in `ai_alerts.cascade.map` (`{"base-repo": ["client-repo"]}`) says so - is listed under that one in the brief ("Also red because of it (fix this one first)") and carries `origin` in the feed.
- **Stream.** With `ai_alerts.stream.enabled` (off by default), `GET /api/ai/stream[?only=real]` sends server-sent events: a `hello` frame (how many real alerts are open, the first ones, the age of the brief) and one `alert` frame per event of the feed; `Last-Event-ID` (or `?since=`) resumes. It is read only, follows the same access rules as the rest of the page (in the network mode, the access token as a header or cookie), and is limited by `stream.max_clients` and `stream.max_seconds`.
- **Sentinel panels.** The panels A1..A13 of the Sentinel tab and the second sentinel (issues and pull requests) are also data: `GET /api/sentinel/panels[?lang=xx]` (read only, same access rules as the page) gives, per panel, its level (`bad` = act, `warn` = keep an eye on it), one line and the rows to act on, each with its repository and a link; the MCP tool `sentinel_panels` returns the same. The rows of a panel at `bad` or `warn` also become alerts of the feed (class `real` or `watch`, field `panel`), so the stream, the hook, `alerts_open` and the counter "N real alert(s)" of the brief include them, and the brief has a section "Sentinel panels" (its own size limit, it never pushes the CI alerts out). The red workflows of A2 are not repeated: they are alerts already.
- **MCP tools.** `alerts_open` (open alerts with age, diagnosis and origin), `alert_diagnose(id)` (the kept diagnosis, or a read of the log with read-only `gh` calls) and, only with `--allow-ack`, `alert_ack(id)`. When the AI tool connects, the server tells it in its `instructions` and with one notification how many real alerts are open.
- **Gate script.** `python monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user]` (also `status` and `uninstall`; `--dry-run` shows the change) adds `ai_hook.py` to the hook settings of the tool: SessionStart and UserPromptSubmit add the brief to the session when real alerts are open; Stop asks the AI to look at them before it ends a turn, but only with `ai_alerts.client_hook.block_on_stop` (off by default) and not more than once per `cooldown_minutes`. The settings file is merged (other hooks stay), a copy is kept (the last three), a file that is not valid JSON is refused untouched, and everything written is plain ASCII. The default target writes the file `settings.local.json` (project) or `settings.json` (user) in the tool's own hidden folder; `--cursor` writes `.cursor/hooks.json` (best effort: its hook format may change); `--generic` writes nothing and prints the commands. The script needs only Python and reads its figures from `ai_alerts.client_hook`.
- **Is an AI connected?** With `ai_alerts.heartbeat.enabled` a small local file `ai_heartbeat.json` records the last read by the stream, the MCP server, the gate script or an endpoint, and the bar at the foot of the page shows "AI: mcp, 3 min ago" (or "none connected") for `window_minutes`. Nothing is sent anywhere.
- **Does the brief agree with the running monitor?** Yes: its `Monitor:` line says what the monitor is doing (cycle complete, a cycle in progress, connection lost, last cycle failed) and the `Updated` hour is the one of that note; while a cycle is not complete the alerts listed are the ones kept from the last complete cycle (a partial cycle never opens or closes an alert). `actions_monitor_log.txt` writes a `cycle=started` line when each cycle begins, so a long cycle is not mistaken for a monitor that stopped.
- **Private files.** The feed, the brief, the heartbeat and every other state file of the monitor are created with mode 0600 (and the folders the monitor creates with 0700). On Windows the file modes cannot be enforced by the program: the folders inherit the permissions of their parent, so keep the monitor folder inside your own profile.
