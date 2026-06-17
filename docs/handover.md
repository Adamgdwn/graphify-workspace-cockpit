# Handover — Graphify Workspace Cockpit

Status: superseded archive — 0-to-1 decision-flow polish evidence
Date: 2026-06-17
Owner: Adam Goodwin

---

## What Was Built

The Graphify Workspace Cockpit is a local-first decision surface that turns a
semantic `graph.json` workspace graph into an interactive browser UI. It was
built from zero to one in 19 chunks across a single intensive session, then
polished through Chunk 26 into a Command-first decision workflow with demo
readiness evidence.

### The 0→1 Journey

| Chunk | What Changed |
|-------|-------------|
| 1 | Governance baseline — docs, risk register, agent inventory, policy docs |
| 2 | App shell — FastAPI backend, React/Vite frontend, initial cockpit shell, start.sh |
| 3 | Ask interface — graph-backed Q&A, Ollama synthesis, session transcripts |
| 4 | Readable map — Cytoscape.js, drill-down, inspect panel, path tracing |
| 5 | Decision ledger — persistent classifications, Map badges |
| 6 | Recommendation queue — Ollama cards, accept/reject/defer, evidence links |
| 7 | Steady work mode — bounded background missions, cancel, progress log |
| 8 | Approved actions — dry-run gate, explicit confirmation, rollback note |
| 9 | GitHub packaging — env-var layer, Dockerfile, docker-compose, demo graph, CI |
| 10 | Network-ready deployment — API key auth, Caddy HTTPS, graph upload, responsive |
| 11 | Shared state — Supabase backend, cross-device sync, named graphs, UAOS handoff |
| 12 | Real graph foundation — first live workspace graph, demo_mode flag, validation |
| 13 | Demo polish and UX quality — empty states, exports, Ctrl+K, god node ring |
| 14 | Cloud knowledge base connectors — SharePoint + OneNote OAuth, background sync |
| 15 | Hardening, polish, and help — rate limiting, session pruning, graph rebuild, HelpModal, ErrorBoundary |
| 16 | Knowledge base cluster selector — source/cluster toggles, cluster-filtered context |
| 17 | In-cockpit AI assistant — floating overlay panel, SSE streaming, graph context |
| 18 | Overlap analysis — cross-cluster semantic edge panel, Highlight on map, Create Task from overlap |
| 19 | Signal/noise filtering + LLM triage — same-name detection, similarity chips, POST /overlap/triage, verdict badges, Next step actions, triage-aware task creation, Highlight/fade bug fix |
| 20 | Decision-flow foundation — aligned decision vocabulary and App-level active cockpit context |
| 21 | Evidence navigation — Ask and Recommendation evidence click into focused Map context |
| 22 | Map mode polish — Explore / Trace / Overlap / Review modes |
| 23 | Overlap triage workflow — durable untriaged, triaged, task-created, and dismissed states |
| 24 | Decision Command Center — first-tab attention view for recommendations, actions, overlaps, and graph freshness |
| 25 | Confidence and shipped evidence — live smoke check, demo checklist, runbook gate, current video prompt |
| 26 | Final owner UI readiness sweep — browser walkthrough across seven tabs and Ask evidence submission; no speculative product-code changes |

### Key Design Decisions

**AI assistant as floating overlay, not a tab** (ADR-006 in `docs/architecture.md`)
The original plan called for a sixth Chat tab. During Chunk 17 implementation this was changed to a floating draggable panel rendered at the App root. Rationale: the assistant is most useful when it stays visible while you're working in another tab.

**Local-first by default**
All state is file-based in `workspace/state/`. Supabase and Cloud Connectors are opt-in, configured via env vars. Nothing external is called unless explicitly configured.

**Read-only by construction** (except the approved action gate)
Agents AG-001, AG-002, AG-003, and AG-005 cannot mutate workspace files. Only AG-004 (Action Executor) can execute, and it requires dry-run + explicit human approval for each action.

---

## Current State at Pause

The cockpit is fully functional for the current local demo path. All 26 chunks
in the documented build pathway are complete, with the current decision-flow
polish path marked integration complete. Project completion and release
decisions remain Adam's call after hands-on testing.

**What works:**
- Seven tabs: Command, Ask, Map, Decisions, Recommendations, Work Queue, Settings
- Command Center with pending recommendation, accepted-not-queued, dry-run-ready action, untriaged overlap, graph freshness, and semantic freshness signals
- Ask and Recommendation evidence navigation into focused Map context
- Map modes: Explore, Trace, Overlap, Review
- Durable overlap workflow statuses: untriaged, triaged, task-created, dismissed
- Live demo smoke check: `source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs`
- Manual demo path: `docs/demo-path-checklist.md`
- Floating AI assistant with SSE streaming and cluster-filtered context (Chunk 17)
- Knowledge base cluster selector (Settings → Knowledge Sources) (Chunk 16)
- Cloud connector sync (SharePoint + OneNote) — opt-in via env vars (Chunk 14)
- Supabase cross-device sync — opt-in via `STORAGE_BACKEND=supabase` (Chunk 11)
- API key auth, Caddy HTTPS, Docker deployment, rate limiting (Chunks 9–10, 15)
- Desktop launcher (`~/Desktop/graphify-cockpit.desktop`)
- **Overlap Analysis panel** — 14 cross-cluster pairs, 1,988 semantic edges, Highlight on map, Create Task (Chunk 18)
- **LLM triage** — `POST /overlap/triage` classifies each pair as duplicate/reference/related using phi4; same-name detection surfaces filename matches as strong duplicate signal; verdict drives task title and proposed_action (Chunk 19)
- **Highlight/fade** — fixed CSS specificity bug so non-highlighted pairs actually fade; browse mode dims edges to 22% when panel is open

**What is not yet built (candidates, not commitments):**
- End-to-end test suite (Playwright or Vitest + MSW)
- Markdown rendering for Ask and Chat responses
- Graph rebuild progress streaming (currently polls status endpoint)
- Mobile layout below 768px
- Hosted model adapters (Claude API, OpenAI) — requires separate ADR

---

## How To Resume

1. Open this repo: `cd /home/adamgoodwin/code/agents/graphify-workspace-cockpit`
2. Run `git status --short` and read `AGENTS.md` plus `START_HERE.md`.
3. Read `docs/relationship-map-plan.md` for the active continuation path.
4. Open this handover, `docs/workspace-scope-and-signal-plan.md`, `docs/current-build-pathway.md`, or `docs/stabilization-plan.md` only for historical evidence or regression context.
5. Use `docs/context-map.md` to select which docs to load for the task.

---

## Where Everything Lives

| What | Where |
|------|-------|
| Active relationship map plan | `docs/relationship-map-plan.md` |
| Completed workspace scope + signal history | `docs/workspace-scope-and-signal-plan.md` |
| Completed stabilization evidence | `docs/stabilization-plan.md` |
| Archived build history | `docs/current-build-pathway.md` |
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

The repository remembers. Agents rent context. That principle held through the
0→1 build, the decision-flow polish pass, and the Chunk 25/26 close-out packet.
