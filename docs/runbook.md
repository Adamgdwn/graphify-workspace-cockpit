# Runbook

Status: current
Last Updated: 2026-06-16
Owner: Adam Goodwin

## What This System Does In Operation

The Graphify Workspace Cockpit runs two local processes:

- **Backend** — FastAPI on `http://localhost:8000`. Reads `graph.json`, runs Graphify through the backend service wrapper, calls Ollama for inference, writes workspace state to `workspace/state/`.
- **Frontend** — Vite/React dev server on `http://localhost:5173`. Talks only to the backend.

Neither process connects to the internet unless Supabase (`STORAGE_BACKEND=supabase`) or Cloud Connectors (SharePoint/OneNote) are configured.

## Starting the Cockpit

**Via desktop launcher:** click "Graphify Cockpit" on the desktop. The launcher script starts both processes if not already running, waits for health checks, and opens the browser.

**Via terminal:**
```bash
bash /path/to/repo/scripts/start.sh
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

Response includes `status`, `graph_loaded`, `demo_mode`, and `graphify`. If
`graph_loaded` is false, check `GRAPH_PATH` in `backend/.env`. Check Ollama
separately with `curl http://localhost:8000/status/ollama`.

## Demo Readiness Check

With both processes running, use the lightweight smoke gate before recording or
handoff:

```bash
source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs
```

If the app is bound to `localhost` instead of `127.0.0.1`, override the URLs:

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
| `graph_loaded: false` in `/health` | `GRAPH_PATH` points to a missing or malformed file | Check `backend/.env` or `backend/.env.example`; default graph is `workspace/demo/graph.json` |
| Ask/Chat returns error | Ollama not running | `ollama serve` in a separate terminal; confirm model is pulled (`ollama list`) |
| 401 Unauthorized | `API_KEY` is set but client isn't sending the header | Set `Authorization: Bearer <key>` or `X-API-Key: <key>`; or unset `API_KEY` for local-only use |
| 429 Too Many Requests | Rate limit hit (60 req/min per IP) | Wait 60 seconds; `/health` is exempt |
| CORS errors in browser | `CORS_ORIGINS` doesn't match the frontend URL | Update `CORS_ORIGINS` in `backend/.env` to match exact scheme+host+port |
| AI panel off-screen | `localStorage` position persisted off-screen | Clear `copilot_pos` from DevTools → Application → Local Storage |
| Supabase sync failing | `SUPABASE_URL` or `SUPABASE_KEY` wrong | Check `.env`; test with `curl $SUPABASE_URL/rest/v1/decisions -H "apikey: $SUPABASE_KEY"` |
| Cloud sync failing | MSAL token expired or wrong tenant | Re-run `POST /connectors/{connector_id}/sync` or re-authenticate from Settings |
| Frontend won't load | Port 5173 in use or Vite didn't start | Check `launcher/frontend.log`; kill stale process on that port |
| `GRAPHIFY_MISSING` in Ask or rebuild | Graphify CLI is not installed or not on `PATH` | Run `pip install graphifyy`, rebuild Docker if applicable, then confirm `graphify --version` |
| `GRAPHIFY_TIMEOUT` in Ask or rebuild | Graphify CLI exceeded the route timeout | Retry on a smaller graph or inspect the configured scan directories |
| Graph rebuild hanging | `graphify update` subprocess stalled | Check `GET /graph/rebuild/status`; kill backend and restart if stuck |

## Dependencies

| Dependency | Required | How To Check |
|-----------|----------|-------------|
| Python 3.11+ | Yes | `python3 --version` |
| Node.js 18+ | Yes | `node --version` |
| Ollama | For Ask/Chat/Recommendations | `curl http://localhost:11434` |
| Graphify CLI | For Ask and graph rebuild | `graphify --version` |
| Supabase | Only if `STORAGE_BACKEND=supabase` | Check env vars; see `docs/integration-guide.md` |
| Microsoft 365 OAuth | Only if using Cloud Connectors | MSAL device code; see `docs/integration-guide.md` |

## Stopping the Cockpit

If started with `start.sh`: press `Ctrl-C` — the trap kills both background processes.

If started via the desktop launcher (`nohup`/`disown`):
```bash
pkill -f "uvicorn main:app"
pkill -f "vite"
```

## Recovery

**Backend crash loop:** check `launcher/backend.log` for the exception. Most common cause is a changed `requirements.txt` without reinstalling.

**Corrupted state:** state files live in `workspace/state/`. They are JSON; delete the corrupted file and the backend will recreate it on next write. No data is truly lost — decisions, recommendations, and actions are only ever written; nothing auto-deletes.

**Demo graph vs real graph:** if `demo_mode: true` in `/health` but you expect a real graph, set `GRAPH_PATH` to the absolute path of the real `graph.json` and restart the backend.

## Escalation

This is a single-developer local tool. There is no on-call rotation. If something is broken and the runbook doesn't cover it:

1. Check `launcher/backend.log` and `launcher/frontend.log`.
2. Run `curl http://localhost:8000/health` and read the full response.
3. Grep `backend/main.py` for the failing endpoint.
4. Open a new Codex or Claude Code session in the repo — the docs and code are the source of truth.
