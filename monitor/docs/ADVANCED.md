<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Advanced features (all off by default)

Everything on this page is **off until you switch it on** in *Settings > Advanced* (or in `actions_monitor.json`), and the keys that decide who can reach the monitor or what it may do on GitHub are marked as security options. Switch on only what you need.

## Listen on the network

By default the page answers only on `127.0.0.1`. With `listen.network` on (restart needed) it also listens on `listen.host`: a private address of this computer, or `0.0.0.0` for every interface. A public address is refused.

- **Every request needs the access token** (cookie, `X-Monitor-Access` header or `Authorization: Bearer`). The token is the value of the environment variable named in `listen.token_env` (16 characters or more); without one, a random token is made at each start and shown once in the console. Open the address printed there once: it sets the cookie and goes to the clean address.
- The one-use token of the page is forced on, the page shows a red bar on every tab while the mode is on, and the keys of `listen.*`, `github_token.*`, `act.*` and `github_actions.*` can only be changed from the computer itself.
- `listen.allowed_hosts` lists the names the page may be opened with (protection against DNS rebinding).
- **Risks.** The traffic is plain HTTP: anyone who can read your network can read the token and the data. Use it only on a network you trust, or put a reverse proxy with HTTPS in front (see `DEPLOYMENT.md`). Never expose it to the Internet. The lite edition never listens beyond this computer.

## A GitHub token kept by the monitor

The default stays your own `gh` login. With `github_token.enabled` on you can paste a token in Settings > Advanced: it is kept in the secure store of the system (Windows DPAPI, macOS Keychain, Linux Secret Service) and, only when that is missing, in a file with permissions 600 (the page says so). It is never written to `actions_monitor.json`, a log, the About panel or the text for support, and it reaches `gh` through the environment of the process only. The **Delete the token** button removes it from every place.

## Actions on GitHub

With `github_actions.enabled` on, the monitor can run again a failed run (`rerun_failed`, `rerun_run`, `rerun_job`), cancel a run (`cancel`), close an issue or a pull request (`close_issue`, `close_pr`) and merge one (`merge_pr`, with `github_actions.merge_method`). Only the names in `github_actions.allowed` can be used (by default `rerun_failed` and `cancel`). **Each action is confirmed on its own**: the page shows exactly what will be sent (method and endpoint) and sends nothing until you confirm that plan with the one-use token. The token of GitHub needs the permission (`workflow` for runs, `repo` for issues and pull requests; GitHub's own refusal is shown otherwise). Every attempt is written to `github_actions_log.jsonl`. The AI assistant has no way to start any of these.

## Run a workflow here with act

With `act.enabled` on and the entries `repository:file.yml:event` in `act.allowed` (all three exact), a button runs `act` on the local clone after you confirm the exact command line. No real secrets are given (empty secret, variable, environment and input files, and a minimal environment without any token), the output is shown as it comes, one run at a time, with the time limit `act.timeout_seconds`, and you can stop it.

## Local copy of artifacts

With `mirror.enabled` on and a `mirror.folder` on this computer, the artifacts of finished runs are copied there (`mirror.max_per_cycle` per cycle, `mirror.max_mb` for the folder, `mirror.keep_days` of retention), once each, with cleaned names inside the folder.

## Self-hosted runners

With `runners.enabled` on, Settings > Advanced shows each runner as idle, busy or offline. Disk and load are shown only for the runners listed in `runners.metrics` ({name: address of a node exporter on this computer or a private address}).

## OpenTelemetry

With `otlp.enabled` on and an `otlp.endpoint` (HTTPS, or HTTP on this computer), finished runs go out as traces and the header figures as metrics (OTLP/HTTP with JSON), each run once. Only repository, workflow, branch, event, conclusion and duration are sent.

## Organisations and costs

- `organizations.discover` lists the organisations of the login in Settings > Basic. To watch one, start a second monitor with `github_owner` set to it.
- `finops.jobs_per_cycle` above 0 reads the labels of the jobs of that many finished private runs per cycle, so the minutes use the right multiplier (Linux, Windows, macOS and the larger runners of `quotas.json`) instead of one assumed system. With the billing report on (`quota.billing_api`) Codespaces and Packages dollars, the storage in use and the price of the minutes above the included ones are shown too.

## Checking against the real services

`python tools/manual_check_live.py` (in the repository) reads the scopes of your token, the billing report, the organisations, the runners and the flags of `gh copilot`, and asks a running monitor to send a test message through your channels. It never asks for a secret.
