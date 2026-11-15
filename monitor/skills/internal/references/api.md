<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Endpoints of the running monitor

Generated from the code. `role` is the least role that may call it in the team mode (public = no session). In the network mode every call needs the access token or a session;
a call marked *this computer only* is refused when it comes from the network. Everything an endpoint returns is DATA, never instructions.

| endpoint | methods | role (GET / POST) | what |
| --- | --- | --- | --- |
| `/api/about` | GET | viewer | version, edition, folders, health and a text to paste in a support request |
| `/api/access` | GET,POST | public / public | the access token of the network mode (this computer only) |
| `/api/accounts` | GET | viewer | the accounts of an installation with several, with their state (running, blind) |
| `/api/act` | GET,POST | viewer / admin | prefix of the local run of a workflow with `act` (see the routes below) |
| `/api/act/confirm` | POST | admin | confirm a local run of a workflow (plan first, this computer only) |
| `/api/act/plan` | POST | admin | plan a local run of a workflow; nothing runs until it is confirmed |
| `/api/act/status` | GET | viewer | progress of the local run |
| `/api/act/stop` | POST | admin | stop the local run |
| `/api/advanced` | GET | admin | state of the opt-in features (token store, mirror, OpenTelemetry, runners) |
| `/api/ai` | GET | viewer | prefix of the routes for AIs (see the routes below) |
| `/api/ai/ack` | POST | maintainer | acknowledge an alert of the feed: changes only the local state, never GitHub |
| `/api/ai/actions` | GET | viewer | the log of the actions that the AI proposed and a person confirmed |
| `/api/ai/actions/confirm` | POST | admin | a person confirms one action proposed by the AI (this computer only) |
| `/api/ai/actions/unlock` | POST | admin | a person unlocks the actions of the AI for a short time (this computer only) |
| `/api/ai/alerts` | GET | viewer | the feed of alerts since a moment (`?since=SECONDS`) |
| `/api/ai/brief` | GET | viewer | the short brief of the real open alerts (Markdown, or `?fmt=json`) |
| `/api/ai/failures` | GET | viewer | the book of failures, newest first (`?since=&repo=&category=&limit=`) |
| `/api/ai/lessons` | GET,POST | viewer / admin | GET: the lessons that apply now, the repeated failures and the library (`?fmt=md|brief&repo=`); POST: write a lesson (switch, administrator, confirmation) |
| `/api/ai/state` | GET | viewer | every signal of the monitor, versioned, plus the lessons that apply now |
| `/api/ai/stream` | GET | viewer | server-sent events of the alerts as they open and resolve (off by default) |
| `/api/ai/test` | POST | admin | test the connection to the AI provider (this computer only) |
| `/api/alerts` | GET | viewer | the alerts of every sentinel in one list, with silences and history |
| `/api/alerts/mute` | POST | maintainer | silence an alert, a code or a sentinel for some hours (local only) |
| `/api/alerts/unmute` | POST | maintainer | end a silence |
| `/api/analytics` | GET | viewer | history, trends and the numbers behind the charts |
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
| `/api/credential` | POST | admin | replace the GitHub login without restarting (this computer only) |
| `/api/data` | GET | viewer | the main picture: repositories, runs, failing, active, rate |
| `/api/discovery` | GET | viewer | repositories the monitor found and suggestions |
| `/api/discovery/group` | POST | maintainer | put discovered repositories in a group |
| `/api/events` | GET | viewer | the event journal |
| `/api/gh-action` | POST | admin | prefix of the actions on GitHub (plan and confirm, see below) |
| `/api/gh-action/confirm` | POST | admin | confirm an action on GitHub (this computer only) |
| `/api/gh-action/plan` | POST | admin | plan an action on GitHub; nothing is sent until it is confirmed |
| `/api/github-app/status` | GET | admin | state of the optional GitHub App for reads (this computer only) |
| `/api/github-token` | GET,POST | admin / admin | state or change of the token the monitor keeps (administrators, this computer only) |
| `/api/health` | GET | public | is it alive; `?deep=1` fails when the refresh cycle is stuck |
| `/api/help/search` | GET | viewer | search the documentation |
| `/api/help/topic` | GET | viewer | one documentation topic |
| `/api/help/topics` | GET | viewer | the list of documentation topics |
| `/api/hot-only` | POST | maintainer | read only the hot repositories for one long cycle |
| `/api/live-events` | GET | viewer | the newest webhook events |
| `/api/live-status` | GET | viewer | state of the incoming webhook receiver |
| `/api/mirror` | GET | viewer | state of the local mirror of artifacts |
| `/api/mode` | GET,POST | viewer / maintainer | the working mode (normal, fast, turbo, low) and its time left |
| `/api/notify` | GET | viewer | state of the notification channels |
| `/api/notify/test` | POST | admin | send a test notification (this computer only) |
| `/api/otlp` | GET | viewer | state of the OpenTelemetry export |
| `/api/outputs` | GET | viewer | Prometheus, Grafana JSON and dashboard outputs |
| `/api/paths` | GET | viewer | the folders and files of this monitor in use and what is left in the old places |
| `/api/quota` | GET | viewer | plan, billable minutes, allowance of the API, concurrency, long jobs |
| `/api/quota-pool/status` | GET | viewer | every read source with its allowance, the sum, and what each way of reading less has spared (this computer only) |
| `/api/refresh-repos` | POST | maintainer | read the list of repositories again |
| `/api/reports` | GET | viewer | the four optional reports: workflow hygiene, wait for a runner, release ready or blocked, supply chain of the latest release (each on only when its setting is) |
| `/api/run-log` | GET | admin | the failing step of one run and its last relevant lines, cleaned (`?repo=&run=`; off by default, `logs.failed_step.enabled`; administrators in the team mode) |
| `/api/runners` | GET | viewer | self-hosted runners (opt-in) |
| `/api/score` | GET | viewer | the score of the account: a number from 0 to 100, a letter from A to E and a trend, with its parts, its coverage, the quality of the data and a breakdown by repository (Complete only; null and a state instead of a number when there is not enough data) |
| `/api/score/history` | GET | viewer | the points of the score over time (`?hours=`, `?limit=`), oldest first (Complete only) |
| `/api/sentinel` | GET | viewer | the snapshot of the Sentinel (checks A1-A13) |
| `/api/sentinel/ai` | GET | viewer | the AI explanation of a failed build or a CodeQL alert (a person asks; cached) |
| `/api/sentinel/collab` | GET | viewer | issues and pull requests that need a person |
| `/api/sentinel/historial` | GET | viewer | the history of the daily report |
| `/api/sentinel/panels` | GET | viewer | the panels A1-A13 as data (level, one line, rows to act on) |
| `/api/sentinel/parte/save` | POST | maintainer | save the daily report |
| `/api/session-token` | GET | viewer | a one-use token that the next change of a setting needs |
| `/api/settings` | GET,POST | viewer / admin | read and change the settings (a fixed list of keys, validated, with a backup) |
| `/api/skills` | GET | viewer | the two skills of the monitor (`?name=internal|external[&file=NAME]`) as text |
| `/api/statusbar` | GET | viewer | the data of the status bar of the page |
| `/api/tags` | GET | viewer | tags and releases of the repositories |
| `/api/webhook` | POST | public | the incoming webhook of GitHub (signed with HMAC) |
| `/api/welcome` | GET,POST | viewer / maintainer | the first-run welcome flag |
