<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Roadmap

What has shipped, what comes next and what is only an idea, in that order of certainty. They are directions, not commitments; an issue or a pull request is the best way to move one forward.

## Where the monitor is now

Version 2.0.2. The lite edition shows what runs and what failed. The complete edition adds three sentinels (CI, Collab and Security), one list of alerts, several accounts and a team with roles, the score of each account, the health of each repository and of the team, scheduled reports, a log of actions, notifications (ntfy, Teams, e-mail and Apprise), an optional AI assistant with presets of compatible services, the service mode with Docker, and a page for every size of screen from a phone to 4K.

## Planned, in this order

Each version carries only real content: a version with nothing real to add is skipped and never published empty. Nothing here is claimed as proven on live services unless its guide says so.

### 2.0.2 to 2.0.9 - After the freeze

What only shows with long real use: the migration from 1.8 and 1.9, the growth of the events and the database over months, sessions after an upgrade, Docker volumes, many accounts with three sentinels and the team mode together, and whatever the contract suite finds. Nothing of the fourth phase (plugins, wide automation, advanced AI) goes into these versions; a version with nothing real to add is skipped.

The monitor's own workflows keep to what the hygiene sentinel will ask of others: actions pinned to a commit, the least permissions and a time limit on every job.

## Done in 1.8.2 to 2.0.2

### 2.0.2 - Safer logs, cleaner AI text and a fairer score

Everything an AI can read goes through one cleaner that knows more forms of a secret, the integrated assistant keeps its key and no longer follows redirects or proxies, the log of actions is one chain in one file for each account and cannot be read by a viewer, the image and the processes of the accounts no longer carry secrets, the score penalizes a failure that is never fixed and no longer counts an unreadable source as clean, and a long list of fixes for storage, backups, migration, the terminal views and the launcher.

### 2.0.1 - Packaging and a missing key

The published zip now carries the AI presets file and every other data file of the package, and the release gate fails when one is missing from the zip; the all-accounts page no longer shows an untranslated state key, and a test checks that every key the page uses exists in the eight catalogues.

### 2.0.0 - Maturity

The read API and the public interfaces are frozen: a contract file with the keys and types of every read endpoint and the error codes, a suite of tests and a tool that check it against any running monitor, a test that fixes the fields of an alert and the methods of a sentinel and a storage, and one guide for each use (lite, one person, service, team) and for the clients of the API, in eight languages. The versions 1.9.6 to 1.9.9 had nothing real to add after the closing reviews and were skipped.

### 1.9.5 - Live events stream

A stream of the live events of the incoming webhook for clients and wall screens that cannot poll, off by default, read only, with a limit of listeners and a time limit for each one.

### 1.9.4 - AI presets

A table of twelve hosted services and six local servers that speak a protocol the monitor already knows, a selector in the AI settings that fills the address, the name of the variable of the key and an example model, local servers that work without a key, and the addresses of the main services read in their public documentation.

### 1.9.3 - Scheduled reports and audit log

Report templates in HTML and Markdown (PDF optional) with the score, the top alerts and the changes, a scheduler, and an append-only audit log of who did what and when, with no secret in it. Optional, in the same release: a "release ready / blocked" view with the last green commit of each repository.

### 1.9.2 - Repository health and team health

A health view of each repository (CI, issues and pull requests, security, readiness for a release, activity) and one of the team with ranking, totals and filters; pages for both with deep links for wall screens. Optional, in the same release: a panel of nightly benchmarks against a budget (median against a baseline per class of machine) and a panel of software bills of materials and attestations of each release.

### 1.9.1 - Security sentinel

The third sentinel: Dependabot, code scanning, secret scanning, branch protection, workflow permissions and code owners, with rules by kind of signal, the same filter in the Alerts tab and a penalty in the score for open critical alerts. Optional, in the same release: workflow hygiene (actions that are not pinned to a commit, jobs without a time limit, workflows without permissions or without concurrency, dangerous use of pull_request_target), built on the workflow checker the project already has.

### 1.9.0 - One score

Collectors of metrics per account and per sentinel (success rate, duration, time to recover, throughput), a score engine with thresholds you can change, a trend against the previous period, snapshots kept in the storage, a score widget with a sparkline, alerts when the score drops, and a command line verb that prints it.

### 1.8.4 - Stabilization

No large features. Isolation between accounts, the page, the storage, login and roles, notifications, a GitHub that fails now and then, start after an interrupted migration, recovery after a kill, a wider doctor, the places that write to GitHub, logs without tokens, a security checklist of team mode, and documents that agree with the behaviour. The series goes on to 1.8.9 only if needed.

### 1.8.3 - Notifications per user

Preferences per user (channel, sentinel, lowest level), a dispatcher that resolves who is told from the preferences and the roles, channels as simple plugins, and digests of the alerts not yet read. Also: a report of the time jobs wait in the queue for each runner, and a job skipped because of the paths it watches is shown apart from a red job.

