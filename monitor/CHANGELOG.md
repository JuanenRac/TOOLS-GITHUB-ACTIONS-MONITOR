<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Changelog

Version of the tool itself (monitor + sentinel + batch tools), semver of its own. The number lives in `tool_version.py`
and is shown as `tool_version` in the sentinel snapshot and by `read_report.py --version`; `make_release.py` refuses to build
when this file and `tool_version.py` disagree.

## [Unreleased]

### Changed

- **A job that did not run is shown apart from a failure**: a job or run that GitHub skipped because of a condition or a path filter now has its own words ("skipped (path filter)"), a dashed outline instead of a filled colour and a hint that says it is not a failure; in the list of jobs of a running workflow its bar is empty with a dashed edge, neither green nor red. A cancelled run says "cancelled". The rule that decides what is red did not change: a skipped run never made a workflow red.

- **The product folder is tidy: next to the launchers there is nothing but folders**: the configuration is in `config/` (`actions_monitor.json`, `targets.json`, `quotas.json` ... and `config_backups/`), the state, the caches and the accounts in `data/`, the logs in `logs/`, and everything an AI reads in `ai/` (`ALERTS_BRIEF.md`, `ai_alerts.jsonl`, `ci_red.json`, the state of the hook). The short commands (`read_report.py`, `monitor_cli.py`, `ai_hook.py`, `mcp_server.py`, `tui.py` ...) are in `bin/`, and the README and QUICKSTART of the package in eight languages in `docs/`. No copy and no link is left in the old places: every part of the monitor (the page, the command line, the gate script, the MCP server, the doctor, the lite edition, the supervisor of several accounts, the Docker image and the systemd unit) reads the new ones. The folders can be moved with `MONITOR_CONFIG_DIR`, `MONITOR_DATA_DIR`, `MONITOR_LOGS_DIR`, `MONITOR_AI_DIR` or `config/paths.json`; the image keeps `/config` and `/data` as its two volumes. See the guide LAYOUT.

- **An installation of 1.8.1 or older moves by itself, and it can be undone**: on the first start what lies next to the launchers goes to its folder. Nothing is deleted or overwritten (a file that already exists in the new place stays and the doctor says so), the configuration is copied to `config/config_backups/` first and every move is written to a journal. `python -m github_actions_monitor.util.rootmigrate` shows what would move, `--apply` moves it and `--undo` puts it back; `MONITOR_NO_AUTO_MIGRATION=1` turns the automatic move off. The `layout` check of `--doctor` lists what is still next to the launchers.

- **The gate script of an AI tool is `bin/ai_hook.py` now**: a hook registered with the old path must be registered again with `python bin/monitor_cli.py ai-hook install`. The script finds the `ai/` folder and the configuration like the monitor does (including `MONITOR_AI_DIR`), and `ci_red.json` is written to `ai/` unless `sentinel.ci_red_file` says otherwise.

- **Nothing repeats in the lists of the page**: the panel "Right now" has ONE row for each repository, with a counter ("3 running", "2 queued") and its runs in a folding list that a refresh does not fold again; a repository with a single run looks as before. The alerts of runs possibly stuck and of failing workflows are ONE line for each repository ("3 runs possibly stuck", "2 workflows failing (build, docs)"). The new texts exist in the eight languages and a test in a browser checks that three runs of one repository give one row with a counter of three.

- **The CI of the repository is lighter and does not pile up**: every pull request runs Ubuntu and Windows; macOS runs on a push to main, on a tag, every night, by hand and on a pull request that carries the label full-ci, always on a fixed Apple Silicon image (macOS 15) instead of the label that moves. A new push to a pull request cancels the run it supersedes (main, tags and the nightly run are never cancelled), Homebrew does not update itself, every Python job reads the same pip cache and a test checks all of it. The workflow that publishes the image was tried by hand on main (it builds both platforms and pushes nothing) and passes.

- **The release gate makes the zip and its SHA256SUMS, nothing else**: the variant of the zip for e-mail is gone.

- **`/api/health` says more, and `?deep=1` asks more**: besides `ok`, `version`, `loaded` and `offline` the answer carries the state of the refresh `cycle`, of the GitHub `credential` of the account and where the monitor `listening` is (the supervisor answers the same words). `/api/health?deep=1` is the deep check: 503 when the refresh cycle of an account is stuck or gone and, in the supervisor, also when its loop stopped, when the cycle of any account is stuck or when no account answers after the start. Without `deep` nothing fails that did not fail before.

- The notification kinds `credential_blind` and `credential_back` are new; `credential_blind` is in the default list and in the example configuration. The Alerts tab, `/api/alerts` and the command line know the level `critical` and the sentinel `system`, and a critical alert is listed first.

- `--doctor` tells the login of each account apart by its own credential file too, so two accounts that each got a replacement are not reported as sharing one token.

- The time limits of the release gate are 3600 seconds by default (they were 900 and 1800, too short for a loaded computer). `MONITOR_RELEASE_TEST_TIMEOUT` and `MONITOR_RELEASE_CLEAN_TIMEOUT` change them (60 to 86400 seconds), and the default is read when the gate runs, not when the module is loaded.

### Added

- **The allowance of GitHub can be shared by kind of read, with a reserve for your tools, and it is counted as a sum**: `readpool.prefer.<kind>` names the source (user, GitHub App, second account) that answers a kind of read first (runs, security alerts, issues and pull requests, history, discovery, the rest; `auto` keeps the spread of always) and `readpool.reserve.<source>` keeps that many calls free in a source, so the `gh` of your tools and agents always finds some in the allowance of the user. A source that fails or is under its reserve hands the read to the others; writes and actions keep the token of the user. The bar of the allowance and the working modes count the SUM of all the sources; its tooltip shows each one and the Quota tab adds the total. Both settings are in the Quota tab in eight languages.

- **Notifications for each user of the team mode (off by default)**: with `notify.users.enabled` every user chooses, in `GET/POST /api/auth/me/notify`, the channels (`ntfy`, `teams`, `email`), the sentinels, the lowest level, whether they want the events of the system and whether messages come at once or in an hourly or daily digest of the alerts they have not seen (`POST /api/auth/me/notify/seen` drops them, `POST /api/auth/me/notify/test` sends a test). The role decides what a user may be told and an event of an account never reaches someone who may not see that account; `notify.users.max_per_hour` caps the messages for one user. The three channels are small plugins, each off until the administrator turns it on; the address of a Teams webhook and the token of ntfy are kept encrypted by the system (DPAPI, Keychain, Secret Service or a private file), never in the configuration, an answer or a log, and go with the user when the user is deleted. Settings, texts in eight languages and the guide of the notifications are updated.

