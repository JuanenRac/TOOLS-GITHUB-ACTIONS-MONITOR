<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Changelog

Version of the tool itself (monitor + sentinel + batch tools), semver of its own. The number lives in `tool_version.py`
and is shown as `tool_version` in the sentinel snapshot and by `read_report.py --version`; `make_release.py` refuses to build
when this file and `tool_version.py` disagree.

## [Unreleased]

Work in progress after 1.7.4.

### Added

- **`monitor_cli.py --token TOKEN`**, and the access token of the command line now has the name the monitor itself reads: `MONITOR_ACCESS_TOKEN`, then its alias `MONITOR_TOKEN`, then `--token` (a flag shows in the list of processes, so it is the last resort). The message of a refused client names the variable. Tested against a fake monitor that demands the header.
- **A warning on stderr** when `monitor_cli.py` is pointed at plain `http` on another computer (the token and the answers would travel unencrypted); the answer and `--json` are not touched.
- **`listen.query_access`** (on by default, in the Settings tab, in the eight languages): turn it off and the deprecated `?access=` address is refused, so the session opens only with `POST /api/access` (the token in the body) or the header. The address that works answers with a `Deprecation` header and the console says it is deprecated.
- **A silence "until the item changes"**: `POST /api/alerts/mute` takes `until_change` for one alert; the silence keeps the `updated_at` the issue or pull request had and ends at once when it changes (a new comment, a push), or at the end of the hours, whichever comes first. The alerts of Collab now carry `details.updated`.
- **A doctor check for one token shared by several accounts** (`credential`): it compares only a short fingerprint of the tokens the accounts would read GitHub with (the token kept by the monitor, or `GH_TOKEN` / `GITHUB_TOKEN` of the environment) and lists the accounts that share one; the token itself is never shown.
- Tests for each change, including a webhook hygiene test: a payload with a secret, an e-mail, a commit message and a token reaches neither the live list, nor the feed, nor a notification, and the live list is now filtered by a list of allowed fields.

- **`notify.allow_private_targets`** (off by default, in the Settings tab, in the eight languages): a notification destination that is, or resolves to, a loopback, private (10.x, 172.16-31.x, 192.168.x, fc00::/7), link-local (169.254.x, with the cloud metadata address, fe80::/10), shared (100.64.0.0/10) or reserved address is refused. The name is resolved once and the socket is opened to the address that was checked (so a name that changes its answer cannot get past it), and every redirect goes through the same rule. The channels `mqtt` and `http_local` stay loopback only by definition. Tested with a fake server and a fake resolver.
- **A warning about plain HTTP in the network mode**: the help of the switch `listen.network` now says, in the eight languages, that without HTTPS the token and the data travel unencrypted; the console already warns when the monitor starts on the network without a certificate.
- **Times for people in your own time zone**: the `Last read` line and the silences of `monitor_cli.py`, the log `actions_monitor_log.txt`, the reports of the sentinel, the brief for AIs and the notifications used to show UTC (`...Z`) without saying so, an hour or two away from the clock on the wall. They now read like `11:43:07 CET (10:43:07 UTC)`: the zone of the computer, its name, and the UTC time next to it. Daylight saving time is followed (tested around both changes of the year and for Madrid, UTC, Tokyo and New York).
- **`display.timezone`** (`local` by default, in the Settings tab and in the eight languages): `utc` or an IANA name such as `Europe/Madrid` shows the texts and the clocks of the page in that zone; the environment variable `MONITOR_TIMEZONE` wins over the file. Without a time zone database on the system (Windows without `tzdata`) a built-in table of the usual zones is used.
- **Fields for machines keep UTC and get a readable sibling**: `generated_local` in `ci_red.json` and in the local queue export, `updated_local` in `monitor_cli.py status --json` and in the data of the page, and an `Updated:` line in `ALERTS_BRIEF.md`. The clocks of the page and the bar at the foot show the zone (`CET`, `JST`...).
- **A button "Until it changes" in the Alerts tab**: it silences an alert of an issue or pull request until its `updated_at` changes (a new comment, a push), or for the usual hours at most; the silenced alert says "silenced until it changes". Texts in the eight languages and a regression test.

### Changed

- **The API calls the edition `complete`** (it said `full`) in `/api/about`, `/api/statusbar`, `--doctor --json` and the command line; `full` stays reserved for what the sentinel may execute. The page and the command line still understand both words.
- **Silences are made only from the computer of the monitor** (also in the network mode, until the editions with users): the guide of Collab says so in the eight languages, and a test keeps the route behind that rule.
- **The workflows of this repository use actions pinned to a full commit**, with the version in a comment, and a test keeps them so.

### Fixed

- **Issues that could be closed** (surface check): a green run of another workflow no longer proposes closing an issue; the issue must name the workflow (by its name or by its file, "Firmware build failed" for `firmware-build.yml`) and that same workflow must have a later green run on the default branch. An issue that names no workflow proposes nothing.
- **Tag against manifest** (surface check): when the tag of the latest release is ahead of the manifest read from the clone, the manifest of the default branch on GitHub is read once for that release (the clone may be behind after a release) and the warning disappears if it already had that version; tags that are not versions (`meshes-1`) are ignored.
- **Next step of a release candidate**: a repository whose release needs a signed build now says "build in Actions and sign", apart from "bump the version", "sign" and "publish"; the repositories of ecosystems handled elsewhere stay out of the candidates (tested).
- **The runs in progress and queued are counted once**: the tiles "running" and "queued", the list "Right now", the status bar (new item "N running · M queued", also in `/api/statusbar` as `runs`) and `monitor_cli status` give the same numbers for the same data, in both editions. When the filters of the page (ecosystem, state, search, a list from a tile) hide some runs the tiles show "3 of 13" and the list begins with "Showing 3 of 14 (filters active)", so a filter saved in the browser can no longer look like a mismatch. The list of active runs also drops a run read twice. Texts in the eight languages and tests for both editions.

### Security

- **`/api/statusbar` no longer hands the address of the computer on the local network (`lan_address`) to a client of the network** in the network mode; the bar draws without it.
- The deprecated `?access=` address is honoured only on a `GET`.

## [1.7.4]

A bar at the foot of the page for the notices and the facts of the monitor, a full screen button, tables that sort by one or several columns with the columns of your choice, and the command line as a client of the running monitor.

### Added

- **A status bar at the foot of the page** (all editions) in place of the line of authorship. On the left, the most important notice (red before yellow) with the number of the others and a button that opens a window with all of them, newest first, with a filter by level; with no notice it says so. On the right, the connection (a lamp: GitHub online, offline, or allowance low), the allowance and when it renews, the last read, the working mode, how many sentinels are on, the repositories watched, the account, the version and edition, the address of the monitor and the local date and time. It follows the width of the window: the secondary facts fold away on narrow screens. `GET /api/statusbar` gives it the facts that GitHub data does not carry (no GitHub call, no secret).
- **A full screen button** in the top right corner (the Fullscreen API; a second press leaves it), with its icon and text in the eight languages.
- **Sortable tables**: Repositories and History sort by a click on a header (up, down, none), by several columns at once with Shift+click (each key shows its number and direction), the empty values always last, and the order is remembered. A column chooser adds more columns: run number, actor, short commit, attempt, queue wait, file and ecosystem in History; ecosystem, run number, actor, commit, attempt, queue wait, runs in 24 h, default branch, visibility, last push and open pull requests in Repositories. The monitor now sends the run number and the queue wait of every run and a small block of facts per repository (taken from what it already read; nothing new from GitHub).
- **`monitor_cli.py`**, the command line as a client of the running monitor (`status`, `health` or `check`, `doctor`, `accounts`, `alerts`, `live`): it reads `GET /api/...` on this computer or at `--url` / `MONITOR_URL`, prints plain text or one JSON document with `--json`, takes `--account`, `--sentinel`, `--level`, `--muted`, `--timeout` and `--lang`, and uses stable exit codes (0 all right, 1 wrong use, 2 monitor not reachable, 3 credential refused, 4 degraded, 5 alerts found with `--fail-on`). `health` tells a monitor that does not answer from a GitHub login that failed and from an allowance that ran out. The lite edition answers `status`, `doctor` and `health`. It never writes to GitHub; the access token of the network mode goes in `MONITOR_TOKEN`. The older tools keep working. Guide in eight languages (`CLI.md`).
- Tests for each change, including the sorting logic run for real with Node where it is installed, the commands against a fake monitor, every exit code and a test that every changelog, in every language, lists its versions from the newest to the oldest, with the same versions as the source.

### Changed

- **The red and yellow notices no longer sit on top of the page**: the same notices are shown in the bar at the foot (the most important one) and in its window (all of them).
- **The README of the package** (`README_<lang>.txt`) no longer carries a history of versions: it points to the changelog.
- The pictures of the README, the architecture and the structure are drawn again for this version, with a picture of the new tables and bar.

### Removed

- **The line of authorship at the foot of the page**: the author and the licence are in About.

## [1.7.3]

A second sentinel for issues and pull requests, one tab with the alerts of every sentinel, and silences that end by themselves. Collab only reads; nothing here writes to GitHub.

### Added

