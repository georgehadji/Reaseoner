@echo off
cd /d "%~dp0"

if not exist "start_all.py" (
    echo [ERROR] Run from the project root.
    pause & exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] python not found in PATH.
    pause & exit /b 1
)

python start_all.py %*
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% neq 0 echo [ERROR] Exited with code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
