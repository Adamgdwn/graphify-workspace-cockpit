# Graphify Workspace Cockpit launcher (Windows).
#
# Mirrors launcher/launch-cockpit.sh: if the backend and frontend are not already
# running, it sets them up on first run (Python venv + pip install, npm install),
# starts both, waits for them to come up, then opens the browser.
#
# HOW TO RUN: double-click launch-cockpit.bat (it calls this script with the
# execution policy bypassed). You can also run it directly:
#   powershell -NoProfile -ExecutionPolicy Bypass -File launcher\launch-cockpit.ps1
#
# STATUS: best-effort Windows launcher. The verified, previously-tested
# cross-platform path on Windows is Docker Desktop -- see docs/deployment-guide.md.
# If this script misbehaves on your machine, use the Docker path instead and
# please report what happened.
#
# PLANNED: a true double-click desktop app with native installers (Tauri/Electron)
# is intended once real-world usability on a separate Windows machine is confirmed.
# Until then, this script + the Docker guide are the supported Windows paths.

$ErrorActionPreference = 'Stop'

$LauncherDir = $PSScriptRoot
$RepoDir     = Split-Path -Parent $LauncherDir
$BackendDir  = Join-Path $RepoDir 'backend'
$FrontendDir = Join-Path $RepoDir 'frontend'
$FrontendUrl = 'http://localhost:5173'
$BackendUrl  = 'http://localhost:8000'
$BackendLog  = Join-Path $LauncherDir 'backend.log'
$FrontendLog = Join-Path $LauncherDir 'frontend.log'

# -- helpers ------------------------------------------------------------------

function Test-Up([string]$url) {
    try {
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri $url | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Wait-Up([string]$url, [string]$label) {
    for ($i = 0; $i -lt 30; $i++) {
        if (Test-Up $url) { return }
        Start-Sleep -Seconds 1
    }
    Write-Error "Failed to start $label - check $LauncherDir\*.log"
    exit 1
}

function Require-Tool([string]$name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Error "'$name' was not found on PATH. Install it (python.org / nodejs.org) or use the Docker path in docs\deployment-guide.md."
        exit 1
    }
}

# Start a long-running process in the background, appending stdout+stderr to a
# log file. cmd.exe handles the '>> file 2>&1' redirection so npm.cmd and the
# venv executables resolve the same way they would in a normal shell.
function Start-Bg([string]$workdir, [string]$command, [string]$logfile) {
    $full = "$command >> `"$logfile`" 2>&1"
    Start-Process -WindowStyle Hidden -WorkingDirectory $workdir `
        -FilePath $env:ComSpec -ArgumentList '/c', $full | Out-Null
}

# -- already running? ---------------------------------------------------------

if ((Test-Up "$BackendUrl/health") -and (Test-Up $FrontendUrl)) {
    Write-Host 'Cockpit already running - opening browser.'
    Start-Process $FrontendUrl
    exit 0
}

Require-Tool 'python'
Require-Tool 'npm'

# -- start backend ------------------------------------------------------------

if (-not (Test-Up "$BackendUrl/health")) {
    Write-Host '==> Starting backend...'
    Push-Location $BackendDir
    if (-not (Test-Path '.venv')) {
        python -m venv .venv
        & '.venv\Scripts\python.exe' -m pip install -q -r requirements.txt
    }
    $uvicorn = Join-Path $BackendDir '.venv\Scripts\uvicorn.exe'
    Start-Bg $BackendDir "`"$uvicorn`" main:app --host 127.0.0.1 --port 8000" $BackendLog
    Pop-Location
}

# -- start frontend -----------------------------------------------------------

if (-not (Test-Up $FrontendUrl)) {
    Write-Host '==> Starting frontend...'
    Push-Location $FrontendDir
    if (-not (Test-Path 'node_modules')) {
        npm install
    }
    Start-Bg $FrontendDir 'npm run dev' $FrontendLog
    Pop-Location
}

# -- wait and open ------------------------------------------------------------

Write-Host 'Cockpit starting...'
Wait-Up "$BackendUrl/health" 'backend'
Wait-Up $FrontendUrl 'frontend'

Write-Host 'Cockpit ready - opening browser.'
Start-Process $FrontendUrl
