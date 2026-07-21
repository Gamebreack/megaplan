#!/usr/bin/env python3
"""Shared markdown-parsing helpers for the Megaplan scripts.

Previously `parse_markdown_section` / `parse_metadata_table` / `extract_id` /
`find_repo_root` were copied into compile_spec.py, verify_workflow.py and
validate_backlog.py. They now live here so there is a single source of truth.

Behavior is preserved verbatim for the existing callers. The only additions are
opt-in (`warn=True`) stderr warnings on a missed section lookup and a
`parse_front_matter` helper used by the AI wiki tooling.
"""
import os
import re
import sys


def find_repo_root(start=None):
    """Walk upward from `start` (default: cwd) until a repo marker is found.

    compile_spec.py historically started from the script directory; the other
    scripts started from the current working directory. Pass `start` explicitly
    to preserve each caller's original behavior.
    """
    if start is None:
        start = os.getcwd()
    current = os.path.abspath(start)
    while current != os.path.dirname(current):
        if os.path.exists(os.path.join(current, "AGENTS.md")) or os.path.exists(
            os.path.join(current, ".git")
        ):
            return current
        current = os.path.dirname(current)
    return os.path.abspath(os.getcwd())


def parse_markdown_section(content, section_name, warn=False):
    """Extract the body of a markdown section identified by heading name.

    Returns "" when the section is absent. Set `warn=True` to emit a stderr
    warning on a miss (used by the wiki scanners, which touch many file shapes);
    existing callers keep `warn=False` so their output is unchanged.
    """
    lines = content.split("\n")
    section_lines = []
    in_section = False
    in_code_block = False
    section_level = None

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block

        if not in_code_block:
            match = re.match(r"^(#+)\s+(.+)$", line)
            if match:
                level = len(match.group(1))
                name = match.group(2).strip()
                name_clean = re.sub(r"[*_`]", "", name).strip().lower()

                if name_clean == section_name.lower():
                    in_section = True
                    section_level = level
                    continue
                elif in_section and level <= section_level:
                    break

        if in_section:
            section_lines.append(line)

    if in_section:
        return "\n".join(section_lines).strip()

    if warn:
        print(
            f"warning: markdown section '{section_name}' not found", file=sys.stderr
        )
    return ""


def parse_metadata_table(content):
    """Parse the `## Metadata` pipe-table into a dict (values kept as-authored)."""
    lines = content.split("\n")
    in_metadata = False
    in_code_block = False
    metadata = {}

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
        if in_code_block:
            continue
        match = re.match(r"^(#+)\s+(.+)$", line)
        if match:
            name = re.sub(r"[*_`]", "", match.group(2).strip()).lower()
            if name == "metadata":
                in_metadata = True
                continue
            elif in_metadata:
                break
        if in_metadata and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            if len(cells) >= 2:
                field = re.sub(r"[*_`]", "", cells[0]).strip().lower()
                value = re.sub(r"[*_`]", "", cells[1]).strip()
                if field not in ("field",) and not re.match(r"^:?-+:?$", field):
                    metadata[field] = value

    return metadata


def parse_detail_metadata(detail_path):
    """Parse a detail file's Metadata table, lowercasing values.

    Distinct from `parse_metadata_table`: this reads from a path, extracts the
    Metadata section first, and lowercases values (validate_backlog.py relies on
    the lowercasing for status/workflow-step comparisons).
    """
    if not os.path.exists(detail_path):
        return {}
    with open(detail_path, "r", encoding="utf-8") as f:
        content = f.read()

    metadata_table = parse_markdown_section(content, "Metadata")
    if not metadata_table:
        return {}

    result = {}
    for line in metadata_table.split("\n"):
        line_str = line.strip()
        if line_str.startswith("|"):
            cells = [c.strip() for c in line_str.split("|")[1:-1]]
            if len(cells) >= 2:
                field = re.sub(r"[*_`]", "", cells[0]).strip().lower()
                value = re.sub(r"[*_`]", "", cells[1]).strip()
                if field == "field" or re.match(r"^:-*-*|-*-*:-*|-*-*$", field):
                    continue
                result[field] = value.lower()
    return result


def extract_id(content, filepath):
    """Return the B-item/Bug ID from the h1 title, falling back to the filename."""
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        id_match = re.match(
            r"^([a-zA-Z0-9]+-B[0-9]+(?:\.B[0-9]+)?)", re.sub(r"[*_`]", "", title)
        )
        if id_match:
            return id_match.group(1)
    return os.path.splitext(os.path.basename(filepath))[0]


def parse_front_matter(content):
    """Parse a leading YAML-ish front-matter block (`---` … `---`).

    Supports the small subset the wiki pages use: `key: value` and
    `key: [a, b, c]` inline lists. stdlib only — no external YAML dependency,
    matching the repo's zero-dependency posture. Returns ({}, content) when no
    front-matter block is present, otherwise (metadata_dict, remaining_body).
    """
    if not content.startswith("---"):
        return {}, content

    lines = content.split("\n")
    if lines[0].strip() != "---":
        return {}, content

    meta = {}
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if not m:
            continue
        key = m.group(1).strip().lower()
        raw = m.group(2).strip()
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            items = [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
            meta[key] = items
        else:
            meta[key] = raw.strip("'\"")

    if end_idx is None:
        # No closing delimiter — treat as a normal document, not front-matter.
        return {}, content

    body = "\n".join(lines[end_idx + 1 :])
    return meta, body
