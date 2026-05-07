# Backlog

## Status vocabulary

| Status | Meaning |
|--------|---------|
| `pending` | Defined, not started, no blocker identified |
| `ready` | Defined, unblocked, ready to pick up |
| `in-progress` | Actively being worked on |
| `blocked` | Hard dependency unresolved |
| `external` | Owned by another team; waiting on their delivery |
| `done` | Delivered; code and docs in place |
| `superseded` | Was delivered but later replaced; kept for traceability |

## Rules

- Every status transition updates both this file and the detail file in the same commit.
- New items are created from `templates/backlog-item.md` before any code is written.
- Never create a B-item without a detail file.

## Index

| ID | Title | Phase | Status | Priority | Owner | Depends on | Detail |
|----|-------|-------|--------|----------|-------|------------|--------|
| 0-B1 | Example item | 0-P1 | pending | P0 | — | — | [0-B1](backlog-items/0-B1.md) |