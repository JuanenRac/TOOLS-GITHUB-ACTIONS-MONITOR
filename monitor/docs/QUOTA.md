<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](QUOTA_spa.md) | [🇫🇷 Français](QUOTA_fra.md) | [🇮🇹 Italiano](QUOTA_ita.md) | [🇩🇪 Deutsch](QUOTA_deu.md) | [🇨🇳 简体中文](QUOTA_zho.md) | [🇯🇵 日本語](QUOTA_jpn.md) | [🇵🇹 Português](QUOTA_por.md)

# More quota, less spending

GitHub gives every account a limited **allowance of API calls**, shared by every tool that uses it. This guide explains how it works and every way the monitor has to spend less of it.

## How the allowance works
- **REST**: 5000 calls an hour per user (60 without a login). **GraphQL** has its own, separate allowance. The `GITHUB_TOKEN` of a workflow in Actions has its own too. A **GitHub App** has an allowance of its own, separate from yours, that grows with the repositories it is installed on (about 10 000 an hour with 130 repositories).
- What counts and what does not: a conditional read that answers `304 Not Modified` (ETag) does not count; asking for `rate_limit` is free; `git push`, `git fetch` and `git clone` do not use the API.

## The ways the monitor saves
1. **Conditional reads** (ETag and `304`): `cache.etag.enabled` (on by default); the page shows how many reads were saved.
2. **Low mode**: only the hot repositories every 4 minutes, the rest every 30; `modes.auto_low` (on) goes in under 1000 calls left and comes back over 2500 or at the renewal; presets in `modes.low`. The bar says that the figures can be old, and how old.
3. **Central panel as a base line**: `central.source` (`off`, `git`, `http`) reads `data/sentinel.json` of your profile repository, refreshed by a workflow with its own token; it spends none of your allowance. `central.max_age_minutes` (120): older than that it is "behind" and not trusted.
4. **One notice when the allowance runs out**: the reads stop until the renewal, the page says "allowance used up until HH:MM" once (not one error per repository), and they resume by themselves.
5. **A GitHub App for the reads** (`github_app.*`), below.
6. **GraphQL for quiet repositories (on by default)**: `network.graphql_checks` reads the repositories that are not hot in batches (`network.graphql_batch`, 20 by default) through GraphQL, which has an allowance of its own; one call replaces many REST calls. It sees only the last commit of the default branch (a workflow that did not run on it is not listed) and gives no durations, attempts or other branches, so the hot repositories and any repository that GraphQL does not answer are still read through REST in the same cycle. The accounting (batches, repositories, points, repositories that went to REST) is in the brief and in the state for the AI tools. It is on by default since a measure on a real account: 40 repositories read in two batches took 2 calls instead of 40 (95 % fewer), every repository was answered and there was no error. Set `network.graphql_checks` to false to read everything through REST.

## A GitHub App, step by step
1. In GitHub, *Settings*, *Developer settings*, *GitHub Apps*, *New GitHub App*. No webhook. **Read-only** permissions: Actions, Checks, Code scanning alerts, Commit statuses, Contents, Dependabot alerts, Issues, Pull requests, Secret scanning alerts and Metadata.
2. *Generate a private key* and keep the `.pem` **outside any repository**, readable only by you.
3. *Install App* on your account, on all the repositories you want to watch.
4. In the monitor: `github_app.enabled` on, `github_app.app_id` (the number of the App) and `github_app.key_path` (only the PATH of the key). `github_app.installation_id` can stay empty.
5. Check it with `GET /api/github-app/status` (this computer only): it shows the name, the installation, the permissions granted and the allowance of the App, never the key or a token. The doctor checks `openssl`, the key file and its permissions.
6. Test the credentials: **Quota tab > Test the token** (or `GET /api/credential/probe`, this computer only) says who the login of the monitor is, whether it is a classic token (and which scopes it lacks for your account) or a fine-grained token or an App, how many repositories it sees (and whether single sign-on cuts the list) and how much allowance is left. With a GitHub App it also says its name, its installation and the permissions it lacks, and when the App is installed on several accounts and none is yours it lists the installations so you can write one in `github_app.installation_id`. Left empty, that setting is found by itself: the installation of the account the monitor watches, or the only one. At most one real check is made every 10 seconds; nothing is written to GitHub and no token or key is shown.

Security: the monitor reads the key into memory only to sign a JWT of at most ten minutes (with the standard library, no `openssl` needed; `openssl` is only the fallback) and never copies, prints or logs it. The installation token lasts an hour, stays in memory and is renewed five minutes early. **Only reads** use it; writes and actions keep your token. If the App fails or lacks a permission, the read is made again with your token. The page shows both allowances.

## When several tools share the same allowance
Every tool of the account spends the same 5000 calls an hour. A good pattern: one small wrapper around `gh` with a **shared cache** of a couple of minutes, a **reserve** (it refuses to call when fewer than about 1000 are left, except for what is urgent), work that needs fresh data **right after the renewal**, and never `gh run watch` (it polls). For example, a wrapper that stores the answer of each read in a temporary file named after the command and serves it again for 120 seconds, and checks `gh api rate_limit` before any other call.

