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
| **Needs** | Python 3.11+ and the GitHub CLI (`gh auth login`); nothing else |
| **Opens** | a page on `127.0.0.1` only, in eight languages |
| **Writes to GitHub** | never by itself: only batch commands you run with an explicit `--go` |
| **Exports** | `ci_red.json`, Prometheus metrics and JSON for Grafana (all off until you switch them on) |

## Screenshots

<p align="center"><img src="docs/screenshots/monitor_now_dark.png" alt="Now" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_sentinel_dark.png" alt="Sentinel" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_charts_dark.png" alt="Charts" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_settings_light.png" alt="Settings" width="92%"></p>

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

## Settings

Everything lives in `actions_monitor.json` (created from `actions_monitor.example.json`). The **Settings** tab edits it safely; tokens and secrets are never shown or saved. Ecosystems, build targets and batch profiles are separate files you point to (`ecosystems_file`, `targets_file`, `profiles_file`); neutral `*.example.json` templates are included. Full reference: [`monitor/docs/SETTINGS.md`](monitor/docs/SETTINGS.md).

## Outputs for Grafana and dashboards

All off by default, local only (`127.0.0.1`) and with no extra token. When enabled in Settings you get `/metrics` (Prometheus format), `/api/outputs/grafana.json` and `/api/outputs/dashboard.json`, plus an importable Grafana dashboard in [`monitor/docs/grafana`](monitor/docs/grafana). Details: [`monitor/docs/OUTPUTS.md`](monitor/docs/OUTPUTS.md). The format of `ci_red.json`: [`monitor/docs/CI_RED_SCHEMA.md`](monitor/docs/CI_RED_SCHEMA.md).

## Security

- It listens on `127.0.0.1` only and refuses requests whose `Host` or `Origin` is not local. Never bind it to `0.0.0.0`: it has no login.
- It stores no token: it asks your own `gh`.
- It writes nothing to GitHub on its own. Only `dispatch --go`, `dispatch --real` and `finalize --execute` write, and only when you run them.
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
├── monitor/                          the program
├── docs/                             architecture, screenshots
├── tools/                            picture generators
├── images/                           banner and pictures
├── .github/                          CI and issue forms
├── CHANGELOG.md                      changes per version
├── LICENSE NOTICE AUTHORS            licences and author
├── CONTRIBUTING.md SECURITY.md       how to help, report
├── SUPPORT.md CODE_OF_CONDUCT.md     support and conduct
└── monitor/
    ├── actions_monitor.py            local server
    ├── actions_monitor.html          the web page
    ├── sentinel_local.py             alerts and report
    ├── surface.py readiness.py       repo checks, readiness
    ├── settings_api.py outputs.py    settings, metrics, JSON
    ├── signstate.py sigverify.py     signing state and check
    ├── read_report.py                report from the terminal
    ├── gha_dispatch_all.py           batch builds
    ├── events.py report_history.py   events and history
    ├── ci_red.py export_status.py    files others read
    ├── i18n.py locales/              eight languages
    ├── toolconfig.py workspace.py    settings and clones
    ├── tests/                        offline tests
    └── docs/                         settings, outputs, Grafana
```

## Documentation

- [`monitor/docs/SETTINGS.md`](monitor/docs/SETTINGS.md): every setting
- [`monitor/docs/OUTPUTS.md`](monitor/docs/OUTPUTS.md): metrics, Grafana and exports
- [`monitor/docs/CI_RED_SCHEMA.md`](monitor/docs/CI_RED_SCHEMA.md): the format of ci_red.json
- [`monitor/docs/CI_RED_BRIDGE.md`](monitor/docs/CI_RED_BRIDGE.md): carrying ci_red.json to a dashboard
- [`monitor/QUICKSTART_en.txt`](monitor/QUICKSTART_en.txt): first steps, in eight languages

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Report bugs and ideas with the issue forms; report security problems as described in [SECURITY.md](SECURITY.md).

## Author

Written by **JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## License

The code is GPL-3.0-or-later; the documentation is CC BY-SA 4.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
