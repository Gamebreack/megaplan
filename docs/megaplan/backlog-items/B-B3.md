# B3: Path transformation for laid-out docs

## Metadata

| Field | Value |
|-------|-------|
| ID | B-B3 |
| Status | done |
| Workflow Step | complete |
| Owner | — |
| Verification | TDD |
| Wiki-Impact | none |
| Depends on | — |
| Target | `scripts/bootstrap.py`, `templates/*.md`, `templates/wiki/*.md`, `AGENTS.md`, `docs/methodology.md`, `tests/test_bootstrap.py` |
| Last updated | 2026-07-21 |

## Outcome

When the bootstrap lays out `AGENTS.md`, `methodology.md`, `SKILL.md`, and the templates into the user's project, the path references *inside* those files are rewritten to match the user-project layout (e.g., `scripts/verify_workflow.py` → `scripts/megaplan/verify_workflow.py`; `docs/methodology.md` → `docs/megaplan/methodology.md`; `templates/backlog-item.md` → `docs/megaplan/backlog-items/_template.md`). The framework repo's own files stay as-is (no transformation when destination is the framework itself).

## Scope

- [ ] **`PathRewriter` class** in `bootstrap.py` (or a new `scripts/_paths.py`): a small state machine that takes a `(framework_root, user_project_dir)` pair and rewrites a string according to a configurable set of `(from, to)` path substitutions. The substitutions are applied in order, longest-match-first.
- [ ] **Substitution table** — a module-level constant `USER_PROJECT_PATH_REWRITES`:
  - `scripts/` → `scripts/megaplan/` (for any file under `scripts/`)
  - `docs/methodology.md` → `docs/megaplan/methodology.md`
  - `templates/megaplan.md` → `docs/megaplan/megaplan.md`
  - `templates/backlog.md` → `docs/megaplan/backlog.md`
  - `templates/glossary.md` → `docs/megaplan/glossary.md`
  - `templates/backlog-item.md` → `docs/megaplan/backlog-items/_template.md`
  - `templates/adr.md` → `docs/megaplan/adr/_template.md`
  - `examples/simple-todo-api/` → `https://github.com/Gamebreack/megaplan/tree/main/examples/simple-todo-api/` (URL, not path)
  - `templates/wiki/` → `docs/megaplan/wiki/` (only relevant for wiki-page files)
- [ ] **Lay-out-time transformation**: when `lay_out_framework` copies a text file (`.md` or `.py` or any file under the `LAYOUT` paths), the destination content is run through `PathRewriter` before being written. The path-table substitution is bidirectional-safe: re-applying doesn't cycle.
- [ ] **Self-detection**: if `project_dir == framework_root` (the user is running the bootstrap on the framework itself, e.g., for dogfooding), skip the transformation. The framework's own paths stay correct.
- [ ] **Templates' "next steps" section** in `templates/backlog.md` is updated to reference `docs/megaplan/backlog-items/_template.md` rather than the old `templates/backlog-item.md`. Or, the bootstrap rewrites the existing reference. Choose one; document in the B-item notes.
- [ ] **AGENTS.md "Templates" section** is removed (the bootstrap already did the copy) and replaced with a single line: "Templates were installed by the bootstrap to `docs/megaplan/`."
- [ ] **docs/methodology.md "File templates" table** is reframed from "copy from templates/ to docs/megaplan/" (the user already has these) to "see `docs/megaplan/` for the installed copies."
- [ ] **`SKILL.md` "Reference" link** to `references/methodology.md` is updated to `docs/megaplan/methodology.md`.
- [ ] **Re-run idempotency**: running lay-out twice with the new transformation produces the same result (the rewritten text is the same on the second pass — no second-order substitution).

## Non-goals

- No changes to `docs/methodology.md`'s deeper content (the workflow, the gates, the philosophy). Only the path references and the templates table.
- No changes to the templates' substantive content (the metadata schema, the B-item structure). Only path references.
- No new templating engine. The `PathRewriter` is a simple `str.replace` loop with care for ordering, not Jinja or similar.

## Dependencies / blockers

- None. B3 is independent of B1 and B2.

## Test plan

