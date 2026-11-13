@echo off
rem Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
rem GPL-3.0-or-later - see LICENSE
rem GitHub Actions monitor, LITE edition: what is running, the failures of the last 24 hours, the history and basic charts. No sentinel. Local only, port 8766.
rem Stop: Ctrl+C in this window. The window does NOT close by itself.
title GitHub Actions Monitor LITE - port 8766 - no sentinel
cd /d "%~dp0"
if not defined PYTHONPATH goto nopp
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
goto ppdone
:nopp
set "PYTHONPATH=%~dp0src"
:ppdone
where gh >nul 2>nul
if errorlevel 1 (
  py -3 -m github_actions_monitor.cli.launcher_msg gh_missing 2>nul || echo GitHub CLI ^(gh^) not found. Install it and run: gh auth login
  pause
  exit /b 1
)
py -3 -m github_actions_monitor.lite %*
echo.
py -3 -m github_actions_monitor.cli.launcher_msg stopped 2>nul || echo The monitor has stopped.
pause
