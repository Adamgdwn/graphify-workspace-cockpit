# Graphify Workspace Cockpit

A local-first decision cockpit for developers and builders who use [Graphify](https://github.com/safishamsi/graphify) to map their workspace.

> Show me what I have, explain what it means, recommend what to do next, and wait for permission before acting.

---

## Built on Graphify

This project is powered by **[Graphify](https://github.com/safishamsi/graphify)** — an open-source tool by [safishamsi](https://github.com/safishamsi) that extracts semantic knowledge graphs from codebases and workspaces.

Graphify does the heavy lifting:
- Indexes your workspace into a traversable `graph.json`
- Exposes `graphify query`, `graphify path`, and `graphify explain` commands
- Finds relationships, communities, and patterns across any codebase or project folder

The cockpit is a UI layer on top of that graph. All credit for the core extraction and query engine belongs to the Graphify project.

---

## What This Cockpit Does

| Surface | What it does |
|---------|--------------|
| **Command** | First-screen readiness and attention view for runtime state, pending recommendations, accepted-but-not-queued work, dry-run-ready actions, untriaged overlaps, and graph freshness |
| **Ask** | Natural language questions answered from your graph (`graphify query/path/explain`) with optional local Ollama synthesis |
| **Map** | Interactive project-level relationship map — click to inspect, filter by type/theme/decision, drill down on demand |
| **Decisions** | Durable ledger of human decisions about workspace areas: invest, client-ready, monitor, archive, or paused |
| **Recommendations** | Model-backed cards with evidence, confidence, risk, action plans, read-only decision packets, and accept/reject/defer controls |
| **Work Queue** | Approval-gated action queue with dry-run previews, rollback notes, and execution reports |
| **Settings** | Graph upload, Ollama status, source + cluster toggles, AI assistant configuration, and graph rebuild |
| **AI Assistant** | Floating draggable/resizable chat panel — available in every tab. Streams responses from Ollama using your active cluster context. Collapse to a button when not needed. |

---

## Safety Model

- Read-only by default. No destructive actions without explicit human approval.
- Recommendations are proposals — they do not trigger actions.
- Decision packets combine evidence, judgement, recommendations, and approval state for review only; actions still flow through the Work Queue dry-run gate.
- No autonomous commits, pushes, deletes, or unapproved external side effects.
- Supabase and cloud connectors are opt-in and disabled unless configured.
- User-supplied graphs stay local. Secrets and environment files are never indexed, printed, or committed.

> **Security note:** Leave `API_KEY` unset only for localhost use. Set `API_KEY` before exposing the backend to any non-local network, and prefer HTTPS for hosted deployments.

---

## Prerequisites

- Python 3.10+ (backend)
- Node.js 18+ and npm (frontend)
- [Graphify](https://github.com/safishamsi/graphify): `pip install graphifyy` (required for Ask and graph rebuild; demo graph browsing still works without it)
- [Ollama](https://ollama.com) (optional — cockpit works without it, recommendations fall back to graph-only)

---

## Quick Start (one command)

The fastest way to run the cockpit. The launcher sets up the backend and frontend
on first run, starts both, and opens your browser at `http://localhost:5173`.
Assumes Python 3.10+ and Node 18+ are installed (see Prerequisites); the Docker
path below needs neither.

**Linux / macOS**

```bash
git clone <repo-url>
cd graphify-workspace-cockpit
./launcher/launch-cockpit.sh
```

For a click-to-launch icon in your application menu (Linux), run this once:

```bash
bash launcher/install-desktop-entry.sh
```

Then start the cockpit any time from your app menu — no terminal needed.

**Windows**

```bat
git clone <repo-url>
cd graphify-workspace-cockpit
```

Then double-click `launcher\launch-cockpit.bat`.

> The Windows launcher is **best-effort** and not yet tested across native Windows
> setups. If it misbehaves, use the verified Docker path below.

**Any OS (Docker)**

```bash
docker-compose up --build
```

Docker is the verified cross-platform option — see
[docs/deployment-guide.md](docs/deployment-guide.md) for Windows Docker Desktop
and Linux server instructions.

> **Coming later:** a true double-click desktop app with native installers for
> Windows and Linux — no terminal, no prerequisites — is planned once real-world
> usability on other machines is confirmed. For now, the launchers above and the
> Docker path are the supported ways to run it.

Prefer to set up each piece by hand? See **Setup: Local Dev Mode** below.

---

## Setup: Local Dev Mode

This is the manual path — set up each piece yourself. Use it if you want full
control or the one-command launcher above doesn't fit your environment. No Docker
required.

**1. Clone and install**

```bash
git clone <repo-url>
cd graphify-workspace-cockpit
```

**2. Set up the backend**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. Point it at your graph** (optional — demo graph is used by default)

```bash
cp .env.example .env               # from the backend/ directory
# Edit .env and set GRAPH_PATH to your graph.json:
# GRAPH_PATH=/path/to/your/workspace/graph.json
```

To generate a graph from your own workspace:
```bash
pip install graphifyy
graphify update /path/to/your/workspace
```

The backend reports Graphify runtime status in `/health` and Settings. If the
CLI is missing, the cockpit still loads with the active graph, but Ask and graph
rebuild return `GRAPHIFY_MISSING` until Graphify is installed on `PATH`.

**4. Set up the frontend**

```bash
cd ../frontend
npm install
```

**5. Launch both**

```bash
cd ..
bash scripts/start.sh
```

The app opens at `http://localhost:5173` or `http://127.0.0.1:5173`.
Backend runs at `http://localhost:8000` or `http://127.0.0.1:8000`.

---

## Setup: Docker (Hosted Mode)

Use this when you want to run the cockpit on a server or access it from multiple devices.

**1. Clone**

```bash
git clone <repo-url>
cd graphify-workspace-cockpit
```

**2. Configure**

```bash
cp backend/.env.example .env
# Optionally edit .env — the demo graph is used by default
```

**3. Start**

```bash
docker-compose up --build
```

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`

State (decisions, recommendations, actions) is persisted in `workspace/state/` on the host via a Docker volume mount.

The backend image installs `graphifyy` from `backend/requirements.txt`, so Ask
and graph rebuild are available in Docker as long as any configured scan paths
exist inside the container.

**Key env vars for hosted mode:**

| Variable | Default | Notes |
|----------|---------|-------|
| `GRAPH_PATH` | `workspace/demo/graph.json` | Path to your graph.json inside the container |
| `STATE_DIR` | `workspace/state` | Persistent state directory |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated list of allowed frontend origins; include the exact `localhost` or `127.0.0.1` URL you use |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Ollama server URL — `host.docker.internal` reaches the host machine |
| `VITE_API_URL` | `http://localhost:8000` | Backend URL the browser sends requests to (build-time). Use `/api` for Caddy-hosted same-origin deployments; use an absolute backend URL when the frontend and API are served separately. |
| `API_KEY` | unset | Required before exposing the backend beyond trusted localhost use |

To use your own graph with Docker, either:
- Set `GRAPH_PATH` to a path inside the container and mount the file
- Or use the graph upload API

> **Security note:** When you run this on a non-local host, set `API_KEY` and use HTTPS before exposing the backend to a network. In the browser, open Settings → API to save, test, or clear the key locally; the UI sends it as `X-API-Key` on backend requests.

---

## Demo

A synthetic demo graph (`workspace/demo/graph.json`) ships with the cockpit. It contains three fictional projects — `cockpit`, `knowledge-hub`, and `automation` — with enough nodes and links to demonstrate all tabs and the AI assistant. No private workspace data is included.

For the current demo-readiness gate, run:

```bash
source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs
```

Then follow `docs/demo-path-checklist.md` for the manual click path.

---

## Configuration Reference

**Backend** (see `backend/.env.example`):

```
GRAPH_PATH      Path to graph.json (default: workspace/demo/graph.json)
STATE_DIR       Persistent state directory (default: workspace/state)
CORS_ORIGINS    Comma-separated allowed origins (default: http://localhost:5173)
OLLAMA_URL      Ollama base URL (default: http://localhost:11434)
API_KEY         Optional API key for non-local deployments
```

**Frontend** (see `frontend/.env.example`):

```
VITE_API_URL    Backend API URL (default: http://localhost:8000)
```

For the optional Caddy HTTPS profile, build the frontend with
`VITE_API_URL=/api`. Caddy routes `/api/*` to the backend after stripping the
`/api` prefix, while `/` continues to serve the frontend.

When `API_KEY` is set, the frontend can store the key in browser localStorage
from Settings → API. Leave `API_KEY` unset only for fully trusted local
development.

---

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python FastAPI |
| Frontend | React + Vite (TypeScript) |
| Graph view | Cytoscape.js |
| Local model | Ollama HTTP API (optional) |
| Graph input | Graphify `graph.json` |
| Container | Docker + nginx |

---

## Documentation

- [docs/architecture.md](docs/architecture.md) — component map, data flow, state layout
- [docs/relationship-map-plan.md](docs/relationship-map-plan.md) — active relationship-map plan
- [docs/workspace-scope-and-signal-plan.md](docs/workspace-scope-and-signal-plan.md) — completed workspace scope and signal history
- [docs/stabilization-plan.md](docs/stabilization-plan.md) — completed hosted-beta stabilization evidence
- [docs/current-build-pathway.md](docs/current-build-pathway.md) — archived 0-to-1 build history and old validation evidence
- [docs/manual.md](docs/manual.md) — operator and developer manual
- [docs/runbook.md](docs/runbook.md) — operational startup, failure, and recovery notes
- [docs/demo-path-checklist.md](docs/demo-path-checklist.md) — demo-readiness smoke and manual walkthrough
- [docs/roadmap.md](docs/roadmap.md) — what's next
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — chunk-by-chunk change history
- [docs/agent-inventory.md](docs/agent-inventory.md) — agent definitions and autonomy levels
- [docs/tool-permission-matrix.md](docs/tool-permission-matrix.md) — what the cockpit can and cannot do
- [docs/risks/risk-register.md](docs/risks/risk-register.md) — known risks and controls
- [docs/vision.md](docs/vision.md) — strategic direction and multi-device architecture

---

## Credits

Core graph engine: **[Graphify](https://github.com/safishamsi/graphify)** by [safishamsi](https://github.com/safishamsi) — `pip install graphifyy`

Cockpit UI, recommendation layer, decision ledger, and work queue: Adam Goodwin / Guided AI Labs