- **The Collab sentinel** (`sentinel_collab.py`, complete edition only, off by default): the open issues and pull requests of your repositories, on a clock of its own (`sentinels.collab.refresh_seconds`) that never alters the CI sentinel. Six rules with stable codes: `collab.issue.stale`, `collab.issue.critical`, `collab.issue.external`, `collab.pr.review_pending`, `collab.pr.draft_old` and `collab.pr.conflict`. It reads with conditional requests (an unchanged repository costs no allowance), at most `max_repos_per_tick` repositories per round, pauses under `min_rate_remaining`, keeps its state in `collab_state.json` (inside the folder of each account) and announces only changes. Bots are left out. Its layer *Issues and pull requests* is in the Sentinel tab and `GET /api/sentinel/collab` serves it.
- **Two new events**, `collab_new` and `collab_fixed`, for the feed and for every notification channel (they are in the list of events of the channels and in the event schema).
- **The Alerts tab** (complete edition): one list with the alerts of every sentinel, each with its origin (CI or Collab) and level, a filter by origin and by level, a link to GitHub and a red dot on the tab with the errors that are open. `?view=alerts&sentinel=collab` opens it filtered.
- **Silences with an end** (`alert_center.py`): from the Alerts tab an alert, a rule (its code) or a whole sentinel can be silenced for `alerts.mute_hours` hours (24 by default, 1 to 720). A silence lapses by itself, can be restored at once, and a short history says what was silenced, since when and until when. It is a note of the monitor, kept per account in `alert_mutes.json`; nothing changes on GitHub.
- **`ignore_labels`** in the rules of Collab (`monitor:ignore` by default): an issue or pull request that a person labelled so on GitHub raises no alert. The monitor never writes labels.
- **`GET /api/alerts`** (`?sentinel=`, `?level=`, `?muted=show|hide|only`) and **`GET /api/events`** (`?sentinel=`, `?since=`), both read only and per account; `POST /api/alerts/mute` and `/api/alerts/unmute` (this computer only, one-use token, like every other change).
- **A checklist in the Live view** (secret of 32 characters or more, forward or tunnel to `/api/webhook`, the test event of GitHub, watch the allowance) and the same steps in the webhook guide.
- **A guide of the Collab sentinel** in the eight languages (`COLLAB.md`), found by the Help.
- Tests for each change: the rules and their stable codes, the cost (conditional reads, the cap per round, the pause), that it only reads, the silences (scopes, end, bounds, history, a damaged file), the ignore label, the endpoints, that lite has none of it, the files of state of each account and of the demo, and the texts in the eight languages.

### Changed

- The settings page has twelve settings for Collab in one block of the Sentinel tab, and `alerts.mute_hours` beside them.
- The files `alert_mutes.json`, `collab_state.json`, `ai_alerts_state.json` and `ALERTS_BRIEF.md` are never committed and never travel in a package.

## [1.7.2]

A header that reads in order and fits the window, the quick controls fixed in the top right corner, About in the side panel, and the end of the notice of a new version. The tests stop leaving files next to the code, which is what had replaced the settings of a person by the neutral template.

### Changed

- **The figures of the header, in order and in a grid** (all editions): the first row now goes from what is going on to what needs attention (running, queued, failures, successes, compute minutes, open issues, workflows red on main, unsigned) and the second keeps the machinery (repositories, hot, mode, reads saved, allowance, connection, updated). Each row is a grid of eight columns, four or two according to the width of its own block, so the two rows always fill their lines at any window width, from a 1080p screen up (a tile never forces a width of its own). The long allowance tile takes two columns.
- **The quick controls stay at the top right corner**: the hot-only button, the speed list (normal, fast, turbo) and the health chips of the ecosystems (and the budget and paused badges) are fixed there, in a column of their own, and wrap inside it without moving the figures. Below 1100 points wide the corner goes above the figures. The page of all the accounts hides it, as it hides the figures.
- **Settings, Help and About are only in the side panel**: the gear, the question mark and the information buttons leave the header. Settings was already a section of the panel; Help for this tab stays at its foot and **About** is added beside it. The guide of the Settings says so in the eight languages.

### Removed

- **The notice of a new version in the header** (the orange badge) with its code and its style. The About panel still says whether there is a newer version, and so does the console; the setting `updates.check` and the cache of 24 hours are the same.

### Fixed

- **The neutral template could replace the settings of a person.** Three groups of tests (the lite isolation, the one-use token and the lite part of the accounts) started a monitor whose first start writes `actions_monitor.json` or `update_check.json` next to the code, and nothing removed them; copying the `monitor/` folder over an installation then replaced the settings of the person (their own catalogue of ecosystems) by the template, and every repository fell into the group "Everything else" (a corner that read "Everything else 54"). Each of those tests now removes what it created, and a test proves it. The package never carried the settings or the catalogue of anyone, and still does not.

## [1.7.1]

A new page and the same sentinel behind a contract. The page has a side panel on the left with the logo, the sections in groups and sixteen themes; the CI sentinel is now one of the sentinels of a registry, which is what lets the next ones arrive. What the monitor shows and decides does not change.

### Added

- **A side panel** (all editions): the logo of the tool (an SVG that draws itself with the colours of the theme and stands still when the system asks for less motion), the account switcher, the sections in three groups that fold (Watch, Data, System) and the help. The panel collapses to its icons and both choices are remembered in the browser. The top bar shows the name of the section and the tools. The arrow keys, up and down too, move between sections. On a small screen the panel goes on top. `?chrome=0` hides it, as it hid the tab bar.
- **Sixteen themes** besides auto, light and dark: the ones of the alarm system Studio (Armor, Aqua, Midnight, Ember, Forest, Violet, Solar, Ice, Crimson, Mono, High contrast, Metallic, Professional, Videogame, Terminal and Blueprint), chosen from a list in Settings > This browser or with `?theme=`. Each one sets the page, the side panel, the panels, the lines, the text, the accent, the corners and the letters. Green, red, amber and blue keep their meaning in all of them, lightened or darkened where a theme needs it so that every figure reads at 4.5:1 or more, and the text of a badge follows its colour.
- **`BaseSentinel`, `Alert` and `SentinelRegistry`** (`sentinel_base.py`, `sentinel_registry.py`; the complete edition only): the contract of a sentinel (`start`, `stop`, `tick`, `get_status`, `get_alerts`, `get_metrics`, `get_config_schema`, `refresh_seconds`), an alert with a stable code that never depends on the language (`ci.red`, `ci.stuck`, `ci.pending_sign`) and the account it belongs to, and a registry that gives every sentinel a clock of its own. `sentinels.<name>.enabled` in `actions_monitor.json` switches one on or off; without it `sentinel.enabled` decides, as always, and where both say something the new block wins.
- **`SentinelCI`** (`sentinel_ci.py`): the sentinel of always behind that contract. It holds the old `Sentinel` and does not change how it decides: the same rule of red (the last completed run of each workflow on the default branch), the same files, the same loop, the same snapshot.
- Tests for every change of this release: the contract, the registry and its switches, the CI sentinel and its alerts in two languages, that the lite edition loads none of it, the side panel, and the sixteen themes (that each one defines every variable and that the text, the small grey text, the accent and the four status colours read at 4.5:1 on its page and its panels).

### Changed

- The theme is chosen from a list in Settings > This browser (it was a button that went round auto, light and dark); a theme saved by an earlier version is still understood.
- The colour of a badge, a bar and a notice that was white on red, amber or green is now the one that reads on that colour in the theme in use.
- The sentinel is started through the registry; `SENTINEL["obj"]` is still the CI sentinel, so everything that asked it something keeps working. The events, the files and the endpoints are the same.

### Fixed

- A test of 1.7.0 read the output of `tasklist` in the wrong code page and could fail on a Windows with another language.
- **A refusal could be lost on the way** (all editions): a POST that the monitor refused before reading its body (a missing token, a body too big) closed the connection with data still unread, and Windows, sometimes Linux, answered with a reset: the client saw a broken connection instead of the 403 it was owed. The monitor now reads and drops what is left of a body (up to 1 MB, for at most 2 seconds) after it has answered, so the answer always arrives. The refusal itself, its code and its text are the same. A test sends the headers, waits and sends the body, and fails without this.

## [1.7.0]

Several accounts in the complete edition, each one a monitor of its own, and a page that knows about them. The lite edition is unchanged: one account, and it does not even show the new options.

### Added

- **Several accounts** (complete edition only). A folder `accounts/<id>/` per account (a person or an organisation) with its own `actions_monitor.json`, its own cache, events, analytics, sentinel state and logs; `accounts/global.json` is optional (`default_account`, `enabled_accounts`) and `MONITOR_ACCOUNTS_DIR` moves the folder. The id is lower case letters, digits, `_` and `-` (up to 40), so it is always a safe folder name. Without an `accounts/` folder nothing changes: one account, its files next to the code.
- **A supervisor** (`accounts_supervisor.py`): with an `accounts/` folder, `python actions_monitor.py` starts one small process on the usual port that runs one monitor per account (`account_child.py`), each one on its own port of `127.0.0.1`. A crash, a slow answer or a rate limit of one account never touches another; a dead account is started again with a growing wait (2, 5, 15, 30, 60, then 120 seconds) and the summary says it is down meanwhile. It reads nothing from GitHub and writes nothing; stopping it ends every process it started, also on Windows, where the interpreter of a virtual environment is a launcher with a child of its own.
- **The API of the accounts**: `GET /api/accounts` (the summary), `GET /api/accounts/<id>/status`, and every other `/api/` request goes to the account named with `?account=<id>` or the header `X-Account-Id` (the default account without one; an unknown account is a 404). The access rules are the ones of a single monitor: the same host and origin check and the same access token in the network mode, and the one-use token of a change is asked from the same account the change goes to.
- **One webhook for all of them**: `POST /api/webhook` is a single address for the installation; the supervisor reads only the owner in `repository.full_name` and passes the event untouched to the account whose `github_owner` is that owner, which verifies the signature with its own secret. An owner nobody watches is answered and ignored; `?account=<id>` chooses the account yourself.
- **`--accounts`, `--account <id>` and `--migrate-accounts [--apply]`**: list the accounts, run only one as an ordinary monitor, and move the old layout into `accounts/default/`. The migration is a dry run unless `--apply`, never moves or deletes the originals, leaves a marker, refuses a second run so two states never mix, and does not touch the files of the lite edition.
- **The page with several accounts**: a switcher of accounts under the header, an entry **All accounts** with one card per account (state, repositories, running, failing) that opens any of them, and the same page for each account. Every window keeps its own account and view, read from the address and not from one setting that another window would overwrite.
- **Views by address** (`?view=now|alerts|charts|repos|settings|live` and `?chrome=0`, a screen without header buttons, tabs or filters for a wall or a second monitor): one monitor serves every window, so the allowance is not spent twice. The **Live** view shows the last events GitHub sent, the state of the webhook receiver (on or off, how many deliveries were accepted, ignored, repeated or refused, whether the secret is long enough, never the secret) and a selector of the working mode. `GET /api/live-status` is its source.
- `tools/demo_accounts.py`: the supervisor with three invented accounts for the pictures, and the guide `ACCOUNTS.md` in eight languages.
- Tests for every change of this release (the suite grew from 866 to 914): the ids, the folders, the migration, the supervisor and its API with a stand-in for the monitor of an account (a dead account, the growing wait, switching an account off and on, stopping everything, one free port each), the routing of the webhook, the token of the right account, what the lite edition never loads, and that every state file of an account lands in its own folder.

