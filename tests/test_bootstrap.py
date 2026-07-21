"""Tests for `scripts/bootstrap.py` (dumb-install bootstrap)."""
import io
import json
import os
import sys
import tarfile
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
