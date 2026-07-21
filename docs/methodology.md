<!-- megaplan v2.0.0 -->
# Megaplan — Methodology Reference

Full reference for the Megaplan plan-tracking system. See `AGENTS.md` for the condensed agent-facing version and `README.md` for the quick start.

---

## What it is

Megaplan is a **plan-tracking system** designed to give an AI agent the full context it needs to deliver software incrementally, safely, and traceably — without losing coherence across sessions.

It combines three things:
1. **A roadmap** — Cycles (major milestones) broken into sequenced B-items
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
- `glossary.md` — canonical domain glossary
- ADRs at `adr/ADR-NNN.md` — when warranted (see [ADR discipline](#adr-discipline))

Output: a complete, actionable backlog. No code until all three behaviors are done.

### 3. Implement

Pick up B-items one at a time, following `document (pre) → red → green → blue → document (post) → COMPLETE`. See [The workflow](#the-workflow) for the full sequence.

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
B-items within a cycle are sequenced by dependency (B1 before B2 before B3).

### Backlog item (B-item)

A **Backlog item** is a single deliverable. It has an ID (`<CYCLE>-B<N>`) and lives in its own file under `backlog-items/`.

A B-item is the unit of work the agent picks up and delivers. Each one contains:
- Business outcome (one sentence — who benefits)
- Scope (bullet list — what's in, what's not)
- Dependencies and blockers
- Test plan (which files, which levels)
- Acceptance criteria (done checklist)
- Traceability (links to glossary, ADRs, related items)

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

**Task decomposition:** Inside a B-item, tasks should be ~2–5 minutes of work each. Small enough to avoid hallucination, large enough to be meaningful.

---

## The workflow

Every B-item moves through exactly these steps:

```
document (pre) → red → green → blue → document (post) → COMPLETE
```

| Step | What happens |
|---|---|
| **document (pre)** | Write/update all relevant docs (glossary, ADRs). No code until intent is documented. |
| **red** | Write failing tests that describe the desired behavior. Run the test suite — it must fail. |
| **green** | Write the minimum production code to pass all tests. Nothing extra. Run tests — they must pass. |
| **blue** | Refactor without adding features or breaking tests. Run tests — must still pass. |
| **document (post)** | Update all docs (including glossary) to reflect exactly what was built (not what was planned). |
| **COMPLETE** | Mark done in both `backlog.md` (index row) and the item detail file. Do both in the same commit. |

**This sequence is the default standard.** The agent should refuse to write production code without a failing test, and refuse to close an item without updating both status locations. Use a 'Workflow Step' field in the item's metadata table to declare the current step (e.g., red, green) during pauses or handovers.

**The Red step is the first to slip.** No `green:` commit without a prior `red:` commit in the same branch. The agent must verify: were failing tests written and confirmed failing before production code?

### Security & Exceptions
* **Sandbox Rule:** All execution/verification/test commands MUST run inside an isolated sandbox environment to prevent host system damage.
* **Configuration/Scaffolding Exception:** Items specifying `Verification: manual` or `Verification: CI` in their metadata can bypass the strict Red/Green workflow in favor of execution validation (running logs/verification commands to confirm success). For configuration/scaffolding exceptions where TDD is bypassed, manual validation steps, commands, and outputs must be documented in the item's 'Notes' section before completion.

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `pending` | Defined, not started |
| `in-progress` | Actively being worked on |
| `done` | Delivered; code and docs in place |
| `superseded` | Was delivered but later replaced; kept for traceability |

> [!NOTE]
> Projects can extend this core vocabulary with additional statuses if needed (e.g., `ready` for unblocked items ready to pick up, `blocked` for items waiting on dependencies, or `external` for external team dependencies), as demonstrated in the example project backlog.

**Drift:** When an item is `done` but has known issues (e.g., "cron name doesn't match the migration"), document the drift in the item's Notes section. Don't leave it `in-progress` — mark it `done` and list the drift explicitly.

**Every status transition must update both the index row in `backlog.md` and the detail file in the same commit.** Drift between the two is a documentation bug.

**Every status transition updates both `backlog.md` AND the detail file in the same commit.**

---

## Bugs

Bug fixes spawned from completed B-items use the convention `<CYCLE>-B<N>.B<M>`:
- `<N>` = parent B-item number
- `<M>` = sequential bug number within that item
- Example: first bug found in A-B2 → `A-B2.B1`

Track bugs inline under the parent B-item. Include: severity, file, symptom, cause, fix, verification, status. For substantial bugs, create a separate B-item.

Once a cycle is closed, any new bugs found must be tracked as new B-items in the active cycle (referencing the parent ID for pedigree) rather than reopening the original B-item (which violates cycle gating).

---

## File templates

The `templates/` directory contains ready-to-copy starter files for each document type:

| Template | Copy to |
|----------|---------|
| `templates/megaplan.md` | `docs/megaplan/megaplan.md` |
| `templates/backlog.md` | `docs/megaplan/backlog.md` |
| `templates/glossary.md` | `docs/megaplan/glossary.md` |
| `templates/backlog-item.md` | `docs/megaplan/backlog-items/<ID>.md` |

For a worked example showing all templates filled in across two cycles, see [`examples/simple-todo-api/`](../examples/simple-todo-api/).

---

## Canonical patterns (carry forward per domain)

When a cycle establishes a reusable pattern, document it as canonical. Subsequent cycles reference it rather than reinventing it. Typical patterns to document:

- **CRUD + audit**: data layer → action/handler → UI → audit log write
- **Soft-delete + hard-delete**: `deleted_at` column; hard-delete gated by confirmation step
- **Authorization**: guard pattern at the action or route layer
- **Pagination**: cursor vs. offset, page size conventions
- **Error boundaries**: where validation happens, what errors surface to the caller

Document the canonical pattern in the cycle that establishes it. Reference it in subsequent cycles.

---

## Glossary and ADRs

### Glossary (mandatory)

Every Megaplan project maintains `docs/megaplan/glossary.md` — the canonical glossary of domain terms. It is the single source of truth for ubiquitous language across all Cycles and B-items.

**Purpose:**
- Prevents terminology drift between Cycles — the same word means the same thing in Cycle B as it did in Cycle A
- Gives every agent session the same vocabulary — no guessing what "cancellation" means in this project
- Forces precision during planning — terms mean exactly one thing, no ambiguity

The glossary is created during Cycle 0's `document (pre)` step and updated inline whenever a term is resolved, redefined, or retired.

**Structure:** Each entry contains a term, its definition, a canonical usage example (from code or design), and a note on common confusions. See `templates/glossary.md`.

### Glossary review protocol ("grilling")

When scoping a new Cycle or B-item that introduces or uses a domain concept, apply this protocol:

1. **Challenge against the glossary** — When a term is used in a new B-item, check `glossary.md`. If it conflicts with the established definition, call it out: "Your glossary defines 'cancellation' as X, but this B-item seems to mean Y — which is it?"

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
| B-item is too large (e.g., "CRUD for 8 tables") | Agent loses focus; split into atomic items before starting |
| Marking `done` without documenting known drift | Use the drift convention — don't pretend it's perfect |
| Using `superseded` to hide decisions | Always keep superseded items — they explain why things changed |
| Speculating future scope into the backlog | Adds noise; scope cycles when they start, not earlier |
| Missing AGENTS.md at project root | Methodology has no teeth across sessions |
| Setting `Wiki-Impact: none` to skip a real architectural change | The escape hatch is for genuinely no-impact items; abusing it starves the AI wiki and defeats Layer 3 |
| Treating the AI wiki as a source of truth | It is derived/disposable — trusting stale wiki prose over code/source docs propagates confidently-wrong context |

---

## Agentic Integration (Karpathy's 3-Layer Method)

Megaplan integrates Karpathy's 3-Layer architecture for autonomous coding agents. These layers are enforced by the `verify_workflow.py` gate script.

### 1. Dynamic Spec Compilation (Layer 1)
Before an agent starts a task, compile the active B-item detail file into a concise `SPEC.md` at the project root using `scripts/compile_spec.py`. This limits the agent's context window, preventing context rot and keeping execution focused. The gate script verifies SPEC.md is compiled and current before transitioning from `document (pre)` to `red`.

### 2. Multi-Stage Verifier (Layer 2)
Multi-stage verification runs inside the execution sandbox:
- **Stage 1** — Functional tests (unit/integration). Enforced at `green → blue`.
- **Stage 2** — Static analysis (`mypy`, `eslint`, `cargo clippy`, etc.). Enforced at `blue → document (post)`.
- **Stage 3** — Documentation & glossary checks. Enforced at `document (post) → COMPLETE`.

Run with `python scripts/verify_workflow.py check <b_item> --run-verifier`.

### 3. Automated Ingestion Loop (Layer 3)
During the `document (post)` step, verify documentation artifacts and refresh the AI wiki:
- Backlog index and detail file are dual-updated
- Glossary reflects implemented changes
- Links between backlog items are valid
- The **AI wiki** is ingested (see below)

Enforced by the gate script at the `document (post) → COMPLETE` transition.

#### The AI Wiki (`docs/megaplan/wiki/`)

The wiki is **AI-targeted documentation** — a machine-maintained context store the
coding agent reads at session start to load a project's accumulated architecture,
contracts, decisions and gotchas, instead of re-deriving them every time. It is
distinct from the **human-targeted** docs (`methodology.md`, `AGENTS.md`,
`backlog.md`, `glossary.md`, `adr/`), which remain the sources of truth.

**Golden rule:** the wiki is **derived and disposable**. If it disagrees with the
code or a human-facing source doc, the source wins and the wiki is stale — re-ingest.
It never becomes an authority; it augments dual-update, it does not replace it.

Ingestion is split into a deterministic half and an authored half:
- **Deterministic** — `scripts/ingest_wiki.py <b_item>` records which files changed
  and at which commit into `wiki/_meta/manifest.json`. It also calls
  `scripts/_wiki_map.py → suggest_pages(repo_root, touched_files)` to compute a
  `suggested_pages` field on the manifest entry — a list of
  `(wiki_relpath, [h2_anchors])` tuples derived from a deterministic
  module-slug → page mapping. The function has no judgment; re-runs are
  idempotent. The agent decides what to do with each suggestion.
- **Authored** — during `document (post)`, review the `suggested_pages` list as a
  starting point, then patch only the heading-anchored subsections of the wiki
  pages you decide to update (create a page if a module has none), and list the
  pages you touched under `manifest.json → items[<id>].pages`. Decision digests
  **link** to the canonical ADR — never restate its rationale. The `pages[]`
  field is the agent's authored decision; `suggested_pages` is the script's
  deterministic suggestion. The two are kept separate so re-ingestion never
  silently overwrites an authored decision.

The wiki is **opt-in**: gates and checks are no-ops until `docs/megaplan/wiki/`
exists. `scripts/validate_wiki.py` verifies structure (manifest well-formed,
front-matter parses, refs resolve) — it cannot verify that authored prose is
*true*, so an agent must still read wiki context skeptically. Compiled `SPEC.md`
feeds the matching wiki pages forward as a bounded "Prior Context" section.

A B-item whose work genuinely changes no architecture may set `| Wiki-Impact | none |`
in its Metadata to waive the ingestion-record requirement.

**Advisories vs gates.** Structural validation (manifest well-formed, front-matter
parses, refs resolve) is **blocking** — manifest corruption is a real bug. The
ingestion record (missing or stale entry) is **advisory** — the wiki is
derived/disposable, and forcing every B-item to populate it would invert the
source-wins relationship. Three non-blocking signals surface stale state
without blocking the gate (see `ADR-001`):

- **Per-cycle waiver rate** — `validate_backlog.py → waiver_advisory(repo_root)`
  reports `<cycle>: <n>/<m> B-items waived Wiki-Impact (<pct>%)`. Surfaced
  via `validate_backlog` and printed to stderr. No threshold; the human/agent
  judges.
- **Per-item freshness lag** — `validate_backlog.py → freshness_advisory(repo_root)`
  reports `<id>: <n> commits behind HEAD (recorded <sha>)`. Surfaced via
  `validate_backlog` and per-item in `verify_workflow.py check` at
  `document (post) → COMPLETE`. No threshold; staleness is visible, not gated.
- **Per-item wiki reminder** — `verify_workflow.py → check_layer3_wiki` prints
  `Layer 3 advisory (wiki): ...` to stderr when the manifest entry is missing
  or stale, or when `suggested_pages` is populated but `pages[]` is empty. The
  reminder is a hint, not a gate: agents can either patch the wiki and
  re-ingest, or set `Wiki-Impact: none` to silence it.

The 3-Layer gate at `document (post) → COMPLETE` enforces the structural check
(blocking) and surfaces the three advisories. It does **not** block on
ingestion record state.

