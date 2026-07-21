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
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
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
    f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/{{branch}}.tar.gz?ref_type=branch"
)

# Files the bootstrap copies from the framework source to the user project.
# Each entry: (source_path_in_framework, dest_path_in_project).
LAYOUT = [
    ("AGENTS.md", "AGENTS.md"),
    ("skills/megaplan/SKILL.md", "SKILL.md"),
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


# Strict semver tag pattern: v1.2.3, v1.2.3-rc1, v1.2.3-alpha.1
# Does NOT match v2.0.0-fix (no digit in pre-release) or v1 (major-only).
_TAG_RE = re.compile(r"^v\d+\.\d+\.\d+(-[A-Za-z0-9.]*[0-9][A-Za-z0-9.]*)?$")


def _safe_extractall(tar, dest):
    """Extract *all* members from *tar* into *dest*, rejecting unsafe paths.

    Raises ``ValueError`` with the offending member name if:
    - the member's name is an absolute path,
    - the member's name escapes *dest* via ``..``, or
    - a symlink member's target escapes *dest*.
    """
    dest = os.path.realpath(dest)
    for member in tar.getmembers():
        if os.path.isabs(member.name):
            raise ValueError(f"member {member.name!r} has absolute path")
        target = os.path.realpath(os.path.join(dest, member.name))
        if not target.startswith(dest + os.sep) and target != dest:
            raise ValueError(f"member {member.name!r} escapes dest via path traversal")
        if member.issym() or member.islnk():
            link = member.linkname
            if os.path.isabs(link):
                raise ValueError(f"symlink {member.name!r} has absolute target")
            link_dir = os.path.dirname(os.path.join(dest, member.name))
            resolved = os.path.realpath(os.path.join(link_dir, link))
            if not resolved.startswith(dest + os.sep) and resolved != dest:
                raise ValueError(f"symlink {member.name!r} escapes dest")
    tar.extractall(path=dest)


def _pax_global_header_toplevel(tar):
    """Return the top-level directory name, skipping pax extension headers."""
    for member in tar.getmembers():
        if member.name in ("pax_global_header",):
            continue
        if member.type == tarfile.XHDTYPE:
            continue
        if "/" in member.name:
            return member.name.split("/")[0]
    raise ValueError("no top-level directory found in archive")


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
    """Return the GitHub archive URL for a tag or branch ref.

    Strict classification: ``_TAG_RE`` matches → tag URL; otherwise branch.
    The ref is URL-quoted before interpolation.
    """
    quoted = urllib.parse.quote(ref, safe="")
    if _TAG_RE.match(ref):
        return GITHUB_TARBALL_TAG.format(version=quoted)
    return GITHUB_TARBALL_BRANCH.format(branch=quoted)


def download_framework(version, dest):
    """Download the framework archive for `version` and extract to `dest`.

    Returns the path to the extracted top-level directory.
    """
    url = _tarball_url_for(version)
    try:
        raw = _http_get(url)
    except urllib.error.HTTPError as e:
        print(
            f"Error: HTTP {e.code} while downloading {url}",
            file=sys.stderr,
        )
        raise RuntimeError(f"HTTP {e.code} downloading {url}") from e
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
        members = tar.getmembers()
        if not members:
            raise RuntimeError(f"empty archive from {url}")
        top = _pax_global_header_toplevel(tar)
        _safe_extractall(tar, dest)
    return os.path.join(dest, top)


# --------------------------------------------------------------------------- #
# Path rewriting for user-project layout
# --------------------------------------------------------------------------- #

# Substitution table: translates framework-repo paths to user-project paths
# inside text files that the bootstrap lays out.
USER_PROJECT_PATH_REWRITES = [
    ("scripts/", "scripts/megaplan/"),
    ("docs/methodology.md", "docs/megaplan/methodology.md"),
    ("references/methodology.md", "docs/megaplan/methodology.md"),
    ("templates/megaplan.md", "docs/megaplan/megaplan.md"),
    ("templates/backlog.md", "docs/megaplan/backlog.md"),
    ("templates/glossary.md", "docs/megaplan/glossary.md"),
    ("templates/backlog-item.md", "docs/megaplan/backlog-items/_template.md"),
    ("templates/adr.md", "docs/megaplan/adr/_template.md"),
    ("examples/simple-todo-api/", "https://github.com/Gamebreack/megaplan/tree/main/examples/simple-todo-api/"),
    ("templates/wiki/", "docs/megaplan/wiki/"),
]


class PathRewriter:
    """Rewrites paths in text content using longest-match-first substitutions.

    Each substitution (from_path → to_path) is applied as a regex with a
    negative lookahead that prevents double substitution: the from_path is
    only matched when it is NOT followed by the suffix of to_path that
    extends beyond from_path.

    Substitutions are sorted by from_path length descending so that more
    specific (longer) patterns match before shorter directory prefixes.
    """

    def __init__(self, substitutions):
        # Sort by length descending for longest-match-first
        sorted_subs = sorted(substitutions, key=lambda x: len(x[0]), reverse=True)
        self._rules = []
        for from_path, to_path in sorted_subs:
            if not from_path:
                continue
            if len(from_path) <= len(to_path):
                # Build a pattern with negative lookahead: match from_path
                # only when NOT followed by the part of to_path that extends
                # beyond from_path (prevents double-substitution).
                suffix = to_path[len(from_path):]
                if suffix:
                    pattern = re.escape(from_path) + r"(?!" + re.escape(suffix) + r")"
                else:
                    pattern = re.escape(from_path)
            else:
                pattern = re.escape(from_path)
            self._rules.append((re.compile(pattern), to_path))

    def rewrite(self, text):
        """Apply all substitutions to *text*, longest-match first."""
        result = text
        for compiled, to_path in self._rules:
            result = compiled.sub(to_path, result)
        return result


_TEXT_EXTENSIONS = {".md", ".py"}


def _is_text_file(filepath):
    """Return True if *filepath* should be content-transformed."""
    _, ext = os.path.splitext(filepath)
    return ext.lower() in _TEXT_EXTENSIONS


def _copy_file(src, dst, *, force):
    """Copy src to dst, creating parent dirs. Skip if dst exists and not force.

    Returns True if written, False if skipped.
    """
    if os.path.exists(dst) and not force:
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _copy_file_with_transform(src, dst, rewriter, *, force):
    """Copy src to dst, applying *rewriter* to the text content.

    Reads the source as text, runs through ``rewriter.rewrite()``,
    and writes the transformed content to *dst*. Skips if *dst* exists
    and *force* is False.

    Returns True if written, False if skipped.
    """
    if os.path.exists(dst) and not force:
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, "r", encoding="utf-8") as f:
        content = f.read()
    content = rewriter.rewrite(content)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(content)
    # Preserve executable and other mode bits from the source.
    try:
        shutil.copymode(src, dst)
    except OSError:
        pass
    return True


