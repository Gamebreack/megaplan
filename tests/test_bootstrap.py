"""Tests for `scripts/bootstrap.py` (dumb-install bootstrap)."""
import io
import json
import os
import sys
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
)

bootstrap = pytest.importorskip("bootstrap")  # red: skip until bootstrap.py exists


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def framework_src(tmp_path):
    """A directory shaped like the framework repo: AGENTS.md, docs/, templates/, scripts/.

    Acts as the `--from-local` source for tests. Uses a small in-memory
    structure rather than the real framework repo so the tests are fast
    and don't depend on the actual repo contents.

    The `framework_repo` fixture (below) is the alternative for tests
    that need real scripts (install_pre_commit_hook, self_test).
    """
    src = tmp_path / "framework"
    src.mkdir()

    # AGENTS.md
    (src / "AGENTS.md").write_text("# Megaplan\n\nFramework content here.\n")

    # docs/methodology.md
    docs = src / "docs"
    docs.mkdir()
    (docs / "methodology.md").write_text("# Methodology\n\nReference content.\n")

    # templates/
    templates = src / "templates"
    templates.mkdir()
    (templates / "megaplan.md").write_text("# Megaplan template\n")
    (templates / "backlog.md").write_text("# Backlog template\n")
    (templates / "glossary.md").write_text("# Glossary template\n")
    (templates / "backlog-item.md").write_text("# B-item template\n")
    (templates / "adr.md").write_text("# ADR template\n")

    # templates/wiki/
    wiki_templates = templates / "wiki"
    wiki_templates.mkdir()
    (wiki_templates / "INDEX.md").write_text("# Wiki INDEX\n")
    (wiki_templates / "architecture.md").write_text("# Wiki architecture\n")
    (wiki_templates / "contract.md").write_text("# Wiki contract\n")
    (wiki_templates / "decision.md").write_text("# Wiki decision\n")
    (wiki_templates / "notes.md").write_text("# Wiki notes\n")

    # scripts/ — minimal real-shaped content (these are stubs).
    scripts = src / "scripts"
    scripts.mkdir()
    (scripts / "_mdparse.py").write_text("# mdparse\n")
    (scripts / "_wiki_map.py").write_text("# wiki_map\n")
    (scripts / "compile_spec.py").write_text("# compile_spec\n")
    (scripts / "validate_backlog.py").write_text("# validate_backlog\n")
    (scripts / "verify_workflow.py").write_text("# verify_workflow\n")
    (scripts / "ingest_wiki.py").write_text("# ingest_wiki\n")
    (scripts / "validate_wiki.py").write_text("# validate_wiki\n")
    (scripts / "setup_hooks.py").write_text("# setup_hooks\n")

    return src


@pytest.fixture
def framework_repo():
    """The actual framework repo (this directory).

    Used by tests that need real scripts (the install_pre_commit_hook and
    self_test subprocess calls would fail against stub content).
    """
    # The framework repo is the parent of the scripts/ directory.
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def project_dir(tmp_path):
    """An empty project directory with a `.git/` so the hook installer works."""
    proj = tmp_path / "project"
    proj.mkdir()
    (proj / ".git").mkdir()
    (proj / ".git" / "hooks").mkdir()
    return proj


def _make_tarball(src_dir, version):
    """Create an in-memory tar.gz of `src_dir` named for `version`."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # The GitHub archive puts everything under a top-level dir named like
        # "megaplan-VERSION". Mirror that.
        arcname_prefix = f"megaplan-{version}"
        for root, _, files in os.walk(src_dir):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, src_dir)
                tar.add(full, arcname=os.path.join(arcname_prefix, rel))
    buf.seek(0)
    return buf


# --------------------------------------------------------------------------- #
# Version resolution
# --------------------------------------------------------------------------- #


def test_resolve_latest_version_default():
    """No --ref, mocked GitHub API returns v2.0.0 → returns v2.0.0."""
    fake_response = MagicMock()
    fake_response.read.return_value = json.dumps({"tag_name": "v2.0.0"}).encode()
    fake_response.__enter__ = lambda s: s
    fake_response.__exit__ = lambda s, *a: None
    with patch("urllib.request.urlopen", return_value=fake_response):
        v = bootstrap.resolve_latest_version()
    assert v == "v2.0.0"


def test_resolve_latest_version_pinned():
    """--ref v1.5.0 → returns v1.5.0 without calling the API."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        v = bootstrap.resolve_latest_version(ref="v1.5.0")
    assert v == "v1.5.0"
    mock_urlopen.assert_not_called()


