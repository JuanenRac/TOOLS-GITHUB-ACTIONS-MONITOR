#!/usr/bin/env bash
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# macOS: double-click in Finder (opens Terminal and starts the LITE monitor).
cd "$(dirname "$0")" || exit 1
printf '\033]0;%s\007' "GitHub Actions Monitor LITE - port 8766 - no sentinel"
exec bash ./MONITOR_LITE_GITHUB_ACTIONS.sh "$@"
