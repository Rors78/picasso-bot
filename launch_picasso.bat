@echo off
title PICASSO Fibonacci Trader
cd /d D:\PicassoBot

rem Operator risk settings (paper simulation - live mode is always spot 1x)
set PICASSO_LEVERAGE=20

rem Bankroll: seeds balance.json on first run only; balance.json is the authority
rem after that. Operator reset to $80.56 on 2026-08-27. Sizing risks
rem PICASSO_RISK_PCT (default 20) percent of the current balance per trade.
set PICASSO_BALANCE=80.56

rem Tuned 2026-08-27 via --tune 90: vol 1.0 (filter off), touch tol 0.03
rem (defaults 1.5/0.02 were the worst combo on the grid)
set PICASSO_VOL_MULT=1.0
set PICASSO_TOUCH_TOL=0.03

rem Restart semantics: kill any running Picasso first, then start fresh.
rem Kills ONLY picasso.py by command line - never other python bots in the fleet.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%%'\" | Where-Object { $_.CommandLine -match 'picasso\.py' } | ForEach-Object { Write-Host ('  Restarting: killing old PICASSO (PID ' + $_.ProcessId + ')'); Stop-Process -Id $_.ProcessId -Force }"

rem Open the web dashboard once the bot's server is up
start "" cmd /c "timeout /t 5 /nobreak >nul & start "" http://localhost:8877"

python picasso.py
echo.
echo  PICASSO stopped.
pause