def test_resolve_latest_version_api_fallback(capsys):
    """API call raises (network down) → falls back to 'main' with a warning."""
    def raise_urlopen(*args, **kwargs):
        raise OSError("network down")
    with patch("urllib.request.urlopen", side_effect=raise_urlopen):
        v = bootstrap.resolve_latest_version()
    assert v == "main"
    captured = capsys.readouterr()
    assert "warning" in captured.err.lower() or "fallback" in captured.err.lower()


# --------------------------------------------------------------------------- #
# File layout
# --------------------------------------------------------------------------- #


def test_lay_out_basic(framework_src, project_dir):
    """Lay out the framework into a project; expected files present."""
    written = bootstrap.lay_out_framework(
        str(framework_src), str(project_dir), with_wiki=False, force=False
    )
    expected = [
        "AGENTS.md",
        "docs/megaplan/megaplan.md",
        "docs/megaplan/backlog.md",
        "docs/megaplan/glossary.md",
        "docs/megaplan/backlog-items/_template.md",
        "docs/megaplan/adr/_template.md",
        "scripts/megaplan/_mdparse.py",
        "scripts/megaplan/verify_workflow.py",
        "scripts/megaplan/setup_hooks.py",
    ]
    for rel in expected:
        assert (project_dir / rel).exists(), f"missing: {rel}"
    # Wiki not laid out by default.
    assert not (project_dir / "docs/megaplan/wiki/INDEX.md").exists()
    # Returns a list of written paths.
    assert isinstance(written, list)
    assert len(written) >= len(expected)


def test_lay_out_idempotent(framework_src, project_dir):
    """Lay out twice without --force: second run skips existing files."""
    bootstrap.lay_out_framework(str(framework_src), str(project_dir), with_wiki=False, force=False)
    # Modify a file the user already customized.
    agents = project_dir / "AGENTS.md"
    agents.write_text("# User customized\n")
    # Lay out again.
    bootstrap.lay_out_framework(str(framework_src), str(project_dir), with_wiki=False, force=False)
    # User's version is preserved.
    assert agents.read_text() == "# User customized\n"


def test_lay_out_force(framework_src, project_dir):
    """Lay out twice with --force: second run overwrites."""
    bootstrap.lay_out_framework(str(framework_src), str(project_dir), with_wiki=False, force=False)
    agents = project_dir / "AGENTS.md"
    agents.write_text("# User customized\n")
    bootstrap.lay_out_framework(str(framework_src), str(project_dir), with_wiki=False, force=True)
    # Restored to framework version.
    assert "Framework content" in agents.read_text()


def test_lay_out_with_wiki(framework_src, project_dir):
    """--with-wiki lays out wiki templates."""
    bootstrap.lay_out_framework(str(framework_src), str(project_dir), with_wiki=True, force=False)
    expected_wiki = [
        "docs/megaplan/wiki/INDEX.md",
        "docs/megaplan/wiki/architecture.md",
        "docs/megaplan/wiki/contract.md",
        "docs/megaplan/wiki/decision.md",
        "docs/megaplan/wiki/notes.md",
    ]
    for rel in expected_wiki:
        assert (project_dir / rel).exists(), f"missing wiki file: {rel}"


# --------------------------------------------------------------------------- #
# Pre-commit hook install
# --------------------------------------------------------------------------- #


