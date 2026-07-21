# ADR-001: Wiki advisories are non-blocking

## Status

Accepted — 2026-07-21

## Context

The AI wiki (`docs/megaplan/wiki/`) is described in `docs/methodology.md` as
"derived and disposable" — source docs and code win on conflict, the wiki never
becomes an authority, and the wiki is opt-in per project.

Layer 3 of the workflow (the `document (post) → COMPLETE` transition) was
designed around this stance. As implemented in `b865ff8`,
`verify_workflow.py check_layer3_wiki` enforces:

- Structural validation errors (manifest corruption, frontmatter failure) →
  **blocking** (via `errors.append`).
- Missing ingestion record for the B-item → **blocking**.
- Stale ingestion record (commit not an ancestor of HEAD) → **blocking**.

The two non-structural blocks are inconsistent with the "derived and
disposable" stance. The wiki is allowed to be stale. A missing ingestion
record is a process lapse, not a bug. Forcing every B-item to either patch
the wiki or set `Wiki-Impact: none` would:

- Convert the wiki from an opt-in tool into a forced chore.
- Invert the source-wins relationship: an unwritten wiki would block
  otherwise-correct B-items.
- Defeat the "advisory, not gated" framing already in the methodology.

The methodology's anti-patterns table explicitly calls out: "Setting
`Wiki-Impact: none` to skip a real architectural change" and "Treating the AI
wiki as a source of truth." Both suggest the wiki should be *advisory in
effect*, even when its machinery is well-formed.

## Decision

Wiki checks in `verify_workflow.py check_layer3_wiki` split into two
categories:

| Check | Behavior | Rationale |
|-------|----------|-----------|
| Structural validation (manifest well-formed, frontmatter parses, refs resolve) | **Blocking** | These are real bugs. A corrupt manifest is not "the wiki being stale" — it's broken state. |
| Missing or stale ingestion record for a B-item | **Advisory** (printed to stderr) | The wiki is disposable. A missing entry is a reminder, not an error. The agent can either re-ingest or confirm `Wiki-Impact: none`. |
| `validate_wiki.py` standalone: errors vs warnings | Already split (errors block, warnings advise) | The structural/advisory distinction was already correct at this layer. |

The `document (post) → COMPLETE` gate now distinguishes: "your wiki is
*broken*" (block) from "your wiki is *out of date*" (advise).

## Consequences

**Positive**

- The wiki is no longer a forced chore. Projects that opt in can ignore the
  ingestion-record step at low cost and the gate still passes.
- Agents get a useful reminder when they forget to ingest, without the gate
  blocking on the lapse.
- The methodology's "derived/disposable" stance is now reflected in code, not
  just prose.

**Negative**

- Projects that want strict wiki discipline must enforce it themselves (e.g.,
  via a stricter `validate_backlog.py` rule that fails on a low `pages[]`
  fill rate). The framework does not provide this out of the box.
- The reminder can be ignored silently. A project that ignores every wiki
  reminder ends up with an empty wiki and no signal. The per-cycle waiver
  advisory in 0-B3 is the compensating signal: it surfaces the rate so the
  pattern is visible.
- The framework's own pytest suite must continue to cover the structural
  validation path, since users may rely on the framework tests as a sanity
  check that "the wiki gate works at all" even when the advisories are
  silent.

**Neutral**

- `Wiki-Impact: none` remains a B-item metadata field. Its semantics are
  unchanged: it is the explicit signal that this B-item does not change the
  wiki. The reminder does not require it; it merely points the agent at it
  as one of two ways to clear the advisory.

## Alternatives considered

- **Block on missing/stale ingestion (status quo from `b865ff8`).**
  Rejected. Inverts the source-wins relationship. Forces every B-item to
  patch the wiki.
- **Remove all wiki checks from `verify_workflow.py`.**
  Rejected. Loses the structural-validation signal (manifest corruption is
  a real bug that agents should catch).
- **Block on missing ingestion but allow stale.**
  Rejected. The two cases are the same kind of issue (the manifest doesn't
  reflect the current state); treating them differently is more surprising
  than helpful.
- **Make the strictness configurable per project (a `wiki.gate: blocking |
  advisory` setting in the megaplan config).**
  Considered. Deferred — no megaplan config system exists yet, and adding
  one for a single setting is over-engineering. Projects that want
  strictness can write their own `validate_backlog.py` check.

## Notes

- This ADR is a cycle-level decision affecting `0-B3` (per-cycle advisories
  for waiver rate + freshness) and `0-B4` (per-item reminder at
  `document (post) → COMPLETE`). Both B-items are scoped to this decision.
- The "freshness lag" advisory in `0-B3` and the "missing/stale ingestion"
  reminder in `0-B4` are the same underlying signal (the manifest doesn't
  reflect HEAD), surfaced at two granularities. They share an ADR.
