# Handover — Graphify Workspace Cockpit

Status: paused — build complete
Date: 2026-06-14
Owner: Adam Goodwin

---

## What Was Built

The Graphify Workspace Cockpit is a local-first decision surface that turns a
semantic `graph.json` workspace graph into an interactive browser UI. It was
built from zero to one in 17 chunks across a single intensive session.

### The 0→1 Journey

| Chunk | What Changed |
|-------|-------------|
| 1 | Governance baseline — docs, risk register, agent inventory, policy docs |
| 2 | App shell — FastAPI backend, React/Vite frontend, five-tab cockpit, start.sh |
| 3 | Ask interface — graph-backed Q&A, Ollama synthesis, session transcripts |
| 4 | Readable map — Cytoscape.js, drill-down, inspect panel, path tracing |
| 5 | Decision ledger — persistent classifications, Map badges |
| 6 | Recommendation queue — Ollama cards, accept/reject/defer, evidence links |
| 7 | Steady work mode — bounded background missions, cancel, progress log |
| 8 | Approved actions — dry-run gate, explicit confirmation, rollback note |
| 9 | GitHub packaging — env-var layer, Dockerfile, docker-compose, demo graph, CI |
| 10 | Network-ready deployment — API key auth, Caddy HTTPS, graph upload, responsive |
| 11 | Shared state — Supabase backend, cross-device sync, named graphs, UAOS handoff |
| 12 | Real graph foundation — live 533-node/645-edge graph, demo_mode flag, validation |
| 13 | Demo polish and UX quality — empty states, exports, Ctrl+K, god node ring |
| 14 | Cloud knowledge base connectors — SharePoint + OneNote OAuth, background sync |
| 15 | Hardening, polish, and help — rate limiting, session pruning, graph rebuild, HelpModal, ErrorBoundary |
| 16 | Knowledge base cluster selector — source/cluster toggles, cluster-filtered context |
| 17 | In-cockpit AI assistant — floating overlay panel, SSE streaming, graph context |

### Key Design Decisions

**AI assistant as floating overlay, not a tab** (ADR-006 in `docs/architecture.md`)
The original plan called for a sixth Chat tab. During Chunk 17 implementation this was changed to a floating draggable panel rendered at the App root. Rationale: the assistant is most useful when it stays visible while you're working in another tab.

**Local-first by default**
All state is file-based in `workspace/state/`. Supabase and Cloud Connectors are opt-in, configured via env vars. Nothing external is called unless explicitly configured.

**Read-only by construction** (except the approved action gate)
Agents AG-001, AG-002, AG-003, and AG-005 cannot mutate workspace files. Only AG-004 (Action Executor) can execute, and it requires dry-run + explicit human approval for each action.

---

## Current State at Pause

The cockpit is fully functional. All 17 chunks are complete and committed through Chunk 14. Chunks 15–17 and the documentation pass are uncommitted local changes.

**What works:**
- All six tabs: Ask, Map, Decisions, Recommendations, Work Queue, Settings
- Floating AI assistant with SSE streaming and cluster-filtered context
- Knowledge base cluster selector (Settings → Knowledge Sources)
- Cloud connector sync (SharePoint + OneNote) — opt-in via env vars
- Supabase cross-device sync — opt-in via `STORAGE_BACKEND=supabase`
- API key auth, Caddy HTTPS, Docker deployment, rate limiting
- Desktop launcher (`~/Desktop/graphify-cockpit.desktop`)

**What is not yet built (candidates, not commitments):**
- End-to-end test suite (Playwright or Vitest + MSW)
- Markdown rendering for Ask and Chat responses
- Graph rebuild progress streaming (currently polls status endpoint)
- Mobile layout below 768px
- Hosted model adapters (Claude API, OpenAI) — requires separate ADR

---

## How To Resume

1. Open this repo in Claude Code: `cd /home/adamgoodwin/code/agents/graphify-workspace-cockpit`
2. Run `git status --short` and read `START_HERE.md`.
3. Read `docs/current-build-pathway.md` to confirm which chunks are complete.
4. Any new work should be defined as a new chunk with: objective, acceptance criteria, validation, and stop condition.
5. Use `docs/context-map.md` to select which docs to load for the task.

---

## Where Everything Lives

| What | Where |
|------|-------|
| Active build plan | `docs/current-build-pathway.md` |
| Architecture + ADRs | `docs/architecture.md` |
| All domain terms | `docs/domain-language.md` |
| Agent boundaries | `docs/agent-inventory.md` |
| Prompt templates | `backend/prompts/` + inline in `backend/main.py` |
| Risk register | `docs/risks/risk-register.md` |
| Roadmap and non-goals | `docs/roadmap.md` |
| Operational runbook | `docs/runbook.md` |
| Full build history | `docs/CHANGELOG.md` |
| Operator manual | `docs/manual.md` |
| Context routing map | `docs/context-map.md` |
| Deployment and env vars | `docs/deployment-guide.md` |
| Cloud + Supabase setup | `docs/integration-guide.md` |
| App state | `workspace/state/` |
| Demo graph | `workspace/demo/graph.json` |
| Real workspace graph | `graphify-out/graph.json` |
| Desktop launcher | `launcher/launch-cockpit.sh` + `~/Desktop/graphify-cockpit.desktop` |

---

## Hosting Decision (When Going Live with UAOS)

The cockpit currently runs local-first. When UAOS needs to reach it remotely,
inference is the deciding dependency — Ollama is local and can't follow UAOS
into the cloud.

**Option A — Local machine + Cloudflare Tunnel (bridge option)**
Keep everything local. Cloudflare Tunnel (free) or Tailscale in front of Caddy
exposes the API to UAOS without port-forwarding. Fastest inference (your own
hardware). Downside: availability tied to your machine being on.

**Option B — VPS + Claude/OpenAI API inference (recommended for full UAOS live)**
- FastAPI backend on a small VPS (Hetzner CX22, ~€5/month — no GPU needed, just serves the app)
- React frontend as a static build on Vercel (free)
- Swap Ollama for Claude Haiku or Sonnet at the inference layer — the graph context passed as system prompt is already in the right shape for the API
- Supabase (already wired in) handles persistent state
- Graph syncs to the VPS via the existing graph upload API (`POST /graph/upload`)
- API key auth already in place

**What's already done toward Option B:** Supabase storage backend (Chunk 11),
graph upload API (Chunk 10), API key auth (Chunk 10), Docker deployment (Chunk 9).

**What's still needed:** ADR for hosted model adapter (noted in
`docs/model-registry.md`), small backend change to swap `OLLAMA_URL` for a
Claude/OpenAI client, and a Vite production build pointing at the VPS URL.

---

## What Made This Build Unusual

This 0→1 was done in a single continuous agentic session. The session hit the
Claude context ceiling mid-build (multiple compactions). The governance
baseline from Chunk 1 was load-bearing — it meant every subsequent agent
could re-orient from `START_HERE.md`, `AI_BOOTSTRAP.md`, and
`docs/context-map.md` without needing the full conversation history.

The repository remembers. Agents rent context. That principle held through 17
chunks and a session that ran so long the user needed a utilization break.
