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
| **Version** | **1.6.0** · [all releases](https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases) |
| **Needs** | Python 3.11+ and the GitHub CLI (`gh auth login`); nothing else (the terminal view uses the optional package `rich`) |
| **Opens** | a page on `127.0.0.1` only, in eight languages |
| **Writes to GitHub** | never by itself: only batch commands you run with an explicit `--go` |
| **Exports** | `ci_red.json`, Prometheus metrics and JSON for Grafana (all off until you switch them on) |

## Screenshots

### The page

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_now_light.png"><img src="docs/screenshots/web_now_dark.png" alt="Now" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_light.png"><img src="docs/screenshots/web_sentinel_dark.png" alt="Sentinel" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_queue_light.png"><img src="docs/screenshots/web_sentinel_queue_dark.png" alt="Signing queue (most urgent first)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_analytics_light.png"><img src="docs/screenshots/web_sentinel_analytics_dark.png" alt="A12 · Analytics: durations, queue time, steps and flaky workflows" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_charts_light.png"><img src="docs/screenshots/web_charts_dark.png" alt="Charts" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_repositories_light.png"><img src="docs/screenshots/web_repositories_dark.png" alt="Repositories" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_history_light.png"><img src="docs/screenshots/web_history_dark.png" alt="History" width="92%"></picture></p>

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

</details>

<details><summary><b>Console tools</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_read_report_light.png"><img src="docs/screenshots/console_read_report_dark.png" alt="read_report.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_migrate_state_light.png"><img src="docs/screenshots/console_migrate_state_dark.png" alt="migrate_state.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_plan_light.png"><img src="docs/screenshots/console_plan_dark.png" alt="gha_dispatch_all.py plan" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_lint_light.png"><img src="docs/screenshots/console_lint_dark.png" alt="lint_workflows.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_tui_light.png"><img src="docs/screenshots/console_tui_dark.png" alt="tui.py" width="92%"></picture></p>

</details>

Each picture follows the light or dark theme of your GitHub page.

*Demo data: the repositories and names in the pictures are invented.*

## What it does

- **Red or not, by one rule**: the last finished run of each workflow on the default branch. Cancelled and skipped runs never hide an earlier failure.
- **Sentinel**: security alerts, repository hygiene, stale pull requests, releases that are ready to cut, builds waiting to be signed, and a plain-language report.
- **Settings page**: change paths, intervals, quotas and switches from the browser; only a fixed list of keys, validated, with a backup before every save.
- **Charts and history**: compute minutes, failures and successes with animated bars and a daily history (it respects reduced motion).
- **Eight languages** (en, es, de, fr, it, ja, zh, pt) with English as the base; switch in Settings.
- **Outputs for dashboards**: `ci_red.json`, a Prometheus endpoint and a JSON source for Grafana, with an importable Grafana dashboard.
- **Batch tools**: plan and dispatch many builds at once; nothing is fired without `--go`.

## Architecture

<p align="center"><img src="images/architecture.svg" alt="Architecture" width="100%"></p>

## Quick start

