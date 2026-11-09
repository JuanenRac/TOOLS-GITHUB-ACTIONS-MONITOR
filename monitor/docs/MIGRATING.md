<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Updating from a version before 1.5.0

**English** · [Español](MIGRATING_spa.md) · [Français](MIGRATING_fra.md) · [Italiano](MIGRATING_ita.md) · [Deutsch](MIGRATING_deu.md) · [简体中文](MIGRATING_zho.md) · [日本語](MIGRATING_jpn.md) · [Português](MIGRATING_por.md)

Version 1.5.0 gave English names to files, folders, scripts and one setting. Nothing is lost: the monitor still READS the old names, so you can update first and tidy up afterwards.

## Steps

1. Stop the monitor and unzip the new version over the old folder (keep your `actions_monitor.json`).
2. See what would change: `python migrate_state.py` (a dry run, it changes nothing).
3. Do it: `python migrate_state.py --apply` copies the old files to the new names and keeps the old ones; add `--move` to rename them instead. Nothing that already exists is overwritten, and the setting `parte_history_days` becomes `report_history_days` after saving a copy of `actions_monitor.json`.
4. Start the monitor with `MONITOR_GITHUB_ACTIONS` (the same launcher as before) and use `BATCH_GITHUB_ACTIONS` for the batch tools.
5. Delete the old launchers you may still have: `LOTE_GITHUB_ACTIONS.bat`, `.sh` and `.command`.

## Old and new names

| Before 1.5.0 | From 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py`, `parte_history.py` | `events.py`, `report_history.py` |
| `LOTE_GITHUB_ACTIONS.*` | `BATCH_GITHUB_ACTIONS.*` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` |
| `PARTE_CENTINELA_*` | `SENTINEL_REPORT_*` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_*.json` | `<signed_dir>/batches/batch_*.json` |
| `parte_history_days` | `report_history_days` |
| `monitor_y_centinela` | `github_actions_monitor` |

`ci_red.json`, its schema and the `--export-status` files did not change. The language is English until you choose another one in Settings.

# From 1.5.x to 1.6.x

Nothing you have has to be converted: the monitor keeps reading your `actions_monitor.json` and adds the new keys, with safe defaults, the first time you save from Settings.

1. Stop the monitor and unzip the new version over the old folder (keep your `actions_monitor.json` and your catalogue files).
2. Start it as before. New files appear next to it (`etag_cache.json`, `analytics_history.json`, `update_check.json`, `sentinel_history.json`); they can be deleted at any time.
3. Optional: `python actions_monitor.py --doctor` checks the installation.

What is different: the **lite edition** exists (`MONITOR_LITE_GITHUB_ACTIONS`, port 8766, its own `actions_monitor_lite.json`, no sentinel); **red on main** is one rule (the last finished run of each workflow on the default branch; cancelled, skipped, neutral and stale runs say nothing), so a figure may differ from 1.5.x; the Settings page has a **Basic** tab first; notifications, analytics, the linter, the webhook events and the AI assistant exist and are **off** until you switch them on; writing to GitHub still needs your explicit confirmation. Rich and Textual stay optional; Python 3.11 or newer.

# From 1.6.4 to 1.6.5

Nothing has to be converted. What now behaves differently, on purpose, because an unproven thing is no longer taken as safe:

- **Batches**: `finalize` offers for signing only a run whose batch RECORDS that it was built on the commit that was checked. A batch written by an older version says `needs_review`. To use one anyway: `finalize --accept-legacy` reads the run again from GitHub, accepts it only if its commit is the recorded one, and asks for the word LEGACY before each signature. Or fire the build again.
- **Green CI** means the required workflow files passed on that commit (default `ci.yml`; `dispatch.required_ci`, `dispatch.required_ci_repos`, `dispatch.required_ci_profiles`), nothing failed or waits for approval, and the list of runs is complete. A repository whose CI file has another name needs its name in `dispatch.required_ci`.
- **A failed `git fetch`** (no network, no credentials) stops the dispatch of that repository.
- **targets.json**: `tool` must be a plain file name (no folder, no `..`) that sits in the tools folder; `extra` may only hold `-f key=value` pairs (not `dry_run` or `ref`); `finalize_flags` only long flags such as `--bench`. A catalogue that does not comply is refused with the reason.
- **Notifications**: `max_per_hour` counts messages (one per channel), not events.
- **Webhook**: every request needs `X-GitHub-Delivery` (GitHub always sends it); a repeated id is ignored; the owner of `full_name` must be the watched account.
- **act**: a clone that is a link to another folder is refused (`act.allow_symlinks` allows it).
- **Network mode**: only IPv4 addresses; the address shown is the one the server listens on; `GET /api/sentinel/parte.txt?save=1` no longer writes (the copy is a POST with the one-use token).
- The stored GitHub token is no longer put in the environment of the process: only `gh` receives it.
- The test that unpacks the zip in a clean folder is no longer part of the ordinary suite; `make_release.py` runs it as its own stage.

# From 1.6.5 to 1.6.6

Nothing has to be converted. What now behaves differently, on purpose:

- **Network mode over HTTPS**: the changes made from the page now work; the `Origin` must have the scheme of the session and the port of the monitor. Behind a proxy keep the monitor's port in the address, or the check refuses it.
- **Network mode**: every setting that the schema marks `secure` can only be changed from the computer itself (before: only `listen.`, `github_token.`, `act.`, `github_actions.`). A script on another computer that changed `webhook.*`, `notify.*` and similar now gets 403 `local_only`.
- **act**: after Stop the run is free at once; a start right after no longer answers `busy`.
- New files next to the monitor: `degraded.json` and `degraded_lite.json` (the counters of swallowed failures); they can be deleted at any time.
- The history of changes (Help > Changelog) is translated: one file `docs/CHANGELOG_<lang>.md` per language.

# From 1.6.6 to 1.6.7

Nothing has to be converted. What now behaves differently, on purpose:

- **Network mode behind an HTTPS proxy on port 443**: new setting `listen.proxy_public_host` (empty by default, nothing changes if you leave it). Put the public host name of the proxy there when it forwards `Host` and `Origin` without a port; that one name is then accepted as it is, only while the network mode is on and the session is HTTPS. It can only be changed from the computer itself. Behind a proxy that keeps the port nothing changes.
- The history of changes (Help > Changelog) is now translated for 1.6.7 and 1.6.5 in the other seven languages; older entries still show the English text under a translated notice.
