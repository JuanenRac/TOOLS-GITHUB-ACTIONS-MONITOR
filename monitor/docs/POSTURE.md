<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](POSTURE_spa.md) | [🇫🇷 Français](POSTURE_fra.md) | [🇮🇹 Italiano](POSTURE_ita.md) | [🇩🇪 Deutsch](POSTURE_deu.md) | [🇨🇳 简体中文](POSTURE_zho.md) | [🇯🇵 日本語](POSTURE_jpn.md) | [🇵🇹 Português](POSTURE_por.md)

# Posture of repositories and organization

A list of checks, read only, of how your repositories and organization are protected: webhooks, Actions settings, scanning, branches, deploy keys, secret age, apps, releases. Nothing is changed on GitHub. Complete and Full editions; off by default.

## Turn it on

Set `posture.enabled` (Settings > Posture). A few repositories are read per cycle (`posture.repos_per_cycle`), each at most every `posture.refresh_hours`; this uses GitHub allowance. `posture.org_checks` adds the organization.

## What is checked

Each finding carries its place in the OWASP Top 10 CI/CD risks and in the CIS Software Supply Chain guide. The mapping helps to read; it is not a certification.

| Area | Identifiers |
|---|---|
| Webhooks | webhook.no_secret webhook.plain_http webhook.tls_off |
| Actions | actions.token_write actions.approves_prs actions.all_allowed actions.sha_not_required actions.fork_approval |
| Code and dependencies | scan.no_code scan.no_credentials scan.no_push_protection scan.no_dependency_alerts repo.no_policy repo.no_update_tool |
| Branches | branch.unprotected branch.no_review branch.bypass branch.release_unprotected branch.merged_unreviewed |
| Keys and secrets | deploy.write deploy.old stored.old |
| Organization | org.no_two_factor org.default_write org.public_creation org.app_broad org.settings_changed |
| Runners | runner.not_hardened runner.coverage_lost |
| Releases | release.asset_replaced release.asset_removed release.tag_moved release.outside_window |

## Honest coverage

What GitHub refuses or does not answer is listed as **not checked**, never as fine, and earlier findings of that area stay. Many settings need administrator read rights: the report lists the permission each group of checks needs and which were refused. Of a webhook only the host is kept; of a secret only name and dates. Releases are compared with what the monitor saw before, so the first read only remembers. Archived repositories and forks are skipped.

## Baseline and options

`posture.profile` is basic or strict. `posture.types` gives patterns a kind (`standard`, `library`, `internal`, `sandbox`), each with its own baseline; `posture.skip` leaves checks out. `posture.release_branches` are protected-branch patterns. `posture.deploy_max_days` and `posture.stored_max_days` set ages. Off until you ask: `posture.audit_log` (organization audit log, GitHub Enterprise), `posture.review_sample` (merged changes without approval), `posture.runner_runs` (hardening step in what actually ran). `posture.releases` watches replaced files and moved tags; `posture.release_window` sets the hours of publication.

## Where to see it

The Security tab of the Sentinel area shows the findings, the maturity of the security pipeline of each repository, a history per day and the permissions. `posture.alerts` puts each finding in the Alerts tab, where it can be silenced. API: `GET /api/posture`. Command line:

```
posture status
posture matrix
posture check --repo-name my-repo
```

## Limits

Not read: fine-grained tokens of organization members (GitHub only lists them to a GitHub App), and a second, writing app is not managed. The organization checks have been tested with made-up answers only.