## What NOT to do
Do not use several accounts or several tokens of the same user to get around the limit: it is against the rules of GitHub and it can get the account blocked. Use an App, the central panel and Low mode.

## Settings
| Setting | Default |
|---|---|
| `cache.etag.enabled` | on |
| `modes.auto_low` / `modes.auto_low_enter` / `modes.auto_low_exit` | on / 1000 / 2500 |
| `modes.low.*` (`refresh_seconds`, `cold_refresh_seconds`, `runs_per_repo`, `hot_hours`) | 240 / 1800 / 10 / 2 |
| `min_rate_remaining` | 800 |
| `central.source` / `central.max_age_minutes` | off / 120 |
| `github_app.enabled` / `github_app.app_id` / `github_app.key_path` / `github_app.installation_id` | off / empty / empty / empty |

## Troubleshooting and FAQ
- *"allowance used up until HH:MM"*: wait; the monitor resumes by itself. Other tools may be spending it: look at theirs.
- *The figures are old*: Low mode is on (chosen or automatic); the bar says so.
- *The App does not work*: look at `/api/github-app/status` and the doctor: openssl, the key path, the permissions.
- *Does `git fetch` cost allowance?* No. See also [QUOTAS.md](QUOTAS.md) (plans and minutes) and [MODES.md](MODES.md).

## The Quota tab and a second account
Everything about the allowance is in one place: *Settings*, tab *Quota*. It groups the modes (`modes.auto_low`, `modes.auto_low_enter`, `modes.auto_low_exit` and the values of Low in `modes.low.*`), the saving (`network.etag`, together with `cache.etag.enabled`), the central panel (`central.source`, `central.max_age_minutes`), the GitHub App (`github_app.*`) and a **second account for the reads**. The buttons of the tab show the allowance of every source (your login, the App, the second account) with the hour of renewal, test the App and the second account, list the permissions the App lacks, and apply the recommended values or the defaults.

The second account (`extra_reader.enabled`, `extra_reader.file`) is a read-only account whose fine-grained token sits in a text file outside any repository, readable only by you; the setting holds ONLY the path of that file. The monitor reads the token at the moment of use, keeps it in memory and never stores, prints or logs it. The reads are spread over your login, the App and the second account according to the calls each one has left (the figure of the free `rate_limit` call, minus the reads made since); a source that is refused is left out for five minutes and the read is made again with the next one. Writes and actions never use it. It is for an account of your own (for example a second account you own with read access to the repositories), not a way to get around the limit with other people's accounts. The file must be inside the accounts folder of the monitor (`accounts/`, or the folder named by `MONITOR_ACCOUNTS_DIR`) and is never read through a link; `extra_reader.any_folder` (off by default) lifts the folder rule. What depends on who asks (your account, its organisations, the notifications, a search for `@me`, `gh auth`, `gh repo list` without an owner) is always answered by your own login, and only a plain `gh api ENDPOINT` read (with at most the options `--jq`, `--paginate`, `-H`, `-i` and `--cache`) is spread over the sources: any other call goes to your login.

## The program openssl and one monitor for each port

