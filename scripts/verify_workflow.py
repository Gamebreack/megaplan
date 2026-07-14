#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import subprocess
import sys


WORKFLOW_STEPS = ["document-pre", "red", "green", "blue", "document-post", "complete"]
STEP_DISPLAY = {
    "document-pre": "document (pre)",
    "red": "red",
    "green": "green",
    "blue": "blue",
    "document-post": "document (post)",
    "complete": "COMPLETE",
}


def find_repo_root():
    current = os.path.abspath(os.getcwd())
    while current != os.path.dirname(current):
        if os.path.exists(os.path.join(current, "AGENTS.md")) or os.path.exists(
            os.path.join(current, ".git")
        ):
            return current
        current = os.path.dirname(current)
    return os.path.abspath(os.getcwd())


def command_exists(cmd):
    first_word = cmd.split()[0]
    return shutil.which(first_word) is not None


def get_tool_type(cmd):
    parts = cmd.split()
    if not parts:
        return None
    first = parts[0]
    if first == "python" and len(parts) > 2 and parts[1] == "-m":
        return parts[2]
    return first


def is_project_type(tool_type, repo_root):
    if tool_type == "npm":
        return os.path.exists(os.path.join(repo_root, "package.json"))
    elif tool_type == "cargo":
        return os.path.exists(os.path.join(repo_root, "Cargo.toml"))
    elif tool_type == "go":
        return os.path.exists(os.path.join(repo_root, "go.mod"))
    elif tool_type in ("pytest", "python", "ruff"):
        for filename in [
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "tox.ini",
            "pytest.ini",
        ]:
            if os.path.exists(os.path.join(repo_root, filename)):
                return True
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in ("venv", ".venv", "env")
            ]
            if any(f.endswith(".py") for f in files):
                return True
        return False
    elif tool_type == "eslint":
        for filename in [
            ".eslintrc",
            ".eslintrc.json",
            ".eslintrc.js",
            "eslint.config.js",
            "package.json",
        ]:
            if os.path.exists(os.path.join(repo_root, filename)):
                return True
        return False
    return True


def parse_metadata_table(content):
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


def parse_markdown_section(content, section_name):
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
                name = re.sub(r"[*_`]", "", match.group(2).strip()).lower()
                if name == section_name.lower():
                    in_section = True
                    section_level = level
                    continue
                elif in_section and level <= section_level:
                    break
        if in_section:
            section_lines.append(line)

    if in_section:
        return "\n".join(section_lines).strip()
    return ""


def extract_id(content, filepath):
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        id_match = re.match(
            r"^([a-zA-Z0-9]+-B[0-9]+(?:\.B[0-9]+)?)", re.sub(r"[*_`]", "", title)
        )
        if id_match:
            return id_match.group(1)
    return os.path.splitext(os.path.basename(filepath))[0]


def get_workflow_step(metadata):
    raw = metadata.get("workflow step", "").strip().lower()
    if raw in ("—", "-", ""):
        return None
    normalized = raw.replace(" ", "-").replace("_", "-")
    if normalized == "document-(pre)":
        normalized = "document-pre"
    elif normalized == "document-(post)":
        normalized = "document-post"
    return normalized


def get_next_step(current_step):
    try:
        idx = WORKFLOW_STEPS.index(current_step)
        if idx < len(WORKFLOW_STEPS) - 1:
            return WORKFLOW_STEPS[idx + 1]
    except ValueError:
        pass
    return None


def run_command(cmd, cwd=None):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=120, cwd=cwd
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out after 120 seconds"
    except Exception as e:
        return False, "", str(e)


def check_layer1_spec(b_item_path, repo_root):
    errors = []
    spec_path = os.path.join(repo_root, "SPEC.md")

    if not os.path.exists(spec_path):
        errors.append(
            "Layer 1 FAIL: SPEC.md not found at project root. "
            "Run: python scripts/compile_spec.py " + b_item_path
        )
        return errors

    try:
        with open(spec_path, "r", encoding="utf-8") as f:
            spec_content = f.read()
        expected_source = os.path.basename(b_item_path)
        if expected_source not in spec_content:
            errors.append(
                f"Layer 1 FAIL: SPEC.md does not correspond to the current B-item '{expected_source}'. "
                "Re-run: python scripts/compile_spec.py " + b_item_path
            )
            return errors
    except Exception as e:
        errors.append(f"Layer 1 FAIL: Could not read SPEC.md: {e}")
        return errors

    spec_mtime = os.path.getmtime(spec_path)
    item_mtime = os.path.getmtime(b_item_path)

    if item_mtime > spec_mtime:
        errors.append(
            "Layer 1 FAIL: SPEC.md is stale (source B-item was modified after compilation). "
            "Re-run: python scripts/compile_spec.py " + b_item_path
        )

    return errors


