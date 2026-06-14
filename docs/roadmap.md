# Roadmap

Last Updated: 2026-06-14
Owner: Adam Goodwin

## Done

- **Chunk One** — Governance baseline: docs filled, risk register, agent inventory, prompt register, tool permission matrix
- **Chunk Two** — Single app shell: FastAPI backend, React/Vite frontend, five-tab cockpit, start.sh launcher
- **Chunk Three** — Ask interface: graph-backed Q&A via `graphify query/path/explain`, session transcripts
- **Chunk Four** — Readable map: clustered project-level Cytoscape.js view, drill-down, inspect panel, filters
- **Chunk Five** — Decision ledger: persistent classifications, map badges, accept/edit/retire
- **Chunk Six** — Recommendation queue: Ollama-backed cards, accept/reject/defer, evidence inspection
- **Chunk Seven** — Steady work mode: bounded background missions, progress log, cancel
- **Chunk Eight** — Approved actions: dry-run gate, explicit confirmation, execution report, rollback note

## Now

- **Chunk Nine** — GitHub packaging + network wiring:
  - env-var layer (`VITE_API_URL`, `GRAPH_PATH`, `STATE_DIR`, `CORS_ORIGINS`, `OLLAMA_URL`)
  - `Dockerfile` + `docker-compose.yml`
  - demo graph (no private data)
  - clean README (local dev + hosted Docker modes)
  - CI on push
  - auth warning in docs before any network exposure

## Next

- **Chunk Ten** — Network-ready deployment:
  - API key authentication gate
  - HTTPS via Caddy reverse proxy
  - graph upload API (no SSH required)
  - responsive layout for Android tablet
  - Windows Docker setup guide
  - configurable Ollama URL

## Soon

- **Chunk Eleven** — Shared state / company-wide source of truth:
  - storage backend abstraction (`file` or `supabase`)
  - decisions + recommendations + actions visible across all devices in real time
  - `created_by` identity on all records
  - multiple named graphs per organization
  - Graphify → UAOS handoff contract endpoint (`GET /actions?format=uaos`)
  - organization settings panel

## Strategic Direction

The cockpit is the knowledge backbone of Adam's AI-native operating system.

The build sequence follows a deliberate progression:

```
Single-machine local tool (Chunks 1–8)
  → Portable and installable anywhere (Chunk 9)
    → Reachable from any device on the network (Chunk 10)
      → Shared truth across all devices and team members (Chunk 11)
        → Knowledge spoke consumed by UAOS mission envelope (Chunk 11 handoff)
```

Each layer is independently useful and does not require the next. A developer
who only does Chunk 9 gets a clean local tool. A developer who adds Chunk 10
gets cross-device access. Chunk 11 turns individual use into organizational
memory.

## What Becomes Possible After Each Chunk

| After Chunk | New capability |
|---|---|
| 9 | Any laptop can clone and run the cockpit in under 15 minutes |
| 10 | Android tablet, Windows laptop, or remote worker can use the cockpit without a local install |
| 10 | A single hosted instance serves the whole team |
| 11 | Decision made on one device is immediately visible on all others |
| 11 | UAOS can consume cockpit decisions as mission candidates through the handoff endpoint |
| 11 | The organization has a single source of truth for workspace decisions, recommended actions, and approved changes |

## Non-Goals For Chunks 1–9

- Multi-user collaboration
- Cloud sync
- External authentication (OAuth, SSO)
- Client workspace access
- Public internet exposure (auth is a Chunk 10 prerequisite)
- Autonomous execution without approval
- Editing arbitrary source files from the UI

## Non-Goals For Chunks 10–11

- Autonomous commits, pushes, or destructive actions
- Public client access (separate governance decision required)
- Whole-workspace semantic re-extraction from the UI
- Replacing Codex or Claude as the coding assistant
- Microsoft 365 integration (separate UAOS spoke — defined in
  `user-ai-operating-system/docs/specs/graphify-workspace-cockpit-uaos-integration.md`)