### Changed

- The state files of a monitor that is one account of several (the update check, the welcome, the organisations, the counter of swallowed failures) live in its folder through `state_dir()`; a single monitor keeps them next to the code, as always.
- The pictures of the README are taken again and the README in eight languages shows the accounts.

### Security

- The supervisor and the accounts listen on `127.0.0.1` only unless the network mode is on, exactly like a single monitor. The webhook has no Host check and no access token (a tunnel changes the host) and its proof is still the HMAC of GitHub; a cookie of the session is never passed on to an account.
- The page of the supervisor embeds the list of account ids and nothing else; no secret reaches it and none reaches the summary.

### Fixed

- The Live view of 1.6.8 had no state of the receiver: with the webhook off or with a secret shorter than 32 characters it said nothing, and now it says which.


## [1.6.8]

The HTTPS proxy of 1.6.7 is now checked against a real proxy, the pictures are taken again, and the history of changes is translated back to 1.6.3.

### Added

- `python tools/manual_check_live.py proxy HOST [PORT] [CONNECT]`: checks, through your real HTTPS proxy on port 443, that the page is let in (the session opens with the access token in the body and the cookie comes back `Secure` and `HttpOnly`) and that three requests stay refused (the other scheme, another host name, the name with a port). It reads the access token from `MONITOR_ACCESS_TOKEN`, never prints it, and says what to put in nginx or Caddy when it is run without arguments.
- `tools/demo_monitor.py --network` shows the page as it looks in the network mode (the persistent red bar, and in Settings the warning for every interface and the new proxy name) so that it can be photographed; the demo still listens on `127.0.0.1` only. `tools/make_screenshots.py` takes two new pictures with it: `web_network_now` and `web_network_settings`.
- Tests that run the whole chain: a client over real TLS, a reverse proxy that ends the TLS and forwards `Host` and `Origin` without a port, and the real monitor behind it. They check that a change made from the page reaches the settings, that the same request is refused without `listen.proxy_public_host`, that a wrong scheme, name or port stays refused, that the session opens and the cookie is `Secure`, and that the check by hand agrees with the proxy and never prints the token (the suite grew from 858 to 866).

### Changed

- The history of changes (Help > Changelog) is translated in the other seven languages for 1.6.8 to 1.6.3 (1.6.7 and 1.6.5 already were); the entries before 1.6.3 keep the English text under a translated notice.
- The pictures of the README are taken again, 76 of them, and the README in eight languages shows the Advanced sub-tab of Settings and the two pictures of the network mode.
- `docs/MIGRATING.md` has a block from 1.6.7 to 1.6.8, and the roadmap in eight languages lists what is left: the older entries of the changelog and the checks that need your own services.

### Fixed

- The changelog of 1.6.7 said that only 1.6.7 and 1.6.5 were translated and that the proxy was checked only with the guard; this version translates the rest back to 1.6.3 and checks the proxy end to end, as above.


## [1.6.7]

An HTTPS proxy on the default port 443 now works with the network mode, and more of the history of changes is translated.

### Added

- `listen.proxy_public_host` (Settings > Advanced > Network, empty by default): the public host name of an HTTPS proxy on the default port 443 that forwards `Host` and `Origin` without a port. Until now the guard compared both with the port of the monitor, so such a proxy was refused; that one name is now accepted as it is. It only counts while the network mode is on and the session is HTTPS (direct TLS or `listen.secure_cookie`), it must be a plain host name (a port, a path, a user, a space or an IPv6 literal make it empty), like every setting the schema marks `secure` it can only be changed from the computer itself, and its label and help are in eight languages.
- Tests for every change of this release (the suite grew from 843 to 858 and the new file checks the guard, the value, the schema and the texts).

### Security

- The exception of the guard is as narrow as it can be: only that one name is accepted without a port, never another host without a port, never under plain HTTP, and the `Origin` must carry the same name with the scheme `https` (another scheme, a port, a path, a user or a different host are still refused). The proxy name never appears in the public state of the guard.

### Changed

- The history of changes (Help > Changelog) is translated in the other seven languages for 1.6.7 and 1.6.5 (1.6.6 already was); the older entries keep the English text under a translated notice and will follow, newest first.
- `docs/ADVANCED.md` (eight languages) explains the proxy on the default port instead of saying it is not supported, `docs/MIGRATING.md` has a block from 1.6.6 to 1.6.7, and the guide of the settings and the index of the Help are regenerated.


## [1.6.6]

Corrections to the network mode and to `act`, the pending items of 1.6.5, and the history of changes in eight languages.

### Added

- A persistent red bar at the top of Settings when the network mode listens on every interface (`listen.host` = `0.0.0.0`), in eight languages. Until now only `--doctor` said it.
- `POST /api/access` with `{"token": "..."}`: opens the session of the network mode with the access token in the body, so it never sits in an address bar, a history or a log. Same checks as every request (host, origin, lock-out after wrong tokens, constant-time comparison); the cookie comes back `HttpOnly`, `SameSite=Strict` and, over HTTPS, `Secure`. The `?access=` address of 1.6.5 keeps working.
- A counter of the failures the monitor swallows on purpose (`degraded.py`): a structured line on the console for each one, a count by origin kept in `degraded.json` next to the monitor, the new `--doctor` check `degraded` and a "Swallowed failures" line in the About panel. The behaviour does not change: they still never stop the monitor.
- The history of changes (Help > Changelog) now has a translation file per language, `docs/CHANGELOG_<lang>.md`, with the same versions and sections as the English source; `tools/make_help_index.py --check` and a test fail when a version of the source is missing in a translation. Entries not yet translated say so, in the language of the reader.
- Tests for every change of this release (the suite grew from 811 to 843).

### Fixed

- **Network mode over HTTPS was unusable from the page.** The same-origin guard accepted only an `http://` origin, so with direct TLS or an HTTPS proxy (`listen.secure_cookie`) the browser's own `Origin: https://...` was refused and every change (settings, confirmations) answered 403. The guard now builds the allowed origin from the scheme of the session (https or http, never both), compares host and port exactly and refuses a malformed origin. Tested with a real TLS server and a certificate the test makes.
- `act`: Stop now frees the run, so the next start is no longer `busy` for ever when the process does not end; a worker that returns late never touches a newer run; the output pipe and the timer are closed in every case (normal end, time limit, Stop, unexpected error) and the suite no longer emits `ResourceWarning`.
- `tools/make_screenshots.py` could end without a word: the browser runs without captured pipes and with a time limit, a missing browser or a demo that does not start is said, `MONITOR_BROWSER` names a browser by hand, and the exit code is 1 when a picture was not made.

### Security

- In network mode every setting that the schema marks `secure` can only be changed from the computer itself, not only the four families listed before (`listen.`, `github_token.`, `act.`, `github_actions.`): also the webhook, the AI actions, notifications, OpenTelemetry, the mirror, runners, outputs and the rest. The list is read from the schema, so a new secure setting is covered without anyone remembering it; a test walks all of them.

### Changed

- The pictures of About, Help, Now, Basic and Advanced in the README and the guides are taken again.
- `docs/ADVANCED.md` (eight languages): HTTPS with your certificate or behind a proxy, the origin rule, the session opened by POST and the warning bar.

## [1.6.5]

A release of integrity and security: no large new feature. What cannot be proven is no longer taken as safe.

### Added

- New settings, all with a conservative default: `dispatch.required_ci` (and, in the file, `dispatch.required_ci_repos` and `dispatch.required_ci_profiles`), `act.allow_symlinks`, `listen.tls_cert_file`, `listen.tls_key_file`, `listen.secure_cookie`, `listen.max_failed_attempts`, `webhook.replay_seconds`, `webhook.max_per_minute`; the guide of the settings is regenerated.
- `finalize --accept-legacy` for batches written by an older version, and the `--doctor` checks `risks` and `backend` (eight languages).
- Tests for every change of this release (the suite grew from 729 to more than 800).

### Security

