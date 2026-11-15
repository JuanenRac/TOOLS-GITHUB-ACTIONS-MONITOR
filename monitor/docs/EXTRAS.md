<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](EXTRAS_spa.md) | [🇫🇷 Français](EXTRAS_fra.md) | [🇮🇹 Italiano](EXTRAS_ita.md) | [🇩🇪 Deutsch](EXTRAS_deu.md) | [🇨🇳 简体中文](EXTRAS_zho.md) | [🇯🇵 日本語](EXTRAS_jpn.md) | [🇵🇹 Português](EXTRAS_por.md)

# Optional extras

Both are **off by default** and are switched on in the Settings.

## The log of the failed step

`logs.failed_step.enabled`: an alert of a failed run gets a button **Failed step**. One press reads the jobs and the failed log of that run from GitHub (two calls of your allowance), shows the failing step and its last relevant lines (`logs.failed_step.lines`, `logs.failed_step.max_bytes`) and keeps the answer in memory, so pressing again costs nothing. The text is cleaned of tokens, keys, addresses and the home folder. Only repositories the monitor watches can be asked, through `GET /api/run-log?repo=&run=`; in the team mode only an administrator.

## A read-only token of the GitHub App for your tools

`github_app.share_reads`: the command below prints, on this computer, an installation token of your GitHub App that lasts one hour, so that the `gh` of your tools and agents reads with the allowance of the App and not with yours (`GH_TOKEN`). The token goes only to the standard output, never to a file or a log, and the command needs `--read-only`; give the App read-only permissions when you create it. Without `github_app.share_reads` it refuses. The token is asked for apart from the one the monitor keeps, with read permissions only; if the answer carries any write permission the command refuses to print it.

```
python bin/monitor_cli.py gh-token --read-only
```

## Four optional reports

All four are off by default. They appear in a block "Optional reports" at the bottom of the Alerts tab and in `GET /api/reports`. The ones that read GitHub spend at most `reports.max_calls_per_cycle` calls in a cycle, read a few repositories each time and keep what they read in memory for a day.

- `reports.workflow_hygiene.enabled`: reads the workflow files of the repositories and lists what is badly written - actions not pinned to a commit, permissions not limited, a job without `timeout-minutes`, no `concurrency` group, `pull_request_target` and injection risks, secrets in clear (the rules of the linter of the panel A13, which reads local clones, plus the two new ones).
- `reports.queue.enabled`: reads the jobs of a few finished runs that waited and says how long a job waited before it started for each kind of runner (Linux, Windows, macOS, larger, self-hosted).
- `reports.release_view.enabled`: no call at all; from what the Sentinel knows it says which repositories are READY for a release (entries in the changelog or a green build nobody released, nothing red, no signature waiting) and which are BLOCKED, and why.
- `reports.supply_chain.enabled`: reads the latest release of the repositories and says, by the names of its files, whether it carries a software bill of materials (SBOM), checksums and a signature or attestation. The files are never downloaded.
