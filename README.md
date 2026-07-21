# Megaplan

A plan-tracking skill for AI agent harnesses. Gives agents the roadmap, backlog, and workflow they need to deliver software incrementally — without losing coherence across sessions.

## Why it exists

AI agents start with zero memory each session. Megaplan fixes that by encoding *what was decided*, *why*, and *what still needs to happen* into files the agent reads at the start of every task.

## How it works

**Cycles → B-items.** A Cycle is a major milestone (Cycle 0 scaffolds the project; Cycle A delivers the first domain; and so on). Each cycle contains sequenced B-items — the atomic unit of work.

**The workflow is mandatory.** Every B-item follows: `document (pre) → red → green → blue → document (post) → COMPLETE`. No production code before a failing test. No closing an item without updating docs.

**Dual-update discipline.** Every status change updates both the global `backlog.md` index and the individual B-item detail file in the same commit. Drift between the two is a documentation bug.

See `docs/methodology.md` for the full reference.

## Quick start

Run this in your project directory (any git repo):

```bash
curl -sSL https://raw.githubusercontent.com/Gamebreack/megaplan/main/scripts/bootstrap.py | python3 -
```

That lays out `AGENTS.md` at the root, `docs/megaplan/` with the four core templates (plus the wiki templates if you opt in), the framework scripts under `scripts/megaplan/`, and the pre-commit hook. The bootstrap resolves the **latest version** automatically from the GitHub Releases API; pin a specific version with `--ref v2.0.0` if you need to.

Verify the install any time:

```bash
python scripts/megaplan/verify_workflow.py --selftest
# expected: "selftest OK: Megaplan install is internally consistent."
```

### Windows (PowerShell 5+)

```powershell
powershell -c "irm https://raw.githubusercontent.com/Gamebreack/megaplan/main/scripts/bootstrap.ps1 | iex"
```

Prerequisites: **Python 3.10+** (for running the framework scripts), **Git for Windows** (for the pre-commit hook, which requires Git Bash), and **PowerShell 5+** (included with Windows 10/11).

> **Limitations:** The pre-commit hook is a bash script and requires Git Bash (installed by default with Git for Windows). PowerShell-native git hooks are not supported. If Python is not on your PATH, the bootstrap prints a warning and skips the self-test — install Python first, then run the verification manually.

```bash
python scripts/megaplan/verify_workflow.py --selftest
```

### Flags

| Flag | What it does |
|------|--------------|
| `--with-wiki` | Also lay out the opt-in AI wiki templates (`docs/megaplan/wiki/`) |
| `--force` | Overwrite existing files (default: skip, with a warning) |
| `--ref v2.0.0` | Pin a specific version (tag or branch name) |
| `--project-dir PATH` | Install into a different directory (default: current) |
| `--from-local PATH` | Use a local framework checkout instead of downloading (testing/dev) |
| `--skip-hook` | Skip the pre-commit hook install |
| `--skip-self-test` | Skip the self-test at the end (not recommended) |

Re-running the bootstrap is idempotent: existing files are skipped (with a warning), the existing pre-commit hook is preserved unless `--force` is passed.

### Passing flags

Pass flags through the pipe by using `python3 -`:

```bash
curl -sSL https://raw.githubusercontent.com/Gamebreack/megaplan/main/scripts/bootstrap.py | python3 - --ref v2.0.0
```

### Troubleshooting

- **`Error: <dir> is not a git repository`** — Run `git init` first, or pass `--skip-hook` to install without the hook.
- **`warning: could not reach GitHub Releases API`** — Network blocked or rate-limited; the bootstrap fell back to `main` (unstable). Pass `--ref v2.0.0` to pin a stable version.
- **`Self-test: FAILED`** — Run `python scripts/megaplan/verify_workflow.py --selftest` for the specific missing files. The most common cause is a partial lay-out from a previous interrupted run; re-run the bootstrap.
- **Python version** — Megaplan requires Python 3.10+ (3.12+ recommended for the secure tarfile filter; 3.9-3.11 falls back to a manual path-traversal check). Check with `python3 --version`.

## Harness compatibility

After the bootstrap, your `AGENTS.md` is at the project root. Different harnesses pick it up differently:

| Harness | How it picks up `AGENTS.md` |
|---------|-----------------------------|
| **OpenCode** | Loaded automatically from the project root |
| **Hermes Agent** | Loaded automatically, or `hermes skills install Gamebreack/megaplan` |
| **Claude Code** | Create `CLAUDE.md` with `@AGENTS.md`, or symlink: `ln -s AGENTS.md CLAUDE.md` |
| **Cursor** | AGENTS.md is auto-loaded; or create `.cursorrules` with `cat AGENTS.md >> .cursorrules` |
| **Aider** | Read AGENTS.md via `--read` flag or `CONVENTIONS.md` symlink |
| **Windsurf** | AGENTS.md is auto-loaded; or rename to `.windsurfrules` |
| **GitHub Copilot** | AGENTS.md is loaded via `.github/copilot-instructions.md` symlink: `ln -s ../../AGENTS.md .github/copilot-instructions.md` |

## Marketplace install

You can also install Megaplan via AI coding tool marketplaces:

| Harness | How to install |
|---------|----------------|
| **Hermes Agent** | `hermes skills install Gamebreack/megaplan` |
| **OpenCode** | Manual install: copy the files to `.opencode/skills/megaplan/` (marketplace integration coming) |

## File inventory

| Path | Purpose |
|------|---------|
| `AGENTS.md` | The skill — copied to your project root by the bootstrap |
| `templates/megaplan.md` | Starter for your project root plan |
| `templates/backlog.md` | Starter for your backlog index |
| `templates/glossary.md` | Starter for your domain glossary |
| `templates/backlog-item.md` | Starter for each B-item detail file |
| `templates/adr.md` | Starter for Architecture Decision Records (ADRs) |
| `templates/wiki/` | AI wiki templates (opt-in) |
| `scripts/bootstrap.py` | The dumb-install bootstrap (one-line install, Linux/macOS) |
| `scripts/bootstrap.ps1` | The dumb-install bootstrap (one-line install, Windows PowerShell 5+) |
| `scripts/compile_spec.py` | Compile a B-item into `SPEC.md` |
| `scripts/validate_backlog.py` | Verify backlog integrity and cycle sync |
| `scripts/verify_workflow.py` | Workflow gate enforcement + `--selftest` |
| `scripts/ingest_wiki.py` | Layer 3 wiki ingestion |
| `scripts/validate_wiki.py` | Layer 3 wiki structural validation |
| `scripts/_mdparse.py`, `scripts/_wiki_map.py` | Shared helpers |
| `scripts/setup_hooks.py` | Pre-commit hook installer |
| `docs/methodology.md` | Full methodology reference |
| `examples/simple-todo-api/` | Complete example: Todo API with Cycle 0 (scaffold) and Cycle A (CRUD) |

---

v2.0.0
