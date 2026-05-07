# Megaplan — Simple Todo API

## Vision

A RESTful Todo API that allows users to create, read, update, and delete todo items. The API supports pagination for listing todos and follows REST conventions.

## Delivery model

Cycle 0 scaffolds the project with database and CI. Cycle A delivers the first production domain: Todo CRUD.

- Cycle 0: Project scaffold, database schema, CI/CD
- Cycle A: Todo CRUD operations and list with pagination

## Phase workflow

document (pre) → red → green → blue → document (post) → COMPLETE

## Cycles

### Cycle 0 — Scaffold
Status: COMPLETE

Scope: Project setup, database schema, CI pipeline, basic tooling

### Cycle A — Todo Domain
Status: IN PROGRESS

Scope: Todo CRUD operations, list with pagination

| Phase | Title | Status |
|-------|-------|--------|
| 0-P1 | Scaffold | done |
| A-P1 | Todo CRUD | in-progress |

## Errata

- 2026-05-01: Initial project setup with Node.js, PostgreSQL, Prisma ORM