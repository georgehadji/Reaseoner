@echo off
title Reasoner - Kill Servers
cls
echo ============================================================
echo   Reasoner - AI Reasoning Platform
echo   Stopping all servers...
echo ============================================================
echo.

:: Show any processes on our standard ports before killing
set SHOW_PORTS=1
if "%1"=="--quiet" set SHOW_PORTS=0

if %SHOW_PORTS%==1 (
    echo [INFO] Checking ports...
    powershell -NoProfile -Command "try { $c = Get-NetTCPConnection -LocalPort 8001 -ErrorAction Stop; $p = Get-Process -Id $c[0].OwningProcess; Write-Host ('  Port 8001 in use by: ' + $p.ProcessName + ' (PID ' + $p.Id + ')') } catch { Write-Host '  Port 8001: free' }"
    powershell -NoProfile -Command "try { $c = Get-NetTCPConnection -LocalPort 3000 -ErrorAction Stop; $p = Get-Process -Id $c[0].OwningProcess; Write-Host ('  Port 3000 in use by: ' + $p.ProcessName + ' (PID ' + $p.Id + ')') } catch { Write-Host '  Port 3000: free' }"
    echo.
)

if not exist "kill_servers.py" (
    echo [ERROR] kill_servers.py not found in current directory.
    echo         Please run this batch file from the project root.
    pause
    exit /b 1
)

python kill_servers.py %*
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% neq 0 (
    echo.
    echo ============================================================
    echo   Server stop failed with error code %EXIT_CODE%
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo   All Reasoner servers stopped.
    echo ============================================================
)

pause
