<!-- megaplan v2.0.0 -->
# Megaplan

A plan-tracking system for long-running software projects managed by AI coding agents.

## What this is

Megaplan provides a roadmap, backlog, and workflow that let an AI agent deliver software
incrementally, safely, and traceably — without losing coherence across sessions.

It combines three things:
1. **A roadmap** — Cycles (major milestones) each containing sequenced B-items
2. **A backlog** — Every B-item as a detail file with scope, tests, acceptance criteria
3. **A workflow** — Mandatory sequence: document → red → green → blue → document → COMPLETE

## Loading this skill

Place `AGENTS.md` at your project root. Most modern AI coding harnesses load it automatically.

## How it works

Three behaviors, in order:

1. **Discover** — Grill the user about the project. Resolve every domain term into `glossary.md`
   before writing anything else.
2. **Document** — Build the Megaplan structure: vision, cycles, glossary, ADRs, B-items.
3. **Implement** — Execute B-items one at a time via the workflow below.

See `docs/methodology.md` for the full lifecycle.

## Core concepts

### Cycle

A **Cycle** is a major delivery milestone. Typically:
- **Cycle 0** — Project scaffold, CI, data model, tooling
- **Cycle A** — First production-ready domain (e.g., entity CRUD + auth)
- **Cycle B** — Second domain or integration

Cycles gate each other: Cycle B never starts until Cycle A exit criteria are met.
B-items within a cycle are sequenced by dependency (B1 before B2 before B3).

### Backlog item (B-item)

A **B-item** is a single, atomic deliverable with its own file.
One focused behavior per item — an agent should finish it in one session. Each contains:
- Business outcome (one sentence)
- Scope (bullet list)
- Dependencies and blockers
- Test plan
- Acceptance criteria (done checklist)

**Granularity rule:** Decompose until the item answers "what single behavior does this deliver?"
- **Not:** "CRUD for products table" — mixes create, read, update, delete
- **Yes:** "Insert logic for products table"
- **Yes:** "List endpoint for products"

**Task decomposition:** Inside a B-item, tasks should be ~2–5 minutes of work each.
Small enough to avoid hallucination, large enough to be meaningful.

## Workflow (no exceptions)

Every B-item moves through exactly this sequence:

```
document (pre) → red → green → blue → document (post) → COMPLETE
```

| Step | What happens |
|------|--------------|
| **document (pre)** | Write/update docs (glossary, ADRs). No code until intent is documented. |
| **red** | Write failing tests that describe desired behavior. Tests must fail. |
| **green** | Write minimum production code to pass all tests. Nothing extra. |
| **blue** | Refactor without adding features or breaking tests. |
| **document (post)** | Update all docs (including glossary) to reflect exactly what was built. |
| **COMPLETE** | Mark done in both `backlog.md` index and detail file. |

**Never write production code without a failing test.**
**Never close an item without updating both status locations.**

**The Red step is non-negotiable.** No `green:` commit without a prior `red:` commit
in the same branch. This is the first step to slip — both audits confirmed it.

## Status vocabulary

| Status | Meaning |
|--------|---------|
| `pending` | Defined, not started |
| `in-progress` | Actively being worked on |
| `done` | Delivered; code and docs in place |
| `superseded` | Was delivered but later replaced |

**Drift:** When an item is `done` but has known issues (e.g., "cron name doesn't match
the migration"), document the drift in the item's Notes section. Don't leave it
`in-progress` — mark it `done` and list the drift explicitly.

**Every status transition updates both `backlog.md` AND the detail file in the same commit.**

## Bugs

Bug fixes spawned from completed B-items use the convention `<CYCLE>-B<N>.B<M>`:
- `<N>` = parent B-item number
- `<M>` = sequential bug number within that item
- Example: first bug found in A-B2 → `A-B2.B1`

Track bugs inline under the parent B-item. Include: severity, file, symptom, cause, fix,
verification, status. For substantial bugs, create a separate B-item.

## Directory structure

```
docs/megaplan/
├── megaplan.md              # Vision, cycle index, B-item table per cycle
├── backlog.md               # Global B-item index
├── glossary.md              # Canonical domain glossary
├── backlog-items/           # One file per B-item
└── adr/                     # Architecture Decision Records
```

## Templates

Copy these into `docs/megaplan/` in your project:
- `templates/megaplan.md` → `docs/megaplan/megaplan.md` (project root plan)
- `templates/backlog.md` → `docs/megaplan/backlog.md` (backlog index)
- `templates/glossary.md` → `docs/megaplan/glossary.md` (canonical domain glossary)
- `templates/backlog-item.md` → `docs/megaplan/backlog-items/<ID>.md` (one per B-item)

## Reference

- `docs/methodology.md` — Full methodology reference

## Anti-patterns

| Anti-pattern | Why it breaks the system |
|--------------|--------------------------|
| Writing code before a failing test | No red means no confidence the test is testing anything |
| Updating `backlog.md` without the detail file | Index and detail go out of sync |
| Skipping the `document (pre)` step | Agent writes code first, docs drift from reality |
| Creating a B-item without a detail file | Agent has no scope, test plan, or acceptance criteria |
| B-item is too large (e.g., "CRUD for 8 tables") | Agent loses focus; split into atomic items |
| Marking `done` without documenting known drift | Use the drift convention — don't pretend it's perfect |
| Deploying without AGENTS.md at project root | Methodology has no teeth across sessions |

## Quick reference

```
Workflow: document (pre) → red → green → blue → document (post) → COMPLETE
Status: pending | in-progress | done | superseded
Bugs: <CYCLE>-B<N>.B<M> (parent B-item N, sequential bug M)
```

Before starting any B-item:
1. Read `docs/megaplan/backlog-items/<ID>.md` — create from template if missing
2. Read `docs/megaplan/glossary.md` — use project terminology, not your own
3. Check all dependencies are `done`
4. Follow the workflow — Red before Green, always

---

## K.I.S.S. Mode — Anti-bloat principles

### Limits (evidence-backed)
- AGENTS.md: target 150 lines, max 200 lines
- Any template: max 80 lines

### Simplify-first principle
- Default to omission, not addition
- If you can't explain it in 3 sentences, it doesn't belong here
- Link external docs instead of embedding

### Lifecycle rules
- Stale content: mark as "archived" in filename — never delete (preserves traceability)
- Review cadence: monthly — check for contradictions, not usage

### Anti-bloat checklist (before committing)
- [ ] Does this add a new rule?
- [ ] Could this be a link instead of embedded content?
- [ ] Would a new agent understand this in under 30 seconds?
- [ ] Does this increase line count? If yes, what am I removing to compensate?