- **A map of the monitor for the AIs that talk to it**: `ai/INDEX.json` lists every file of the `ai/` folder (purpose, format, who writes it, when it changes), the real path of every folder of the monitor and the endpoints of the running monitor, so an AI, local or external, never depends on a fixed path; `ai/README.md` explains the folder to an AI that has never seen it. Both are rewritten at every start. `GET /api/paths` answers with the folders in use, the main files and what is still in the old places, in both editions and in the supervisor of several accounts.

- **The tests of the new order**: the table of places, the folders that move, the migration of an installation of 1.7.x and of 1.8.0 (clean root, same bytes, the copy of the configuration, a second run that does nothing, a file that is never overwritten, the undo), the index and the map for the AIs, the places the gate script finds, and the entry points in `bin/`.

- **Official Docker image and service mode**: `deploy/Dockerfile` is multi-stage (the GitHub CLI from its signed apt repository, the compiled code without the tests, and a final image with only Python, `gh`, the CA certificates and the code, read-only and owned by root). It runs as the user 10001, never as root, with two volumes (`/config` and `/data`), `tini` as init and a health check that is the deep one. `python -m github_actions_monitor.service` prepares everything a person does by hand before the first start from documented environment variables: the configuration, the first account (or several with `MONITOR_ACCOUNTS`), the keys of `listen` and `auth`, and an access token that is made once, kept with mode 600 and never printed. `MONITOR_CONFIG` places the configuration file outside the code.

- **Compose with a reverse proxy, and systemd**: `deploy/compose.yaml` (code read-only, no capabilities, the login as a Docker secret) with an optional Caddy in front (`deploy/Caddyfile`; TLS by itself for a public name, its own authority for a private one, or none), `deploy/.env.example`, and, for a classic install, `deploy/github-actions-monitor.service` with its env file (hardened, restarts on failure, checks the deep health after the start, reloads the credential files on `systemctl reload`). The guide `DEPLOYMENT.md` in the eight languages lists every environment variable, the first start as a service, the backup, the upgrade and the check of the attestation of the image.

- **Image for `linux/amd64` and `linux/arm64` in ghcr.io**: the workflow `release-image.yml` builds and publishes it when a release is published (or by hand), with the minimum permissions of each job, every action pinned by commit, a time limit on every job, tags `X.Y.Z`, `X.Y` and `latest`, and an attestation of the provenance. Pushing is a separate step that only a release takes: the same workflow builds without pushing when started by hand with `push` off, and the CI builds the image on every change.

- **A deep health check**: `/api/health?deep=1` (see above), `python -m github_actions_monitor.cli.healthcheck` for a container or a service manager (exit codes 0, 1, 2 and 3) and `monitor_cli.py health --deep` from any computer. An account whose GitHub login is no good is named but is not a failure: a restart does not fix a lost login.

- **A login that GitHub revokes or lets expire marks only that account as blind**: after two refusals in a row that say the login itself is no good (401, `Bad credentials`, expired or revoked token, suspended account, no login) the account is blind; the others go on. The page, `/api/accounts` (`state: blind`), the health check and the command line say so, a critical system alert (`system.credential_blind`) opens once, the channels are told once (`credential_blind`, and `credential_back` when it works again) and the account keeps trying. A refusal of one permission (a 403 for one repository) does not make an account blind. A service that starts with a login that is already no good stays up and blind instead of giving up.

- **The login can be replaced without restarting anything**: the endpoint `/api/accounts/<id>/credential` (an `admin` session in the team mode; the computer of the monitor otherwise), `monitor_cli.py credential replace --account ID --new-token-file FILE` (or `-` for the standard input; a token is never taken from a flag), and SIGHUP where the system has it (every account reads its credential files again). The new token is checked against GitHub BEFORE it is kept, so a token GitHub refuses changes nothing; a good one is kept only in the folder of that account (mode 600) and used at once. `GH_TOKEN_FILE` names a file for the login of all the accounts, read at the start and on SIGHUP. The token is never in an answer, a log, an alert or the audit.

- **The supervisor of several accounts listens in the network mode** like the monitor of one account: the access token on every request (cookie, header or `/api/access`), lock-out after wrong tokens, the `Host` check, optional TLS with your certificate, the second port of the person at the computer (`listen.local_port`), and the keys that decide exposure, the login of GitHub and the actions on GitHub only from the computer of the monitor (the account treats a request from the network as remote).

- **The page and the tools say where the monitor listens**: this computer, the network or behind a proxy (`listen.proxy_public_host`, `listen.secure_cookie`, `listen.trusted_proxy`), in the bottom bar of the page, in `/api/accounts`, `/api/health` and the first lines of `monitor_cli.py status` and `monitor_cli.py accounts`.

- **The command line works against a monitor on another computer**: `--url` or `MONITOR_URL`, `--ca-file` or `MONITOR_CA_FILE` to trust the authority of an HTTPS certificate of your own, and in the team mode `--user` with `--password-file` (or `MONITOR_USER`, `MONITOR_PASSWORD_FILE`) to sign in with a Bearer session (`auth.allow_bearer`). `status` and `accounts` end with exit code 3 for an account that is blind.

- **Tests**: a test of the container in the CI that builds the image, starts it read-only and without root, revokes the login of one of two accounts and checks that only that account turns blind, that the critical alert opens, that the deep health check stays green, that a refused token changes nothing, that a good one brings the account back without a restart, and that SIGHUP does the same; and one regression test for each behaviour of a revoked login (the count, the other accounts, the alert, the notice, the replacement, the file, SIGHUP, the roles, the audit and the token that never appears).

### Fixed

- **A failure that the monitor swallows on purpose leaves a line in its log**: every `degraded` count now also writes one line to the log file with the origin, the kind of error, the place in the code where it was raised, the cleaned message (never a token) and the count; a failure that repeats writes its first twenty lines and then one in twenty-five, and the recent failures of the doctor and the page carry the place too. Before, the reason was only on the console.

- **The network mode does not start before the first administrator exists**: with `auth.enabled` and `listen.network` both on and no user yet, the monitor stops at the start and says how to go on (turn `listen.network` off, start the monitor, create the administrator from this computer, turn it on and start again). The local mode and the individual mode start as always.

- **The OpenTelemetry export obeys the rule for outgoing requests**: a collector on this computer is called directly and a redirect from it is not followed; any other collector is refused when it, or a redirect, leads to a loopback, private, link-local or metadata address (unless the setting that allows private targets is on), and the proxy of the environment is not used. Before, the export used a plain request that followed every redirect.

- **The proxy of the environment is said to be a frontier of trust**: the help of its setting (and the code) now say that the proxy resolves the name again on its own, so the check before the proxy is a first filter, not a guarantee, and that it should be turned on only behind a managed proxy that refuses loopback, private, link-local and metadata destinations. It stays off by default.

