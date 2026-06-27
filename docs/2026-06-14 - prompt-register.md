# Prompt Register

Document ID: PRM-REG-001
Status: current
Last Updated: 2026-06-14

| Prompt ID | Agent | Purpose | Template Path | Current Version | Status | Last Reviewed |
| --- | --- | --- | --- | --- | --- | --- |
| P-001 | Ask Synthesizer | Synthesize a natural language answer from graphify CLI output and user question; return short answer + evidence nodes + follow-up suggestions | Inline in `POST /ask` handler (`backend/main.py`) | v0.1 | Implemented (Chunk 3) | 2026-06-14 |
| P-002 | Recommendation Generator | Generate ranked recommendation cards from graph context using decision score (build direction, skill, reuse, profit, learning, cleanup, evidence, completeness, urgency, risk, effort) | `backend/prompts/recommend_ranked.txt` | v0.1 | Implemented (Chunk 6) | 2026-06-14 |
| P-003 | Recommendation Generator | Find archive candidates from graph metadata and decision history | `backend/prompts/recommend_archive.txt` | v0.1 | Implemented (Chunk 6) | 2026-06-14 |
| P-004 | Recommendation Generator | Identify duplicated build surfaces across workspace projects | `backend/prompts/recommend_duplicates.txt` | v0.1 | Implemented (Chunk 6) | 2026-06-14 |
| P-005 | Steady Work Agent | Rank next-build candidates using decision score | `backend/prompts/steady_rank_builds.txt` | v0.1 | Implemented (Chunk 7) | 2026-06-14 |
| P-006 | Steady Work Agent | Find weak docs/tests on active projects | `backend/prompts/steady_weak_coverage.txt` | v0.1 | Implemented (Chunk 7) | 2026-06-14 |
| P-007 | Action Executor | Propose a safe, bounded, dry-run-verifiable action from an accepted recommendation | Inline in `POST /actions/{id}/execute` handler (`backend/main.py`) | v0.1 | Implemented (Chunk 8) | 2026-06-14 |
| P-008 | AI Assistant | Stream conversational responses using cluster-filtered graph context; system prompt is user-configurable | Configurable — stored in `workspace/state/chat-config.json`; default applied inline in `POST /chat` handler | v0.1 | Implemented (Chunk 17) | 2026-06-14 |

## Prompt Governance Rules

- Prompts that propose actions must include a dry-run check requirement.
- Prompts must not instruct the model to skip approval gates.
- Prompts must not ask the model to read, print, or summarize secrets or environment files.
- Prompt templates live in `backend/prompts/`.
- Changes to prompts that affect action proposals, destructive suggestions, or autonomy level require an updated entry in this register and a reviewer sign-off.
