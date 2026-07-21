# A-B1: Dumb-install bootstrap

## Metadata

| Field | Value |
|-------|-------|
| ID | A-B1 |
| Status | done |
| Workflow Step | complete |
| Owner | — |
| Verification | TDD |
| Wiki-Impact | none |
| Depends on | — |
| Target | `scripts/bootstrap.py`, `scripts/setup_hooks.py`, `scripts/verify_workflow.py`, `tests/test_bootstrap.py`, `tests/test_verify_workflow.py`, `README.md`, `AGENTS.md`, `skills/megaplan/SKILL.md`, `docs/methodology.md` |
| Last updated | 2026-07-21 |

## Outcome

A user with an empty project can adopt megaplan by running one command — `curl -sSL https://raw.githubusercontent.com/Gamebreack/megaplan/main/scripts/bootstrap.py | python3` — and get a working install: `AGENTS.md` at the root, `docs/megaplan/` with the four core templates, the framework scripts under `scripts/megaplan/`, the pre-commit hook installed, and a self-test command the user can re-run any time. The bootstrap resolves the latest version automatically; pinning is opt-in via `--ref`.

## Scope

- [ ] New `scripts/bootstrap.py` (in the framework repo; not laid out into user projects) with:
  - `resolve_latest_version(ref=None) -> str` — calls the GitHub Releases API; falls back to `main` if the API is unavailable or `ref` is set explicitly.
  - `download_framework(version, dest) -> Path` — downloads the matching release tarball (or `main` archive if no release), extracts to a temp dir.
  - `lay_out_framework(src, project_dir, *, with_wiki=False, force=False) -> list[Path]` — copies the framework files into the user's project, skipping existing files unless `--force`. Returns the list of paths written.
  - `install_pre_commit_hook(project_dir, *, force=False) -> Path` — invokes the laid-out `scripts/megaplan/setup_hooks.py` with the right arguments.
  - `self_test(project_dir) -> bool` — runs the laid-out `verify_workflow.py --selftest`; returns True on success.
  - `main()` — orchestrates the above with argparse for `--ref`, `--with-wiki`, `--force`, `--project-dir`, `--from-local <path>` (testing hook; bypasses the network).
- [ ] Modify `scripts/setup_hooks.py` to use `find_repo_root` from `_mdparse.py` instead of fixed-path math, so it works when laid out at `scripts/megaplan/setup_hooks.py`.
- [ ] Modify `scripts/verify_workflow.py` to add a `--selftest` mode: confirms the install is internally consistent (scripts importable, repo root findable, no obvious breakage). Exits 0 on success, non-zero with a clear message otherwise.
- [ ] New `tests/test_bootstrap.py` covering: version resolution (mocked HTTP), tarball extraction, file layout (with and without `--with-wiki`), idempotency (re-run skips existing), `--force` overwrites, `--from-local` bypasses network, pre-commit hook install (in a tmp repo), self-test command runs.
- [ ] New tests in `tests/test_verify_workflow.py` for the `--selftest` mode.
- [ ] Update `README.md` Quick start: the one-line command, expected output, verification command. Add a "Troubleshooting" section with the three most likely errors (no `.git/`, Python < 3.10, network blocked).
- [ ] Update `AGENTS.md` and `skills/megaplan/SKILL.md` to mention the bootstrap as the first step under "Loading this skill."
- [ ] Update `docs/methodology.md` to add a "Quick start" section pointing to the bootstrap and explaining when to use `--with-wiki`.

## Non-goals

- No PyPI publication (Shape B from the design discussion). Reserved for a future cycle if needed.
- No interactive prompts. The bootstrap is non-interactive; flags opt into behavior changes.
- No overwriting existing files by default. `--force` is the explicit escape hatch.
- No `pip install megaplan` flow. The framework is methodology + scripts, not a runtime package.
- No release-tarball publishing work (the bootstrap uses `archive/refs/heads/main.tar.gz` by default; release-tarball support is automatic once a release is tagged).
- No changes to the harness compatibility table (OpenCode, Hermes, Claude Code) — those still work the same way; the bootstrap just gives a faster path to a working `AGENTS.md`.

## Dependencies / blockers

- None. Builds on the framework scripts already shipped in commits `b865ff8` and `9b9e4ff` (which include `setup_hooks.py` and the wiki-related files).

## Test plan

