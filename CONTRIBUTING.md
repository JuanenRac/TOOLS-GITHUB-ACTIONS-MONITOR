# Contributing to GitHub Actions Monitor

## Technology stack
- **Language**: Python 3.11 or newer, the core needs no packages (the terminal view, `tui.py`, uses Rich, which is optional; the tests skip what needs it when it is missing).
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

## Refreshing a status dashboard after each release

`.github/workflows/dashboard-dispatch.yml` runs after the `CI` workflow finishes green on `main` (push events only). If the maintainer defines the optional repository secret `ECOSYSTEM_DASHBOARD_DISPATCH_TOKEN`, it asks a dashboard repository to refresh its table of versions; without the secret it exits quietly, has no permissions and never changes or delays the CI. The version in `electro-hobby-3d.project.json` must equal `tool_version.py` at every release; a test checks it.

- Help checklist: the Settings help (`cfg.h.<key>`) of every new setting, the help of the tab that changed, the guides in `monitor/docs/`, the eight languages, the help index (`python tools/make_help_index.py`) and the changelog.
