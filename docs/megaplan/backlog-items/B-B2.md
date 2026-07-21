# B2: Self-test as trust check + hook integrity

## Metadata

| Field | Value |
|-------|-------|
| ID | B-B2 |
| Status | done |
| Workflow Step | complete |
| Owner | — |
| Verification | TDD |
| Wiki-Impact | none |
| Depends on | B-B1 |
| Target | `scripts/verify_workflow.py`, `scripts/setup_hooks.py`, `scripts/_mdparse.py`, `scripts/bootstrap.py`, `tests/test_verify_workflow.py`, `tests/test_bootstrap.py` |
| Last updated | 2026-07-21 |

## Outcome

`verify_workflow.py --selftest` is a **trust check**, not a completeness check. It verifies that the laid-out files match an expected hash manifest (or, on first run, computes and stores the manifest). It exercises `find_repo_root` correctly (realpath, prefer `.git` over `AGENTS.md`, fail closed). It verifies the installed pre-commit hook content. Import checks run in a subprocess, not in the running Python process.

## Scope

- [ ] **`EXPECTED_FILES_MANIFEST`** constant in `bootstrap.py` or a new `scripts/_integrity.py`: a dict mapping relative paths to SHA-256 hashes. Built at install time (bootstrap computes and writes the manifest as part of lay-out) or shipped with each release (a per-release `manifest.json` in the tarball). First B-item: install-time computation; the manifest lives in `docs/megaplan/.integrity-manifest.json` and the self-test reads it.
- [ ] **`verify_workflow.py --selftest`** computes SHA-256 of each required file in the laid-out project and compares against the manifest. Missing manifest → fail with a clear message ("No integrity manifest found at `docs/megaplan/.integrity-manifest.json`. Was the install completed?"). Mismatched hash → fail with file path, expected, actual.
- [ ] **`verify_workflow.py --selftest`** reads `.git/hooks/pre-commit` and computes its SHA-256. Compares against the value in the manifest. Mismatch → fail.
- [ ] **`find_repo_root`** uses `os.path.realpath(start)` and `os.path.realpath` on the candidate dir before checking. Prefers `.git` (as a directory or file, supporting worktrees) over `AGENTS.md`. Skips any candidate that is itself a symlink (use `os.path.islink` to detect and `continue`).
- [ ] **`find_repo_root`** fails closed: when no marker is found in any parent dir, raises `FileNotFoundError` (or returns a sentinel and the caller raises). No more `os.path.abspath(os.getcwd())` fallback.
- [ ] **Bash hook** in `setup_hooks.py`'s `HOOK_SCRIPT` constant: if the walk-up finds no `AGENTS.md` or `.git` in any parent, the hook exits 1 with a clear error message instead of guessing.
- [ ] **Import checks** in `verify_workflow.py`'s `--selftest` run in a subprocess (the framework re-invokes itself with a flag like `--selftest-imports <project_dir>`). This avoids the `sys.path` mutation that masks broken modules in the target project.
- [ ] **`bootstrap.py`** writes the integrity manifest during `lay_out_framework`. The manifest is a JSON object with `files: {relpath: sha256}` and `hook: {pre-commit: sha256}`.

## Non-goals

- No Sigstore / signed-manifest verification. The install-time manifest is the v1. A signed manifest is a future B-item (would require release infrastructure).
- No runtime file monitoring (post-install detection of modified files). The self-test is user-initiated.
- No changes to the user-facing `--selftest` CLI. The verbosity and output format stay the same; the underlying checks just get stronger.

## Dependencies / blockers

- B1: `_safe_extractall` and the corrected `download_framework` from B1 are upstream. B2's bootstrap changes (writing the manifest) build on B1's extraction fix.

## Test plan

