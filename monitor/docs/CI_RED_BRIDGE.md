<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](CI_RED_BRIDGE_spa.md) | [🇫🇷 Français](CI_RED_BRIDGE_fra.md) | [🇮🇹 Italiano](CI_RED_BRIDGE_ita.md) | [🇩🇪 Deutsch](CI_RED_BRIDGE_deu.md) | [🇨🇳 简体中文](CI_RED_BRIDGE_zho.md) | [🇯🇵 日本語](CI_RED_BRIDGE_jpn.md) | [🇵🇹 Português](CI_RED_BRIDGE_por.md)

# From the monitor to the dashboard: `ci_red.json`

What the monitor writes, how to export it and what a reader of the file needs. The monitor only reads GitHub and writes local files: it never pushes, never commits and never closes anything on its own.

## What the monitor writes

`ci_red.json` next to `bin/actions_monitor.py`, refreshed after every sentinel pass (schema 2):

| Field | Meaning |
|---|---|
| `schema` | `2`. Fields are only ever added, never renamed. |
| `generated` | UTC time of the pass. |
| `tool_version` | Version of the tool that wrote the file. |
| `complete` | `true` when every watched repository was read in that pass. `false` while loading, when the API quota ran short or when clones are missing: do not act on the list of red repositories or on the signing queue until it is `true`. |
| `red_repos` / `pending_sign_repos` | Counts. |
| `repos.<NAME>.ecosystem` | `armor`, `urtc`, `hydra`, `eh3d` or `other`. |
| `repos.<NAME>.red[]` | One entry per workflow whose latest completed run on the default branch failed: `workflow`, `conclusion`, `since`, `streak`, `url`. |
| `repos.<NAME>.pending_sign[]` and `pending_sign_hours` | Releases built and not signed yet, and the age of the oldest. |

## How to export it

```
py -3 bin/read_report.py --export-status DIR          # ci_status_public.json + .md, only what may be published
py -3 bin/read_report.py --export-sign-queue FILE     # the signing queue
```

Both read the running monitor on `127.0.0.1` (no GitHub quota). They refuse to write while the snapshot is loading and tell why; the exit code is not zero in that case.

## What a reader (the dashboard generator) needs

1. Read `schema`; accept any value `>= 2` and ignore unknown fields.
2. Read `complete`; when it is `false`, keep the last complete export instead of replacing it.
3. Show `generated` next to the numbers so a stale file is obvious.
4. Use `repos.<NAME>.red[].url` as the link; never rebuild it.

## What the monitor does not do

It does not publish the file, does not push to the profile repository and does not touch any workflow. Carrying the export to the dashboard is a step of the owner (or of a workflow of the profile repository that reads the exported file).

## The profile dashboard (consumer contract)

The status dashboard of a profile repository can read the same document in two ways: from the running monitor (`GET /api/outputs/dashboard.json`, off until `outputs.dashboard.enabled` is on, this computer only) or from the file written by `py -3 bin/read_report.py --export-status DIR` (red workflows only, never the signing side). What the dashboard may rely on, checked by a test of this repository:

1. `schema` is `2` and fields are only ever added.
2. The served document is exactly the one of `ci_red.json`.
3. `complete: false` means: keep your last complete picture.
4. The public export has the keys `schema`, `generated`, `tool_version`, `complete`, `red_repos` and `red`, and nothing of the signing state.

The monitor never pushes the file to the profile repository; carrying it there is a step of its owner.
