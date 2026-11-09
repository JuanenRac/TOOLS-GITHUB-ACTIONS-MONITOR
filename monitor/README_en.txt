Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

GITHUB ACTIONS MONITOR + SENTINEL (version 1.7.0)
=================================================
WHICH ONE TO START? (a new user decides in two minutes)
  COMPLETE  MONITOR_GITHUB_ACTIONS.*       the page with the sentinel (port 8765): alerts, signing queue, analytics. Start here if you own several repositories.
  LITE      MONITOR_LITE_GITHUB_ACTIONS.*  the same page without the sentinel (port 8766): what is red, stuck or running. Lighter; can run next to the complete one.
  BATCH     BATCH_GITHUB_ACTIONS.*         only if you sign and publish your own builds.
  TERMINAL  python tui_textual.py (add --lite for the lite edition)   the interactive terminal application; tui.py --once prints one screen.
  CHECK     python actions_monitor.py --doctor (--json for scripts)   tells what is missing and the exact command that fixes it.
  TRY IT    python actions_monitor.py --demo   the page with invented data: no gh, no login, nothing of yours is touched.

Requirements: Python 3.11+ and the GitHub CLI (`gh`) logged in (gh auth login). Nothing else: the core needs no package (the terminal view, tui.py, uses the optional package rich).
Quick steps for a first use: QUICKSTART_en.txt.

