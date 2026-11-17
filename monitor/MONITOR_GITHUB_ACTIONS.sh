#!/usr/bin/env bash
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# GitHub Actions monitor (Linux and macOS): opens a page in the browser with what is happening NOW (runs, jobs, steps), charts, history and alerts.
# Local only (127.0.0.1). Stop: Ctrl+C. The port is ports.complete of actions_monitor.json (8765 by default); --port N overrides it. Optional arguments: --port N --no-browser --lang de
cd "$(dirname "$0")" || exit 1
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
printf '\033]0;%s\007' "GitHub Actions Monitor COMPLETE - sentinel on"
PY="$(command -v python3 || command -v python)"
if [ -z "$PY" ]; then echo "Python 3.11+ not found / No se encontro Python 3.11+ / Python 3.11+ nicht gefunden / Python 3.11+ introuvable / Python 3.11+ non trovato / 未找到 Python 3.11+ / Python 3.11+ não encontrado / Python 3.11+ が見つかりません"; exit 1; fi
if ! command -v gh >/dev/null 2>&1; then
  "$PY" -m github_actions_monitor.cli.launcher_msg gh_missing
  exit 1
fi
"$PY" -m github_actions_monitor "$@"
echo
"$PY" -m github_actions_monitor.cli.launcher_msg stopped
