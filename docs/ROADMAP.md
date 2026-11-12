<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Roadmap

Ideas that did not fit in the current version, in no promised order. They are directions, not commitments; an issue or a pull request is the best way to move one forward.

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

- **Decided, not done in 1.6.6**: the active notice to an external AI (off by default, a first confirmation per provider, only the redacted fields of the closed list, a cap of calls and of cost an hour, the key by the name of an environment variable, and the AI never runs an action) with its variant of an outgoing command (closed list, no shell); and the repositories of several owners in one page (the monitor identifies a repository by its name alone, so it needs the owner in every identifier; it is the base of several accounts). Each is a feature of its own that needs its design and its tests, so 1.6.6 closed the corrections first.
- **The older entries of the changelog in the other seven languages**: the Help shows the history in each language, and 1.6.8 back to 1.6.3 are translated; 1.6.2 and older keep the English text under a translated notice and will be translated version by version, from the newest to the oldest.
- **Several owners in one process and one page**: since 1.7.0 every account is a monitor of its own and the page shows them side by side, but a repository is still identified by its name alone inside one monitor, so two owners in the same monitor would mix. The accounts of 1.7.0 are the way to keep them apart; bringing them into one process, with the owner in every identifier, is what is left.
- **The billing report against a login that may read it**: the real answer for a login without the `user` scope is "not found" and the monitor degrades to the estimate (checked); the figures themselves have not been compared with a billing account.
- **The prices of larger runners** in `quotas.json` come from memory of the public price list and are marked as unverified; compare them with the billing page of GitHub and edit the file.
- **`gh copilot`**: its flags are checked with `gh copilot -- --help`, which needs the Copilot command line; it is not installed here, so they stay unverified.
- **Notifications, webhook, Enterprise Server and the service examples** against live services: `tools/manual_check_live.py` checks them by hand; they need your channels and hosts, so they were not run here.
- **The terminal application** edits the simple settings and shows the AI status; the explanation of a single red workflow and the editing of lists and maps stay in the page.
- **A check for a new release that downloads or installs**: never; the monitor only tells.

## Later

- **More notification adapters**: ntfy, Microsoft Teams and e-mail through a local relay.
- **Several accounts in one page**: done in 1.7.0, each account in its own monitor under a supervisor.
- **Hardware telemetry of runners** through an agent: today only an optional node exporter endpoint is read.

## Ideas that need a decision first

- A login screen for the page, so that the network mode needs no access token typed once. Today the answer is the access token and, for the Internet, a reverse proxy with authentication (see `monitor/docs/DEPLOYMENT.md`).
- Reading the logs of a failed step in the page, with the same cleaning that the AI assistant applies.
