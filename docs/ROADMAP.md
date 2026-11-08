<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Roadmap

Ideas that did not fit in the current version, in no promised order. They are directions, not commitments; an issue or a pull request is the best way to move one forward.

## Next

- **Self-hosted runners**: a view of the runners of an account or an organisation (online, busy, offline, labels) and of the jobs waiting for one.
- **Cost by organisation (FinOps)**: Actions minutes and storage per organisation and per repository, with the ceilings and the alerts of the minute budget extended to several organisations.
- **OpenTelemetry export (OTLP)**: the run, job and step timings as traces and metrics for any OTLP collector, next to the Prometheus endpoint.
- **Local mirror of artifacts**: an optional, off-by-default copy of the artifacts of the runs, in a folder you choose, with a size ceiling and a retention.
- **Run a workflow locally**: a button that runs the suggested `act -W FILE -j JOB` command after an explicit confirmation (today the command is only shown).
- **More notification adapters**: ntfy, Microsoft Teams and e-mail through a local relay.
- **Several accounts in one page**: today each account runs in its own monitor.

## Ideas that need a decision first

- A login for the page, so that it can leave `127.0.0.1` without a reverse proxy. Today the answer is a reverse proxy with authentication (see `monitor/docs/DEPLOYMENT.md`).
- Reading the logs of a failed step in the page, with the same cleaning that the AI assistant applies.