- **A test keeps the page from putting free text into markup without escaping it**: every text of the API that goes into a markup string passes through the escaping function, and the two places that write it as plain text are listed; the help documents are checked to escape their markup and to refuse scripts and non-web links.

- **A name with a line feed at the end is no longer a valid name**: the checks of account ids, repository names, keys, owners, addresses and the like ended in the end-of-line mark, which also accepts a text that is followed by one more line feed ("alpha" and "alpha" plus a line feed were the same id). They now end at the end of the text, 76 checks in all, and a test keeps every new check that way.

- **The pause of the hook of an AI tool is kept in one step**: reading the last moment and writing the new one take a lock, so two events at the same time cannot both pass; and when the moment cannot be written the answer is "do not block", not "ok" (before, a failed write still allowed the block and the pause was never applied).

- **The exporter of a self-hosted runner can no longer send the monitor somewhere else**: a redirect is followed only to this computer or a private address, with the same scheme, no credentials, and at most three times; a public host, another scheme or a loop ends the read with no figures. No proxy is used for it.

- **Calls to GitHub that never return are counted, and the monitor stops piling them up**: when a call gives up waiting its thread is remembered until it ends; with `watchdog_max_abandoned` of them (8 by default, 0 = no limit) still alive the monitor starts no new call to GitHub, and the deep health check answers "degraded" with the number, instead of restarting the loop again and again while threads and connections pile up.

- **Each account has its own feed for the AIs**: with several accounts, every account process keeps its alerts, its brief and the ledger of the notices to an external AI in its own folder (ai/accounts/ and the id of the account) instead of one folder that all of them rewrote. An alert carries its account and its id depends on it, so the same workflow red in two accounts is two alerts; the refresh of one account closes only its own alerts (before, an account closed the alerts of the others because they were not in its snapshot). Installations with one account change nothing. The alerts that an older version left in the shared folder stay there and are closed by the account of the product folder.

- **Refresh, acknowledgement and status of the feed for the AIs are one step at a time**: they take the same lock, between threads and between processes that share a folder, so an acknowledgement is no longer undone by a refresh that read the state a moment before. A refresh that cannot get the lock in ten seconds is skipped and tried again at the next cycle; the diagnosis of a log is read before the lock is taken.

- **The cap of notices to an external AI cannot be passed by notices that run at the same time**: the calls and the cost of the hour are checked and reserved in one locked step before anything is sent, also across processes that share the ledger. A reservation made by a process that died before sending counts until its hour is over.

- **With the team mode on and no user yet, only the person at this computer gets in**: until the first administrator exists a request from anywhere else (the network, or through a proxy) is answered 403 "create the first administrator from this computer first" for everything that is not public (health check, login page, webhook); before, the whole monitor stayed open to the network during that time. Turning the team mode on changes nothing for the person at this computer, who still creates the first administrator from the login page.

- **The process of each account answers only to its supervisor**: it asks for the key the supervisor gave it when it started it, on every request; another user of the same machine who reaches the port of an account process gets a 403 instead of the data, whatever the team mode says.

- The test of an account that dies at once no longer depends on the speed of the computer: the wait before an account is started again is checked with a clock that the test gives, and a second test checks the schedule of the waits without reading the real time (the old one failed under load in the gate of a release).

- **Saving the settings never goes on without the lock of the file**: when another process keeps the lock for more than ten seconds the save is refused with "another process is saving the settings: try again in a moment" and nothing is written; before, it went on after the wait and could undo the save of the other process.

- **The command of the sentinel is checked before it is run**: it has to be a list whose first word is the full path of a program that is not a shell (not sh, bash, cmd, powershell and the like), with no shell characters in any word, no word with a blank after the first, and no flag that makes a program read a command line (-c, /c, -Command). Anything else is not run at all.

- **Tokens for scripts are off by default**: the login with the client "api" and the Authorization: Bearer header are refused until the setting for tokens for scripts and apps is turned on in the Advanced tab; the browser session is unchanged. A token or a password never reaches the audit file.

## [1.8.1]

### Fixed

- **The "loading repositories" box stays on the page after the last repository is read**: the finished picture now reaches the page as soon as the reading ends, without waiting for the upkeep that follows it (the brief for the AI tools, the alert centre), and a long list of Sentinel panels can no longer make that brief loop for ever (it was the loop that kept the last partial picture, 131 / 131, on the page).

- **Reloading the page (F5) no longer takes minutes to get the data**: the endless loop of the brief used all the processor time of the monitor and the page gave up with an abort; besides, the answer of the data endpoint was written to the connection with the global lock held, so one stalled connection (a closed tab) froze every other page and the refresh cycle. The lock is now held only to take the picture. A browser test checks that the box shows while loading and leaves with the last repository, and server tests check that the brief ends, that the finished picture is published before the upkeep and that a stalled connection does not block a reload.

## [1.8.0]

### Changed

- **New folder layout, same behaviour**: the code is now an importable package in `src/github_actions_monitor/` (`app`, `accounts`, `sentinels`, `security`, `data_pipeline`, `integrations`, `cli`, `ui`, `i18n`, `util`); the page, the neutral examples with `quotas.json` and the eight language catalogues are in `assets/` (`static`, `examples`, `locales`); `make_release.py` is in `tools/`. The launchers stay in the product folder and start `python -m github_actions_monitor` (complete) or `python -m github_actions_monitor.lite` (lite): same address, same port. The data of the person who runs it (`actions_monitor.json`, caches, logs, `accounts/`, catalogues) still lives next to the launchers, never inside `src/`.

- The commands of the guides (`python read_report.py`, `python actions_monitor.py --doctor`, `python monitor_cli.py status` ...) keep working: a small entry-point file with the same name stays in the product folder, so the hooks and MCP servers already registered by path keep working too. The release zip keeps its folder name and now carries `src/`, `assets/` and `tools/`.

- **The roadmap tells what 1.8.0 holds and what each next version brings**: what is already in the main branch, what is finished and waiting to be merged, what is still being finished, and the plan from 1.8.2 to 2.0.0 in the order it will be done, in the eight languages.

- **The bar at the foot of the page is one line and says only what the boxes at the top do not**: the connection, the allowance, the runs, the last read and the repositories were said twice (as boxes at the top and as items of the bar); the bar keeps the sentinels, the Low-mode warning (the only mode it says), the AI, the account, the version, the address, the sound chip and the clock, and it no longer wraps at any width (on a narrow screen the date and the zone leave first). A browser test measures it in several languages, wide and narrow.
- **The "loading repositories" box** is checked in a browser: it is shown while repositories load and it is gone with the last one.

