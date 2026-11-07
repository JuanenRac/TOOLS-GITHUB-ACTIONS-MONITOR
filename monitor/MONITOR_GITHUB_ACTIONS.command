#!/usr/bin/env bash
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# macOS: double-click in Finder (opens Terminal and starts the monitor).
cd "$(dirname "$0")" || exit 1
exec bash ./MONITOR_GITHUB_ACTIONS.sh "$@"
