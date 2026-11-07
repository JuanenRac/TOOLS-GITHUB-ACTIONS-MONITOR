<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# The Settings tab

The Settings tab (the gear icon in the header or in the tab bar) changes the values of `actions_monitor.json` from the page, so nobody has to edit the file by hand.
It is written in the eight languages of the page and follows the look of the rest of it.

## What can be changed

Only the keys of the list in `settings_api.py` (the schema). Each one has a type and a range, and the page says whether a change needs a **restart** of the monitor (the loop reads
its configuration once) or **applies now**.

| Group | Keys |
|---|---|
| This browser | language of the page, theme (auto / light / dark), dense view of the Now tab. These are kept in the browser, not in the file. |
| General | `language` (default language of the tools), `github_owner`, `mode` (`full` / `lite`), `ecosystems`, `exclude`, `report_history_days` |
| Refresh and limits | `refresh_seconds`, `cold_refresh_seconds`, `issues_refresh_seconds`, `discover_refresh_seconds`, `stuck_minutes`, `runs_per_repo`, `cold_runs_per_repo`, `hot_hours`, `max_workers`, `min_rate_remaining` |
| Sentinel | `sentinel.enabled`, the cycles, the API budget, the thresholds of candidates, stale pull requests and pending signatures, `sentinel.require_verified_signature`, the A2 lookups |
| Surface checks (A10) | `sentinel.surface.enabled`, its cycles, the repositories per cycle, the allowance factor and the share of the budget |
| Readiness (A11) | `sentinel.readiness.enabled`, `min_coverage`, `warn_below` |
| Folders and files | `workspace_root`, `signed_dir`, `audit_dir`, `ecosystems_file`, `targets_file`, `profiles_file`, `tools_dir`, `sentinel.ci_red_file`, `sentinel.ci_red_audit_copy` |
| Outputs for other tools | `outputs.prometheus.enabled`, `outputs.prometheus.per_repo`, `outputs.json.enabled`, `outputs.dashboard.enabled` (see OUTPUTS.md) |

## What can never be changed or seen from the page

Tokens, secrets, signature keys, the webhook secret, the command the sentinel can run (`sentinel.notify_command`), the AI settings and any key of another tool: they are **not in the
schema**, so the page neither shows nor writes them, and a request that names one is refused. Every other key of the file is kept exactly as it was.

## How a save works

1. Only the values that changed are sent, as `POST /api/settings` with `Content-Type: application/json` and a body of at most 16 KB.
2. Every value is checked against its type and range; one invalid value refuses the whole request and nothing is written. Paths must be text without control characters, never a
   network (UNC) path and never on the `D:` drive.
3. The previous file is copied to `config_backups/actions_monitor-<time>.json` (the last ten copies are kept).
4. The new file is written to a temporary file and moved over the old one (atomic), so a crash never leaves half a file. A file that is not valid JSON is never overwritten from the page.
5. The page says which saved values need a restart and keeps a banner until you restart.

## Who may ask

Only the page of the same machine: the server listens on `127.0.0.1` and refuses a request whose `Host` or `Origin` is not its own address (the same checks as every other endpoint).
A cross-site form cannot reach it because the request must be JSON.

## Before 1.5.0

The language of the tools was decided by the language of the system; now they start in English and the language is a setting (here, `language`, `MONITOR_LANG` or `--lang`).
`parte_history_days` is now `report_history_days` (the old name is still read).
