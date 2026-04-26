@echo off
setlocal EnableDelayedExpansion
title Reasoner - Stopping...
cls

echo.
echo  ============================================================
echo    Reasoner  -  Stop All Servers
echo  ============================================================
echo.

:: ── Working directory guard ──────────────────────────────────────────
if not exist "kill_servers.py" (
    echo  [ERROR] Run from the project root ^(where kill_servers.py lives^).
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

:: ── Port status (single PowerShell call for all three ports) ─────────
if not "%1"=="--quiet" (
    echo  Active Reasoner processes:
    powershell -NoProfile -Command ^
        "foreach ($port in @(8003, 50001, 3000)) {" ^
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
)

:: ── Kill servers ──────────────────────────────────────────────────────
python kill_servers.py %*
set EXIT_CODE=%ERRORLEVEL%

title Reasoner - Stopped
echo.
if %EXIT_CODE% neq 0 (
    echo  [ERROR] Stop script exited with code %EXIT_CODE%.
) else (
    echo  [OK]  All servers stopped.
)
echo.

if "%1"=="--quiet" (
    endlocal & exit /b %EXIT_CODE%
)
pause
endlocal
exit /b %EXIT_CODE%
