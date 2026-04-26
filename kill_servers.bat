@echo off
setlocal EnableDelayedExpansion
title Reasoner - Stopping...
cls

echo.
echo  ============================================================
echo    Reasoner  -  Stop All Servers
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

:: ── Python check ─────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] python not found in PATH.
    echo.
    pause & exit /b 1
)

:: ── Parse arguments ──────────────────────────────────────────────────
set QUIET_FLAG=
set "EXTRA_ARGS="

:PARSE_LOOP
if "%~1"=="" goto :PARSE_DONE

if "%~1"=="--quiet" (
    set QUIET_FLAG=1
    shift
    goto :PARSE_LOOP
)

:: Pass through everything else (--force, etc.)
set "EXTRA_ARGS=%EXTRA_ARGS% %1"
shift
goto :PARSE_LOOP

:PARSE_DONE

:: ── Port status (single PowerShell call for all three ports) ─────────
if not defined QUIET_FLAG (
    echo  Active Reasoner processes:
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
)

:: ── Kill servers ──────────────────────────────────────────────────────
python kill_servers.py%EXTRA_ARGS%
set EXIT_CODE=%ERRORLEVEL%

title Reasoner - Stopped
echo.
if %EXIT_CODE% neq 0 (
    echo  [ERROR] Stop script exited with code %EXIT_CODE%.
) else (
    echo  [OK]  All servers stopped.
)
echo.

if defined QUIET_FLAG (
    endlocal & exit /b %EXIT_CODE%
)
pause
endlocal
exit /b %EXIT_CODE%
