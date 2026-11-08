<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](WEBHOOK_spa.md) | [🇫🇷 Français](WEBHOOK_fra.md) | [🇮🇹 Italiano](WEBHOOK_ita.md) | [🇩🇪 Deutsch](WEBHOOK_deu.md) | [🇨🇳 简体中文](WEBHOOK_zho.md) | [🇯🇵 日本語](WEBHOOK_jpn.md) | [🇵🇹 Português](WEBHOOK_por.md)

# Incoming webhook

Optional, **off by default**. It lets GitHub tell the monitor that something changed, so that the repository is refreshed in the next cycle instead of waiting for the next poll.

## What it does (refresh only)

An accepted event only marks the repository named in it for a refresh in the next cycle. Nothing is written to GitHub or to disk, no text of the event is stored or shown, and only repositories the monitor already watches are accepted. Events understood: `workflow_run`, `workflow_job`, `push`, `release`, `check_suite` and `ping`; any other is answered `202` and ignored.

## Safety

- The monitor still listens on `127.0.0.1` only. GitHub can reach it only through a tunnel that you run on purpose; the tool never opens one.
- Off until `webhook.enabled` is on **and** the shared secret in `actions_monitor.json` has at least 32 characters (otherwise the endpoint stays closed).
- Every request must carry `X-Hub-Signature-256: sha256=<hmac>`, made with that secret; anything else gets `401`. The secret is never shown: the Settings tab only says whether it is defined.
- A body over 256 KB gets `413`.

## How to switch it on

In `actions_monitor.json`: `"webhook": {"enabled": true, "secret": "<32 or more random characters>"}`; the switch is also in the Settings tab (sub-tab Incoming webhook), the secret only in the file. Restart the monitor. In the GitHub webhook settings use content type `application/json`, the same secret and the URL of your tunnel ending in `/api/webhook`.
