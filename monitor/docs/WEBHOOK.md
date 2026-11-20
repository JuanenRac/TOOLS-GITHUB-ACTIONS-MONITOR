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
- The shared secret is the only barrier: GitHub cannot send an access token, so the receiver asks for none and trusts nothing but the signature. With the receiver on and no secret set it refuses every delivery with `401`, and the doctor says so in red. Keep the address behind a tunnel or proxy that you control.
- Every request must carry `X-Hub-Signature-256: sha256=<hmac>`, made with that secret and compared in constant time; anything else gets `401`, and nothing of the payload is looked at before the signature is checked.
- A body over `webhook.max_body_kb` (1 MiB by default, up to 25 MiB) gets `413`, before anything is read or computed; the refusals are counted in `stats.too_big`.
- The lists are closed: only `workflow_run`, `workflow_job`, `check_run`, `push`, `release`, `check_suite` and `ping` are acted on, only short validated fields of an event are kept (never a commit message or any free text), and everything else is answered `202` and dropped.

## How to switch it on

1. Make a secret of 32 or more random characters, for example `python -c "import secrets; print(secrets.token_hex(32))"`.
2. Give it to the monitor through its environment, never through the file: `$env:MONITOR_WEBHOOK_SECRET = "<the secret>"` in PowerShell before starting the monitor, `export MONITOR_WEBHOOK_SECRET=...` in a shell, `Environment=` or `EnvironmentFile=` (a file only you can read) in a service, `-e` or a secret file named by `MONITOR_WEBHOOK_SECRET_FILE` in a container.
3. Switch the receiver on (Settings > Incoming webhook > Receiver on, or `"webhook": {"enabled": true}` in `actions_monitor.json`) and restart the monitor.
4. Make the address reachable: GitHub cannot reach `127.0.0.1`. Use a tunnel that you run on purpose (an HTTPS address ending in `/api/webhook`) or, on this computer, `gh webhook forward` pointing at `http://127.0.0.1:PORT/api/webhook` (see the GitHub CLI documentation for how to give it the same secret without writing it on the command line).
5. In GitHub open the repository (or the organisation) > Settings > Webhooks > Add webhook. **Payload URL**: the address of your tunnel ending in `/api/webhook`. **Content type**: `application/json`. **Secret**: the same secret. **SSL verification**: enabled. **Events**: "Let me select individual events", then Workflow runs and Workflow jobs, and optionally Check runs, Pushes and Releases. **Active**: on. One webhook of an organisation covers all its repositories; the monitor ignores the ones it does not watch.
6. Check it: in GitHub, Recent deliveries must show `200` for the first `ping`; in the monitor the Live view shows the receiver on, the counters and the coverage.

## Real-time events

- When `webhook.record_events` is on (the default), a signed `workflow_run` event updates the run list of that repository at once, without reading GitHub first: the run keeps the kind of event it already had, so its colour does not change, and the repository is read again in the next cycle to confirm it (one read per accepted event). A `workflow_job` event also brings the queue time and the time of each step for the analytics.
- Only short validated fields are kept (workflow, run, status, conclusion, branch, short commit, link to the run, durations); never the commit message or the author. The short names of the workflow, the branch, the job and the steps are kept too, in one line and cleaned like any text that leaves the monitor. The newest `webhook.live_events_keep` events can be read at `GET /api/live-events` (in the network mode, with the access token).
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
| `413` | The body is over `webhook.max_body_kb` (1 MiB by default). |
| `503` | The queue of events is full: GitHub or you send it again later (`Retry-After`); the delivery is not remembered as a duplicate. |
| `400` | No valid `X-GitHub-Delivery` id, or a payload that is not understood. |
| `202` | Accepted and ignored: a repository that is not watched, an event outside the list, a repeated delivery or a repository over its limit per minute. |
| `429` | One address sent more than 120 correctly signed requests in a minute, or more than `webhook.max_bad_per_minute` (120 by default) whose signature does not verify. |

## Replays and floods

