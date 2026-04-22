@echo off
title Reasoner - All Servers
cls
echo ============================================================
echo   Reasoner - AI Reasoning Platform
echo   Starting all servers...
echo ============================================================
echo.

:: Check if main backend port 8001 is occupied
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "try { $c = Get-NetTCPConnection -LocalPort 8001 -ErrorAction Stop; Write-Host 'IN_USE' } catch { Write-Host 'FREE' }"') do set PORT_8001_STATUS=%%a

if "%PORT_8001_STATUS%"=="IN_USE" (
    echo [ERROR] Port 8001 is already in use!
    echo         Please free port 8001 or set a custom port with --main-port.
    echo.
    pause
    exit /b 1
)

:: Start servers (default backend port 8001 to avoid common Docker/WSL conflicts on 8000)
python start_all.py --main-port 8001 %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo ============================================================
    echo   Server startup failed with error code %ERRORLEVEL%
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo   Servers stopped.
    echo ============================================================
)

pause
