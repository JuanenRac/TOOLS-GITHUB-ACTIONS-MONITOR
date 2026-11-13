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
- **HTTPS.** With your own certificate and key (`listen.tls_cert_file`, `listen.tls_key_file`) the monitor serves HTTPS itself; behind a proxy that does it for you, set `listen.secure_cookie`. In both cases the browser sends `Origin: https://host:port` with every change, and the guard accepts exactly the scheme of the session (the other scheme, another host, another port or a malformed origin are refused). The address the browser uses must carry the port of the monitor, except behind an HTTPS proxy on the default port 443 that forwards `Host` and `Origin` without a port: put its public name in `listen.proxy_public_host` (a host name only, empty by default). It only counts under HTTPS, only that one name is accepted without a port, and it can only be changed from the same computer.
- **Open the session by POST.** Instead of the `?access=` address you can send `POST /api/access` with the JSON `{"token": "..."}`: the token stays out of the address bar, the history and the logs, and the cookie comes back in the answer. The `?access=` address is deprecated: it still works by default (nothing already set up breaks) and only on a `GET`, but the token stays in the history, the logs and the `Referer`, and the monitor answers it with a `Deprecation` header. Turn `listen.query_access` off to refuse it and open the session only with `POST /api/access` or the header `X-Monitor-Access`. A red bar at the top of Settings warns when `listen.host` is `0.0.0.0`. Every setting that the schema marks as secure (not only `listen.*`, `github_token.*`, `act.*` and `github_actions.*`: also the webhook, the AI actions, notifications, OpenTelemetry, the mirror, runners and outputs) can only be changed from the computer itself.
- **First steps when you listen on the network.** Turn `listen.query_access` off first (the token then never travels in an address, a history or a log; open the session with `POST /api/access` or the header), and put HTTPS (a certificate in `listen.tls_cert_file` or an HTTPS proxy) or a VPN in front of it. The console repeats this when the network mode starts while the old address is still accepted.

## Team mode: users and roles

Off by default: one person uses the monitor with no login. With `auth.enabled` on (no restart needed) nothing changes until the first administrator exists. The lite edition never has a login.

- **First administrator.** Open `/login` on the computer that runs the monitor and create it (only from that computer and only once; a request that arrives through a proxy is refused). Or on the console: `python -m github_actions_monitor.security.auth_cli create-admin NAME --password-env VAR` (the password never goes in the command line). After that the page asks for a login; `reset-password` and `revoke` of the same tool recover a lost administrator password.
- **Roles.** `viewer` reads (every GET); `maintainer` also silences and acknowledges alerts and changes the working mode; `admin` also changes settings, users and everything that can reach GitHub or the outside. A route that is not listed is closed to everyone but an admin. Each user also has the list of accounts they may see (admins see all): another account asked for with `?account=` or `X-Account-Id` answers 403 `account_scope`, in the API and in the exports.
- **Sessions.** The browser gets the cookie `monitor_session` (HttpOnly, SameSite=Strict, Secure over HTTPS) and a CSRF token (`X-CSRF-Token`, returned by the login and by `/api/auth/me`) that every POST must send. A script or an app uses `POST /api/auth/login` with `{"client": "api"}` and sends the token it gets as `Authorization: Bearer msn_...` (`auth.allow_bearer` turns this off). The one-use token of the page (`session_guard`) still applies on top of the session.
- **Passwords** are kept only as a salted scrypt hash and must have `auth.min_length` characters. After `auth.max_failed_logins` wrong passwords the user is locked for `auth.lockout_minutes`, and each address has its own limit of requests. A new password, role or state ends the sessions of that user; there is always at least one active administrator.
- **Endpoints.** `/api/auth/login`, `logout`, `me`, `bootstrap`, `password`; for admins `/api/auth/users` (with `/update`, `/delete`, `/revoke`) and `/api/auth/audit`. Errors are JSON with a stable code: `{"error": "...", "code": "..."}`.
- **Audit.** `auth_audit.jsonl` (a private file; one older copy is kept) records logins, locks, refused requests and changes of users; never a password, a hash or a token. `auth.audit` turns it off.
- **Several accounts.** With the accounts of `ACCOUNTS.md`, `GET /api/accounts` lists, and `/api/accounts/<id>/status` and every request with `?account=` or `X-Account-Id` reach, only the accounts assigned to the user (an admin sees all). The monitor of an account is told who is acting, so a silence of the Alerts tab records who made it (`muted_by` in `GET /api/alerts` and the history of silences).
- **Risk.** Over plain HTTP on a network the cookie and the passwords travel in clear: use HTTPS or a VPN, as for the network mode.

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

## Safety notes (read before switching anything on)

- **Network mode**: use it only on a network you trust. The access token does not replace encryption; on plain HTTP the token and the data travel in the clear. Put an HTTPS proxy in front (and set `listen.secure_cookie`) or give the monitor your own certificate and key (`listen.tls_cert_file`, `listen.tls_key_file`): it then serves HTTPS itself (TLS 1.2 or newer) and refuses to start if the files cannot be used. Prefer ONE private address of this computer to every interface. Only IPv4 addresses are accepted. After the first visit the address bar is cleaned of the token and the cookie is HttpOnly, SameSite=Strict (and Secure over HTTPS). A address that sends `listen.max_failed_attempts` wrong tokens within a minute is refused for five minutes. `/metrics` and `dashboard.json` list your repositories: in the network mode they need the token too.
- **Actions on GitHub**: **off by default, one confirmation per action, a closed list** (rerun a run or job, cancel, close an issue or pull request, merge a pull request when you list it). Deleting branches or repositories, secrets and settings are **not** there. The AI can propose a smaller list (`rerun_failed`, `rerun_run`, `close_issue`) and never merges.
- **act**: off by default, each run confirmed, a closed list of `repository:file:event`, no real secrets. The clone must be a real folder inside the workspace: a folder that is a link to another place is refused unless `act.allow_symlinks` is on. The time limit and Stop end the whole tree of processes that the run started, and remove the `act-` containers it created.
- **Your own token** is kept in the store of the system when there is one; the plain file (permissions 600) is the weakest store. It goes to `gh` only, never to `act` or to your commands. `--doctor` shows the store, never the token.
- **Combinations to avoid** (`--doctor` names them): network mode on every interface; AI actions that execute while the network mode is on; `act` while the network mode is on; the token in a plain file.
- The MCP server speaks over standard input and output only; never put it behind a network port.

`listen.trusted_proxy` (off by default): only if a reverse proxy of YOURS on the same computer is the only way in. Failed attempts are then counted against the last address of `X-Forwarded-For` (the one your proxy adds) and not against the proxy; a request that comes through a proxy is still never treated as this computer. If anybody else can reach the monitor directly, leave it off.