START      Windows: MONITOR_GITHUB_ACTIONS.bat | Linux: ./MONITOR_GITHUB_ACTIONS.sh | macOS: double-click MONITOR_GITHUB_ACTIONS.command
           (opens http://127.0.0.1:<port>, local only). On any system you can also run:  python3 actions_monitor.py  (Windows: py -3 actions_monitor.py)
BATCHES    BATCH_GITHUB_ACTIONS.bat / .sh / .command  (gha_dispatch_all.py: plan, dispatch, status, finalize, hygiene). Optional, for people who sign their builds locally.
WHAT IT NEVER DOES   It listens only on 127.0.0.1 unless you switch on the network mode (Settings > Advanced: a private address, an access token for every request, a warning in the page). It stores no token (it asks `gh`) unless you switch on the optional token kept in the secure store of the system. On its own it writes nothing to GitHub: only the batch commands `dispatch --go`, `dispatch --real` and `finalize --execute` write to GitHub (fire workflows, create the unsigned draft, publish), and only when you run them.
           It does NOT sign and does NOT publish anything by itself: signing and publishing are commands that YOU run, and the monitor only shows them as text.
           No AI is in the critical path; the optional AI explainer is off by default.

LANGUAGE   8 languages: en, es, de, fr, it, ja, zh, pt (European Portuguese). It starts in ENGLISH: the language of your system does not decide. Choose another one in the SETTINGS tab of the page
           (gear icon; the browser remembers it), or set "language" in actions_monitor.json, or the environment variable MONITOR_LANG, or --lang CODE in the command line tools (it beats the rest).
           Lines that scripts read (SKIP, DISPATCHED, READY, FAILED, Summary:, BUILD ONLY...) are always English.
CONFIG     actions_monitor.json (created from actions_monitor.example.json on the first start). Useful keys: github_owner (empty = the account of gh),
           language, ecosystems_file, targets_file, refresh_seconds, cold_refresh_seconds, max_workers, min_rate_remaining, sentinel.*
           ecosystems_file: groups repositories by name prefix (see ecosystems.example.json; "*" = every repository). targets_file: the catalogue of builds
           for the batch tools (see targets.example.json). profiles_file (profiles.example.json): batch profiles. Keys that start with "_" in these files are metadata.
WORKSPACE  OPTIONAL: a folder with local clones of your repositories (MONITOR_ROOT, "workspace_root" in the json, or a parent folder with a .monitor-root file).
           Without it the monitor starts in REDUCED MODE and says so: only what the GitHub API gives (no local signing queue, no audit report, no CHANGELOG scan).
           With it you also get release candidates, the signing queue and the batch tools. Signing records: "signed_dir"; audit files: "audit_dir".
TESTS      py -3 -I -m unittest discover -s tests   (Linux/macOS: python3 -I -m unittest discover -s tests). They need no network.
PROBLEMS   "API rate limit": the shared quota of gh (5000/hour) is used up; wait for the reset (gh api rate_limit) and raise refresh_seconds / lower max_workers.
           The monitor stops at start if gh does not answer. A corrupt cache file is ignored; delete sentinel_cache.json to start the cache again.
           Restart the monitor after updating the package (a running process keeps the old code).

TOOLS      read_report.py [--lang CODE] [--json] [--export-status DIR] [--export-sign-queue FILE]  prints what the running monitor says (local, no GitHub quota)
           gha_dispatch_all.py [--lang CODE] plan|dispatch|status|finalize|hygiene    batch of GitHub Actions builds (nothing is compiled on your PC)
           release_notes.py REPO [--since TAG] [--out FILE]    draft of release notes from commits (a proposal; it publishes nothing)
           release_candidates.py    projects with entries in CHANGELOG [Unreleased] and an old last release (read only)
EVENTS     The Sentinel writes one JSON line per CHANGE (new red, recovered CI, stuck build, new alerts...) in events_monitor.jsonl. Each line has a stable
           `code` (it never depends on the language), `kind`, `level`, `repo`, `args` and `text` (in the configured language). `tail -F` follows it.
RED CI     One criterion: the LAST finished run of each workflow on the default branch. Red = failure, timed_out, startup_failure or action_required.
           cancelled, skipped, neutral and stale do not count.

WHAT IS NEW IN 1.5.1 (history: CHANGELOG.md)
  - SETTINGS tab: new group "External AI for the sentinel" (ai.provider none / ollama / openai-compatible, model, the address of Ollama (this computer only), an https endpoint, the NAME of the environment variable that holds the key, calls per day). The key itself is never saved. Off by default; an outside service receives data of your repositories.
  - migrate_state.py: brings the files written before 1.5.0 to the new names. `python migrate_state.py` is a dry run; `--apply` copies (the old files stay), `--move` renames. Nothing is overwritten. One page in docs/MIGRATING.md, in 8 languages.
  - First start without your own catalogue files: the monitor says it is using the example ones (console), and `--init-catalog` creates editable copies of ecosystems.json, targets.json and profiles.json.
  - Python 3.11 or newer (tested on 3.11 and 3.13, on Windows, Linux and macOS).

WHAT IS NEW IN 1.5.0 (history: CHANGELOG.md)
  - SETTINGS tab: change the values of actions_monitor.json from the page (a list of allowed keys with type and range, checked, a copy in config_backups/ before every save, never tokens or secrets; docs/SETTINGS.md).
  - Buttons with relief that light up and sink, inline SVG icons with a name and tooltip in 8 languages, the look of the status dashboard, bars and figures with life (all of it stops with prefers-reduced-motion).
  - Optional outputs, off by default, only on 127.0.0.1: /metrics (Prometheus), /api/outputs/grafana.json (Grafana JSON / Infinity), /api/outputs/dashboard.json (docs/OUTPUTS.md, example dashboard in docs/grafana/).
  - A neutral package: your ecosystems, targets and profiles live outside it (ecosystems_file, targets_file, profiles_file; tools_dir for the local signing tools); English by default; names of files and folders in English.
  UPDATING from 1.4.x: the names below changed (the old ones are still read where a file may exist; the new ones are the only ones written):
  leer_parte.py -> read_report.py          eventos.py -> events.py          parte_history.py -> report_history.py
  LOTE_GITHUB_ACTIONS.bat/.sh/.command -> BATCH_GITHUB_ACTIONS.bat/.sh/.command
  eventos_monitor.jsonl -> events_monitor.jsonl          eventos_estado.json -> events_state.json
  PARTE_CENTINELA_DIA_<day>.* -> SENTINEL_REPORT_DAY_<day>.*     PARTE_CENTINELA_<time>.txt -> SENTINEL_REPORT_<time>.txt     CANDIDATAS_RELEASE.txt -> RELEASE_CANDIDATES.txt
  <signed_dir>/lotes/lote_<time>.json -> <signed_dir>/batches/batch_<time>.json     parte_history_days -> report_history_days     monitor_y_centinela.zip -> github_actions_monitor.zip
  sentinel.audit_files: names of the A8 audit files (neutral defaults RECONCILIATION_TOTAL_*.txt, ROUNDS_MAP_2*.txt, ROUNDS_MAP_EXTRA_*.txt)
  ci_red.json and --export-status: unchanged (a contract).

WHAT IS NEW IN 1.4.2 (history: CHANGELOG.md)
  When A2 asks for the last run of a hidden workflow, a run in progress or a cancelled one no longer counts as seen (it could hide an earlier red): the Sentinel asks for the
  last completed runs of that workflow and uses the first with a real conclusion (cancelled and skipped are ignored). If there is none on the default branch, only that workflow stays inconclusive.

WHAT IS NEW IN 1.4.1 (history: CHANGELOG.md)
  A2 no longer reports a whole repository as inconclusive because its run sample is full: for each workflow of the clone that is missing from the
  sample it asks GitHub for the last run of that one workflow on the default branch (read only, same quota gate as A10, limited by
  sentinel.a2_resolve_max_calls_per_tick, answers kept sentinel.a2_resolve_ttl_seconds). Red counts as red; a workflow with no run on the branch stays
  inconclusive and the panel names it.

WHAT IS NEW IN 1.4.0 (history: CHANGELOG.md)
  A11 "Readiness" panel: release readiness per repository (CI of the default branch and its commit, version above the last release, build, signing, next step),
  ecosystem health (a score from real counts only, withheld when too few repositories have data) and dependency pins that are behind their provider
  (read from pin files of the local clones, configured in sentinel.readiness.pins.sources). Read only; nothing is estimated.

WHAT IS NEW IN 1.3.0 (history: CHANGELOG.md)
  8 languages in the page, the command line, the events and the reports; language selector; ecosystems, targets and GitHub account as data (github_owner,
  ecosystems_file, targets_file); optional workspace with an honest reduced mode; authorship and GPL-3.0-or-later in every file; LICENSE, NOTICE, AUTHORS;
  README and QUICKSTART in 8 languages.
LICENCE    GPL-3.0-or-later (see LICENSE and NOTICE). Copyright (C) 2026 JuanenRac (Electro Hobby 3D).

HELP, ABOUT AND CHECKS (1.6.4)
-----------------------------
The page has an Help button (round ?) and an About button (i); in the console use --help-topics, --help-search, --about and --doctor; --demo shows the page with invented data. The lite edition starts with its own banner and window title (LITE, port 8766, no sentinel); the complete edition says COMPLETE, port 8765, sentinel on. A notice of a newer version can be switched off (Settings > Basic).

WHAT IS NEW IN 1.7.0 (several accounts; history: CHANGELOG.md)
  The complete edition can watch several GitHub accounts: one folder accounts/<id>/ per account and one monitor per account under a supervisor, so a failure of one never touches another.
  --accounts, --account <id>, --migrate-accounts [--apply]; a switcher and the page All accounts; ?view= and ?chrome=0; the Live view with the state of the webhook; one /api/webhook for all.
  Guide: docs/ACCOUNTS.md. Without an accounts/ folder nothing changes. The lite edition has one account and none of this.

WHAT IS NEW IN 1.6.8 (proxy checked for real; history: CHANGELOG.md)
  The HTTPS proxy of 1.6.7 is checked against a real proxy on port 443 (tools/manual_check_live.py proxy in the repository) and by tests that run the whole chain. The changelog is
  translated back to 1.6.3 (Help > Changelog). No setting changes.

WHAT IS NEW IN 1.6.7 (HTTPS proxy on the default port; history: CHANGELOG.md)
  New setting listen.proxy_public_host (empty by default): the public name of an HTTPS proxy on port 443 that forwards Host and Origin without a port is accepted as it is, only under
  HTTPS, and it can only be changed from the computer itself. The changelog is translated for 1.6.7, 1.6.6 and 1.6.5 (Help > Changelog).

WHAT IS NEW IN 1.6.6 (corrections of the network mode and of act; history: CHANGELOG.md)
  Network mode over HTTPS works from the page (the origin follows the scheme of the session); every setting marked secure can only be changed from the computer itself; POST /api/access opens the
  session without the token in the address; a red bar in Settings when it listens on every interface; a counter of swallowed failures in --doctor and About. act: Stop frees the run and
  the pipe is closed. The history of changes is translated into eight languages (Help > Changelog).

WHAT IS NEW IN 1.6.5 (integrity and security; history: CHANGELOG.md)
  Batches: green CI means the required workflow passed (dispatch.required_ci), a failed git fetch stops the dispatch, targets.json cannot name a tool outside the tools folder or
  change dry_run/ref, and finalize offers only runs whose batch recorded the commit check (finalize --accept-legacy for old batches). act stays inside the workspace and Stop ends the
  whole tree. Network mode: optional HTTPS, lockout after wrong tokens, IPv4 only. Webhook: no replays. Notifications: max_per_hour counts messages. --doctor warns about dangerous combinations.