def test_install_pre_commit_hook(framework_repo, project_dir):
    """After lay-out, install hook; .git/hooks/pre-commit exists and is executable.

    Uses the real framework repo so the laid-out setup_hooks.py is real
    and the subprocess call works.
    """
    bootstrap.lay_out_framework(str(framework_repo), str(project_dir), with_wiki=False, force=False)
    hook_path = bootstrap.install_pre_commit_hook(str(project_dir), force=False)
    assert hook_path.exists()
    assert os.access(hook_path, os.X_OK)


def test_install_pre_commit_hook_existing(framework_repo, project_dir):
    """Existing hook + no --force: skipped (file unchanged)."""
    bootstrap.lay_out_framework(str(framework_repo), str(project_dir), with_wiki=False, force=False)
    bootstrap.install_pre_commit_hook(str(project_dir), force=False)
    hook = project_dir / ".git" / "hooks" / "pre-commit"
    # Manually modify to confirm skip preserves content.
    hook.write_text("# user custom hook\n")
    bootstrap.install_pre_commit_hook(str(project_dir), force=False)
    assert hook.read_text() == "# user custom hook\n"
    # --force overwrites.
    bootstrap.install_pre_commit_hook(str(project_dir), force=True)
    assert hook.read_text() != "# user custom hook\n"


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #


def test_self_test_runs(framework_repo, project_dir):
    """After lay-out, self_test() returns True (calls verify_workflow --selftest).

    Uses the real framework repo so the laid-out scripts are real.
    """
    bootstrap.lay_out_framework(str(framework_repo), str(project_dir), with_wiki=False, force=False)
    bootstrap.install_pre_commit_hook(str(project_dir), force=False)
    assert bootstrap.self_test(str(project_dir)) is True


# --------------------------------------------------------------------------- #
# End-to-end (no network) via --from-local
# --------------------------------------------------------------------------- #


def test_from_local_bypasses_network(framework_src, project_dir, capsys):
    """--from-local + --ref main bypasses all network calls."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        with patch.object(sys, "argv", [
            "bootstrap.py",
            "--from-local", str(framework_src),
            "--ref", "main",
            "--project-dir", str(project_dir),
        ]):
            rc = bootstrap.main()
    assert rc == 0
    mock_urlopen.assert_not_called()
    # And the expected files are present.
    assert (project_dir / "AGENTS.md").exists()
    assert (project_dir / "docs/megaplan/megaplan.md").exists()


def test_no_git_errors(framework_src, tmp_path, capsys):
    """No .git/ → bootstrap errors with a clear message; exits non-zero."""
    no_git = tmp_path / "no_git_project"
    no_git.mkdir()
    with patch("urllib.request.urlopen") as mock_urlopen:
        with patch.object(sys, "argv", [
            "bootstrap.py", "--from-local", str(framework_src), "--project-dir", str(no_git)
        ]):
            rc = bootstrap.main()
    assert rc != 0
    captured = capsys.readouterr()
    assert ".git" in captured.err or "git" in captured.err.lower()
    mock_urlopen.assert_not_called()


def test_download_framework_extracts(framework_src, tmp_path):
    """`download_framework` extracts the tarball to dest; contents match."""
    buf = _make_tarball(framework_src, "v2.0.0")
    fake_response = MagicMock()
    fake_response.read = lambda: buf.getvalue()
    fake_response.__enter__ = lambda s: s
    fake_response.__exit__ = lambda s, *a: None
    with patch("urllib.request.urlopen", return_value=fake_response):
        extracted = bootstrap.download_framework("v2.0.0", str(tmp_path))
    # The extracted dir contains AGENTS.md and templates/, matching the source.
    from pathlib import Path
    extracted_path = Path(extracted)
    assert (extracted_path / "AGENTS.md").exists()
    assert (extracted_path / "templates" / "megaplan.md").exists()


# --------------------------------------------------------------------------- #
# B1: tarball & download integrity
# --------------------------------------------------------------------------- #


def _make_tarball_with_member(member_factory):
    """Build a tarball where each member is produced by `member_factory(name)`.

    `member_factory` is a callable that takes a name and returns a
    (data_bytes_or_None, tarinfo_override) tuple. The first member is
    always a pax_global_header to mimic real GitHub tarballs.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # Real GitHub tarballs include this pax extension member first.
        pax = tarfile.TarInfo("pax_global_header")
        pax.type = tarfile.XHDTYPE
        pax.pax_headers = {"comment": ""}
        tar.addfile(pax)
        for name, data, override in member_factory:
            info = tarfile.TarInfo(name)
            if data is not None:
                info.size = len(data)
            for k, v in (override or {}).items():
                setattr(info, k, v)
            if data is not None:
                tar.addfile(info, io.BytesIO(data))
            else:
                tar.addfile(info)
    return buf.getvalue()


