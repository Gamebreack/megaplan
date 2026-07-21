#!/usr/bin/env python3
"""Deterministic file-to-wiki-page mapping for Layer 3 ingestion.

`suggest_pages(repo_root, touched_files)` is the *deterministic half* of Layer 3:
given a list of repo-relative file paths, it returns a list of
`(wiki_relpath, [h2_anchors])` tuples suggesting which wiki pages the agent
should patch at `document (post)`. The function has no judgment; re-runs are
idempotent. The agent decides what to do with each suggestion (recorded under
`manifest.items[<id>].pages`).

Module-slug derivation rules (in priority order):

1. Test directory or `test_` prefix → strip and recurse on the remainder.
2. Path starts with a SOURCE_ROOT (`src`, `lib`, `app`, `pkg`, `internal`, `cmd`) →
   the next component is the slug, with the `internal` middle component skipped.
3. Otherwise → use the parent directory name. If the file is at the repo root,
   use the file stem (without extension).

Page matching for each touched file's slug:

1. `wiki/architecture/<slug>.md` if it exists.
2. `wiki/notes/<slug>.md` if it exists.
3. `wiki/contracts/<api>.md` ONLY if the file matches the contract heuristic
   (filename contains `route|endpoint|api|schema|graphql|openapi`, or path
   contains `routes/`, `api/`, `endpoints/`, `schema/`) and the contract page
   exists.
"""
import os
import re
from typing import List, Optional, Tuple

Suggestion = Tuple[str, List[str]]

SOURCE_ROOTS = ("src", "lib", "app", "pkg", "internal", "cmd")
WIKI_SUBDIRS = ("architecture", "notes", "contracts")
WIKI_REL = os.path.join("docs", "megaplan", "wiki")

CONTRACT_FILENAME_RE = re.compile(
    r"(route|endpoint|api|schema|graphql|openapi)", re.IGNORECASE
)
CONTRACT_PATH_RE = re.compile(r"(?:^|/)(routes|api|endpoints|schema)/")
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _derive_module_slug(path: str) -> Optional[str]:
    """Return the module slug for a repo-relative path, or None if no slug."""
    parts = [p for p in path.replace("\\", "/").split("/") if p]
    if not parts:
        return None

    # Rule 1: test directory or test_ prefix
    if parts[0] in ("tests", "test"):
        rest = parts[1:]
        if rest and rest[0].startswith("test_"):
            rest[0] = rest[0][5:]
        return _derive_module_slug("/".join(rest)) if rest else None

    # Rule 2: source root
    if parts[0] in SOURCE_ROOTS:
        if len(parts) == 1:
            return None
        # Drop the `internal` middle component if present.
        if len(parts) > 2 and parts[1] == "internal":
            return parts[2]
        return parts[1]

    # Rule 3: parent dir name, or file stem if at root
    if len(parts) == 1:
        stem = parts[0].rsplit(".", 1)[0] if "." in parts[0] else parts[0]
        return stem or None
    return parts[-2]


def _is_contract_file(path: str) -> bool:
    """True if `path` matches the contract heuristic."""
    norm = path.replace("\\", "/")
    if CONTRACT_FILENAME_RE.search(norm.rsplit("/", 1)[-1]):
        return True
    return bool(CONTRACT_PATH_RE.search(norm))


def _extract_h2_headings(file_path: str) -> List[str]:
    """Return a list of H2 heading names from a markdown file, or [] if missing."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return H2_RE.findall(f.read())


def _contract_slug(path: str) -> Optional[str]:
    """Return the contract-page slug for a contract file, or None.

    Heuristic: take the directory name that contains the contract keyword
    (e.g., `routes/`, `api/`, `endpoints/`, `schema/`). Falls back to the
    file's module slug if no keyword directory is found.
    """
    m = CONTRACT_PATH_RE.search(path.replace("\\", "/"))
    if m:
        return m.group(1)
    return _derive_module_slug(path)


def _wiki_rel(sub: str, slug: str) -> str:
    return os.path.join(WIKI_REL, sub, f"{slug}.md")


def _sort_key(rel: str) -> Tuple[int, str]:
    for i, sub in enumerate(WIKI_SUBDIRS):
        if rel.startswith(os.path.join(WIKI_REL, sub)):
            return (i, rel)
    return (len(WIKI_SUBDIRS), rel)


def suggest_pages(repo_root: str, touched_files: List[str]) -> List[Suggestion]:
    """Return a deterministic list of (wiki_relpath, [h2_anchors]) suggestions.

    `touched_files` is a list of repo-relative paths. Tuples are returned in
    the order: per-slug, architecture → notes → contract. Multiple touched
    files in the same module collapse to a single architecture/notes
    suggestion (the function deduplicates by wiki_relpath).
    """
    if not touched_files:
        return []
    if not os.path.isdir(os.path.join(repo_root, WIKI_REL)):
        return []

    seen: "dict[str, List[str]]" = {}

    for path in touched_files:
        slug = _derive_module_slug(path)
        if slug:
            for rel in (_wiki_rel("architecture", slug), _wiki_rel("notes", slug)):
                if rel not in seen and os.path.exists(os.path.join(repo_root, rel)):
                    seen[rel] = _extract_h2_headings(os.path.join(repo_root, rel))

        if _is_contract_file(path):
            cslug = _contract_slug(path)
            if cslug:
                rel = _wiki_rel("contracts", cslug)
                if rel not in seen and os.path.exists(os.path.join(repo_root, rel)):
                    seen[rel] = _extract_h2_headings(os.path.join(repo_root, rel))

    return [(rel, seen[rel]) for rel in sorted(seen, key=_sort_key)]