The monitor looks for `openssl` in the PATH and, if it is not there, where Git for Windows keeps it (`Git\usr\bin`, `Git\mingw64\bin` in Program Files and in the user's Programs) and in the usual folders of macOS and Linux, so a monitor started from a `.bat` or a service finds it. `github_app.openssl_path` (an absolute path to the program) chooses one by hand. `/api/github-app/status` shows `openssl` and `openssl_path`, and the doctor says which one signs when it is not the one of the PATH.

On Windows the port of the monitor is bound for the monitor alone (SO_EXCLUSIVEADDRUSE): two processes can no longer listen on 8765 at the same time. And a monitor that starts while another monitor already answers on its port says so and stops instead of looking for another port.

## Sharing the allowance: preferred source and reserve

By default each read goes to the source (user, GitHub App, second account) with the most calls left. The block `readpool` changes that, in the Quota tab of the settings, with the conservative defaults of always (`auto`, reserve 0):

- `readpool.prefer.<kind>` (`auto`, `user`, `app`, `extra`): the source that answers a KIND of read first. The kinds are told by the call: `runs` (runs, workflows, checks), `security` (code scanning, Dependabot, secret scanning), `issues` (issues and pull requests), `history` (releases, commits, tags, contents), `discovery` (organisations, search, repository lists) and `other`. If the preferred source fails or is under its reserve, the others answer, the user last.
- `readpool.reserve.<source>` (0 to 4000): calls kept free in that source. While a source has no more calls left than its reserve, the monitor does not read with it if another source can. Use `readpool.reserve.user` to leave calls to the `gh` of your tools and agents.
- `quota.failover` (off by default): a read that answers 429 or "rate limit exceeded" is made once more with another source that can read, and the source that ran dry counts as spent until its next free check. When every source is spent the last good copy of that read is shown with its age instead of an error (`quota.failover_max_age_minutes`, 60 by default, 1 to 1440; an older copy is not shown). A limit is never taken for a refusal of permission, a write never fails over, and `GET /api/quota-pool/status` has the block `failover` with how many times it acted.

Writes and actions always use the token of the user. The bar of the allowance and the working modes (fast and turbo) count the SUM of all the sources: the tile shows the sum and its tooltip the figure of each source, and the Quota tab (State) adds a line with the total next to the allowance of the user, the App and the second account.

## Read less: the webhook first and free sources

Both ways are **off by default** and only touch quiet repositories (those whose latest runs are all finished and green). A repository that is running, red or touched by an event is read as always.

- `savings.webhook_first`: while the incoming webhook is alive (it delivered an event in the last `savings.webhook_window_minutes`), a quiet repository is not read on its slow turn: GitHub tells when something happens. It is still read in full every `savings.webhook_full_minutes`. Without a live webhook nothing changes.
- `savings.webhook_live_per_repo`: makes "alive" a thing of each repository. Only a quiet repository whose OWN events arrived in the last `savings.webhook_window_minutes` skips its slow read; one whose webhook was never set up, or broke, is read as always while the others are spared. It spares fewer reads, and the Webhook panel counts the repositories that are alive by themselves. Off by default; it works together with `savings.webhook_first`.
- `savings.feeds.enabled`: before a quiet repository is read with the API, the newest commit of its default branch is asked from a source that costs no allowance - the public Atom feed of the commits, `git ls-remote`, or either (`savings.feeds.method`: `atom`, `git`, `auto`). If it is the commit of the last full read, the repository is left as it is. Every `savings.feeds.max_age_minutes` it is read in full anyway. Public repositories only: for a private one, an error or an odd answer the repository is read with the API as always. Only GET requests to github.com leave the computer, never a password, and nothing is written. Not used when the monitor is air-gapped.

What it costs: a run that starts without a push (a schedule, a re-run) on a quiet repository is seen at the next full read, not at once. The Quota tab (State) shows the reads each way has spared since the monitor started (about one call of the API each): conditional reads, GraphQL, webhook first, Atom feed, git and the central panel.

## Large accounts: what the list of runs covers, and a budget

A repository that starts hundreds of runs an hour fills a list of 20-100 runs in minutes, so an older failure or a workflow that runs rarely is simply not in it. The monitor says so instead of looking green:

- **Coverage**: the Repositories table shows how far back each list reaches. A full list that reaches back less than `sampling.min_coverage_minutes` is marked *low coverage*; a list shorter than what was asked for is *complete* (it holds the whole history); a total of 2,500 or 40,000 is where GitHub stops counting, so it is shown as *at least*. The block `sampling` of `GET /api/data` has the same figures.
- **Second look**: with `sampling.default_branch_probe` on, a full list also asks for the pushes to the default branch (pull requests left out), one more request per read, so the runs that decide red on main are not pushed out by pull requests and schedules.
- **Look at the running runs**: with `sampling.active_probe` on, a full list also asks, in two light requests, for the runs still `in_progress` and the runs `queued`, so a long run that started before the window of the list is not lost or shown as finished. Two more requests per full repository per read; off by default.
- **A2 together**: a repository with `sentinel.a2_resolve_batch_min` or more workflows to look up is asked once for its newest completed runs of the default branch (`sentinel.a2_resolve_batch_pages` pages of 100 at most) and they are settled together; what that list does not show is asked one by one. With 100 or more workflows this takes a few cycles instead of four workflows per cycle.
- **Budget**: `sampling.api_budget_per_hour` (0 = none) limits the requests for run lists in an hour. Past it the repositories with a red workflow are read first, a tenth of the budget is always kept for them, and the rest wait; the page says how many. The estimate of requests per hour for the number of repositories and the intervals is shown from 3,500 on (GitHub allows 5,000 an hour), or whenever a budget is set.

The defaults change nothing for an account with a few repositories: the second look and the budget are off, and the mark of low coverage only appears when a full list reaches back less than half an hour.

## When the App is on and is not used

If `github_app.enabled` is on but the App cannot give a token, the reads go on with your token and the allowance is the smaller one of the user. It is never silent: the doctor turns amber with the cause, a failure is noted once in the list of swallowed failures, and the Quota tab shows a line `GitHub App` with the cause and the limit in use. The causes: the key cannot be read or is not an RSA key without a passphrase (`key_unreadable`), the key could not sign (`sign_failed`), the App is not installed on the account (`app_not_installed`), GitHub refused the token (`token_refused`) and the App is on without its number or key file (`not_configured`). The same note is in `GET /api/quota` as `app` and in `GET /api/github-app/status` as `signer` and `code`.
