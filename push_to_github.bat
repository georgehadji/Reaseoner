@echo off
setlocal EnableDelayedExpansion

cls
echo ============================================================
echo   Push changes to GitHub
echo ============================================================
echo.

:: --- Find Python ---
for /f "delims=" %%P in ('where python 2^>nul') do (
    set PYTHON=%%P
    goto :found_python
)
for /f "delims=" %%P in ('where py 2^>nul') do (
    set PYTHON=%%P
    goto :found_python
)
echo [ERROR] Python not found in PATH.
echo         Install Python or add it to PATH.
pause
exit /b 1

:found_python

:: --- Prompt for message ---
set /p msg="Enter commit message (or press Enter for auto): "

:: --- Run Python script ---
if "!msg!"=="" (
    "%PYTHON%" "%~dp0push_to_github.py"
) else (
    "%PYTHON%" "%~dp0push_to_github.py" "!msg!"
)

set EXITCODE=%ERRORLEVEL%

if %EXITCODE% neq 0 (
    echo.
    echo ============================================================
    echo   Push failed with error code %EXITCODE%
    echo ============================================================
)

echo.
pause
