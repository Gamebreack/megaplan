# A-B2: List todos

## Metadata

| Field | Value |
|-------|-------|
| Status | ready |
| Priority | P1 |
| Owner | team |
| Phase | [A-P1](../phases/A-P1.md) |
| Depends on | A-B1 |
| Target | 2026-05-10 |
| Last updated | 2026-05-03 |

## Outcome

Users can list all todos with pagination support.

## Scope

- [ ] GET /todos — List all todos with pagination
- [ ] Query params: page, limit
- [ ] Response: todos array + pagination metadata

## Non-goals

- Filtering (future cycle)
- Sorting (future cycle)
- Search (future cycle)

## Dependencies / blockers

- [A-B1](A-B1.md) — Todo CRUD must complete first

## Test plan

| Level | File | Intent |
|-------|------|--------|
| Unit | `src/todo-list.test.ts` | Pagination logic |
| E2E | `tests/todo-list.spec.ts` | Full API journey |

## Acceptance criteria

- [ ] GET /todos returns paginated list
- [ ] Page/limit params work
- [ ] Metadata included (total, page, limit, hasMore)
- [ ] All tests pass
- [ ] Status set to `done` in both `backlog.md` and this file

## Traceability

- Phase: [A-P1](../phases/A-P1.md)
- ADR: —
- Related items: [A-B1](A-B1.md)

## Notes

Queued behind A-B1. Will start after A-B1 reaches document (post) phase.