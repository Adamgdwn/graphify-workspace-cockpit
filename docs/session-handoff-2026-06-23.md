# Session Handoff - 2026-06-23T09:57:48-06:00

Objective:

Box up the Windows-side Graphify Workspace Cockpit session after implementing
automatic graph generation escalation and updating the durable docs/control
records needed for a clean restart.

Current state:

Automatic graph escalation is implemented as a draft-complete feature ready for
owner verification. Default behavior remains local-only. When explicitly enabled
with environment variables, workspace map generation asks the local Ollama model
for a quick `local` vs `elevated` routing decision. If Ollama cannot answer, the
backend falls back to deterministic source-file/root-count heuristics. Local
route runs `graphify update --no-cluster`; elevated route runs configured
`graphify extract --backend <provider> --no-cluster`. Both routes keep the same
workspace-scope filter, merge, activation, and stale semantic-cache clearing
path.

Why this matters:

Adam rejected a manual "use a stronger model" path. The cockpit should decide
from the selected scope whether the local build is enough and elevate
automatically when configured. This keeps the selection workflow smooth while
leaving provider setup as the explicit opt-in boundary.

What changed in this session:

- `backend/config.py` gained graph escalation env settings:
  `GRAPH_ESCALATION_ENABLED`, backend/model, thresholds, decider model,
  timeouts, API timeout, and max concurrency.
- `backend/services/graphify_service.py` gained `run_graphify_extract()`, a
  typed subprocess wrapper around `graphify extract`.
- `backend/main.py` now estimates selected rebuild size, asks local Ollama for a
  route decision, falls back to heuristics, and records route metadata in
  `/graph/rebuild/status`.
- Rebuild callers now execute either local `graphify update --no-cluster` or
  elevated `graphify extract --backend ... --no-cluster` through one shared
  command boundary.
- `WorkspaceScopePicker`, `Map`, and `Settings` now show route-aware progress
  copy such as route evaluation, local graph generation, or elevated extraction.
- Env examples, Docker Compose, README, architecture, runbook, model registry,
  agent inventory, tool permission matrix, active relationship-map plan, and
  ADR-009 were updated to document the new opt-in external boundary.
- Windows work tracking was updated under:
  `C:\Users\adamg\01. Code Projects\01 Work Tracking\Enhanced Graphify`.

Important configuration:

```env
GRAPH_ESCALATION_ENABLED=true
GRAPH_ESCALATION_BACKEND=openai
GRAPH_ESCALATION_MODEL=gpt-4.1
OPENAI_API_KEY=...
```

Provider can be any backend supported by Graphify `extract` such as `gemini`,
`claude`, `openai`, `deepseek`, or `ollama`, with the matching provider
credentials present in the backend process environment. To roll back, set
`GRAPH_ESCALATION_ENABLED=false` or remove `GRAPH_ESCALATION_BACKEND`, then
restart the backend.

Files directly changed by the escalation/handoff work:

- `backend/config.py`
- `backend/main.py`
- `backend/services/graphify_service.py`
- `frontend/src/components/WorkspaceScopePicker.tsx`
- `frontend/src/tabs/Map.tsx`
- `frontend/src/tabs/Settings.tsx`
- `tests/test_graphify_service.py`
- `.env.example`
- `backend/.env.example`
- `docker-compose.yml`
- `README.md`
- `docs/adr-009-automatic-graph-escalation.md`
- `docs/agent-inventory.md`
- `docs/architecture.md`
- `docs/handover.md`
- `docs/model-registry.md`
- `docs/relationship-map-plan.md`
- `docs/runbook.md`
- `docs/tool-permission-matrix.md`
- `START_HERE.md`
- `AGENT_QUICKSTART.md`
- `docs/session-handoff-2026-06-23.md`

Validation run:

- `backend\.venv\Scripts\python.exe -m pytest tests/test_graphify_service.py -q`
  passed: 34 tests.
- `backend\.venv\Scripts\python.exe -m pytest tests -q` passed: 104 tests.
- `backend\.venv\Scripts\python.exe -m compileall -q backend` passed.
- `npm --prefix frontend run typecheck` passed.
- `npm --prefix frontend run build` passed.
- `git diff --check` passed, with expected Windows LF/CRLF warnings only.
- `graphify update . --no-cluster` passed and rebuilt the local graph:
  1,765 nodes and 3,400 edges.

Governance/preflight notes:

- The repo is still selected as `risk_tier: low` and `governance_level: 1`
  despite the `AI agent with tools` use case. This mismatch is a known owner
  override in the existing docs.
- The requested change adds an opt-in external model/provider boundary, so the
  control docs were updated instead of leaving the code ahead of the governance
  story.
- `bash scripts/governance-preflight.sh` fails directly on Windows because the
  shell scripts have CRLF endings. Running temporary LF-normalized copies showed
  the underlying checker then reports false-negative failures for
  `project-control.yaml` values that are visibly present, also due to CRLF.
  The project controls were not rewritten solely to fix line endings.

Known risks or unverified items:

- No live elevated provider call was run because no provider key was supplied in
  this session.
- Route decisions from the local model need owner verification on real broad
  selections. If decisions feel too aggressive or too timid, tune the prompt and
  thresholds rather than adding per-run prompts.
- The worktree was already dirty at startup with many user-owned changes. Do not
  assume every modified file in `git status --short` belongs to this session.
- Work tracking lives outside this git repository and is not versioned here.

Completion status:

Task complete for documentation closeout and draft-complete for the automatic
graph escalation feature. It is ready for owner verification, not release-ready
for arbitrary provider use.

Exact next step:

Restart with `git status --short`, `AGENTS.md`, `START_HERE.md`, this handoff,
and `docs/relationship-map-plan.md`. Then configure a provider backend if Adam
wants live verification, restart the backend, generate a broad workspace map,
and inspect `/graph/rebuild/status` to confirm the route decision and outcome.
