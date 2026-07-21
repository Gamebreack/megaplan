# B5: Windows support (`bootstrap.ps1`)

## Metadata

| Field | Value |
|-------|-------|
| ID | B-B5 |
| Status | done |
| Workflow Step | complete |
| Owner | — |
| Verification | TDD |
| Wiki-Impact | none |
| Depends on | — |
| Target | `scripts/bootstrap.ps1`, `README.md`, `tests/test_bootstrap.py` |
| Last updated | 2026-07-21 |

## Outcome

Windows users can install Megaplan with a one-line PowerShell command, parallel to the Linux/macOS `curl | python3` one-liner. The Windows path is the same code: it downloads the tarball, lays out the files, and runs the self-test. The implementation uses PowerShell's `Invoke-RestMethod` and `Expand-Archive` (no Python dependency at install time, but the laid-out scripts still require Python ≥ 3.10 to *run*).

## Scope

- [ ] **`scripts/bootstrap.ps1`** — a PowerShell 5+ script that:
  1. Resolves the latest version via the GitHub Releases API (`Invoke-RestMethod`)
  2. Downloads the tarball (`Invoke-WebRequest` to a temp file, fallback to `curl.exe` if not available)
  3. Extracts the tarball using `tar.exe` (bundled with Windows 10+)
  4. Lays out files using `Copy-Item` with the same destination mapping as `bootstrap.py` (table-driven; mirror the `LAYOUT` constant)
  5. Applies the same `PathRewriter` (B3) — implemented as a PowerShell hashtable + `Replace` calls
  6. Installs the pre-commit hook (`.git/hooks/pre-commit`) using `Set-Content` and the bash hook template (the hook is bash; Windows users with Git Bash get it working via the `bash.exe` in their PATH; Windows users without Git Bash are out of scope — the methodology requires a POSIX shell for the framework's hooks)
  7. Runs `python scripts/megaplan/verify_workflow.py --selftest` (requires Python on PATH; if not present, prints a clear warning but exits 0 — installing Python is the user's responsibility)
  8. Prints "Next steps" in the same format as `bootstrap.py`
- [ ] **`README.md`** documents the Windows install:
  ```
  powershell -c "irm https://raw.githubusercontent.com/Gamebreack/megaplan/main/scripts/bootstrap.ps1 | iex"
  ```
  Add a "Windows" subsection to the Quick start, with the prerequisite (Python ≥ 3.10, Git for Windows) and the limitation (no self-test if Python is missing; install Python first).
- [ ] **Cross-platform flag parity**: the PowerShell bootstrap supports the same flags as `bootstrap.py` (where applicable): `--ref`, `--with-wiki`, `--force`, `--project-dir`, `--from-local`, `--skip-hook`, `--skip-self-test`. PowerShell's parameter syntax is different (`-Ref` not `--ref`), so the PowerShell version uses native parameters.
- [ ] **Limitations documented**:
  - No self-test if Python is not on PATH (PowerShell script can't import the framework's modules)
  - The pre-commit hook is bash — requires Git Bash. PowerShell-native git hooks are not supported.
  - The integrity manifest (B2) is not yet verified on Windows — `sha256sum` is not on Windows by default; the PowerShell bootstrap writes the manifest but doesn't re-verify it. (Future work: use PowerShell's `Get-FileHash` to verify.)

## Non-goals

- No PowerShell-native version of the pre-commit hook. The hook is bash; Windows users who want pre-commit validation must use Git Bash.
- No rewrite of the laid-out PowerShell scripts (Megaplan has no PowerShell scripts to lay out — only bash and Python).
- No Windows-specific installer (`.msi`, `.exe`). The PowerShell one-liner is the installer.
- No rewriting `bootstrap.py` to be cross-platform via PowerShell — the two scripts share the design but the implementations are separate.

## Dependencies / blockers

- None. B5 is independent of B1–B4. The PowerShell bootstrap is a parallel implementation; it doesn't reuse Python code.
- B3's `PathRewriter` concept is shared — the PowerShell version uses the same path-rewriting table, just expressed in PowerShell syntax.

## Test plan

| Level | File | Intent |
|-------|------|--------|
| Unit | `tests/test_bootstrap.py::test_bootstrap_ps1_exists` | `scripts/bootstrap.ps1` exists. |
| Unit | `tests/test_bootstrap.py::test_bootstrap_ps1_parsable` | The PowerShell file has no obvious syntax errors (e.g., uses `param(...)`, has matching braces, no stray backticks). |
| Unit | `tests/test_bootstrap.py::test_bootstrap_ps1_has_help` | The script defines a `Get-Help`-compatible comment block at the top. |
| Unit | `tests/test_bootstrap.py::test_bootstrap_ps1_uses_irm_invoke_webrequest` | The script uses `Invoke-RestMethod` or `Invoke-WebRequest` for HTTP, not `curl.exe` directly. |
| Unit | `tests/test_bootstrap.py::test_bootstrap_ps1_mirrors_layout` | The PowerShell `LAYOUT` hashtable has the same keys as `bootstrap.py`'s `LAYOUT` (or an obviously-equivalent set). |
| Unit | `tests/test_bootstrap.py::test_bootstrap_ps1_handles_no_python` | When Python is not on PATH, the script prints a clear warning and skips the self-test (does not error). |
| Unit | `tests/test_readme.py::test_readme_documents_windows_install` | The README has the PowerShell one-liner in the Quick start. |
| Unit | `tests/test_readme.py::test_readme_documents_windows_prereqs` | The Windows subsection lists the prereqs (Python ≥ 3.10, Git for Windows, PowerShell 5+). |

## Verification & Acceptance Criteria

- [ ] `python scripts/verify_workflow.py check docs/megaplan/backlog-items/B5.md` gate passes at each step transition.
- [ ] `python -m pytest tests/` passes (112 pre-existing + 8 new for B5, all green).
- [ ] `ruff check .` has no new warnings (the PowerShell file is linted only by PowerShell, not by ruff — this is acceptable).
- [ ] Manual end-to-end test on Windows 10/11: a user with PowerShell 5+ and Python 3.10+ can run the PowerShell one-liner and get a working install. (Cannot automate this from Linux CI; documented as a manual test in the B-item's "Manual" section.)
- [ ] The README's Quick start shows both the Linux/macOS and Windows one-liners, side by side.
- [ ] Status set to `done` in both `backlog.md` and this file (same commit).
- [ ] `SPEC.md` compiled and current.

## Traceability

- Glossary: —
- ADR: —
- Related items: B1–B4's bootstrap.py changes don't need to be mirrored in PowerShell for this B-item; the PowerShell bootstrap is a separate implementation that *imports* the design (LAYOUT, PathRewriter concept) but not the code.

## Notes

- The PowerShell bootstrap is *not* a translation of `bootstrap.py` line-by-line. It's a parallel implementation that uses PowerShell idioms (`Invoke-RestMethod`, `Expand-Archive`, `Copy-Item`). The two share the *design* (LAYOUT, PathRewriter, hook installation) but the code is separate.
- Why not use Python under the hood for both? The PowerShell bootstrap is the entry point — it has to work even if Python is broken. Once the user has a working install, the Python scripts take over. The PowerShell script's only Python requirement is the optional self-test at the end.
- The "no PowerShell-native git hook" limitation is real. Git's pre-commit hook is bash on every platform. On Windows, the user needs Git Bash (installed by default with Git for Windows). If we wanted Windows-native hooks, we'd need to ship a separate PowerShell pre-commit script, which Git doesn't invoke by default. The pragmatic answer: require Git Bash, document the limitation, move on.
- The `Invoke-WebRequest` fallback to `curl.exe` is for Windows systems where PowerShell's built-in HTTP is too slow or has issues. The fallback path is rarely used in practice; we ship it for completeness.
- Cross-version PowerShell compatibility: the script targets PowerShell 5+ (Windows 10 ships with 5.1; PowerShell 7+ is the cross-platform version). The script avoids PowerShell 7+ syntax (no `using namespace`, no ternary) so it works on 5.1 too.
- Closed on 2026-07-21 as part of the Cycle B close-out (B-B1..B-B5 all done).
