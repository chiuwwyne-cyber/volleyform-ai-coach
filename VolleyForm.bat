@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_volleyform.ps1"
if errorlevel 1 (
    echo.
    echo VolleyForm did not start correctly. See the message above.
    pause
)