### Added

- **Storage layer** (`src/github_actions_monitor/storage/`): a `Storage` interface (configuration, sentinel state, the event feed, analytics, small named documents and the global records of users, their accounts and sessions) that keeps the rule "a write is atomic, a damaged item reads as empty" for every backend. `FileStorage` is the first backend and keeps the layout of `accounts/<id>/` exactly as before (and the flat installation next to the launchers): the same files with the same names, written through a temporary file that is flushed and renamed. `create_storage` is the one place that picks the backend; the lite edition always gets the file backend.

- Backups of a storage that any backend can restore: one `.zip` with a dump and a manifest of counts, size and SHA-256; the restore verifies the copy first and refuses to write over a storage that already holds accounts unless it is forced.

- **SQLite backend** (optional, off by default): the same data in a database, one file per account (`accounts/<id>/storage.sqlite3`), so the process of an account is the only one that writes it. WAL journal and a busy timeout, every write one short transaction, versioned schema migrations that run in the same transaction as the bump of the version (an interrupted one leaves the database as it was; a database from a newer version is refused), an index on the events of an account by time, and a process killed in the middle of a write recovers on the next start. The state that moves to the database: the event feed, what the feed announced, the analytics, the state of the sentinels, the silences and the update notice; the configuration stays a JSON file (it is what names the backend), and caches and logs stay files. The lite edition has no such option and always uses files.

- A shared database for the whole installation (several accounts and processes in one file) is kept ready and tested: WAL, busy timeout, two processes ticking at once and a reader that never waits for a writer.

- `tools/migrate_storage.py` moves the state between the file backend and SQLite in either direction: a dry run by default, `--apply` copies every account in one step and then reads both sides back and compares every item and every event; your files are never changed or deleted; an interrupted run leaves each account whole or as it was and the same command resumes. `tools/backup_storage.py` makes, checks and restores the backups of either backend (a backup of files restores into SQLite and the other way round).

- **Retention and rotation** (Complete): a monitor that runs for months no longer grows without a ceiling. `retention.events_days` (90 by default) and `retention.analytics_days` (180) set how long the events and the days of the analytics history are kept; `retention.mode` is `archive` (default; the old events are first written to a `.gz` in `events/archive/` of the account, outside the hot path, then removed from the feed) or `delete`; `retention.enabled` is the switch and `retention.interval_hours` (24) says how often a short pass runs at the end of a refresh. Each pass leaves a line in an audit document (when, how many events removed and kept, the archive file, how many analytics days, any error). The purge only removes events and analytics days older than their limit: never the configuration, the state of the sentinels, the silences, nor an event that has no time. `retention.events_max_kb` (512, as before) is the separate ceiling in size of the feed file with the file backend. The settings are in the Folders and files tab; the lite edition does not have them.

- `--doctor` has two new checks: the storage (SQLite database present, passes its integrity check and has a schema this version understands, read only, nothing is created or migrated) and the retention (the size of the events of each account against `retention.warn_events_mb`, and a warning for a monitor that runs as a service, on the network, without a browser or in a container, whose configuration has no retention block).

- `tools/migrate_layout.py` for a folder that was a flat installation: a dry run by default; `--apply` copies your configuration to `layout_backup_<stamp>/config/` and MOVES (never deletes, never overwrites) the old modules, page, examples and `locales/` to `layout_backup_<stamp>/old_code/`. `--doctor` warns while such leftovers exist. `MIGRATING.md` describes it in the eight languages.

- **Team mode: users, roles and sessions** (`src/github_actions_monitor/security/auth.py`, `auth_http.py`, `auth_cli.py`; off by default with `auth.enabled`, so one person alone notices nothing): once the first administrator exists (created at `/login` or on the console, only from the computer that runs the monitor and only once) every request needs a session. Roles `viewer` (reads), `maintainer` (also silences, acknowledges, changes the working mode) and `admin` (also settings, users and everything that can reach GitHub); a route nobody listed is closed to all but an admin. Each user has the accounts they may see: another account asked for with `?account=`, `X-Account-Id` or an export answers 403. Passwords are kept as a salted scrypt hash; the session is an HttpOnly, SameSite=Strict cookie (Secure over HTTPS) with a CSRF token on every POST, or a Bearer token for scripts and apps (`auth.allow_bearer`); a user is locked after `auth.max_failed_logins` wrong passwords, each address is rate-limited, a changed password, role or state ends the user's sessions and there is always one active administrator. Endpoints `/api/auth/login`, `/api/auth/users` and `/api/auth/audit` answer errors as `{"error", "code"}`; `auth_audit.jsonl` records logins, locks, refused requests and user changes without any secret. The lite edition never has a login, the one-use token of the page still applies, and `python -m github_actions_monitor.security.auth_cli` recovers a lost administrator password. Seven settings (`auth.*`) with their help in the eight languages and a section in `docs/ADVANCED.md` in the eight languages; `tests/test_auth.py` covers the rules, the roles of every kind of route, the scope between accounts, the cookie, CSRF, Bearer, locks and the audit on the real server.

- The accounts supervisor filters by user: `GET /api/accounts`, `/api/accounts/<id>/status`, the page of an account and every request with `?account=` or `X-Account-Id` show and reach only the accounts assigned to the user (an admin sees all), and the monitor of an account is told who is acting. A silence of the Alerts tab now keeps who made it: `muted_by` in `GET /api/alerts` and in the history of silences.

- **The page says when it is out of step with the monitor**: the bottom bar shows "data from Ns ago" (the time since the last good answer) and turns red, with the connection lamp, after 60 seconds; a failed request shows "retrying in N s" and retries by itself; a request that hangs is cut after 15 seconds; a watchdog asks again when the page is late and nothing is on the way, and coming back to the tab asks at once. Data that stop changing for two minutes (longer in low mode) count as old. When the page comes back from a gap it asks again for the sentinels, the history and the mode.

- **The sound can be unlocked and no longer misses a red that came while the page was closed**: a visible notice "Sound blocked by the browser: click here to turn it on" appears while the browser keeps the audio locked (any click on the page unlocks it; the notice button also plays a test tone); the page remembers the reds it had seen (per account, up to six hours), so a red that appeared while the page was closed or reloading sounds; and when the page returns from a gap the cooldown no longer hides a new red. The help of `sound.server_beep` (off by default, this computer only) now says what the page cannot do and what that switch adds, in the eight languages.

