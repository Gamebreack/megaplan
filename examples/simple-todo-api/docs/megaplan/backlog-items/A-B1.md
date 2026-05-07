# A-B1: Todo CRUD

## Metadata

| Field | Value |
|-------|-------|
| Status | in-progress |
| Priority | P0 |
| Owner | team |
| Phase | [A-P1](../phases/A-P1.md) |
| Depends on | 0-B2 |
| Target | 2026-05-07 |
| Last updated | 2026-05-03 |

## Outcome

Users can create, read, update, and delete todo items via REST API endpoints.

## Scope

- [x] POST /todos — Create a new todo
- [x] GET /todos/:id — Get a single todo
- [x] PATCH /todos/:id — Update a todo
- [x] DELETE /todos/:id — Delete a todo

## Non-goals

- List all todos (deferred to A-B2)
- Pagination (deferred to A-B2)
- Authentication (future cycle)

## Dependencies / blockers

- [0-B2](0-B2.md) — Database schema must exist

## Test plan

| Level | File | Intent |
|-------|------|--------|
| Unit | `src/todo.test.ts` | CRUD operations, validation |
| E2E | `tests/todo-crud.spec.ts` | Full API journey |

## Required checks

- [ ] `npm test` — must pass
- [ ] `npm run lint` — no new warnings
- [ ] `npm run typecheck` — no type errors
- [ ] Docs updated (API docs)

## Acceptance criteria

- [ ] All CRUD endpoints work correctly
- [ ] Validation errors return 400
- [ ] Not found returns 404
- [ ] All tests pass
- [ ] No new lint warnings
- [ ] No type errors
- [ ] Docs updated
- [ ] Status set to `done` in both `backlog.md` and this file

## Traceability

- Phase: [A-P1](../phases/A-P1.md)
- ADR: —
- Related items: [0-B2](0-B2.md), [A-B2](A-B2.md)

## Notes

Currently implementing. Red phase complete (tests written). Green phase in progress.