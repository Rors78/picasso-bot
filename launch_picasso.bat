@echo off
title PICASSO Fibonacci Trader
cd /d D:\PicassoBot

rem Restart semantics: kill any running Picasso first, then start fresh.
rem Kills ONLY picasso.py by command line - never other python bots in the fleet.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%%'\" | Where-Object { $_.CommandLine -match 'picasso\.py' } | ForEach-Object { Write-Host ('  Restarting: killing old PICASSO (PID ' + $_.ProcessId + ')'); Stop-Process -Id $_.ProcessId -Force }"

python picasso.py
echo.
echo  PICASSO stopped.
pause
