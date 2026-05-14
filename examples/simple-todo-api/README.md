# Simple Todo API — Megaplan example

A worked example of Megaplan applied to a small Todo CRUD API. Two cycles:

- **Cycle 0**: scaffold + database schema (`0-B1`, `0-B2`)
- **Cycle A**: CRUD endpoints (`A-B1`, `A-B2`, `A-B3`)

Plus an early prototype kept for traceability: `0-B3` (superseded).

## Layout

```
docs/megaplan/
├── megaplan.md             # cycle overview
├── backlog.md              # status index across all items
├── adr/
│   └── ADR-001.md          # ORM choice (Prisma)
└── backlog-items/          # one file per backlog item
```

## Statuses demonstrated

| Status | Where to see it |
|---|---|
| `done` | `0-B1`, `0-B2` |
| `in-progress` | `A-B1` |
| `ready` | `A-B2` |
| `blocked` | `A-B3` |
| `superseded` | `0-B3` |
| `pending` | not shown — same shape as `ready` minus the "unblocked" confirmation |

The full status vocabulary is defined in [`docs/methodology.md`](../../docs/methodology.md) (and mirrored in [`docs/megaplan/backlog.md`](docs/megaplan/backlog.md)).