- **The refresh loop has a heartbeat and a watchdog**: `/api/data` now carries `loop` (the phase of the cycle, how long it has been running, the last good cycle, the last error and the phase it happened in, the restarts and any problem writing the log or the brief for the AI). The page says "The monitor does not refresh: its cycle has been in <phase> for <time>" in the bottom bar when a cycle runs far too long, and a log or brief that cannot be written is shown there too instead of failing in silence. A watchdog thread checks every 30 seconds: a cycle that runs longer than the new setting `watchdog_minutes` (default 10, 0 = off) or a loop whose thread is gone is restarted in a new thread, after writing the traceback of every thread to the log file (where it hangs). The old loop, if it ever wakes up, sees it was replaced and leaves without publishing.

- **The "bing bing" also sounds when the page loses the monitor itself**: once per loss (no answer for over a minute, or a cycle stuck), together with the red bar. The mute chip, the `sound.on_connection_lost` switch, the cooldown and the browser's sound lock apply as for any other sound; the help of that setting says so in the eight languages.

- **GraphQL for quiet repositories** (`network.graphql_checks`, off by default; `network.graphql_batch`, 1 to 30, 20 by default; in the Quota tab, in the eight languages): the repositories that are not hot are read in batches through GraphQL, which has an allowance of its own, instead of one REST call each; the hot ones and any repository the query does not answer are still read through REST in the same cycle, and a failed batch falls back to REST. It sees only the last commit of the default branch and gives no durations, attempts or other branches (the guide of the allowance says so). The accounting (batches, repositories, points, repositories sent to REST) is part of the allowance line of the brief and of the state for the AI tools, next to the reads answered `304`.

- **The active notice to an external AI** (`ai_notify.*`, in the AI tab, local-only, off by default, in the eight languages): when a NEW real alert opens, a short summary goes to the provider of the AI block and its answer is kept as advice in `ai_notify.jsonl`. A first confirmation per provider (`ai_notify.confirmed_provider`, changing the provider needs a new one), only the redacted fields of a closed list (severity, class, repository, workflow, conclusion, streak, cause, next step, link), a cap of calls an hour and a cap of declared cost an hour (a call is counted before it is made), the key by the name of an environment variable, and the AI never runs an action (its answer is cut, its links are defused and nothing of it is read as a command). The variant of an outgoing command (`ai_notify.command` (only in the configuration file, never in the Settings page)) names ONE file by its absolute path, started without a shell and without arguments, that receives the same JSON on its standard input. The notice leaves from a thread of its own, so a slow provider never holds a cycle.

- **The terminal application edits lists and maps**: in the Settings tab of `tui_textual.py`, a list (the items separated by commas) and a map of numbers (`name=3, other=5`) can be typed and saved like a simple setting; the server checks every value again, the options of security still change only in the page, and the guide of the console tools says so.

- **The page of the team mode shows who is signed in**: a box in the header with the name and the role (a text, not only a colour) that opens a menu to change the password, to see and manage the users and the audit (administrators only) and to sign out; the first time, with the mode on and no user yet, it points to `/login`. Every change the page sends carries the CSRF token, a session that ended sends the person to `/login`, and a wrong token is renewed and tried once. In the individual mode and in the lite edition the page draws nothing and asks nothing new; `tests/test_auth_page.py` runs the wrapper of `fetch` in Node against a fake network.

- **Every status lamp has a shape as well as a colour**: a tick for ok, an exclamation mark for warn, a cross for bad, an i for info and a question mark for unknown, in the lamps of the sentinels and in the lamp of the bar at the foot, so the level never depends on the colour alone.

- **The lamps are alive**: each one breathes at a pace that follows its level (slow when all is well, quick when something is red) with a soft glow of its own colour.

- **A lamp that changes plays one short transition**, and the tooltip of the lamps of the sentinels says what the level was before (also for a keyboard user, with the focus on the lamp).

- **The boxes at the top answer when their state changes**: a short pop when a box turns red, yellow, green or starts running, a small tick when a figure changes and a slight bob of the icon of the active runs.

- **Hover and focus say more**: the lamps of the sentinels lift and show their text in a tip that follows the keyboard focus too, and the rows of the alerts answer to the pointer.

- **Filters move**: when you change a filter, the rows that are drawn arrive with a short slide instead of jumping.

- **Less motion means no motion**: with the preference of the system for reduced motion nothing breathes, pops or slides, and the light edition keeps its figures and its bar with the same lamps. No library was added.

- A check of the life of the page in a real browser (the lamps are animated, every lamp has a shape and a text, a changed lamp plays its transition, the same page with reduced motion stands still, nothing is logged as an error), run by the job of the page.

### Fixed

- The dashboard could stay on one old picture while the monitor was running: a call to `gh` that never returned (a child process holding its pipes after the timeout) held the refresh loop for good while the page still answered at once. Every `gh` call is now bounded by a hard deadline in a helper thread, and a loop that still hangs is found and restarted by the watchdog above.
- A failure to write the log was swallowed and could end a cycle; it is now kept and shown, and the cycle goes on.
- The page showed old data without any warning when the monitor stopped or answered slowly (a request that never returned left the page looking alive), and the "bing bing" stayed silent after a reload or a long gap.
- The SQLite storage no longer fails with "database is locked" when several processes open or write the same database at once: the wait for another writer is 30 seconds by default and can be set with `busy_timeout_ms` in the `storage` block, and the steps that SQLite does not make wait (the first switch to WAL, taking the writer lock) are tried again a few times with growing pauses.
- The brief for the AI tools (`ALERTS_BRIEF.md`) and the log (`actions_monitor_log.txt`) now agree with a monitor that is running: the brief has a `Monitor:` line (cycle complete, cycle in progress, connection lost, last cycle failed) and the hour of that note, so a cycle that is still reading repositories no longer leaves the hour of the previous cycle as the last word (the alerts it lists are the ones kept from the last complete cycle, and a partial cycle never opens or closes one); the log writes a `cycle=started` line when a cycle begins.

- **The stream of events for AIs no longer dies on an ordinary log line**: the line of the feed is cleaned field by field and then written, instead of cleaning a JSON that was already written (a cause that ended in `password: x`, `token=x` or `DB_PASSWORD=x` broke it). A line that cannot be cleaned is skipped and the stream goes on; the answers of the MCP server are cleaned the same way. In the cleaner, the value of a `key=value` pair stops at a quote, a comma or a semicolon, and a quoted value is cleaned whole.

- **The test of the ports of the accounts no longer fails when suites run at once**: the supervisor can be told where to start looking for free ports (the default stays 18800) and the tests ask the system for an unused stretch instead of a fixed one.

### Security

- **The lock-out of wrong tokens brakes again (network mode)**: an address that is not this computer and is locked is refused BEFORE its token is judged, in every way of presenting it (header, cookie, `?access=` and `POST /api/access`); until now a locked address could keep guessing and the right token still got in. The person at this computer is never locked out of their own monitor.

