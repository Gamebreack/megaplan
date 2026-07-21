#!/usr/bin/env python3
"""Dumb-install bootstrap for the Megaplan framework.

A user runs:

    curl -sSL https://raw.githubusercontent.com/Gamebreack/megaplan/main/scripts/bootstrap.py | python3

The script resolves the latest version (or honors --ref), downloads the
framework archive, lays out the files into the user's project, installs
the pre-commit hook, and runs a self-test. Re-runs are idempotent:
existing files are skipped (with a warning); --force overwrites.

This file lives only in the framework repo. It is fetched by URL and is
NOT laid out into the user's project — the user always gets the latest
version by re-pasting the same one-liner.
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

REPO_OWNER = "Gamebreack"
REPO_NAME = "megaplan"
GITHUB_API_LATEST = (
    f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
)
GITHUB_TARBALL_TAG = (
    f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/tags/{{version}}.tar.gz"
)
GITHUB_TARBALL_BRANCH = (
    f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/{{branch}}.tar.gz"
)

# Files the bootstrap copies from the framework source to the user project.
# Each entry: (source_path_in_framework, dest_path_in_project).
LAYOUT = [
    ("AGENTS.md", "AGENTS.md"),
    ("docs/methodology.md", "docs/megaplan/methodology.md"),
    ("templates/megaplan.md", "docs/megaplan/megaplan.md"),
    ("templates/backlog.md", "docs/megaplan/backlog.md"),
    ("templates/glossary.md", "docs/megaplan/glossary.md"),
    ("templates/backlog-item.md", "docs/megaplan/backlog-items/_template.md"),
    ("templates/adr.md", "docs/megaplan/adr/_template.md"),
]

# Wiki template files (only laid out with --with-wiki).
WIKI_LAYOUT = [
    ("templates/wiki/INDEX.md", "docs/megaplan/wiki/INDEX.md"),
    ("templates/wiki/architecture.md", "docs/megaplan/wiki/architecture.md"),
    ("templates/wiki/contract.md", "docs/megaplan/wiki/contract.md"),
    ("templates/wiki/decision.md", "docs/megaplan/wiki/decision.md"),
    ("templates/wiki/notes.md", "docs/megaplan/wiki/notes.md"),
]

# Framework scripts, all under scripts/megaplan/ in the user's project.
SCRIPT_FILES = [
    "_mdparse.py",
    "_wiki_map.py",
    "compile_spec.py",
    "validate_backlog.py",
    "validate_wiki.py",
    "verify_workflow.py",
    "ingest_wiki.py",
    "setup_hooks.py",
]


# --------------------------------------------------------------------------- #
# Version resolution + download
# --------------------------------------------------------------------------- #


def _http_get(url, timeout=30):
    """Read a URL into bytes. Raises OSError on failure."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


def resolve_latest_version(ref=None):
    """Return the version ref to use for the install.

    - If `ref` is given, return it directly without any network call.
    - Otherwise, call the GitHub Releases API to find the latest tag.
    - Fall back to "main" on any failure, with a warning to stderr.
    """
    if ref:
        return ref
    try:
        data = json.loads(_http_get(GITHUB_API_LATEST).decode("utf-8"))
        tag = data.get("tag_name")
        if tag:
            return tag
        print(
            "warning: GitHub Releases API returned no tag_name; "
            "falling back to main",
            file=sys.stderr,
        )
        return "main"
    except Exception as e:
        print(
            f"warning: could not reach GitHub Releases API ({e}); "
            "falling back to main",
            file=sys.stderr,
        )
        return "main"


def _tarball_url_for(ref):
    """Return the GitHub archive URL for a tag or branch ref."""
    # Tags look like v1.2.3; branch names don't have leading "v" and
    # contain no "/". Be conservative: only treat refs starting with "v"
    # followed by a digit as tags.
    if ref.startswith("v") and len(ref) > 1 and ref[1].isdigit():
        return GITHUB_TARBALL_TAG.format(version=ref)
    return GITHUB_TARBALL_BRANCH.format(branch=ref)


def download_framework(version, dest):
    """Download the framework archive for `version` and extract to `dest`.

    Returns the path to the extracted top-level directory.
    """
    url = _tarball_url_for(version)
    raw = _http_get(url)
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
        members = tar.getmembers()
        if not members:
            raise RuntimeError(f"empty archive from {url}")
        # GitHub archives put everything under a top-level dir like
        # "megaplan-VERSION/". Extract, then return that path.
        top = members[0].name.split("/")[0]
        # `filter="data"` is the safe default for Python 3.12+; for older
        # versions the filter argument is ignored. This protects against
        # the path-traversal vulnerabilities that tarfile's default
        # `extractall` historically allowed.
        try:
            tar.extractall(path=dest, filter="data")
        except TypeError:
            tar.extractall(path=dest)
    return os.path.join(dest, top)


# --------------------------------------------------------------------------- #
# File layout
# --------------------------------------------------------------------------- #


def _copy_file(src, dst, *, force):
    """Copy src to dst, creating parent dirs. Skip if dst exists and not force.

    Returns True if written, False if skipped.
    """
    if os.path.exists(dst) and not force:
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return True


def lay_out_framework(src, project_dir, *, with_wiki=False, force=False):
    """Copy the framework files from `src` into `project_dir`.

    Returns a list of (path, status) where status is "written" or "skipped".
    """
    results = []
    layouts = list(LAYOUT)
    if with_wiki:
        layouts.extend(WIKI_LAYOUT)
    for src_rel, dst_rel in layouts:
        src_path = os.path.join(src, src_rel)
        if not os.path.exists(src_path):
            continue
        dst_path = os.path.join(project_dir, dst_rel)
        written = _copy_file(src_path, dst_path, force=force)
        results.append((dst_path, "written" if written else "skipped"))

    # Scripts go under scripts/megaplan/ in the user's project.
    scripts_dst = os.path.join(project_dir, "scripts", "megaplan")
    for fname in SCRIPT_FILES:
        src_path = os.path.join(src, "scripts", fname)
        if not os.path.exists(src_path):
            continue
        dst_path = os.path.join(scripts_dst, fname)
        written = _copy_file(src_path, dst_path, force=force)
        results.append((dst_path, "written" if written else "skipped"))

    return results


