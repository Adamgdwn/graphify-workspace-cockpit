# Graphify Workspace Cockpit launcher (Windows).
#
# Double-click launcher\launch-cockpit.bat, or run this file directly:
#   powershell -NoProfile -ExecutionPolicy Bypass -File launcher\launch-cockpit.ps1
#
# The launcher bootstraps a Python virtual environment, keeps backend/frontend
# dependencies in sync, loads optional backend/frontend .env files, starts both
# local services, waits for health checks, and opens the browser.

param(
    [switch]$NoBrowser,
    [switch]$Restart
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http

$LauncherDir = $PSScriptRoot
$RepoDir     = Split-Path -Parent $LauncherDir
$BackendDir  = Join-Path $RepoDir 'backend'
$FrontendDir = Join-Path $RepoDir 'frontend'
$VenvDir     = Join-Path $BackendDir '.venv'
$VenvScripts = Join-Path $VenvDir 'Scripts'
$VenvPython  = Join-Path $VenvDir 'Scripts\python.exe'
$FrontendUrl = 'http://localhost:5173'
$BackendUrl  = 'http://127.0.0.1:8000'
$BackendLog  = Join-Path $LauncherDir 'backend.log'
$BackendErr  = Join-Path $LauncherDir 'backend.err.log'
$FrontendLog = Join-Path $LauncherDir 'frontend.log'
$FrontendErr = Join-Path $LauncherDir 'frontend.err.log'

# -- helpers ------------------------------------------------------------------

function Test-Up([string]$url) {
    $client = [System.Net.Http.HttpClient]::new()
    try {
        $client.Timeout = [TimeSpan]::FromSeconds(2)
        $response = $client.GetAsync($url).GetAwaiter().GetResult()
        try {
            return $response.IsSuccessStatusCode
        } finally {
            $response.Dispose()
        }
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Wait-Up([string]$url, [string]$label) {
    for ($i = 0; $i -lt 30; $i++) {
        if (Test-Up $url) { return }
        Start-Sleep -Seconds 1
    }
    Write-Error "Failed to start $label - check launcher\backend*.log and launcher\frontend*.log"
    exit 1
}

function Require-Tool([string]$name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Error "'$name' was not found on PATH. Install it (python.org / nodejs.org) or use the Docker path in docs\deployment-guide.md."
        exit 1
    }
}

function Import-DotEnv([string]$path) {
    if (-not (Test-Path $path)) { return }
    foreach ($line in Get-Content -LiteralPath $path) {
        $trimmed = $line.Trim()
        if ($trimmed.Length -eq 0 -or $trimmed.StartsWith('#')) { continue }
        if ($trimmed.StartsWith('export ')) {
            $trimmed = $trimmed.Substring(7).Trim()
        }
        $idx = $trimmed.IndexOf('=')
        if ($idx -lt 1) { continue }
        $name = $trimmed.Substring(0, $idx).Trim()
        $value = $trimmed.Substring($idx + 1).Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}

function File-Hash([string]$path) {
    if (-not (Test-Path $path)) { return '' }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash
}

function Add-PathPrefix([string]$path) {
    if (-not (Test-Path $path)) { return }
    $parts = $env:PATH -split ';'
    if ($parts -notcontains $path) {
        $env:PATH = "$path;$env:PATH"
    }
}

function Open-Cockpit {
    if ($NoBrowser) { return }
    Start-Process -FilePath 'explorer.exe' -ArgumentList $FrontendUrl | Out-Null
}

function Start-Bg([string]$workdir, [string]$filePath, [string[]]$arguments, [string]$stdoutLog, [string]$stderrLog) {
    Start-Process -WindowStyle Hidden -WorkingDirectory $workdir `
        -FilePath $filePath -ArgumentList $arguments `
        -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog | Out-Null
}

function Stop-CockpitListeners {
    $listenerProcessIds = Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($listenerProcessId in $listenerProcessIds) {
        if ($listenerProcessId -and $listenerProcessId -ne $PID) {
            Stop-Process -Id $listenerProcessId -Force -ErrorAction SilentlyContinue
        }
    }

    if ($listenerProcessIds) {
        Start-Sleep -Seconds 2
    }
}

function Install-BackendDeps {
    Push-Location $BackendDir
    try {
        if (-not (Test-Path $VenvPython)) {
            Write-Host '==> Creating backend virtual environment...'
            python -m venv .venv
        }

        $requirements = Join-Path $BackendDir 'requirements.txt'
        $marker = Join-Path $VenvDir '.requirements.sha256'
        $currentHash = File-Hash $requirements
        $savedHash = if (Test-Path $marker) { (Get-Content -LiteralPath $marker -Raw).Trim() } else { '' }

        if ($currentHash -ne $savedHash) {
            Write-Host '==> Installing backend dependencies...'
            & $VenvPython -m pip install -q --upgrade pip
            & $VenvPython -m pip install -q -r requirements.txt
            Set-Content -LiteralPath $marker -Value $currentHash -Encoding ascii
        }
    } finally {
        Pop-Location
    }
}

function Install-FrontendDeps {
    Push-Location $FrontendDir
    try {
        $lockfile = Join-Path $FrontendDir 'package-lock.json'
        $packageFile = Join-Path $FrontendDir 'package.json'
        $hashSource = if (Test-Path $lockfile) { $lockfile } else { $packageFile }
        $marker = Join-Path $FrontendDir 'node_modules\.package-lock.sha256'
        $currentHash = File-Hash $hashSource
        $savedHash = if (Test-Path $marker) { (Get-Content -LiteralPath $marker -Raw).Trim() } else { '' }

        if ((-not (Test-Path 'node_modules')) -or ($currentHash -ne $savedHash)) {
            Write-Host '==> Installing frontend dependencies...'
            & $NpmCmd install
            Set-Content -LiteralPath $marker -Value $currentHash -Encoding ascii
        }
    } finally {
        Pop-Location
    }
}

# -- already running? ---------------------------------------------------------

if ($Restart) {
    Write-Host '==> Restarting existing cockpit listeners...'
    Stop-CockpitListeners
}

if ((Test-Up "$BackendUrl/health") -and (Test-Up $FrontendUrl)) {
    if ($NoBrowser) {
        Write-Host 'Cockpit already running.'
    } else {
        Write-Host 'Cockpit already running - opening browser.'
    }
    Open-Cockpit
    exit 0
}

Require-Tool 'python'
Require-Tool 'node'
Require-Tool 'npm'

$NpmCommand = Get-Command 'npm.cmd' -ErrorAction SilentlyContinue
if (-not $NpmCommand) {
    $NpmCommand = Get-Command 'npm' -ErrorAction SilentlyContinue
}
$NpmCmd = $NpmCommand.Source

Import-DotEnv (Join-Path $BackendDir '.env')
Import-DotEnv (Join-Path $FrontendDir '.env')

# -- start backend ------------------------------------------------------------

if (-not (Test-Up "$BackendUrl/health")) {
    Install-BackendDeps
    Add-PathPrefix $VenvScripts
    Write-Host '==> Starting backend...'
    Start-Bg -workdir $BackendDir -filePath $VenvPython `
        -arguments @('-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000') `
        -stdoutLog $BackendLog -stderrLog $BackendErr
}

# -- start frontend -----------------------------------------------------------

if (-not (Test-Up $FrontendUrl)) {
    Install-FrontendDeps
    Write-Host '==> Starting frontend...'
    Start-Bg -workdir $FrontendDir -filePath $NpmCmd `
        -arguments @('run', 'dev') `
        -stdoutLog $FrontendLog -stderrLog $FrontendErr
}

# -- wait and open ------------------------------------------------------------

Write-Host 'Cockpit starting...'
Wait-Up "$BackendUrl/health" 'backend'
Wait-Up $FrontendUrl 'frontend'

if ($NoBrowser) {
    Write-Host 'Cockpit ready.'
} else {
    Write-Host 'Cockpit ready - opening browser.'
}
Open-Cockpit
