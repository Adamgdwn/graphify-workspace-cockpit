# Tool Permission Matrix

Document ID: TPM-001
Status: current
Last Updated: 2026-06-15

Applies to all backend tools and agent actions in this cockpit.

| Tool | Purpose | Allowed Actions | Prohibited Actions | Approval Required | Notes |
| --- | --- | --- | --- | --- | --- |
| Read graph.json | Load workspace graph for queries and map rendering | Read user-selected local graph.json | Read any file not explicitly selected by user | No | User selects path at startup or in settings |
| Graphify CLI | Run query, path, explain against loaded graph | `graphify query`, `graphify path`, `graphify explain` | `graphify update`, `graphify init`, any mutation subcommand | No | Subprocess only; no shell expansion from user input |
| Read workspace files | Load file content for Ask context | Read files within user-selected roots | Read secrets, .env files, or files outside selected roots | No for reads within selected roots | Selected roots configured in settings; .env and secrets excluded at all times |
| Write decision state | Persist decision records | Write to `workspace/state/decisions.json` | Write outside `workspace/state/` | No | App-internal state only |
| Write recommendation state | Persist recommendation cards | Write to `workspace/state/recommendations/` | Write outside `workspace/state/` | No | Cards are proposals only; no action is triggered by writing them |
| Write action queue | Persist action records | Write to `workspace/state/action-queue/` | Write outside `workspace/state/` | Yes (action created only from an explicitly accepted recommendation) | Action records are proposals until approved |
| Ollama API | Local model inference | POST to configured local Ollama endpoint | Call any external URL; send secrets or env content | No (local only) | Defaults to localhost; endpoint is user-configurable |
| Shell / file mutation | Execute approved workspace actions | Dry-run preview; explicit approved execution only | Any destructive action without dry-run and human approval | Yes — dry-run first, then explicit user approval for each action | Enabled only through the Chunk Eight dry-run and approval gate |
| Supabase API | Cross-device shared state | Read/write decisions, recommendations, actions to Supabase tables when `STORAGE_BACKEND=supabase` | Send secrets, env values, or raw graph content | No (opt-in only; disabled when `STORAGE_BACKEND=file`) | Enabled in Chunk 11; requires `SUPABASE_URL` and `SUPABASE_KEY` env vars |
| Microsoft OAuth / Graph API | Cloud knowledge base connectors (SharePoint + OneNote) | MSAL device code auth; read site/notebook content for graph sync | Write to Microsoft services; access any Microsoft resource beyond the configured site/notebook | No (user initiates sync via Settings) | Enabled in Chunk 14; requires `MS_CLIENT_ID`, `MS_TENANT_ID` env vars |
| GitHub operations | Interact with GitHub repos | None | All GitHub operations | Not implemented — no current use case | Add via explicit ADR if a future chunk needs it |
| Arbitrary external HTTP | Any non-local, non-configured HTTP call | None | All unconfigured external HTTP calls | Prohibited | Cockpit is local-first; all external integrations are explicitly enumerated above |
