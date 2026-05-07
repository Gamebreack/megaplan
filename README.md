# Megaplan

A plan-tracking skill for AI agent harnesses. Gives agents the roadmap, backlog, and workflow they need to deliver software incrementally — without losing coherence across sessions.

## Why it exists

AI agents start with zero memory each session. Megaplan fixes that by encoding *what was decided*, *why*, and *what still needs to happen* into files the agent reads at the start of every task.

## How it works

**Cycles → Phases → B-items.** A Cycle is a major milestone (Cycle 0 scaffolds the project; Cycle A delivers the first domain; and so on). Each cycle contains sequenced Phases. Each phase contains one or more Backlog items (B-items) — the atomic unit of work.

**The workflow is mandatory.** Every B-item follows: `document (pre) → red → green → blue → document (post) → COMPLETE`. No production code before a failing test. No closing an item without updating docs.

**Dual-update discipline.** Every status change updates both the global `backlog.md` index and the individual B-item detail file in the same commit. Drift between the two is a documentation bug.

See `docs/methodology.md` for the full reference.

## Quick start

**1. Copy `AGENTS.md` to your project root**

Most modern AI coding harnesses load `AGENTS.md` automatically.

**2. Create the directory structure**

```bash
mkdir -p docs/megaplan/backlog-items docs/megaplan/phases docs/megaplan/cycles
```

**3. Copy the templates and fill them in**

```bash
cp templates/megaplan.md      docs/megaplan/megaplan.md
cp templates/backlog.md       docs/megaplan/backlog.md
# Copy templates/backlog-item.md and templates/phase.md as you create each item/phase
```

Write your project vision in `megaplan.md`, scope Cycle 0, and start working through phases.

## File inventory

| File | Purpose |
|------|---------|
| `AGENTS.md` | The skill — copy this to your project root |
| `templates/megaplan.md` | Starter for your project root plan |
| `templates/backlog.md` | Starter for your backlog index |
| `templates/backlog-item.md` | Starter for each B-item detail file |
| `templates/phase.md` | Starter for each phase doc |
| `docs/methodology.md` | Full methodology reference |
| `examples/simple-todo-api/` | Complete example: Todo API with Cycle 0 (scaffold) and Cycle A (CRUD) |

---

v1.0.0
