# B4: User-facing install UX (pipe-args, harnesses, polish)

## Metadata

| Field | Value |
|-------|-------|
| ID | B-B4 |
| Status | done |
| Workflow Step | complete |
| Owner | — |
| Verification | TDD |
| Wiki-Impact | none |
| Depends on | B-B3 |
| Target | `README.md`, `AGENTS.md`, `skills/megaplan/SKILL.md`, `scripts/bootstrap.py`, `docs/methodology.md`, `templates/backlog.md` |
| Last updated | 2026-07-21 |

## Outcome

The install path is friendly to a first-time user. Flag-passing through `python3 -` is documented. The harness compatibility table covers the major AI coding tools (Cursor, Aider, Windsurf, Copilot) in addition to OpenCode, Hermes, and Claude Code. The bootstrap's "Next steps" tells the user exactly what to do (copy the template, fill in the B-item, point at the example). Self-test failure exits non-zero so CI scripts catch it.

## Scope

- [ ] **Pipe-args fix in the one-liner**: every instance of `curl ... | python3` in `README.md`, `AGENTS.md`, `skills/megaplan/SKILL.md`, `docs/methodology.md` becomes `curl ... | python3 -`. Add an explicit "Passing flags" example showing `curl -sSL ... | python3 - --ref v2.0.0`.
- [ ] **Harness compatibility table** in `README.md` is extended to include Cursor, Aider, Windsurf, and GitHub Copilot. Each row has the harness name and a one-line "how to use" (e.g., Cursor: "AGENTS.md is auto-loaded; or create `.cursorrules` with `cat AGENTS.md >> .cursorrules`").
- [ ] **Bootstrap "Next steps" output** is updated:
  - Step 1: `Edit docs/megaplan/megaplan.md to describe your project's vision.`
  - Step 2: `Copy docs/megaplan/backlog-items/_template.md to docs/megaplan/backlog-items/0-B1.md and fill it in.`
  - Step 3: `Read docs/megaplan/methodology.md for the full workflow.`
  - Step 4: `See a complete example at https://github.com/Gamebreack/megaplan/tree/main/examples/simple-todo-api.`
  - Step 5: `Re-run python scripts/megaplan/verify_workflow.py --selftest any time.`
  - All paths are project-relative (no absolute paths).
- [ ] **Bootstrap returns non-zero exit code** when the self-test fails (so CI scripts catch it). The summary line at the end becomes "Install completed with warnings (self-test failed)" or similar — not a silent success.
- [ ] **README Troubleshooting section** adds: "Python version" — "Megaplan requires Python 3.10+ (3.12+ recommended for the secure tarfile filter; 3.9-3.11 falls back to a manual path-traversal check). Check with `python3 --version`."
- [ ] **`templates/backlog.md`** is updated: the example row in the index is either replaced with a comment (e.g., `<!-- Replace this row with your first B-item -->`) or removed entirely; the "Rules" section references `docs/megaplan/backlog-items/_template.md` rather than the old `templates/backlog-item.md`.
- [ ] **`AGENTS.md` is trimmed to ≤ 200 lines** (the K.I.S.S. limit). The K.I.S.S. section can be removed or consolidated since the framework is now self-installing.
- [ ] **Marketplace install paths** in `README.md`: a short section pointing at the AI coding tool marketplaces where Megaplan can be installed via plugin/skill mechanisms. Two concrete paths today: Hermes Agent (`hermes skills install Gamebreack/megaplan`) and OpenCode skills (manual install to `.opencode/skills/megaplan/`).

## Non-goals

- No new CLI flags on the bootstrap.
- No interactive prompts.
- No changes to the bootstrap's *output* other than the "Next steps" lines and the exit code.
- No new docs (e.g., no separate INSTALL.md — by industry standard, install lives in the README).

## Dependencies / blockers

- B3: the path transformation makes the "Next steps" project-relative paths correct. Without B3, the B4 "Next steps" would be misaligned with the user-project layout.

## Test plan

