# Glossary

Canonical domain terms for the megaplan framework. Every agent session uses these
words — no synonyms, no improvisation.

## Terms

| Term | Definition | Canonical example | Common confusions | Category |
|------|------------|-------------------|-------------------|----------|
| Megaplan | The plan-tracking framework shipped by this repo. | "Megaplan v2.0.0" | Not "the project a user is building" — the framework is the tool. | Framework |
| Cycle | A major delivery milestone. Cycle 0 scaffolds; Cycle A delivers the first domain. | "Cycle 0 — Scaffold" | Not the same as a "sprint" or "iteration" — cycles gate each other. | Framework |
| B-item | A single, atomic deliverable with its own file. | `0-B1: suggest_pages helper` | Not a "task" or "ticket" — B-items carry their own scope, test plan, and acceptance criteria. | Framework |
| Workflow step | One of `document-pre`, `red`, `green`, `blue`, `document-post`, `complete`. | `Workflow Step: red` | The "step" is the *current position* in the mandatory sequence, not a status. | Framework |
| Layer 1 | Karpathy's spec-compilation gate: B-item compiled to `SPEC.md` before `red`. | `check_layer1_spec` | "Compile the spec" — Layer 1 is about context control. | Framework |
| Layer 2 | Karpathy's multi-stage verifier: tests → lint/types → docs. | `check_layer2_verifier` | The *executable* check, run inside the sandbox. | Framework |
| Layer 3 | Karpathy's automated ingestion loop: dual-update + wiki ingest. | `check_layer3_ingestion` | The *documentation-system* check at `document (post) → COMPLETE`. | Framework |
| Gate | A specific check inside `verify_workflow.py` that must pass before advancing. | "GATE PASSED — Safe to advance from `red` to `green`." | Gates can be blocking or advisory; the distinction matters. | Framework |
| Dual-update | The rule that every status change updates both `backlog.md` and the detail file in the same commit. | `Status: done` in both files | Not a suggestion — index/detail drift is a documentation bug. | Framework |
| Sandbox | The isolated execution environment required for all verification commands. | "Run pytest inside the sandbox" | Not the same as the host shell — the methodology forbids host execution of verification commands. | Framework |
| AI wiki | The opt-in, machine-targeted doc store at `docs/megaplan/wiki/`. Derived and disposable. | `architecture/users.md` | Not a substitute for human docs — source docs and code always win on conflict. | Wiki |
| Source-wins | The rule that if the wiki disagrees with code or a source doc, the source wins and the wiki is stale. | "Re-ingest at `document (post)`." | Not "wiki is wrong" — the wiki is *allowed* to be stale; it's the agent's job to re-ingest. | Wiki |
| Wiki page | A file under `wiki/{architecture,contracts,decisions,notes}/<slug>.md` with strict YAML frontmatter. | `architecture/users.md` | A page is one of four types: architecture, contract, decision, notes. | Wiki |
| Decision digest | A wiki page that is a search-optimized stub linking to a canonical ADR. | `decisions/A-B3.md` → `ADR-003` | Not a restatement — digests only link, never restate the rationale. | Wiki |
| Manifest | `_meta/manifest.json` — the deterministic per-B-item ingestion record. | `{"items": {"A-B1": {"touched_files": [...]}}}` | Not authored prose — manifest is pure bookkeeping. | Wiki |
| Touched files | The list of files changed for a B-item, recorded in the manifest. | `["src/users/service.py"]` | Computed by git; excludes `wiki/`, `SPEC.md`, `__pycache__/`. | Wiki |
| Wiki-Impact | The B-item metadata field declaring whether the item changes the wiki. | `Wiki-Impact: none` | Not a status — it's a waiver. `none` is the escape hatch from Layer 3's ingestion record. | Wiki |
| Module slug | A deterministic string derived from a file path that names the module a file belongs to. | `src/users/service.py` → `users` | Not a file path — slugs group files into a single wiki page. | Wiki |
| Wiki page suggestion | A deterministic `(wiki_relpath, [h2_anchors])` tuple computed from touched files. | `["architecture/users.md", ["Responsibility", "Boundaries"]]` | Not an agent decision — the suggestion is reproducible; the agent decides what to *do* with it. | Wiki |
| Deterministic suggestion | The half of Layer 3 ingestion that is pure code: file-to-slug, slug-to-page, manifest bookkeeping. | `suggest_pages()` in `_wiki_map.py` | Has no judgment. Re-runs are idempotent. | Wiki |
| Authored decision | The half of Layer 3 ingestion that is agent-owned: which wiki pages to patch and what to write. | `manifest.items[id].pages` | Not a script's job — the agent owns the call. | Wiki |
| Waived rate | The fraction of B-items in a cycle that set `Wiki-Impact: none`. | "3/12 (25%) waived" | Advisory-only, not a threshold. The methodology warns against treating the rate as a quality gate. | Wiki |
| Freshness lag | The number of commits between `manifest.items[id].updated_at_commit` and HEAD. | "5 of 9 items > 3 commits behind" | Advisory — surfaces stale wiki ingestion, not blocks it. | Wiki |
