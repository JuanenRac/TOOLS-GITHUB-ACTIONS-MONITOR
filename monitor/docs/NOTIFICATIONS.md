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
- `kind` is one of `red_new`, `red_fixed`, `stuck_new`, `pending_sign`, `release_due`, `rate_low`, `offline`, `online`, `alerts_up`, `workflow_failed`, `ai_alert`, `collab_new`, `collab_fixed`, `credential_blind`, `credential_back`, `score_dropped`, `security_new`, `security_fixed`. Fields are only ever added. Answer any 2xx; anything else is counted as a failure.
- `mqtt` publishes the same JSON as the payload of a QoS 0 message on `notify.channels.mqtt.topic`.

## Apprise (optional, off by default)

The channel `apprise` hands the message to the `apprise` command (install it yourself, for example `pip install apprise`) so that any of the services it knows can be reached. The addresses hold the secrets of those services, so they are in an environment variable whose NAME is `notify.channels.apprise.urls_env` (separated by spaces or commas, at most ten); they are written to a private temporary file for the instant of the call, never to the arguments of the command, and the command gets an environment without the keys of the monitor. **Apprise opens its own connections: the guard of the monitor against private addresses does not apply to it**, so what it reaches is up to the addresses you give it; that is why the channel has its own switch, off by default, and is marked as a security setting. If the command is missing the channel says `not_installed`; a failure is counted like any other and never stops the monitor.

## The limit per hour counts messages

`notify.max_per_hour` limits the MESSAGES that leave the computer, not the events: an event that goes to three channels uses three of the allowance, one for each channel. When the allowance is not enough for every channel, the first channels in the list get the message and the rest are dropped (the page counts them as "limited"). A channel that cannot send (no secret, a wrong address) books nothing. The count is made under one lock, so several threads can never go over the limit.

## Notifications for each user (team mode)

Off by default (`notify.users.enabled`). With the team mode on, every user chooses in `GET/POST /api/auth/me/notify` the channels (`ntfy`, `teams`, `email`), the sentinels (`ci`, `collab`), the lowest level (`info`, `warn`, `bad`), whether they want the events of the system, and whether the messages come at once or gathered in a digest (`hourly`, `daily`). The role decides what a user may be told: a viewer, the events of CI of the accounts they may see; a maintainer also what waits for a person to act (a build waiting for its signature, a release that is due); an administrator also the events of the system. An event of an account never reaches someone who may not see that account. `notify.users.max_per_hour` caps the messages one user gets.

- `ntfy`: the topic of each user on the server `notify.channels.ntfy.server` (https, or one on this computer); an access token is optional.
- `teams`: the address of the incoming webhook of a Teams channel (hosts of Microsoft only).
- `email`: the address of the user, sent through a relay on this computer that needs no login (`notify.channels.email`).

The address of the Teams webhook and the token of ntfy are kept encrypted by the system (DPAPI, Keychain, Secret Service, or a private file) and never come back in an answer, a log or the configuration; deleting a user deletes them. `MONITOR_SECRET_BACKEND=file` forces the private file. Every channel is off until the administrator turns it on. The digest gathers the alerts the user has not seen (up to `notify.digest.max_items`); `POST /api/auth/me/notify/seen` marks them as seen and they are not sent; `POST /api/auth/me/notify/test` sends a test message to the channels of the user. An administrator reads everybody's preferences (never a secret) in `GET /api/auth/notify`.

### The panel of each user

In the team mode, the menu of the signed-in user (the name at the top) has the entry **Notifications**. The panel shows and saves the same preferences as `GET/POST /api/auth/me/notify`: whether you want notifications, the channels (ntfy with its topic and an optional token, Teams with the web address of the channel, e-mail with an address), the sentinels (CI, collaboration), the lowest level, the events of the system (only for an administrator) and whether each alert comes at once or in an hourly or daily digest. A secret that is already stored is shown as stored and is never put back in the page; it is sent only when you type a new one, and an empty box keeps it. **Send a test** sends a message to your channels and **I have seen my alerts** marks the pending ones as seen. If the administrator has not turned on `notify.users.enabled`, the panel says so: you can save your choices, nothing is sent yet.

## Many alerts, or the same ones again and again

Four optional settings of the block `alerts` (all off or empty by default) decide what reaches the channels above. The lists, the Alerts tab and the events feed keep showing everything.

- **Permanent silences** (`alerts.silences`): one entry per line, `repository:workflow:branch;reason;review date`. Every part but the repository is optional and `*` matches any text. The matching alerts are shown as silenced, nobody is notified, and on the review date one reminder is announced; the silence keeps working until you remove it.
- **Services and short crons** (`alerts.service`): a workflow that only runs on a schedule or by hand and fails now and then is announced only after `failures` failures in a row, or when `rate_percent` of its last runs failed; it is announced once and cleared once instead of alerting in a loop. `workflows` adds more workflows to this class.
- **Group by commit** (`alerts.group`): when `min` or more workflows of one repository turn red on the same commit, one notification lists them.
- **Summary when there are many** (`alerts.digest`): after `threshold` notifications in the last hour, the rest are held back and told as one summary every `minutes` minutes. The held events stay in the events feed.
