---
type: architecture
module: <module-slug>
b_item_refs: [<CYCLE>-B<N>]
adr_refs: []
glossary_terms: []
updated_at_commit: <short-sha>
stability: evolving
---

# Architecture: <Module Name>

> AI-targeted. Derived/disposable — if this disagrees with the code or a source
> doc, the source wins. Re-ingest at `document (post)`.

## Responsibility
[One paragraph: what this module owns and what it deliberately does not.]

## Boundaries
- Depends on: [modules/services]
- Depended on by: [modules/services]

## Key symbols
[Reference symbol names, never line ranges — line numbers rot on every edit.]

| Symbol | File | Role |
|--------|------|------|
| `ClassOrFunc` | `src/path/file.ext` | what it does |

## Data flow
[Optional: short prose or a mermaid diagram of the main path through the module.]
