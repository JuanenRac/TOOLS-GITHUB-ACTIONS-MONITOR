<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](COLLAB_spa.md) | [🇫🇷 Français](COLLAB_fra.md) | [🇮🇹 Italiano](COLLAB_ita.md) | [🇩🇪 Deutsch](COLLAB_deu.md) | [🇨🇳 简体中文](COLLAB_zho.md) | [🇯🇵 日本語](COLLAB_jpn.md) | [🇵🇹 Português](COLLAB_por.md)

# The Collab sentinel: issues and pull requests

A second sentinel next to the CI one. It looks at the **open issues and pull requests** of your repositories and tells you what needs a person: forgotten issues, critical labels, reviews that nobody does, drafts that never end, conflicts that stay. It runs on a clock of its own, never changes what the CI sentinel decides, and **never writes to GitHub**. It belongs to the complete edition; the lite edition does not load it.

## Switch it on

It is off by default. Settings > Sentinel > Issues and pull requests, or in `actions_monitor.json`:

```
"sentinels": {"collab": {"enabled": true, "refresh_seconds": 600, "max_repos_per_tick": 10, "repos": "all",
  "rules": {"issue_stale_days": 14, "issue_critical_labels": ["security", "critical"], "pr_review_pending_days": 3,
            "pr_draft_max_days": 30, "pr_conflict_days": 7, "watch_external_comments": false, "ignore_labels": ["monitor:ignore"]}}}
```

`repos` is `"all"`, a list of repositories or `{"ecosystems": [...]}`.

## The rules (stable codes)

| Code | Level | When |
|---|---|---|
| `collab.issue.stale` | warning | an open issue with no activity for `issue_stale_days` |
| `collab.issue.critical` | error | an open issue with one of `issue_critical_labels`, whatever its age |
| `collab.issue.external` | warning | (only with `watch_external_comments`) an issue by someone outside the team that nobody answered after a day |
| `collab.pr.review_pending` | warning | a pull request with a requested review that has waited `pr_review_pending_days` |
| `collab.pr.draft_old` | info | a draft pull request open for `pr_draft_max_days` |
| `collab.pr.conflict` | warning | a pull request with conflicts for `pr_conflict_days` |

Bots are left out. The defaults are slow on purpose: a draft that waits for months is normal in many teams.

## What it costs

A round reads at most `max_repos_per_tick` repositories, two conditional requests each (a repository that did not change costs no allowance) and up to six pull request details per round. It stops while the allowance is below `min_rate_remaining`. The state is kept in `collab_state.json` (inside the folder of the account when there are several), so a restart announces nothing twice.

## Less noise: ignore and silence

- **Ignore label**: put a label from `ignore_labels` (`monitor:ignore` by default) on the issue or pull request **on GitHub** and Collab raises no alert for it. The monitor never writes labels itself.
- **Silence in the monitor**: in the Alerts tab, each alert has buttons to silence this alert, its rule or the whole sentinel for `alerts.mute_hours` hours (24 by default, 1 to 720). It lapses by itself, can be restored at any time, and the tab keeps a short history of what was silenced and until when. It is a note of this monitor; nothing changes on GitHub. In the network mode a silence can only be made (and lifted) from the computer where the monitor runs (`this_computer`); a client of the network sees the silences and cannot change them. This stays so until a later edition has users of its own. A silence of one alert can also last "until the item changes" (`until_change` in the request of `POST /api/alerts/mute`): it ends at once when the `updated_at` of the issue or pull request changes, or at the end of the hours, whichever comes first.

## Where you see it

- The **Alerts** tab: one list for every sentinel, a filter by origin (CI, Collab) and by level, and the silenced ones on request.
- The Sentinel tab: the layer *Issues and pull requests*.
- `GET /api/alerts?sentinel=collab&level=&muted=show|hide|only` and `GET /api/sentinel/collab`; `GET /api/events?sentinel=collab&since=` for the events (`collab_new`, `collab_fixed`, also sent by the notification channels when you pick them; see NOTIFICATIONS).

## Limits

Only the first 100 open issues and 100 open pull requests of a repository are read, the most recently updated first. Collab proposes nothing and executes nothing; actions on issues and pull requests belong to a later edition.
