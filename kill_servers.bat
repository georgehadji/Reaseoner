@echo off
title Reasoner - Kill Servers
cls
echo ============================================================
echo   Reasoner - AI Reasoning Platform
echo   Stopping all servers...
echo ============================================================
echo.

python kill_servers.py %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo ============================================================
    echo   Server stop failed with error code %ERRORLEVEL%
    echo ============================================================
)

pause