| Level | File | Intent |
|-------|------|--------|
| Unit | `tests/test_bootstrap.py::test_resolve_latest_version_default` | No `--ref`, mocked GitHub API returns `v2.0.0` → function returns `v2.0.0` |
| Unit | `tests/test_bootstrap.py::test_resolve_latest_version_pinned` | `--ref v1.5.0` → function returns `v1.5.0` without calling the API |
| Unit | `tests/test_bootstrap.py::test_resolve_latest_version_api_fallback` | API call raises (network down) → falls back to `main` with a warning to stderr |
| Unit | `tests/test_bootstrap.py::test_lay_out_basic` | Lay out the framework into a tmp project; expected files present (`AGENTS.md`, `docs/megaplan/megaplan.md`, `scripts/megaplan/verify_workflow.py`, etc.) |
| Unit | `tests/test_bootstrap.py::test_lay_out_idempotent` | Lay out twice without `--force` → second run reports "skipped" for each existing file; nothing destroyed |
| Unit | `tests/test_bootstrap.py::test_lay_out_force` | Lay out twice with `--force` → second run overwrites |
| Unit | `tests/test_bootstrap.py::test_lay_out_with_wiki` | `--with-wiki` lays out `docs/megaplan/wiki/{INDEX,architecture,contracts,decisions,notes}.md` |
| Unit | `tests/test_bootstrap.py::test_install_pre_commit_hook` | Lay out into a tmp project, install hook; `.git/hooks/pre-commit` exists and is executable |
| Unit | `tests/test_bootstrap.py::test_install_pre_commit_hook_existing` | Existing hook + no `--force` → skipped; `--force` overwrites |
| Unit | `tests/test_bootstrap.py::test_self_test_runs` | After lay-out, `self_test` invokes `verify_workflow.py --selftest` and returns True |
| Unit | `tests/test_bootstrap.py::test_from_local_bypasses_network` | `--from-local <path>` uses the local path; no HTTP calls (verified via mock) |
| Unit | `tests/test_bootstrap.py::test_no_git_errors` | No `.git/` directory → bootstrap errors with a clear message; exits non-zero |
| Unit | `tests/test_verify_workflow.py::test_selftest_succeeds` | In a fully-laid-out test repo, `verify_workflow --selftest` exits 0 |
| Unit | `tests/test_verify_workflow.py::test_selftest_detects_missing_scripts` | Missing `scripts/megaplan/verify_workflow.py` → `--selftest` exits non-zero with a clear message |

## Verification & Acceptance Criteria

- [ ] `python scripts/verify_workflow.py check docs/megaplan/backlog-items/A-B1.md` gate passes at each step transition.
- [ ] `python -m pytest tests/` passes (50 pre-existing + the new bootstrap/selftest tests, all green).
- [ ] `ruff check .` has no new warnings.
- [ ] Manual end-to-end test: in a fresh tmp directory, run the bootstrap via `--from-local` (which doesn't need network), confirm the laid-out project has all expected files and `python scripts/megaplan/verify_workflow.py --selftest` exits 0.
- [ ] `README.md` Quick start shows the one-line command and the verification command, both copy-paste-runnable.
- [ ] `AGENTS.md` and `skills/megaplan/SKILL.md` reference the bootstrap.
- [ ] `docs/methodology.md` has a Quick start section pointing to the bootstrap.
- [ ] Status set to `done` in both `backlog.md` and this file (same commit).
- [ ] `SPEC.md` compiled and current.

## Traceability

- Glossary: [B-item](../../megaplan/glossary.md), [sandbox](../../megaplan/glossary.md)
- ADR: —
- Related items: this is the only B-item in Cycle A

## Notes

- The bootstrap does NOT get laid out into the user's project. It only lives in the framework repo at `scripts/bootstrap.py` and is fetched by URL. This avoids the user having a stale `bootstrap.py` in their project; the URL is always the latest.
- `setup_hooks.py` is being modified to use `find_repo_root` so it works from `scripts/megaplan/`. This is in-scope because the bootstrap needs the hook to install correctly when scripts are at a non-default path.
- `verify_workflow.py --selftest` is a small, focused addition: imports the framework's own modules, checks for obvious breakage, exits with a clear status. It's a self-check, not a project validator.
- The design decision to use GitHub Releases API for version resolution (rather than always using `main`) is to avoid forcing users onto unstable code. The fallback to `main` is the escape hatch for projects that want bleeding edge.
- Tests use `unittest.mock` to stub the network call; no test requires internet access.
- The `--from-local` flag exists primarily for testing but is also useful for developers who want to test a local clone of the framework without publishing a release.
