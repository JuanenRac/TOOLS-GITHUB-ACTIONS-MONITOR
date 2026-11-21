<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](API_spa.md) | [🇫🇷 Français](API_fra.md) | [🇮🇹 Italiano](API_ita.md) | [🇩🇪 Deutsch](API_deu.md) | [🇨🇳 简体中文](API_zho.md) | [🇯🇵 日本語](API_jpn.md) | [🇵🇹 Português](API_por.md)

# The API for clients

What a script, a wall screen or a mobile client can rely on. From 2.0.0 the read endpoints are frozen: a key listed in the contract keeps its name and its type, new keys may appear, and nothing is removed or changed without a new major version.

## Asking

- In the default mode the API answers on `127.0.0.1` with no login. In the network mode every request carries the access token in the header `X-Monitor-Access` (or the session cookie, or `POST /api/access` once). With the team mode a script logs in at `POST /api/auth/login`.
- A word in the query that an endpoint does not know is ignored. The answers are JSON in UTF-8, apart from the brief in Markdown and the streams.

## Errors

- An error is JSON `{"error": "word"}`, sometimes with a `code`. `401 access` means the token is missing or wrong, `403 forbidden` that the request does not come from where it is allowed (also a foreign `Host`), `404` that the path does not exist in this edition (the lite edition answers 404 for what only the complete one has), `429` that the address is locked or the listeners are full.
- A refused write never changes anything. The writes are not part of the contract.

## The contract

- `docs/schemas/api_contract.json` lists every read endpoint with its keys and types in each edition and the error codes. The routes that can be read but are not frozen (streams, text, exports of other tools) are listed under `unfrozen` in the same file, each with its reason; `/api/data`, which gives the runs, the repositories and the allowance, is frozen. Its keys go down to the elements of the lists: a list written as `[{...}]` in the file describes its elements (the first three are checked), so the runs, the repositories and the allowance of `/api/data`, the alerts of `/api/alerts` and `/api/auth/me` cannot change without the check failing.
- `python tools/check_api_contract.py` checks a running monitor against it (`--lite`, `--url`, `--token-file`) and prints `CONTRACT=PASS` or `CONTRACT=FAIL`; run it after each upgrade of the monitor or of your client.

## Read API v1 (automatic by default)

- Set `api.v1_enabled` (Settings, Advanced, Read API v1): `auto` (the default) answers when the monitor runs as a service (an account of the team mode, the Docker image, the systemd unit) and stays closed for one person at one computer; `on` always; `off` never (the old true and false mean on and off). When it answers, every read route is also served under `/api/v1/` (for example `/api/v1/alerts`): the same answer and the same roles, plus the header `X-API-Version: 1`. While it is closed, in the lite edition and for any other version number the prefix answers 404.
- `/api/v1/me`: who is asking: `mode` (`individual` or `team`), `authenticated`, `user`, and the `role` and `accounts` of the team session (null without one), what the session may do (`capabilities`: `read`, `write`, `admin` and `v1_write`, always false because the prefix is read only), the `limits` of the lists, the version of the monitor and the version of the contract (`contract`, `1.0`: it grows with every key added and never loses one).
- `/api/v1/repos`: the repositories the monitor watches, one line each (`repo`, `ecosystem`, `state`, `risk`, `runs_24h`, `failures_24h`, `red_workflows`, `stuck_runs`, `alerts`, `last_run_at`). Filters `state`, `ecosystem` and `q`; `limit` (by default `api.default_limit`, at most `api.max_limit`); `cursor` (the `next_cursor` of the previous page, signed and valid for `api.cursor_ttl_seconds`); `fields=a,b` or `profile=compact` for shorter lines. The answer is compressed with gzip when the client accepts it.
- `/api/v1/openapi.json`: the OpenAPI 3 description of the whole frozen read API, built from the contract (`docs/schemas/api_contract.json`) and never written by hand: every frozen route with the keys and types it promises, `x-lite` (what the lite edition answers) and `x-local-only`. The routes the contract does not freeze are experimental: they answer 404 under `/api/v1/` and are not in the document, unless `api.experimental_routes` is on (then they are listed with `x-experimental`). The old routes under `/api/` never change. Download it with `python bin/monitor_cli.py api openapi`.
- A step by step guide for whoever writes a client, with the commands in order and the errors: [API_V1.md](API_V1.md).
- `python tools/api_contract_suite.py` is the contract suite for outside clients (only the standard library, only reads): give it the address of a server (`--url`) and a token of read (`--token-file`) and it takes the document the server serves as the description of what to check: the shape of every route that needs no parameter, the header `X-API-Version`, the error envelope and its stable codes, the pages and their cursors, `fields` and `profile=compact`, gzip and that nothing can be written under the prefix. It prints one line per check and `API_CONTRACT=PASS` or `API_CONTRACT=FAIL` (`--json` for a document); the exit code is 0, 1 or 2 (nothing answers). `python bin/monitor_cli.py api contract-check` runs it against the monitor of the command line.
- The same three things are tools of the MCP server (`python bin/mcp_server.py`, read only, no flag needed): `api_me` (who the monitor takes the client for), `api_openapi` (the document, or one route with `path`) and `api_contract_check` (the contract suite, answer `{ok, checks, failed, rows}`). HTTP, the command line (`api me`, `api openapi`, `api contract-check`) and MCP give the same document; a test compares them. While the prefix is closed the tools say so in one line.
- The two own routes answer an error as `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}`: `error` and `code` are stable, `message` follows the language of `?lang=`. Codes: api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile, api.server_error. Everything is read only: there is no write under `/api/v1/`. The shape is frozen in the section `v1_endpoints` of the contract and is checked with `python tools/check_api_contract.py --v1` against a monitor that has `api.v1_enabled` on.

