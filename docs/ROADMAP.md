<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Roadmap

Ideas that did not fit in the current version, in no promised order. They are directions, not commitments; an issue or a pull request is the best way to move one forward.

## Done in 1.8.0

A new folder layout (the package in `src/`, the page, the examples and the languages in `assets/`); the bottom bar is one line and says only what the boxes at the top do not; the brief for the AI tools and the log agree with a monitor that is running; an optional read of quiet repositories through GraphQL (off by default) with its accounting; the active notice to an external AI (off by default, a first confirmation per provider, only the redacted fields of a closed list, a cap of calls and of cost an hour, the key by the name of a variable, and the AI never runs an action); the terminal application edits lists and maps; and the history of changes is translated in the eight languages back to 1.0.0.

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

- A login screen for the page, so that the network mode needs no access token typed once. Today the answer is the access token and, for the Internet, a reverse proxy with authentication (see `monitor/docs/DEPLOYMENT.md`).
- Reading the logs of a failed step in the page, with the same cleaning that the AI assistant applies.
