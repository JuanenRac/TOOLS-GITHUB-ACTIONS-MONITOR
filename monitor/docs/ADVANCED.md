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
- **Open the session by POST.** Instead of the `?access=` address you can send `POST /api/access` with the JSON `{"token": "..."}`: the token stays out of the address bar, the history and the logs, and the cookie comes back in the answer. The `?access=` address is deprecated: it is refused by default (turn `listen.query_access` on to accept it) and, when accepted, only on a `GET`, but the token stays in the history, the logs and the `Referer`, and the monitor answers it with a `Deprecation` header. Left off (the default), the session is opened only with `POST /api/access` or the header `X-Monitor-Access`. A red bar at the top of Settings warns when `listen.host` is `0.0.0.0`. Every setting that the schema marks as secure (not only `listen.*`, `github_token.*`, `act.*` and `github_actions.*`: also the webhook, the AI actions, notifications, OpenTelemetry, the mirror, runners and outputs) can only be changed from the computer itself.
- **First steps when you listen on the network.** Keep `listen.query_access` off, as it is by default (the token then never travels in an address, a history or a log; open the session with `POST /api/access` or the header), and put HTTPS (a certificate in `listen.tls_cert_file` or an HTTPS proxy) or a VPN in front of it. The console repeats this when the network mode starts if you turned the old address on.

## Team mode: users and roles

Off by default: one person uses the monitor with no login. With `auth.enabled` on (no restart needed) nothing changes until the first administrator exists. The lite edition never has a login.

- **First administrator.** Open `/login` on the computer that runs the monitor and create it (only from that computer and only once; a request that arrives through a proxy is refused). Or on the console: `python -m github_actions_monitor.security.auth_cli create-admin NAME --password-env VAR` (the password never goes in the command line). After that the page asks for a login; `reset-password` and `revoke` of the same tool recover a lost administrator password.
- **Roles.** `viewer` reads (every GET); `maintainer` also changes the working mode and, from the computer of the monitor only (never from the network), silences and acknowledges alerts; `admin` also changes settings, users and everything that can reach GitHub or the outside. A route that is not listed is closed to everyone but an admin. Each user also has the list of accounts they may see (admins see all): another account asked for with `?account=` or `X-Account-Id` answers 403 `account_scope`, in the API and in the exports. A request that gives `account` more than once answers 400 `account_repeated`: the account is decided once, and the same one is judged and served.
- **Sessions.** The browser gets the cookie `monitor_session` (HttpOnly, SameSite=Strict, Secure over HTTPS) and a CSRF token (`X-CSRF-Token`, returned by the login and by `/api/auth/me`) that every POST must send. A script or an app uses `POST /api/auth/login` with `{"client": "api"}` and sends the token it gets as `Authorization: Bearer msn_...` (only while `auth.allow_bearer` is on; it is off by default). The one-use token of the page (`session_guard`) still applies on top of the session.
- **Passwords** are kept only as a salted scrypt hash and must have `auth.min_length` characters. After `auth.max_failed_logins` wrong passwords the user is locked for `auth.lockout_minutes`, and each address has its own limit of requests. A new password, role or state ends the sessions of that user; there is always at least one active administrator. A person at the computer of the monitor is never locked out and their wrong passwords do not count against the user; a name that does not exist is counted and locked the same way, so "locked" does not tell which names exist.
- **Endpoints.** `/api/auth/login`, `logout`, `me`, `bootstrap`, `password`; for admins `/api/auth/users` (with `/update`, `/delete`, `/revoke`) and `/api/auth/audit`. Errors are JSON with a stable code: `{"error": "...", "code": "..."}`.
- **Audit.** `auth_audit.jsonl` (a private file; one older copy is kept) records logins, locks, refused requests and changes of users; never a password, a hash or a token. `auth.audit` turns it off.
- **Several accounts.** With the accounts of `ACCOUNTS.md`, `GET /api/accounts` lists, and `/api/accounts/<id>/status` and every request with `?account=` or `X-Account-Id` reach, only the accounts assigned to the user (an admin sees all). The monitor of an account is told who is acting, so a silence of the Alerts tab records who made it (`muted_by` in `GET /api/alerts` and the history of silences).
- **The page.** A box in the header shows the name and the role of the person who is signed in and opens a menu: change my password, the users and the audit (administrators), sign out. Every change the page sends carries the CSRF token; in the individual mode and in the lite edition the page draws and asks nothing new.
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

