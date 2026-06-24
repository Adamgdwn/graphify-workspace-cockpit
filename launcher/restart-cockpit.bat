@echo off
REM Graphify Workspace Cockpit restart helper (Windows).
REM
REM Double-click this after pulling updates or changing frontend/backend code.
REM It stops only the cockpit listeners on ports 8000 and 5173, then starts them again.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch-cockpit.ps1" -Restart %*

if %ERRORLEVEL% neq 0 (
  echo.
  echo Launcher exited with an error.
  echo See launcher\backend*.log and launcher\frontend*.log,
  echo or use the Docker path in docs\deployment-guide.md.
  echo.
  pause
)
