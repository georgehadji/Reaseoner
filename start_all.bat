@echo off
title Reasoner - All Servers
cls
echo ============================================================
echo   Reasoner - AI Reasoning Platform
echo   Starting all servers...
echo ============================================================
echo.

python start_all.py %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo ============================================================
    echo   Server startup failed with error code %ERRORLEVEL%
    echo ============================================================
)

pause