- **A green commit needs the required CI.** `gha_dispatch_all.py` marks a commit green only when the required workflow files succeeded on it (`ci.yml` by default; `dispatch.required_ci`, `dispatch.required_ci_repos`, `dispatch.required_ci_profiles`), nothing failed, timed out or waits for an approval (`action_required` blocks like a failure), nothing is still running and the list of runs is complete (it reads up to five pages; a longer list is not green).
- **A failed `git fetch` stops the dispatch** of that repository, git commands have a time limit and the commit ids are checked; an old `origin/main` is never taken as proof.
- **The catalogue cannot leave its folder or change the dispatch.** `tool` must be a plain file name that sits in the tools folder (links that leave it are refused too); `extra` may only hold `-f key=value` workflow inputs (never `dry_run`, `ref`, `-R`, `--ref`); `finalize_flags` only long flags; the arguments of `gh workflow run` are built from the validated pieces and checked again when the batch fires.
- **Old batches are not signed blindly.** `finalize` offers for signing only a run whose batch recorded that it was built on the commit that was checked. A batch written by an older version is `needs_review`; `finalize --accept-legacy` reads the run again from GitHub, accepts it only if its commit is the recorded one, warns, and asks for the word LEGACY before each signature.
- **`act` stays inside the workspace.** The clone is resolved and must be a real folder of the workspace (a link, a `..` name or a `.github` that points elsewhere is refused; `act.allow_symlinks` allows a link to a clone). The time limit and Stop end the whole tree of processes the run started (a process group on Linux and macOS, `taskkill /T` on its own PID on Windows) and remove the `act-` containers that run created.
- **Network mode**: HTTPS served directly with your own certificate and key (`listen.tls_cert_file`, `listen.tls_key_file`; TLS 1.2 or newer; the monitor does not start on plain HTTP if they cannot be used) or the `Secure` cookie behind an HTTPS proxy (`listen.secure_cookie`); the access token leaves the address bar at once (redirect, no `Referer`); an address that sends too many wrong tokens is refused for five minutes (`listen.max_failed_attempts`); the address of the page is the one the server listens on; only IPv4 addresses are accepted, in the settings and in the guard alike; the console says when the connection is plain HTTP.
- **Webhook**: every delivery needs its `X-GitHub-Delivery` id and a repeated one is ignored for `webhook.replay_seconds`; a repository can cause at most `webhook.max_per_minute` accepted events a minute; the owner in `full_name` must be the watched account; one address is limited to 120 requests a minute in the network mode; an accepted event drops the stored conditional reads of that repository and marks it for the next cycle; a signature header with unusual characters is a plain refusal.
- **MCP server**: a message of the wrong shape (parameters, arguments, id, method) gets an error for that message only, an unexpected defect in a tool is an internal error that does not end the server, and a line over 64 KB is refused.
- **The stored GitHub token is given to `gh` only.** It is no longer put in the environment of the monitor, so `act`, your notification command and every other child cannot inherit it.
- **A GET never writes.** The copy of the daily report in the audit folder is a POST with the one-use token (`/api/sentinel/parte/save`); `?save=1` on the GET is gone.
- `--doctor` names dangerous combinations (network mode on every interface, AI actions that execute while the network mode is on, `act` while the network mode is on, the token in a plain file) and shows where the token is kept, never the token.

### Fixed

- `max_per_hour` of the notifications now limits messages (one unit per channel, booked at once under one lock) and not events; a channel that cannot send books nothing.
- Two saves of the settings at the same time no longer lose one of them (a lock in the process and a lock file).
- The signing queue export says why it did not write (a refused drive or network path, a folder instead of a file, the error of the system) instead of a bare refusal.
- The secondary-limit wait and the retry after a timeout carry a random jitter.
- The test that unpacks the zip in a clean folder is no longer part of the ordinary suite: `make_release.py` runs the suite once with a time limit, then the clean install as its own stage, and shows stdout and stderr when either fails.

### Changed

- The guides of notifications, webhook, advanced features, outputs, AI alerts and migration say all of this in the eight languages; `docs/MIGRATING.md` has a block from 1.6.4 to 1.6.5.

## [1.6.4]

### Added

- **Alerts for AIs**: the monitor writes a local, read-only feed (`ai_alerts.jsonl`, one line per event, and `ALERTS_BRIEF.md`, rewritten at every cycle, 2 KB by default) with one alert per red workflow: stable id, severity, probable cause told apart as real or transient with editable rules, suggested action, and a state (open, acknowledged, resolved by itself when the workflow turns green). Everything goes through a cleaner of tokens, keys, e-mail addresses, IP addresses and home folders. `GET /api/ai/brief` and `GET /api/ai/alerts`, an optional read-only MCP server (`mcp_server.py`: `get_alerts`, `get_red_repos`, `get_run_failure`, `get_quota`, and `ack_alert` with `--allow-ack`), a notification when a new REAL alert appears, an optional hook to an address on this computer (off), and an optional `ai_hint` in `ci_red.json`. New guide `AI_ALERTS.md` in eight languages.
- **Opt-in features, all off by default, each with its switch in Settings > Advanced** and tests that prove they refuse without the switch, the confirmation or the token: the network mode (a private address, an access token for every request, accepted host names, a persistent red bar, exposure keys changeable only from the computer itself); a GitHub token kept by the monitor in the secure store of the system (Windows DPAPI, macOS Keychain, Linux Secret Service, else a file with permissions 600) and never in a setting, a log or an answer, with a delete button; actions on GitHub (run again, cancel, close, merge), each confirmed on its own after showing exactly what will be sent; running a workflow here with `act` from a closed list, with no real secrets; a local mirror of artifacts; self-hosted runners (idle, busy, offline, optional disk and load); OpenTelemetry export (traces and metrics, OTLP/HTTP JSON); the organisations of the login; FinOps by job labels (Linux, Windows, macOS and larger runners), the price of the minutes above the included ones, Codespaces, Packages and storage from the billing report. New guide `ADVANCED.md` in eight languages, and `tools/manual_check_live.py` to try the real services by hand.
- `--doctor --json`; the doctor also reports busy ports, the allowance left, whether you have your own targets file, the one-use token and the exposure. The README of the package starts with the choice of launcher (complete, lite, batch, terminal, doctor, demo).
- The terminal application edits the simple settings (not the security ones) and has an AI tab; a persistent banner for settings that need a restart survives a reload; the header shows when the sentinel's A10 is paused for quota and how much of the minutes budget is used; the welcome is remembered by the server too.
- `redrule.py` ignores the dynamic runs of dependency updates like the dashboard does, and the shared cases of the rule are now a test fixture.

### Changed

- **The Help is complete in eight languages**: the roadmap, contributing, security and support documents are translated, the fixed labels of the changelog are translated and its entries are marked as English only, with a translated notice; `tools/make_help_index.py --check` and a test fail when a topic lacks a language. A search shows at most 30 hits and a huge document no longer holds the server thread.
- The red tile counts workflows in both editions and says in how many repositories. The lite edition inherits the refresh rhythm of the complete one at its first start.
- A passing failure (a TLS hiccup, a 5xx) is retried with an exponential backoff and is shown as an error only after three cycles in a row; the last picture stays.
- The terminal view of the lite edition no longer asks for the sentinel; the lite edition never loads the sentinel module (the local guard moved to `localguard.py`).
- `--demo` redirects every file it could write (logs, caches, event feed, history, welcome) to its temporary folder.

### Security

- With `updates.check` off or `airgapped` on, the monitor makes no network request at all for the update notice (tested).
- Verified against the real GitHub API: the scopes of the token are read correctly, the organisations list and the billing report degrade silently (a login without the `user` scope gets "not found" and the monitor keeps the estimate).

## [1.6.3]

### Added

