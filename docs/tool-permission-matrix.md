# Tool Permission Matrix

Document ID: TPM-001
Status: draft
Last Updated: 2026-06-14

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
| Shell / file mutation | Execute approved workspace actions | Dry-run preview; explicit approved execution only | Any destructive action without dry-run and human approval | Yes — dry-run first, then explicit user approval for each action | Disabled for MVP; enabled in Chunk Eight with additional controls |
| GitHub operations | Interact with GitHub repos | None in MVP | All GitHub operations | Disabled for MVP | Enable in Chunk Nine after explicit governance decision |
| External HTTP | Any non-local HTTP call | None in MVP | All external calls except configured local Ollama | Disabled for MVP | Cockpit is local-first; external hooks are post-MVP |
