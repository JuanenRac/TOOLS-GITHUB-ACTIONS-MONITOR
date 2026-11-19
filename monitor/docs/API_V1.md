<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](API_V1_spa.md) | [🇫🇷 Français](API_V1_fra.md) | [🇮🇹 Italiano](API_V1_ita.md) | [🇩🇪 Deutsch](API_V1_deu.md) | [🇨🇳 简体中文](API_V1_zho.md) | [🇯🇵 日本語](API_V1_jpn.md) | [🇵🇹 Português](API_V1_por.md)

# The read API v1, step by step

A guide for whoever writes a client (a script, a wall screen, a mobile app, an AI tool) against the read API of the monitor. The reference of every route is the OpenAPI document the monitor itself serves; the rules of the contract (what is frozen and what may grow) are in [API.md](API.md). Here is the path to follow, with commands that a test runs against a monitor.

## 1. Is the API open?

The prefix `/api/v1/` answers by itself when the monitor runs as a service (an account of the team mode, the Docker image, the systemd unit) and stays closed, answering 404, for one person at one computer. The setting `api.v1_enabled` (`auto`, `on`, `off`) decides. A client starts by asking who it is: a `404` there means the API is closed, not that your client is wrong.

## 2. Identify yourself

From the same computer with no network mode no token is needed. In the network mode every request carries the access token in the header `X-Monitor-Access`, read here from a file so that it never appears on a command line that is kept in a history; with the team mode a script logs in at `POST /api/auth/login`. A token of read is all a client of this API ever needs: there is no write under the prefix.

## 3. The commands

In this order: who you are and the version of the contract (`/api/v1/me`), the description of every frozen route (`/api/v1/openapi.json`), the repositories in pages (`state`, `ecosystem` and `q` filter; `limit`; `fields` or `profile=compact` for shorter lines; `cursor` is the `next_cursor` of the previous page, until it is `null`), the answer compressed with gzip, and two routes of the old API that the prefix also serves with the same answer.

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?fields=repo,state,risk&limit=5"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
curl -s --compressed -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=100"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/health
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/alerts
```

## 4. Errors

An error of the own routes is a JSON object with three keys: `error` and `code` are stable and meant for programs, `message` follows the language of `?lang=` and is meant for people. The codes are api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile and api.server_error. Every answer of the prefix, errors included, carries the header `X-API-Version: 1`.

```
curl -s -i -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=0"
```

The answer, after the headers, is `{"error": "bad_request", "code": "api.bad_limit", "message": "..."}`.

## 5. The same from the command line and from an AI tool

Three doors give the same documents, and a test compares them: HTTP as above, the command line (`python bin/monitor_cli.py api me`, `api openapi`, `api contract-check`; add `--json` for the answer as data) and the MCP server (`python bin/mcp_server.py`, read only: the tools `api_me`, `api_openapi` and `api_contract_check`).

## 6. Check a server before you rely on it

`python tools/api_contract_suite.py --url URL --token-file token.txt` takes the document that the server serves as the description of what to check and prints one line per check and `API_CONTRACT=PASS` or `API_CONTRACT=FAIL`. `python tools/check_api_contract.py --v1` runs the same suite and also compares the answers with the frozen contract. Run either after each upgrade of the monitor or of your client; the CI of the monitor runs the suite against a demo in the service mode.
