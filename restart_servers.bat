@echo off
setlocal EnableDelayedExpansion
title Reasoner - Restarting...
cls

echo.
echo  ============================================================
echo    Reasoner  -  Restart All Servers
echo  ============================================================
echo.

:: ── Switch to the batch file's directory ─────────────────────────────
cd /d "%~dp0"

:: ── Working directory guard ──────────────────────────────────────────
if not exist "kill_servers.py" (
    echo  [ERROR] Run from the project root ^(where kill_servers.py lives^).
    echo.
    pause & exit /b 1
)
if not exist "start_all.py" (
    echo  [ERROR] Run from the project root ^(where start_all.py lives^).
    echo.
    pause & exit /b 1
)

:: ── Python check ─────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] python not found in PATH.
    echo.
    pause & exit /b 1
)

:: ── Port status before kill ───────────────────────────────────────────
echo  Active Reasoner processes (before stop):
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -Command ^
    "foreach ($port in @(8003, 8002, 50001, 3000)) {" ^
    "  try {" ^
    "    $c = Get-NetTCPConnection -LocalPort $port -EA Stop;" ^
    "    $p = Get-Process -Id $c[0].OwningProcess -EA SilentlyContinue;" ^
    "    $name = if ($p) { $p.ProcessName + ' (PID ' + $p.Id + ')' } else { 'unknown' };" ^
    "    Write-Host ('    :' + $port + '  ->  ' + $name)" ^
    "  } catch {" ^
    "    Write-Host ('    :' + $port + '  ->  free')" ^
    "  }" ^
    "}"
echo.

:: ── Step 1: Kill servers ──────────────────────────────────────────────
echo  [1/2] Stopping all servers...
python kill_servers.py --force
set KILL_CODE=%ERRORLEVEL%

if %KILL_CODE% neq 0 (
    echo  [ERROR] Stop script exited with code %KILL_CODE%.
    echo.
    pause & exit /b %KILL_CODE%
)
echo  [OK]  All servers stopped.
echo.

:: ── Brief pause to let ports fully release ───────────────────────────
timeout /t 2 /nobreak >nul

:: ── Step 2: Start servers ─────────────────────────────────────────────
echo  [2/2] Starting all servers...
echo.
python start_all.py %*
set START_CODE=%ERRORLEVEL%

title Reasoner - Running
echo.
if %START_CODE% neq 0 (
    echo  [ERROR] Start script exited with code %START_CODE%.
    echo.
    pause & exit /b %START_CODE%
)

echo  [OK]  All servers restarted.
echo.
pause
endlocal
exit /b 0
