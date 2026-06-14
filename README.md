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

| Tab | What it does |
|-----|--------------|
| **Ask** | Natural language questions answered from your graph (`graphify query/path/explain`) with optional local Ollama synthesis |
| **Map** | Interactive project-level relationship map — click to inspect, filter by type/theme/decision, drill down on demand |
| **Decisions** | Durable ledger of human decisions about workspace areas: invest, finish, merge, archive, extract, or ignore |
| **Recommendations** | Model-backed cards with evidence, confidence, risk, and accept/reject/defer controls |
| **Work Queue** | Approval-gated action queue with dry-run previews, rollback notes, and execution reports |

---

## Safety Model

- Read-only by default. No destructive actions without explicit human approval.
- Recommendations are proposals — they do not trigger actions.
- No autonomous commits, pushes, deletes, or external service calls.
- User-supplied graphs stay local. Secrets and environment files are never indexed, printed, or committed.

> **Security note:** The API has no authentication in this release. Do not expose the backend to a non-local network without first adding the API key gate described in [Chunk Ten](docs/current-build-pathway.md). Running behind `localhost` is safe; running on a public port is not.

---

## Prerequisites

- Python 3.10+ (backend)
- Node.js 18+ and npm (frontend)
- [Graphify](https://github.com/safishamsi/graphify): `pip install graphifyy`
- [Ollama](https://ollama.com) (optional — cockpit works without it, recommendations fall back to graph-only)

---

## Setup: Local Dev Mode

This is the fastest way to get started. No Docker required.

**1. Clone and install**

```bash
git clone <repo-url>
cd graphify-workspace-cockpit
```

**2. Set up the backend**

```bash
cd backend
python -m venv .venv
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

The app opens at `http://localhost:5173`. Backend runs at `http://localhost:8000`.

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

**Key env vars for hosted mode:**

| Variable | Default | Notes |
|----------|---------|-------|
| `GRAPH_PATH` | `workspace/demo/graph.json` | Path to your graph.json inside the container |
| `STATE_DIR` | `workspace/state` | Persistent state directory |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated list of allowed frontend origins |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Ollama server URL — `host.docker.internal` reaches the host machine |
| `VITE_API_URL` | `http://localhost:8000` | Backend URL the browser sends requests to (build-time) |

To use your own graph with Docker, either:
- Set `GRAPH_PATH` to a path inside the container and mount the file
- Or use the graph upload API (available in Chunk Ten)

> **Security note:** When you run this on a non-local host, set `API_KEY` and use HTTPS (both available in Chunk Ten) before exposing the backend to a network. The current release is authentication-free and designed for localhost use.

---

## Demo

A synthetic demo graph (`workspace/demo/graph.json`) ships with the cockpit. It contains three fictional projects — `cockpit`, `knowledge-hub`, and `automation` — with enough nodes and links to demonstrate all five tabs. No private workspace data is included.

---

## Configuration Reference

**Backend** (see `backend/.env.example`):

```
GRAPH_PATH      Path to graph.json (default: workspace/demo/graph.json)
STATE_DIR       Persistent state directory (default: workspace/state)
CORS_ORIGINS    Comma-separated allowed origins (default: http://localhost:5173)
OLLAMA_URL      Ollama base URL (default: http://localhost:11434)
```

**Frontend** (see `frontend/.env.example`):

```
VITE_API_URL    Backend API URL (default: http://localhost:8000)
```

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
- [docs/current-build-pathway.md](docs/current-build-pathway.md) — live build route and chunk status
- [docs/roadmap.md](docs/roadmap.md) — what's next
- [docs/agent-inventory.md](docs/agent-inventory.md) — agent definitions and autonomy levels
- [docs/tool-permission-matrix.md](docs/tool-permission-matrix.md) — what the cockpit can and cannot do
- [docs/risks/risk-register.md](docs/risks/risk-register.md) — known risks and controls
- [docs/vision.md](docs/vision.md) — strategic direction and multi-device architecture

---

## Credits

Core graph engine: **[Graphify](https://github.com/safishamsi/graphify)** by [safishamsi](https://github.com/safishamsi) — `pip install graphifyy`

Cockpit UI, recommendation layer, decision ledger, and work queue: Adam Goodwin / Guided AI Labs
