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

## Workflow

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
| **document (post)** | Update all docs; ingest the AI wiki if `docs/megaplan/wiki/` exists. |
| **COMPLETE** | Mark done in both `backlog.md` index and detail file. |

**The Red step is the default standard for TDD-verified items.**

### Security & Exceptions

* **Sandbox Rule:** All execution/verification/test commands MUST run inside an isolated sandbox environment to prevent host system damage.
* **Configuration/Scaffolding Exception:** Items specifying `Verification: manual` or `Verification: CI` in their metadata can bypass the strict Red/Green workflow in favor of execution validation (running logs/verification commands to confirm success).

## Status vocabulary

| Status | Meaning |
|--------|---------|
| `pending` | Defined, not started |
| `in-progress` | Actively being worked on |
| `done` | Delivered; code and docs in place |
| `superseded` | Was delivered but later replaced |

*Note: Projects can extend this vocabulary with additional statuses if needed (e.g. `ready`, `blocked`, `external`).*

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

## Verification gates (mandatory)

Before advancing a workflow step, run the gate script:
  `python scripts/verify_workflow.py check <b_item_path> [--run-verifier]`

| Gate | Transition | Checks |
|------|------------|--------|
| Layer 1 | doc → red | SPEC.md compiled and current (`compile_spec.py`) |
| Layer 1 | red → green | Test plan populated in B-item |
| Layer 2 | green → blue | Tests pass (`--run-verifier`) |
| Layer 2 | blue → doc | Tests + lint pass (`--run-verifier`) |
| Layer 3 | doc → COMPLETE | Backlog + glossary dual-updated; AI wiki ingested (opt-in, if `wiki/` exists) |

Install pre-commit hooks: `python scripts/setup_hooks.py`
See `references/methodology.md` for the full 3-Layer reference. The AI wiki
(`docs/megaplan/wiki/`) is AI-targeted, derived/disposable context — source docs
win on conflict; waive per-item with `Wiki-Impact: none`.

## Anti-patterns

| Anti-pattern | Why it breaks |
|--------------|---------------|
| Skipping a gate | No confidence the step was actually done |
| Writing code before a failing test | No red means the test may not test anything |
| Updating `backlog.md` without the detail file | Index and detail go out of sync |
| B-item is too large (e.g., "CRUD for 8 tables") | Agent loses focus |
| Marking `done` without documenting known drift | Pretending it's perfect |
| Missing A.G.E.N.T.S..md at project root | Methodology has no teeth across sessions |

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

## Reference

Detailed methodology: [references/methodology.md](references/methodology.md)
Templates for bootstrapping new projects: [templates/](templates/)

## Quick reference

* Status: `pending` | `in-progress` | `done` | `superseded`
* Bugs: `<CYCLE>-B<N>.B<M>` (parent B-item N, sequential bug M)
* Startup checks:
  1. Compile to `SPEC.md` (`python scripts/compile_spec.py <path_to_b_item>`)
  2. Read source B-item, `docs/megaplan/glossary.md`, and the AI wiki if present (`docs/megaplan/wiki/INDEX.md`)
  3. Ensure dependencies are `done`
  4. Follow workflow (Red before Green unless Exception applies)
  5. Run `verify_workflow.py check <b_item_path>` before advancing each step


<!-- megaplan v2.0.0 -->
