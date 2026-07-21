#!/usr/bin/env python3
import os
import stat
import sys

# Add the scripts/megaplan/ directory (where this file lives) to sys.path
# so we can import the shared markdown parser. Works whether the file is
# at <repo>/scripts/setup_hooks.py or at <repo>/scripts/megaplan/setup_hooks.py.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from _mdparse import find_repo_root


HOOK_SCRIPT = """#!/bin/bash
# Megaplan pre-commit hook — validates backlog integrity, glossary, and workflow gates
set -e

# Walk up from this script's location to find the project root (the dir
# containing AGENTS.md or .git/). Works whether the script is at
# <root>/scripts/setup_hooks.py or <root>/scripts/megaplan/setup_hooks.py.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT=""
DIR="$SCRIPT_DIR"
while [ "$DIR" != "/" ]; do
    if [ -f "$DIR/AGENTS.md" ] || [ -d "$DIR/.git" ]; then
        REPO_ROOT="$DIR"
        break
    fi
    DIR="$(dirname "$DIR")"
done

if [ -z "$REPO_ROOT" ]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

EXIT_CODE=0

if [ -f "$REPO_ROOT/docs/megaplan/backlog.md" ]; then
    echo "Megaplan: Validating backlog and active workflow gates..."
    ARGS=""
    if [ "$MEGAPLAN_RUN_VERIFIER" = "1" ]; then
        ARGS="--run-verifier"
    fi

    if ! python3 "$REPO_ROOT/scripts/megaplan/validate_backlog.py" "$REPO_ROOT" $ARGS 2>&1; then
        echo ""
        echo "Megaplan validation FAILED. Commit blocked."
        echo "Fix the errors above and try again."
        EXIT_CODE=1
    fi
fi

exit $EXIT_CODE
"""


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Install Megaplan pre-commit hook")
    parser.add_argument(
        "-y",
        "--yes",
        "--force",
        action="store_true",
        help="Overwrite existing hook without prompting",
    )
    args = parser.parse_args()

    # Walk up from the script's location to find the project root. Works
    # whether the script is at <root>/scripts/setup_hooks.py or
    # <root>/scripts/megaplan/setup_hooks.py.
    repo_root = find_repo_root(start=os.path.dirname(os.path.abspath(__file__)))
    git_hooks_dir = os.path.join(repo_root, ".git", "hooks")

    if not os.path.exists(git_hooks_dir):
        print(
            "Error: .git/hooks/ directory not found. Are you in a git repository?",
            file=sys.stderr,
        )
        sys.exit(1)

    hooks_target = os.path.join(git_hooks_dir, "pre-commit")

    if os.path.exists(hooks_target) and not args.yes:
        try:
            overwrite = input(
                f"pre-commit hook already exists at {hooks_target}. Overwrite? [y/N] "
            )
            if overwrite.lower() != "y":
                print("Aborted.")
                sys.exit(0)
        except EOFError:
            print(
                "Non-interactive session detected. Aborting to avoid overwrite. Use --yes or --force to overwrite.",
                file=sys.stderr,
            )
            sys.exit(1)

    with open(hooks_target, "w") as f:
        f.write(HOOK_SCRIPT)

    st = os.stat(hooks_target)
    os.chmod(hooks_target, st.st_mode | stat.S_IEXEC)

    print(f"Megaplan pre-commit hook installed at {hooks_target}")
    print(
        "The hook will run validate_backlog.py on every commit to validate the backlog, glossary, and active workflow gates."
    )


if __name__ == "__main__":
    main()