| Level | File | Intent |
|-------|------|--------|
| Unit | `tests/test_bootstrap.py::test_lay_out_writes_integrity_manifest` | After `lay_out_framework`, `docs/megaplan/.integrity-manifest.json` exists with the expected keys and SHA-256 values for at least `AGENTS.md`, `docs/megaplan/megaplan.md`, and `scripts/megaplan/verify_workflow.py`. |
| Unit | `tests/test_bootstrap.py::test_lay_out_manifest_includes_hook` | The manifest's `hook.pre-commit` matches the SHA-256 of the actually-written `.git/hooks/pre-commit`. |
| Unit | `tests/test_bootstrap.py::test_lay_out_manifest_updated_on_force` | When `--force` overwrites a file, the manifest's hash for that file is updated to the new content's hash. |
| Unit | `tests/test_verify_workflow.py::test_selftest_verifies_file_hashes` | After lay-out, modify a laid-out file (e.g., `AGENTS.md`). Selftest fails with a clear message naming the file, expected hash, actual hash. |
| Unit | `tests/test_verify_workflow.py::test_selftest_verifies_hook` | After lay-out, modify `.git/hooks/pre-commit`. Selftest fails naming the hook. |
| Unit | `tests/test_verify_workflow.py::test_selftest_missing_manifest` | Run selftest in a project with no `.integrity-manifest.json`. Selftest fails with a clear message. |
| Unit | `tests/test_verify_workflow.py::test_selftest_imports_in_subprocess` | Selftest imports happen in a subprocess; mutating `sys.modules` in the parent process doesn't affect the import check. |
| Unit | `tests/test_verify_workflow.py::test_find_repo_root_uses_realpath` | When `start` is a path through a symlink, `find_repo_root` returns the realpath of the repo, not the symlink's target. |
| Unit | `tests/test_verify_workflow.py::test_find_repo_root_prefers_git` | When a parent dir has both `.git` and `AGENTS.md`, the `.git`-containing one is returned (`.git` is a stronger signal). |
| Unit | `tests/test_verify_workflow.py::test_find_repo_root_fails_closed` | A walk-up that finds no marker raises (doesn't return cwd). |
| Unit | `tests/test_verify_workflow.py::test_find_repo_root_skips_symlinked_markers` | If `AGENTS.md` is a symlink, the candidate is skipped. |
| Unit | `tests/test_bootstrap.py::test_selftest_after_force_rerun` | After `--force` lay-out, the new selftest passes (the manifest was updated). |

## Verification & Acceptance Criteria

- [ ] `python scripts/verify_workflow.py check docs/megaplan/backlog-items/B2.md` gate passes at each step transition.
- [ ] `python -m pytest tests/` passes (76 pre-existing + 12 new for B2, all green).
- [ ] `ruff check .` has no new warnings.
- [ ] End-to-end smoke test: lay out into a fresh project, modify `AGENTS.md`, run `verify_workflow.py --selftest`. Exit code non-zero, stderr names the file and shows expected vs actual.
- [ ] Hook content is verified by selftest (modify `.git/hooks/pre-commit`, selftest fails).
- [ ] `find_repo_root` raises on a project with no `AGENTS.md` or `.git` in any parent.
- [ ] Status set to `done` in both `backlog.md` and this file (same commit).
- [ ] `SPEC.md` compiled and current.

## Traceability

- Glossary: [manifest](../../megaplan/glossary.md)
- ADR: —
- Related items: [B-B1](B-B1.md) provides the safe extraction; [B-B3](B-B3.md) rewrites paths in laid-out docs but the manifest's paths are already correct.

## Notes

- The integrity manifest lives in `docs/megaplan/.integrity-manifest.json` (hidden by convention — it's framework-managed, not user-edited). Add `.integrity-manifest.json` to the `gitignore` template? No — it MUST be tracked so the user's project can detect tampering across machines.
- The selftest subprocess for imports re-invokes `verify_workflow.py` with a hidden flag (`--selftest-imports <dir>`). The hidden flag is added to the parser but is not in `--help` output.
- The `find_repo_root` symlink-skip is a conservative defense. Worktrees (which use `.git` files) still work because `os.path.exists` returns True for files. We just skip the case where the *marker itself* is a symlink, not where `.git` is a symlink to a real dir.
- The "fail closed" change to `find_repo_root` is a behavior change. Callers (e.g., `compile_spec.py`'s `find_repo_root` for the path-traversal check) need to handle the new exception. Add a try/except in those callers.
- The bash hook's walk-up also fails closed: it `exit 1`s if no marker is found, instead of guessing. The pre-commit hook will refuse to run on a corrupted project, which is the correct behavior.
- Closed on 2026-07-21 as part of the Cycle B close-out (B-B1..B-B5 all done).
