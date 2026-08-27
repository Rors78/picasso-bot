@echo off
title PICASSO Fibonacci Trader
cd /d D:\PicassoBot

rem Operator risk settings (paper simulation - live mode is always spot 1x)
set PICASSO_LEVERAGE=20

rem Tuned 2026-08-27 via --tune 90: vol 1.0 (filter off), touch tol 0.03
rem (defaults 1.5/0.02 were the worst combo on the grid)
set PICASSO_VOL_MULT=1.0
set PICASSO_TOUCH_TOL=0.03

rem Restart semantics: kill any running Picasso first, then start fresh.
rem Kills ONLY picasso.py by command line - never other python bots in the fleet.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%%'\" | Where-Object { $_.CommandLine -match 'picasso\.py' } | ForEach-Object { Write-Host ('  Restarting: killing old PICASSO (PID ' + $_.ProcessId + ')'); Stop-Process -Id $_.ProcessId -Force }"

python picasso.py
echo.
echo  PICASSO stopped.
pause
