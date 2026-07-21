# AI Wiki — <Project Name>

> **AI-targeted documentation.** Machine-maintained context store for the coding
> agent. It is **derived and disposable**: if the wiki disagrees with the code or
> a human-facing source doc (`backlog-items/`, `glossary.md`, `adr/`), the source
> wins and the wiki is stale — re-ingest at `document (post)`.
>
> Humans read `docs/methodology.md`, `AGENTS.md`, `backlog.md`, `glossary.md`,
> `adr/`. Agents read this to load accumulated project context at session start.

## Layout

| Path | Contents |
|------|----------|
| `architecture/<module>.md` | Module map, boundaries, key symbols |
| `contracts/<api>.md` | Endpoint/interface/schema lookup tables |
| `decisions/<CYCLE>-B<N>.md` | Decision digests (link to canonical ADR) |
| `notes/<module>.md` | Gotchas, non-obvious coupling, dead-ends tried |
| `glossary-links.md` | term → wiki pages → code → B-items cross-index |
| `_meta/manifest.json` | Per-B-item ingestion record (touched files, commit) |
| `_meta/ingestion.log` | Append-only ingestion history |

## Pages
[Regenerate/update this list during ingestion.]
