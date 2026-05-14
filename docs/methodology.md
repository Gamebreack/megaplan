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

## Project lifecycle

Megaplan operates in three sequential behaviors from project start to delivery:

### 1. Discover

The agent interviews you about the project — what it does, who it serves, what the domain concepts are. Use the [Glossary review protocol](#glossary-review-protocol-grilling) to resolve every term into a precise definition before writing any documents or code. Output: a populated `glossary.md` and a clear mental model of what to build.

### 2. Document

Capture the understanding as a Megaplan structure:
- `megaplan.md` — project vision and cycle index
- `backlog.md` — backlog index with status tracking
- `backlog-items/<ID>.md` — one per B-item (see [B-item granularity](#backlog-item-b-item))
- `phases/<CYCLE>-P<N>.md` — phase workflow docs
- ADRs at `adr/ADR-NNN.md` — when warranted (see [ADR discipline](#adr-discipline))

Output: a complete, actionable backlog. No code until all three behaviors are done.

### 3. Implement

Pick up B-items one at a time, following `document (pre) → red → green → blue → document (post) → COMPLETE`. See [The workflow](#the-workflow-mandatory-no-exceptions) for the full sequence.

---

## Directory layout

```
docs/megaplan/
├── megaplan.md              # from templates/megaplan.md — product vision, cycle index
├── backlog.md               # from templates/backlog.md — global backlog index
├── glossary.md              # from templates/glossary.md — canonical domain glossary
├── backlog-items/           # one file per B-item, from templates/backlog-item.md
│   ├── A-B1.md
│   └── ...
├── phases/                  # one file per phase, from templates/phase.md
│   └── A-P1.md
├── adr/                     # architecture decision records
│   └── ADR-001.md
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

### B-item granularity

A B-item must be **atomic** — one focused behavior an agent can deliver in a single session with minimal hallucination risk.

**Not:**
- "CRUD for products table" — mixes create, read, update, delete into one item

**Yes:**
- "Insert logic for products table"
- "List endpoint for products"
- "Update logic for products table"
- "Delete logic for products table"

Decompose until each B-item answers: "what single behavior does this deliver?"

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

## Glossary and ADRs

### Glossary (mandatory)

Every Megaplan project maintains `docs/megaplan/glossary.md` — the canonical glossary of domain terms. It is the single source of truth for ubiquitous language across all Cycles, Phases, and B-items.

**Purpose:**
- Prevents terminology drift between Cycles — the same word means the same thing in Cycle B as it did in Cycle A
- Gives every agent session the same vocabulary — no guessing what "cancellation" means in this project
- Forces precision during planning — terms mean exactly one thing, no ambiguity

The glossary is created during Cycle 0's `document (pre)` step and updated inline whenever a term is resolved, redefined, or retired.

**Structure:** Each entry contains a term, its definition, a canonical usage example (from code or design), and a note on common confusions. See `templates/glossary.md`.

### Glossary review protocol ("grilling")

When scoping a new Cycle or B-item that introduces or uses a domain concept, apply this protocol:

1. **Challenge against the glossary** — When a term is used in a new B-item or phase, check `glossary.md`. If it conflicts with the established definition, call it out: "Your glossary defines 'cancellation' as X, but this B-item seems to mean Y — which is it?"

2. **Sharpen fuzzy language** — When vague or overloaded terms appear, propose a precise canonical term. "You say 'account' — do you mean Customer or User? Those are different things in this project."

3. **Cross-reference with code** — When a term's meaning is stated, check whether the code agrees. "The code cancels entire Orders, but this B-item says partial cancellation is possible — which is right?"

4. **Resolve one decision at a time** — Don't batch ambiguity. Ask one question, resolve it, update the glossary, then move to the next.

5. **Update glossary inline** — When a term is resolved, update `glossary.md` immediately. Don't defer or batch these changes.

### GLOSSARY-MAP.md (for multi-domain projects)

If the project spans multiple bounded contexts (e.g., separate `ordering/` and `billing/` domains), create `docs/megaplan/glossary-map.md` mapping each domain to its own glossary file. Each domain maintains its own terminology.

### ADR discipline

Create an ADR only when **all three** conditions are true:

1. **Hard to reverse** — the cost of changing this decision later is meaningful
2. **Surprising without context** — a future reader would wonder "why did they do it this way?"
3. **The result of a real trade-off** — genuine alternatives existed and one was chosen for specific reasons

If any condition is missing, skip the ADR. Store ADRs at `docs/megaplan/adr/ADR-NNN.md`.

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