- **About panel** (the **i** button of the header, in both editions): version, edition, author, licence, Python and system, links (repository, releases, changelog, documentation, issues), the files it uses (read only), the health of the server, the credits of the libraries and a button that copies the information for support (no secret, no token, the home folder shown as `~`). `GET /api/about`, and `--about` in the console.
- **Help panel** (the **?** button, the key `?`, and a "?" in the tab bar that opens the page of the tab you are on): the whole documentation (README, quick start, every guide, roadmap, changelog, contributing, security) as an index you can search, in the language of the page and in English where a document is not translated, served by the local server without Internet. It is built from the real documents by `tools/make_help_index.py` (`--check` in the CI), so no text is written twice; the markdown is rendered safely (everything escaped, no image loaded, only `http(s)` links and links to other documents). In the console: `--help-topics [TOPIC]` and `--help-search WORDS`.
- **Notice of a newer version**: a discreet badge in the header, a line in About, in the console and in `--doctor` when a newer release is published. One read-only request a day to the public releases page, through the same client as everything else (conditional read), never downloads or installs anything, sends nothing about you, ignores pre-releases, compares versions as numbers (1.6.10 is newer than 1.6.9), is silent offline and is off with `updates.check` or in an air-gapped installation (`airgapped`).
- **Settings > Basic**, the first tab: open the browser at start, the update notice, the air-gapped switch, the one-use token, the discovery options, the lifecycle rules, and the plan and quotas. Under it, what the monitor found in the account (owner, repositories found, watched, left out), the news and the suggested groups.
- **`--doctor`**: Python, `gh`, the login, the allowance, the network, the write permission of the folder, a free port, and the optional Docker, Rich and Textual; each failure comes with the exact command that fixes it, in eight languages.
- **`--demo`**: the page with invented data, with no `gh`, no login and no network; nothing of yours is read or written.
- **A welcome of three steps** the first time the page is opened (what it does, what it found in your account, where to go next).
- **Automatic discovery**: events for a new, vanished, archived or unarchived repository (console, Settings > Basic and, in the complete edition, the notifications); a suggested group when three or more unclassified repositories share a prefix, added only after your confirmation and with a copy of the file; lifecycle rules to leave out forks, empty and private repositories; an optional automatic refresh frequency that follows the real activity inside the call budget.
- **A one-use token** (`session_guard`, on by default) that the page asks for right before it saves a setting or confirms an action, and a **restart bar** on every tab while a saved setting waits for a restart.
- **Levels of the workflow linter** (information, warning, error) as filters in the page, and `Scripts` in the terminal application.
- **Quotas and plans for every kind of account**: your plan in Settings > Basic; the figures (included minutes as money, rates per system, concurrency, limits of a job and of a run, allowances of the API) live in `quotas.json`, which you can edit without a new version; billable minutes apart from clock minutes (public repositories cost none, private ones use the multiplier of Windows or macOS), a monthly projection marked as an estimate, a warning once per month at 75 % and 90 % of the included minutes through the notifications, jobs running and queued against the limit of the plan, jobs near the 6-hour limit and the kind of token read from GitHub's own headers (with the advice to log in when only 60 calls an hour are left). The real usage comes only from the optional, read-only billing report (`quota.billing_api`, off by default, silent on a 403 or 404). `GET /api/quota`.
- **Working modes: normal, fast and turbo** (`modes.py`, guide `MODES`): a selector with a gauge icon in the header and `--mode` / `--mode-minutes` in the console, in both editions. The presets live in the `modes` block of the configuration; before it starts the page shows the worst-case calls an hour, what the conditional reads usually save and how long the allowance left would last; it goes back to normal by itself when the time is up or when the allowance falls under `min_rate_remaining`, with a notice; without a login (60 calls an hour) fast and turbo are refused with the reason; it needs the one-use token, lives in memory and the console banner names it. `GET` and `POST /api/mode`.
- **After a secondary rate limit** the monitor waits at least a minute and then doubles the wait up to five minutes instead of retrying quickly.
- **The interactive terminal application** `tui_textual.py` (optional, `pip install textual`): tabs Summary, Repositories, Builds, Performance, Scripts and Settings (the basic switches), a filter, the levels of the linter, refresh, open in the browser, About and Help; `--lite` shows the lite tabs. The simple Rich view (`tui.py`, `--once`) stays and also has `--about` and `--help-topics`.
- **The edition is clear at a glance**: a start-up banner (`GitHub Actions Monitor LITE 1.6.3 · port 8766 · actions_monitor_lite.json · no sentinel · http://127.0.0.1:8766/`, or COMPLETE · port 8765 · sentinel on), the title of the window of the console and of the terminal, the tag `[LITE]` / `[COMPLETE]` in the status lines, in `--doctor` and in the terminal views, and the same title in the launchers.
- New guides in eight languages: **The sentinel and its checks A1-A13** (what it is, how it starts, the files it writes, how to read it, the exact rule, the setting and the action of each check and the twenty-five checks of A10; a test keeps the guide and the code in agreement), **Quotas and plans** and **Your first five minutes** (`FIRST_STEPS`); the migration guide has a block from 1.5.x to 1.6.x and the README has a chooser between the two editions.
- Tests for all of it (the semantic versions, the notice offline, switched off and air-gapped, the safe markdown, the index, the one-use token, discovery, `--doctor`, the quotas for public and private repositories, Windows and macOS, no token, Enterprise and a 403 of the billing report, the banner and the launchers).

### Changed

- The Settings page starts with the **Basic** tab; the guide `SETTINGS` is generated with it.
- The monitor lists the repositories of the account with their kind (archived, fork, private, empty); an older `gh` without those fields falls back to the plain list.

### Security

- Nothing new writes to GitHub. The update notice, the billing report and the discovery are read only and switchable; none of them sends data about you. The Help and About panels are served from this computer and the support text carries no secret.
- Writing a setting, confirming an action of the AI assistant and adding a suggested group need the one-use token of the page.

## [1.6.2]

### Added

- **A catch-all group** `rest` ("Everything else", prefix `*`) at the end of the example catalogue of ecosystems, so a new installation leaves no repository out.
- **An automatic group "Unclassified"** for the repositories that no group claims (setting `show_unclassified`, on by default; an explicit choice of ecosystems is respected).
- **A warning when the filter hides repositories**: a banner (complete and lite) says "your ecosystem filter hides N of the M repositories of the account" and names them.
- **The lite edition starts with what you already set up**: on its first start `actions_monitor_lite.json` copies from `actions_monitor.json` (when it exists) the account, the repositories and ecosystems to watch, the catalogue files, the exclusions, the language and the reading depth, and says so on the console. Without such a file its template watches all the ecosystems.
- **`tui.py --lite`** (or `MONITOR_MODE=lite`) reads the lite edition on port 8766.
- **`redrule.py`**, the single small rule of "red on main", used by the sentinel and by the lite edition (which marks the figure as approximate because it guesses the default branch).
- **`ghamon_etag_invalid_total`**, the count of damaged cache entries, in `/metrics`.
- Tests: header-data parity between the complete and the lite edition, the catch-all group, the hidden-repository count, the lite start, the webhook hot mark, the damaged cache entry, and that importing the monitor or the sentinel never loads Rich.
- Guides `LITE` and `SETTINGS` (eight languages) updated.

### Changed

- **Both editions show the same header figures**: runs, failures, successes, compute minutes, running and queued are counted once, by the server, over the same 24 hours with each run counted once; the lite edition reads as deep as the complete one. The lite edition hides the "unsigned" tile.
- **A webhook event marks the repository as hot**, so the next cycle reads it again whatever the event said.
- The GitHub allowance tile is painted from the first moment, while the repositories are still loading.

### Fixed

- A new installation with the example catalogue saw almost no repository; the lite edition detected one repository out of 129 because its template filtered by ecosystem.
- **A damaged cache entry is only a miss**: it is thrown away and the endpoint is read again in full.
- "Red on main" and the compute minutes differed between the two editions.

### Security

- The lite edition never inherits the sentinel, the AI, the webhook, the outputs or the notifications, nor any secret, from the complete one; it writes neither `ci_red.json` nor a signing queue.

## [1.6.1]

### Added

- **The lite edition**, a second and simpler product in the same package: `MONITOR_LITE_GITHUB_ACTIONS.bat` / `.sh` / `.command` or `--lite` / `MONITOR_MODE=lite`. What is running and what failed, failures and successes of 24 hours, red on main, the history and the basic charts; a short Settings page (account, repositories and ecosystems, refresh, language, theme); its own file `actions_monitor_lite.json`, its own state files with the suffix `_lite` and port 8766, so both can run side by side.
- **`act` command in the repository panel**: for each workflow of the repository, `act -W .github/workflows/FILE -j JOB` ready to copy. The monitor never runs it (running it exists only as a confirmed action of the AI assistant).
- **A container example** (`deploy/Dockerfile`) that the CI builds.
- Guide `LITE` in eight languages, a Lite-versus-Complete table in every README and new screenshots of both editions in light and dark.
- The roadmap lists what did not fit: local mirror of artifacts, FinOps of the minutes, self-hosted runner status and an OTLP export, and the notes of the terminal view (why it uses Rich).

### Security

- The lite edition has no sentinel: it is not imported and its endpoints answer 404.

## [1.6.0]

### Added

