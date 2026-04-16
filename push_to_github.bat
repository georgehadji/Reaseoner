@echo off
cls
echo ============================================================
echo   Push changes to GitHub
echo ============================================================
echo.

set /p msg="Enter commit message (or press Enter for auto): "

if "%msg%"=="" (
    python push_to_github.py
) else (
    python push_to_github.py "%msg%"
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo ============================================================
    echo   Push failed with error code %ERRORLEVEL%
    echo ============================================================
)

pause
