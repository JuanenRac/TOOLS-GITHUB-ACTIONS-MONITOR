<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](CI_RED_SCHEMA_spa.md) | [🇫🇷 Français](CI_RED_SCHEMA_fra.md) | [🇮🇹 Italiano](CI_RED_SCHEMA_ita.md) | [🇩🇪 Deutsch](CI_RED_SCHEMA_deu.md) | [🇨🇳 简体中文](CI_RED_SCHEMA_zho.md) | [🇯🇵 日本語](CI_RED_SCHEMA_jpn.md) | [🇵🇹 Português](CI_RED_SCHEMA_por.md)

# ci_red.json - schema 2 (stable contract)

`ci_red.json` is the snapshot the monitor writes (atomically, next to itself by default) so that any consumer can read the CI state without asking
the monitor or GitHub: a dashboard, a script, a notification hook. The format is **stable: fields are only ever added, never renamed or removed**.
Read it with `.get()`; ignore fields you do not know.

Where it goes is set in `actions_monitor.json`:

| key (`sentinel.`) | meaning |
|---|---|
| `ci_red_file` | `""` = `ci_red.json` next to the monitor (default); `"off"` = not written; a path = there (relative paths are relative to the monitor folder; a D: drive, a UNC path or a drive the running system cannot use is refused) |
| `ci_red_audit_copy` | `true` also copies it into the audit folder when that folder exists |

## Shape

```json
{
  "schema": 2,
  "generated": "2026-01-01T12:00:00Z",
  "tool_version": "1.2.0",
  "complete": true,
  "red_repos": 1,
  "pending_sign_repos": 1,
  "pending_sign_hours_threshold": 24,
  "repos": {
    "REPO": {
      "ecosystem": "armor | urtc | hydra | eh3d | other",
      "red": [{"workflow": "CI", "conclusion": "failure", "since": "2026-01-01T10:00:00Z", "streak": 2, "url": "https://github.com/OWNER/REPO/actions/runs/1"}],
      "pending_sign_hours": 31.5,
      "pending_sign": [{"workflow": "firmware-build.yml", "hours": 31.5, "state": "built_on_gha | signed_local",
                         "signature_kind": "none | dev | release", "signature_verified": true,
                         "last_build_at": "2026-01-01T08:00:00Z", "url": "https://github.com/OWNER/REPO/actions/runs/2"}]
    }
  }
}
```

* `complete` is `false` while the sentinel is still loading: do not treat a missing repository as green in that case.
* `signature_verified` is `true`, `false` or the string `"unknown"` (never a guess: formats this tool cannot check are `"unknown"`).
* `pending_sign*` fields describe the **local signing side** and are for your own local tools. A public consumer should ignore them.

## The rule of "red" (one definition, everywhere)

Look at the **last completed run of each workflow on the default branch**. It is red when its conclusion is `failure`, `timed_out`,
`startup_failure` or `action_required` (it waits for an approval). `cancelled`, `skipped`, `neutral` and `stale` say nothing and are ignored.
"Green" for the signing state uses the same list of runs. A consumer that recomputes the rule from the workflow runs must use exactly this
definition to agree with the monitor.

## Publishing is a separate, explicit step

**Decision: this PC does not publish `ci_red.json` and does not publish `pending_sign` or any other part of the signing side to a repository, a dashboard or any
service.** The file stays on the machine (and, when `ci_red_audit_copy` is on, in the local audit folder). A public dashboard must recompute the red list from the
public workflow runs with the rule below, or use the export described next, which never carries the signing state.

Nothing in the monitor publishes this file to a repository. If a public dashboard needs the red list, either let it recompute the rule from the
public run data, or export the non-sensitive part yourself:

```
python3 read_report.py --export-status DIR
```

This writes `ci_status_public.json` and `ci_status_public.md` into the folder you name and **only** the list of red workflows (repository,
ecosystem, workflow, conclusion, since, streak, run link). No signing state, no key names, no local paths, no commands. The tool never commits or
pushes; what happens to the folder afterwards is up to you.

`python3 read_report.py --export-sign-queue FILE` (`.json` or `.csv`) writes the global signing queue with the exact local commands. That file is
for the PC that runs the monitor and says so inside.
