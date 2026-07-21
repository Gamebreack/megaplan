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

- **Status**: in-progress
- **Objectives**:
  - Bootstrap the megaplan structure in this repo (glossary, backlog, B-items, ADRs).
  - Close the four open design questions from the Layer 3 wiki work.
  - Keep the framework's own codebase within the methodology's discipline.
- **Exit Criteria**:
  - All four B-items (`0-B1`..`0-B4`) reach `done`.
  - Full pytest suite green.
  - `docs/methodology.md` accurately reflects the new behavior.
  - No `_meta/ingestion.log` writes anywhere in the framework or its tests.
  - `validate_wiki.py`, `validate_backlog.py`, and `verify_workflow.py` advisories
    are documented in the methodology as non-blocking.

## Errata

- **2026-07-21 — Wiki is opt-in; the framework repo does not enable a wiki for itself.**
  The AI wiki (`docs/megaplan/wiki/`) is a feature for *projects that use* megaplan, not
  for megaplan itself. The framework is the tool, not a project that benefits from the
  tool. The wiki machinery is covered by pytest instead.
- **2026-07-21 — Uncommitted Layer 3 work was committed as `b865ff8` as a foundation.**
  The four B-items in Cycle 0 are behavior *changes on top of* that foundation, not
  reproductions of it.
