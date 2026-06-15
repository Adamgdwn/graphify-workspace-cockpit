#!/usr/bin/env bash
# Graphify Workspace Cockpit launcher.
# Starts backend and frontend if not already running, then opens the browser.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_DIR/backend"
FRONTEND_DIR="$REPO_DIR/frontend"
FRONTEND_URL="http://localhost:5173"
BACKEND_URL="http://localhost:8000"
LOG_DIR="$REPO_DIR/launcher"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# ── helpers ──────────────────────────────────────────────────────────────────

notify() {
  command -v notify-send &>/dev/null && notify-send "Graphify Cockpit" "$1" --icon="$LOG_DIR/icon.png" 2>/dev/null || true
}

open_browser() {
  local url="$1"
  # Try multiple methods in order — xdg-open can be unreliable on COSMIC/Wayland
  if command -v xdg-open &>/dev/null; then
    xdg-open "$url" 2>/dev/null &
    disown
    return
  fi
  for browser in firefox google-chrome chromium-browser brave-browser; do
    if command -v "$browser" &>/dev/null; then
      "$browser" "$url" 2>/dev/null &
      disown
      return
    fi
  done
}

backend_running() {
  curl -sf "$BACKEND_URL/health" >/dev/null 2>&1
}

frontend_running() {
  curl -sf "$FRONTEND_URL" >/dev/null 2>&1
}

wait_for() {
  local url="$1" label="$2" tries=0
  while ! curl -sf "$url" >/dev/null 2>&1; do
    tries=$((tries + 1))
    if [ "$tries" -gt 30 ]; then
      notify "Failed to start $label — check $LOG_DIR/*.log"
      exit 1
    fi
    sleep 1
  done
}

load_node_env() {
  if command -v npm >/dev/null 2>&1; then
    return
  fi
  if [ -s "$HOME/.nvm/nvm.sh" ]; then
    # GUI launchers and non-interactive shells often skip nvm initialization.
    # shellcheck source=/dev/null
    source "$HOME/.nvm/nvm.sh"
  fi
}

# ── already running? ─────────────────────────────────────────────────────────

if backend_running && frontend_running; then
  notify "Cockpit already running — opening browser"
  open_browser "$FRONTEND_URL"
  exit 0
fi

# ── start backend ─────────────────────────────────────────────────────────────

if ! backend_running; then
  echo "==> Starting backend…"
  cd "$BACKEND_DIR"
  if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
  fi
  nohup .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 >> "$BACKEND_LOG" 2>&1 &
  disown
fi

# ── start frontend ────────────────────────────────────────────────────────────

if ! frontend_running; then
  echo "==> Starting frontend…"
  cd "$FRONTEND_DIR"
  load_node_env
  if [ ! -d "node_modules" ]; then
    npm install --silent
  fi
  nohup npm run dev >> "$FRONTEND_LOG" 2>&1 &
  disown
fi

# ── wait and open ─────────────────────────────────────────────────────────────

notify "Cockpit starting…"
wait_for "$BACKEND_URL/health" "backend"
wait_for "$FRONTEND_URL" "frontend"

notify "Cockpit ready"
open_browser "$FRONTEND_URL"