- **A declared reverse proxy makes loopback stop meaning "this computer"** (`listen.proxy_public_host`, `listen.secure_cookie` or `listen.trusted_proxy`): a proxy that forgets its forwarding headers can no longer turn every client of the internet into the owner. The person at the computer of the monitor uses the new second port that only listens on `127.0.0.1` (`listen.local_port`, 0 = off, restart needed, same access token). With `listen.trusted_proxy`, the wrong tokens of all the clients of the proxy are also counted together (three times the limit of one address), so rotating `X-Forwarded-For` does not defeat the lock-out.

- **The guide of the reverse proxy** (`DEPLOYMENT.md`, eight languages) gives the whole recipe: public `Host`, `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto`, the network mode and the declaration of the proxy; it no longer says that the monitor "has no login", and it says that `listen.trusted_proxy` assumes a proxy on the same computer.

- **`GET /api/settings` for a client of the network** returns the value only of the settings it may change; for every other setting (paths of keys and tokens, folders, names of variables) it says only whether it is defined.

- **Test of every "this computer only" route**: a table of the routes is walked against a real server with a client that is not on loopback (and the source is scanned so that a new route cannot be forgotten).

- **An address of GitHub passes the cleaner only in the shapes of a closed list** (a repository, a run with its job or attempt, a commit, an issue, a pull request, a file); it is cut at the first character that is not a letter, a digit, a dot, a hyphen, an underscore or a slash, and what follows is cleaned like any text. Until now a secret glued to a link (an encoded query, a list separated by commas, a colon, an opaque segment of the path, an e-mail that starts in the address) travelled whole to the AI.

- **The hook of the AI client hands over no text of a log**: only the repository, the workflow, the conclusion and the link of each alert. The order to act without waiting to be told is gone; the closing line now says that a log can hold text written by third parties, that it is untrusted data and that instructions found in it are never followed. In the eight languages.

- **What depends on who asks is always answered by your own login**: `gh api user`, `user/orgs`, notifications, a search for `@me`, `gh auth` and `gh repo list` without an owner never go to the GitHub App or to the second account, however many calls those have left (with the second account on, the monitor could take the owner of that account as its owner and list its organisations).

- **A `gh` call is a read only when it is on a white list**: `gh api ENDPOINT` with at most the options `--jq`, `--paginate`, `-H` (of the kind a read sends), `-i` and `--cache`. The attached spellings of a write (`-XPOST`, `--method=DELETE`, `-fa=b`, `--field=a=b`, `--input=-`) and any other option go to your login instead of being spread over the sources.

- **The token file of the second account** (`extra_reader.file`) must be inside the accounts folder of the monitor (`accounts/`, or `MONITOR_ACCOUNTS_DIR`) and is opened without following a link and only if it is a small regular file; outside that folder the setting is empty. The new switch `extra_reader.any_folder` (off by default, local only) lifts the folder rule for a file that must stay elsewhere.

- **A central panel dated in the future is not trusted**: its age was clamped to zero, so it counted as fresh for ever; now it is behind, the summary says the date is not trusted and a clock that runs ahead by up to five minutes is tolerated.

- **A page that breaks turns the CI red**: a new job (`page`, without `continue-on-error`) opens the page of the demo monitor in a real browser (`tools/check_page.py`), goes through every tab and every sub-tab of Settings, requires a minimum of fields in each one and fails on any error of the page, unhandled promise or console.error. A page broken on purpose (a second definition, an assignment to the name of a function, a call to a function that does not exist) must make it fail. The test that looks for functions defined twice now also sees a declaration with an indent, one with `async` and an assignment to the name of a function.

## [1.7.9]

### Fixed

- The links of the runs that the AI tools receive (feed, brief, state, hook) were cut to "https://github.[blob]": the redactor took the address for an opaque string. Whole https addresses of github.com now pass untouched; tokens, keys, e-mails, IP addresses and personal paths are still cleaned, also inside a link.

## [1.7.8]

### Added

- **`listen.trusted_proxy`** (off by default, local-only, in the eight languages): behind a reverse proxy of your own on the same computer, a failed attempt is counted against the last address of `X-Forwarded-For` instead of against the proxy, so the wrong tokens of one person do not lock out everybody. It only changes that counting: a request that comes through a proxy is still never treated as this computer.

### Fixed

- The Settings page showed "The local monitor does not respond" and no tabs: the box of the Quota tab had the same name as an older function of the Basic tab and was replaced by it. The Quota box is renamed, and a test now fails if a function of the page is defined twice.

## [1.7.7]

### Added

