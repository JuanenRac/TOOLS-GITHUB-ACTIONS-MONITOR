<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](CHATOPS_spa.md) | [🇫🇷 Français](CHATOPS_fra.md) | [🇮🇹 Italiano](CHATOPS_ita.md) | [🇩🇪 Deutsch](CHATOPS_deu.md) | [🇨🇳 简体中文](CHATOPS_zho.md) | [🇯🇵 日本語](CHATOPS_jpn.md) | [🇵🇹 Português](CHATOPS_por.md)

# Chat commands (Slack and Discord)

Optional, **off by default**. It lets people ask the monitor, from a Slack or Discord channel, for a short status: how many repositories are red, the open alerts, the queue and the score. It is **read only**.

## What it does (and never does)

- The commands are a closed list: `help`, `status`, `alerts`, `red`, `queue` and `score`. Anything else is answered with "I do not know that command". `chatops.allowed_words` can only narrow the list.
- A command reads what the monitor already holds (the last cycle, the alerts, the score). It never writes on GitHub, never runs an action, never changes a setting and never reads a secret; there is no command for that and none can be added from the chat.
- The answer is seen only by the person who asked, mentions nobody and carries no link except one: when `chatops.links` is on (the default), the address of a repository (`https://<host>/<owner>/<repository>`, checked) next to a name that is shown as it is. Every text that comes from GitHub (a repository or a workflow name) is cleaned, cut and escaped for the platform.
- Every command that reaches the monitor leaves one line in the log of actions (`chatops_command`) with the ids of the chat, never the text of the request.

## Safety

- Off until `chatops.enabled` and the switch of the platform (`chatops.slack.enabled`, `chatops.discord.enabled`) are on **and** the proof is in the environment. Settings keep only the NAME of the variable (`chatops.slack.signing_secret_env`, `chatops.discord.public_key_env`), never its value; the value is never written, shown or logged.
- Slack: every request must carry `X-Slack-Signature: v0=<hmac>`, the HMAC-SHA256 of `v0:<timestamp>:<body>` made with the signing secret, and `X-Slack-Request-Timestamp` no older than `chatops.max_age_seconds` (five minutes at most). The comparison takes the same time whatever the signature is.
- Discord: every request must carry `X-Signature-Ed25519` and `X-Signature-Timestamp`: an Ed25519 signature of the timestamp followed by the body, checked with the public key of your app (RFC 8032, standard library; nothing is accepted without the check).
- A bad, old or future signature gets `401` and nothing of the body is looked at. A signature already accepted is never accepted again. A body over 16 KB gets `413`. One address can make 120 requests a minute.
- **The lists are required**: `chatops.allowed_teams`, `chatops.allowed_channels` and `chatops.allowed_users`. With none of them filled in, no command runs (the challenge of the platform is still answered so that you can finish the setup). A list that has entries must contain the team, the channel or the user of the request.
- Limits per minute: `chatops.rate_per_user_per_minute`, `chatops.rate_per_channel_per_minute` and `chatops.rate_per_minute`. The answer must come in 3 seconds: the monitor answers from memory and, if it were slower, says it is busy.
- The two routes (`/api/chatops/slack`, `/api/chatops/discord`) do not ask for the access token of the network mode, because a platform cannot send it: the signature is their proof, as with the incoming webhook. The monitor still listens on `127.0.0.1` unless you open the network mode; the platforms can reach it only through an HTTPS address that you run on purpose (a tunnel or a reverse proxy; the tool never opens one). Publish only `/api/chatops/` through it.

## The commands

| Command | Answer |
| --- | --- |
| `help` | the list of commands |
| `status` | repositories red, stuck, waiting, green and idle, and the open alerts |
| `alerts` | the open alerts (level, code and repository), up to `chatops.max_rows` |
| `red` | the red workflows with the time they have been red, up to `chatops.max_rows` |
| `queue` | running, queued, waiting for approval and minutes used in 24 hours |
| `score` | the score, its letter and its change |

`chatops.show_repo_names` decides the names: `all` (the default: every name, private repositories included), `public` (a private repository is `private-N` and its workflows are not named) or `none`. **Risk of `all`:** the names of private repositories and workflows reach every channel and user your lists allow. That is why the lists are required and every list with entries must match (team, channel and user together). Choose `public` or `none` if the channel is wider than the people who may know those names.

## Slack, step by step

1. Open api.slack.com/apps > Create New App > From scratch. Name it and pick your workspace.
2. Slash Commands > Create New Command: command `/monitor`, **Request URL** `https://<your public address>/api/chatops/slack`, a short description. No bot scope is needed.
3. Basic Information > App Credentials > **Signing Secret**: copy it and give it to the monitor through its environment, never through the file: `$env:MONITOR_SLACK_SIGNING_SECRET = "<signing secret>"` in PowerShell before starting the monitor, `export MONITOR_SLACK_SIGNING_SECRET=...` in a shell, an environment entry or a secret file in a service or a container.
4. Install the app in the workspace (Install App).
5. Fill the lists: your team id (starts with `T`), the id of the channel (open the channel, its details, the id at the bottom: `C...`) and your member id (your profile > Copy member ID: `U...`). Put them in Settings > Chat commands, or `"chatops": {"allowed_channels": ["C0123456789"]}` in `actions_monitor.json`.
6. Switch on Chat commands and Slack, and restart the monitor.

## Discord, step by step

1. Open discord.com/developers/applications > New Application. In General Information copy the **Public Key** (64 hexadecimal characters) and give it to the monitor through its environment: `$env:MONITOR_DISCORD_PUBLIC_KEY = "<public key>"` in PowerShell, `export MONITOR_DISCORD_PUBLIC_KEY=...` in a shell.
2. Fill the lists and switch on Chat commands and Discord (Settings > Chat commands), then restart the monitor. Do this **before** the next step: Discord sends a signed test when you save the address and refuses it if the monitor does not answer.
3. General Information > **Interactions Endpoint URL**: `https://<your public address>/api/chatops/discord`, then Save.
4. Register the command once with your own tool (the Discord API, `POST /applications/<application id>/commands`) with this body:

```json
{
  "name": "monitor",
  "description": "Read only status of the GitHub Actions Monitor",
  "type": 1,
  "options": [{"name": "command", "description": "help, status, alerts, red, queue or score", "type": 3, "required": false,
               "choices": [{"name": "help", "value": "help"}, {"name": "status", "value": "status"}, {"name": "alerts", "value": "alerts"}, {"name": "red", "value": "red"}, {"name": "queue", "value": "queue"}, {"name": "score", "value": "score"}]}]
}
```

5. Invite the app with the scope `applications.commands` only (OAuth2 > URL Generator); no bot permission is needed. Ids: in Discord turn on Developer Mode (Advanced) and use Copy ID on the server, the channel and your user.

## Try it

In an allowed channel type `/monitor help` (Slack) or `/monitor command:status` (Discord). Answers other than the status of the monitor:

| What you see | Meaning |
| --- | --- |
| nothing, or "did not respond" | the address is not reachable, the monitor is off, or it answered `401` (wrong secret or key, or a clock more than five minutes off) |
| "This command is not available here." | the team, channel or user is not in the lists |
| "Too many commands." | one of the three limits per minute |
| "The monitor has not read GitHub yet." | the first cycle has not finished |
