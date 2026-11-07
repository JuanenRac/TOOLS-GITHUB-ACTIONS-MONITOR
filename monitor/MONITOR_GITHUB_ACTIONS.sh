#!/usr/bin/env bash
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# GitHub Actions monitor (Linux and macOS): opens a page in the browser with what is happening NOW (runs, jobs, steps), charts, history and alerts.
# Local only (127.0.0.1). Stop: Ctrl+C. Optional arguments: --port 8765 --no-browser --lang de
cd "$(dirname "$0")" || exit 1
PY="$(command -v python3 || command -v python)"
if [ -z "$PY" ]; then echo "Python 3.10+ not found / No se encontro Python 3.10+ / Python 3.10+ nicht gefunden / Python 3.10+ introuvable / Python 3.10+ non trovato / 未找到 Python 3.10+ / Python 3.10+ não encontrado"; exit 1; fi
if ! command -v gh >/dev/null 2>&1; then
  "$PY" launcher_msg.py gh_missing
  exit 1
fi
"$PY" actions_monitor.py "$@"
echo
"$PY" launcher_msg.py stopped
