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

## Read API v1 (off by default)

- Turn on `api.v1_enabled` (Settings, Advanced, Read API v1). Every read route is then also served under `/api/v1/` (for example `/api/v1/alerts`): the same answer and the same roles, plus the header `X-API-Version: 1`. While it is off, in the lite edition and for any other version number the prefix answers 404.
- `/api/v1/me`: who is asking: `mode` (`individual` or `team`), `authenticated`, `user`, and the `role` and `accounts` of the team session (null without one), the `limits` of the lists and the version.
- `/api/v1/repos`: the repositories the monitor watches, one line each (`repo`, `ecosystem`, `state`, `risk`, `runs_24h`, `failures_24h`, `red_workflows`, `stuck_runs`, `alerts`, `last_run_at`). Filters `state`, `ecosystem` and `q`; `limit` (by default `api.default_limit`, at most `api.max_limit`); `cursor` (the `next_cursor` of the previous page, signed and valid for `api.cursor_ttl_seconds`); `fields=a,b` or `profile=compact` for shorter lines. The answer is compressed with gzip when the client accepts it.
- `/api/v1/openapi.json`: a light OpenAPI 3 description of those two routes.
- The two own routes answer an error as `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}`: `error` and `code` are stable, `message` follows the language of `?lang=`. Codes: api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile. Everything is read only: there is no write under `/api/v1/`. The shape is frozen in the section `v1_endpoints` of the contract and is checked with `python tools/check_api_contract.py --v1` against a monitor that has `api.v1_enabled` on.

## Streams

- `GET /api/ai/stream` (the alerts) and `GET /api/live-events/stream` (the events of the webhook, `live.sse.enabled`) are server-sent events, read only and off by default; see [AI_ALERTS.md](AI_ALERTS.md) and [WEBHOOK.md](WEBHOOK.md).
