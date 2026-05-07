<!-- megaplan v1.0.0 -->
# Megaplan — Methodology Reference

Full reference for the Megaplan plan-tracking system. See `AGENTS.md` for the condensed agent-facing version and `README.md` for the quick start.

---

## What it is

Megaplan is a **plan-tracking system** designed to give an AI agent the full context it needs to deliver software incrementally, safely, and traceably — without losing coherence across sessions.

It combines three things:
1. **A roadmap** — Cycles (major milestones) broken into Phases (focused work streams)
2. **A backlog** — Every deliverable as a detail file with scope, tests, acceptance criteria, and traceability
3. **A workflow** — A mandatory sequence: document → red → green → blue → document → complete

### Why it works for AI agents

An AI session starts with zero memory. Megaplan fixes that by encoding *what was decided*, *why it was decided*, and *what still needs to happen* into files the agent reads at the start of each task. The agent never has to infer history from git blame or oral tradition.

---

## Directory layout

```
docs/megaplan/
├── megaplan.md              # from templates/megaplan.md — product vision, cycle index
├── backlog.md               # from templates/backlog.md — global backlog index
├── backlog-items/           # one file per B-item, from templates/backlog-item.md
│   ├── A-B1.md
│   └── ...
├── phases/                  # one file per phase, from templates/phase.md
│   └── A-P1.md
└── cycles/                  # optional scoping docs for longer cycles
    └── cycle-b.md
```

---

## Core concepts

### Cycle

A **Cycle** is a major delivery milestone. Typically:
- **Cycle 0** — Project scaffold, CI, data model, tooling
- **Cycle A** — First production-ready domain (e.g., entity CRUD + auth)
- **Cycle B** — Second domain or integration on top of Cycle A
- **Cycle C+** — Subsequent expansions, dashboards, integrations

Cycles gate each other: Cycle B never starts until Cycle A exit criteria are met.

### Phase

A **Phase** is a focused work stream within a cycle. Phases are sequenced: later phases depend on earlier ones completing first.

Each phase has a **Phase document** (`phases/<CYCLE>-P<N>.md`) tracking the workflow checklist.

Name phases after their business outcome, not their technical method:
- `A-P1: Schema and migrations` not `A-P1: Database setup`
- `B-P2: Contract CRUD` not `B-P2: Backend routes`

### Backlog item (B-item)

A **Backlog item** is a single deliverable. It maps to one phase (usually), has an ID (`<CYCLE>-B<N>`), and lives in its own file under `backlog-items/`.

A B-item is the unit of work the agent picks up and delivers. Each one contains:
- Business outcome (one sentence — who benefits)
- Scope (bullet list — what's in, what's not)
- Dependencies and blockers
- Test plan (which files, which levels)
- Acceptance criteria (done checklist)
- Traceability (links to phase, ADRs, related items)

---

## The workflow (mandatory, no exceptions)

Every B-item moves through exactly these steps:

```
document (pre) → red → green → blue → document (post) → COMPLETE
```

| Step | What happens |
|---|---|
| **document (pre)** | Write/update all relevant docs (ADRs, architecture, phase file). No code until intent is documented. |
| **red** | Write failing tests that describe the desired behavior. Run the test suite — it must fail. |
| **green** | Write the minimum production code to pass all tests. Nothing extra. Run tests — they must pass. |
| **blue** | Refactor without adding features or breaking tests. Run tests — must still pass. |
| **document (post)** | Update all docs to reflect exactly what was built (not what was planned). |
| **COMPLETE** | Mark done in both `backlog.md` (index row) and the item detail file. Do both in the same commit. |

**This sequence is non-negotiable.** The agent should refuse to write production code without a failing test, and refuse to close an item without updating both status locations.

---

## Backlog status vocabulary

| Status | Meaning |
|---|---|
| `pending` | Defined, not started, no blocker identified |
| `ready` | Defined, unblocked, ready to pick up |
| `in-progress` | Actively being worked on |
| `blocked` | Hard dependency unresolved |
| `external` | Owned by another team; waiting on their delivery |
| `done` | Delivered; code and docs in place |
| `superseded` | Was delivered but later replaced; kept for traceability |

**Every status transition must update both the index row in `backlog.md` and the detail file in the same commit.** Drift between the two is a documentation bug.

---

## Priority levels

| Level | Meaning |
|---|---|
| P0 | Critical; blocks other phases or is the core deliverable of the cycle |
| P1 | High; important stakeholder value |
| P2 | Medium; hardening or polish |
| P3 | Low; deferred until resources allow |

---

## File templates

The `templates/` directory contains ready-to-copy starter files for each document type:

| Template | Copy to |
|----------|---------|
| `templates/megaplan.md` | `docs/megaplan/megaplan.md` |
| `templates/backlog.md` | `docs/megaplan/backlog.md` |
| `templates/backlog-item.md` | `docs/megaplan/backlog-items/<ID>.md` |
| `templates/phase.md` | `docs/megaplan/phases/<CYCLE>-P<N>.md` |

For a worked example showing all four templates filled in across two cycles, see [`examples/simple-todo-api/`](../examples/simple-todo-api/).

---

## Canonical patterns (carry forward per domain)

When a cycle establishes a reusable pattern, document it as canonical. Subsequent cycles reference it rather than reinventing it. Typical patterns to document:

- **CRUD + audit**: data layer → action/handler → UI → audit log write
- **Soft-delete + hard-delete**: `deleted_at` column; hard-delete gated by confirmation step
- **Authorization**: guard pattern at the action or route layer
- **Pagination**: cursor vs. offset, page size conventions
- **Error boundaries**: where validation happens, what errors surface to the caller

Document the canonical pattern in the phase that establishes it. Reference it in subsequent phases.

---

## Anti-patterns to avoid

| Anti-pattern | Why it breaks the system |
|---|---|
| Writing code before a failing test | No red means no confidence the test is testing anything |
| Updating `backlog.md` without the detail file (or vice versa) | Index and detail go out of sync; agent gets stale context |
| Closing an item without updating docs | Next agent session has accurate code but stale documentation |
| Skipping the `document (pre)` step | Agent writes code first and retrofits docs, which drift from reality |
| Creating a B-item without a detail file | Agent has no scope, test plan, or acceptance criteria to work from |
| Using `superseded` to hide decisions | Always keep superseded items — they explain why things changed |
| Speculating future scope into the backlog | Adds noise; scope cycles when they start, not earlier |