- **A check that no text leaves its box** (`tools/check_overflow.py` and a test that skips cleanly without a browser): the page is opened in a headless browser in the eight languages, wide and narrow, goes through every tab and window, and fails when any text is wider than a box that has a border or a background or leaves the window.
- **`display.blink_red_tiles`** (on by default, in the Settings tab, in the eight languages): the tiles at the top and the items of the bar at the foot that turn red blink softly until the cause is solved; with reduced motion in the system they show a fixed, thicker red edge instead.
- **A doctor check for the time zone**: a zone that neither the system nor the built-in table knows is reported, and the times are then shown in UTC (they used to fall back to the zone of the computer without saying so).
- **The History tab says "Showing n of N"** when the list is shorter than what the header counted (the monitor keeps the 600 most recent runs; the data carry `runs_total`).
- **The panels of the Sentinel tab as data**: `GET /api/sentinel/panels` (read only), the MCP tool `sentinel_panels` and a section "Sentinel panels" in the brief give, for A1..A13 and the second sentinel, the level, a line and the rows to act on with repository and link; the rows of a panel at "act" or "keep an eye on it" also become alerts of the feed (classes `real` and `watch`), so the stream, the hook, `alerts_open` and the counter of real alerts include them.
- **A "bing bing" for something new that fails** (the `sound` settings, in the eight languages): the page plays two short tones (Web Audio) only for a NEW red or a lost connection, never at a refresh or for what was already there, with a cooldown, a volume and a chip "Sound" in the bar at the foot that unlocks the audio of the browser, mutes it and is remembered; a button "Test sound" in This browser; and `sound.server_beep` (off by default, local only) for when the page is closed (Windows beep, macOS `afplay`, Linux `canberra-gtk-play` or the terminal bell, without a shell and without the network).
- **Everything the monitor says, as signals for an AI tool**: one inventory (`signals.py`) with a level (act / watch / info), a summary and rows with repository, link, age and next step for the Now tab and its tiles, the alerts, the repositories, the sentinel panels A1..A13 and the second sentinel, the allowance, the connection and the health of the monitor; `GET /api/ai/state` (versioned, read only), a brief with "What to do now", "Pending" and "Monitor health" and the counter of signals to act on, and the MCP tools `monitor_state`, `signals`, `diagnose` and `act`. A test walks the page and fails for a tile or tab that is neither in the inventory nor marked decorative.
- **The connection with an AI tool is the same in the lite and the complete edition**: the same channels (brief, feed, `/api/ai/state`, stream, MCP tools, `ai-hook`), the same code and the same settings in both; the state says `edition` and lists the panels that do not exist in lite, so a missing panel is not taken for missing data.
- **A Low mode (extreme saving of the allowance)**: next to Normal, Fast and Turbo, `low` reads only the hot repositories every 4 minutes and the rest every 30, with short run lists, and says in the bar and in the brief that its figures can be old and how old; `modes.auto_low` (on by default) goes in by itself under 1000 calls left and comes back over 2500 or when the allowance renews (two different numbers, no flapping); the values are in `modes.low` of the file.
- **The central panel as a base line that spends no allowance** (`central.source`: off by default, `git` or `http`; `central.max_age_minutes`, in the eight languages): the monitor reads `data/sentinel.json` of the profile repository (refreshed every half hour by a workflow with its own token) with a plain git fetch or the raw file, shows "source: central panel, N min ago" in the state and the brief, ignores a file that is behind (more than two hours) and says so, and in Low mode asks the API live only for the repositories the panel says are red, those with a run in progress and what the panel does not carry.
- **An optional GitHub App for the reads** (`github_app.enabled`, off by default, with `app_id`, `key_path` and an optional `installation_id`, in the eight languages): the reads of the monitor use the installation token of an App, whose allowance is separate from the user's and bigger the more repositories it covers; the JWT (at most ten minutes) is signed by `openssl` from the path of the key, which the monitor never reads, copies, prints or logs; the token lasts an hour, is kept in memory and renewed five minutes early; writes and actions keep the user's token; if the App fails or lacks a permission the read is repeated with the user's token; `GET /api/github-app/status` (this computer only) shows the name, the installation, the permissions granted and the allowance of the App, never the key or the token; the data carry the allowance of the user next to the one of the App, and the doctor checks openssl, the key file and its permissions.
- **Two new guides, in the eight languages**: `docs/AI_CONNECTION.md` (connect an AI tool: what it sees, the five channels, step by step, security, troubleshooting, what each edition shows) and `docs/QUOTA.md` ("More quota, less spending": how the allowance works, every way the monitor saves it, a GitHub App step by step, sharing the allowance between tools, what not to do); both are linked from the README and the help index, and a test checks that every setting they cite exists.
- **The help is checked on every change**: a setting without its label and help in the eight languages, a tab without a help topic, or a changelog line that names a setting or an endpoint missing from the help and the guides now fail the tests; a help checklist is in CONTRIBUTING and in the pull request template.
- **A Quota tab in Settings** (in the eight languages, also in the lite edition): the modes and the values of Low (`modes.*`), the saving (`network.etag`, an alias that works together with `cache.etag.enabled`), the central panel, the GitHub App and a second account for the reads in one place, with buttons that show the allowance of every source with its renewal time, test the App and the second account, list the permissions the App lacks, and apply the recommended values or the defaults.
- **A second read-only account for the reads** (`extra_reader.enabled`, `extra_reader.file`): the setting holds only the PATH of a file with a fine-grained token, which the monitor reads at the moment of use, keeps in memory and never stores, prints or logs; the reads are spread over your login, the App and the second account by the calls each has left, a refused source is left out for five minutes and the read is made again with the next one, and writes and actions never use it.
- **Accounting of the reads**: the state, the brief and the data say how many conditional calls were made and how many answered 304 (no allowance spent) and the allowance of each source.
- **Who spends the allowance**: the monitor compares, inside each hourly window, what the whole account spent with its own calls and says in the Quota tab, the state and the brief how much other tools spend, with a warning when they spend most of it (GitHub does not say which tool).
- **The stream carries the other signals too**: the allowance used up, the connection that drops, data that go stale, a central panel that is behind and the health warnings become events of the feed (and of the stream and the hook) when they appear, change or are solved, not only the red workflows and the panels of the Sentinel tab.
- **The batch dispatch keeps the attempt of the run it found** (`run_attempt` in the batch record, from the field `attempt` of `gh run list`; empty when `gh` does not give it), and the guides of the connection with an AI tool and of the quota describe the second read-only account.

### Changed

- **The bar at the foot is redesigned**: every item is a chip with its own border, the connection and the quota take the colour of their state, the clock is a framed box with large bold tabular digits, the date above and the zone in small letters, and the bar keeps its order in narrow windows.
- **Every box lets its text break instead of leaving it** (tiles, chips, badges, cells, headings, buttons of the windows): the time of the last reading keeps its zone apart in small letters, the alert rows are laid out in two columns in narrow windows and the grids of the tiles can shrink below their content.
- **The tiles of a row have the same height**, whatever their small text needs.

### Fixed

- **One number for the open failures**: the tile "red on main", the list of alerts, the bar at the foot and the brief count the same thing, a workflow whose last run on the default branch failed (a failure on a work branch no longer shows as an open alert), and the bar never says "no notices" while alerts are open.
- **The start-up of the monitor names the version once**: the line "GitHub Actions v..." that repeated the banner is gone; the author and the licence stay in one line.
- **Damaged state files** (collab state, sentinel cache and history of the wrong shape) are ignored entry by entry instead of reaching the code that reads them.
- **A used-up GitHub allowance is ONE notice, not one error per repository**: the reads of the repositories stop until the renewal (and resume by themselves), the Alerts list says "GitHub allowance used up until HH:MM ... (N repositories not refreshed)", the bar at the foot says it too, nothing turns red and nothing reaches the feed, the sound or the brief as a failure; the error texts of `gh` are cut to one line (no legal paragraph, no request id) and many repositories with the same kind of error are grouped in one line.
- **About (and every page) no longer waits for the network**: the check for a new version of the monitor was read inside the request of /api/about when its answer was older than a day, so a `gh` without a login or a slow network made the About window take from 10 to 25 seconds; now the answer of the cache is returned at once and the read is made by a thread in the background, one at a time.

## [1.7.6]

The connection between the monitor and an AI tool: the feed always agrees with the page, each alert says why it is red, a stream and three MCP tools push the news, a command installs the gate script, the bar shows whether an AI is connected, and every state file is private to its owner.

### Added