| Level | File | Intent |
|-------|------|--------|
| Unit | `tests/test_bootstrap.py::test_path_rewriter_simple_substitution` | `PathRewriter.rewrite("see scripts/setup_hooks.py")` returns `"see scripts/megaplan/setup_hooks.py"`. |
| Unit | `tests/test_bootstrap.py::test_path_rewriter_longest_first` | `PathRewriter.rewrite("scripts/foo")` matches `scripts/megaplan/foo`, not just `scripts/`. |
| Unit | `tests/test_bootstrap.py::test_path_rewriter_idempotent` | `PathRewriter.rewrite(PathRewriter.rewrite(s)) == PathRewriter.rewrite(s)` for various `s`. |
| Unit | `tests/test_bootstrap.py::test_path_rewriter_does_not_double_substitute` | `PathRewriter.rewrite("scripts/megaplan/verify_workflow.py")` returns the same string — no second-order rewrite. |
| Unit | `tests/test_bootstrap.py::test_lay_out_rewrites_agents_md_paths` | After lay-out, the user-project `AGENTS.md` has `scripts/megaplan/verify_workflow.py`, not `scripts/verify_workflow.py`. |
| Unit | `tests/test_bootstrap.py::test_lay_out_rewrites_methodology_paths` | After lay-out, the user-project `docs/megaplan/methodology.md` has `docs/megaplan/...` references, not `docs/...`. |
| Unit | `tests/test_bootstrap.py::test_lay_out_rewrites_skill_md_paths` | After lay-out, the user-project `SKILL.md` has `docs/megaplan/methodology.md`, not `references/methodology.md`. |
| Unit | `tests/test_bootstrap.py::test_lay_out_rewrites_backlog_template` | After lay-out, the user-project `backlog.md` does not reference the old `templates/backlog-item.md` path. |
| Unit | `tests/test_bootstrap.py::test_lay_out_no_transformation_for_framework_repo` | When `project_dir == framework_root`, the laid-out `AGENTS.md` is byte-identical to the source (no transformation). |
| Unit | `tests/test_bootstrap.py::test_lay_out_idempotent_with_transformation` | Lay out twice; the second run is idempotent (the rewritten text is the same on the second pass). |

## Verification & Acceptance Criteria

- [ ] `python scripts/verify_workflow.py check docs/megaplan/backlog-items/B3.md` gate passes at each step transition.
- [ ] `python -m pytest tests/` passes (88 pre-existing + 10 new for B3, all green).
- [ ] `ruff check .` has no new warnings.
- [ ] End-to-end smoke test: lay out into a fresh project. `grep "scripts/verify_workflow.py" AGENTS.md` returns nothing (the old path is gone). `grep "scripts/megaplan/verify_workflow.py" AGENTS.md` returns at least one match (the new path is present).
- [ ] The framework's own `AGENTS.md`, `methodology.md`, `SKILL.md` are byte-identical to their pre-B3 versions (no transformation when destination is the framework).
- [ ] `git grep "templates/backlog-item.md"` in `AGENTS.md` and `docs/methodology.md` (laid-out copies) returns nothing.
- [ ] Status set to `done` in both `backlog.md` and this file (same commit).
- [ ] `SPEC.md` compiled and current.

## Traceability

- Glossary: —
- ADR: —
- Related items: [B-B4](B-B4.md) updates the harness table and other user-facing docs which build on the path transformation; [B-B5](B-B5.md) cross-platform work doesn't touch paths.

## Notes

- The "longest-match-first" rule is critical: a path `scripts/setup_hooks.py` must match `scripts/...` (the substitution), not just `scripts/` (a hypothetical narrower rule). The `PathRewriter` orders substitutions by length descending.
- Self-detection of "framework repo" is done by checking if `project_dir` contains an `AGENTS.md` AND a `docs/megaplan/` (which user projects don't have at install time). Simpler: check if `project_dir == os.path.dirname(os.path.dirname(__file__))` (the framework repo is always two levels up from `scripts/bootstrap.py`). Use the latter.
- The example-project URL rewrite (`examples/simple-todo-api/` → GitHub URL) is a deliberate choice: the user can't follow a relative path to the framework's examples from their own project, but they can click a GitHub URL.
- "Bidirectional-safe" means: after one rewrite pass, no further substitutions apply. The `USER_PROJECT_PATH_REWRITES` table is the single source of truth; adding a new entry doesn't break idempotency as long as the entries don't overlap.
- The bootstrap's pre-existing transformation for `tarfile` extraction (B1) is orthogonal to this — B1 fixes extraction, B3 fixes content rewriting. Both are needed for a correct user-project layout.
- Closed on 2026-07-21 as part of the Cycle B close-out (B-B1..B-B5 all done).