# --------------------------------------------------------------------------- #
# Pre-commit hook install + self-test
# --------------------------------------------------------------------------- #


def install_pre_commit_hook(project_dir, *, force=False):
    """Install the pre-commit hook in `project_dir`.

    Invokes the laid-out `scripts/megaplan/setup_hooks.py` with the
    appropriate flags. If the hook already exists and `force` is False,
    the existing hook is preserved (the user may have customized it).
    Returns the path to the installed (or existing) hook.
    """
    setup_hooks = os.path.join(project_dir, "scripts", "megaplan", "setup_hooks.py")
    if not os.path.exists(setup_hooks):
        raise FileNotFoundError(
            f"setup_hooks.py not found at {setup_hooks}; did the lay-out run?"
        )
    hook_target = Path(project_dir) / ".git" / "hooks" / "pre-commit"
    if hook_target.exists() and not force:
        return hook_target  # preserve the user's existing hook
    args = [sys.executable, setup_hooks]
    if force:
        args.append("--yes")
    result = subprocess.run(args, cwd=project_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"setup_hooks.py failed (rc={result.returncode}): {result.stderr}"
        )
    return hook_target


def self_test(project_dir):
    """Run `verify_workflow.py --selftest` in `project_dir`. Returns True on success."""
    verify = os.path.join(project_dir, "scripts", "megaplan", "verify_workflow.py")
    if not os.path.exists(verify):
        print(f"self-test: {verify} not found", file=sys.stderr)
        return False
    result = subprocess.run(
        [sys.executable, verify, "--selftest", "--project-dir", project_dir],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"self-test failed (rc={result.returncode}): {result.stderr}", file=sys.stderr)
    return result.returncode == 0


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap a project with the Megaplan framework"
    )
    parser.add_argument(
        "--ref",
        help="Pin a specific version (tag like v2.0.0, or branch like main). "
        "Default: latest release tag, falling back to main.",
    )
    parser.add_argument(
        "--project-dir",
        default=os.getcwd(),
        help="The project directory to install into (default: current directory).",
    )
    parser.add_argument(
        "--with-wiki",
        action="store_true",
        help="Also lay out the AI wiki templates (opt-in feature).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files. Default: skip existing files.",
    )
    parser.add_argument(
        "--from-local",
        help="Use a local path as the framework source instead of downloading. "
        "Useful for testing and local development.",
    )
    parser.add_argument(
        "--skip-self-test",
        action="store_true",
        help="Skip the self-test at the end (not recommended).",
    )
    parser.add_argument(
        "--skip-hook",
        action="store_true",
        help="Skip the pre-commit hook install.",
    )
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)

    # Sanity: project must be a git repo (the pre-commit hook needs .git/).
    if not args.skip_hook and not os.path.isdir(os.path.join(project_dir, ".git")):
        print(
            f"Error: {project_dir} is not a git repository (no .git/ directory).",
            "Either run `git init` first or pass --skip-hook to install without the hook.",
            file=sys.stderr,
            sep="\n",
        )
        return 1

    # 1. Resolve version.
    version = resolve_latest_version(args.ref)
    print(f"Megaplan bootstrap: version {version}")

    # 2. Get the framework source.
    if args.from_local:
        src = os.path.abspath(args.from_local)
        if not os.path.isdir(src):
            print(f"Error: --from-local path is not a directory: {src}", file=sys.stderr)
            return 1
    else:
        with tempfile.TemporaryDirectory() as tmp:
            extracted = download_framework(version, tmp)
            src = extracted
            return _do_install(src, project_dir, version, args)

    return _do_install(src, project_dir, version, args)


def _do_install(src, project_dir, version, args):
    """Run the lay-out, hook install, and self-test. Returns process exit code."""
    # 3. Lay out.
    results = lay_out_framework(
        src, project_dir, with_wiki=args.with_wiki, force=args.force
    )
    written = sum(1 for _, s in results if s == "written")
    skipped = sum(1 for _, s in results if s == "skipped")
    print(f"Lay-out: {written} files written, {skipped} skipped.")

    # 4. Install hook.
    if not args.skip_hook:
        try:
            install_pre_commit_hook(project_dir, force=args.force)
            print("Pre-commit hook installed.")
        except Exception as e:
            print(f"Warning: hook install failed: {e}", file=sys.stderr)

    # 5. Self-test.
    if not args.skip_self_test:
        if self_test(project_dir):
            print("Self-test: OK")
        else:
            print("Self-test: FAILED (see above)", file=sys.stderr)

    _print_next_steps(version, project_dir)
    return 0


def _print_next_steps(version, project_dir):
    print()
    print("Next steps:")
    print(
        f"  1. Edit {project_dir}/docs/megaplan/megaplan.md to describe "
        "your project's vision."
    )
    print(
        f"  2. Scope Cycle 0 in {project_dir}/docs/megaplan/megaplan.md "
        "and create the first B-item."
    )
    print(
        f"  3. Read {project_dir}/docs/megaplan/methodology.md for the "
        "full workflow."
    )
    print(
        "  4. Re-run `python scripts/megaplan/verify_workflow.py --selftest` "
        "any time to confirm the install is healthy."
    )


if __name__ == "__main__":
    sys.exit(main())
