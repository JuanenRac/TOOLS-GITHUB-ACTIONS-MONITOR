#!/usr/bin/env bash
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# GitHub Actions build batch (Linux and macOS): NOTHING is compiled on this machine.
#   1 = plan, 2 = FIRE the batch (dry_run=true), 3 = status, 4 = finalize (download, verify, sign and publish; asks before each one), 5 = hygiene, 6 = quit
# The menu texts come from launcher_msg.py (your language).
cd "$(dirname "$0")" || exit 1
PY="$(command -v python3 || command -v python)"
if [ -z "$PY" ]; then echo "Python 3.10+ not found / No se encontro Python 3.10+ / Python 3.10+ nicht gefunden / Python 3.10+ introuvable / Python 3.10+ non trovato / 未找到 Python 3.10+ / Python 3.10+ não encontrado"; exit 1; fi
while true; do
  "$PY" launcher_msg.py menu
  ASK="$("$PY" launcher_msg.py choose)"
  read -r -p "$ASK " op
  case "$op" in
    1) "$PY" gha_dispatch_all.py plan ;;
    2) "$PY" gha_dispatch_all.py dispatch --go ;;
    3) "$PY" gha_dispatch_all.py status ;;
    4) "$PY" gha_dispatch_all.py finalize --execute ;;
    5) "$PY" gha_dispatch_all.py hygiene ;;
    6) exit 0 ;;
  esac
done