def check_layer2_verifier(repo_root, skip_stages=None):
    errors = []
    skip_stages = skip_stages or []

    if "test" not in skip_stages:
        for cmd in [
            "npm test",
            "pytest",
            "cargo test",
            "go test ./...",
            "python -m pytest",
        ]:
            tool_type = get_tool_type(cmd)
            if tool_type and not is_project_type(tool_type, repo_root):
                continue
            if not command_exists(cmd):
                continue
            success, stdout, stderr = run_command(cmd, cwd=repo_root)
            if success:
                break
            else:
                errors.append(f"Layer 2 Stage 1 FAIL: Tests failed ({cmd})")
                break

    if "lint" not in skip_stages:
        for cmd in ["npm run lint", "ruff check .", "eslint .", "cargo clippy"]:
            tool_type = get_tool_type(cmd)
            if tool_type and not is_project_type(tool_type, repo_root):
                continue
            if not command_exists(cmd):
                continue
            success, stdout, stderr = run_command(cmd, cwd=repo_root)
            if success:
                break
            else:
                errors.append(
                    f"Layer 2 Stage 2 FAIL: Lint/static analysis failed ({cmd})"
                )
                break

    if "docs" not in skip_stages:
        glossary_path = os.path.join(repo_root, "docs", "megaplan", "glossary.md")
        glossary_map_path = os.path.join(
            repo_root, "docs", "megaplan", "glossary-map.md"
        )
        if not os.path.exists(glossary_path) and not os.path.exists(glossary_map_path):
            errors.append(
                "Layer 2 Stage 3 FAIL: Neither docs/megaplan/glossary.md nor docs/megaplan/glossary-map.md was found"
            )

    return errors


def check_layer3_ingestion(repo_root, b_item_path):
    errors = []

    backlog_path = os.path.join(repo_root, "docs", "megaplan", "backlog.md")
    if not os.path.exists(backlog_path):
        errors.append("Layer 3 FAIL: docs/megaplan/backlog.md not found")

    glossary_path = os.path.join(repo_root, "docs", "megaplan", "glossary.md")
    glossary_map_path = os.path.join(repo_root, "docs", "megaplan", "glossary-map.md")
    if not os.path.exists(glossary_path) and not os.path.exists(glossary_map_path):
        errors.append(
            "Layer 3 FAIL: Neither docs/megaplan/glossary.md nor docs/megaplan/glossary-map.md was found"
        )

    item_id = None
    if os.path.exists(b_item_path):
        with open(b_item_path, "r", encoding="utf-8") as f:
            item_id = extract_id(f.read(), b_item_path)

    if item_id and os.path.exists(backlog_path):
        with open(backlog_path, "r", encoding="utf-8") as f:
            backlog_content = f.read()
        if not re.search(r"\b" + re.escape(item_id) + r"\b", backlog_content):
            errors.append(
                f"Layer 3 FAIL: B-item {item_id} not found in backlog.md (dual-update violation)"
            )

    return errors


def check_step_gate(current_step, b_item_path, repo_root, run_verifier=False):
    errors = []

    if current_step == "document-pre":
        spec_errors = check_layer1_spec(b_item_path, repo_root)
        errors.extend(spec_errors)

    elif current_step == "red":
        with open(b_item_path, "r", encoding="utf-8") as f:
            content = f.read()
        test_plan = parse_markdown_section(content, "Test plan")
        if not test_plan or test_plan.strip() in ("", "—", "-"):
            errors.append("Gate FAIL: No test plan defined in B-item")

    elif current_step == "green":
        if run_verifier:
            verifier_errors = check_layer2_verifier(
                repo_root, skip_stages=["lint", "docs"]
            )
            errors.extend(verifier_errors)

    elif current_step == "blue":
        if run_verifier:
            verifier_errors = check_layer2_verifier(repo_root, skip_stages=["docs"])
            errors.extend(verifier_errors)

    elif current_step == "document-post":
        ingestion_errors = check_layer3_ingestion(repo_root, b_item_path)
        errors.extend(ingestion_errors)
        if run_verifier:
            verifier_errors = check_layer2_verifier(repo_root)
            errors.extend(verifier_errors)

    return errors


