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
GraphQL is not used for the runs of the workflows: it does not offer them.

## A GitHub App, step by step
1. In GitHub, *Settings*, *Developer settings*, *GitHub Apps*, *New GitHub App*. No webhook. **Read-only** permissions: Actions, Checks, Code scanning alerts, Commit statuses, Contents, Dependabot alerts, Issues, Pull requests, Secret scanning alerts and Metadata.
2. *Generate a private key* and keep the `.pem` **outside any repository**, readable only by you.
3. *Install App* on your account, on all the repositories you want to watch.
4. In the monitor: `github_app.enabled` on, `github_app.app_id` (the number of the App) and `github_app.key_path` (only the PATH of the key). `github_app.installation_id` can stay empty.
5. Check it with `GET /api/github-app/status` (this computer only): it shows the name, the installation, the permissions granted and the allowance of the App, never the key or a token. The doctor checks `openssl`, the key file and its permissions.

Security: the monitor never reads, copies, prints or logs the key; it hands its path to `openssl`, which signs a JWT of at most ten minutes. The installation token lasts an hour, stays in memory and is renewed five minutes early. **Only reads** use it; writes and actions keep your token. If the App fails or lacks a permission, the read is made again with your token. The page shows both allowances.

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
