#!/usr/bin/env bash
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# macOS: double-click in Finder (opens Terminal and starts the monitor).
cd "$(dirname "$0")" || exit 1
printf '\033]0;%s\007' "GitHub Actions Monitor COMPLETE - port 8765 - sentinel on"
exec bash ./MONITOR_GITHUB_ACTIONS.sh "$@"
