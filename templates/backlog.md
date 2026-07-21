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
- New items are created from `docs/megaplan/backlog-items/_template.md` before any code is written.
- Never create a B-item without a detail file.

## Index

<!-- Replace this row with your first B-item -->
| ID | Title | Status | Owner | Depends on | Detail |
|----|-------|--------|-------|------------|--------|
