@echo off
setlocal EnableDelayedExpansion
title Reasoner - Starting...
cls

echo.
echo  ============================================================
echo    Reasoner  -  AI Reasoning Platform
echo  ============================================================
echo.

:: ── Working directory guard ──────────────────────────────────────────
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

:: ── Parse --main-port / --neuro-port / --frontend-port from %* ───────
set MAIN_PORT=8003
set NEURO_PORT=50001
set FRONTEND_PORT=3000
set _GRAB=

for %%A in (%*) do (
    if defined _GRAB (
        set !_GRAB!=%%A
        set _GRAB=
    ) else (
        if "%%A"=="--main-port"     set _GRAB=MAIN_PORT
        if "%%A"=="--neuro-port"    set _GRAB=NEURO_PORT
        if "%%A"=="--frontend-port" set _GRAB=FRONTEND_PORT
    )
)

:: ── Port conflict checks (netstat - no subprocess overhead) ──────────
echo  Checking ports...

call :CHECK_PORT %MAIN_PORT% backend BLOCK
call :CHECK_PORT %NEURO_PORT% neuro WARN
call :CHECK_PORT %FRONTEND_PORT% frontend WARN
echo.

echo  Starting servers  ^(press Ctrl+C to stop all^)...
echo.

title Reasoner - Running :%MAIN_PORT%
python start_all.py --main-port %MAIN_PORT% --neuro-port %NEURO_PORT% --frontend-port %FRONTEND_PORT% %*
set EXIT_CODE=%ERRORLEVEL%

title Reasoner - Stopped
echo.
if %EXIT_CODE% neq 0 (
    echo  [ERROR] Exited with code %EXIT_CODE%.
) else (
    echo  [OK]  All servers stopped cleanly.
)
echo.
pause
endlocal
exit /b %EXIT_CODE%

:: ── Subroutine: CHECK_PORT <port> <label> <BLOCK|WARN> ───────────────
:CHECK_PORT
netstat -ano 2>nul | find ":%~1 " | find "LISTENING" >nul 2>&1
if not errorlevel 1 (
    if "%~3"=="BLOCK" (
        echo  [ERROR] Port %~1 ^(%~2^) is already in use.
        echo          Run kill_servers.bat first, or pass --%~2-port ^<port^>.
        echo.
        pause & exit /b 1
    )
    echo  [WARN]  Port %~1 ^(%~2^) in use - server may not start.
) else (
    echo    Port %~1  ^(%~2^)  free
)
exit /b 0