- **The brief and the feed follow every refresh of the Alerts tab** (and every read of the feed and every cycle): they used to follow it by one cycle, so an AI could read 10 alerts while the page showed 6. `ALERTS_BRIEF.md` now carries `Updated:` in your time zone and a machine line `updated_epoch:`, and `GET /api/ai/brief?fmt=json` adds `updated`, `updated_local` and `age_seconds`. A cycle that has not loaded its data yet never resolves alerts.
- **`ai_alerts.diagnose`** (off by default, in the Settings tab, in the eight languages): each alert of a new red run carries `diagnosis`, the first failing step and about ten relevant lines of the log, read with read-only calls, cleaned of secrets and bounded in size and in runs per cycle; an infrastructure error in the log makes the alert transient.
- **`ai_alerts.cascade`**: alerts that are red because another repository is red (named in the log or in the rule `ai_alerts.cascade.map`) are listed under it in the brief and carry `origin`.
- **`GET /api/ai/stream`** (`ai_alerts.stream`, off by default): server-sent events, read only, with the access token in the network mode, limited in listeners and in time, resumable with `Last-Event-ID`; the lite edition does not have it.
- **MCP tools `alerts_open`, `alert_diagnose` and `alert_ack`** (the last one only with `--allow-ack`), and a notice to the AI when it connects, in the `instructions` and with one notification, saying how many real alerts are open.
- **`monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]`** and the gate script `ai_hook.py` (standard library only): it adds the brief to the AI session and, only with `ai_alerts.client_hook.block_on_stop` (off by default), asks the AI to look at open real alerts before it ends a turn. The settings of the tool are merged, never replaced, a copy of the file is kept, a file that is not valid JSON is refused untouched, and everything written is plain ASCII. The figures live in `ai_alerts.client_hook` (Settings tab, eight languages).
- **An AI heartbeat** (`ai_alerts.heartbeat`): the stream, the MCP server, the gate script and the endpoints note their last read in a small local file, and the bar at the foot of the page shows whether an AI is connected and how long ago it read.
- **`monitor_cli.py --token-file FILE`** and a warning on stderr when `--token` is used (it shows in the list of processes) or when the token file can be read by other users.
- Tests for every change, in a temporary folder and offline, including the mode of every state file under a lax `umask`.

### Changed

- **Every state file of the monitor is created with mode 0600** (and the folders it creates with 0700) through one helper, `private_io.py`: silences, events, the feed, the brief, caches, the settings and the files written by the gate script installer. On Windows the modes cannot be enforced by the program (the folders inherit the permissions of their parent).
- **Starting the network mode** while `listen.query_access` is still on now prints the first steps (turn it off; use HTTPS or a VPN), and the help of `listen.network` and the advanced guide say the same in the eight languages.
- **The feed of alerts for AIs is off by default** (`ai_alerts.enabled`, it was on): a new installation writes no feed until you turn it on. An installation that already has a feed in its folder keeps it on, and the console says so once at start, so nobody who was using it on purpose is switched off.


### Security

- **Outgoing notifications ignore the proxy variables of the environment** (`http_proxy`, `https_proxy`): a proxy made the check judge the address of the proxy and not the one of the destination, and a proxy that answered with a redirect could send the request to the local network (the metadata address of a cloud included). The new setting `network.use_proxy` (off by default, in the Settings tab, in the eight languages) uses them again, and then the destination and the target of every redirect are checked before the proxy gets anything. Tested with a proxy that redirects to the metadata address.
- **`/api/ai/actions/confirm`, `/api/ai/actions/unlock`, `/api/ai/test` and `/api/notify/test` are for this computer only** in the network mode (403 `local_only`), like the other endpoints that act.
- **A plan of `act` is bound to its workflow**: the plan keeps the resolved path and the SHA-256 of the file, and both are checked again right before `act` starts; a workflow edited, replaced or removed after the confirmation does not run (`workflow_changed`, with a text in the eight languages).
- **The macOS Keychain no longer gets the token on a command line**: `security -i` reads the command from standard input, so the token is not in the list of processes.
- **Everything `gh` prints is cleaned before it is kept**: the log of the actions for AIs and the detail of a refused action go through the redactor, which now also covers the old 40-hex tokens and the token the monitor keeps.
- **The list of refused addresses is bounded** (`localguard`): the next lock purges every lock that ended, not only the one of the address that asks, and it never holds more than 2000 entries.
- **A silence that could not be saved is not reported as saved**: `POST /api/alerts/mute` and `unmute` answer `ok: false` when the file could not be written.
- **The command line never shows a traceback for an answer of the wrong shape**: a list, `null` or a number instead of an object, or a field of the wrong type, ends with exit code 4 and a message.
- **A client of the network can write only a short allow list of settings** (the language, the time zone and the pace of the page): every notification channel, every path, every name of an environment variable and the files that the signing and dispatch flow trusts are changed from the computer of the monitor. A setting added later is local-only until it is listed on purpose.
- **Behind a reverse proxy on the same machine** a request with a forwarding header (`Forwarded`, `X-Forwarded-*`, `X-Real-IP`) or with the public name of the proxy is never "this computer", and the access token is judged before the lock by address, so a flood of wrong tokens cannot lock the owner out.
- **Calls to this computer never go through a proxy of the environment** (`netguard.local_open`, used by the command line, the MCP server, the terminal views and the hooks), and the command line does not follow a redirect, so the access token is not sent on to another address.
- **Every answer forbids being framed** (`X-Frame-Options: DENY`, `frame-ancestors 'none'`, `nosniff`), the page checks the `Host` like the API does, and every answer authenticated through the deprecated `?access=` address carries the `Deprecation` header.
- **Dispatch and signing**: the runs that exist before a dispatch are noted and only a new one can be taken as ours (no clocks); two new candidates need review; the input `ref` is the commit that was checked; a required workflow is matched with its FILE, never with a visible name; the name of a batch is in UTC.
- **The cleaner of the feed for AIs covers more formats**: names that end in `PASSWORD`, `PWD`, `SECRET` or `TOKEN`, credentials inside an address, webhooks of Slack and Discord, Telegram bot tokens, `glpat-`, `npm_` and `pypi-` tokens, private keys, long hexadecimal strings and the access token of this monitor. `get_run_failure` of the MCP server only reads repositories the monitor watches (or `ai.allowed_repos`).
- **Files edited by hand** (silences, update state) lose only their bad entries, and a bad update state no longer stops the start.
- **Time zones**: Cairo follows its daylight saving time since 2023 in the built-in table, and a zone name the system does not know is refused in the Settings tab. The complete edition reports the red workflows in the header like the lite one, and `monitor_cli.py status` without data ends with exit code 4 like `health`.

## [1.7.5]

The command line takes the access token under its own name, the network mode is safer by default (the address of the computer is hidden from the network, the old ?access= address can be turned off, notification destinations on the local network are refused, a warning about plain HTTP), times for people use your own time zone, an alert can be silenced until the item changes, and the counts and checks that gave wrong answers are corrected.

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
