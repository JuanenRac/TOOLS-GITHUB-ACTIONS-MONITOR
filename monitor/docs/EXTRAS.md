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

`github_app.share_reads`: the command below prints, on this computer, an installation token of your GitHub App that lasts one hour, so that the `gh` of your tools and agents reads with the allowance of the App and not with yours (`GH_TOKEN`). The token goes only to the standard output, never to a file or a log, and the command needs `--read-only`; give the App read-only permissions when you create it. Without `github_app.share_reads` it refuses.

```
python bin/monitor_cli.py gh-token --read-only
```

## Not here yet

The workflow hygiene panel, the queue report, the release ready or blocked view and the supply chain panel are not part of this version.
