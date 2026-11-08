<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Roadmap

Ideas that did not fit in the current version, in no promised order. They are directions, not commitments; an issue or a pull request is the best way to move one forward.

## Next: a version about the first five minutes

Everything a new user should not have to think about. In this order:

- **Zero configuration at the first start**: detect `gh` (installed, logged in, scopes, host) and the account, list the organisations it belongs to and watch what the user can see by default.
- **First-start wizard** in the page, three steps at most, with a preview of what enters, and the lite edition as the default door ("start here"). Also a basic settings sub-tab placed before the advanced ones: port and opening the browser, theme, density, time format, start tab, sorting and archived / fork / empty / private repositories, the thresholds, the browser notification when something turns red, the tiles to show, restore defaults per tab and export / import of the settings (never secrets).
- **Doctor** (`--doctor` and a Diagnostics tile): Python, `gh`, session, scopes, quota, network, write permission of the folders, free port, optional Docker and Rich, each failure with the exact command that fixes it, in eight languages; plus an exportable diagnostic file without secrets.
- **Demo mode** (`--demo`) with invented data and no `gh` or network.
- **Plain-language errors** (no traceback for the user), progressive disclosure with a "what is this?" help on every setting and tile and a short glossary, launchers that keep the error visible, and an optional (off by default) check for a new release that only reads the public releases page.
- **Automatic discovery**: compare what `gh` lists with what is watched at every cycle and report a new, a vanished, an archived or an unarchived repository (a stable code, the report, `/metrics` and the optional notifications); suggest creating a group when three or more unclassified repositories share a prefix (never without a confirmation and a backup of the file); tune the hot / cold frequency by the real activity within the quota budget; lifecycle rules for archived, fork, empty and private repositories.
- A "First five minutes" guide in eight languages with pictures of the wizard.
- From the external review of 1.6.1: a short chooser in the README and the quick start ("start with Lite"), a one-use session token for the settings and the AI actions, a persistent restart banner that counts the pending settings, a migration block "from 1.5.x to 1.6.x", the lint levels info / warn / error with an allowlist in Settings, tiles for "API paused" and a minimal FinOps tile of the minutes against `minutes_budget`.

## Later

- **Self-hosted runners**: a view of the runners of an account or an organisation (online, busy, offline, labels) and of the jobs waiting for one.
- **Cost by organisation (FinOps)**: Actions minutes and storage per organisation and per repository, with the ceilings and the alerts of the minute budget extended to several organisations.
- **OpenTelemetry export (OTLP)**: the run, job and step timings as traces and metrics for any OTLP collector, next to the Prometheus endpoint.
- **Local mirror of artifacts**: an optional, off-by-default copy of the artifacts of the runs, in a folder you choose, with a size ceiling and a retention.
- **Run a workflow locally**: a button that runs the suggested `act -W FILE -j JOB` command after an explicit confirmation (today the command is only shown).
- **More notification adapters**: ntfy, Microsoft Teams and e-mail through a local relay.
- **Several accounts in one page**: today each account runs in its own monitor.
- **FinOps of the minutes**: multipliers per operating system, a breakdown by repository, workflow, branch and author, an alert for an anomaly and for a monthly allowance.
- **Self-hosted runner status** from the runners API (idle, busy, offline, queue and capacity), and hardware telemetry only through an optional node_exporter-like endpoint.

## Next: an interactive terminal application

The simple Rich view (`tui.py`, with `--once` for scripts) stays. The terminal is asked to reach the level of the web page, so an interactive application on **Textual** is planned as an optional extra (`pip install textual`; without it a clear message with that command). The core keeps needing no package. It reads the same local API of the complete or the lite edition (read only for data) and plans:

- the header tiles with the same states and colours;
- tabs with keyboard and mouse: Now, Sentinel (alerts, A10, readiness, signing queue with the trust filter), Charts (Unicode bars and sparklines, p50 / p95, queue, flaky), Repositories (sortable table, search, filters), History and Settings;
- the detail of a repository or run (jobs, steps with times, the link, and the `gh run view` / `rerun` / `act` command to copy);
- editable Settings with the same sub-tabs, validation and saving through the same API as the page, with the pending-restart notice;
- language (eight), theme and density; an events centre; the AI panel with the same closed list and confirmation;
- a help key, documented shortcuts, tests with Textual's pilot and exported SVG screenshots; `--lite` shows only the lite tabs.

## Ideas that need a decision first

- A login for the page, so that it can leave `127.0.0.1` without a reverse proxy. Today the answer is a reverse proxy with authentication (see `monitor/docs/DEPLOYMENT.md`).
- Reading the logs of a failed step in the page, with the same cleaning that the AI assistant applies.
