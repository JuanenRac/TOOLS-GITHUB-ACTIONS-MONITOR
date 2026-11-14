<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](CONSOLE_TOOLS_spa.md) | [🇫🇷 Français](CONSOLE_TOOLS_fra.md) | [🇮🇹 Italiano](CONSOLE_TOOLS_ita.md) | [🇩🇪 Deutsch](CONSOLE_TOOLS_deu.md) | [🇨🇳 简体中文](CONSOLE_TOOLS_zho.md) | [🇯🇵 日本語](CONSOLE_TOOLS_jpn.md) | [🇵🇹 Português](CONSOLE_TOOLS_por.md)

# Console tools: workflow linter and terminal view

Two optional command line tools. The monitor itself needs no package; the terminal view uses Rich when you ask for it.

## The workflow linter: `bin/lint_workflows.py`

- `py -3 bin/lint_workflows.py [PATH ...] [--json] [--fail-on info|warn|bad]` checks `.github/workflows/*.yml` before you push. With no path it looks at the current folder. It only opens files.
- Rules (each can be switched off and given another severity in the Settings tab, sub-tab Workflow linter): `unpinned_uses` (an action not pinned to a full commit SHA), `permissions` (no `permissions:` block, or `write-all`), `secrets_in_clear` (what looks like a token or key written in the file), `injection` (text of an outsider pasted into a `run:` script) and `pr_target` (`pull_request_target` with a checkout of the pull request's code).
- The exit code is 1 when a finding reaches `--fail-on` (default `bad`), so it can be a pre-push hook. When the monitor can see your clones it also adds one line to the daily report.
- A value that looks like a secret is classified without ever being printed or stored: a known token format or a long high-entropy string is serious (`bad`), a readable filler such as `placeholder`, `dummy`, `changeme` or `ci` is only information, anything else is a warning, and `${{ secrets.X }}`, `${X}` or an empty value is no finding. To silence one finding write a comment on its line or on the line before: `# monitor-lint: ignore secrets_in_clear because it is a filler for docker compose config` (a rule name or `all`); or list `repository:file:rule` patterns, with `*`, in the setting `lint.ignore`.


## The terminal view: `bin/tui.py`

- `pip install rich`, then `py -3 bin/tui.py [--port 8765] [--refresh 5] [--once] [--theme dark|light]`. It draws a live grid of what is running, the red workflows, the signing queue and the report, read from the running monitor on `127.0.0.1` (it uses no GitHub quota).
- It is read-only: there is no key that re-runs, closes or writes anything. Without Rich it says how to install it and exits with code 3; the monitor and its tests never need Rich.
- The interactive terminal application `bin/tui_textual.py` (`pip install textual`; add `--lite` for the lite edition) edits the simple settings of the groups it lists, **lists** (type the items separated by commas: `a, b, c`) and **maps** of numbers (`name=3, other=5`) in the Settings tab; the server checks every value again, and the options of security can only be changed in the page.
