#!/usr/bin/env python3
"""Deterministic half of Layer 3 wiki ingestion.

Records, for a B-item, which files changed and at what commit — the bookkeeping
an agent then uses at `document (post)` to know which wiki pages to patch. Pure
git/JSON work; no judgment, no LLM. Idempotent: re-running for the same item
refreshes its record without touching other items or the agent-authored `pages`.

Usage:
    python scripts/ingest_wiki.py <path_to_b_item.md>
"""
import json
import os
import subprocess
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from _mdparse import extract_id, find_repo_root

WIKI_REL = os.path.join("docs", "megaplan", "wiki")


def git(args, cwd):
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except Exception:
        return None


def head_sha(repo_root):
    out = git(["rev-parse", "--short", "HEAD"], repo_root)
    return out.strip() if out else None


def commit_exists(repo_root, sha):
    return git(["cat-file", "-e", sha + "^{commit}"], repo_root) is not None


def earliest_commit_for_id(repo_root, item_id):
    """Parent of the earliest commit whose message references the item ID."""
    out = git(
        ["log", "--all", "--format=%H", "--grep", item_id, "--reverse"], repo_root
    )
    if not out or not out.strip():
        return None
    earliest = out.strip().split("\n")[0]
    parent = git(["rev-parse", earliest + "^"], repo_root)
    return parent.strip() if parent else earliest


def changed_files(repo_root, since):
    files = set()
    # Uncommitted (staged + unstaged + untracked-tracked-by-status).
    status = git(["status", "--porcelain"], repo_root)
    if status:
        for line in status.split("\n"):
            if not line.strip():
                continue
            path = line[3:].strip()
            if " -> " in path:  # rename
                path = path.split(" -> ", 1)[1].strip()
            files.add(path)
    # Committed range, if we have a starting point.
    if since:
        diff = git(["diff", "--name-only", since, "HEAD"], repo_root)
        if diff:
            files.update(p for p in diff.split("\n") if p.strip())
    return files


def is_noise(path):
    """Exclude self-referential and compiled artifacts from touched_files."""
    norm = path.replace("\\", "/")
    if norm.startswith(WIKI_REL.replace("\\", "/")):
        return True
    if norm == "SPEC.md" or norm.endswith("/SPEC.md"):
        return True
    if "__pycache__/" in norm or norm.endswith(".pyc"):
        return True
    return False


def load_manifest(manifest_path):
    if not os.path.exists(manifest_path):
        return {"items": {}}
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "items" not in data:
            return {"items": {}}
        return data
    except (json.JSONDecodeError, OSError):
        print(
            "warning: manifest.json unreadable/corrupt — starting a fresh manifest",
            file=sys.stderr,
        )
        return {"items": {}}


def ingest(b_item_path):
    b_item_path = os.path.abspath(b_item_path)
    if not os.path.exists(b_item_path):
        print(f"Error: B-item file not found: {b_item_path}", file=sys.stderr)
        return 1

    repo_root = find_repo_root(start=os.path.dirname(b_item_path))
    wiki_dir = os.path.join(repo_root, WIKI_REL)
    if not os.path.isdir(wiki_dir):
        print(
            f"Error: AI wiki not initialized (no {WIKI_REL}/). "
            "Create the directory to opt in before ingesting.",
            file=sys.stderr,
        )
        return 1

    with open(b_item_path, "r", encoding="utf-8") as f:
        item_id = extract_id(f.read(), b_item_path)

    meta_dir = os.path.join(wiki_dir, "_meta")
    os.makedirs(meta_dir, exist_ok=True)
    manifest_path = os.path.join(meta_dir, "manifest.json")
    manifest = load_manifest(manifest_path)

    prior = manifest["items"].get(item_id, {})
    since = prior.get("updated_at_commit")
    if since and not commit_exists(repo_root, since):
        since = None
    if not since:
        since = earliest_commit_for_id(repo_root, item_id)

    touched = sorted(p for p in changed_files(repo_root, since) if not is_noise(p))
    sha = head_sha(repo_root) or "unknown"

    entry = dict(prior)
    entry["touched_files"] = touched
    entry["updated_at_commit"] = sha
    entry.setdefault("pages", [])  # agent fills these when it patches wiki pages
    entry.setdefault("adr_refs", [])
    manifest["items"][item_id] = entry

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")

    log_path = os.path.join(meta_dir, "ingestion.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{sha}\t{item_id}\t{len(touched)} file(s)\n")

    print(
        f"Ingested {item_id}: {len(touched)} touched file(s) recorded at {sha}.\n"
        f"Next: patch the affected wiki pages for these files, then list them "
        f"under items['{item_id}'].pages in {os.path.relpath(manifest_path, repo_root)}."
    )
    return 0


def main():
    if len(sys.argv) != 2:
        print("Usage: ingest_wiki.py <path_to_b_item.md>", file=sys.stderr)
        sys.exit(1)
    sys.exit(ingest(sys.argv[1]))


if __name__ == "__main__":
    main()