With `runners.model.enabled` on (off by default, read only) the labels (`runs-on`) of the jobs tell **GitHub-hosted**, **larger**, **paid third-party** and **self-hosted** runners apart. Add your own names with `runners.model.thirdparty_labels` (the start of a label), `runners.model.large_labels` (names or patterns of your own larger-runner groups) and `runners.model.self_labels`. Up to `runners.model.jobs_per_cycle` unfinished runs per cycle are read (one request each). `GET /api/runners/model` and Settings > Advanced then show the queue by kind (jobs waiting and the oldest wait), the minutes and cost by kind of the finished runs that `finops.jobs_per_cycle` samples (a third-party minute has a price only if you set `runners.model.thirdparty_usd_per_minute`; GitHub never bills it), the workflows that started `runners.model.runaway_runs_per_hour` times or more in the last hour (pull requests do not count; the monitor only sees the runs it samples per repository, and says so when the limit is above that sample) and the jobs that have waited `runners.model.queue_warn_minutes` or more for a self-hosted runner, with the reason: no online runner has their labels, every fitting runner is busy, or an idle one does not take them (it is `unknown` while `runners.enabled` is off). A runaway workflow and a self-hosted queue with nobody to take it are alerts (`runners.model.alerts`, level `runners.model.alert_level`). The list of runners, the organisations of the account, the update notice and the allowance of every source are read by the cycle (at most every five minutes, or at their own pace); the `GET` routes only show what was read and never start `gh`. With `runners.model.observed_reads_per_cycle` above 0 (off by default) the monitor also reads the workflow files of the repositories that have a job on a self-hosted runner and compares what the files say (`runs-on`) with where the jobs really ran: `observed` in `GET /api/runners/model` lists each such repository with the runners seen and a reason when one is worth a look (a runner that comes from an expression or that no file declares, or a self-hosted runner in a public repository). Only the jobs of unfinished runs are seen, a repository is read again after six hours and a file only when it changed; nothing is written.

**Known limits.** The kind is read from the labels of the job, so a runner group renamed by you needs `runners.model.large_labels` or `runners.model.self_labels`. The repository plan can be `unknown` (private or free repositories do not say): quotas are then shown without a plan limit instead of an error.

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

`listen.trusted_proxy` (off by default): only if a reverse proxy of YOURS on the SAME computer is the only way in. Failed attempts are then counted against the last address of `X-Forwarded-For` (the one your proxy adds: in nginx, `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`) and not against the proxy, and, only for the requests that arrive without a usable `X-Forwarded-For`, against all of them together with a limit three times higher (that shared lock never stops a request that carries the right token). The monitor believes that header on any connection that arrives over loopback, so never use it with a proxy on another machine, and if anybody else can reach the monitor directly, leave it off. With a proxy declared (`listen.proxy_public_host`, `listen.secure_cookie` or `listen.trusted_proxy`) nothing that arrives on the main port is treated as this computer; `listen.local_port` (0 = off, otherwise 1024 to 65535) opens a second port that only listens on `127.0.0.1` for the person at the computer of the monitor (see the deployment guide). If the proxy is in another container or on another machine, list its address or network in `listen.trusted_proxies` (`MONITOR_TRUSTED_PROXIES`; in the Docker Compose file, the network `MONITOR_SUBNET`): a connection from those addresses, or from this computer, has its `X-Forwarded-For` believed to count the attempts; it never makes a request count as this computer.

## The refresh loop: heartbeat and watchdog

`/api/data` also returns `loop`: the phase of the refresh cycle (`collect`, `maintain`, `publish`, `log`, `extras`, `idle`), how long the cycle has been running, the last good cycle, the last error and the phase it happened in, the restarts and any problem writing the log or the brief for the AI. The bottom bar of the page shows it in red when a cycle runs far too long, and as a warning when a file cannot be written. A watchdog restarts a cycle that runs longer than `watchdog_minutes` (default 10, 0 switches it off) in a new thread, after writing the traceback of every thread to `actions_monitor_log.txt`.

## The network mode does not start without an administrator

With `auth.enabled` and `listen.network` both on and no user yet, the monitor does not start and says how to go on: the first administrator can only be created from this computer, so turn `listen.network` off, start the monitor (it listens on this computer only), open the page and create the administrator, then turn `listen.network` on and start it again. The local mode (127.0.0.1) always starts.

## Switches of the newest features

Everything below is local and read only, and off unless it says it is on. Each has its guide in the page (the ? button) and in this folder. (lessons is on and only writes a local file; the rest are off)

- `lessons.enabled` - docs/LESSONS.md
- `savings.webhook_first`, `savings.feeds.enabled` - docs/QUOTA.md
- `sentinels.collab.search_api` - docs/COLLAB.md
- `logs.failed_step.enabled`, `github_app.share_reads` - docs/EXTRAS.md
- `reports.workflow_hygiene.enabled`, `reports.queue.enabled`, `reports.release_view.enabled`, `reports.supply_chain.enabled` - docs/EXTRAS.md
- `ai.skill` - docs/SKILLS.md
- `ui.orientation`, `ui.screen1_tabs`, `ui.now_sort`, `ui.alerts_sort` - docs/SCREENS.md
- `ports.complete`, `ports.lite` - docs/DEPLOYMENT.md
- `notify.users.enabled` - docs/NOTIFICATIONS.md
