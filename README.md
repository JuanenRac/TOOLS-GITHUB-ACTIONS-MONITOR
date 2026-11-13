<p align="center">
  <img src="images/GITHUB_ACTIONS_MONITOR_BANNER.svg" alt="GitHub Actions Monitor" width="100%">
</p>

# GitHub Actions Monitor

<p align="center">
  <b>🇺🇸 English</b> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

<p align="center">
  <a href="https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases/latest"><img src="https://img.shields.io/github/v/release/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR?label=version&color=2EE6A6" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL-3.0-or-later">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Dependencies-none-2EE6A6.svg" alt="No dependencies">
  <img src="https://img.shields.io/badge/Languages-8-FFB300.svg" alt="8 languages">
</p>

> Watches the workflows of every repository you own and tells you, on one local page, what is red, what is stuck and what is waiting for you.

**GitHub Actions Monitor** is a small program that runs on your own computer. It asks GitHub, through your own `gh` login, for the latest runs of every workflow of your repositories, decides what is really red, raises alerts (security, hygiene, releases that are ready, quota) and shows everything on a web page that only your machine can open. It has no dependencies beyond Python and `gh`, it never stores a token and, by default, it only reads.

## At a glance

| | |
|---|---|
| **Version** | **1.7.9** · [all releases](https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases) |
| **Needs** | Python 3.11+ and the GitHub CLI (`gh auth login`); nothing else (the terminal view uses the optional package `rich`) |
| **Opens** | a page on `127.0.0.1` only, in eight languages |
| **Writes to GitHub** | never by itself: only batch commands you run with an explicit `--go` |
| **Exports** | `ci_red.json`, Prometheus metrics and JSON for Grafana (all off until you switch them on) |

<!-- glance:begin -->

**Measured today** (v1.7.9)

| | |
|---|---|
| **Maturity** | functional |
| **Tests** | 1264 test methods (`python -m unittest discover -s monitor/tests`) |
| **Settings** | 288 settings, all with help |
| **Languages** | 8 (English, Spanish, German, French, Italian, Japanese, Chinese, Portuguese) |
| **Tested in the CI on** | ubuntu, windows, macos, Python 3.11, 3.13 |

## Project status

Each line is one part of this repository and the light says how far it is today: what the tests and the CI can show and what has run for real, not what is planned.

🟢 Done and verified · 🟡 Works, with known limits · 🟠 Partly done or not verified yet · 🔴 Not done or not working

| Area | State | What it means here |
|---|---|---|
| Monitor and page | 🟢 | Runs every day on a real account; the tests run in the CI on three systems. |
| Sentinel (A1..A13) | 🟢 | Runs every day on a real account; its levels and rows are tested with fixtures. |
| Notifications | 🟡 | Tested against simulated servers; not every channel has been tried against the real service. |
| Connection with an AI tool and MCP | 🟡 | The feed, the state, the stream, the hook and the MCP tools are tested with a real server and a simulated client; no independent user has run them yet. |
| Lite edition | 🟡 | Tested in the CI and shares the channels and settings of the complete one; little real use so far. |
| GitHub App, central panel and Low mode | 🟠 | New: tested with simulated servers and files; not yet run for a long time against the real service. |
| Linux and macOS | 🟠 | Tested in the CI only; the daily use is on Windows. |

<!-- glance:end -->

## Screenshots

