# Domain Language

Document type: shared vocabulary
Audience: project owner, builders, AI coding agents, reviewers, and operators
Purpose: define the terms used consistently across code, docs, tests, UI, prompts, runbooks, and release notes.

## Purpose

This file defines the shared vocabulary for the project.

Domain terms are named consistently across labels, API routes, state file schemas, React components, backend models, docs, and prompts.

When a term changes, update this file and the affected code or documentation in the same chunk where practical.

## Terms

| Term | Meaning | Avoid Saying | Code/Docs Usage |
|------|---------|--------------|-----------------|
| **Graph** | The `graph.json` produced by Graphify — a semantic representation of a workspace as nodes and edges | "index", "database", "knowledge base" when meaning the graph | `GRAPH_PATH`, `graph_summary()`, `/graph/summary`, Graph View |
| **Node** | A single entity in the graph (file, function, concept, document) with a type, label, and optional metadata | "vertex", "item", "entity" | Cytoscape.js node, `node.id`, `nodes_used` chip |
| **Edge** | A directed relationship between two nodes (depends_on, references, belongs_to, etc.) | "link", "connection", "line" | Cytoscape.js edge, edge count in Settings |
| **Cluster** | A named group of thematically related nodes, produced by Graphify community detection | "tag", "category", "folder" | `cluster-selection.json`, cluster toggle in Settings |
| **Source** | A named origin of graph content — a local workspace path or a cloud knowledge base (SharePoint, OneNote) | "provider", "connector", "feed" | Source toggle in Settings, source chip in Map |
| **Active Cluster Selection** | The user-configured set of sources and clusters whose nodes are included in Ask, Chat, and Recommendation context | "filter", "scope", "active graph" | `cluster-selection.json`, `GET/PUT /cluster-selection` |
| **Decision** | A durable human classification of a workspace area: invest, finish, merge, archive, extract, or ignore | "choice", "verdict", "label" | `decisions.json`, `POST /decisions`, Decisions tab |
| **Classification** | The specific value of a Decision (invest / finish / merge / archive / extract / ignore) | "status", "category", "type" | `classification` field in decision record |
| **Recommendation** | A model-backed proposal card with evidence, confidence, risk, and a proposed action | "suggestion", "hint", "alert" | `recommendations/`, `POST /recommendations`, Recommendations tab |
| **Action** | An approved, dry-run-verified operation queued for execution in the workspace | "task", "job", "command" | `action-queue/`, `POST /actions`, Work Queue tab |
| **Dry Run** | A preview of what an action would do without executing it — required before all actions | "preview", "simulate", "check" | `GET /actions/{id}/dry-run`, dry-run gate |
| **Work Queue** | The UI view of pending, approved, and executed actions | "task list", "action log" | Work Queue tab, `action-queue/` state dir |
| **Mission** | A bounded background analysis run that produces recommendation cards (not user-visible actions) | "job", "task", "background process" | `missions/`, `POST /missions`, Work Queue sub-panel |
| **Session** | A single Ask Q&A interaction — question + answer + evidence — saved to disk | "conversation", "query", "history" | `workspace/state/sessions/`, `session_id` |
| **Chat Session** | A single AI assistant interaction record saved to disk (metadata only, not full message history) | "conversation log", "chat history" | `workspace/state/chat-sessions/` |
| **AI Assistant** | The floating in-cockpit chat panel backed by Ollama; uses cluster-filtered graph context | "copilot", "chatbot", "LLM UI" | `AICopilot.tsx`, `POST /chat`, "AI" button |
| **Evidence** | The graph nodes that support a recommendation or answer, shown as linked references | "sources", "citations", "context" | `evidence` field in recommendation record, evidence node list in Ask |
| **Nodes Used** | The count of graph nodes included in the system context for a Chat or Ask response | "context size", "tokens used" | "X nodes used" chip on assistant messages |
| **Graph Context** | The formatted text prepended to an Ollama prompt containing relevant graph nodes | "context", "system prompt context" | `_build_graph_context()`, `sys_content` in `/chat` |
| **Demo Mode** | The state when the cockpit is running against the bundled demo graph rather than a real workspace graph | "sample mode", "test mode" | `demo_mode` in `/health`, dismissible banner |
| **Workspace State** | The `workspace/state/` directory where all persistent app state lives | "database", "data folder" | `WORKSPACE_STATE`, `STATE_DIR` env var |

## Naming Guidance

Use domain-specific names. A name should explain the responsibility it owns.

Challenge vague names when they hide unclear responsibility:

- `manager`, `helper`, `utils`, `thing`, `stuff`, `data`, `processor`, `handler`, `misc`, `temp`, `common`, `general`

Prefer names that point to the actual domain concept, boundary, or behavior.

## Agent Guidance

When terminology is vague or inconsistent, the agent should:

1. Flag the naming issue.
2. Explain the risk to comprehension, tests, prompts, or future changes.
3. Recommend the smallest safe naming improvement.
4. Keep related code, docs, tests, UI, and prompts aligned when the owner accepts the change.

Do not rename broadly just for style. Improve names when the change fits the active chunk or the owner approves the refactor.