### Examples with curl

The token is the access token of the network mode (or use a session of the team mode); without a network mode no token is needed from the same computer. A client follows `next_cursor` until it is `null`, and reads `/api/v1/me` first to know the version of the contract and what the session may do.

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
```

## Streams

- `GET /api/ai/stream` (the alerts) and `GET /api/live-events/stream` (the events of the webhook, `live.sse.enabled`) are server-sent events, read only and off by default; see [AI_ALERTS.md](AI_ALERTS.md) and [WEBHOOK.md](WEBHOOK.md).
- `POST /api/chatops/slack` and `POST /api/chatops/discord` receive the read only commands of a chat (off by default, `chatops.enabled`). They do not use the access token: the signature of the platform is the proof, and a request without a valid one is refused before anything is read. See [CHATOPS.md](CHATOPS.md).

## Other routes of the page

These routes serve the page and the tools of this computer. They are not part of the frozen contract and can change between versions. POST changes something; "this computer" means that only the computer that runs the monitor may use it.

| Route | What it does |
| --- | --- |
| `/api/about` | The About panel: versions, links, files, health, credits and the notice of an update; no secret. |
| `/api/act/plan` | POST, this computer. Prepares what a local run with `act` would do; nothing runs yet. |
| `/api/act/confirm` | POST, this computer. Runs a workflow on this computer with `act` after its plan; the run is recorded. |
| `/api/act/status` | The state of the local run in progress. |
| `/api/act/stop` | POST, this computer. Stops the local run. |
| `/api/advanced` | The state of the features you switch on by choice: the network, the store of the GitHub token, the actions on GitHub, the local run and the demo mode; never a token. |
| `/api/ai/actions` | The state of the actions of the AI (locked or not), their log, the proposals that wait (`proposals`) and the state of the AI. |
| `/api/ai/actions/confirm` | POST, this computer. Runs one action that the AI proposed, after you confirm it; recorded. |
| `/api/ai/actions/review` | POST, this computer. Approves or rejects one proposal of the AI (`id`, `decision`); recorded. Nothing runs. |
| `/api/ai/actions/unlock` | POST, this computer. Unlocks the actions of the AI for a limited time; recorded. |
| `/api/ai/budget` | The calls and the estimated cost of today for each AI model, the limits and the last failures; it asks no provider. |
| `/api/ai/test` | POST, this computer. Tests the connection of the AI that is set up; it changes nothing. |
| `/api/alerts/unmute` | POST. Lifts the silence of an alert; recorded. |
| `/api/analytics` | The summary of the analytics of the runs: durations, queue, steps, flaky tests and slower runs. |
| `/api/discovery` | What the discovery found: the box with the account and the repositories shown and hidden, the last events, the suggested groups, its settings, the forks and the organizations. |
| `/api/discovery/group` | POST. Adds a suggested group to the ecosystems file, keeping a copy of the file. |
| `/api/gh-action/plan` | POST, this computer. Prepares what would be sent to GitHub (a rerun, a cancel, a dispatch or a merge); nothing is sent yet. |
| `/api/gh-action/confirm` | POST, this computer. Sends to GitHub what the plan said, after you confirm; recorded. When GitHub refuses, the answer carries `reason`: forbidden, not_found, method, conflict or invalid. |
| `/api/github-token` | This computer only. The state of the store of the GitHub token (the backend and whether one is stored); never its value. |
| `/api/help/search` | Searches the help topics with a word and returns the matching ones. |
| `/api/help/topic` | The text of one help topic (`id=`) in the language of the page. |
| `/api/help/topics` | The list of the help topics with their titles. |
| `/api/hot-only` | POST, this computer. The switch "only hot" of the page; it changes no stored state. |
| `/api/mirror` | The state of the mirror of the repositories (off by default). |
| `/api/mode` | GET: the working mode, the estimate of each mode and the time left. POST, this computer: changes the mode. |
| `/api/notify/test` | POST. Sends a test message to one notification channel; it changes nothing. |
| `/api/quota-pool/status` | This computer only. The allowance of every source of reads and what the GitHub App lacks; never a key or a token. |
| `/api/refresh-repos` | POST, this computer. Refreshes only the repositories you name and rewrites the file of the red ones (used by `finalize --execute`). |
| `/api/screens/logo` | GET: the logo of the organization as an image. POST: stores a new one (at most 1 MB, checked by its real type). |
| `/api/screens/logo/remove` | POST. Removes the logo of the organization; recorded. |
| `/api/sentinel/ai` | POST. Asks the AI to explain an alert or a build; the request is small and the question is cleaned of secrets first. It does not exist while the AI is off. |
| `/api/sentinel/historial` | Yesterday against today: the reds and the pending signatures that appear or disappear. |
| `/api/sentinel/parte/save` | POST. Saves a copy of the daily report in the audit folder; a GET never writes. |
| `/api/sentinel/security` | What GitHub says is open or missing about security (the Security sentinel; off by default; read only). |
| `/api/session-token` | A token of one use for the next change of a setting; the page asks for it right before it writes. |
| `/api/statusbar` | What the bar at the foot of the page shows: edition, address, account and sentinels; no secret and no call to GitHub. |
| `/api/welcome` | GET: whether the first-start guide is done. POST, this computer: marks it as done or not. |
