# <ID>: <Title>

## Metadata

| Field | Value |
|-------|-------|
| ID | — |
| Status | pending |
| Workflow Step | — |
| Owner | — |
| Verification | TDD |
| Wiki-Impact | — |
| Depends on | — |
| Target | — |
| Last updated | YYYY-MM-DD |

## Outcome

[One sentence — who benefits and what they can now do]

## Scope

- [ ] Item 1
- [ ] Item 2

## Non-goals

- What is explicitly out of scope

## Dependencies / blockers

- None

## Test plan

| Level | File | Intent |
|-------|------|--------|
| Unit | `src/path/to/file.test.ext` | happy path + edge cases |
| E2E | `tests/path/to/file.spec.ext` | full user journey |

## Verification & Acceptance Criteria

- [ ] `python scripts/verify_workflow.py check` gate passes at each step transition
- [ ] `npm test` / Verification command passes
- [ ] `npm run lint` / Lint command has no new warnings
- [ ] `npm run typecheck` / Typecheck command has no type errors
- [ ] Documentation updated (if applicable)
- [ ] Status set to `done` in both `backlog.md` and this file (same commit)
- [ ] `SPEC.md` compiled and current (`python scripts/compile_spec.py <this_file>`)

## Traceability

- Glossary: [link]
- ADR: [link or —]
- Related items: [IDs or —]

## Notes

[Free-form context, hardening concerns, migration notes, known drift]
