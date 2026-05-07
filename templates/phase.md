# Cycle <X> — Phase <N>: <Title>

## Status

PENDING

## Scope

[What this phase delivers in business terms]

## Business outcome

[One sentence — who benefits and what they get]

## Backlog items

- [<ID>: Title](../backlog-items/<ID>.md)

## Workflow

### 1. Document (pre)

- [ ] Update architecture docs
- [ ] Create or update ADR if there's a significant decision
- [ ] Draft this phase file

### 2. Red — Failing tests

- [ ] Unit tests as defined in each B-item's test plan
- [ ] E2E tests for user-facing behavior

### 3. Green — Implementation

- [ ] Implement each B-item per its scope

### 4. Blue — Refactor

- [ ] Clean up duplication
- [ ] Align naming to conventions

### 5. Document (post)

- [ ] Update architecture docs to reflect what was built
- [ ] Update phase status

## Phase complete when

- [ ] All backlog items for this phase are `done`
- [ ] All tests pass
- [ ] Docs updated (architecture README, any ADRs)
- [ ] Phase status set to COMPLETE in `megaplan.md`

## Dependencies

- [ ] List any external dependencies or prerequisites

## Notes

[Free-form context, decisions, concerns]