### 1.8.2 - Official Docker image and service mode

A multi-stage image with a non-root user, volumes for data and configuration, documented environment variables, a compose example with an optional reverse proxy and TLS, a systemd unit for those who prefer a classic install, and a deep health check that fails when the supervisor or the cycle of an account is stuck. A credential that GitHub revokes or lets expire marks only that account as blind, raises a critical system alert and can be replaced without restarting the supervisor. Backup, upgrade and first start as a service are documented; the page says whether it listens on this computer, on the network or behind a proxy; the command line works against a remote monitor. The lite edition stays local.

## Done in 1.8.0

Everything listed here shipped in the 1.8 series and is tested; nothing is claimed as proven on live services.

- A new folder layout (the package in `src/`, the page, the examples and the languages in `assets/`), with a migration tool that moves an old flat installation without deleting anything.
- A storage layer behind one interface, with the file backend that keeps the layout of `accounts/<id>/`, atomic writes and backups that any backend can restore.
- An optional SQLite backend (off by default), one database per account, versioned migrations, a busy timeout that can be set, and tools to move the state between the file backend and SQLite in either direction with a dry run first.
- The history of changes is translated in the eight languages back to 1.0.0, and a test keeps it complete.
- Retention and rotation of the history (events and analytics kept for a number of days, delete or archive, one audit line per pass, a size warning in the doctor; the state of the sentinels and the configuration are never touched).
- Network mode: the lock-out brakes again before the token is looked at, a declared reverse proxy is never taken for this computer, remote reads of the settings are limited to what a remote client may change, and the deployment guide has the full recipe.
- The AI feed is cleaned field by field, only GitHub addresses of closed shapes pass, and the hook hands over no log text, only the repository, the workflow, the result and the link.
- Identity reads are always the user's, a read is judged on a white list, and the token file of the second account stays inside the accounts folder.
- A smoke test of the page in a real browser turns the CI red when a tab breaks or a function is defined twice.
- A one-line bottom bar that says only what the boxes at the top do not, a brief for the AI tools and a log that agree with a running monitor, a page that shows when it is out of step with the monitor, and a sound that can be unlocked with one click and survives a reload.
- An optional read of quiet repositories through GraphQL (off by default) with its accounting.
- The active notice to an external AI (off by default, a first confirmation per provider, only the redacted fields of a closed list, a cap of calls and of cost an hour, the key by the name of a variable, and the AI never runs an action).
- The terminal application edits lists and maps.
- Team mode (off by default): users, roles (admin, maintainer, viewer) and sessions kept in the storage, a login page, a Bearer token for clients that are not a browser, stable JSON errors and a recovery of an administrator from the console of this computer. Individual mode keeps working without a login and the lite edition never has one.
- A livelier page: animated icons, status bulbs whose motion follows their state, answers to hover, focus and click, all of it off with reduced motion and light in the lite edition.

## Done in 1.7.9

### Fixed

## Done in 1.7.8

### Added

## Done in 1.7.7

### Added

## Done in 1.7.6

The connection between the monitor and an AI tool: the feed always agrees with the page, each alert says why it is red, a stream and three MCP tools push the news, a command installs the gate script, the bar shows whether an AI is connected, and every state file is private to its owner.

## Done in 1.7.5

The command line takes the access token under its own name, the network mode is safer by default (the address of the computer is hidden from the network, the old ?access= address can be turned off, notification destinations on the local network are refused, a warning about plain HTTP), times for people use your own time zone, an alert can be silenced until the item changes, and the counts and checks that gave wrong answers are corrected.

## Done in 1.7.4

