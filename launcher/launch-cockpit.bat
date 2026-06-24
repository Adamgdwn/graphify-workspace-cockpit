@echo off
REM Graphify Workspace Cockpit launcher (Windows) -- double-click entry point.
REM
REM This wrapper runs launch-cockpit.ps1 with the execution policy bypassed so a
REM double-click works regardless of the system PowerShell settings.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch-cockpit.ps1" %*

if %ERRORLEVEL% neq 0 (
  echo.
  echo Launcher exited with an error.
  echo See launcher\backend*.log and launcher\frontend*.log,
  echo or use the Docker path in docs\deployment-guide.md.
  echo.
  pause
)
