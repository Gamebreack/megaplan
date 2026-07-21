#!/usr/bin/env python3
"""Structural validation for the AI wiki (docs/megaplan/wiki/).

Verifies STRUCTURE, not TRUTH. It cannot tell whether an authored page correctly
describes the code — only that the manifest is well-formed, front-matter parses,
and cross-references resolve. Prose fidelity is an accepted, documented residual
risk (see docs/methodology.md, Layer 3).

Errors block; warnings are advisory (heuristic dangling-reference checks that may
false-positive). Importable via `validate_wiki(repo_root) -> (errors, warnings)`.

Usage:
    python scripts/validate_wiki.py [project_root]
"""
import json
import os
import re
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from _mdparse import parse_front_matter

WIKI_REL = os.path.join("docs", "megaplan", "wiki")
AUTHORED_DIRS = ("architecture", "contracts", "decisions", "notes")
SOURCE_ROOTS = ("src", "lib", "app", "pkg", "internal", "cmd", "tests", "test")


def _iter_pages(wiki_dir):
    for sub in AUTHORED_DIRS:
        d = os.path.join(wiki_dir, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.endswith(".md"):
                yield os.path.join(d, name)


def _item_exists(repo_root, item_id):
    path = os.path.join(
        repo_root, "docs", "megaplan", "backlog-items", f"{item_id}.md"
    )
    return os.path.exists(path)


def _adr_exists(repo_root, adr_ref):
    # Accept "ADR-001" or "ADR-001.md" or a filename.
    name = adr_ref if adr_ref.endswith(".md") else adr_ref + ".md"
    return os.path.exists(os.path.join(repo_root, "docs", "megaplan", "adr", name))


def _check_manifest(repo_root, wiki_dir, errors):
    manifest_path = os.path.join(wiki_dir, "_meta", "manifest.json")
    if not os.path.exists(manifest_path):
        return  # manifest is created on first ingestion; absence is not an error
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        errors.append(f"manifest.json is not valid JSON: {e}")
        return
    if not isinstance(data, dict) or not isinstance(data.get("items"), dict):
        errors.append("manifest.json must be an object with an 'items' object.")
        return
    for item_id, entry in data["items"].items():
        if not isinstance(entry, dict):
            errors.append(f"manifest item '{item_id}' must be an object.")
            continue
        if "updated_at_commit" not in entry:
            errors.append(f"manifest item '{item_id}' missing 'updated_at_commit'.")
        for page in entry.get("pages", []) or []:
            if not os.path.exists(os.path.join(wiki_dir, page)):
                errors.append(
                    f"manifest item '{item_id}' lists page '{page}' that does not exist."
                )
        for adr in entry.get("adr_refs", []) or []:
            if not _adr_exists(repo_root, adr):
                errors.append(
                    f"manifest item '{item_id}' references '{adr}', which has no ADR file."
                )


def _check_pages(repo_root, wiki_dir, errors, warnings):
    for page_path in _iter_pages(wiki_dir):
        rel = os.path.relpath(page_path, wiki_dir)
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()
        meta, body = parse_front_matter(content)
        if not meta:
            errors.append(f"wiki page '{rel}' has no parseable YAML front-matter.")
            continue
        for ref in meta.get("b_item_refs", []) or []:
            if ref and not _item_exists(repo_root, ref):
                errors.append(
                    f"wiki page '{rel}' references B-item '{ref}', which has no detail file."
                )
        for adr in meta.get("adr_refs", []) or []:
            if adr and not _adr_exists(repo_root, adr):
                errors.append(
                    f"wiki page '{rel}' references '{adr}', which has no ADR file."
                )
        # Heuristic dangling-source-path check (advisory).
        for token in re.findall(r"`([\w./-]+\.\w+)`", body):
            norm = token.replace("\\", "/")
            first = norm.split("/", 1)[0]
            if "/" in norm and first in SOURCE_ROOTS:
                if not os.path.exists(os.path.join(repo_root, norm)):
                    warnings.append(
                        f"wiki page '{rel}' cites source path '{norm}', "
                        "which no longer exists (possible drift)."
                    )


def validate_wiki(repo_root):
    """Return (errors, warnings). Empty errors == structurally valid."""
    errors, warnings = [], []
    wiki_dir = os.path.join(repo_root, WIKI_REL)
    if not os.path.isdir(wiki_dir):
        return errors, warnings  # opt-in: no wiki, nothing to validate
    _check_manifest(repo_root, wiki_dir, errors)
    _check_pages(repo_root, wiki_dir, errors, warnings)
    return errors, warnings


def main():
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    errors, warnings = validate_wiki(os.path.abspath(project_root))
    for w in warnings:
        print(f"  ! {w}", file=sys.stderr)
    if errors:
        print("AI wiki validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    print("AI wiki validation passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
