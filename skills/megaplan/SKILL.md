---
name: megaplan
description: Plan-tracking system for long-running software projects. Use when starting a new coding project, scoping work, or picking up a software development task — provides Cycles, atomic B-items, red-green-blue workflow, glossary discipline, bug tracking convention, and documentation-first approach.
metadata:
  hermes:
    tags: [coding, planning, project-management, architecture]
    category: development
---

# Megaplan

A plan-tracking methodology that gives AI agents the roadmap, backlog, and workflow they need to deliver software incrementally, safely, and traceably — without losing coherence across sessions.

## When to use

Load this skill when:
- Starting a new software project and need to scope Cycles and B-items
- Picking up a B-item for implementation
- Writing or reviewing project documentation (glossary, ADRs)
- Tracking bugs spawned from completed B-items
- The user mentions planning, backlog, cycles, or B-items

## How it works

Three behaviors, in order:

1. **Discover** — Grill the user about the project. Resolve every domain term into `glossary.md` before writing anything else.
2. **Document** — Build the Megaplan structure: vision, cycles, B-items, glossary, ADRs.
3. **Implement** — Execute B-items one at a time via the mandatory workflow.

## Core concepts

### Cycle

A major delivery milestone. Cycle 0 scaffolds the project. Cycle A delivers the first domain. Cycles gate each other. B-items within a cycle are sequenced by dependency (B1 before B2 before B3).

### B-item

A single, atomic deliverable. One focused behavior per item. Decompose until each answers "what single behavior does this deliver?" Inside a B-item, tasks should be ~2–5 minutes each.

## Workflow (no exceptions)

Every B-item moves through exactly this sequence:

```
document (pre) → red → green → blue → document (post) → COMPLETE
```

| Step | What happens |
|------|--------------|
| **document (pre)** | Write/update docs (glossary, ADRs). No code until intent is documented. |
| **red** | Write failing tests. Run them — they must fail. |
| **green** | Write minimum production code to pass all tests. |
| **blue** | Refactor without adding features or breaking tests. |
| **document (post)** | Update all docs to reflect what was built. |
| **COMPLETE** | Mark done in both `backlog.md` index and detail file. |

**The Red step is non-negotiable.** No green commit without a prior red commit in the same branch.

## Status vocabulary

| Status | Meaning |
|--------|---------|
| `pending` | Defined, not started |
| `in-progress` | Actively being worked on |
| `done` | Delivered; code and docs in place |
| `superseded` | Was delivered but later replaced |

**Drift:** When `done` but with known issues, document the drift in Notes. Don't leave it `in-progress`.

Every status transition updates both `backlog.md` AND the detail file in the same commit.

## Bugs

Bug fixes use `<CYCLE>-B<N>.B<M>` convention. Track inline under the parent B-item with severity, file, symptom, cause, fix, verification, status.

## Directory structure

```
docs/megaplan/
├── megaplan.md
├── backlog.md
├── glossary.md
├── backlog-items/
└── adr/
```

## What to do

1. If no `docs/megaplan/` directory exists in the project, offer to bootstrap it using the templates.
2. Before writing any code, ensure `glossary.md` has resolved terms — challenge fuzzy language.
3. For each B-item, follow the workflow: document → red → green → blue → document → COMPLETE.
4. Update both `backlog.md` and the detail file on every status change.
5. Document drift in Notes rather than leaving items in limbo.

## Anti-patterns

| Anti-pattern | Why it breaks |
|--------------|---------------|
| Writing code before a failing test | No confidence the test tests anything |
| Updating `backlog.md` without the detail file | Index and detail go out of sync |
| Skipping the `document (pre)` step | Docs drift from reality |
| B-item is too large (e.g., "CRUD for 8 tables") | Agent loses focus |
| Marking `done` without documenting known drift | Pretending it's perfect |
| Missing AGENTS.md at project root | Methodology has no teeth across sessions |

## Reference

Detailed methodology: [references/methodology.md](references/methodology.md)
Templates for bootstrapping new projects: [templates/](templates/)