### The page

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_now_light.png"><img src="docs/screenshots/web_now_dark.png" alt="Now" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_alerts_light.png"><img src="docs/screenshots/web_alerts_dark.png" alt="Alerts: every sentinel in one list, with local silences" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_light.png"><img src="docs/screenshots/web_sentinel_dark.png" alt="Sentinel" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_queue_light.png"><img src="docs/screenshots/web_sentinel_queue_dark.png" alt="Signing queue (most urgent first)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_analytics_light.png"><img src="docs/screenshots/web_sentinel_analytics_dark.png" alt="A12 · Analytics: durations, queue time, steps and flaky workflows" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_charts_light.png"><img src="docs/screenshots/web_charts_dark.png" alt="Charts" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_repositories_light.png"><img src="docs/screenshots/web_repositories_dark.png" alt="Repositories" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_history_light.png"><img src="docs/screenshots/web_history_dark.png" alt="History" width="92%"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_about_light.png"><img src="docs/screenshots/web_about_dark.png" alt="About" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_help_light.png"><img src="docs/screenshots/web_help_dark.png" alt="Help, searchable and offline" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_basic_light.png"><img src="docs/screenshots/web_settings_basic_dark.png" alt="Settings · Basic: plan, quotas and discovery" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_now_light.png"><img src="docs/screenshots/web_network_now_dark.png" alt="The network mode: the persistent red bar" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_notices_light.png"><img src="docs/screenshots/web_network_notices_dark.png" alt="The bar at the foot: the most important notice and the window with all of them" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_settings_light.png"><img src="docs/screenshots/web_network_settings_dark.png" alt="Settings · the network mode with its warning and the HTTPS proxy name" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_all_light.png"><img src="docs/screenshots/web_accounts_all_dark.png" alt="All the accounts: one card per account" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_one_light.png"><img src="docs/screenshots/web_accounts_one_dark.png" alt="The page of one account, with the switcher" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_live_light.png"><img src="docs/screenshots/web_accounts_live_dark.png" alt="Live view: the webhook receiver and the working mode" width="92%"></picture></p>

<details><summary><b>Settings, sub-tab by sub-tab</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_interface_light.png"><img src="docs/screenshots/web_settings_interface_dark.png" alt="Settings · This browser" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_general_light.png"><img src="docs/screenshots/web_settings_general_dark.png" alt="Settings · General" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_polling_light.png"><img src="docs/screenshots/web_settings_polling_dark.png" alt="Settings · Refresh and limits" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_cache_light.png"><img src="docs/screenshots/web_settings_cache_dark.png" alt="Settings · Reads and cache" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_sentinel_light.png"><img src="docs/screenshots/web_settings_sentinel_dark.png" alt="Settings · Sentinel" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_surface_light.png"><img src="docs/screenshots/web_settings_surface_dark.png" alt="Settings · Surface checks (A10)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_readiness_light.png"><img src="docs/screenshots/web_settings_readiness_dark.png" alt="Settings · Readiness (A11)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_paths_light.png"><img src="docs/screenshots/web_settings_paths_dark.png" alt="Settings · Folders and files" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_outputs_light.png"><img src="docs/screenshots/web_settings_outputs_dark.png" alt="Settings · Outputs for other tools" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_ai_light.png"><img src="docs/screenshots/web_settings_ai_dark.png" alt="Settings · External AI for the sentinel" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_webhook_light.png"><img src="docs/screenshots/web_settings_webhook_dark.png" alt="Settings · Incoming webhook" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_notify_light.png"><img src="docs/screenshots/web_settings_notify_dark.png" alt="Settings · Notifications" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_analytics_light.png"><img src="docs/screenshots/web_settings_analytics_dark.png" alt="Settings · Analytics" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_lint_light.png"><img src="docs/screenshots/web_settings_lint_dark.png" alt="Settings · Workflow linter" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_console_light.png"><img src="docs/screenshots/web_settings_console_dark.png" alt="Settings · Terminal view" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_advanced_light.png"><img src="docs/screenshots/web_settings_advanced_dark.png" alt="Settings · Advanced (opt-in)" width="92%"></picture></p>

</details>

<details><summary><b>Console tools</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_read_report_light.png"><img src="docs/screenshots/console_read_report_dark.png" alt="read_report.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_migrate_state_light.png"><img src="docs/screenshots/console_migrate_state_dark.png" alt="migrate_state.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_plan_light.png"><img src="docs/screenshots/console_plan_dark.png" alt="gha_dispatch_all.py plan" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_lint_light.png"><img src="docs/screenshots/console_lint_dark.png" alt="lint_workflows.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_tui_light.png"><img src="docs/screenshots/console_tui_dark.png" alt="tui.py" width="92%"></picture></p>

</details>

<details><summary><b>The lite edition</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_now_light.png"><img src="docs/screenshots/web_lite_now_dark.png" alt="lite · Now" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_charts_light.png"><img src="docs/screenshots/web_lite_charts_dark.png" alt="lite · Charts" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_history_light.png"><img src="docs/screenshots/web_lite_history_dark.png" alt="lite · History" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_settings_light.png"><img src="docs/screenshots/web_lite_settings_dark.png" alt="lite · Settings" width="92%"></picture></p>