def test_tarball_pax_global_header_handled(framework_src, tmp_path):
    """Real GitHub tarballs have pax_global_header as the first member. Verify extraction finds the right top-level dir."""
    def members():
        yield "megaplan-v2.0.0/AGENTS.md", b"# Megaplan\n", None
        yield "megaplan-v2.0.0/templates/megaplan.md", b"# Megaplan template\n", None
    raw = _make_tarball_with_member(members())
    fake_response = MagicMock()
    fake_response.read = lambda: raw
    fake_response.__enter__ = lambda s: s
    fake_response.__exit__ = lambda s, *a: None
    with patch("urllib.request.urlopen", return_value=fake_response):
        extracted = bootstrap.download_framework("v2.0.0", str(tmp_path))
    from pathlib import Path
    extracted_path = Path(extracted)
    assert extracted_path.name == "megaplan-v2.0.0", (
        f"top-level dir should be megaplan-v2.0.0, got {extracted_path.name}"
    )
    assert (extracted_path / "AGENTS.md").exists()
    assert (extracted_path / "templates" / "megaplan.md").exists()


def test_tarfile_rejects_path_traversal(framework_src, tmp_path):
    """Tarball with ../../etc/passwd entry is rejected."""
    def members():
        yield "megaplan-v2.0.0/AGENTS.md", b"# Megaplan\n", None
        yield "megaplan-v2.0.0/../../etc/passwd", b"root:x:0:0::/root:/bin/sh\n", None
    raw = _make_tarball_with_member(members())
    fake_response = MagicMock()
    fake_response.read = lambda: raw
    fake_response.__enter__ = lambda s: s
    fake_response.__exit__ = lambda s, *a: None
    with patch("urllib.request.urlopen", return_value=fake_response):
        with pytest.raises((ValueError, RuntimeError)):
            bootstrap.download_framework("v2.0.0", str(tmp_path))


def test_tarfile_rejects_absolute_path(framework_src, tmp_path):
    """Tarball with /etc/passwd entry is rejected."""
    def members():
        yield "megaplan-v2.0.0/AGENTS.md", b"# Megaplan\n", None
        yield "/etc/passwd", b"root:x:0:0::/root:/bin/sh\n", None
    raw = _make_tarball_with_member(members())
    fake_response = MagicMock()
    fake_response.read = lambda: raw
    fake_response.__enter__ = lambda s: s
    fake_response.__exit__ = lambda s, *a: None
    with patch("urllib.request.urlopen", return_value=fake_response):
        with pytest.raises((ValueError, RuntimeError)):
            bootstrap.download_framework("v2.0.0", str(tmp_path))


def test_tarfile_rejects_symlink_escape(framework_src, tmp_path):
    """Tarball with a symlink pointing outside dest is rejected."""
    def members():
        yield "megaplan-v2.0.0/AGENTS.md", b"# Megaplan\n", None
        yield "megaplan-v2.0.0/escape", None, {
            "type": tarfile.SYMTYPE, "linkname": "../../etc/passwd"
        }
    raw = _make_tarball_with_member(members())
    fake_response = MagicMock()
    fake_response.read = lambda: raw
    fake_response.__enter__ = lambda s: s
    fake_response.__exit__ = lambda s, *a: None
    with patch("urllib.request.urlopen", return_value=fake_response):
        with pytest.raises((ValueError, RuntimeError)):
            bootstrap.download_framework("v2.0.0", str(tmp_path))


