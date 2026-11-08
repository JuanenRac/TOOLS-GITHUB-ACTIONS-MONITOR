<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Roadmap

Ideas that did not fit in the current version, in no promised order. They are directions, not commitments; an issue or a pull request is the best way to move one forward.

## Done in 1.6.4

Isolation tests of the lite edition and of the demo, no network request at all when the update check is off or the installation is air-gapped, a README that starts with the choice of launcher, `--doctor --json`, a persistent bar for the network mode, the Help and its documents in eight languages, and the opt-in features (network mode, a token kept by the monitor, actions on GitHub, `act`, a local mirror of artifacts, self-hosted runners, OpenTelemetry, FinOps by job labels); see the changelog and `ADVANCED.md`.

## Next

What 1.6.4 did not reach, and why:

- **Several owners in one page**: the monitor identifies a repository by its name alone (runs, sentinel, cache, exports), so two owners with a repository of the same name would mix. Organisations are listed, and each is watched by its own monitor (`github_owner`). Doing it in one page needs the owner in every identifier.
- **The billing report against a login that may read it**: the real answer for a login without the `user` scope is "not found" and the monitor degrades to the estimate (checked); the figures themselves have not been compared with a billing account.
- **The prices of larger runners** in `quotas.json` come from memory of the public price list and are marked as unverified; compare them with the billing page of GitHub and edit the file.
- **`gh copilot`**: its flags are checked with `gh copilot -- --help`, which needs the Copilot command line; it is not installed here, so they stay unverified.
- **Notifications, webhook, Enterprise Server and the service examples** against live services: `tools/manual_check_live.py` checks them by hand; they need your channels and hosts, so they were not run here.
- **The terminal application** edits the simple settings and shows the AI status; the explanation of a single red workflow and the editing of lists and maps stay in the page.
- **A check for a new release that downloads or installs**: never; the monitor only tells.

## Later

- **More notification adapters**: ntfy, Microsoft Teams and e-mail through a local relay.
- **Several accounts in one page**: today each account runs in its own monitor.
- **Hardware telemetry of runners** through an agent: today only an optional node exporter endpoint is read.

## Ideas that need a decision first

- A login screen for the page, so that the network mode needs no access token typed once. Today the answer is the access token and, for the Internet, a reverse proxy with authentication (see `monitor/docs/DEPLOYMENT.md`).
- Reading the logs of a failed step in the page, with the same cleaning that the AI assistant applies.
