Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

GITHUB ACTIONS MONITOR + SENTINEL (version 1.7.3)
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

HISTORY OF CHANGES
  Every version, newest first, is in CHANGELOG.md (in eight languages in docs/CHANGELOG_*.md, and in the page: Help > Changelog).

HELP, ABOUT AND CHECKS (1.6.4)
-----------------------------
The page has an Help button (round ?) and an About button (i); in the console use --help-topics, --help-search, --about and --doctor; --demo shows the page with invented data. The lite edition starts with its own banner and window title (LITE, port 8766, no sentinel); the complete edition says COMPLETE, port 8765, sentinel on. A notice of a newer version can be switched off (Settings > Basic).
