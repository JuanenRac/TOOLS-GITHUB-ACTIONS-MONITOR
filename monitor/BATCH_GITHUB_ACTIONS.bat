@echo off
rem Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
rem GPL-3.0-or-later - see LICENSE
rem GitHub Actions build batch: NOTHING is compiled on this PC.
rem   1 plan, 2 FIRE the batch (dry_run=true), 3 status, 4 finalize (download, verify, sign, publish; asks first), 5 hygiene, 6 quit.
rem The window does NOT close by itself. Menu texts come from -m github_actions_monitor.cli.launcher_msg (your language).
title GitHub Actions batch
cd /d "%~dp0"
if not defined PYTHONPATH goto nopp
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
goto ppdone
:nopp
set "PYTHONPATH=%~dp0src"
:ppdone
set "PY=py -3"
where py >nul 2>nul
if errorlevel 1 set "PY=python"
:menu
%PY% -m github_actions_monitor.cli.launcher_msg menu
for /f "delims=" %%p in ('%PY% -m github_actions_monitor.cli.launcher_msg choose') do set "ask=%%p"
set "op="
set /p op=%ask% 
if "%op%"=="1" %PY% -m github_actions_monitor.cli.gha_dispatch_all plan
if "%op%"=="2" %PY% -m github_actions_monitor.cli.gha_dispatch_all dispatch --go
if "%op%"=="3" %PY% -m github_actions_monitor.cli.gha_dispatch_all status
if "%op%"=="4" %PY% -m github_actions_monitor.cli.gha_dispatch_all finalize --execute
if "%op%"=="5" %PY% -m github_actions_monitor.cli.gha_dispatch_all hygiene
if "%op%"=="6" goto fin
goto menu
:fin
pause
