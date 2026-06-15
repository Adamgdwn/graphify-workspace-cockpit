# Video Script Generation Prompt

Copy everything from the horizontal rule below and paste it to Claude or ChatGPT.
Replace `[TOPIC]` with your chosen topic from the list at the bottom, then send.

---

## The Prompt

You are writing a detailed YouTube video script for a developer audience. The
video is about the **Graphify Workspace Cockpit** — a local-first browser UI
that turns a semantic workspace graph into an interactive decision surface for
developers and builders.

---

### What the Cockpit Is

The Graphify Workspace Cockpit sits on top of
[Graphify](https://github.com/safishamsi/graphify), a CLI tool that reads a
codebase or workspace and produces a semantic `graph.json` — nodes (files,
functions, concepts, documents), edges (relationships between them), and
clusters (thematic groupings detected automatically).

The cockpit is a local web app (FastAPI backend + React/Vite frontend). No
account, no cloud, no data leaving the machine. It runs at
`http://localhost:5173`.

---

### What It Does — Tab by Tab

**Ask tab**
Graph-backed Q&A. You type a natural language question. The backend runs
`graphify query`, `graphify path`, and `graphify explain` against the live
graph, optionally synthesizes a natural language answer via Ollama (local
model), and returns: short answer, evidence nodes (linked to the Map), and
follow-up question suggestions. The active cluster selection filters which
graph nodes are included in context.

**Map tab**
Interactive Cytoscape.js graph at the project or cluster level. Click any
node to inspect it. Filter by type, theme, or decision status. "Why connected?"
traces the shortest path between any two nodes. God nodes (top-5 by edge
weight) are highlighted with a gold ring. Drill down to file level on demand.

**Decisions tab**
A durable human decision ledger. You classify workspace areas: invest,
client-ready, monitor, archive, or paused. Decisions persist in
`workspace/state/decisions.json` and appear as badges on Map nodes. The model
never makes decisions — only surfaces options.

**Recommendations tab**
Ollama-generated cards with: evidence nodes, confidence score, risk level, and
a proposed action. You accept, reject, or defer each one. Accepted
recommendations flow into the Work Queue.

**Work Queue tab**
Pending and executed actions from accepted recommendations. Every action
requires a dry-run preview before execution. After execution, a rollback note
is recorded. Background missions (bounded analysis runs) also appear here.

**Settings tab**
Graph upload, Ollama connection status, source + cluster toggles (Knowledge
Sources panel), AI assistant configuration, and a graph rebuild button with
token savings estimate.

**AI Assistant (floating overlay)**
A draggable, resizable chat panel visible in every tab — click the "AI" button
to open it. Streams responses from Ollama using the active cluster selection
as graph context. Each response shows an "X nodes used" chip. The panel
position, size, and expanded state persist across page loads via localStorage.
The system prompt and model are configurable in Settings → AI Assistant. The
assistant is read-only: it cannot trigger actions, write decisions, or mutate
anything.

---

### Key Technical Facts

- **Graph:** `graph.json` produced by Graphify CLI. 533 nodes, 645 edges in the
  real workspace graph. A bundled demo graph ships with the repo for first-run.
- **Inference:** Ollama (local). No external model API required. Degrades
  gracefully if Ollama is unavailable.
- **State:** All persistence is in `workspace/state/` — flat JSON files.
  Optional Supabase backend for cross-device sync (`STORAGE_BACKEND=supabase`).
- **Cloud connectors:** SharePoint and OneNote sync via Microsoft OAuth (MSAL
  device code). Cloud-source nodes are visually distinct on the Map.
- **Deployment:** `bash scripts/start.sh` for local dev. Docker + Caddy for
  network deployments with HTTPS. API key auth via `API_KEY` env var.
- **Safety model:** All agents are A1 (read-only) except the Action Executor
  (A2 — dry-run + explicit human approval required before each execution).
- **Rate limiting:** 60 req/min per IP via slowapi. `/health` exempt.

---

### Strategic Layer (use when the video needs a bigger-picture angle)

The cockpit is Layer 2 of an AI-native operating system:

```
Layer 1 — Knowledge Extraction
  Graphify CLI + graph.json
  Reads repos, docs, workspace structure
  Produces a semantic workspace graph

Layer 2 — Decision Intelligence (the cockpit)
  Answers questions, maps relationships, proposes recommendations
  Records human decisions, accepted recommendations, approved actions
  Exports durable governed artifacts via GET /actions?format=uaos

Layer 3 — Mission Execution
  User AI Operating System (UAOS)
  Reads cockpit artifacts through the handoff contract
  Proposes and executes policy-gated missions
```

---

### Script Format

Write the script in this structure:

**YouTube Comment (50–80 words)**
A short comment the creator could drop on a related video. Confident, specific,
no hype words.

**Full Video Script**
- `### Hook (0:00–0:30)` — open with the problem or a surprising demo moment
- `### The Problem It Solves (0:30–1:00)` — who this is for, what it replaces
- `### Demo (1:00–3:30)` — walk through the UI with `[screen direction]` notes
- `### The Key Insight (3:30–4:15)` — what makes this different or non-obvious
- `### What's Next (4:15–4:45)` — optional: roadmap or call to action
- `### Close (4:45–5:00)` — direct, no fluff

**Recording Notes**
Bullet list of what needs to be live/demo-ready before recording, what can be
narrated vs. shown, and any caveats about the current state of the feature.

---

### Tone

- Direct and technical. Developer audience — assume they know what a REST API
  and a graph are.
- No hype words: "revolutionary", "game-changer", "insane", "absolutely".
- Show, don't tell. If the demo proves the point, the script shouldn't re-explain
  it in words.
- First-person builder voice. "I built this because..." not "This tool allows
  users to..."

---

### Video Topic

Write a full script for this topic:

**[TOPIC]**

---

### Available Topics (pick one or suggest your own)

1. **The floating AI assistant** — Why a tab was the wrong call. How the overlay
   panel changes the way you use the cockpit. Demo: open a Map node, ask a
   question about it without leaving Map, see "X nodes used".

2. **The dry-run gate** — How approved actions work. Why every action requires
   a preview before execution and a rollback note after. The difference between
   a recommendation and an action.

3. **Cluster-filtered context** — How the Knowledge Sources panel changes what
   the AI knows. Demo: answer the same question with all clusters active vs. one
   cluster active. Show the node count change.

4. **The decision ledger** — Why durable human decisions are the foundation of
   the whole system. Demo: classify a project area, see the badge on the Map,
   see how it suppresses duplicate recommendations.

5. **Cloud connectors** — How SharePoint and OneNote fold into the same graph as
   the codebase. What it looks like when a document node sits next to a function
   node.

6. **Building your AI agent's brain** — The full Layer 1 → 2 → 3 stack.
   Graphify extracts the graph, the cockpit records the decisions, UAOS consumes
   the handoff. What the export looks like and why the format matters.

7. **Zero to one in one session** — The build story. 19 chunks, one Claude Code
   session, one context ceiling hit. What the governance baseline in Chunk 1
   made possible in Chunks 14–19.

8. **Ask vs. Chat** — When to use the Ask tab (structured Q&A with evidence
   nodes) vs. the AI assistant (conversational follow-up). How they share cluster
   context but serve different mental modes.
