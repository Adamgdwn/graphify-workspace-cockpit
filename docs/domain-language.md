# Domain Language

Document type: shared vocabulary
Audience: project owner, builders, AI coding agents, reviewers, and operators
Purpose: define the terms used consistently across code, docs, tests, UI, prompts, runbooks, and release notes.

## Purpose

This file defines the shared vocabulary for the project.

Important domain terms should be named consistently across labels, database tables, functions, services, tests, docs, prompts, and runbooks.

When a term changes, update this file and the affected code or documentation in the same chunk where practical.

## Terms

| Term | Meaning | Avoid Saying | Code/Docs Usage |
|---|---|---|---|
| Example Term | Clear definition | Vague synonym | Where and how this term appears. |

## Naming Guidance

Use domain-specific names. A name should explain the responsibility it owns.

Challenge vague names when they hide unclear responsibility:

- `manager`
- `helper`
- `utils`
- `thing`
- `stuff`
- `data`
- `processor`
- `handler`
- `misc`
- `temp`
- `common`
- `general`

Prefer names that point to the actual domain concept, boundary, or behavior.

## Agent Guidance

When terminology is vague or inconsistent, the agent should:

1. Flag the naming issue.
2. Explain the risk to comprehension, tests, prompts, or future changes.
3. Recommend the smallest safe naming improvement.
4. Keep related code, docs, tests, UI, and prompts aligned when the owner accepts the change.

Do not rename broadly just for style. Improve names when the change fits the active chunk or the owner approves the refactor.
