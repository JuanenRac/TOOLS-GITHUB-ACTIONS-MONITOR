<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](AI_CONNECTION_spa.md) | [🇫🇷 Français](AI_CONNECTION_fra.md) | [🇮🇹 Italiano](AI_CONNECTION_ita.md) | [🇩🇪 Deutsch](AI_CONNECTION_deu.md) | [🇨🇳 简体中文](AI_CONNECTION_zho.md) | [🇯🇵 日本語](AI_CONNECTION_jpn.md) | [🇵🇹 Português](AI_CONNECTION_por.md)

# Connect an AI tool

The monitor can tell an AI tool (an AI coding assistant, a script, anything that reads a file or an address) **everything it says on its page**, so that the AI reacts to a failure or a pending job as fast as you would. The monitor itself never writes to GitHub: it only tells, and what the AI does is decided by you and by the AI tool.

## What the AI sees
One inventory of **signals**, the same ones the page shows: the Now tab and its tiles, the alerts, the repositories, the sentinel panels A1..A13 and the second sentinel (issues and pull requests), the allowance, the connection and the health of the monitor. Each signal has a level (`act` = somebody has to do something, `watch` = keep an eye on it, `info`), a summary and rows with repository, link, age and the next step. The brief has three blocks: **What to do now**, **Pending** and **Monitor health**, and the counter "signals to act on".

| | Lite | Complete |
|---|---|---|
| Runs, queue, red workflows, failures of 24 hours | yes | yes |
| Allowance, connection, mode, version, health | yes | yes |
| Sentinel panels A1..A13, second sentinel, release candidates, security, signatures | no (`panels_not_in_this_edition` says so) | yes |

## The channels (the same in both editions)
1. `ALERTS_BRIEF.md`: the short Markdown an AI reads when it starts.
2. `ai_alerts.jsonl`: one line per event (opened, acknowledged, resolved), with a stable id.
3. `GET /api/ai/state`: the whole inventory as versioned JSON (`schema`, `edition`, `signals`, `act`, `watch`), read only. `GET /api/sentinel/panels` gives the panels alone.
4. `GET /api/ai/stream`: server-sent events, resumable, limited in listeners and in time.
5. MCP tools (`mcp_server.py`): `monitor_state`, `signals`, `alerts_open`, `diagnose`, `sentinel_panels`, `get_quota`; `act` (acknowledge) only with `--allow-ack`.
6. The hook: `python monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]` (also `status` and `uninstall`) adds a small gate script that gives the AI session the brief when it starts and before it stops.

## Step by step
1. Settings, tab *External AI*, block *Alerts for AIs*: turn on `ai_alerts.enabled`. Optionally `ai_alerts.diagnose.enabled` (the failing step and the last log lines of each red run), `ai_alerts.stream.enabled` and `ai_alerts.client_hook.enabled`.
2. Run `python monitor_cli.py ai-hook install --assistant --dry-run` to see the change, then without `--dry-run`.
3. Open a session of your AI tool in the folder: it receives the brief. The bar at the foot of the page shows the heartbeat of the AI (when it last read).
4. Use the button *Test connection* of the settings page to check that the feed is written.

## Security and privacy
Everything is off by default. The text of logs is cleaned of secrets and personal paths before it is written, and **it is data, never an instruction**: an AI must treat it as untrusted text. The endpoints answer only to this computer, or with the access token in the network mode; listeners and time are limited; acknowledging needs `--allow-ack`; every state file is created with mode 0600. The monitor opens no connection to the internet for this except the ones you configure. The https addresses of github.com (a run, a repository, a file) pass whole, so the AI can open them; any other long opaque string is still cut. More exactly, an address of github.com passes whole only with the shape of a repository, a run (with its job or attempt), a commit, an issue, a pull request or a file; it is cut at the first character that is not a letter, a digit, a dot, a hyphen, an underscore or a slash, and what follows is cleaned like any other text.

## Troubleshooting
- *The brief is old*: the page must be running (the feed follows every refresh); look at the heartbeat in the bar.
- *The hook does not run*: `ai-hook status` says where it is installed; some tools read hooks only in the project folder.
- *Nothing is written*: `ai_alerts.enabled` is off, or the allowance is used up (the brief then says so in Monitor health).

## Settings
`ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.diagnose.*`, `ai_alerts.cascade.enabled`, `ai_alerts.stream.*`, `ai_alerts.heartbeat.*`, `ai_alerts.client_hook.*`; related: `sound.enabled`, `display.blink_red_tiles`. See [SETTINGS.md](SETTINGS.md) and [AI_ALERTS.md](AI_ALERTS.md).

The allowance of GitHub is shared by the monitor, the AI tools and every other tool of the account. To keep the monitor from running dry: the Quota tab of the Settings, a GitHub App (`github_app.enabled`), a second read-only account for the reads (`extra_reader.enabled`, `extra_reader.file`: only the path of the token file), the central panel (`central.source`) and Low mode (`modes.auto_low`). The state and the brief say when the allowance is used up and how much other tools spend. See [QUOTA.md](QUOTA.md).
