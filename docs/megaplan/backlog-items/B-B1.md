# B1: Tarball & download integrity

## Metadata

| Field | Value |
|-------|-------|
| ID | B-B1 |
| Status | done |
| Workflow Step | complete |
| Owner | — |
| Verification | TDD |
| Wiki-Impact | none |
| Depends on | — |
| Target | `scripts/bootstrap.py`, `tests/test_bootstrap.py` |
| Last updated | 2026-07-21 |

## Outcome

`bootstrap.py` verifies the integrity of the framework tarball before extraction, handles malformed archives gracefully, and surfaces network errors with friendly messages. The `--from-local` path is a true offline install. Tarfile path-traversal attacks (CVE-2007-4559) are blocked on every supported Python version, not just 3.12+.

## Scope

- [ ] **`_safe_extractall(tar, dest)`** that walks `tar.getmembers()` and rejects (a) absolute paths, (b) any path that escapes `dest` via `..`, (c) symlinks whose targets escape `dest`. Raises `ValueError` with the offending member name. Replaces the current `try/except TypeError` fallback that silently drops to no-filter extraction on Python < 3.12.
- [ ] **`_pax_global_header_toplevel(tar)`** that finds the first member whose name contains a `/` (i.e., is a file inside the top-level dir) and uses that as the root. Skips `pax_global_header` and any other pax extension members. Errors if no real top-level dir is found.
- [ ] **`_tarball_url_for(ref)`** strict classification: tag iff `ref` matches `^v\d+\.\d+\.\d+(-[A-Za-z0-9.]+)?$`; otherwise branch. URL-quote the ref with `urllib.parse.quote(ref, safe="")`.
- [ ] **`_http_get`** distinguishes `urllib.error.HTTPError` (status code known) from generic OS errors. `download_framework` catches HTTPError and prints a friendly message including the URL and status, then exits non-zero.
- [ ] **`resolve_latest_version`** short-circuits when `args.from_local` is set and `args.ref` is None — returns the string `"local"` and never calls the network.
- [ ] **`main()`** exits non-zero if `--from-local` is set but the path is not a directory (current behavior just prints an error, but `resolve_latest_version` runs first and may have already failed).
- [ ] **`lay_out_framework`** records missing source files in the results with status `"missing"` and prints a warning to stderr for each. Tests assert the warning is emitted.

## Non-goals

- No SHA256 / Sigstore verification of the tarball in this B-item. That's a separate concern (see B2 — self-test as trust check) because the manifest-of-expected-hashes is the natural home for those checks. B1 lays the groundwork (correct extraction, friendly errors, offline path) without committing to a specific signing scheme.
- No changes to the `--ref` user-facing behavior. The flag's *meaning* is unchanged; only the classification and quoting are tightened.
- No changes to the wiki or templates. B1 is bootstrap-only.

## Dependencies / blockers

- None. B1 is the first item in Cycle B; everything builds on it.
- B2 will reuse B1's `_safe_extractall` and `_pax_global_header_toplevel` in the self-test path.

## Test plan

| Level | File | Intent |
|-------|------|--------|
| Unit | `tests/test_bootstrap.py::test_tarball_pax_global_header_handled` | Tarball with `pax_global_header` as first member + legitimate entries under `megaplan-v2.0.0/`. `download_framework` finds the right top-level dir, returns the correct path. |
| Unit | `tests/test_bootstrap.py::test_tarfile_rejects_path_traversal` | Tarball with entry `megaplan-v2.0.0/../../etc/passwd`. `download_framework` raises. |
| Unit | `tests/test_bootstrap.py::test_tarfile_rejects_absolute_path` | Tarball with entry `/etc/passwd`. `download_framework` raises. |
| Unit | `tests/test_bootstrap.py::test_tarfile_rejects_symlink_escape` | Tarball with a symlink `megaplan-v2.0.0/foo -> ../../../etc`. `download_framework` raises. |
| Unit | `tests/test_bootstrap.py::test_url_ref_quoted` | `resolve_latest_version(ref="main?x=1")` produces a URL with `%3Fx%3D1` (the query is quoted). |
| Unit | `tests/test_bootstrap.py::test_branch_classification_strict` | `_tarball_url_for("v2.0.0-fix")` returns the branch URL, not the tag URL. |
| Unit | `tests/test_bootstrap.py::test_branch_classification_prerelease` | `_tarball_url_for("v2.0.0-rc1")` returns the tag URL (semver pre-release). |
| Unit | `tests/test_bootstrap.py::test_from_local_no_network_when_no_ref` | `main()` with `--from-local` and no `--ref` does not call `urllib.request.urlopen`. |
| Unit | `tests/test_bootstrap.py::test_http_error_surfaced` | Mocked `urlopen` raises `HTTPError(404, ...)`. `download_framework` raises a clear error mentioning the URL and status. |
| Unit | `tests/test_bootstrap.py::test_missing_source_warns` | `lay_out_framework(src, dst)` where `src` lacks `AGENTS.md` — function returns a result with status `"missing"` for that file; the function or its caller prints a warning to stderr. |
| Unit | `tests/test_bootstrap.py::test_safe_extractall_raises_on_unsafe_archive` | Direct call to `_safe_extractall` with a tarball crafted to include each of the four rejected patterns. Asserts `ValueError` is raised and the message includes the offending entry name. |

## Verification & Acceptance Criteria

- [ ] `python scripts/verify_workflow.py check docs/megaplan/backlog-items/B1.md` gate passes at each step transition.
- [ ] `python -m pytest tests/` passes (65 pre-existing + 11 new for B1, all green).
- [ ] `ruff check .` has no new warnings.
- [ ] End-to-end smoke test: in a fresh tmp dir, `python scripts/bootstrap.py --from-local <repo> --ref main --project-dir <tmp>` completes without any HTTP calls. Confirm via a mock that `urlopen` is not called.
- [ ] End-to-end tarball attack test: a tarball with `pax_global_header` first and a `../../etc/passwd` entry fails cleanly with a message naming the offending entry, exit code non-zero.
- [ ] `git grep "extractall"` in `scripts/` returns nothing (the unsafe `extractall` is gone).
- [ ] Status set to `done` in both `backlog.md` and this file (same commit).
- [ ] `SPEC.md` compiled and current.

## Traceability

- Glossary: [manifest](../../megaplan/glossary.md)
- ADR: —
- Related items: [B-B2](B-B2.md) reuses B1's extraction helpers; [B-B3](B-B3.md) reuses B1's tests; [B-B4](B-B4.md) documents the resulting behavior.

## Notes

- The `_safe_extractall` function is the same shape as the one in the adversarial review's recommendation. ~15 lines, no third-party deps.
- The `pax_global_header` issue affects every GitHub-generated tarball. The fix is to skip non-`/` members when finding the top-level dir name. This is a well-known pattern.
- The strict semver regex covers `v1.2.3`, `v1.2.3-rc1`, `v1.2.3-alpha.1`. It does NOT cover `v1` (intentionally — that's a major-version branch, not a tag).
- The `--from-local` short-circuit uses the string `"local"` as the resolved version. The `--ref main` default no longer fires when `--from-local` is set, so the network call is skipped.
- The HTTPError branch in `download_framework` prints to stderr and raises a `RuntimeError`. The caller in `main()` propagates this as a non-zero exit. This is a behavior change from the current "swallow and re-raise generic Exception" path.
- Closed on 2026-07-21 as part of the Cycle B close-out (B-B1..B-B5 all done).