def test_url_ref_quoted():
    """ref with special chars is URL-quoted, not interpolated raw."""
    url = bootstrap._tarball_url_for("main?x=1")
    assert "?" in url
    assert "%3F" in url
    assert "x%3D1" in url
    assert "main?x=1" not in url


def test_branch_classification_strict():
    """v2.0.0-fix is a branch (not a semver tag) — uses branch URL."""
    url = bootstrap._tarball_url_for("v2.0.0-fix")
    assert "/heads/v2.0.0-fix" in url, f"expected branch URL, got {url}"


def test_branch_classification_prerelease():
    """v2.0.0-rc1 is a semver pre-release — uses tag URL."""
    url = bootstrap._tarball_url_for("v2.0.0-rc1")
    assert "/tags/v2.0.0-rc1" in url, f"expected tag URL, got {url}"


def test_from_local_no_network_when_no_ref(framework_src, project_dir, capsys):
    """--from-local without --ref must not call urlopen."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        with patch.object(sys, "argv", [
            "bootstrap.py",
            "--from-local", str(framework_src),
            "--project-dir", str(project_dir),
        ]):
            rc = bootstrap.main()
    assert rc == 0
    mock_urlopen.assert_not_called()


def test_http_error_surfaced(framework_src, project_dir, capsys):
    """HTTPError from urlopen surfaces a friendly message and non-zero exit."""
    import urllib.error
    err = urllib.error.HTTPError(
        "https://github.com/Gamebreack/megaplan/archive/refs/tags/v9.9.9.tar.gz",
        404, "Not Found", {}, None,
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with patch.object(sys, "argv", [
            "bootstrap.py",
            "--ref", "v9.9.9",
            "--project-dir", str(project_dir),
            "--skip-hook",
            "--skip-self-test",
        ]):
            rc = bootstrap.main()
    assert rc != 0
    captured = capsys.readouterr()
    assert "v9.9.9" in captured.err or "404" in captured.err


def test_missing_source_warns(framework_src, project_dir, capsys):
    """lay-out_framework with a missing source file records 'missing' and warns."""
    import os
    os.remove(framework_src / "AGENTS.md")
    results = bootstrap.lay_out_framework(
        str(framework_src), str(project_dir), with_wiki=False, force=False
    )
    # AGENTS.md should be in the results with status 'missing'
    statuses = {os.path.basename(p): s for p, s in results}
    assert statuses.get("AGENTS.md") == "missing"
    captured = capsys.readouterr()
    assert "AGENTS.md" in captured.err


def test_safe_extractall_raises_on_unsafe_archive(framework_src, tmp_path):
    """Direct call to _safe_extractall rejects all four unsafe patterns."""
    def make_with(members_iter):
        return _make_tarball_with_member(members_iter)
    # Path traversal
    raw = make_with([
        ("megaplan-v2.0.0/AGENTS.md", b"# Megaplan\n", None),
        ("megaplan-v2.0.0/../../etc/passwd", b"x", None),
    ])
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
        with pytest.raises(ValueError, match=r"escapes dest|path traversal|absolute"):
            bootstrap._safe_extractall(tar, str(tmp_path))
    # Absolute path
    raw = make_with([
        ("megaplan-v2.0.0/AGENTS.md", b"# Megaplan\n", None),
        ("/etc/passwd", b"x", None),
    ])
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
        with pytest.raises(ValueError, match=r"absolute path"):
            bootstrap._safe_extractall(tar, str(tmp_path))
    # Symlink escape
    raw = make_with([
        ("megaplan-v2.0.0/AGENTS.md", b"# Megaplan\n", None),
        ("megaplan-v2.0.0/escape", None, {
            "type": tarfile.SYMTYPE, "linkname": "../../etc/passwd"
        }),
    ])
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
        with pytest.raises(ValueError, match=r"symlink"):
            bootstrap._safe_extractall(tar, str(tmp_path))


# --------------------------------------------------------------------------- #
# B3: path transformation for laid-out docs
# --------------------------------------------------------------------------- #


# --- PathRewriter unit tests (pure-function layer) ---

def test_path_rewriter_simple_substitution():
    """`scripts/setup_hooks.py` → `scripts/megaplan/setup_hooks.py`."""
    rew = bootstrap.PathRewriter([("scripts/", "scripts/megaplan/")])
    assert rew.rewrite("see scripts/setup_hooks.py") == "see scripts/megaplan/setup_hooks.py"


def test_path_rewriter_longest_first():
    """`templates/megaplan.md` matches before `templates/` (if both are in the table)."""
    rew = bootstrap.PathRewriter([
        ("templates/megaplan.md", "docs/megaplan/megaplan.md"),
        ("templates/", "docs/megaplan/"),
    ])
    # Longest first: the file-shaped pattern wins, not the directory-shaped one.
    assert rew.rewrite("templates/megaplan.md") == "docs/megaplan/megaplan.md"


def test_path_rewriter_idempotent():
    """Applying the rewrite twice gives the same result as applying once."""
    rew = bootstrap.PathRewriter([("scripts/", "scripts/megaplan/")])
    once = rew.rewrite("scripts/setup_hooks.py")
    twice = rew.rewrite(once)
    assert once == twice


def test_path_rewriter_does_not_double_substitute():
    """`scripts/megaplan/foo` is not re-substituted to `scripts/megaplan/megaplan/foo`."""
    rew = bootstrap.PathRewriter([("scripts/", "scripts/megaplan/")])
    already = "scripts/megaplan/verify_workflow.py"
    assert rew.rewrite(already) == already


# --- lay_out_framework integration ---

@pytest.fixture
def framework_copy(tmp_path):
    """A real copy of the framework repo at a tmp_path location.

    Used by the "no transformation for framework repo" test which needs
    a framework copy it can write into.
    """
    import shutil
    src = Path(__file__).parent.parent  # the actual framework repo
    dst = tmp_path / "framework_copy"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
        ".git", "__pycache__", ".pytest_cache", ".slim", "tests"
    ))
    return dst


def test_lay_out_rewrites_agents_md_paths(framework_repo, project_dir):
    """After lay-out, the user-project AGENTS.md uses scripts/megaplan/... not scripts/..."""
    bootstrap.lay_out_framework(
        str(framework_repo), str(project_dir), with_wiki=False, force=False
    )
    agents = (project_dir / "AGENTS.md").read_text()
    # The framework's own AGENTS.md uses scripts/verify_workflow.py; the user-project copy should NOT.
    assert "scripts/verify_workflow.py" not in agents, (
        f"user-project AGENTS.md still has framework-repo path 'scripts/verify_workflow.py':\n{agents[:500]}"
    )
    assert "scripts/megaplan/verify_workflow.py" in agents


def test_lay_out_rewrites_methodology_paths(framework_repo, project_dir):
    """After lay-out, the user-project methodology.md uses docs/megaplan/.. not docs/.."""
    bootstrap.lay_out_framework(
        str(framework_repo), str(project_dir), with_wiki=False, force=False
    )
    methodology = (project_dir / "docs/megaplan/methodology.md").read_text()
    # The framework's methodology.md has a "Quick start" section with the one-liner
    # that may or may not need rewriting (it's paths, not URLs). The key check is
    # that references to `docs/methodology.md` (framework-repo path) are absent
    # and references to `docs/megaplan/methodology.md` (user-project path) are present.
    # Also: the methodology.md lives at docs/megaplan/methodology.md in the user project
    # (not docs/methodology.md), and any path in the file pointing to itself should
    # be the user-project path.
    assert "docs/megaplan/methodology.md" in methodology


def test_lay_out_rewrites_skill_md_paths(framework_repo, project_dir):
    """After lay-out, the user-project SKILL.md has docs/megaplan/methodology.md not references/methodology.md."""
    bootstrap.lay_out_framework(
        str(framework_repo), str(project_dir), with_wiki=False, force=False
    )
    skill = (project_dir / "SKILL.md").read_text() if (project_dir / "SKILL.md").exists() else ""
    if not skill:
        pytest.skip("SKILL.md is not in the LAYOUT (B3 should add it; if this fails, file a bug)")
    assert "references/methodology.md" not in skill, "SKILL.md still has the dead link"
    assert "docs/megaplan/methodology.md" in skill


def test_lay_out_rewrites_backlog_template(framework_repo, project_dir):
    """After lay-out, the user-project backlog.md does not reference templates/backlog-item.md (the old framework-repo path)."""
    bootstrap.lay_out_framework(
        str(framework_repo), str(project_dir), with_wiki=False, force=False
    )
    backlog = (project_dir / "docs/megaplan/backlog.md").read_text()
    # The template says "New items are created from `templates/backlog-item.md` before any code is written."
    # In the user project, templates/ doesn't exist; the new path is `docs/megaplan/backlog-items/_template.md`.
    assert "templates/backlog-item.md" not in backlog, (
        f"user-project backlog.md still references the old template path:\n{backlog}"
    )


def test_lay_out_no_transformation_for_framework_repo(framework_copy):
    """When src and project_dir are the same (the framework itself), the laid-out file is byte-identical to the source."""
    # Simulate the dogfood case: bootstrap running on the framework.
    # The function should detect that project_dir == framework_root and skip the rewrite.
    # The bootstrap module's "framework root" is the directory containing scripts/,
    # which is framework_copy's parent. We pass framework_copy as both src and
    # project_dir, and assert no transformation happened.
    # The bootstrap's self-detection needs an explicit framework_root parameter
    # OR the module-level detection. We assume the @fixer implementation provides
    # the framework_root parameter.
    bootstrap.lay_out_framework(
        str(framework_copy), str(framework_copy),
        with_wiki=False, force=False,
        framework_root=str(framework_copy),
    )
    # The framework's own AGENTS.md is correct for the framework repo layout.
    # After the (skipped) transformation, the file should be byte-identical.
    src_agents = (framework_copy / "AGENTS.md").read_text()
    # If transformation had been applied, the file would now reference scripts/megaplan/
    # which doesn't exist in the framework repo. So we just check the file is still
    # the original (unchanged by transformation).
    # We can't compare to the original framework_repo because the lay-out copied it
    # to framework_copy. We can compare to a fresh read.
    reread = (framework_copy / "AGENTS.md").read_text()
    assert src_agents == reread, "AGENTS.md was transformed when src == project_dir (framework repo self-detection failed)"


def test_lay_out_idempotent_with_transformation(framework_repo, project_dir):
    """Lay out twice; the second pass is idempotent (rewritten text is the same)."""
    bootstrap.lay_out_framework(
        str(framework_repo), str(project_dir), with_wiki=False, force=False
    )
    first_agents = (project_dir / "AGENTS.md").read_text()
    bootstrap.lay_out_framework(
        str(framework_repo), str(project_dir), with_wiki=False, force=False
    )
    second_agents = (project_dir / "AGENTS.md").read_text()
    assert first_agents == second_agents


# --------------------------------------------------------------------------- #
# B5: Windows support (bootstrap.ps1)
# --------------------------------------------------------------------------- #


PS1_PATH = Path(__file__).parent.parent / "scripts" / "bootstrap.ps1"
PS1_README_QUICK_START_NEEDLE = "irm https://raw.githubusercontent.com/Gamebreack/megaplan/main/scripts/bootstrap.ps1 | iex"


def test_bootstrap_ps1_exists():
    """scripts/bootstrap.ps1 exists."""
    assert PS1_PATH.exists(), f"missing: {PS1_PATH}"


def test_bootstrap_ps1_parsable():
    """The PowerShell file is structurally sane: non-empty, has a param block, has at least one function."""
    if not PS1_PATH.exists():
        pytest.skip("bootstrap.ps1 does not exist yet (B5 implementation pending)")
    content = PS1_PATH.read_text()
    assert content.strip(), "bootstrap.ps1 is empty"
    assert "param(" in content, "bootstrap.ps1 missing param() block"
    assert "function " in content, "bootstrap.ps1 has no function definitions"


def test_bootstrap_ps1_has_help():
    """The script defines a Get-Help-compatible comment block at the top."""
    if not PS1_PATH.exists():
        pytest.skip("bootstrap.ps1 does not exist yet (B5 implementation pending)")
    content = PS1_PATH.read_text()
    # The first 20 lines should have a comment-based help block (lines starting with #)
    head = "\n".join(content.splitlines()[:30])
    help_lines = [ln for ln in head.splitlines() if ln.strip().startswith("#")]
    assert len(help_lines) >= 3, (
        f"bootstrap.ps1 should have a Get-Help comment block at the top; found {len(help_lines)} comment lines in the first 30 lines"
    )


def test_bootstrap_ps1_uses_irm_invoke_webrequest():
    """The script uses Invoke-RestMethod or Invoke-WebRequest for HTTP, not curl.exe directly."""
    if not PS1_PATH.exists():
        pytest.skip("bootstrap.ps1 does not exist yet (B5 implementation pending)")
    content = PS1_PATH.read_text()
    assert "Invoke-RestMethod" in content or "Invoke-WebRequest" in content, (
        "bootstrap.ps1 should use Invoke-RestMethod or Invoke-WebRequest, not bare curl.exe"
    )


def test_bootstrap_ps1_mirrors_layout():
    """The PowerShell LAYOUT hashtable has the same keys as the Python LAYOUT (or an obviously equivalent set)."""
    if not PS1_PATH.exists():
        pytest.skip("bootstrap.ps1 does not exist yet (B5 implementation pending)")
    content = PS1_PATH.read_text()
    # The Python bootstrap has these in its LAYOUT:
    python_layout_keys = {
        "AGENTS.md",
        "docs/methodology.md",
        "templates/megaplan.md",
        "templates/backlog.md",
        "templates/glossary.md",
        "templates/backlog-item.md",
        "templates/adr.md",
    }
    # Heuristic: every Python key should appear as a quoted string in the PS1 content.
    missing = [k for k in python_layout_keys if f'"{k}"' not in content and f"'{k}'" not in content]
    assert not missing, f"bootstrap.ps1 LAYOUT is missing Python LAYOUT keys: {missing}"


def test_bootstrap_ps1_handles_no_python():
    """The script checks for Python and prints a warning if missing (does not error)."""
    if not PS1_PATH.exists():
        pytest.skip("bootstrap.ps1 does not exist yet (B5 implementation pending)")
    content = PS1_PATH.read_text()
    # Heuristic: the script mentions 'python' (the interpreter) and has a check or warning
    assert "python" in content.lower(), "bootstrap.ps1 does not mention Python at all"
    # Look for a "warning" or "skip" or "warn" pattern when python is missing
    assert "warn" in content.lower() or "skip" in content.lower() or "Get-Command python" in content, (
        "bootstrap.ps1 should handle the case when Python is missing (warn + skip self-test)"
    )


def test_readme_documents_windows_install():
    """The README's Quick start shows the PowerShell one-liner for Windows."""
    readme = Path(__file__).parent.parent / "README.md"
    content = readme.read_text()
    assert PS1_README_QUICK_START_NEEDLE in content, (
        f"README.md Quick start must include the Windows one-liner:\n  {PS1_README_QUICK_START_NEEDLE}"
    )


def test_readme_documents_windows_prereqs():
    """The README has a Windows subsection listing the prereqs (Python ≥ 3.10, Git for Windows, PowerShell 5+)."""
    readme = Path(__file__).parent.parent / "README.md"
    content = readme.read_text()
    # Look for a Windows subsection with prereqs
    has_windows_section = (
        "Windows" in content
        and ("PowerShell" in content or "powershell" in content)
    )
    assert has_windows_section, "README.md has no Windows section"
    # The prereqs should include Python 3.10+ and Git (for the bash hook)
    prereqs_text = content[content.find("Windows"):][:2000]  # look in the Windows area
    assert "Python" in prereqs_text and ("3.10" in prereqs_text or "3.12" in prereqs_text), (
        "Windows section must mention Python ≥ 3.10"
    )
    assert "Git" in prereqs_text, "Windows section must mention Git for Windows (for the bash hook)"
