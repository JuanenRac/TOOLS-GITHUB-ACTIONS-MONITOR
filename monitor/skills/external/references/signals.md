<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Signals and panels

Generated from the code. `GET /api/ai/state` lists the signals the monitor says now, each with a level (`act` somebody has to do something, `watch` keep an eye on it, `info` nothing to do) and rows with
the repository, a link, how old it is and the next step. `GET /api/sentinel/panels` gives the panels of the Sentinel as data.

| signal | what it says |
| --- | --- |
| `alerts.issues` | open issues of failed builds |
| `alerts.unresolved` | workflows red on the default branch (act when there is one) |
| `connection` | online or offline since |
| `health.central` | the central panel read without allowance and whether it is trusted |
| `health.doctor` | warnings of the doctor: timezone, risks, failures swallowed on purpose (degraded) |
| `health.mode` | the working mode (normal, fast, turbo, low) |
| `health.refresh` | how old the data is (stale means the picture is old) |
| `now.fail24` | failures and successes of the last 24 hours |
| `now.runs` | running, queued and stuck runs (level act when a run is stuck) |
| `quota` | the allowance of the API: low, used up or fine |
| `quota.accounting` | conditional reads answered 304 and reads spared |
| `quota.trend` | who spends the allowance (the monitor or other tools) |
| `repos.errors` | repositories read without data |
| `sentinel.` | the panel `` of the Sentinel: ui._title |
| `sentinel.a1` | the panel `a1` of the Sentinel: A1 · Stuck or failed builds |
| `sentinel.a10` | the panel `a10` of the Sentinel: A10 · Actions and releases surface |
| `sentinel.a11` | the panel `a11` of the Sentinel: A11 · Release readiness, ecosystem health and pins |
| `sentinel.a12` | the panel `a12` of the Sentinel: A12 · Analytics: durations, queue time, steps and flaky workflows |
| `sentinel.a13` | the panel `a13` of the Sentinel: A13 · Workflow linter |
| `sentinel.a2` | the panel `a2` of the Sentinel: A2 · Red CI (last run of each workflow on main) |
| `sentinel.a3` | the panel `a3` of the Sentinel: A3 · Security alerts |
| `sentinel.a4` | the panel `a4` of the Sentinel: A4 · Dependabot pull requests |
| `sentinel.a5` | the panel `a5` of the Sentinel: A5 · Releases |
| `sentinel.a6` | the panel `a6` of the Sentinel: A6 · Repository hygiene |
| `sentinel.a7` | the panel `a7` of the Sentinel: A7 · Usage |
| `sentinel.a8` | the panel `a8` of the Sentinel: A8 · Audits and rounds |
| `sentinel.a9` | the panel `a9` of the Sentinel: A9 · GitHub roadmaps |
| `sentinel.collab` | the panel `collab` of the Sentinel: Issues and pull requests |

## Panels of the Sentinel

| panel | title |
| --- | --- |
| `a1` | A1 · Stuck or failed builds |
| `a2` | A2 · Red CI (last run of each workflow on main) |
| `a3` | A3 · Security alerts |
| `a4` | A4 · Dependabot pull requests |
| `a5` | A5 · Releases |
| `a6` | A6 · Repository hygiene |
| `a7` | A7 · Usage |
| `a8` | A8 · Audits and rounds |
| `a9` | A9 · GitHub roadmaps |
| `a10` | A10 · Actions and releases surface |
| `a11` | A11 · Release readiness, ecosystem health and pins |
| `a12` | A12 · Analytics: durations, queue time, steps and flaky workflows |
| `a13` | A13 · Workflow linter |
| `collab` | Issues and pull requests |
