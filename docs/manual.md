# Manual

## What This Project Is

Graphify Workspace Cockpit is a local-first decision surface for developers and
builders who use [Graphify](https://github.com/safishamsi/graphify) to map
their workspace. It turns a semantic `graph.json` into an interactive cockpit
where you can ask questions, inspect relationships, record decisions, review
model recommendations, approve actions, and chat with an AI assistant — all
without leaving your browser.

The cockpit is read-only by default. It cannot make commits, push code, or
delete files without explicit human approval through the dry-run gate in the
Work Queue.

See `docs/vision.md` for the strategic context and `docs/architecture.md` for
the technical component map.

## How To Run It

**Local dev:**

```bash
bash scripts/start.sh
```

Opens the frontend at `http://localhost:5173`. Backend runs at `http://localhost:8000`.

**Docker:**

```bash
docker-compose up --build
```

See `docs/deployment-guide.md` for network deployments, API key setup, and HTTPS via Caddy.

## What The Tabs Do

| Tab | Purpose |
|-----|---------|
| **Ask** | Ask natural language questions about your workspace graph. Answers are backed by `graphify query/path/explain` with optional Ollama synthesis. Evidence nodes link directly to map view. |
| **Map** | Interactive Cytoscape.js graph at project/cluster level. Click any node to inspect. Filter by type, theme, or decision status. Use "Why connected?" to trace paths between nodes. |
| **Decisions** | Record durable human decisions about workspace areas. Classifications: invest, finish, merge, archive, extract, ignore. Decision badges appear on Map nodes. |
| **Recommendations** | Review model-backed cards with evidence, confidence, risk, and a proposed action. Accept, reject, or defer. Accepted recommendations flow into the Work Queue. |
| **Work Queue** | Review queued actions from accepted recommendations. Every action requires a dry-run preview before execution. Executed actions include a rollback note. |
| **Settings** | Upload a graph, view Ollama connection status, configure source + cluster toggles for context filtering, configure the AI assistant, and trigger a graph rebuild. |

## The AI Assistant

The AI assistant is a floating panel available in every tab. Click the "AI"
button in the corner to open it. It streams responses from Ollama using your
active cluster selection as context. The "X nodes used" chip on each response
shows how many graph nodes were included.

The assistant is read-only — it cannot trigger actions, write decisions, or
execute anything. Use it to explore the graph, ask follow-up questions, or
think through recommendations.

Configure the system prompt and model in **Settings → AI Assistant**.

## Knowledge Sources and Cluster Context

The **Settings → Knowledge Sources** panel controls which sources and clusters
are active. Active clusters filter the graph context passed to Ask, Chat, and
Recommendation endpoints. Narrowing the cluster selection focuses answers on a
specific project area and reduces noise.

The Map tab shows a source chip ("X of Y sources active") and links to Settings
when sources are filtered.

## Working In This Repo (for agents and developers)

For ordinary scoped work:

1. Check `git status --short`.
2. Read repo-local agent instructions (`CLAUDE.md`, `AI_BOOTSTRAP.md`).
3. Use `docs/context-map.md` to choose only the docs and source areas needed.
4. Inspect specific files or errors relevant to the task.
5. Run targeted validation after the change.

For material or risk-triggering changes:

1. Run `bash scripts/governance-preflight.sh`.
2. Review `docs/standards/README.md`.
3. Review `docs/standards/engineering-governance-by-use-case.md`.
4. Review `docs/policy/durable-development-engineering-policy.md`.
5. Review `docs/standards/ship-ready-engineering-standard.md`.
6. Capture a timestamp with `date -Iseconds`.
7. Confirm roadmap and runbook still match reality.
8. Update docs when behavior or operating expectations change.

## Common Gotchas

- **Ollama not running:** Ask and Chat return an error message; the cockpit still works for Map, Decisions, and Work Queue. Start Ollama with `ollama serve`.
- **Graph not loading:** Check `GRAPH_PATH` in `backend/.env`. The default is the demo graph at `workspace/demo/graph.json`.
- **CORS errors:** `CORS_ORIGINS` must match the exact scheme + host + port the browser uses.
- **API 401:** Set `Authorization: Bearer <key>` or `X-API-Key: <key>` if `API_KEY` is set.
- **Panel off-screen:** The AI assistant position is saved in `localStorage`. Clear `copilot_pos` from browser DevTools → Application → localStorage to reset it.

## Expected Outputs

- Working code or deliverables
- Current operational documentation
- A maintained roadmap (`docs/roadmap.md`)
- Timestamped build pathway updates for material work
- Scoped context and budget notes for meaningful chunks
- Reviewable governance records

## Completion Standard

A task is not complete until relevant validation is run or a blocker is clearly
stated. Valid completion labels: `Draft complete`, `Task complete`,
`Integration complete`, `Release ready`, or `Blocked`. Project completion is a
human decision.
