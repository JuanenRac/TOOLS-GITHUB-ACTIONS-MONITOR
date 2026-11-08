<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Roadmap

Ideas that did not fit in the current version, in no promised order. They are directions, not commitments; an issue or a pull request is the best way to move one forward.

## Done in 1.6.3

The first five minutes (Settings > Basic, the welcome, `--doctor`, `--demo`), automatic discovery, the one-use token, the lint levels, About and Help, the update notice, the interactive terminal application on Textual, quotas and plans and the guides of the sentinel were done; see the changelog.

## Next

What 1.6.3 did not reach, and why:

- **Zero configuration for organisations**: listing the organisations of the login and watching what it can see by default needs a real multi-organisation account to be tried against; it is only done for the account of the login.
- **Reading the billing report against a live account**: the reading of `usageItems` follows the public description of the report and is covered by simulated answers; it has not been tried with a login allowed to see billing.
- **Per-job systems for the minutes estimate**: the monitor estimates with one assumed system (`quota.default_runner`) because it does not read the labels of every job; reading them for each run costs calls and needs its own budget.
- **Prices per extra minute, larger runners, storage in use, Codespaces and Packages** are not tracked.
- **Textual**: the terminal application is covered by Textual's headless pilot in the tests; the editing of every setting (only the basic switches) and the panel of the AI assistant are left for a later version.
- **Local mirror of artifacts, wider FinOps, self-hosted runners and an OTLP export**: each is a feature of its own (settings, tests, documentation in eight languages, pictures); they were not started so that the rest could be finished well. The multipliers per system are now in `quotas.json`.
- **The flags of `gh copilot`**: they are checked with `gh copilot -- --help`, which needs the Copilot command line installed; it is not, so the current flags stay as they are and unverified.
- **A check for a new release that downloads or installs**: never; the monitor only tells.

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

## Ideas that need a decision first

- A login for the page, so that it can leave `127.0.0.1` without a reverse proxy. Today the answer is a reverse proxy with authentication (see `monitor/docs/DEPLOYMENT.md`).
- Reading the logs of a failed step in the page, with the same cleaning that the AI assistant applies.