- **Conditional reads (ETag)**: every read of the run lists sends `If-None-Match`; a `304 Not Modified` answer costs no quota. The header and `ghamon_etag_saved_total` count the reads saved; `cache.etag.*` in the Settings tab.
- **Resilience to network cuts**: when every read of a cycle fails with a connection problem the page keeps the last picture with an offline banner and resumes by itself; `offline` and `online` events (they can be notified) and `ghamon_offline`.
- **Analytics** (section A12 of the Sentinel tab, `/api/analytics`, `/metrics`, the Grafana JSON source): p50 / p95 of the duration of each workflow, of the queue time of its jobs and of each step; workflows that got slower than usual; **flaky** workflows (failed, then passed on the same commit, or needed another attempt), only a label that never changes what counts as red.
- **Incoming webhook in real time**: a signed `workflow_run` event updates the run list of its repository without reading GitHub, `workflow_job` events bring queue and step times; only short validated fields are kept (`/api/live-events`).
- **Workflow linter**: `lint_workflows.py` (actions not pinned by SHA, missing or broad permissions, secrets in clear text, injection, `pull_request_target` with the PR's code), rules switchable with their own severity, a line in the daily report and the section A13. A comment `# monitor-lint: ignore RULE reason` or the setting `lint.ignore` silences a finding.
- **Notifications** (off by default): Telegram, Discord, Slack, Matrix, MQTT and a local HTTP address, a limit per hour, a test button and a documented adapter contract (`monitor/docs/schemas/notification_event.schema.json`).
- **AI assistant**: new providers `anthropic` (Messages API, the model is yours to choose) and `copilot` (`gh copilot` with your own login, text only, no tools); new tasks (daily report, release notes, a question about a repository); settings for the kinds of event, the repositories, the language and the limits, a test button and the use of the day. A closed list of actions (`gh run rerun`, `gh issue close`, `act`), only PROPOSED by default.
- **The figures of the header are tiles** with an icon, a big figure and a small label, coloured by state, with a tooltip, a click that leads to the tab, counting figures and a skeleton that shows the last known values at once; the second line (repositories, hot, mode, reads saved, GitHub allowance with a bar and a live countdown, connection, last update and the loading progress) is made of tiles too.
- **Terminal view**: `tui.py` draws a live grid in the console (read-only, optional, needs the package `rich`; the monitor and its tests need no package).
- **For servers and bigger accounts**: `GET /api/health`, `GH_HOST` for GitHub Enterprise Server (every link of the page follows it), `discover_limit`, minimum permissions per feature, and a guide to run it as a service (systemd, launchd, a scheduled task, a container) and behind a reverse proxy.
- Published JSON schemas of `ci_red.json`, of the public export and of the notification event (`monitor/docs/schemas`), and a public roadmap (`docs/ROADMAP.md`).
- New guides in eight languages: notifications, the AI assistant, analytics, console tools and deployment; the webhook guide covers the real-time events. All screenshots were redone (light and dark, console tools included) with `tools/make_screenshots.py` and invented data.

### Changed

- **Settings**: new sub-tabs for reads and cache, notifications, analytics, the linter and the terminal view; the AI and webhook sub-tabs have all their options.

### Fixed

- **The linter no longer cries wolf on placeholders**: a value that looks like a secret is classified (a known token format or a long high-entropy string is serious, a readable filler such as `placeholder` or `changeme` is only information, anything else a warning; references and empty values are no finding) and its value is never printed or stored.
- **A browser that closes or reloads its tab while the page is loading no longer prints a traceback** (`ConnectionAbortedError`, `ConnectionResetError`, `BrokenPipeError`): they are counted in `ghamon_client_disconnects_total`; a real error is still shown.

### Security

- The incoming webhook stays off by default, on `127.0.0.1`, with a mandatory HMAC.
- Notification secrets live only in environment variables; hosts are fixed; notifications never write to GitHub.
- AI actions: running one needs its own switch and a confirmation of the full command each time, only on targets the monitor already watches, with a limit per hour, a local log and a lock after two failures in a row.

## [1.5.2]

### Added

- **The Settings tab is organised in sub-tabs**, ordered from the common to the advanced (This browser, General, Refresh and limits, Sentinel, Surface checks A10, Readiness A11, Folders and files, Outputs, External AI, Incoming webhook). Inside a sub-tab the settings sit in titled blocks whose first field is the main switch (the rest of the block dims while it is off). Every field shows its unit and range, a badge (needs a restart / applies now), a badge for the safety options that start in their conservative state, and one line of help. A search box filters all the sub-tabs, each sub-tab counts its unsaved changes, Save and Discard stay visible, the arrow keys, Home and End move between the tabs and the last sub-tab used is remembered by the browser.
- **Every setting of the configuration file is in the page now**: the A10 checks (a switch per check and its limits), the weights of the ecosystem health score, the sources of the pinned versions, the Actions-minutes ceilings, the required files, the audit file patterns, the hot period of the sentinel, the unknown-sample rule of A2, the candidate prefixes, the list of repositories and the switch of the incoming webhook.
- **Signing queue by trust**: each row says `verified`, `unknown` or `failed`; the Sentinel tab has a Signature filter with the count of each kind; `read_report.py --sign-trust` filters the console list and the export, and the exported rows carry `trust`.
- **Readiness chips in the header**: one coloured chip per ecosystem with its health score.
- **A minimal Grafana board** (`red_by_ecosystem.json`) and a test that checks every metric of both boards against what `/metrics` serves.
- New guide `WEBHOOK` (refresh-only mode) and a commented example of the pin sources, in eight languages.
- `tools/make_settings_doc.py` writes the settings table of the guides from the schema and the texts of the page, and the CI checks it.

### Changed

- **The daily report groups the issue-closing suggestions** in one line per repository (the monitor still closes nothing).
- **The contract of the profile dashboard** is documented and checked by a test (`/api/outputs/dashboard.json` is exactly the document of `ci_red.json`; the public export never carries the signing side).

### Security

- The shared secret of the webhook is never shown in the page: it only says whether it is defined.

## [1.5.1]

### Added

- **The settings page can set the external AI of the sentinel** (group "External AI for the sentinel"): `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (only this computer), `ai.base_url` (https only), `ai.api_key_env` and `ai.daily_limit`. Off by default; an outside service receives data of your repositories.
- **`migrate_state.py`**: brings the files written before 1.5.0 to the new names (events, report history, release candidates, batch records, the `report_history_days` setting). A dry run by default; `--apply` copies and keeps the old files, `--move` renames them; nothing that exists is overwritten. One-page guide in `docs/MIGRATING.md`, in eight languages.
- **`--init-catalog`** creates editable `ecosystems.json`, `targets.json` and `profiles.json` from the examples.
- A test makes sure no document sends the reader to a command that was renamed in 1.5.0 (only the tables of old and new names and the migration guides may name them).
- The version in every README.

### Changed

- **First start without catalogue files of your own**: the console says the example files are in use.
- Python 3.11 or newer is the documented minimum (tested on 3.11 and 3.13 on Windows, Linux and macOS).

### Security

- Only the NAME of the environment variable that holds the AI key can be set: the key itself is never shown or saved.

## [1.5.0]

**Update notice (read this first).** Several files and settings have English names now. Nothing is lost: the old names are still READ where a file written by an earlier version may exist, and the new names are the only ones written.

| Before 1.5.0 | From 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py` | `events.py` |
| `parte_history.py` | `report_history.py` |
| `LOTE_GITHUB_ACTIONS.bat` / `.sh` / `.command` | `BATCH_GITHUB_ACTIONS.bat` / `.sh` / `.command` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` (copy or rename them to keep the history of events) |
| `PARTE_CENTINELA_DIA_<day>.txt/.json` (report history) | `SENTINEL_REPORT_DAY_<day>.txt/.json` (the old ones are still read) |
| `PARTE_CENTINELA_<time>.txt` (saved report) | `SENTINEL_REPORT_<time>.txt` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_<time>.json` | `<signed_dir>/batches/batch_<time>.json` (the old records are still read) |
| `parte_history_days` (setting) | `report_history_days` (the old name is still read) |
| `monitor_y_centinela.zip` and folder | `github_actions_monitor.zip` and folder; `LEEME_CORREO.txt` is `README_MAIL.txt` |
| A8 looked for `RECONCILIACION_TOTAL_AUDITORIAS_*.txt`, `MAPA_DE_RONDAS_*` | the names are `sentinel.audit_files` (neutral defaults `RECONCILIATION_TOTAL_*.txt`, `ROUNDS_MAP_2*.txt`, `ROUNDS_MAP_EXTRA_*.txt`); set your own there |
| `ci_red.json`, its schema and the `--export-status` files | unchanged (they are a contract) |

- **English by default.** The language of the system no longer decides: the tools start in English until you choose another one in the Settings tab, with `language` in `actions_monitor.json`, `MONITOR_LANG` or `--lang`.
- **A clean, neutral package.** `ecosystems.json`, `targets.json` and `profiles.json` are no longer part of the package: only the `*.example.json` files travel, and a missing default file falls back to its example. Your own files live anywhere and are named by `ecosystems_file`, `targets_file` and the new `profiles_file`; the folder of your local signing tools is the new `tools_dir`. The tests use their own fixtures (`tests/fixtures`).
- **Settings tab.** A new tab changes the values of `actions_monitor.json` from the page: a whitelist of keys with their type and range, one request refused as a whole when a value is invalid, a copy of the previous file in `config_backups/` before every save (the last ten are kept), an atomic write, only on 127.0.0.1 with the same Host and Origin checks as every other endpoint, JSON only. Tokens, secrets, signature keys and the command of the sentinel are not in the list: they are never shown and never written, and every other key of the file is kept as it was. Each setting says whether it needs a restart. The language selector, the theme and the dense view moved there.
- **Buttons and icons.** Buttons have relief, light up on hover and sink when pressed; the icon buttons are inline SVG with an accessible name and a tooltip in the 8 languages. Colours, type, cards, bars and the ring follow the status dashboard of the profile repository.
- **Life in the charts.** Bars grow in, what is red or running has a discreet pulse, the figures of the header count up, hovering a bar highlights it and gives its text as a tooltip, widths change smoothly; all of it stops with `prefers-reduced-motion`.
- **Outputs for other tools (off by default, 127.0.0.1 only, no new token).** `/metrics` in the Prometheus format (red workflows per ecosystem and repository, red streaks and hours, builds waiting for a signature, A10 paused, allowance left, incomplete snapshot...), `/api/outputs/grafana.json` for the Grafana JSON / Infinity source and `/api/outputs/dashboard.json` (the `ci_red.json` document) for the status dashboard. An importable Grafana dashboard is in `docs/grafana/` and the details in `docs/OUTPUTS.md`.
- **Report:** a line (code `tag_vs_manifest`) when a release tag is ahead of the version of the manifest; the unsigned figure is ordered by the longest wait and says how long it is; the repository panel suggests the `gh issue close` command (never run) for a failure issue whose workflow is green again; the `hil` batch profile is documented in `profiles.example.json`; tests for `finalize` and for `monitor_link`.
- **Docs:** `docs/SETTINGS.md`, `docs/OUTPUTS.md`, README and QUICKSTART in the 8 languages updated, screenshots made with invented repositories.

## [1.4.5]

- **The report says when the snapshot is incomplete:** a line with the stable code `incomplete` (still loading, no local workspace, errors while reading) right after the headline, so nobody acts on a half-read list of red repositories or signing queue.
- **Signing summary:** one line with how many releases wait to be signed (verified / not checked / failed the check) and how many builds are build-only on purpose, so "not signed on purpose" is not confused with "signature missing" (code `sign_summary`).
- **A10 paused for the quota is said in the report** (code `a10_paused`) with the allowance left and needed, and the three knobs that control it.
- Texts in the 8 languages; tests for the three lines.

## [1.4.4]

- **Author and licence are always visible:** the web panel has a footer with the author and the licence, `read_report.py --version` and the new `gha_dispatch_all.py --version` print them under the version, and the monitor prints the same line when it starts. The text is in the 8 languages (`ui.about`); the author and the licence come from `tool_version.py`.
- **Bridge to the dashboard written down:** `docs/CI_RED_BRIDGE.md` says what `ci_red.json` contains (schema 2, `complete`), how to export it and what a reader must check; the monitor still never pushes or commits.
- Tests for the author line in the 8 languages, the footer, both `--version` flags and the start-up line.

## [1.4.3]

- **A workflow that only runs on pull requests no longer makes A2 inconclusive:** `pull_request` and `pull_request_target` join the events whose runs never sit on the default branch (like `workflow_dispatch`, `release` and `workflow_call`), so a workflow such as a contract integration check that only runs on pull requests is not asked for a last run on main. A workflow that also has `push` or `schedule` still counts. Tests for both cases.

## [1.4.2]

- **A2 no longer counts a run in progress or a cancelled one as seen:** when it resolves a hidden workflow, the Sentinel now asks for the last completed runs of that workflow on the default branch (`gh run list -w <file> --branch <default> --status completed -L 10`, read only) and uses the first one with a real conclusion. A cancelled or skipped run (and anything without a conclusion) is ignored, so it can no longer hide an earlier red; a workflow with no completed run with a conclusion on the branch stays inconclusive on its own. Same quota gate, call limit and cache as before.

## [1.4.1]

- **A2 resolves a hidden workflow instead of giving up on the whole repository:** when a repository has a full run sample and a workflow of its clone (one that can run on the default branch) is missing from it, the Sentinel asks GitHub for the last run of THAT workflow on the default branch (`gh run list -w <file> --branch <default> -L 1`, read only). A red answer counts as red in A2; a green one removes the workflow from the inconclusive list; a workflow with no run on the branch stays inconclusive on its own and the panel names it (`repo/file.yml (no run on the default branch)`) instead of only the repository. Without quota (same gate as A10: `min_rate_remaining` x `surface.min_rate_factor`, plus the hourly budget) the workflow stays inconclusive and the panel says why. New options `sentinel.a2_resolve_max_calls_per_tick` (4; 0 = never ask) and `sentinel.a2_resolve_ttl_seconds` (3600, how long an answer is kept; it is also saved in the cache file). The snapshot carries `a2.inconclusive_workflows` (labels) and `a2.inconclusive_details`; `a2.inconclusive` is still the list of repositories. 5 new texts in the 8 languages and a reworded `ui.a2_inconclusive`.

## [1.4.0]

- **New layer A11 "Readiness" (read only, real data only):** a panel of the Sentinel tab, a traffic light in its header and two lines of the report. It is switched with `sentinel.readiness.enabled` and described in `readiness.py`.
  - **Release readiness:** one row per repository with at least `candidate_min_entries` entries in `[Unreleased]` (external ecosystems excluded): CI of the default branch (the single rule of A2) with the commit it ran on, whether the version the clone declares (`*.project.json`, else `pyproject.toml`, else the first CHANGELOG heading) is already above the last release, whether a build exists after that release, whether it is signed (the states of A5), and the next step (`fix the red CI`, `wait for run data`, `bump the version`, `build in Actions`, `sign`, `publish`, `cut and publish`). A green CI over a full run sample that may hide an older workflow says so.
  - **Ecosystem health:** per ecosystem, 100 minus weighted counts of red CI, stuck builds, secrets, serious alerts, other alerts, Dependabot PRs older than `stale_pr_days`, builds waiting for signing and repositories with hygiene problems (`sentinel.readiness.health.weights`); the parts that lower the score are listed. No score is shown (`?`) when fewer than `min_coverage` (0.5) of the repositories of the ecosystem have run data and alerts. The report warns when a score is under `warn_below` (70).
  - **Dependency pins:** repositories that pin an older version than the one of the repository that provides the contract or library. Where the pins live is data (`sentinel.readiness.pins.sources`): a JSON table of pins in the provider (`pin_table`) or lock files in the consumers (`lock_files`, the oldest one found counts). Plain file reads of the local clones, cached `pins.refresh_seconds`; an ecosystem without a configured source is listed as having none, and nothing is guessed. The shipped example has no source.
  - 60 new texts in the 8 languages; `tests/test_readiness.py` (rules, weights, coverage, pins on a temporary tree, the page and the 8 catalogues).
- **`docs/CI_RED_SCHEMA.md`:** says explicitly that the PC publishes neither `ci_red.json` nor `pending_sign` to any repository or dashboard (the signing side is local by decision); a public consumer recomputes the rule from the public runs or uses `read_report.py --export-status`.
- **Quota tuning from the log (`actions_monitor_log.txt`, 3 days, 889 samples):** the shared allowance was under the floor (`min_rate_remaining` 1500) in 11% of the samples since 5 November and under 3000 in 45%; the hourly burn was 3000-5000 calls in most hours and reached the limit in some. In the maintainer's `actions_monitor.json`: `refresh_seconds` 120 -> 180 (the real cycle was a median of 139 s) and `sentinel.surface.min_rate_factor` 2.0 -> 1.5 (the cold calls of A10 are about 260 a day, so they can run above 2250; with 3000 they waited almost half of the time). `max_repos_per_tick` (6) and the daily cold cycle stay: they cost less than 1% of the allowance. The shipped example keeps its neutral defaults.

## [1.3.3]

- **A2 ignores workflows that never run on the default branch:** when deciding whether a full run sample hides a workflow, the files of the clone whose `on:` has no `push`, `pull_request` or `schedule` for the branch (only `workflow_dispatch`, `release`, tag-only `push` without `branches`, or `workflow_call`) are no longer expected in the sample. `on:` is read with the standard library only (string, list, map, and the YAML `true` key); if it cannot be parsed the workflow counts as before. The workflow scan carries the new field `main_triggered` (`true`/`false`/`null`).

## [1.3.2]

- **A2 shows `unknown` instead of green when its sample is full and inconclusive:** a repository whose list of runs is as long as the sample asked for (`runs_per_repo` / `cold_runs_per_repo` of the monitor, which the check did not see before) and whose clone has a workflow file with no run in that sample (or that has no clone) is listed as inconclusive, and A2 is `unknown` unless something is red. New option `sentinel.a2_full_sample_unknown` (default `true`; `false` = only informative as before). The page lists the repositories.
- **`profiles.example.json`:** a neutral batch-profiles template that matches `targets.example.json` and `ecosystems.example.json`. A test (and the release gate) validates it against those catalogues, not the maintainer's, and checks that every profile selects at least one target.
- **Clean-install check in `make_release`:** before anything is left in the output folder the zip is extracted into a new, empty temporary directory and, from there with `python -I`, every member must be present, every module must compile, `read_report.py --version` must run and the whole suite must pass; any gap fails the release.
- **Wording:** README and QUICKSTART in the 8 languages now say that the package writes nothing to GitHub on its own and that only `dispatch --go`, `dispatch --real` and `finalize --execute` (which you run) do.
- **A10 quota:** the share of the sentinel's per-tick call budget that A10 may use is now `sentinel.surface.budget_share` (default `0.5`, as before but configurable); the page shows "A10 paused for quota" with the allowance left and the one needed (`min_rate_remaining` x `min_rate_factor`) while the cold calls wait.

## [1.3.1]

- **A run built on another commit is never offered for signing:** when `dispatch` could only find a recent run of another commit (`sha_matched` false), `finalize` now lists it as not ready with the reason and gives no signing command; an old batch without the field behaves as before. Tests with two concurrent runs of different commits.
- **`/api/data` goes through the same Host/Origin guard as the other routes** of the local server (DNS rebinding).

## [1.3.0]

Made to be shared: eight languages, authorship and licence in every file, no private data, and nothing tied to one GitHub account.

- **8 languages** (en, es, de, fr, it, ja, zh, pt = European Portuguese) for the page, the command line tools, the launchers, the events, the reports and the error
  messages. `i18n.py` + `locales/<lang>.json` (one flat catalogue per language, standard library only, `t("key", name=value)` with a fallback to English). The language
  is `language` in `actions_monitor.json` (default: the system language, English if unsupported), a selector in the header of the page (remembered by the browser),
  `MONITOR_LANG` / `JUANENRAC_LANG`, or `--lang CODE` in every tool (it wins over the rest). Technical names, commands, paths and the markers that scripts read
  (`SKIP`, `DISPATCHED`, `READY`, `FAILED`, `Summary:`, `BUILD ONLY`, `WOULD DISPATCH`...) are never translated. Events in `events_monitor.jsonl` now carry a stable
  `code` (and `args`) next to the text, so nobody has to parse a language.
- A test checks that the 8 catalogues have exactly the same keys, none empty, the same `{placeholders}`, that every key used by the code and the page exists, and that no
  visible string in the code bypasses `t()`.
- README and QUICKSTART in the 8 languages (`README_<lang>.txt`, `QUICKSTART_<lang>.txt`); `README.txt` is now a short language chooser with the quick start.
- **Authorship and licence**: every source file carries "Copyright (C) 2026 JuanenRac (Electro Hobby 3D)" and "GPL-3.0-or-later - see LICENSE"; JSON data files carry
  `_author` / `_license`; `LICENSE` (GPL-3.0 text), `NOTICE` and `AUTHORS` travel in the zip. `make_release.py` refuses to build when a file lacks them, when private data
  would travel, when the locales differ, or when a launcher loses its executable bit.
- **Shareable**: `github_owner` in the configuration (default: the account of `gh`) replaces the constant that was spread over three modules; the ecosystem prefixes and the
  signing tools are data (`ecosystems.json`, neutral `ecosystems.example.json`; `"*"` = every repository; `"external": true` = only reported) and so are the targets (`targets.json`
  is the maintainer's real catalogue, `targets.example.json` the neutral one; `targets_file` / `ecosystems_file` choose them; keys that start with `_` are metadata).
  The example configuration is neutral. Nothing of this adds a call to the hot cycle.
- **The workspace is optional**: without local clones the monitor starts in a reduced mode (only what the GitHub API gives: no local signing queue, no audit report, no
  CHANGELOG scan) and says so on the page, in the report and at start, instead of stopping. `MONITOR_ROOT` / `MONITOR_AUDIT_DIR` / `MONITOR_SIGNED_DIR` and `signed_dir`
  were added next to the old names. The roadmap layer (A9) is optional too.
- Launchers: menus and messages come from `launcher_msg.py` (your language); comments in English; header on every file.
- Fix: `workspace_root()` no longer ends the monitor when the sentinel starts without a workspace.

## [1.2.0]

What was missing and what else can be done on GitHub, all of it read only and local.

**Part A - what was missing**
- `ci_red.json` schema 2 is now a documented contract: `docs/CI_RED_SCHEMA.md` (shape, the one rule of "red", what is for the owner only). Nothing is
  published from the PC. Optional, explicit exports (never a commit or a push): `read_report.py --export-status DIR` writes ONLY the red list
  (`ci_status_public.json/.md`); `read_report.py --export-sign-queue FILE` (.json/.csv) writes the global signing queue with the local commands.
- Attestation: the signing queue shows whether the build has an attestation (existence by digest of the signed files, one lookup per entry, no signature
  check; switch `sentinel.surface.checks.attestation`). A missing one is a line in the report.
- More verified formats: HYDRA `hydra-sign` (`FILE.sig` = base64 Ed25519 over the bytes of the file, the pinned release key, read in blocks) is checked
  definitively; URTC `.imgsig` has its strict format checked (152 hex digits + LF; malformed = not valid) and stays "unknown" when well formed (the signed
  message also needs the build header, which the signed folder does not carry); ARMOR APKs are signed inside the APK by apksigner and stay "unknown".
- `HYDRA-UMC-OS` is labelled on purpose in `targets.json` (`"build_only": true` + `reason`): `plan` lists it under BUILD ONLY and it is no longer an orphan.
  The signing tools were not touched (its workflow takes other inputs and a different signature scheme).
- Fix: `ci_red.target_path` refused every Windows path written with backslashes (`C:\...`); only forward slashes were accepted.

**Part B - the A10 layer "Actions & releases surface"** (`surface.py`, new section of the tab, a switch and a threshold per check under `sentinel.surface`)
- Actions: workflows disabled by hand, schedules with no run in N days (only when the sample of runs covers the window), `uses:` not pinned by SHA
  (reusable workflows flagged apart), `permissions: write-all`, `pull_request_target` with a checkout of the PR, stuck concurrency queues, failures on only one
  OS of a matrix, artifact cost and retention, required status checks that are red or missing (GraphQL), `dispatch --profile release|nightly|hil` with a canary
  (the first target alone, the rest only if it is green) and a quota gate (`--min-rate`, fails closed). Profiles live in `profiles.json`.
- Releases: expected assets per kind of target (alert when a release was published incomplete), tag vs manifest vs CHANGELOG, GitHub Packages, forgotten drafts
  and pre-releases, `release_notes.py` (a DRAFT of notes from the commits since the last tag; it publishes nothing).
- Security: critical/high alerts by age with a ranking of repositories, coverage (a stack without CodeQL/Dependabot), secret scanning open vs resolved,
  Dependabot by priority (runtime major first, CI-only last).
- Issues and PRs: suggestion of `gh issue close` for build issues whose CI is green again (an event with the text; nothing is ever closed), overdue milestones,
  old human PRs, PRs that touch workflows or CODEOWNERS, the merge queue (approved with green checks). Stale board cards: PENDING (needs per-item reads and a threshold).
- Manifest vs evidence (maturity), 8-language README parity failures, Actions minutes per ecosystem in the header, the report and A7.
- `finalize --execute` now tells the running monitor (127.0.0.1) to refresh just the signed repositories and rewrite `ci_red.json` at once (`monitor_link.py`).
- Optional signed webhook receiver (`webhook.enabled`, off by default, 127.0.0.1 only, HMAC with a shared secret from the config, never a GitHub token).
- Cost: nothing in the hot cycle. Cold, spread over ticks and inside the hourly budget: 2 REST calls per repository per day, one GraphQL query per 15
  repositories per day, 3 for Packages, plus the jobs of red runs and the attestation lookups of the signing queue, and only while the allowance is above
  twice `min_rate_remaining`. The hot GraphQL pass asks for 3 more fields per node (alert dates, review decision, checks state): no extra call.
- The gate also compares `sentinel.surface` of the example file with the defaults and validates `profiles.json`.

## [1.1.1]

- **Cross-platform:** the monitor and the batch tools work on Windows, macOS and Linux. Launchers `MONITOR_GITHUB_ACTIONS.sh`/`.command` and `BATCH_GITHUB_ACTIONS.sh`/`.command` (the zip keeps the executable permission and make_release rejects Windows line endings in them).
- New `platform_compat.py`: the command that starts a child tool (`py -3` on Windows, the current interpreter elsewhere), the text of the commands that `finalize` shows (cmd/PowerShell or POSIX quoting), UTF-8 console and a notice with the way to install `gh` on each system.
- New tests of the cross-platform part (Windows and POSIX simulated from any system).

## [1.1.0]

Signature trust, a stable bridge to the dashboard, orphans and conventions in the batch tools, and a more useful page.

- Signature trust: `sigverify.py` (standard library, read only, no network) checks the signed folder `_firmados/<REPO>/release-<version>/` against the PUBLIC
  key each ecosystem pins (URTC `release_sign.py`, ARMOR helper `PACKAGE_PUBLIC_KEY`, HYDRA updater `RELEASES_PUBLIC_KEY`, or `sentinel.signature_pubkeys`).
  Every state now carries `signature_kind` (none | dev | release) and `signature_verified` (true | false | "unknown"); only a release signature that verifies
  (`trusted`) lowers the pending-signature alert, besides "published". A signature that does not verify keeps the alert and says so in the report.
  `sentinel.require_verified_signature` (default true; false = the 1.0.0 rule). Formats this module cannot check (.sig2, .hdr2, .imgsig, APK, hydra-sign) are
  "unknown", never "false". The build attestation still needs the network and stays with the signing tools.
- `ci_red.json` schema 2: per repository a `pending_sign` list (workflow, hours, state, signature_kind, signature_verified, last_build_at, url) next to the red
  workflows, plus `schema`, `pending_sign_repos` and the threshold; the format is documented in `ci_red.py` and is only ever extended.
- One definition of "last run on main" (`signstate.completed_runs`) shared by the red check, the green-without-release check and the target states.
- `ci_red.target_path` refuses D: paths, WSL/Git Bash forms of D: and drive/UNC paths that the running system cannot use; the tests simulate both systems
  and the whole suite now passes on Linux.
- `gha_dispatch_all.py plan` always ends with the section "Signature orphans" (green CI + known `*-build.yml` + no target); coverage is by repository AND workflow.
- Convention for targets (ecosystem prefix -> default signing tool, workflow in the known list); `targets.json` only holds the overrides and always wins.
  `hygiene --write-candidates` writes the proposed entries to `targets.candidates.json` (never applied by itself, never packaged).
- Page: clickable header counters "red on main" and "unsigned" (filter the repositories; the second one also focuses the signing queue), the signing queue
  with its commands and a copy button, repository panel with build / signed / published, signature kind and verification, and the suggested command;
  a header badge when a minutes budget reaches 80 % (red when exceeded); "yesterday vs today" also compares budget warnings and the lines of the report.

Not done: reading the build attestation / SBOM (network); `HYDRA-UMC-OS` has a build workflow but its signing tool does not support it yet (listed as an orphan).

## [1.0.0]

First numbered version. What the package does:

- Monitor of GitHub Actions for the four ecosystems (local web page, run cache, stuck builds, build-failed/build-stuck issues).
- Sentinel layer A (read only, no AI needed): A1 stuck builds, A2 red CI (one criterion: last completed run of each workflow on the default
  branch), A3 CodeQL/Dependabot/secret alerts, A4 Dependabot pull requests, A5 releases (candidates, green builds without a release,
  pending signature), A6 hygiene, A7 consumption (minutes and API allowance), A8 audits and rounds, A9 roadmap boards.
- Explicit state of each build target: built_on_gha -> signed_local (none | dev | release) -> published, with `last_build_at`,
  `last_signed_at`, `signature_kind` and the real hours waiting; local batch and signed-folder records lower the pending-signature
  alert without waiting for GitHub.
- Signing queue of the day (`a5.sign_queue`): most urgent first, with the exact finalize command of each target.
- Budget of Actions minutes per ecosystem (`sentinel.minutes_budget`, empty by default): warning at 80 % in the report and as an event.
- Event feed (`events_monitor.jsonl`) and `ci_red.json` (repository -> red workflows + hours pending signature), written atomically.
- Batch tools: `gha_dispatch_all.py plan|dispatch|status|finalize|hygiene` with `--only` or `--ecosystem`, `plan --json`,
  `finalize --json`, one retry of a failed dispatch at the end of the batch, targets as data in `targets.json`.
- `read_report.py`: the report as plain text from the running monitor, without spending API quota.
- `make_release.py`: quality gate (unit tests, clean zip, complete example configuration, version/changelog agreement) and SHA256SUMS.

Not done in this version: verifying release signatures against the public key and the build attestation from the sentinel
(different signature formats per ecosystem; the attestation needs the network; the signing tools verify both before publishing).
