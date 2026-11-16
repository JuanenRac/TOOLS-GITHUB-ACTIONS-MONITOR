<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](ORGANIZATIONS_spa.md) | [🇫🇷 Français](ORGANIZATIONS_fra.md) | [🇮🇹 Italiano](ORGANIZATIONS_ita.md) | [🇩🇪 Deutsch](ORGANIZATIONS_deu.md) | [🇨🇳 简体中文](ORGANIZATIONS_zho.md) | [🇯🇵 日本語](ORGANIZATIONS_jpn.md) | [🇵🇹 Português](ORGANIZATIONS_por.md)

# Organizations and big accounts

How to point the monitor at an organization, or at a personal account with hundreds of repositories, and what to do when a read comes back empty.

## 1. The smallest token that works

The monitor only reads. Use the login of `gh` (`gh auth login`) or a token in `GH_TOKEN`, and give it the least it needs.

| Kind of token | What to give it |
|---|---|
| **Classic** (personal access token) | `repo` for private repositories (`public_repo` is enough when everything is public) and `read:org` to list the repositories and teams of an organization. Optional: `security_events` (code scanning alerts, panel A3), `read:project` (the Projects boards, panel A9). It does not need `workflow` or any write scope. |
| **Fine-grained** | One *resource owner* only: create one token per organization (or per personal account). Repository access: all repositories, or the selected ones. Read-only permissions: Metadata, Actions, Contents, Pull requests, Issues, Administration (rulesets and branch rules), Code scanning alerts, Dependabot alerts, Secret scanning alerts. An organization can require an owner to approve the token first. |
| **GitHub App** | Reads with the allowance of the App instead of yours (see `QUOTA.md`). |

A **personal account** (`github_owner` is a user) needs nothing more than the above for its own repositories. The repositories of an organization you belong to are read with a token whose resource owner (fine-grained) or scopes (classic) include that organization.

## 2. Single sign-on (SSO) and private repositories

If the organization enforces SAML single sign-on, a classic token must be authorised for it: on GitHub open *Settings > Developer settings > Personal access tokens*, choose the token and press *Configure SSO > Authorize*. A login made with `gh auth login` is authorised in the browser when you accept the organization. Until then GitHub answers `403` (*Resource protected by organization SAML enforcement*) or, worse, answers `200` with the private repositories left out (the header `X-GitHub-SSO: partial-results`), which looks like an organization with few repositories.

A token that cannot see a private repository gets `404`, exactly as if it did not exist. So an empty answer can mean: SSO not authorised, a missing scope or permission, a private repository the login cannot see, or no Actions at all. The next section tells them apart.

## 3. `--doctor` explains it

`py -3 bin/actions_monitor.py --doctor` (also `bin/monitor_cli.py doctor`) makes three small reads and reports two lines:

- **The login can read the account or organization** (`access`): `ok` with the login and its scopes; or `warn` with the cause in the detail: `sso` (not authorised, or private repositories hidden), `rate_limited`, `scope` (a permission is missing), `not_found` (the account does not exist or is not visible), `forbidden`; `fail` when GitHub refuses the credentials. A fine-grained token has no scopes to list and the line says so.
- **The reads an hour fit the allowance** (`estimate`): the repositories of the account and the reads an hour the current settings would need, against the 5,000 an hour of a personal token. It is an estimate with no call: the polling of the runs (a tenth of the repositories hot, refreshed every `refresh_seconds`; the rest every `cold_refresh_seconds`), the Sentinel (at most `sentinel.budget_per_hour`) and, when the workflow files are read without clones, their share. `warn` above 60 %. To lower it: raise `cold_refresh_seconds`, turn on Low mode, watch fewer repositories (`repos`), or read with a GitHub App.

The same causes are written, with the repository, wherever the monitor could not read workflow files: the Sentinel panel A13 lists them as *not evaluable* with the reason, never as a silent "no data".

## 4. Watching an account you do not own (observer without permissions)

Any token can read the public repositories of any account, so you can watch an open-source organization with a token that has no scope at all. What an observer does not get, and the monitor treats as *unknown* and never as *fine*: rulesets and branch protection, Dependabot, code scanning and secret scanning alerts, settings, and the run lists of repositories with Actions disabled. Panels that depend on them (A3, parts of A6) are empty or marked not evaluable for those repositories. Nothing is ever written, so no write permission is needed.

## 5. Known limits

- The allowance is 5,000 reads an hour for a personal token; a GitHub App installed on a large organization has more (see `QUOTA.md`). The estimate above is the quickest way to know whether you fit.
- The monitor reads a sample of the latest runs of each repository. A repository that starts hundreds of runs an hour is seen through that sample, not run by run.
- GitHub keeps the logs and artifacts of a run for 90 days by default; the monitor cannot read what GitHub has deleted.
- A fine-grained token belongs to one owner: watching two organizations needs two tokens (two accounts of the monitor, see `ACCOUNTS.md`).
- Organizations that require approval of tokens, or block classic tokens, need an owner to act first; no setting of the monitor can bypass that.
