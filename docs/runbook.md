# Runbook

Status: current
Last Updated: 2026-06-21T20:01:05-06:00
Owner: Adam Goodwin

## What This System Does In Operation

The Graphify Workspace Cockpit runs two local processes:

- **Backend** — FastAPI on `http://localhost:8000`. Reads `graph.json`, runs Graphify through the backend service wrapper, calls Ollama for inference, writes workspace state to `workspace/state/`.
- **Frontend** — React app on `http://localhost:5173`. The Windows launcher builds an optimized production bundle and serves it with `vite preview` (minified, code-split, cached chunks — much faster to load than the dev server, and the heavy Map/cytoscape code is deferred until the Map tab is opened). It rebuilds only when frontend sources changed. Pass `-Dev` to `launch-cockpit.ps1` to fall back to the hot-reload dev server while editing the frontend. Talks only to the backend.

Neither process connects to the internet unless Supabase (`STORAGE_BACKEND=supabase`) or Cloud Connectors (SharePoint/OneNote) are configured.

## Starting the Cockpit

**Via Windows launcher:** double-click `launcher\launch-cockpit.bat`. The launcher script starts both processes if not already running, waits for health checks, and opens the cockpit. When the default browser is Chromium-based (Edge, Chrome, Brave, Vivaldi) it opens a standalone **app-mode window** (`--app=`) rather than a browser tab. App-mode windows are not background-discarded and are throttled far less than tabs, so long-running graph generation keeps running and stays visible even when the window loses focus. Other default browsers (e.g. Firefox) open a normal tab.

After pulling updates or changing local cockpit code, double-click `launcher\restart-cockpit.bat` or run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File launcher\launch-cockpit.ps1 -Restart
```

The restart path stops only the cockpit listeners on ports 8000 and 5173, then starts them again.

**Via Linux/macOS terminal:**
```bash
bash /path/to/repo/scripts/start.sh
```

**Via Windows terminal:**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File launcher\launch-cockpit.ps1
```

**Via Docker:**
```bash
docker-compose up --build
```

See `docs/deployment-guide.md` for network deployments, API key setup, and Caddy HTTPS.

## Health Check

```bash
curl http://localhost:8000/health
```

Response includes `status`, `graph_configured`, `graph_loaded`, `demo_mode`,
`graphify`, and `storage`. On a fresh instance, `graph_configured: false` means
no workspace graph has been generated or uploaded yet.
If `STORAGE_BACKEND=supabase` and `storage.ready` is false, apply the migration
named in `storage.required_migration` after owner approval before using
Supabase mode for hosted beta. Check Ollama separately with
`curl http://localhost:8000/status/ollama`.

For first-use workspace readiness, use the Command tab or query the protected
runtime endpoint with the same API key headers used by the app:

```bash
curl http://localhost:8000/runtime/status
```

The response reports `state` (`ready`, `partial`, or `not_ready`), backend,
Graphify, Ollama, active graph, auth, storage, connector status, warnings, and
the next best action. Treat `not_ready` as a setup blocker; treat `partial` as a
runtime warning state that should be reviewed before hosted beta use.

## Demo Readiness Check

With both processes running, use the lightweight smoke gate before recording or
handoff:

Windows PowerShell:

```powershell
node scripts/demo-path-smoke.mjs
```

Linux/macOS:

```bash
source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs
```

If the app is bound to `localhost` instead of `127.0.0.1`, override the URLs:

Windows PowerShell:

```powershell
$env:API_URL="http://localhost:8000"; $env:FRONTEND_URL="http://localhost:5173"; node scripts/demo-path-smoke.mjs
```

Linux/macOS:

```bash
source "$HOME/.nvm/nvm.sh" && API_URL=http://localhost:8000 FRONTEND_URL=http://localhost:5173 node scripts/demo-path-smoke.mjs
```

Then walk the manual demo path in `docs/demo-path-checklist.md`.

For hosted Caddy deployments, confirm Caddy routes the API prefix and frontend
root separately:

```bash
curl https://cockpit.example.com/api/health
curl -I https://cockpit.example.com/
```

Then run the smoke gate against the hosted origin. If `API_KEY` is set, provide
it as `SMOKE_API_KEY` or `API_KEY`:

```bash
source "$HOME/.nvm/nvm.sh" && API_URL=https://cockpit.example.com/api FRONTEND_URL=https://cockpit.example.com node scripts/demo-path-smoke.mjs
```

## Alerts and Failures

