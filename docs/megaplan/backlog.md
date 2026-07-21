# Backlog

## Status vocabulary

| Status | Meaning |
|--------|---------|
| `pending` | Defined, not started |
| `in-progress` | Actively being worked on |
| `done` | Delivered; code and docs in place |
| `superseded` | Was delivered but later replaced; kept for traceability |

**Drift:** When an item is `done` but has known issues, document the drift in the item's
Notes section. Don't leave it `in-progress` — mark it `done` and list the drift explicitly.

## Rules

- Every status transition updates both this file and the detail file in the same commit.
- New items are created from `templates/backlog-item.md` before any code is written.
- Never create a B-item without a detail file.

## Index

| ID | Title | Status | Owner | Depends on | Detail |
|----|-------|--------|-------|------------|--------|
| 0-B1 | `suggest_pages` helper for wiki ingestion | done | — | — | [0-B1](backlog-items/0-B1.md) |
| 0-B2 | Drop `_meta/ingestion.log` writes | done | — | — | [0-B2](backlog-items/0-B2.md) |
| 0-B3 | Per-cycle waiver + freshness advisories | pending | — | — | [0-B3](backlog-items/0-B3.md) |
| 0-B4 | `verify_workflow.py` non-blocking wiki reminder | pending | — | — | [0-B4](backlog-items/0-B4.md) |