1. Install Python 3.11 or newer and the [GitHub CLI](https://cli.github.com/), then run `gh auth login`.
2. Download this repository (or the zip of the latest release) and open the `monitor` folder.
3. Start it: Windows `MONITOR_GITHUB_ACTIONS.bat`, Linux `./MONITOR_GITHUB_ACTIONS.sh`, macOS double-click `MONITOR_GITHUB_ACTIONS.command`, or `python actions_monitor.py` anywhere.
4. Open the address it prints (`http://127.0.0.1:<port>`). On first start it creates `actions_monitor.json` from the example.
5. Open **Settings** to set your GitHub account, the ecosystems (groups of repositories by name prefix) and anything else.

> Updating from a version before 1.5.0? [`monitor/docs/MIGRATING.md`](monitor/docs/MIGRATING.md)

## Settings

Everything lives in `actions_monitor.json` (created from `actions_monitor.example.json`). The **Settings** tab edits it safely; tokens and secrets are never shown or saved. Ecosystems, build targets and batch profiles are separate files you point to (`ecosystems_file`, `targets_file`, `profiles_file`); neutral `*.example.json` templates are included. Full reference: [`monitor/docs/SETTINGS.md`](monitor/docs/SETTINGS.md).

## Outputs for Grafana and dashboards

All off by default, local only (`127.0.0.1`) and with no extra token. When enabled in Settings you get `/metrics` (Prometheus format), `/api/outputs/grafana.json` and `/api/outputs/dashboard.json`, plus an importable Grafana dashboard in [`monitor/docs/grafana`](monitor/docs/grafana). Details: [`monitor/docs/OUTPUTS.md`](monitor/docs/OUTPUTS.md). The format of `ci_red.json`: [`monitor/docs/CI_RED_SCHEMA.md`](monitor/docs/CI_RED_SCHEMA.md).

## Security

- It listens on `127.0.0.1` only and refuses requests whose `Host` or `Origin` is not local. Never bind it to `0.0.0.0`: it has no login.
- It stores no token: it asks your own `gh`.
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
├── monitor/                             the program
├── docs/                                architecture, screenshots, roadmap
├── tools/                               pictures, guides and demo
├── images/                              banner and pictures
├── .github/                             CI and issue forms
├── CHANGELOG.md                         changes per version
├── LICENSE NOTICE AUTHORS               licences and author
├── CONTRIBUTING.md SECURITY.md          how to help, report
├── SUPPORT.md CODE_OF_CONDUCT.md        support and conduct
└── monitor/
    ├── actions_monitor.py               local server
    ├── actions_monitor.html             the web page
    ├── sentinel_local.py                alerts and report
    ├── surface.py readiness.py          repo checks, readiness
    ├── settings_api.py outputs.py       settings tabs, metrics
    ├── signstate.py sigverify.py        signing state and check
    ├── read_report.py                   report from the terminal
    ├── gha_dispatch_all.py              batch builds
    ├── events.py report_history.py      events and history
    ├── ci_red.py export_status.py       files others read
    ├── etagcache.py resilience.py       conditional reads, lost connection
    ├── analytics.py lint_workflows.py   durations, flaky, workflow linter
    ├── notifiers.py ai_actions.py       notifications, AI closed list
    ├── tui.py migrate_state.py          terminal view, state migration
    ├── i18n.py locales/                 eight languages
    ├── toolconfig.py workspace.py       settings and clones
    ├── tests/                           offline tests
    └── docs/                            guides, schemas, Grafana
```

## Documentation

- [`monitor/docs/SETTINGS.md`](monitor/docs/SETTINGS.md): every setting
- [`monitor/docs/OUTPUTS.md`](monitor/docs/OUTPUTS.md): metrics, Grafana and exports
- [`monitor/docs/CI_RED_SCHEMA.md`](monitor/docs/CI_RED_SCHEMA.md): the format of ci_red.json
- [`monitor/docs/CI_RED_BRIDGE.md`](monitor/docs/CI_RED_BRIDGE.md): carrying ci_red.json to a dashboard
- [`monitor/docs/WEBHOOK.md`](monitor/docs/WEBHOOK.md): the incoming webhook
- [`monitor/docs/NOTIFICATIONS.md`](monitor/docs/NOTIFICATIONS.md): notifications and the adapter contract
- [`monitor/docs/AI.md`](monitor/docs/AI.md): the AI assistant: providers, safety and actions
- [`monitor/docs/ANALYTICS.md`](monitor/docs/ANALYTICS.md): analytics, conditional reads and the lost connection
- [`monitor/docs/CONSOLE_TOOLS.md`](monitor/docs/CONSOLE_TOOLS.md): the workflow linter and the terminal view
- [`monitor/docs/DEPLOYMENT.md`](monitor/docs/DEPLOYMENT.md): running it as a service, behind a proxy, permissions
- [`monitor/QUICKSTART_en.txt`](monitor/QUICKSTART_en.txt): first steps, in eight languages

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Report bugs and ideas with the issue forms; report security problems as described in [SECURITY.md](SECURITY.md).

## Author

Written by **JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## License

The code is GPL-3.0-or-later; the documentation is CC BY-SA 4.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
