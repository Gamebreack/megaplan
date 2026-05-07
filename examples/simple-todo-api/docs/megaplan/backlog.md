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
|----|-------|-------|--------|----------|-------|-----------|--------|
| 0-B1 | Project scaffold | 0-P1 | done | P0 | team | — | [0-B1](backlog-items/0-B1.md) |
| 0-B2 | Database schema | 0-P1 | done | P0 | team | 0-B1 | [0-B2](backlog-items/0-B2.md) |
| 0-B3 | In-memory storage prototype | 0-P1 | superseded | P2 | team | 0-B1 | [0-B3](backlog-items/0-B3.md) |
| A-B1 | Todo CRUD | A-P1 | in-progress | P0 | team | 0-B2 | [A-B1](backlog-items/A-B1.md) |
| A-B2 | List todos | A-P1 | ready | P1 | team | A-B1 | [A-B2](backlog-items/A-B2.md) |
| A-B3 | User accounts | A-P1 | blocked | P1 | team | A-B1 | [A-B3](backlog-items/A-B3.md) |