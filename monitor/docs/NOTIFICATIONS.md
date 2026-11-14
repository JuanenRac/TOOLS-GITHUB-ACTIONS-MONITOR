<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](NOTIFICATIONS_spa.md) | [🇫🇷 Français](NOTIFICATIONS_fra.md) | [🇮🇹 Italiano](NOTIFICATIONS_ita.md) | [🇩🇪 Deutsch](NOTIFICATIONS_deu.md) | [🇨🇳 简体中文](NOTIFICATIONS_zho.md) | [🇯🇵 日本語](NOTIFICATIONS_jpn.md) | [🇵🇹 Português](NOTIFICATIONS_por.md)

# Notifications

Optional and **off by default**. The events of the feed (a new red, a stuck build, a build waiting for its signature, a lost connection, a failed run reported by the webhook) can be sent to a chat or to a device. A notification is only a message with a link: it never re-runs, cancels or writes anything on GitHub.

## Channels

- `telegram` (a bot), `discord` and `slack` (a channel webhook), `matrix` (a room), `mqtt` (a broker on this computer, for lights and beacons) and `http_local` (a POST to an address on this computer).
- Each channel has its own switch in the Settings tab (sub-tab Notifications), and a button to send a test.


## Safety

- Tokens and webhook URLs are never saved in the configuration: you set the NAME of an environment variable and the value is read only at the moment of sending, never shown, never logged.
- `discord` only accepts `discord.com` and `slack` only `hooks.slack.com`; `mqtt` and `http_local` only accept `127.0.0.1`, `localhost` or `[::1]`.
- A destination that is, or resolves to, a loopback, private (10.x, 172.16-31.x, 192.168.x, fc00::/7), link-local (169.254.x with the cloud metadata address, fe80::/10), shared (100.64.0.0/10) or reserved address is refused unless `notify.allow_private_targets` is on (off by default). The name is resolved once, the connection goes to the address that was checked, and every redirect goes through the same rule. This is what keeps a wrong Matrix homeserver from reaching your router or the metadata service of a cloud machine.
- At most `notify.max_per_hour` messages leave the computer; a send that fails is counted and ignored, it never stops the monitor.


## The adapter contract

- To reach a service that is not in the list, run a small receiver on this computer and point `http_local` at it. It receives a POST with `Content-Type: application/json` and this body: `{"kind": "red_new", "repo": "demo-repo", "text": "...", "url": "https://.../actions/runs/1"}`.
- `kind` is one of `red_new`, `red_fixed`, `stuck_new`, `pending_sign`, `release_due`, `rate_low`, `offline`, `online`, `alerts_up`, `workflow_failed`, `collab_new`, `collab_fixed`, `credential_blind`, `credential_back`. Fields are only ever added. Answer any 2xx; anything else is counted as a failure.
- `mqtt` publishes the same JSON as the payload of a QoS 0 message on `notify.channels.mqtt.topic`.

## The limit per hour counts messages

`notify.max_per_hour` limits the MESSAGES that leave the computer, not the events: an event that goes to three channels uses three of the allowance, one for each channel. When the allowance is not enough for every channel, the first channels in the list get the message and the rest are dropped (the page counts them as "limited"). A channel that cannot send (no secret, a wrong address) books nothing. The count is made under one lock, so several threads can never go over the limit.
