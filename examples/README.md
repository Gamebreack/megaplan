# Megaplan Examples

This directory contains a complete, filled-out example of a Megaplan-enabled project.

## What this is

A simple Todo API project demonstrating:
- Cycle 0 (Scaffold): Project setup + database schema
- Cycle A (Todo domain): CRUD operations + list with pagination

The example shows how Megaplan looks in practice: real cycles, backlog items, and status values.

## How to read it

Start with `docs/megaplan/megaplan.md` to see the overall roadmap, then:
1. `backlog.md` — Global index with all items
2. `backlog-items/` — Individual item details

## Status values in this example

| Status | Items | Meaning |
|--------|-------|---------|
| `done` | 0-B1, 0-B2 | Completed work |
| `in-progress` | A-B1 | Currently being worked on |
| `ready` | A-B2 | Queued, waiting for A-B1 |
| `pending` | — | Not yet scoped |
| `blocked` | — | Waiting on dependency |
| `superseded` | — | Replaced by newer approach |

## What to notice

- **Dual-update discipline**: Each done item has status updated in both `backlog.md` (index) and the detail file
- **Cycle gating**: Cycle A cannot start until Cycle 0 is complete
- **Workflow progression**: A-B1 follows document → red → green → blue → document → COMPLETE

## Adding your own example

Want to add another example project? Create a new directory under `examples/` with the same structure.
