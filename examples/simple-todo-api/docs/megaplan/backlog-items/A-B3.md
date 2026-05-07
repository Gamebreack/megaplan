# A-B3: User accounts

## Metadata

| Field | Value |
|-------|-------|
| Status | blocked |
| Priority | P1 |
| Owner | team |
| Phase | [A-P1](../phases/A-P1.md) |
| Depends on | A-B1 |
| Target | — |
| Last updated | 2026-05-05 |

## Outcome

Each todo is owned by a user; users can sign up, sign in, and only see their own todos.

## Scope

- [ ] User model (id, email, password hash, createdAt)
- [ ] POST /auth/signup
- [ ] POST /auth/signin returning a session token
- [ ] Authorization middleware enforcing token on `/todos/*`
- [ ] Foreign key from `Todo.userId` to `User.id`

## Non-goals

- Social login (Google, GitHub) — separate item once provider is chosen
- Password reset flow — deferred to a hardening cycle
- Email verification — deferred

## Dependencies / blockers

- **Blocked**: awaiting ADR on auth provider — Auth0 vs. Clerk vs. roll-your-own JWT. Decision affects the entire surface area of this item (data model, middleware, signup flow), so we cannot start implementation until the ADR lands.
- [A-B1](A-B1.md) — CRUD endpoints must exist before they can be guarded.

## Test plan

| Level | File | Intent |
|-------|------|--------|
| Unit | `src/auth.test.ts` | password hashing, token signing/verification |
| Integration | `tests/auth-flow.spec.ts` | signup → signin → authenticated CRUD |

## Required checks

- [ ] `npm test` — must pass (or your test command)
- [ ] `npm run lint` — no new warnings (or your lint command)
- [ ] `npm run typecheck` — no type errors (or your typecheck command)
- [ ] Docs updated (auth section in API docs)

## Acceptance criteria

- [ ] Signup creates a user with hashed password
- [ ] Signin returns a valid session token
- [ ] Unauthenticated requests to `/todos/*` return 401
- [ ] Users can only access their own todos (cross-user access returns 404)
- [ ] All tests pass
- [ ] Status set to `done` in both `backlog.md` and this file (same commit)

## Traceability

- Phase: [A-P1](../phases/A-P1.md)
- ADR: pending — auth provider decision
- Related items: [A-B1](A-B1.md)

## Notes

This item is the example of a `blocked` status: scope is defined, the team is ready, but a hard upstream decision (the auth provider ADR) must land first. Status will move to `ready` once the ADR is accepted.
