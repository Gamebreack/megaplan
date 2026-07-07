#!/usr/bin/env python3
import os
import stat
import sys


HOOK_SCRIPT = '''#!/bin/bash
# Megaplan pre-commit hook — validates backlog integrity and SPEC.md freshness
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)
HAS_MEGAPLAN_CHANGES=0
HAS_BITEM_CHANGES=0

for file in $STAGED_FILES; do
    if [[ "$file" == docs/megaplan/* ]]; then
        HAS_MEGAPLAN_CHANGES=1
    fi
    if [[ "$file" == docs/megaplan/backlog-items/*.md ]]; then
        HAS_BITEM_CHANGES=1
    fi
done

EXIT_CODE=0

if [ "$HAS_MEGAPLAN_CHANGES" = "1" ]; then
    echo "Megaplan: Validating backlog..."
    python3 "$REPO_ROOT/scripts/validate_backlog.py" "$REPO_ROOT" 2>&1
    if [ $? -ne 0 ]; then
        echo ""
        echo "Backlog validation FAILED. Commit blocked."
        echo "Fix the errors above and try again."
        EXIT_CODE=1
    fi
fi

if [ "$HAS_BITEM_CHANGES" = "1" ]; then
    SPEC_PATH="$REPO_ROOT/SPEC.md"
    if [ -f "$SPEC_PATH" ]; then
        for file in $STAGED_FILES; do
            if [[ "$file" == docs/megaplan/backlog-items/*.md ]]; then
                ITEM_TIME=$(date -r "$file" +%s)
                SPEC_TIME=$(date -r "$SPEC_PATH" +%s)
                if [ "$ITEM_TIME" -gt "$SPEC_TIME" ]; then
                    echo "Megaplan: WARNING — SPEC.md is stale (staged B-item was modified after compilation)"
                    echo "  Staged: $file"
                    echo "  Run: python scripts/compile_spec.py $file"
                fi
            fi
        done
    fi
fi

exit $EXIT_CODE
'''


def main():
    repo_root = os.getcwd()
    git_hooks_dir = os.path.join(repo_root, ".git", "hooks")

    if not os.path.exists(git_hooks_dir):
        print("Error: .git/hooks/ directory not found. Are you in a git repository?", file=sys.stderr)
        sys.exit(1)

    hooks_target = os.path.join(git_hooks_dir, "pre-commit")

    if os.path.exists(hooks_target):
        overwrite = input(f"pre-commit hook already exists at {hooks_target}. Overwrite? [y/N] ")
        if overwrite.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    with open(hooks_target, "w") as f:
        f.write(HOOK_SCRIPT)

    st = os.stat(hooks_target)
    os.chmod(hooks_target, st.st_mode | stat.S_IEXEC)

    print(f"Megaplan pre-commit hook installed at {hooks_target}")
    print("The hook will run validate_backlog.py on every commit that touches docs/megaplan/ files.")


if __name__ == "__main__":
    main()
