# Manual

## What This Project Is

Describe the project in operator-friendly terms.

## How To Work In This Repo

For ordinary scoped work, start lean:

1. Check `git status --short`.
2. Read `START_HERE.md` and the short repo-local agent instructions.
3. Use `docs/context-map.md` to choose only the docs and source areas needed for the task.
4. Review `docs/current-build-pathway.md` for the active chunk, completion target, stop condition, and validation expectations.
5. Run task-relevant validation.

For material or risk-triggering work, add the full governance path:

1. Review `docs/standards/README.md`.
2. Review `docs/standards/engineering-governance-by-use-case.md`.
3. Review `docs/policy/durable-development-engineering-policy.md`.
4. Review `docs/standards/ship-ready-engineering-standard.md`.
5. Run `bash scripts/governance-preflight.sh`.
6. Review `project-control.yaml`.
7. Capture a timestamp with `date -Iseconds`.
8. Confirm the current roadmap and runbook still match reality.
9. Update docs when behavior or operating expectations change.

## Expected Outputs

- working code or deliverables
- current operational documentation
- a maintained roadmap
- timestamped build pathway updates for material work
- scoped context and budget notes for meaningful chunks
- reviewable governance records

## Operator Notes

Capture practical operating tips, common gotchas, and handoff guidance.