</details>

Each picture follows the light or dark theme of your GitHub page.

*Demo data: the repositories and names in the pictures are invented.*

## What it does

- **Red or not, by one rule**: the last finished run of each workflow on the default branch. Cancelled and skipped runs never hide an earlier failure.
- **Sentinel**: security alerts, repository hygiene, stale pull requests, releases that are ready to cut, builds waiting to be signed, and a plain-language report.
- **Collab sentinel and one list of alerts**: open issues and pull requests that need a person (forgotten, critical, reviews waiting, old drafts, conflicts), read only and on a clock of its own, and an Alerts tab with every sentinel in one list, a filter by origin and local silences that end by themselves.
- **A status bar, full screen and tables you can sort**: the most important notice (and a window with all of them), the connection, the allowance, the last read, the mode, the address and the clock at the foot of the page; a full screen button; Repositories and History sort by one or several columns, with the columns you choose.
- **The command line as a client**: `monitor_cli.py` (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`) reads what the running monitor says, with `--json` and stable exit codes; it never writes to GitHub.
- **Settings page**: change paths, intervals, quotas and switches from the browser; only a fixed list of keys, validated, with a backup before every save.
- **Charts and history**: compute minutes, failures and successes with animated bars and a daily history (it respects reduced motion).
- **Eight languages** (en, es, de, fr, it, ja, zh, pt) with English as the base; switch in Settings.
- **Outputs for dashboards**: `ci_red.json`, a Prometheus endpoint and a JSON source for Grafana, with an importable Grafana dashboard.
- **Batch tools**: plan and dispatch many builds at once; nothing is fired without `--go`.
- **About and Help in the page**: the **i** button shows the version, the edition, the links, the files, the health and a button that copies the information for support; the **?** button (or the key `?`) opens the whole documentation, searchable and in your language, with no Internet. The console has `--about` and `--help-topics`, and a tab-by-tab interactive terminal application (optional `textual`).
- **Notice of a newer version**: a discreet badge when a newer release is published; it only reads the public releases page once a day, never installs anything and can be switched off (always off when air-gapped).
- **Quotas for every account**: plan, billable minutes (public repositories cost none), allowance of the API read from GitHub's headers, concurrency and jobs near the 6-hour limit; the figures are in an editable file.

## Architecture

<p align="center"><img src="images/architecture.svg" alt="Architecture" width="100%"></p>

## Start here: which edition?

| If you want... | Start | Port |
|---|---|---|
| to watch what runs and what failed, nothing more (**start here**) | `MONITOR_LITE_GITHUB_ACTIONS` | 8766 |
| the whole account watched for you: alerts, releases, signing, readiness, analytics | `MONITOR_GITHUB_ACTIONS` (with the [sentinel](monitor/docs/SENTINEL.md)) | 8765 |

The console window says which one is running, in its title and in its first line. Not sure yet? `python actions_monitor.py --demo` opens the page with invented data, and `--doctor` checks your installation. [Your first five minutes](monitor/docs/FIRST_STEPS.md)

## Quick start

1. Install Python 3.11 or newer and the [GitHub CLI](https://cli.github.com/), then run `gh auth login`.
2. Download this repository (or the zip of the latest release) and open the `monitor` folder.
3. Start it: Windows `MONITOR_GITHUB_ACTIONS.bat`, Linux `./MONITOR_GITHUB_ACTIONS.sh`, macOS double-click `MONITOR_GITHUB_ACTIONS.command`, or `python actions_monitor.py` anywhere.
4. Open the address it prints (`http://127.0.0.1:<port>`). On first start it creates `actions_monitor.json` from the example.
5. Open **Settings** to set your GitHub account, the ecosystems (groups of repositories by name prefix) and anything else.

> Updating from a version before 1.5.0? [`monitor/docs/MIGRATING.md`](monitor/docs/MIGRATING.md)

## The lite edition

A second, simpler product in the same package: the page of what is running and what failed, without the sentinel. It is for people who only want to watch their runs.

|  | Complete | Lite |
|---|---|---|
| Start | `MONITOR_GITHUB_ACTIONS` (`.bat` / `.sh` / `.command`) | `MONITOR_LITE_GITHUB_ACTIONS` (same three) |
| Port | 8765 | 8766 |
| Tabs | Now, Sentinel, Charts, Repositories, History, Settings | Now, Charts, Repositories, History, a short Settings |
| Header | all the tiles, readiness, signing | running, queued, failures and successes of 24 h, compute minutes, issues, red on main, repositories, allowance, connection |
| Sentinel (alerts, releases, signing queue, readiness, linter) | yes | no: it is not even imported |
| Analytics, notifications, webhook, AI, Prometheus / Grafana outputs | yes, off until you switch them on | no: those paths answer 404 |
| Configuration | `actions_monitor.json` | `actions_monitor_lite.json` (created on the first start; the sentinel is off in it) |
| State files | `etag_cache.json`, `analytics_history.json`... | the same names with the suffix `_lite` |

[`monitor/docs/LITE.md`](monitor/docs/LITE.md)

## Settings

Everything lives in `actions_monitor.json` (created from `actions_monitor.example.json`). The **Settings** tab edits it safely; tokens and secrets are never shown or saved. Ecosystems, build targets and batch profiles are separate files you point to (`ecosystems_file`, `targets_file`, `profiles_file`); neutral `*.example.json` templates are included. Full reference: [`monitor/docs/SETTINGS.md`](monitor/docs/SETTINGS.md).

## Outputs for Grafana and dashboards

All off by default, local only (`127.0.0.1`) and with no extra token. When enabled in Settings you get `/metrics` (Prometheus format), `/api/outputs/grafana.json` and `/api/outputs/dashboard.json`, plus an importable Grafana dashboard in [`monitor/docs/grafana`](monitor/docs/grafana). Details: [`monitor/docs/OUTPUTS.md`](monitor/docs/OUTPUTS.md). The format of `ci_red.json`: [`monitor/docs/CI_RED_SCHEMA.md`](monitor/docs/CI_RED_SCHEMA.md).

## Security

- It listens on `127.0.0.1` only and refuses requests whose `Host` or `Origin` is not local. Never bind it to `0.0.0.0`: it has no login.
- It stores no token: it asks your own `gh` (unless you switch on the optional token of the monitor in Settings > Advanced).
- It writes nothing to GitHub on its own. Only `dispatch --go`, `dispatch --real` and `finalize --execute` write, and only when you run them.
- **Analytics**: p50 / p95 of the duration, of the queue time and of each step of every workflow, flaky workflows (failed, then passed on the same commit) and workflows that got slower; exported to Prometheus and Grafana.
- **Saves quota and survives a cut**: conditional reads (a 304 costs nothing) and a last-picture mode with an offline banner that resumes by itself.
- **Incoming webhook and notifications**: signed events update a repository in real time; optional messages to Telegram, Discord, Slack, Matrix, MQTT or a local address (never a write to GitHub).
- **Workflow linter and terminal view**: `lint_workflows.py` checks `.github/workflows` before you push; `tui.py` (optional, with `rich`) shows a live grid in the console.
- **AI assistant (off by default)**: summaries, triage and explanations with Ollama, an OpenAI-compatible service, Anthropic or `gh copilot`; commands only from a closed list, run only after you confirm each one.
- The settings page writes a fixed list of keys, validated, after saving a backup copy.

## Tests

They need no network and no extra package:

```
python -m unittest discover -s monitor/tests
```

## Repository structure

<p align="center"><img src="images/repository-structure.svg" alt="Repository structure" width="100%"></p>

```
TOOLS-GITHUB-ACTIONS-MONITOR/
├── monitor/                                  the program
├── docs/                                     architecture, screenshots, roadmap
├── tools/                                    pictures, guides and demo
├── deploy/                                   container example
├── images/                                   banner and pictures
├── .github/                                  CI and issue forms
├── CHANGELOG.md                              changes per version
├── LICENSE NOTICE AUTHORS                    licences and author
├── CONTRIBUTING.md SECURITY.md               how to help, report
├── SUPPORT.md CODE_OF_CONDUCT.md             support and conduct
└── monitor/
    ├── actions_monitor.py                    local server
    ├── actions_monitor.html                  the web page
    ├── MONITOR_LITE_GITHUB_ACTIONS.*         the lite edition (no sentinel)
    ├── sentinel_local.py                     alerts and report
    ├── sentinel_collab.py  alert_center.py   issues sentinel, alerts
    ├── surface.py readiness.py               repo checks, readiness
    ├── settings_api.py outputs.py            settings tabs, metrics
    ├── signstate.py sigverify.py             signing state and check
    ├── monitor_cli.py                        command line as a client
    ├── read_report.py                        report from the terminal
    ├── gha_dispatch_all.py                   batch builds
    ├── events.py report_history.py           events and history
    ├── ci_red.py export_status.py            files others read
    ├── etagcache.py resilience.py            conditional reads, lost connection
    ├── analytics.py lint_workflows.py        durations, flaky, workflow linter
    ├── notifiers.py ai_actions.py            notifications, AI closed list
    ├── tui.py migrate_state.py               terminal view, state migration
    ├── about.py  helpdocs.py                 About and Help panels
    ├── quota.py  quotas.json                 plan, minutes and quotas
    ├── modes.py  updatecheck.py              working modes, update notice
    ├── doctor.py  demo_mode.py               --doctor and --demo
    ├── discovery.py  banner.py               discovery, edition banner
    ├── tui_textual.py                        interactive terminal
    ├── i18n.py locales/                      eight languages
    ├── toolconfig.py workspace.py            settings and clones
    ├── tests/                                offline tests
    └── docs/                                 guides, schemas, Grafana
```

## Documentation

- [`monitor/docs/SETTINGS.md`](monitor/docs/SETTINGS.md): every setting
- [`monitor/docs/OUTPUTS.md`](monitor/docs/OUTPUTS.md): metrics, Grafana and exports
- [`monitor/docs/CI_RED_SCHEMA.md`](monitor/docs/CI_RED_SCHEMA.md): the format of ci_red.json
- [`monitor/docs/CI_RED_BRIDGE.md`](monitor/docs/CI_RED_BRIDGE.md): carrying ci_red.json to a dashboard
- [`monitor/docs/WEBHOOK.md`](monitor/docs/WEBHOOK.md): the incoming webhook
- [`monitor/docs/LITE.md`](monitor/docs/LITE.md): The lite edition
- [`monitor/docs/NOTIFICATIONS.md`](monitor/docs/NOTIFICATIONS.md): notifications and the adapter contract
- [`monitor/docs/AI.md`](monitor/docs/AI.md): the AI assistant: providers, safety and actions
- [`monitor/docs/ANALYTICS.md`](monitor/docs/ANALYTICS.md): analytics, conditional reads and the lost connection
- [`monitor/docs/CONSOLE_TOOLS.md`](monitor/docs/CONSOLE_TOOLS.md): the workflow linter and the terminal view
- [`monitor/docs/DEPLOYMENT.md`](monitor/docs/DEPLOYMENT.md): running it as a service, behind a proxy, permissions
- [`monitor/QUICKSTART_en.txt`](monitor/QUICKSTART_en.txt): first steps, in eight languages
- [`monitor/docs/FIRST_STEPS.md`](monitor/docs/FIRST_STEPS.md): your first five minutes
- [`monitor/docs/SENTINEL.md`](monitor/docs/SENTINEL.md): the sentinel and its checks A1-A13
- [`monitor/docs/COLLAB.md`](monitor/docs/COLLAB.md): the Collab sentinel, the Alerts tab and the silences
- [`monitor/docs/CLI.md`](monitor/docs/CLI.md): the command line as a client of the monitor
- [`monitor/docs/ACCOUNTS.md`](monitor/docs/ACCOUNTS.md): several accounts, one process each
- [`monitor/docs/QUOTAS.md`](monitor/docs/QUOTAS.md): quotas and plans of GitHub
- [`monitor/docs/MODES.md`](monitor/docs/MODES.md): working modes: normal, fast and turbo
- [`monitor/docs/AI_CONNECTION.md`](monitor/docs/AI_CONNECTION.md): Connect an AI tool: everything the monitor says, as signals, in the brief, the endpoint, the MCP tools and the hook
- [`monitor/docs/QUOTA.md`](monitor/docs/QUOTA.md): More quota, less spending: Low mode, the central panel, a GitHub App and how to share the allowance

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Report bugs and ideas with the issue forms; report security problems as described in [SECURITY.md](SECURITY.md).

## Author

Written by **JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## License

The code is GPL-3.0-or-later; the documentation is CC BY-SA 4.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
