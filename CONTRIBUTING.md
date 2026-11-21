# Contributing to GitHub Actions Monitor

## Technology stack
- **Language**: Python 3.11 or newer, the core needs no packages (the terminal view, `bin/tui.py`, uses Rich, which is optional; the tests skip what needs it when it is missing).
- **Interface**: a local web page (`monitor/assets/static/actions_monitor.html`) served on `127.0.0.1`, plus command line tools.
- **Data source**: the official GitHub command line client `gh` (read-only calls by default).

## Guidelines
1. **Tests first**: `python -m unittest discover -s monitor/tests` must pass before a pull request. Offline: the tests never call GitHub. To try the real services by hand, use `python tools/manual_check_live.py`.
2. **Eight languages**: every text a user can read lives in `monitor/assets/locales/<lang>.json` for en, es, de, fr, it, ja, zh and pt (European Portuguese). A new key goes into all eight files; the tests check that they have the same keys.
3. **No secrets**: by default the monitor stores no token (it asks `gh`); the one optional token lives only in the secure store of the system (`secretstore.py`). Do not add code that reads, prints, logs or writes credentials anywhere else, and never commit a real `actions_monitor.json`.
4. **Safe by default**: anything that writes to GitHub, runs a program, opens a network port or sends data out is off by default, has its own switch in Settings > Advanced, asks for a confirmation of its own and listens on `127.0.0.1` unless the network mode is on. Such a feature comes with tests that prove it refuses without the switch, without the confirmation and without the token, and that nothing leaks to a log.
5. **Small steps**: one change per pull request, with the matching line in `CHANGELOG.md`.
6. **Pictures**: edit `docs/architecture.json` or `docs/structure.json` and run `python tools/make_architecture.py` / `python tools/make_structure.py`; never edit the SVG by hand.
7. **Changelog in eight languages**: every new entry of `monitor/CHANGELOG.md` gets its translation in `monitor/docs/CHANGELOG_<spa|deu|fra|ita|jpn|zho|por>.md` (same versions and sections; an entry not yet translated keeps the English text under a translated notice). `python tools/make_help_index.py --check` and the release gate fail when a version is missing in a translation.
8. **Every version reviews the whole help**: before a release (in its release pull request) read EVERY help topic - the README of the repository and its translations (At a glance, What it does, Project status, Tests, Repository structure, Documentation, Security), every guide of `monitor/docs/`, the quickstarts and the READMEs of the package - and fix any figure, version, command, path, picture or list of features that went stale, in the eight languages. The generators and the tests of the help (`tools/make_glance.py`, `tools/make_help_index.py`, `tools/make_screenshots.py`, `monitor/tests/test_190_help_current.py`) catch only part of it.

## Refreshing a status dashboard after each release

`.github/workflows/dashboard-dispatch.yml` runs after the `CI` workflow finishes green on `main` (push events only). If the maintainer defines the optional repository secret `ECOSYSTEM_DASHBOARD_DISPATCH_TOKEN`, it asks a dashboard repository to refresh its table of versions; without the secret it exits quietly, has no permissions and never changes or delays the CI. The version in `electro-hobby-3d.project.json` must equal `tool_version.py` at every release; a test checks it.

- Help checklist: the Settings help (`cfg.h.<key>`) of every new setting, the help of the tab that changed, the guides in `monitor/docs/`, the eight languages, the help index (`python tools/make_help_index.py`) and the changelog.

## Checks of the CI that guard the process

- **Tests with the network cut**: `sh tools/run_offline_tests.sh discover -s monitor/tests` runs the whole suite in a network namespace that has only the loopback. A test that needs the internet fails there.
- **Audit of dependencies**: `python tools/audit_dependencies.py` runs `pip-audit` on the packages the CI installs. A suppression in `.github/audit-suppressions.json` needs `id`, `reason` and `expires` (at most 180 days away); an expired one fails, and so does a dead one (the vulnerability is no longer found).
- **Smoke of external sources**: the workflow `sources-smoke.yml` (weekly) runs `tools/smoke_sources.py` against the real status page, the advisories, the description of the REST API and the last release, and fails when one changed its format.
- **Limits**: `tools/limits_check.py` runs the monitor with an account of 120 workflows in a container of one processor and 512 MB.
- **Release order**: create the release of GitHub as a DRAFT and push the tag `vX.Y.Z`; `release-image.yml` builds and publishes the image and, only when it answers by its tag for both platforms, publishes the draft. The tool that publishes it creates the release as a DRAFT, uploads `github_actions_monitor.zip`, `SHA256SUMS` and `monitor_updater.py`, checks that all are there and only then publishes (immutable releases accept no file afterwards); with the image first, it pushes the tag and `release-image.yml` publishes the draft.
