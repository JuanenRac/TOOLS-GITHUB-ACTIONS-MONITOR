<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Roadmap

Ideas that did not fit in the current version, in no promised order. They are directions, not commitments; an issue or a pull request is the best way to move one forward.

## In 1.8.0 (the next release)

Everything listed here is written and tested; it is either already in the main branch or waiting in a pull request. Nothing is claimed as proven on live services (see "Next").

### Already in the main branch

- A new folder layout (the package in `src/`, the page, the examples and the languages in `assets/`), with a migration tool that moves an old flat installation without deleting anything.
- A storage layer behind one interface, with the file backend that keeps the layout of `accounts/<id>/`, atomic writes and backups that any backend can restore.
- An optional SQLite backend (off by default), one database per account, versioned migrations, a busy timeout that can be set, and tools to move the state between the file backend and SQLite in either direction with a dry run first.
- The history of changes is translated in the eight languages back to 1.0.0, and a test keeps it complete.
- Retention and rotation of the history (events and analytics kept for a number of days, delete or archive, one audit line per pass, a size warning in the doctor; the state of the sentinels and the configuration are never touched).

### Finished and waiting to be merged

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

### Still being finished

- Silences that remember who made them (needs team mode).

## Planned, in this order

Each version carries everything of its stretch of the plan: nothing is left hanging from an earlier version and nothing is pushed to the next one. After 1.8.3 and after 1.9.3 the product goes through an independent review and its findings are closed in the stabilization version that follows. There is no 1.8.1: users, roles and sessions arrive with 1.8.0.

### 1.8.2 - Official Docker image and service mode

A multi-stage image with a non-root user, volumes for data and configuration, documented environment variables, a compose example with an optional reverse proxy and TLS, a systemd unit for those who prefer a classic install, and a deep health check that fails when the supervisor or the cycle of an account is stuck. A credential that GitHub revokes or lets expire marks only that account as blind, raises a critical system alert and can be replaced without restarting the supervisor. Backup, upgrade and first start as a service are documented; the page says whether it listens on this computer, on the network or behind a proxy; the command line works against a remote monitor. The lite edition stays local. Also: a report of the time jobs wait in the queue for each runner.

### 1.8.3 - Notifications per user

Preferences per user (channel, sentinel, lowest level), a dispatcher that resolves who is told from the preferences and the roles, channels as simple plugins, and digests of the alerts not yet read. Also: a job skipped because of the paths it watches is shown apart from a red job.

### 1.8.4 - Stabilization

No large features. Isolation between accounts, the page, the storage, login and roles, notifications, a GitHub that fails now and then, start after an interrupted migration, recovery after a kill, a wider doctor, the places that write to GitHub, logs without tokens, a security checklist of team mode, and documents that agree with the behaviour. The series goes on to 1.8.9 only if needed.

### 1.9.0 - One score

Collectors of metrics per account and per sentinel (success rate, duration, time to recover, throughput), a score engine with thresholds you can change, a trend against the previous period, snapshots kept in the storage, a score widget with a sparkline, alerts when the score drops, and a command line verb that prints it.

### 1.9.1 - Security sentinel

The third sentinel: Dependabot, code scanning, secret scanning, branch protection, workflow permissions and code owners, with rules by kind of signal, the same filter in the Alerts tab and a penalty in the score for open critical alerts. Optional, in the same release: workflow hygiene (actions that are not pinned to a commit, jobs without a time limit, workflows without permissions or without concurrency, dangerous use of pull_request_target), built on the workflow checker the project already has.

### 1.9.2 - Repository health and team health

A health view of each repository (CI, issues and pull requests, security, readiness for a release, activity) and one of the team with ranking, totals and filters; pages for both with deep links for wall screens. Optional, in the same release: a panel of nightly benchmarks against a budget (median against a baseline per class of machine) and a panel of software bills of materials and attestations of each release.

### 1.9.3 - Scheduled reports and audit log

Report templates in HTML and Markdown (PDF optional) with the score, the top alerts and the changes, a scheduler, and an append-only audit log of who did what and when, with no secret in it. Optional, in the same release: a "release ready / blocked" view with the last green commit of each repository.

### 1.9.4 - Stabilization of the third phase

The same kind of closing as 1.8.4 for the score, the security sentinel, the health views, the reports and the audit log; the cost in API calls with three sentinels running; a score that stays coherent when a sentinel is off.

### 2.0.0 - Maturity

A major version that cleans up technical debt and freezes the public interfaces: sentinels, storage, alerts, the event schema and the read API, with a suite of contract tests that clients can run against any release. One guide for each way to use the product (lite, individual, service, team) and a reference of settings, events, metrics and API. 2.0.1 onwards is a cushion for what only shows with long real use.

The monitor's own workflows keep to what the hygiene sentinel will ask of others: actions pinned to a commit, the least permissions and a time limit on every job.

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

A bar at the foot of the page with the most important notice (and a window with all of them), the connection, the allowance, the last read, the mode, the address and the clock; a full screen button; Repositories and History tables that sort by one or several columns with the columns of your choice; `monitor_cli.py`, the command line as a client of the running monitor (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`) with `--json` and stable exit codes, and its guide in eight languages; the changelogs checked to be in order, the README of the package without a history inside, and the pictures drawn again.

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

- **More notification adapters**: ntfy, Microsoft Teams and e-mail through a local relay.
- **Several accounts in one page**: done in 1.7.0, each account in its own monitor under a supervisor.
- **Hardware telemetry of runners** through an agent: today only an optional node exporter endpoint is read.

## Ideas that need a decision first

- Reading the logs of a failed step in the page, with the same cleaning that the AI assistant applies.
