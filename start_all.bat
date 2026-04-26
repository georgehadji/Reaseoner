@echo off
setlocal EnableDelayedExpansion
title Reasoner - Starting...
cls

echo.
echo  ============================================================
echo    Reasoner  -  AI Reasoning Platform
echo  ============================================================
echo.

:: ── Switch to the batch file's directory ─────────────────────────────
cd /d "%~dp0"

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

:: ── Parse arguments ──────────────────────────────────────────────────
set MAIN_PORT=8003
set NEURO_PORT=50001
set FRONTEND_PORT=3000
set FORCE_FLAG=
set "EXTRA_ARGS="

:PARSE_LOOP
if "%~1"=="" goto :PARSE_DONE

if "%~1"=="--main-port" (
    set "MAIN_PORT=%~2"
    shift
    shift
    goto :PARSE_LOOP
)
if "%~1"=="--neuro-port" (
    set "NEURO_PORT=%~2"
    shift
    shift
    goto :PARSE_LOOP
)
if "%~1"=="--frontend-port" (
    set "FRONTEND_PORT=%~2"
    shift
    shift
    goto :PARSE_LOOP
)
if "%~1"=="--force" (
    set FORCE_FLAG=1
    set "EXTRA_ARGS=%EXTRA_ARGS% %1"
    shift
    goto :PARSE_LOOP
)

:: Preserve any other flags (e.g. --no-neuro, --no-frontend, --check)
set "EXTRA_ARGS=%EXTRA_ARGS% %1"
shift
goto :PARSE_LOOP

:PARSE_DONE

:: ── Port conflict checks ─────────────────────────────────────────────
echo  Checking ports...
call :CHECK_PORT %MAIN_PORT% backend
call :CHECK_PORT %NEURO_PORT% neuro
call :CHECK_PORT %FRONTEND_PORT% frontend
echo.

echo  Starting servers  ^(press Ctrl+C to stop all^)...
echo.

title Reasoner - Running :%MAIN_PORT%
python start_all.py --main-port %MAIN_PORT% --neuro-port %NEURO_PORT% --frontend-port %FRONTEND_PORT%%EXTRA_ARGS%
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

:: ── Subroutine: CHECK_PORT <port> <label> ────────────────────────────
:CHECK_PORT
netstat -ano 2>nul | "%SystemRoot%\System32\find.exe" ":%~1 " | "%SystemRoot%\System32\find.exe" "LISTENING" >nul 2>&1
if not errorlevel 1 (
    if defined FORCE_FLAG (
        echo  [WARN]  Port %~1 ^(%~2^) in use - will attempt to free with --force.
    ) else (
        echo  [ERROR] Port %~1 ^(%~2^) is already in use.
        echo          Run kill_servers.bat first, or pass --%~2-port ^<port^>.
        echo.
        pause & exit /b 1
    )
) else (
    echo    Port %~1  ^(%~2^)  free
)
exit /b 0
