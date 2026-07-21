# Megaplan — Megaplan (Dogfooded)

## Vision

This is the megaplan framework applied to itself. The framework is a tool, but it
also has its own maintenance surface (scripts, templates, docs, gates) that evolves
over time. To keep that evolution disciplined, the same workflow the framework prescribes
for any project — `document (pre) → red → green → blue → document (post) → COMPLETE` —
is applied to changes in this repo.

Every framework change must be a B-item with a test plan, a green/red/blue history,
and dual-update of `backlog.md` and the item detail file. The framework is its own
first user.

## Delivery model

- **Cycle 0** — Scaffold + framework tooling improvements. Ship the four B-items that
  close the gaps surfaced during the Layer 3 wiki work (deterministic file-to-page
  suggestion, ingestion log removal, waiver + freshness advisories, verify reminder).
- **Cycle A+** — Reserved for future framework expansion. Will be scoped when needed.

## Workflow

`document (pre) → red → green → blue → document (post) → COMPLETE`

Gated by `python scripts/verify_workflow.py check <b_item> [--run-verifier]`.

## Cycles

### Cycle 0 — Scaffold + tooling improvements

- **Status**: done
- **Objectives**:
  - Bootstrap the megaplan structure in this repo (glossary, backlog, B-items, ADRs).
  - Close the four open design questions from the Layer 3 wiki work.
  - Keep the framework's own codebase within the methodology's discipline.
- **Exit Criteria** (all met on 2026-07-21):
  - All four B-items (`0-B1`..`0-B4`) reach `done`. ✅
  - Full pytest suite green (50/50). ✅
  - `docs/methodology.md` accurately reflects the new behavior. ✅
  - No `_meta/ingestion.log` writes anywhere in the framework or its tests. ✅
  - `validate_wiki.py`, `validate_backlog.py`, and `verify_workflow.py` advisories
    are documented in the methodology as non-blocking. ✅

### Cycle A — User-facing install

- **Status**: done
- **Objectives**:
  - Ship a one-command install that any project can use to adopt megaplan.
  - Resolve "latest version" automatically; pin only when the user asks.
  - Verify the install works (a self-test the user can re-run any time).
  - Keep the install non-destructive (skip existing files, never overwrite without
    `--force`).
- **Exit Criteria** (all met on 2026-07-21):
  - `A-B1` (dumb-install bootstrap) reaches `done`. ✅
  - `python scripts/bootstrap.py --from-local <repo> --ref main --project-dir <empty>` lays out
    `AGENTS.md`, `docs/megaplan/`, the framework scripts, and the pre-commit hook in a clean
    test repo. ✅
  - `python scripts/megaplan/verify_workflow.py --selftest` reports the install is OK. ✅
  - Re-running the bootstrap is idempotent (skip + warn, no destructive overwrite). ✅
  - Full pytest suite green (65/65). ✅

### Cycle B — Post-review hardening

- **Status**: done
- **Objectives**:
  - Address 30 actionable findings from a 5-lens post-ship review of A-B1
    (strategic, code, standards, UX, adversarial).
  - The largest meta-findings are: (i) no integrity verification at any layer
    (tarball, file hashes, hook content, self-test); (ii) the self-test is a
    completeness check, not a trust check; (iii) docs written for the framework
    repo are copied verbatim to the user project where paths are different;
    (iv) `curl | python3` flag passing is broken in the docs.
  - Five B-items grouped by meta-finding, sequenced by dependency
    (B-B1 establishes the checksum infrastructure; B-B2 builds on it).
- **Exit Criteria** (all met on 2026-07-21):
  - All five B-items (`B-B1`..`B-B5`) reach `done`. ✅
  - Full pytest suite green at each step transition (118/118). ✅
  - A fresh end-to-end smoke test (clean tmp repo) shows: 0 critical/blocking
    review findings remain, 0 HIGH findings remain. ✅
  - `docs/methodology.md` accurately reflects the new behavior. ✅
  - The framework's own install path follows the same rules as user installs
    (dogfood). ✅

## Errata

- **2026-07-21 — Wiki is opt-in; the framework repo does not enable a wiki for itself.**
  The AI wiki (`docs/megaplan/wiki/`) is a feature for *projects that use* megaplan, not
  for megaplan itself. The framework is the tool, not a project that benefits from the
  tool. The wiki machinery is covered by pytest instead. The 100% waiver advisory
  (`Cycle 0: 4/4 B-items waived Wiki-Impact`) is expected and confirms the scope.
- **2026-07-21 — Uncommitted Layer 3 work was committed as `b865ff8` as a foundation.**
  The four B-items in Cycle 0 are behavior *changes on top of* that foundation, not
  reproductions of it.
- **2026-07-21 — Cycle 0 closed.** All four B-items completed via the full workflow.
  Commits: `9b9e4ff` (0-B1), `04912b7` (0-B2), `cfa3207` (0-B3), `0784a3a` (0-B4).
  `validate_backlog` reports 100% waiver rate for Cycle 0 — this is correct (the
  framework tooling work does not change user-facing architecture that would warrant
  wiki pages) and the methodology's anti-pattern guidance explicitly tolerates it
  when the scope is "tooling not product."
- **2026-07-21 — Cycle A closed.** `0154cdd` shipped the dumb-install bootstrap.
  A post-ship 5-lens review found 30 actionable items; Cycle B addresses them.
- **2026-07-21 — B-item naming convention.** This cycle uses `B1`..`B5` (no cycle
  prefix) for the standard "Cycle B" naming. Per the methodology's "Cycle N — name"
  pattern in `megaplan.md`, the cycle header (`Cycle B — Post-review hardening`)
  gives the human context, while the B-item IDs stay short.
- **2026-07-21 — B-item IDs renamed from `B1`..`B5` to `B-B1`..`B-B5`.** Renamed
  files and updated all references to match the consistent `cycle-B` prefix pattern
  used by cycles 0 and A.
- **2026-07-21 — Cycle B closed.** All 5 B-items (`B-B1`..`B-B5`) completed via the
  full workflow. Commits: (this will be the only commit for Cycle B).

## Errata

- **2026-07-21 — Wiki is opt-in; the framework repo does not enable a wiki for itself.**
  The AI wiki (`docs/megaplan/wiki/`) is a feature for *projects that use* megaplan, not
  for megaplan itself. The framework is the tool, not a project that benefits from the
  tool. The wiki machinery is covered by pytest instead.
- **2026-07-21 — Uncommitted Layer 3 work was committed as `b865ff8` as a foundation.**
  The four B-items in Cycle 0 are behavior *changes on top of* that foundation, not
  reproductions of it.
