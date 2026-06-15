# Start Here

Last Updated: 2026-06-15T16:30:47-06:00
Status: integration complete — decision packet polish complete; awaiting owner UI testing
Owner: Adam Goodwin

## State at Pause

The first 30 build chunks are complete. The cockpit is a working local-first decision
surface: seven tabs (Command, Ask, Map, Decisions, Recommendations, Work Queue, Settings)
plus a floating AI assistant overlay. Desktop launcher is at
`~/Desktop/graphify-cockpit.desktop`.

The current decision-tool polish path is integration complete and split into
token-friendly chunks in `docs/current-build-pathway.md`. Chunk Twenty established the shared decision
vocabulary and App-level active cockpit context. Chunk Twenty-One made Ask and
Recommendation evidence navigate into focused Map context. Chunk Twenty-Two
grouped the Map toolbar into explicit Explore / Trace / Overlap / Review modes.
Chunk Twenty-Three turned overlap analysis into a durable review queue with
untriaged, triaged, task-created, and dismissed workflow states. Chunk
Twenty-Four added the Command Center as the first tab, with attention counts for
pending recommendations, accepted-not-queued items, dry-run-ready actions,
untriaged overlaps, graph freshness, and semantic freshness. Chunk Twenty-Five
added the demo smoke check, demo-path checklist, runbook note, and updated video
prompt. Chunk Twenty-Six closed the decision-flow polish path with a final live
browser sweep across all seven tabs and an Ask evidence submission. No new
owner-reported UI blocker was supplied in Chunk Twenty-Six, so no speculative
product-code change was made. A post-close-out documentation sweep aligned the
README, manual, architecture, deployment guide, roadmap, handover, changelog,
runbook, risk register, integration guide, tool permission matrix, vision, and
video prompts with the current seven-tab/demo-ready state. Chunks Twenty-Seven
through Thirty then deepened the decision surface: node provenance inspector,
overlap evidence dossier, recommendation action plans, and read-only decision
packets in Recommendation cards.

**Chunks 18–19 highlights:**
- Map → Overlap Analysis panel: 14 cross-cluster pairs, 1,988 semantic edges
- Per-pair LLM triage (phi4): classifies duplicate / reference / related with same-name detection
- Highlight on map, filter chips (70–90%), Task button creates verdict-specific recommendation
- Highlight/fade CSS specificity bug fixed; browse mode dims edges when panel open

Latest pushed demo-readiness commits before this planning pass:
`effaf4b` Prepare cockpit demo handoff, `15f889f` Fix launcher Node environment
loading, and `79ccf42` Fix overlap semantic highlight clearing.

## Where Things Live

| What | Where |
|------|-------|
| Build history and chunk status | `docs/current-build-pathway.md` |
| Architecture + ADRs | `docs/architecture.md` |
| Roadmap and non-goals | `docs/roadmap.md` |
| Full 0→1 build record | `docs/handover.md` |
| Operator manual | `docs/manual.md` |
| Operational runbook | `docs/runbook.md` |
| Context routing map | `docs/context-map.md` |

## To Resume

1. `git status --short` — confirm whether the Chunk Twenty-Seven through Thirty decision-tool polish packet has been committed.
2. Read the "Next Path - World-Class Decision Tool Polish" and "Chunk Thirty - Decision Packet View" sections in `docs/current-build-pathway.md`.
3. If Adam reports a specific UI issue, load only the affected tab/component and the related backend endpoint if needed.
4. Use `docs/context-map.md` if routing is still unclear.

## Work Patterns

**Ordinary scoped work:**
1. `git status --short`
2. Read repo-local agent instructions (`AGENTS.md`)
3. Use `docs/context-map.md` when context routing is unclear
4. Inspect only the specific files or errors needed
5. Run targeted validation after the change

**Material or risk-triggering changes:**
1. `bash scripts/governance-preflight.sh`
2. `docs/standards/README.md` → `docs/policy/durable-development-engineering-policy.md`
3. `docs/standards/ship-ready-engineering-standard.md` before declaring complete
4. `date -Iseconds` — timestamp the work
5. Work in the smallest complete chunk that can be reviewed safely

Risk-triggering work: production, deployment, auth, payments, secrets, database
migrations, external side effects, infrastructure, destructive actions, autonomous
tool use, governance changes, release readiness.

## Agent Handoff

Update this file only when the top-level plan or pause state changes. Put
detailed chunk progress in `docs/current-build-pathway.md`.
