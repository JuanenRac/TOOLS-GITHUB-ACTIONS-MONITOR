<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Changelog

Changes of the repository as a whole. The program has its own, more detailed history in [`monitor/CHANGELOG.md`](monitor/CHANGELOG.md).

## [Unreleased]

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
