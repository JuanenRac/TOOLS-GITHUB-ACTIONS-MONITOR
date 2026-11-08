# Contributing to GitHub Actions Monitor

## Technology stack
- **Language**: Python 3.11 or newer, the core needs no packages (the terminal view, `tui.py`, uses Rich, which is optional; the tests skip what needs it when it is missing).
- **Interface**: a local web page (`monitor/actions_monitor.html`) served on `127.0.0.1`, plus command line tools.
- **Data source**: the official GitHub command line client `gh` (read-only calls by default).

## Guidelines
1. **Tests first**: `python -m unittest discover -s monitor/tests` must pass before a pull request. Offline: the tests never call GitHub.
2. **Eight languages**: every text a user can read lives in `monitor/locales/<lang>.json` for en, es, de, fr, it, ja, zh and pt (European Portuguese). A new key goes into all eight files; the tests check that they have the same keys.
3. **No secrets**: the monitor never stores a token. Do not add code that reads, prints or writes credentials, and never commit a real `actions_monitor.json`.
4. **Safe by default**: anything that writes to GitHub, opens a network port or sends data out is off by default and listens on `127.0.0.1` only.
5. **Small steps**: one change per pull request, with the matching line in `CHANGELOG.md`.
6. **Pictures**: edit `docs/architecture.json` or `docs/structure.json` and run `python tools/make_architecture.py` / `python tools/make_structure.py`; never edit the SVG by hand.
