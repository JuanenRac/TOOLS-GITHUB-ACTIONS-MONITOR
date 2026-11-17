<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](WEBHOOK_spa.md) | [🇫🇷 Français](WEBHOOK_fra.md) | [🇮🇹 Italiano](WEBHOOK_ita.md) | [🇩🇪 Deutsch](WEBHOOK_deu.md) | [🇨🇳 简体中文](WEBHOOK_zho.md) | [🇯🇵 日本語](WEBHOOK_jpn.md) | [🇵🇹 Português](WEBHOOK_por.md)

# Incoming webhook

Optional, **off by default**. It lets GitHub tell the monitor that something changed, so that the repository is refreshed in the next cycle instead of waiting for the next poll.

## What it does (refresh only)

An accepted event only marks the repository named in it for a refresh in the next cycle. Nothing is written to GitHub or to disk, no text of the event is stored or shown, and only repositories the monitor already watches are accepted. Events understood: `workflow_run`, `workflow_job`, `push`, `release`, `check_run`, `check_suite` and `ping`; any other is answered `202` and ignored.

## Safety

- The monitor still listens on `127.0.0.1` only. GitHub can reach it only through a tunnel that you run on purpose; the tool never opens one.
- Off until `webhook.enabled` is on **and** the shared secret (32 characters or more) is in the environment variable named by `webhook.secret_env` (`MONITOR_WEBHOOK_SECRET` by default; `MONITOR_WEBHOOK_SECRET_FILE` can name a file whose first line is the secret, as the secrets of a container do). The secret is never written in `actions_monitor.json`, shown, logged, or inherited by the programs the monitor starts; the Settings tab only says whether it is defined. The old way (a `secret` in the file) is read only when `webhook.allow_config_secret` is true, and the Live view warns while it is used.
- Every request must carry `X-Hub-Signature-256: sha256=<hmac>`, made with that secret and compared in constant time; anything else gets `401`, and nothing of the payload is looked at before the signature is checked.
- A body over 256 KB gets `413`, before anything is computed.
- The lists are closed: only `workflow_run`, `workflow_job`, `check_run`, `push`, `release`, `check_suite` and `ping` are acted on, only short validated fields of an event are kept (never a commit message or any free text), and everything else is answered `202` and dropped.

## How to switch it on

1. Make a secret of 32 or more random characters, for example `python -c "import secrets; print(secrets.token_hex(32))"`.
2. Give it to the monitor through its environment, never through the file: `$env:MONITOR_WEBHOOK_SECRET = "<the secret>"` in PowerShell before starting the monitor, `export MONITOR_WEBHOOK_SECRET=...` in a shell, `Environment=` or `EnvironmentFile=` (a file only you can read) in a service, `-e` or a secret file named by `MONITOR_WEBHOOK_SECRET_FILE` in a container.
3. Switch the receiver on (Settings > Incoming webhook > Receiver on, or `"webhook": {"enabled": true}` in `actions_monitor.json`) and restart the monitor.
4. Make the address reachable: GitHub cannot reach `127.0.0.1`. Use a tunnel that you run on purpose (an HTTPS address ending in `/api/webhook`) or, on this computer, `gh webhook forward` pointing at `http://127.0.0.1:PORT/api/webhook` (see the GitHub CLI documentation for how to give it the same secret without writing it on the command line).
5. In GitHub open the repository (or the organisation) > Settings > Webhooks > Add webhook. **Payload URL**: the address of your tunnel ending in `/api/webhook`. **Content type**: `application/json`. **Secret**: the same secret. **SSL verification**: enabled. **Events**: "Let me select individual events", then Workflow runs and Workflow jobs, and optionally Check runs, Pushes and Releases. **Active**: on. One webhook of an organisation covers all its repositories; the monitor ignores the ones it does not watch.
6. Check it: in GitHub, Recent deliveries must show `200` for the first `ping`; in the monitor the Live view shows the receiver on, the counters and the coverage.

## Real-time events

- When `webhook.record_events` is on (the default), a signed `workflow_run` event updates the run list of that repository at once, without reading GitHub: the repository is still read again in the next cycle (the event is the news, the read is the proof), so a delivery shows the change at once but does not save a read. A `workflow_job` event also brings the queue time and the time of each step for the analytics.
- Only short validated fields are kept (workflow, run, status, conclusion, branch, short commit, link to the run, durations); never the commit message. The names of the workflow, the branch and the job are third-party text of up to 100 characters: they are kept and shown as plain text, and the names of the steps go to the statistics. The newest `webhook.live_events_keep` events can be read at `GET /api/live-events` (whoever may open the page: the access token in the network mode, a session in the team mode).
- Optional, off by default: with `live.sse.enabled` on, `GET /api/live-events/stream` sends the same events as they are accepted, as server-sent events (`hello`, then one `live` frame per event, with a running `id` to resume with `Last-Event-ID` or `?since=`, a keep-alive comment and a final `bye`). Read only; in the network mode it asks for the access token like any other request; `live.sse.max_clients` listeners at most, each for `live.sse.max_seconds`. The Lite edition does not have it.
- A run that ends red also sends the notification `workflow_failed` when notifications are on. With `webhook.record_events` off the webhook goes back to the refresh-only mode above.
- GitHub cannot reach `127.0.0.1`: use `gh webhook forward` (see the GitHub CLI documentation) or a tunnel you run on purpose, pointing at `http://127.0.0.1:PORT/api/webhook`.

## Coverage in time

The Live view says how much of the time the events cover the state: **covered by events** (the last event is newer than `savings.webhook_window_minutes`, 60 minutes by default), **no event for ...** (older: a quiet repository or a lost tunnel) or **waiting for the first event**. The polling is always the fallback: a delivery that never arrived (the monitor was off, the tunnel dropped) is caught by the next read of the repository, so the events lower the reads but never replace them. The same figures are in `GET /api/live-status`, under `coverage` and `secret_source` (`env`, `config` or `none`; never the secret).

## If it does not work

| Answer | Meaning |
|---|---|
| `404` | The receiver is off, or the secret is missing or shorter than 32 characters in the environment variable. |
| `401` | The signature does not match: use the same secret on both sides and the content type `application/json`. |
| `413` | The body is over 256 KB. |
| `400` | No valid `X-GitHub-Delivery` id, or a payload that is not understood. |
| `202` | Accepted and ignored: a repository that is not watched, an event outside the list, a repeated delivery or a repository over its limit per minute. |
| `429` | One address sent more than 120 requests in a minute (network mode). |

## Replays and floods

A valid signed request that someone captured and sends again is answered but not acted on: every delivery needs its `X-GitHub-Delivery` id, the ids already accepted are remembered for `webhook.replay_seconds` (one hour by default, bounded memory), and a repeat gets `202 {"duplicate": true}`. (A manual re-delivery from the GitHub page reuses the id, so it is ignored inside that window.) One repository can cause at most `webhook.max_per_minute` accepted events a minute; the rest are answered and ignored. If the payload names `full_name`, its owner must be the watched account (or one listed in `webhook.allowed_owners`). In the network mode one address may send 120 requests a minute. After an accepted event the stored conditional reads of that repository are dropped and the repository is read again in the next cycle, so a live event is always reconciled with GitHub.

## Checklist for the Live view

1. Put a secret of at least 32 characters in the environment variable named by `webhook.secret_env` and switch the webhook on.
2. Forward the port (`gh webhook forward`) or open a tunnel, and use its address ending in `/api/webhook` in GitHub.
3. Send the test event of GitHub (Recent deliveries > Redeliver) and look for it in `?view=live`.
4. Watch the allowance in the header: with webhooks a slower cycle is enough.
