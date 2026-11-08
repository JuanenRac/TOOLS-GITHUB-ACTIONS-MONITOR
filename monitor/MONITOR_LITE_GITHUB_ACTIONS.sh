#!/usr/bin/env bash
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# GitHub Actions monitor, LITE edition (Linux and macOS): what is running, the failures of the last 24 hours, the history and basic charts. No sentinel.
# Local only (127.0.0.1), port 8766 by default. Stop: Ctrl+C. Optional arguments: --port 8766 --no-browser --lang de
cd "$(dirname "$0")" || exit 1
printf '\033]0;%s\007' "GitHub Actions Monitor LITE - port 8766 - no sentinel"
PY="$(command -v python3 || command -v python)"
if [ -z "$PY" ]; then echo "Python 3.11+ not found / No se encontro Python 3.11+ / Python 3.11+ nicht gefunden / Python 3.11+ introuvable / Python 3.11+ non trovato / 未找到 Python 3.11+ / Python 3.11+ não encontrado"; exit 1; fi
if ! command -v gh >/dev/null 2>&1; then
  "$PY" launcher_msg.py gh_missing
  exit 1
fi
"$PY" actions_monitor.py --lite "$@"
echo
"$PY" launcher_msg.py stopped
