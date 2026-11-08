<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Changelog

Changes of the repository as a whole. The program has its own, more detailed history in [`monitor/CHANGELOG.md`](monitor/CHANGELOG.md).

## [Unreleased]

## [1.6.2]

- The example catalogue has a catch-all group so nothing is left out by default, the lite edition inherits the account and the filters of the complete one on its first start, the page warns when the ecosystem filter hides repositories, repositories that no group claims are shown as Unclassified, a webhook event makes the repository hot and a damaged cache entry is only a miss.

## [1.6.1]

- The lite edition (its own launchers, configuration, state files and port, no sentinel), the `act` command in the repository panel, a container example built by the CI and an updated roadmap.

## [1.6.0]

- Conditional reads, a mode for lost connections, analytics (durations, queue time, steps, flaky workflows), real-time webhook events, a workflow linter, optional notifications (chat, MQTT, local HTTP), new AI providers (`anthropic`, `copilot`) with a closed list of actions that run only after a confirmation, a terminal view, a health endpoint and Enterprise Server support.
- Header figures as tiles with live countdown and last known values; the workflow linter tells fillers from real secrets and can be silenced by a comment or by a list.
- New guides in eight languages, published JSON schemas, a roadmap, and every screenshot redone in light and dark, console tools included.

## [1.5.2]

- The Settings tab now has sub-tabs, blocks with a main switch, units, ranges, help lines, a search box and every setting of the configuration file (the A10 checks, health weights, pin sources, minute ceilings and more).
- Signing queue filter by trust (`verified` / `unknown` / `failed`), readiness chips in the header, grouped issue-closing suggestions in the report, a minimal Grafana board and a documented, tested contract for the profile dashboard.
- New guide for the incoming webhook; the settings guides are generated from the schema.

## [1.5.1]

- External AI settings for the sentinel in the Settings tab (only the name of the variable that holds the key), `migrate_state.py` with a one-page guide in eight languages, `--init-catalog`, and the version of the monitor shown in every README.

## [1.5.0]

First public release of the monitor as its own repository.

- **Settings page**: change paths, intervals, quotas and switches from the browser, with a fixed list of validated keys and a backup before every save; tokens and secrets are never shown or saved.
- **Buttons and icons**: 3D buttons that light up on hover and sink when pressed, and inline icons with accessible names in eight languages.
- **Look of the page**: tokens for light and dark themes, cards, charts with relief and animated bars that respect reduced motion.
- **Outputs for dashboards** (off by default, local only): a Prometheus endpoint, a JSON source for Grafana and an importable Grafana dashboard, next to the existing `ci_red.json`.
- **English as the base language**: the language of the system no longer decides; choose another one in Settings.
- **English names for every file and folder**, with a table of the old and new names in `monitor/CHANGELOG.md`.
- **Neutral package**: only `*.example.json` templates are shipped for ecosystems, build targets and batch profiles; the tests use their own fixtures.
- Author and licence shown in the page footer and by every command line tool.
- Documentation and screenshots in eight languages.