| Level | File | Intent |
|-------|------|--------|
| Unit | `tests/test_bootstrap.py::test_next_steps_uses_relative_paths` | Bootstrap's "Next steps" output contains `docs/megaplan/megaplan.md` (no absolute path). |
| Unit | `tests/test_bootstrap.py::test_next_steps_explains_b_item_creation` | Output mentions copying `_template.md` to `0-B1.md`. |
| Unit | `tests/test_bootstrap.py::test_next_steps_points_to_example` | Output contains the GitHub URL for `examples/simple-todo-api`. |
| Unit | `tests/test_bootstrap.py::test_self_test_failure_exit_code_nonzero` | When self-test fails (e.g., remove a required file), `main()` returns non-zero. |
| Unit | `tests/test_readme.py::test_readme_one_liner_uses_python3_dash` | The README's one-liner literally contains `python3 -` (not just `python3`). |
| Unit | `tests/test_readme.py::test_readme_documents_pipe_args` | The README has an explicit example showing how to pass `--ref` through the pipe. |
| Unit | `tests/test_readme.py::test_harness_table_includes_cursor` | The README's harness table includes a row for Cursor. |
| Unit | `tests/test_readme.py::test_harness_table_includes_aider` | Same for Aider. |
| Unit | `tests/test_readme.py::test_harness_table_includes_windsurf` | Same for Windsurf. |
| Unit | `tests/test_readme.py::test_harness_table_includes_copilot` | Same for Copilot. |
| Unit | `tests/test_readme.py::test_readme_troubleshooting_has_python_version` | The Troubleshooting section has a "Python version" entry. |
| Unit | `tests/test_bootstrap.py::test_backlog_template_no_templates_path` | The laid-out `backlog.md` does not reference `templates/backlog-item.md` (it points to `_template.md` instead). |
| Unit | `tests/test_bootstrap.py::test_agents_md_under_kiss_limit` | The laid-out `AGENTS.md` is ≤ 200 lines. |
| Unit | `tests/test_readme.py::test_readme_marketplace_section` | The README has a "Marketplace install" section mentioning Hermes and OpenCode. |

## Verification & Acceptance Criteria

- [ ] `python scripts/verify_workflow.py check docs/megaplan/backlog-items/B4.md` gate passes at each step transition.
- [ ] `python -m pytest tests/` passes (98 pre-existing + 14 new for B4, all green).
- [ ] `ruff check .` has no new warnings.
- [ ] End-to-end smoke test: a fresh user runs the bootstrap. The "Next steps" are project-relative, mention the example URL, and explain B-item creation. The user can copy-paste each step and have it work.
- [ ] End-to-end pipe-args smoke test: `curl -sSL ... | python3 - --ref main` works (no Python error about unknown option).
- [ ] The harness compatibility table covers 7+ harnesses.
- [ ] The laid-out `AGENTS.md` is ≤ 200 lines.
- [ ] Status set to `done` in both `backlog.md` and this file (same commit).
- [ ] `SPEC.md` compiled and current.

## Traceability

- Glossary: —
- ADR: —
- Related items: [B-B3](B-B3.md) provides the path-corrected docs that B4 polishes; [B-B5](B-B5.md) cross-platform.

## Notes

- The "harness table" is the single biggest UX gap caught by the post-ship review. Cursor, Aider, Windsurf, and Copilot together likely exceed OpenCode and Claude Code in active users. Each new row is a small edit but unlocks a real user base.
- The pipe-args fix is one character in many places. It's a documentation bug, not a code bug — `python3` was just doing the right thing and silently consuming the flag.
- "Project-relative paths" in the "Next steps" means: the user knows where they ran the bootstrap. Absolute paths are noise. A simple `os.path.relpath` on the user's project dir suffices.
- The "exit non-zero on self-test failure" change is a small but important contract change for CI users. The current behavior ("prints to stderr, returns 0") is a footgun.
- The AGENTS.md trim is partly to comply with the framework's own K.I.S.S. limit (ironic at 201 lines) and partly because the bootstrap-laid-out AGENTS.md should be lean. Consolidating the K.I.S.S. section into the methodology reference makes the AGENTS.md more focused.
- The marketplace section is brief because Megaplan doesn't yet publish to those marketplaces — it's a "what to do when you want to install via marketplace" section, not a "click here" section. The Hermes install is the only one that works today.
- Closed on 2026-07-21 as part of the Cycle B close-out (B-B1..B-B5 all done).
