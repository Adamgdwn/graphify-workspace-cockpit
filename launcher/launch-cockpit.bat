@echo off
REM Graphify Workspace Cockpit launcher (Windows) -- double-click entry point.
REM
REM This wrapper runs launch-cockpit.ps1 with the execution policy bypassed so a
REM double-click works regardless of the system PowerShell settings.
REM
REM STATUS: best-effort Windows launcher. The verified, previously-tested
REM cross-platform path on Windows is Docker Desktop (see docs\deployment-guide.md).
REM PLANNED: a native double-click app + installers (Tauri/Electron) once
REM real-world usability on a separate Windows machine is confirmed.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch-cockpit.ps1" %*

if %ERRORLEVEL% neq 0 (
  echo.
  echo Launcher exited with an error.
  echo See launcher\backend.log and launcher\frontend.log,
  echo or use the Docker path in docs\deployment-guide.md.
  echo.
  pause
)
