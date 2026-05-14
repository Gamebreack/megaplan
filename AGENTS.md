<!-- megaplan v1.0.0 -->
# Megaplan

A plan-tracking system for long-running software projects managed by AI coding agents.

## What this is

Megaplan provides a roadmap, backlog, and workflow that let an AI agent deliver software incrementally, safely, and traceably — without losing coherence across sessions.

It combines three things:
1. **A roadmap** — Cycles (major milestones) broken into Phases (focused work streams)
2. **A backlog** — Every deliverable as a detail file with scope, tests, acceptance criteria
3. **A workflow** — Mandatory sequence: document → red → green → blue → document → COMPLETE

## Loading this skill

Place `AGENTS.md` at your project root. Most modern AI coding harnesses load it automatically.

## How it works

Three behaviors, in order:

1. **Discover** — Grill the user about the project. Resolve every domain term into `glossary.md` before writing anything else.
2. **Document** — Build the Megaplan structure: vision, cycles, phases, glossary, ADRs, B-items.
3. **Implement** — Execute B-items one at a time via the workflow below.

See `docs/methodology.md` for the full lifecycle.

## Core concepts

### Cycle

A **Cycle** is a major delivery milestone. Typically:
- **Cycle 0** — Project scaffold, CI, data model, tooling
- **Cycle A** — First production-ready domain (e.g., entity CRUD + auth)
- **Cycle B** — Second domain or integration

Cycles gate each other: Cycle B never starts until Cycle A exit criteria are met.

### Phase

A **Phase** is a focused work stream within a cycle. Phases are sequenced — later phases depend on earlier ones.

Name phases after their business outcome, not technical method:
- `A-P1: Schema and migrations` not `A-P1: Database setup`

### Backlog item (B-item)

A **B-item** is a single, atomic deliverable with its own file. One focused behavior per item — an agent should finish it in one session. Each one contains:
- Business outcome (one sentence)
- Scope (bullet list)
- Dependencies and blockers
- Test plan
- Acceptance criteria (done checklist)

## Workflow (no exceptions)

Every B-item moves through exactly this sequence:

```
document (pre) → red → green → blue → document (post) → COMPLETE
```

| Step | What happens |
|------|--------------|
| **document (pre)** | Write/update docs (glossary, ADRs, phase file). No code until intent is documented. |
| **red** | Write failing tests that describe desired behavior. Tests must fail. |
| **green** | Write minimum production code to pass all tests. Nothing extra. |
| **blue** | Refactor without adding features or breaking tests. |
| **document (post)** | Update all docs (including glossary) to reflect exactly what was built. |
| **COMPLETE** | Mark done in both `backlog.md` index and detail file. |

**Never write production code without a failing test.**
**Never close an item without updating both status locations.**

## Status vocabulary

Use only these values:

| Status | Meaning |
|--------|---------|
| `pending` | Defined, not started, no blocker identified |
| `ready` | Defined, unblocked, ready to pick up |
| `in-progress` | Actively being worked on |
| `blocked` | Hard dependency unresolved |
| `external` | Owned by another team; waiting on their delivery |
| `done` | Delivered; code and docs in place |
| `superseded` | Was delivered but later replaced |

**Every status transition updates both `backlog.md` AND the detail file in the same commit.**

## Priority levels

| Level | Meaning |
|-------|---------|
| P0 | Critical; blocks other phases or is the core deliverable |
| P1 | High; important stakeholder value |
| P2 | Medium; hardening or polish |
| P3 | Low; deferred until resources allow |

## Directory structure

```
docs/megaplan/
├── megaplan.md              # Product vision, cycle index, phase workflow
├── backlog.md              # Global backlog index
├── glossary.md             # Canonical domain glossary
├── backlog-items/          # Each deliverable in its own file
├── phases/                 # Phase workflow docs
├── adr/                    # Architecture Decision Records
└── cycles/                # Scoping docs (optional)
```

## Templates

Copy these into `docs/megaplan/` in your project:
- `templates/megaplan.md` → `docs/megaplan/megaplan.md` (project root plan)
- `templates/backlog.md` → `docs/megaplan/backlog.md` (backlog index)
- `templates/glossary.md` → `docs/megaplan/glossary.md` (canonical domain glossary)
- `templates/backlog-item.md` → `docs/megaplan/backlog-items/<ID>.md` (one per B-item)
- `templates/phase.md` → `docs/megaplan/phases/<CYCLE>-P<N>.md` (one per phase)

## Reference

- `docs/methodology.md` — Full methodology reference

## Anti-patterns (what NOT to do)

| Anti-pattern | Why it breaks the system |
|--------------|--------------------------|
| Writing code before a failing test | No red means no confidence the test is testing anything |
| Updating `backlog.md` without the detail file (or vice versa) | Index and detail go out of sync |
| Skipping the `document (pre)` step | Agent writes code first, docs drift from reality |
| Creating a B-item without a detail file | Agent has no scope, test plan, or acceptance criteria |
| Closing an item without updating docs | Next agent session has accurate code but stale docs |
| B-item is too large (e.g., "CRUD for 8 tables") | Agent loses focus; split into atomic items before starting |

## Quick reference

```
Phase workflow: document (pre) → red → green → blue → document (post) → COMPLETE
Status values: pending | ready | in-progress | blocked | external | done | superseded
Priority: P0 > P1 > P2 > P3
```

Before starting any B-item:
1. Read `docs/megaplan/backlog-items/<ID>.md` — create from `templates/backlog-item.md` if missing
2. Read `docs/megaplan/glossary.md` — use project terminology, not your own
3. Check all dependencies are `done`
4. Follow the phase workflow

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