A bar at the foot of the page with the most important notice (and a window with all of them), the connection, the allowance, the last read, the mode, the address and the clock; a full screen button; Repositories and History tables that sort by one or several columns with the columns of your choice; `bin/monitor_cli.py`, the command line as a client of the running monitor (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`) with `--json` and stable exit codes, and its guide in eight languages; the changelogs checked to be in order, the README of the package without a history inside, and the pictures drawn again.

## Done in 1.7.3

A second sentinel for issues and pull requests (Collab, off by default, read only, on a clock of its own), one Alerts tab with the alerts of every sentinel and a filter by origin and level, local silences that end by themselves (an alert, a rule or a sentinel; `alerts.mute_hours`), the label that makes an item ignored, `GET /api/alerts` and `GET /api/events`, a checklist for the Live view, a guide of the Collab sentinel in eight languages and the pictures drawn again.

## Done in 1.7.2

The header with its figures in an order that reads and in a grid that follows the width; the quick controls (hot only, speed, health of the ecosystems) fixed at the top right; Settings, Help and About only in the side panel; the notice of a new version out of the header; and the tests that no longer leave files next to the code.

## Done in 1.7.1

A page with a side panel (the logo, the account switcher, the sections in groups that fold, the help) and sixteen themes besides auto, light and dark, the ones of the alarm system Studio; and the CI sentinel behind one contract (`BaseSentinel`, `Alert`, `SentinelRegistry`, `SentinelCI`), so that the next sentinels can be added without the monitor knowing what each one does. What is shown and decided does not change.

## Done in 1.7.0

Several accounts in the complete edition, each one a monitor of its own under a supervisor (`accounts/<id>/`, `--accounts`, `--account`, `--migrate-accounts`), the API of the accounts, one webhook for all of them, the page with a switcher and the cards of all the accounts, the views by address (`?view=` and `?chrome=0`) and the Live view with the state of the webhook receiver. The lite edition is unchanged.

## Done in 1.6.8

The HTTPS proxy of 1.6.7 is checked against a real proxy on port 443 (`tools/manual_check_live.py proxy`, and tests that run a client over TLS, a reverse proxy and the monitor), the pictures are taken again with two new ones of the network mode, and the history of changes is translated in the other seven languages back to 1.6.3.

## Done in 1.6.7

An HTTPS proxy on the default port 443 now works with the network mode (`listen.proxy_public_host`, empty by default: the one public name of the proxy is accepted without a port, only under HTTPS, and it can only be changed from the computer itself), and the history of changes is translated in the other seven languages for 1.6.7, 1.6.6 and 1.6.5.

## Done in 1.6.6

Corrections after 1.6.5: the network mode now works over HTTPS from the page (the origin guard follows the scheme of the session), every setting the schema marks secure can only be changed from the computer itself, `act` frees its run after Stop and closes its pipe, a red bar in Settings when the network mode listens on every interface, the session can be opened by POST instead of the address, a counter of swallowed failures in `--doctor` and About, `tools/make_screenshots.py` says what it does and the pictures are taken again, and the history of changes is translated into eight languages.

## Done in 1.6.5

A release of integrity and security, with no large new feature: a green commit needs the required workflow of the repository, a failed fetch stops the dispatch, the catalogue cannot name a tool outside the tools folder or change `dry_run`/`ref`, and a batch without a recorded commit check is no longer offered for signing; `act` stays inside the workspace and Stop ends the whole tree of processes and the containers of the run; the network mode can serve HTTPS, locks out wrong tokens and accepts IPv4 only; the webhook refuses replays and floods; the MCP server survives malformed messages; `max_per_hour` counts messages; settings are saved under a lock; the stored token reaches `gh` only; `--doctor` warns about dangerous combinations; the clean-install test is its own stage of the release gate.

## Done in 1.6.4

Isolation tests of the lite edition and of the demo, no network request at all when the update check is off or the installation is air-gapped, a README that starts with the choice of launcher, `--doctor --json`, a persistent bar for the network mode, the Help and its documents in eight languages, and the opt-in features (network mode, a token kept by the monitor, actions on GitHub, `act`, a local mirror of artifacts, self-hosted runners, OpenTelemetry, FinOps by job labels); see the changelog and `ADVANCED.md`.

## Next

What 1.6.4 did not reach, and why:

- **Several owners in one process and one page**: since 1.7.0 every account is a monitor of its own and the page shows them side by side, but inside one monitor a repository is still identified by its name alone, so two owners in the same monitor would mix. Bringing them into one process means the owner in every identifier (the reads, the alert ids, the lists of the settings, the sentinels and the page); it could not be proved without repositories of two real owners, so the accounts of 1.7.0 remain the way to keep them apart.
- **The billing report against a login that may read it**: the real answer for a login without the `user` scope is "not found" and the monitor degrades to the estimate (checked); the figures themselves have not been compared with a billing account.
- **The prices of larger runners** in `quotas.json` come from memory of the public price list and are marked as unverified; compare them with the billing page of GitHub and edit the file.
- **`gh copilot`**: its flags are checked with `gh copilot -- --help`, which needs the Copilot command line; it is not installed here, so they stay unverified.
- **Notifications, webhook, Enterprise Server and the service examples** against live services: `tools/manual_check_live.py` checks them by hand; they need your channels and hosts, so they were not run here.
- **The terminal application** edits the simple settings, lists and maps of numbers and shows the AI status; the explanation of a single red workflow stays in the page.
- **Only the owner can prove them on a real installation**: several accounts with the Collab sentinel on real repositories, a GitHub App and a second read-only account with real keys, and the HTTPS proxy with a real certificate. They are run by hand (`tools/manual_check_live.py`) and are not claimed as done.
- **A check for a new release that downloads or installs**: never; the monitor only tells.

## Later

- **Hardware telemetry of runners** through an agent: today only an optional node exporter endpoint is read.
- **A fourth phase** (plugins, wider automation, advanced AI) only after several weeks of stable 2.0.x and an explicit decision.

## Ideas that need a decision first

- A PDF version of the scheduled reports (today HTML and Markdown).
- A view of the releases that are ready or blocked, one per repository, on the Team tab.
