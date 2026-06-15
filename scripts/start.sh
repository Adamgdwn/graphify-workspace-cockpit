#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_DIR/backend"
FRONTEND_DIR="$REPO_DIR/frontend"

load_node_env() {
  if command -v npm >/dev/null 2>&1; then
    return
  fi
  if [ -s "$HOME/.nvm/nvm.sh" ]; then
    # Non-interactive shells often skip nvm initialization.
    # shellcheck source=/dev/null
    source "$HOME/.nvm/nvm.sh"
  fi
}

echo "==> Starting backend (localhost:8000)…"
cd "$BACKEND_DIR"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

echo "==> Starting frontend (localhost:5173)…"
cd "$FRONTEND_DIR"
load_node_env
if [ ! -d "node_modules" ]; then
  npm install --silent
fi
npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl-C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
