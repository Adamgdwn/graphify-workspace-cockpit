# Integration Guide

Last Updated: 2026-06-14

This guide covers how external systems — particularly the User AI Operating
System (UAOS) — consume the Graphify Workspace Cockpit API, the shape of the
handoff contract, and what a consumer must validate before proposing a mission.

---

## UAOS Handoff Contract

After a recommendation is accepted, queued, dry-run, and executed inside the
cockpit, the resulting action record becomes available to UAOS as a mission
candidate through the handoff endpoint.

### Endpoint

```
GET /actions?status=executed&format=uaos
```

Requires the same `Authorization: Bearer <key>` or `X-API-Key: <key>` header
as all other non-health endpoints when `API_KEY` is configured.

### Response shape

```json
{
  "schema_version": "1.0",
  "exported_at": "2026-06-14T...",
  "actions": [
    {
      "id": "uuid",
      "source_recommendation_id": "uuid",
      "action_type": "create_note | tag_for_archive",
      "description": "human-readable action description",
      "rec_title": "recommendation title",
      "rec_summary": "2-3 sentence summary from the recommendation card",
      "evidence": ["project-area-id", "..."],
      "confidence": 0.75,
      "risk": "low | medium | high | unknown",
      "proposed_action_text": "concrete proposed action from the recommendation",
      "result": {
        "success": true,
        "file_created": "workspace/state/notes/...",
        "message": "Created ..."
      },
      "rollback_note": "To undo: delete ...",
      "approved_at": "iso timestamp",
      "executed_at": "iso timestamp",
      "created_by": "adam",
      "uaos_mission_hint": {
        "proposed_mission_title": "derived from action description",
        "stop_triggers": [
          "stop before deleting files",
          "stop before external commits",
          "stop before mutating source outside workspace/state/"
        ],
        "approval_level": "A2",
        "files_in_scope": ["evidence nodes that are file paths"],
        "non_goals": ["destructive action", "external service calls"]
      }
    }
  ]
}
```

### Consumer validation requirements

Before a UAOS agent proposes a mission from a handoff record, it **must**
validate all of the following. Fail any check → log reason and stop.

| # | Check | How to fail |
|---|-------|-------------|
| 1 | `result.success` is `true` | Reject failed actions |
| 2 | `confidence >= 0.6` | Reject low-confidence cards |
| 3 | `risk` is `"low"` or `"medium"` | Reject `"high"` or `"unknown"` risk |
| 4 | No `stop_triggers` would be crossed | Parse `uaos_mission_hint.stop_triggers`; fail if the proposed mission would trigger one |
| 5 | Evidence nodes still exist in the current graph | Call `GET /graph/summary` or re-run `graphify query` to confirm the nodes are current |
| 6 | No conflicting decision for the same target | Call `GET /decisions` and check for a newer `archive` or `paused` classification on the same `target_id` |

The validator at `uaos_agent_spine/graphify_handoff.py` (REQ-0050) implements
these checks against locally supplied records. Wire it to the live endpoint
after Chunk 11 ships.

---

## Real-time State Synchronisation

The cockpit supports lightweight ETag-based polling. All list endpoints return
an `ETag` response header.

```
GET /decisions      → ETag: "d41d8cd98f00b204e9800998ecf8427e"
GET /recommendations → ETag: "..."
GET /actions        → ETag: "..."
```

A consumer that wants near-real-time state (< 30 seconds) should:

1. Store the last `ETag` value per endpoint.
2. On each poll, send `If-None-Match: <stored-etag>`.
3. If the response is `304 Not Modified`, no change — skip.
4. If the response is `200 OK`, update the stored ETag and process the new body.

Recommended poll interval: **15 seconds** (matches the frontend's built-in
polling). WebSocket upgrade path is documented below.

### Future: WebSocket upgrade

The current polling approach is intentionally simple. If sub-second latency
becomes necessary, a future WebSocket endpoint can be added at
`ws://<host>/ws/events` that pushes `{type: "decisions_changed", etag: "..."}`.
The frontend already uses `useRef`-based ETag tracking that is compatible with
a WebSocket drop-in.

---

## Multiple Named Graphs

The cockpit supports multiple named graph files. The active graph is the one
used by all query, map, and recommendation endpoints.

```
GET /graphs                          # list all available graphs
POST /graphs/{name}/activate         # switch the active graph (no restart needed)
POST /graph/upload                   # upload a new graph.json and activate it
```

A UAOS agent can push an updated workspace graph to the cockpit after running
`graphify update` on the workspace:

```bash
# 1. Update workspace graph
graphify update /home/adamgoodwin/code --no-cluster

# 2. Push to cockpit
curl -X POST \
  -H "X-API-Key: $COCKPIT_KEY" \
  -F "file=@/home/adamgoodwin/code/Tools/graphify/workspace/out/graph.json" \
  http://cockpit.example.com/api/graph/upload
```

---

## Supabase Storage Backend

When `STORAGE_BACKEND=supabase`, the cockpit stores decisions, recommendations,
actions, and sessions in a hosted Supabase database. The API surface is
identical — no frontend changes are required.

### Setup

1. Create a Supabase project at [supabase.com](https://supabase.com).
2. Run the migration: `psql $DATABASE_URL < db/migrations/001_initial.sql`
   or use `supabase db push` if you have the CLI installed.
3. Set env vars:
   ```
   STORAGE_BACKEND=supabase
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-or-service-role-key
   ```
4. Start the backend. All existing data remains in the file backend until
   manually migrated.

### Data migration (file → Supabase)

No automatic migration tool is provided. To migrate existing state:

1. Start with both backends available.
2. Export decisions: `cat workspace/state/decisions.json | jq '.[]'`
3. Import to Supabase via the API or SQL.
4. Repeat for `workspace/state/recommendations/*.json` and
   `workspace/state/action-queue/*.json`.

### Row-level security

The Supabase schema has RLS disabled by default. The cockpit's API key
middleware is the auth boundary. Before any public or multi-tenant deployment,
enable RLS and add policies (commented lines in `db/migrations/001_initial.sql`).

---

## User Identity

The cockpit resolves the API key to a user name via `config/users.json`.

```json
{ "your-api-key-here": "adam" }
```

Copy `config/users.json.example` to `config/users.json` and add entries.
A key not listed in `users.json` resolves to `"adam"` (single-user default).
Unauthenticated local access resolves to `"local"`.

The `created_by` field appears on all decisions, recommendations, and actions.
The UAOS handoff envelope includes `created_by` so the consuming agent can
filter by who made a decision.

---

## Organisation Settings

```
GET /settings/org
```

Returns the active graph, Ollama endpoint, storage backend, and a list of the
last-seen user identities with timestamps (populated by `GET /decisions` and
other polling calls). Useful for a UAOS agent to confirm the cockpit is reachable
and to check which devices have recently been active.

---

## Stop Conditions

The handoff endpoint is **read-only**. The cockpit never:

- executes actions on behalf of a UAOS agent;
- grants write access to workspace files through the handoff endpoint;
- initiates outbound connections to UAOS.

UAOS pulls from the cockpit; the cockpit never pushes to UAOS.

Before proposing a mission from a handoff record, the UAOS agent must stop for
Adam approval if any of the `uaos_mission_hint.stop_triggers` would be
crossed — even if all other validation checks pass.