| Symptom | Likely Cause | First Action |
|---------|-------------|--------------|
| Backend won't start | Missing `.venv` or `requirements.txt` changed | `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| `graph_configured: false` in `/health` | Fresh instance with no workspace graph yet | Open Scope to generate a workspace graph or upload one in Settings |
| `graph_configured: true` and `graph_loaded: false` in `/health` | `GRAPH_PATH` points to a missing or malformed file | Check `.env` for Docker or `backend/.env` for native runs |
| Ask/Chat returns error | Ollama not running | `ollama serve` in a separate terminal; confirm model is pulled (`ollama list`) |
| 401 Unauthorized | `API_KEY` is set but client isn't sending the header | Set `Authorization: Bearer <key>` or `X-API-Key: <key>`; or unset `API_KEY` for local-only use |
| 429 Too Many Requests | Rate limit hit (60 req/min per IP) | Wait 60 seconds; `/health` is exempt |
| CORS errors in browser | `CORS_ORIGINS` doesn't match the frontend URL | Update `CORS_ORIGINS` in `backend/.env` to match exact scheme+host+port |
| AI panel off-screen | `localStorage` position persisted off-screen | Clear `copilot_pos` from DevTools → Application → Local Storage |
| Supabase sync failing | `SUPABASE_URL` or `SUPABASE_KEY` wrong, or migration 002 not applied | Check `.env`; inspect `storage` in `/health`; apply `db/migrations/002_recommendation_action_plans.sql` only with owner approval |
| Cloud sync failing | MSAL token expired or wrong tenant | Re-run `POST /connectors/{connector_id}/sync` or re-authenticate from Settings |
| Frontend won't load | Port 5173 in use or Vite didn't start | Check `launcher/frontend.log`; kill stale process on that port |
| Graph generation appears to stall/reset when the window is backgrounded | Browser background-tab timer throttling and tab discarding — the rebuild itself keeps running in a backend daemon thread; only the UI's view of it was affected | Use the launcher's app-mode window (default for Chromium browsers). The Map tab also re-attaches to an in-flight rebuild on load and catches up immediately on `visibilitychange`, so progress reconnects when you return |
| `GRAPHIFY_MISSING` in Ask or rebuild | Graphify CLI is not installed or not on `PATH` | Run `pip install graphifyy`, rebuild Docker if applicable, then confirm `graphify --version` |
| `GRAPHIFY_TIMEOUT` in Ask or rebuild | Graphify CLI exceeded the route timeout | Retry on a smaller graph or inspect the configured scan directories |
| Rebuild never elevates | `GRAPH_ESCALATION_ENABLED` is false or no `GRAPH_ESCALATION_BACKEND` is configured | Set both env vars, configure the provider key expected by Graphify, restart the backend, then check `/graph/rebuild/status` |
| Elevated rebuild fails | Provider key/model/backend is unavailable or Graphify extract timed out | Check `/graph/rebuild/status.detail`, provider env vars, and `GRAPH_ESCALATION_TIMEOUT`; roll back by setting `GRAPH_ESCALATION_ENABLED=false` |
| Graph rebuild hanging | `graphify update` subprocess stalled | Check `GET /graph/rebuild/status`; kill backend and restart if stuck |

## Dependencies

| Dependency | Required | How To Check |
|-----------|----------|-------------|
| Python 3.11+ | Yes | `python3 --version` |
| Node.js 18+ | Yes | `node --version` |
| Ollama | For Ask/Chat/Recommendations | `curl http://localhost:11434` |
| Graphify CLI | For Ask and graph rebuild | `graphify --version` |
| Supabase | Only if `STORAGE_BACKEND=supabase` | Check env vars and `storage.ready`; see `docs/integration-guide.md` |
| Microsoft 365 OAuth | Only if using Cloud Connectors | MSAL device code; see `docs/integration-guide.md` |

## Stopping the Cockpit

If started with `start.sh`: press `Ctrl-C` — the trap kills both background processes.

If started via the Windows launcher, use `launcher\restart-cockpit.bat` to refresh both services after code updates, or stop the listener processes on ports 8000 and 5173 from Task Manager.

If started via the Linux desktop launcher (`nohup`/`disown`):
```bash
pkill -f "uvicorn main:app"
pkill -f "vite"
```

## Recovery

**Backend crash loop:** check `launcher/backend.log` for the exception. Most common cause is a changed `requirements.txt` without reinstalling.

**Corrupted state:** state files live in `workspace/state/`. They are JSON; delete the corrupted file and the backend will recreate it on next write. No data is truly lost — decisions, recommendations, and actions are only ever written; nothing auto-deletes.

**Active graph:** if `graph_configured: false`, the instance has no workspace graph yet. Generate one from Scope, upload one in Settings, or set `GRAPH_PATH` to an existing `graph.json` and restart the backend.

## Escalation

This is a single-developer local tool. There is no on-call rotation. If something is broken and the runbook doesn't cover it:

1. Check `launcher/backend.log` and `launcher/frontend.log`.
2. Run `curl http://localhost:8000/health` and read the full response.
3. Grep `backend/main.py` for the failing endpoint.
4. Open a new Codex or Claude Code session in the repo — the docs and code are the source of truth.