def cmd_check(args):
    b_item_path = os.path.abspath(args.b_item)

    if not os.path.exists(b_item_path):
        print(f"Error: B-item file not found: {b_item_path}", file=sys.stderr)
        return 1

    repo_root = find_repo_root()

    with open(b_item_path, "r", encoding="utf-8") as f:
        content = f.read()

    metadata = parse_metadata_table(content)
    current_step = get_workflow_step(metadata)

    if current_step is None:
        print(
            "Error: Workflow Step field is missing or empty in B-item metadata.",
            file=sys.stderr,
        )
        print(
            "Add '| Workflow Step | <step> |' to the Metadata table.", file=sys.stderr
        )
        print(
            f"Valid steps: {', '.join(STEP_DISPLAY[s] for s in WORKFLOW_STEPS)}",
            file=sys.stderr,
        )
        return 1

    if current_step not in WORKFLOW_STEPS:
        print(f"Error: Invalid Workflow Step '{current_step}'.", file=sys.stderr)
        print(
            f"Valid steps: {', '.join(STEP_DISPLAY[s] for s in WORKFLOW_STEPS)}",
            file=sys.stderr,
        )
        return 1

    next_step = get_next_step(current_step)
    if next_step is None:
        print(
            f"Item is at final step ({STEP_DISPLAY[current_step]}). Ready to mark COMPLETE."
        )
        return 0

    gate_errors = check_step_gate(
        current_step, b_item_path, repo_root, args.run_verifier
    )

    if gate_errors:
        print(
            f"GATE BLOCKED — Cannot advance from '{STEP_DISPLAY[current_step]}' to '{STEP_DISPLAY[next_step]}':",
            file=sys.stderr,
        )
        for err in gate_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"GATE PASSED — Safe to advance from '{STEP_DISPLAY[current_step]}' to '{STEP_DISPLAY[next_step]}'."
    )
    return 0


def cmd_status(args):
    b_item_path = os.path.abspath(args.b_item)

    if not os.path.exists(b_item_path):
        print(f"Error: B-item file not found: {b_item_path}", file=sys.stderr)
        return 1

    repo_root = find_repo_root()

    with open(b_item_path, "r", encoding="utf-8") as f:
        content = f.read()

    metadata = parse_metadata_table(content)
    item_id = extract_id(content, b_item_path)
    current_step = get_workflow_step(metadata)
    status = metadata.get("status", "unknown")
    verification = metadata.get("verification", "TDD")

    print(f"B-item: {item_id}")
    print(f"Status: {status}")
    print(f"Verification: {verification}")
    print(
        f"Workflow Step: {STEP_DISPLAY.get(current_step, current_step) if current_step else 'NOT SET'}"
    )

    if current_step and current_step in WORKFLOW_STEPS:
        idx = WORKFLOW_STEPS.index(current_step)
        print()
        for i, step in enumerate(WORKFLOW_STEPS):
            marker = ">>>" if i == idx else "   "
            done = "[x]" if i < idx else "[ ]"
            print(f"  {marker} {done} {STEP_DISPLAY[step]}")

    spec_path = os.path.join(repo_root, "SPEC.md")
    if os.path.exists(spec_path):
        spec_mtime = os.path.getmtime(spec_path)
        item_mtime = os.path.getmtime(b_item_path)
        freshness = "current" if item_mtime <= spec_mtime else "STALE"
        print(f"\nSPEC.md: {freshness}")
    else:
        print("\nSPEC.md: NOT COMPILED")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Megaplan workflow gate enforcement (Karpathy 3-Layer)"
    )
    subparsers = parser.add_subparsers(dest="command")

    check_parser = subparsers.add_parser(
        "check",
        help="Verify prerequisites for advancing to the next workflow step",
    )
    check_parser.add_argument("b_item", help="Path to the B-item .md file")
    check_parser.add_argument(
        "--run-verifier",
        action="store_true",
        help="Execute Layer 2 verification commands (tests, lint, typecheck)",
    )

    status_parser = subparsers.add_parser(
        "status",
        help="Show current workflow state of a B-item",
    )
    status_parser.add_argument("b_item", help="Path to the B-item .md file")

    args = parser.parse_args()

    if args.command == "check":
        sys.exit(cmd_check(args))
    elif args.command == "status":
        sys.exit(cmd_status(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