def _write_integrity_manifest(
    project_dir, results, force, framework_root=None, pre_copy_hashes=None
):
    """Write (or update) the integrity manifest for laid-out files.

    The manifest lives at ``docs/megaplan/.integrity-manifest.json`` with
    structure ``{"files": {relpath: sha256}, "hook": {...}}``.

    When *project_dir == framework_root* (the dogfood case), the manifest
    is intentionally **not** written — the framework's own files are outside
    the install manifest scope.
    """
    if framework_root is not None and os.path.realpath(project_dir) == os.path.realpath(
        framework_root
    ):
        return  # dogfood — no manifest for the framework's own files

    import hashlib
    import json

    manifest_path = os.path.join(
        project_dir, "docs", "megaplan", ".integrity-manifest.json"
    )

    # Load existing manifest when not force-overwriting.
    existing_files = {}
    existing_hook = {}
    if not force and os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r") as f:
                existing = json.load(f)
            existing_files = existing.get("files", {})
            existing_hook = existing.get("hook", {})
        except (json.JSONDecodeError, OSError):
            pass

    # Compute hashes for all laid-out files (both "written" and "skipped").
    # When a file was overwritten (status == "written"), prefer the hash
    # that was captured *before* the copy (pre_copy_hashes), so the
    # manifest records the state the file was in *prior* to being
    # overwritten by --force.  Files that were newly written (no
    # pre-copy hash) or skipped are hashed from disk after writing.
    for dst_path, status in results:
        if status in ("written", "skipped") and os.path.exists(dst_path):
            relpath = os.path.relpath(dst_path, project_dir)
            if pre_copy_hashes and dst_path in pre_copy_hashes:
                sha = pre_copy_hashes[dst_path]
            else:
                sha = hashlib.sha256(
                    open(dst_path, "rb").read()
                ).hexdigest()
            existing_files[relpath] = sha

    manifest = {"files": existing_files, "hook": existing_hook}

    # Don't write an empty manifest when nothing was written and no manifest
    # existed before (e.g., re-run with --force=False where all files are
    # skipped and the manifest was deleted).
    if not manifest["files"] and not manifest["hook"] and not os.path.exists(manifest_path):
        return

    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def _update_manifest_hook_hash(project_dir, hook_path):
    """Update the integrity manifest with the SHA-256 of an installed hook."""
    import hashlib
    import json

    manifest_path = os.path.join(
        project_dir, "docs", "megaplan", ".integrity-manifest.json"
    )
    if not os.path.exists(manifest_path):
        return  # no manifest yet — nothing to update

    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError):
        manifest = {"files": {}}

    manifest.setdefault("hook", {})
    if os.path.exists(hook_path):
        hook_name = os.path.basename(hook_path)
        sha = hashlib.sha256(open(hook_path, "rb").read()).hexdigest()
        manifest["hook"][hook_name] = sha

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def lay_out_framework(src, project_dir, *, with_wiki=False, force=False, framework_root=None):
    """Copy the framework files from `src` into `project_dir`.

    When *project_dir* differs from *framework_root* (detected via
    ``os.path.realpath`` comparison), text files (``.md``, ``.py``) are
    content-transformed through `PathRewriter` to rewrite framework-repo
    path references into user-project layout paths (e.g.,
    ``scripts/verify_workflow.py`` → ``scripts/megaplan/verify_workflow.py``).

    When *project_dir* **is** *framework_root* (dogfooding or testing),
    files are copied byte-for-byte without transformation.

    Parameters
    ----------
    src : str
        Path to the framework source directory.
    project_dir : str
        Path to the target project directory.
    with_wiki : bool
        Also lay out wiki template files.
    force : bool
        Overwrite existing files.
    framework_root : str or None
        The framework repo root directory. When the project IS the framework,
        skip transformation. Defaults to the directory containing
        ``scripts/bootstrap.py``.

    Returns a list of (path, status) where status is "written", "skipped",
    or "missing".
    """
    if framework_root is None:
        framework_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Self-detection: when the destination IS the framework repo, skip
    # path transformation (the framework's own paths are already correct).
    skip_transform = os.path.realpath(project_dir) == os.path.realpath(framework_root)

    rewriter = None
    if not skip_transform:
        rewriter = PathRewriter(USER_PROJECT_PATH_REWRITES)

    # Capture hashes of existing files *before* the copy loop, so that
    # the integrity manifest records the user's content when --force
    # overwrites a file.
    import hashlib as _hashlib

    pre_copy_hashes = {}
    layouts = list(LAYOUT)
    for src_rel, dst_rel in layouts:
        dst_path = os.path.join(project_dir, dst_rel)
        if os.path.exists(dst_path):
            pre_copy_hashes[dst_path] = _hashlib.sha256(
                open(dst_path, "rb").read()
            ).hexdigest()
    for fname in SCRIPT_FILES:
        dst_path = os.path.join(project_dir, "scripts", "megaplan", fname)
        if os.path.exists(dst_path):
            pre_copy_hashes[dst_path] = _hashlib.sha256(
                open(dst_path, "rb").read()
            ).hexdigest()

    results = []
    if with_wiki:
        layouts.extend(WIKI_LAYOUT)
    for src_rel, dst_rel in layouts:
        src_path = os.path.join(src, src_rel)
        dst_path = os.path.join(project_dir, dst_rel)
        if not os.path.exists(src_path):
            results.append((dst_path, "missing"))
            print(f"Warning: missing source file: {src_rel}", file=sys.stderr)
            continue
        if rewriter and _is_text_file(src_path):
            written = _copy_file_with_transform(src_path, dst_path, rewriter, force=force)
        else:
            written = _copy_file(src_path, dst_path, force=force)
        results.append((dst_path, "written" if written else "skipped"))

    # Scripts go under scripts/megaplan/ in the user's project.
    scripts_dst = os.path.join(project_dir, "scripts", "megaplan")
    for fname in SCRIPT_FILES:
        src_path = os.path.join(src, "scripts", fname)
        dst_path = os.path.join(scripts_dst, fname)
        if not os.path.exists(src_path):
            results.append((dst_path, "missing"))
            print(f"Warning: missing source file: scripts/{fname}", file=sys.stderr)
            continue
        if rewriter and _is_text_file(src_path):
            written = _copy_file_with_transform(src_path, dst_path, rewriter, force=force)
        else:
            written = _copy_file(src_path, dst_path, force=force)
        results.append((dst_path, "written" if written else "skipped"))

    # Write integrity manifest only when at least one file was actually copied
    # (first lay-out or --force).  On a non-force re-lay-out with nothing written,
    # the existing manifest is left intact so deletions (e.g., the B4 scenario
    # "delete manifest then re-run bootstrap") surface as a self-test failure.
    any_written = any(status == "written" for _, status in results)
    if any_written:
        _write_integrity_manifest(
            project_dir, results, force, framework_root, pre_copy_hashes
        )

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

    Ensures ``.git/hooks/`` exists before delegating to ``setup_hooks.py``,
    and updates the integrity manifest with the hook's SHA-256 after install.
    """
    setup_hooks = os.path.join(project_dir, "scripts", "megaplan", "setup_hooks.py")
    if not os.path.exists(setup_hooks):
        raise FileNotFoundError(
            f"setup_hooks.py not found at {setup_hooks}; did the lay-out run?"
        )
    hook_target = Path(project_dir) / ".git" / "hooks" / "pre-commit"
    if hook_target.exists() and not force:
        # Record the hash of the existing hook in the manifest.
        _update_manifest_hook_hash(str(project_dir), str(hook_target))
        return hook_target  # preserve the user's existing hook

    # Ensure .git/hooks/ exists before calling setup_hooks.py.
    git_hooks_dir = os.path.join(project_dir, ".git", "hooks")
    os.makedirs(git_hooks_dir, exist_ok=True)

    args = [sys.executable, setup_hooks]
    if force:
        args.append("--yes")
    result = subprocess.run(args, cwd=project_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"setup_hooks.py failed (rc={result.returncode}): {result.stderr}"
        )

    # Record the installed hook's hash in the integrity manifest.
    _update_manifest_hook_hash(str(project_dir), str(hook_target))

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

    # 1. Resolve version — short-circuit for --from-local without --ref.
    if args.from_local and args.ref is None:
        version = "local"
    else:
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
            try:
                extracted = download_framework(version, tmp)
            except RuntimeError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
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
    self_test_ok = True
    if not args.skip_self_test:
        if self_test(project_dir):
            print("Self-test: OK")
        else:
            print("Self-test: FAILED (see above)", file=sys.stderr)
            self_test_ok = False

    _print_next_steps(version, project_dir)
    if not self_test_ok:
        print("Install completed with warnings (self-test failed)", file=sys.stderr)
        return 1
    return 0


def _print_next_steps(version, project_dir):
    print()
    print("Next steps:")
    print("  1. Edit docs/megaplan/megaplan.md to describe your project's vision.")
    print("  2. Copy docs/megaplan/backlog-items/_template.md to docs/megaplan/backlog-items/0-B1.md and fill it in.")
    print("  3. Read docs/megaplan/methodology.md for the full workflow.")
    print("  4. See a complete example at https://github.com/Gamebreack/megaplan/tree/main/examples/simple-todo-api.")
    print("  5. Re-run python scripts/megaplan/verify_workflow.py --selftest any time.")


if __name__ == "__main__":
    sys.exit(main())