A valid signed request that someone captured and sends again is answered but not acted on: every delivery needs its `X-GitHub-Delivery` id, the ids already accepted, and the signed body itself, are remembered for `webhook.replay_seconds` (one hour by default, bounded memory), so a captured request sent again with another id is the same delivery, and a repeat gets `202 {"duplicate": true}`. (A manual re-delivery from the GitHub page repeats the same body, so it is ignored inside that window.) One repository can cause at most `webhook.max_per_minute` accepted events a minute; the rest are answered and ignored. If the payload names `full_name`, its owner must be the watched account (or one listed in `webhook.allowed_owners`). One address may send 120 correctly signed requests a minute and `webhook.max_bad_per_minute` whose signature does not verify; the two are counted apart, in every mode, so garbage never uses up the allowance of the real deliveries (with `listen.trusted_proxy` the address is the one the proxy saw). After an accepted event the stored conditional reads of that repository are dropped and the repository is read again in the next cycle, so a live event is always reconciled with GitHub. The memory of deliveries is kept in a private file of the data folder (`webhook.persist_deliveries`, on by default; bounded, and a damaged file is an empty memory), so a restart does not make a captured delivery valid again. With `webhook.reject_stale` on (off by default) a signed workflow event whose own time is older than `webhook.replay_seconds` is answered and ignored. The allowance of correctly signed requests of one address is `webhook.max_verified_per_minute` (120). `webhook.secret_env` never accepts a variable of the system or of your login to GitHub (PATH, GH_TOKEN...) nor a secret that belongs to another setting, and a name can be written in one setting only.

The clock used is always the one of this computer, never the one of the delivery. `webhook.clock_skew_s` (300 seconds by default, 0 to 3600) is how far two clocks may differ: an event that looks that much older than the window is not stale for it (`webhook.reject_stale`), and an event marked while the clock of this computer was ahead of the real time and was set back since still counts as arrived, so a repository is not shown as dead because of a clock; it ages from the moment it is noticed. A mark more than a day ahead is not believed.

## Order, queue and lost deliveries

- **Order.** GitHub does not promise the order of deliveries. A run or a job only moves forward (queued, in progress, completed): an event that says less than what is already known about the same run (what the last cycle read counts too) changes nothing and is counted in `stats.out_of_order` of `GET /api/live-status`. A new attempt of a run starts again.
- **Queue.** An accepted event waits in a queue of at most `webhook.queue_max` events (500 by default, 1 to 10000) and a worker applies it, so GitHub is answered fast. When the queue is full the receiver answers `503` with `Retry-After` and forgets the delivery, so the one GitHub sends again is accepted: an event is never dropped in silence. The depth is `queue` in `GET /api/live-status` and the refusals are `stats.queue_full`.
- **Lost deliveries.** A run that an event left open (queued or in progress) and that gets no final event within `webhook.stale_after_h` hours (6 by default, 1 to 168) is marked `stale` in the run list and its repository is read again in the next cycle (`stats.stale`; `open_runs` counts the runs held open).
- **Ready.** `GET /readyz` (this computer only) answers `200` when the monitor is fit to take work and `503` when it is not, with the check that fails: `loaded` (a first read is in), `cycle` (the refresh loop is neither stuck nor gone), `store` (the data folder can be written) and `queue` (the queue has room). `GET /api/health` only says that the process lives.

## Without a webhook: the events of the account (off by default)

With `events_feed.enabled` on, the monitor reads the events of the account (`GET /orgs/OWNER/events`, or `/users/OWNER/events`; `events_feed.owner_kind` says which, and `auto` tries the organization first) every `events_feed.interval_seconds` (60 by default; `X-Poll-Interval` wins when it is longer) with an ETag. A read that finds nothing new answers `304` and costs no allowance; when something changed (a push, a pull request, a tag or a release) only the repository named in the event is read again in the next cycle, at most `events_feed.max_per_tick` per turn. The first read only learns where the list stands. It needs no webhook and no tunnel, and it can run next to one. The counters are `feed` in `GET /api/live-status`.

## Checklist for the Live view

1. Put a secret of at least 32 characters in the environment variable named by `webhook.secret_env` and switch the webhook on.
2. Forward the port (`gh webhook forward`) or open a tunnel, and use its address ending in `/api/webhook` in GitHub.
3. Run a workflow (or push to a watched repository) and look for the event in `?view=live`. The `ping` of GitHub only proves the signature: it is answered with `200` and is not listed, and re-sending a delivery from GitHub is ignored as a repeat.
4. Watch the allowance in the header: with webhooks a slower cycle is enough.
