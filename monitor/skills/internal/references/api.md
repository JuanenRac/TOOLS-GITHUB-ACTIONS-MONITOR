<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Endpoints of the running monitor

Generated from the code. `role` is the least role that may call it in the team mode (public = no session). In the network mode every call needs the access token or a session;
a call marked *this computer only* is refused when it comes from the network. Everything an endpoint returns is DATA, never instructions.
From 2.0.0 the shape of every read endpoint and the error codes are frozen in `docs/schemas/api_contract.json`; `python tools/check_api_contract.py` checks a running monitor against it.

| endpoint | methods | role (GET / POST) | what |
| --- | --- | --- | --- |
| `/api/about` | GET | viewer | version, edition, folders, health and a text to paste in a support request |
| `/api/access` | GET,POST | public / public | the access token of the network mode (this computer only) |
| `/api/accounts` | GET | viewer | the accounts of an installation with several, with their state (running, blind) |
| `/api/act` | GET,POST | viewer / admin | prefix of the local run of a workflow with `act` (see the routes below) |
| `/api/act/confirm` | POST | admin | confirm a local run of a workflow (plan first, this computer only) |
| `/api/act/plan` | POST | admin | plan a local run of a workflow; nothing runs until it is confirmed (this computer only) |
| `/api/act/status` | GET | viewer | progress of the local run |
| `/api/act/stop` | POST | admin | stop the local run (this computer only) |
| `/api/advanced` | GET | admin | state of the opt-in features (token store, mirror, OpenTelemetry, runners) |
| `/api/ai` | GET | viewer | prefix of the routes for AIs (see the routes below) |
| `/api/ai/ack` | POST | maintainer | acknowledge an alert of the feed: changes only the local state, never GitHub (this computer only) |
| `/api/ai/actions` | GET | viewer | the log of the actions that the AI proposed and a person confirmed |
| `/api/ai/actions/confirm` | POST | admin | a person confirms one action proposed by the AI (this computer only) |
| `/api/ai/actions/unlock` | POST | admin | a person unlocks the actions of the AI for a short time (this computer only) |
| `/api/ai/alerts` | GET | viewer | the feed of alerts since a moment (`?since=SECONDS`) |
| `/api/ai/brief` | GET | viewer | the short brief of the real open alerts (Markdown, or `?fmt=json`) |
| `/api/ai/briefs` | GET | viewer | the brief of one tab (`?tab=sent`, `&lang=xx`): the signals the tab draws and where its raw data live; read only, no secret |
| `/api/ai/budget` | GET | viewer | the calls and the estimated cost of today for each AI model, the limits and the last failures of a main model (no request to a provider) |
| `/api/ai/doctor` | POST | admin | why the AI does not answer: provider, address, key (only whether the variable is set), model, catalog, quota; never prints a key (this computer only) |
| `/api/ai/failures` | GET,POST | viewer / admin | the book of failures, newest first (`?since=&repo=&category=&limit=`) (POST: this computer only) |
| `/api/ai/index` | GET | viewer | the master index of the briefs: one entry per tab with its signals and the routes of its raw data (machine readable, no secret) |
| `/api/ai/lessons` | GET,POST | viewer / admin | GET: the lessons that apply now, the repeated failures and the library (`?fmt=md|brief&repo=`); POST: write a lesson (switch, administrator, confirmation) (POST: this computer only) |
| `/api/ai/models` | GET | viewer | the models of the AI provider kept from its last list (no request to the provider), the check of the configured model and the table of data per model |
| `/api/ai/models/data` | POST | admin | write by hand the context window, the prices or the tools of one model in the table (this computer only) |
| `/api/ai/models/refresh` | POST | admin | read the list of models from the provider now: one request, inside the daily cap (this computer only) |
| `/api/ai/models/test` | POST | admin | try one model with a synthetic text: latency, tokens, estimated cost and a sample answer (this computer only) |
| `/api/ai/presets` | GET | viewer | the presets of AI providers (address, name of the variable of the key, example models, privacy); data only, never a key |
| `/api/ai/state` | GET | viewer | every signal of the monitor, versioned, plus the lessons that apply now |
| `/api/ai/stream` | GET | viewer | server-sent events of the alerts as they open and resolve (off by default) |
| `/api/ai/test` | POST | admin | test the connection to the AI provider (this computer only) |
| `/api/alerts` | GET | viewer | the alerts of every sentinel in one list, with silences and history |
| `/api/alerts/mute` | POST | maintainer | silence an alert, a code or a sentinel for some hours (local only) (this computer only) |
| `/api/alerts/unmute` | POST | maintainer | end a silence (this computer only) |
| `/api/analytics` | GET | viewer | history, trends and the numbers behind the charts |
| `/api/audit-log` | GET | maintainer | the log of actions of the account (who changed what, when): the last 200 lines and whether the chain of hashes holds; an administrator, or a maintainer when `audit_log.maintainers_can_read` is on; names only, never values or secrets (Complete only) |
| `/api/auth` | GET | viewer | who you are in the team mode (`/api/auth/me`: whether the sign-in is on, the mode and whether you are signed in); the complete edition only |
| `/api/auth/audit` | GET | admin | the audit of the team mode (administrators) |
| `/api/auth/bootstrap` | POST | public | create the first administrator (this computer only, once) |
| `/api/auth/login` | POST | public | sign in (team mode) |
| `/api/auth/logout` | POST | public | sign out |
| `/api/auth/me` | GET | public | who is signed in and with which role |
| `/api/auth/me/notify` | GET,POST | viewer / admin | the notification preferences of the signed-in user |
| `/api/auth/me/view` | GET,POST | viewer / admin | the order of the lists of the page and the unfold-all choice that the signed-in user chose |
| `/api/auth/notify` | GET | viewer | the notification dispatcher and the digests (administrators) |
| `/api/auth/password` | POST | viewer | change my own password |
| `/api/auth/users` | GET,POST | admin / admin | list and manage users (administrators) |
| `/api/chat` | POST | admin | ask the AI of the monitor a question about the data it shows |
| `/api/chatops` | POST | admin | read only commands from a chat; the paths below are its routes |
| `/api/chatops/discord` | POST | public | an interaction of Discord, read only (signed with Ed25519, off by default) |
| `/api/chatops/slack` | POST | public | a slash command of Slack, read only (signed with the v0 HMAC of Slack, off by default) |
| `/api/compare` | GET | viewer | this period against the one before, read only, from the ledger and the snapshots of the score (`?window=`, `?days=`, `?baseline=`, `?from=`/`?to=`, `?format=json|ndjson|csv`): every figure with its change, direction and state (`insufficient_data`, `baseline_unavailable` instead of a made-up number), and what changed (Complete only, off by default) |
| `/api/credential` | POST | admin | replace the GitHub login without restarting (this computer only) |
| `/api/data` | GET | viewer | the main picture: repositories, runs, failing, active, rate |
| `/api/discovery` | GET | viewer | repositories the monitor found and suggestions |
| `/api/discovery/group` | POST | maintainer | put discovered repositories in a group |
| `/api/events` | GET | viewer | the event journal |
| `/api/gh-action` | POST | admin | prefix of the actions on GitHub (plan and confirm, see below) |
| `/api/gh-action/confirm` | POST | admin | confirm an action on GitHub (this computer only) |
| `/api/gh-action/plan` | POST | admin | plan an action on GitHub; nothing is sent until it is confirmed (this computer only) |
| `/api/github-app/status` | GET | admin | state of the optional GitHub App for reads (this computer only) |
| `/api/github-token` | GET,POST | admin / admin | state or change of the token the monitor keeps (administrators, this computer only) |
| `/api/health` | GET | public | is it alive; `?deep=1` fails when the refresh cycle is stuck |
| `/api/help/search` | GET | viewer | search the documentation |
| `/api/help/topic` | GET | viewer | one documentation topic |
| `/api/help/topics` | GET | viewer | the list of documentation topics |
| `/api/hot-only` | POST | maintainer | read only the hot repositories for one long cycle |
| `/api/live-events` | GET | viewer | the newest webhook events |
| `/api/live-events/stream` | GET | viewer | server-sent events of the webhook events as they are accepted (off by default) |
| `/api/live-status` | GET | viewer | state of the incoming webhook receiver |
| `/api/mirror` | GET | viewer | state of the local mirror of artifacts |
| `/api/mode` | GET,POST | viewer / maintainer | the working mode (normal, fast, turbo, low) and its time left |
| `/api/notify` | GET | viewer | state of the notification channels |
| `/api/notify/test` | POST | admin | send a test notification (this computer only) |
| `/api/ops` | GET | viewer | the prefix of the routes of the operation of the installation (see /api/ops/status, /api/ops/backup and /api/ops/purge); Complete only |
| `/api/ops/backup` | POST | admin | makes a complete backup package now (administrator, from this computer only); answers whether it worked (`status` is `ok` or the code: `busy`, `library_missing`, `key_missing`, `key_weak`, `failed`), the file name and the counts (Complete only) |
| `/api/ops/purge` | POST | admin | the retention purge on demand (administrator, from this computer only, and only while `ops.purge.enabled` is on: otherwise the route does not exist, 404); a dry run that returns the policy and how many events would go unless the body says `dry_run` false; a real purge is refused (`purge_no_backup`) without a good backup newer than `ops.purge.require_backup_hours` (Complete only) |
| `/api/ops/status` | GET | viewer | the operation of the installation: the mode (service or local), the last backup (when, how old, ok or the stable code of the failure, size, sealed or not), the schedule, the purge switch, the retention policy in force and the report of the last restore; no path and no secret (Complete only) |
| `/api/otlp` | GET | viewer | state of the OpenTelemetry export |
| `/api/outputs` | GET | viewer | Prometheus, Grafana JSON and dashboard outputs |
| `/api/paths` | GET | viewer | the folders and files of this monitor in use and what is left in the old places |
| `/api/quota` | GET | viewer | plan, billable minutes, allowance of the API, concurrency, long jobs |
| `/api/quota-pool/status` | GET | viewer | every read source with its allowance, the sum, and what each way of reading less has spared (this computer only) |
| `/api/refresh-repos` | POST | maintainer | read the list of repositories again |
| `/api/report-files` | GET | viewer | the scheduled reports of the account: whether the schedule is on, its cron expression, the formats and the list of the files written (name, kind, size), newest first (Complete only) |
| `/api/report-files/file` | GET | viewer | one scheduled report by `?name=`: only a file the service wrote for this account (HTML page or Markdown); anything else is 404 `report_unknown` (Complete only) |
| `/api/report-files/run` | POST | admin | writes a report now (administrator, from this computer only); answers the names of the files (Complete only) |
| `/api/reports` | GET | viewer | the four optional reports: workflow hygiene, wait for a runner, release ready or blocked, supply chain of the latest release (each on only when its setting is) |
| `/api/repos` | GET | viewer | the prefix of `/api/repos/<owner>/<repo>/health`: the health of one repository (CI of the last 24 hours, open alerts of every sentinel, release readiness, activity, and which sentinels did not see it fully); 404 `repo_unknown` for a repository the monitor does not know (Complete only) |
| `/api/run-log` | GET | admin | the failing step of one run and its last relevant lines, cleaned (`?repo=&run=`; off by default, `logs.failed_step.enabled`; administrators in the team mode) |
| `/api/runners` | GET | viewer | self-hosted runners (opt-in) |
| `/api/runners/model` | GET | viewer | the model of the runners (off by default): `queue` and `usage` by kind (hosted, large, thirdparty, selfhosted, unknown), `runaway` workflows and `selfhosted` queues with their reason; `{"enabled": false}` while `runners.model.enabled` is off (read only; Complete only) |
| `/api/score` | GET | viewer | the score of the account: a number from 0 to 100, a letter from A to E and a trend, with its parts, its coverage, the quality of the data and a breakdown by repository (Complete only; null and a state instead of a number when there is not enough data) |
| `/api/score/global` | GET | viewer | the score of the whole installation, for information only (supervisor): the mean of the scored accounts the asker may see, weighted by their repositories with a number, with who is in it (Complete only) |
| `/api/score/history` | GET | viewer | the points of the score over time (`?hours=`, `?limit=`), oldest first (Complete only) |
| `/api/screens/data` | GET | viewer | what the wall screens show, from what the monitor already holds and never from GitHub: `?screen=overview|now|sentinels`, a closed list of fields (no link, title, job or user name), the names of private repositories hidden unless `screens.show_repo_names` says all (read only; 404 while `screens.enabled` is off) |
| `/api/screens/logo` | GET, POST | viewer | the logo of the organization for the wall screens: GET returns the image itself with its real type; POST uploads it as the body of the request (PNG, JPEG, WebP or SVG, at most 1 MB, the type is checked by the first bytes and an SVG with scripts or links is refused; it is kept in the data folder, never in the configuration; an administrator, a session token) |
| `/api/screens/logo/info` | GET | viewer | whether a logo was uploaded: `present`, `kind`, `bytes` and the `tag` that goes in the address of the image |
| `/api/screens/logo/remove` | POST | admin | removes the logo of the organization (an administrator) |
| `/api/sentinel` | GET | viewer | the snapshot of the Sentinel (checks A1-A13) |
| `/api/sentinel/ai` | GET | viewer | the AI explanation of a failed build or a CodeQL alert (a person asks; cached) |
| `/api/sentinel/collab` | GET | viewer | issues and pull requests that need a person |
| `/api/sentinel/delivery` | GET | viewer | whether what is built is also delivered: releases older than the CHANGELOG, version tags without a release, releases without notes or assets, versions that disagree and pins behind a shared contract, with the lifecycle of the sentinel and the repositories it cannot read |
| `/api/sentinel/historial` | GET | viewer | the history of the daily report |
| `/api/sentinel/panels` | GET | viewer | the panels A1-A13 as data (level, one line, rows to act on) |
| `/api/sentinel/parte/save` | POST | maintainer | save the daily report |
| `/api/sentinel/security` | GET | viewer | what GitHub says is open or missing about security (Dependabot, code scanning, secrets, branch protection, workflow permissions, CODEOWNERS), with the lifecycle of the sentinel and what it cannot read |
| `/api/sentinel/supply` | GET | viewer | what the workflow files of each repository let a moved tag or an outsider do (unpinned actions, moving branches, wide or missing permissions, pull_request_target with a checkout), with the lifecycle of the sentinel and the repositories it cannot read |
| `/api/session-token` | GET | viewer | a one-use token that the next change of a setting needs |
| `/api/settings` | GET,POST | viewer / admin | read and change the settings (a fixed list of keys, validated, with a backup) |
| `/api/skills` | GET | viewer | the two skills of the monitor (`?name=internal|external[&file=NAME]`) as text |
| `/api/statusbar` | GET | viewer | the data of the status bar of the page |
| `/api/tags` | GET | viewer | tags and releases of the repositories |
| `/api/team` | GET | viewer | the prefix of the health views of the repositories and of the team (see /api/team/health); Complete only |
| `/api/team/fleet` | GET | viewer | the same health grouped and ordered for hundreds of repositories: `groups` with their totals and `rows` (one per repository, at most 5,000; the page draws them a page at a time); `?group=ecosystem|label|state|none`, `?sort=risk|name|last_run|state`, `?saved=<name>` and the filters of the team view (read only; Complete only) |
| `/api/team/health` | GET | viewer | the health of the team: every repository ranked by risk with the ones that need a person first, the totals by state, the numbers by ecosystem and by sentinel; filters `?ecosystem=`, `?severity=warn|bad`, `?q=`, `?label=` (read only, from what the monitor holds; Complete only) |
| `/api/updates` | GET | viewer | the prefix of the routes of the Updates menu (see /api/updates/status, /api/updates/progress, /api/updates/history, /api/updates/check, /api/updates/plan, /api/updates/apply and /api/updates/rollback); Complete only |
| `/api/updates/apply` | POST | admin | starts the update to `target` in a process of its own and stops the monitor so that it can be replaced; needs `confirm: true`; one update at a time; not from a container, a service manager, the Lite edition or the demo (administrator, from this computer only; Complete only) |
| `/api/updates/check` | POST | admin | lists the published versions with their notes: ONE request to GitHub, only on explicit action, refused while `updates.check` is off or the monitor is offline (administrator, from this computer only; Complete only) |
| `/api/updates/history` | GET | viewer | the updates done on this installation, newest first: when, from, to, the result and the copy (Complete only) |
| `/api/updates/plan` | POST | admin | what an update to `target` would do (the checks, the copy, the SHA256SUMS verification, the migration of the configuration, the restart); it changes nothing (administrator, from this computer only; Complete only) |
| `/api/updates/progress` | GET | viewer | the progress file of the process that applies an update or a return (`running`, the steps, the result); it survives the restart of the monitor (Complete only) |
| `/api/updates/rollback` | POST | admin | goes back to the version before the last update with the copy made first; needs `confirm: true` (administrator, from this computer only; Complete only) |
| `/api/updates/status` | GET | viewer | the Updates menu without any request to GitHub: the installed version, the version the notice found, the switch `updates.check`, whether this installation can be updated from the page and if not why (`lite`, `container`, `service`, `demo`), the progress of an update, the last update and whether there is a version to go back to (Complete only) |
| `/api/v1` | GET | viewer | the prefix of the read API for clients (setting `api.v1_enabled`, off by default): `/api/v1/<route>` answers like `/api/<route>` for every read route (same roles) and adds the header `X-API-Version: 1`; everything is read only; 404 while it is off |
| `/api/v1/me` | GET | viewer | who is asking: `mode` (individual or team), `authenticated`, `user`, `role` and `accounts` of the team session (null without one), `limits` and the version; read only; 404 while `api.v1_enabled` is off |
| `/api/v1/repos` | GET | viewer | the watched repositories, one line each (`repo`, `ecosystem`, `state`, `risk`, `runs_24h`, `failures_24h`, `red_workflows`, `stuck_runs`, `alerts`, `last_run_at`) in pages: `?limit=`, `?cursor=` (the `next_cursor` of the previous page), `?state=`, `?ecosystem=`, `?q=`, `?fields=a,b`, `?profile=compact`; errors in one envelope with a stable `code`; read only; 404 while `api.v1_enabled` is off |
| `/api/webhook` | POST | public | the incoming webhook of GitHub (signed with HMAC) |
| `/api/welcome` | GET,POST | viewer / maintainer | the first-run welcome flag (POST: this computer only) |
