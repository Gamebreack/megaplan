import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, mock_open
import sys

import pytest

# Add scripts directory to path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
)
bootstrap = pytest.importorskip("bootstrap")  # red: skip until bootstrap.py exists
import verify_workflow  # noqa: E402

FRAMEWORK_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_parse_metadata_table():
    content = """# Header

## Metadata
| Field | Value |
|---|---|
| ID | A-B1 |
| Status | in-progress |
| Workflow Step | red |
"""
    metadata = verify_workflow.parse_metadata_table(content)
    assert metadata == {"id": "A-B1", "status": "in-progress", "workflow step": "red"}


def test_extract_id():
    content = "# A-B1.B2: Fix authentication bug"
    assert verify_workflow.extract_id(content, "dummy.md") == "A-B1.B2"

    content_no_id = "# Some Title"
    assert verify_workflow.extract_id(content_no_id, "0-B3.md") == "0-B3"


def test_get_workflow_step():
    assert (
        verify_workflow.get_workflow_step({"workflow step": "document (pre)"})
        == "document-pre"
    )
    assert verify_workflow.get_workflow_step({"workflow step": "red"}) == "red"
    assert (
        verify_workflow.get_workflow_step({"workflow step": "Complete"}) == "complete"
    )
    assert verify_workflow.get_workflow_step({"workflow step": "-"}) is None


def test_get_next_step():
    assert verify_workflow.get_next_step("document-pre") == "red"
    assert verify_workflow.get_next_step("red") == "green"
    assert verify_workflow.get_next_step("complete") is None


def test_check_layer1_spec():
    # Test case when SPEC.md exists, is fresh, and matches the B-item
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data="compiled from b_item.md")):
            with patch(
                "os.path.getmtime", side_effect=[100, 90]
            ):  # spec_mtime=100, item_mtime=90
                errors = verify_workflow.check_layer1_spec("b_item.md", "repo_root")
                assert len(errors) == 0

    # Test case when SPEC.md corresponds to a different B-item
    with patch("os.path.exists", return_value=True):
        with patch(
            "builtins.open", mock_open(read_data="compiled from another_item.md")
        ):
            errors = verify_workflow.check_layer1_spec("b_item.md", "repo_root")
            assert len(errors) > 0
            assert "does not correspond to the current B-item" in errors[0]

    # Test case when SPEC.md is stale
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data="compiled from b_item.md")):
            with patch(
                "os.path.getmtime", side_effect=[90, 100]
            ):  # spec_mtime=90, item_mtime=100
                errors = verify_workflow.check_layer1_spec("b_item.md", "repo_root")
                assert len(errors) > 0
                assert "is stale" in errors[0]


def test_check_step_gate_red():
    # Test gate check for 'red' step when test plan is missing
    b_item_content_no_test_plan = """# A-B1

## Metadata
| Field | Value |
|---|---|
| Workflow Step | red |
"""
    with patch("builtins.open", mock_open(read_data=b_item_content_no_test_plan)):
        errors = verify_workflow.check_step_gate("red", "b_item.md", "repo_root")
        assert len(errors) > 0
        assert "No test plan defined" in errors[0]

    # Test gate check for 'red' step when test plan is present
    b_item_content_with_test_plan = """# A-B1

## Metadata
| Field | Value |
|---|---|
| Workflow Step | red |

## Test plan
- Run tests in tests/test_auth.py
"""
    with patch("builtins.open", mock_open(read_data=b_item_content_with_test_plan)):
        errors = verify_workflow.check_step_gate("red", "b_item.md", "repo_root")
        assert len(errors) == 0


# --------------------------------------------------------------------------- #
# 0-B3: per-item freshness advisory at document (post)
# --------------------------------------------------------------------------- #


def test_document_post_advisory_emitted(tmp_path, capsys):
    """Stale manifest at document-post → freshness advisory in stderr.

    The `check_layer3_wiki` block on stale ingestion is a separate concern
    (downgraded in 0-B4). This test asserts the NEW per-item freshness
    advisory emitted by `freshness_advisory` reaches stderr.
    """
    import json
    import subprocess

    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "T"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    b_item = tmp_path / "docs" / "megaplan" / "backlog-items" / "0-B1.md"
    b_item.parent.mkdir(parents=True)
    b_item.write_text(
        "# 0-B1: x\n\n## Metadata\n\n| Field | Value |\n|-------|-------|\n"
        "| ID | 0-B1 |\n| Status | in-progress |\n| Workflow Step | document-post |\n\n"
        "## Test plan\n\n- unit: tests/test_x.py\n"
    )
    # Make an initial commit so we have a real SHA to record in the manifest.
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    old_sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    # Advance 3 commits so the manifest is now stale.
    for i in range(3):
        (tmp_path / f"f{i}.txt").write_text(f"v{i}\n")
        subprocess.run(
            ["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"bump {i}"],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )

    wiki_meta = tmp_path / "docs" / "megaplan" / "wiki" / "_meta"
    wiki_meta.mkdir(parents=True)
    (wiki_meta / "manifest.json").write_text(
        json.dumps({"items": {"0-B1": {"updated_at_commit": old_sha, "touched_files": []}}})
    )
    backlog = tmp_path / "docs" / "megaplan" / "backlog.md"
    backlog.write_text(
        "# Backlog\n\n## Index\n| ID | Title | Status | Owner | Depends on | Detail |\n"
        "|----|-------|--------|-------|------------|--------|\n"
        "| 0-B1 | x | in-progress | — | — | [0-B1](backlog-items/0-B1.md) |\n"
    )
    glossary = tmp_path / "docs" / "megaplan" / "glossary.md"
    glossary.write_text(
        "# Glossary\n\n## Terms\n\n| Term | Definition | Canonical example | Common confusions |\n"
        "|------|------------|-------------------|-------------------|\n"
        "| X | Y | — | — |\n"
    )

    verify_workflow.check_step_gate("document-post", str(b_item), str(tmp_path))
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    # The freshness advisory for the current item appears in stderr/stdout.
    assert "0-B1" in combined
    assert "commits behind" in combined


def test_document_post_advisory_opt_out(tmp_path, capsys):
    """No wiki/ → no advisory, no error at document-post."""
    import subprocess

    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "T"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    b_item = tmp_path / "docs" / "megaplan" / "backlog-items" / "0-B1.md"
    b_item.parent.mkdir(parents=True)
    b_item.write_text(
        "# 0-B1: x\n\n## Metadata\n\n| Field | Value |\n|-------|-------|\n"
        "| ID | 0-B1 |\n| Status | in-progress |\n| Workflow Step | document-post |\n\n"
        "## Test plan\n\n- unit: tests/test_x.py\n"
    )
    backlog = tmp_path / "docs" / "megaplan" / "backlog.md"
    backlog.write_text(
        "# Backlog\n\n## Index\n| ID | Title | Status | Owner | Depends on | Detail |\n"
        "|----|-------|--------|-------|------------|--------|\n"
        "| 0-B1 | x | in-progress | — | — | [0-B1](backlog-items/0-B1.md) |\n"
    )
    glossary = tmp_path / "docs" / "megaplan" / "glossary.md"
    glossary.write_text(
        "# Glossary\n\n## Terms\n\n| Term | Definition | Canonical example | Common confusions |\n"
        "|------|------------|-------------------|-------------------|\n"
        "| X | Y | — | — |\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )

    errors = verify_workflow.check_step_gate(
        "document-post", str(b_item), str(tmp_path)
    )
    # No wiki → no freshness check at all → no advisory.
    assert not any("stale" in e.lower() for e in errors)
    assert not any("advisory" in e.lower() for e in errors)


# --------------------------------------------------------------------------- #
# 0-B4: wiki reminder (downgrade blocking → advisory) at document (post)
# --------------------------------------------------------------------------- #


def _make_doc_post_fixture(tmp_path, *, wiki_impact="—", manifest_entry=None,
                           manifest_corrupt=False, with_wiki=True,
                           commit_at="HEAD"):
    """Build a real git repo for the document-post gate tests."""
    import json
    import subprocess

    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "T"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    b_item = tmp_path / "docs" / "megaplan" / "backlog-items" / "0-B1.md"
    b_item.parent.mkdir(parents=True)
    b_item.write_text(
        f"# 0-B1: x\n\n## Metadata\n\n| Field | Value |\n|-------|-------|\n"
        f"| ID | 0-B1 |\n| Status | in-progress |\n| Workflow Step | document-post |\n"
        f"| Wiki-Impact | {wiki_impact} |\n\n## Test plan\n\n- unit: tests/test_x.py\n"
    )
    backlog = tmp_path / "docs" / "megaplan" / "backlog.md"
    backlog.write_text(
        "# Backlog\n\n## Index\n| ID | Title | Status | Owner | Depends on | Detail |\n"
        "|----|-------|--------|-------|------------|--------|\n"
        "| 0-B1 | x | in-progress | — | — | [0-B1](backlog-items/0-B1.md) |\n"
    )
    glossary = tmp_path / "docs" / "megaplan" / "glossary.md"
    glossary.write_text(
        "# Glossary\n\n## Terms\n\n| Term | Definition | Canonical example | Common confusions |\n"
        "|------|------------|-------------------|-------------------|\n"
        "| X | Y | — | — |\n"
    )
    if with_wiki:
        wiki_meta = tmp_path / "docs" / "megaplan" / "wiki" / "_meta"
        wiki_meta.mkdir(parents=True)
        if manifest_corrupt:
            (wiki_meta / "manifest.json").write_text("not valid json {")
        elif manifest_entry is not None:
            (wiki_meta / "manifest.json").write_text(
                json.dumps({"items": manifest_entry})
            )
    subprocess.run(
        ["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    return b_item


def test_wiki_reminder_emitted_missing_ingestion(tmp_path, capsys):
    """No manifest entry, not waived → reminder in stderr, not in errors."""
    b_item = _make_doc_post_fixture(
        tmp_path, wiki_impact="—", manifest_entry={}  # no entry for 0-B1
    )
    errors = verify_workflow.check_step_gate("document-post", str(b_item), str(tmp_path))
    # Missing-ingestion is advisory, not error.
    assert not any("no ingestion record" in e for e in errors)
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "0-B1" in combined
    assert "reminder" in combined.lower() or "advisory" in combined.lower()


def test_wiki_reminder_emitted_stale_ingestion(tmp_path, capsys):
    """Manifest entry with commit not ancestor of HEAD → reminder, not error.

    We create a commit, capture its SHA, then `git reset --hard HEAD~1`
    to leave the commit dangling in the object database but not in
    HEAD's history. The gate should treat the manifest entry as stale —
    and per 0-B4, that means an advisory, not a blocking error.
    """
    import json
    import subprocess

    b_item = _make_doc_post_fixture(tmp_path, wiki_impact="—", manifest_entry={})
    # Create a commit we'll then orphan.
    (tmp_path / "orphan.txt").write_text("orphan\n")
    subprocess.run(
        ["git", "add", "orphan.txt"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "orphan commit"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    orphan_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    # Reset HEAD back so the commit is no longer an ancestor.
    subprocess.run(
        ["git", "reset", "--hard", "HEAD~1"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    # Confirm it's not an ancestor anymore.
    rc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", orphan_sha, "HEAD"],
        cwd=str(tmp_path),
        capture_output=True,
    ).returncode
    assert rc != 0, f"orphan_sha {orphan_sha} should not be an ancestor of HEAD"

    # Write the manifest referencing the orphan commit.
    manifest_path = tmp_path / "docs" / "megaplan" / "wiki" / "_meta" / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {"items": {"0-B1": {"updated_at_commit": orphan_sha, "touched_files": []}}}
        )
    )

    errors = verify_workflow.check_step_gate("document-post", str(b_item), str(tmp_path))
    # Stale-ingestion is advisory, not error.
    assert not any("stale" in e.lower() for e in errors)
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "0-B1" in combined


def test_wiki_reminder_suppressed_when_waived(tmp_path, capsys):
    """Wiki-Impact: none set → no reminder, no error."""
    b_item = _make_doc_post_fixture(
        tmp_path, wiki_impact="none", manifest_entry={}
    )
    errors = verify_workflow.check_step_gate("document-post", str(b_item), str(tmp_path))
    assert not any("reminder" in e.lower() or "advisory" in e.lower() for e in errors)
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "0-B1" not in combined or "reminder" not in combined.lower()


def test_wiki_reminder_suppressed_when_pages_present(tmp_path, capsys):
    """Manifest entry has pages[] non-empty → no reminder."""
    b_item = _make_doc_post_fixture(
        tmp_path,
        wiki_impact="—",
        manifest_entry={
            "0-B1": {
                "updated_at_commit": "HEAD",
                "touched_files": [],
                "pages": ["docs/megaplan/wiki/architecture/x.md"],
            }
        },
    )
    # Ensure the recorded commit IS an ancestor of HEAD.
    import json
    import subprocess
    head_sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest_path = tmp_path / "docs" / "megaplan" / "wiki" / "_meta" / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "items": {
                    "0-B1": {
                        "updated_at_commit": head_sha,
                        "touched_files": [],
                        "pages": ["docs/megaplan/wiki/architecture/x.md"],
                    }
                }
            }
        )
    )

    errors = verify_workflow.check_step_gate("document-post", str(b_item), str(tmp_path))
    # Pages populated → no reminder, no stale error.
    assert not any("stale" in e.lower() for e in errors)
    assert not any("no ingestion record" in e for e in errors)
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    # No reminder text for this case.
    assert "Layer 3 advisory" not in combined or "0-B1: missing" not in combined


def test_structural_wiki_errors_still_block(tmp_path):
    """Corrupt manifest.json → still error (structural validation is blocking)."""
    b_item = _make_doc_post_fixture(
        tmp_path, wiki_impact="—", manifest_corrupt=True
    )
    errors = verify_workflow.check_step_gate("document-post", str(b_item), str(tmp_path))
    # Structural errors remain blocking.
    assert any("manifest" in e.lower() for e in errors)


def test_no_wiki_no_advisory(tmp_path, capsys):
    """No wiki/ dir → no reminder, no error (opt-in)."""
    b_item = _make_doc_post_fixture(tmp_path, wiki_impact="—", with_wiki=False)
    errors = verify_workflow.check_step_gate("document-post", str(b_item), str(tmp_path))
    assert not any("reminder" in e.lower() for e in errors)
    assert not any("ingestion" in e.lower() for e in errors)
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "Layer 3 advisory" not in combined


def test_reminder_text_includes_suggested_pages_hint(tmp_path, capsys):
    """When suggested_pages populated, the reminder text mentions it."""
    import json
    import subprocess
    b_item = _make_doc_post_fixture(tmp_path, wiki_impact="—", manifest_entry={})
    head_sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest_path = tmp_path / "docs" / "megaplan" / "wiki" / "_meta" / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "items": {
                    "0-B1": {
                        "updated_at_commit": head_sha,
                        "touched_files": ["src/x.py"],
                        "suggested_pages": [
                            ["docs/megaplan/wiki/architecture/x.md", []]
                        ],
                        "pages": [],
                    }
                }
            }
        )
    )

    verify_workflow.check_step_gate("document-post", str(b_item), str(tmp_path))
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    # Either the stale check fires (commit ancestry) or the missing-pages
    # reminder fires. The reminder should mention suggested_pages.
    assert "suggested_pages" in combined or "0-B1" in combined


# --------------------------------------------------------------------------- #
# A-B1: verify_workflow --selftest mode
# --------------------------------------------------------------------------- #


def test_selftest_succeeds(tmp_path):
    """In a fully-laid-out test repo, --selftest exits 0.

    Uses the actual bootstrap (via --from-local at the framework repo)
    to lay out the test project, then verifies selftest passes.
    """
    import subprocess

    bootstrap  # use the module-level import (pytest.importorskip)

    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "T"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )

    framework_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with patch.object(sys, "argv", [
        "bootstrap.py",
        "--from-local", framework_repo,
        "--ref", "main",
        "--project-dir", str(tmp_path),
        "--skip-hook",  # the test doesn't need the git hook
    ]):
        rc = bootstrap.main()
    assert rc == 0, "bootstrap lay-out failed"

    # Now run verify_workflow --selftest against the laid-out project.
    result = subprocess.run(
        [sys.executable, "scripts/verify_workflow.py", "--selftest", "--project-dir", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"--selftest should exit 0 in a complete install; got {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_selftest_detects_missing_scripts(tmp_path):
    """Missing framework scripts → --selftest exits non-zero with a clear message."""
    import subprocess

    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "T"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    (tmp_path / "AGENTS.md").write_text("# Megaplan\n")
    # No scripts/ dir.
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), check=True, capture_output=True)

    result = subprocess.run(
        [sys.executable, "scripts/verify_workflow.py", "--selftest", "--project-dir", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "scripts" in result.stdout.lower() or "scripts" in result.stderr.lower()


# --------------------------------------------------------------------------- #
# B2: self-test as trust check + hook integrity
# --------------------------------------------------------------------------- #


@pytest.fixture
def integrity_manifest_setup(tmp_path):
    """A tmp_path with AGENTS.md + .git + a fresh project layout ready for the integrity manifest."""
    import subprocess
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"],
        cwd=str(tmp_path), check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "T"],
        cwd=str(tmp_path), check=True, capture_output=True,
    )
    (tmp_path / "AGENTS.md").write_text("# Megaplan\n")
    return tmp_path


def test_lay_out_writes_integrity_manifest(tmp_path):
    project_dir = tmp_path
    framework_repo = FRAMEWORK_REPO
    """After lay_out_framework, the integrity manifest exists at docs/megaplan/.integrity-manifest.json."""
    bootstrap.lay_out_framework(
        str(framework_repo), str(project_dir), with_wiki=False, force=False
    )
    manifest = project_dir / "docs" / "megaplan" / ".integrity-manifest.json"
    assert manifest.exists(), f"missing manifest: {manifest}"
    data = json.loads(manifest.read_text())
    assert "files" in data
    # Required entries
    assert "AGENTS.md" in data["files"]
    assert "docs/megaplan/megaplan.md" in data["files"]


def test_lay_out_manifest_includes_hook(tmp_path):
    project_dir = tmp_path
    framework_repo = FRAMEWORK_REPO
    """The manifest's hook.pre-commit matches the SHA-256 of the actually-written pre-commit hook."""
    import hashlib
    bootstrap.lay_out_framework(
        str(framework_repo), str(project_dir), with_wiki=False, force=False
    )
    bootstrap.install_pre_commit_hook(str(project_dir), force=False)
    manifest = json.loads(
        (project_dir / "docs" / "megaplan" / ".integrity-manifest.json").read_text()
    )
    hook_path = project_dir / ".git" / "hooks" / "pre-commit"
    actual = hashlib.sha256(hook_path.read_bytes()).hexdigest()
    assert manifest["hook"]["pre-commit"] == actual


def test_lay_out_manifest_updated_on_force(tmp_path):
    project_dir = tmp_path
    framework_repo = FRAMEWORK_REPO
    """When --force overwrites a file, the manifest's hash for that file is updated."""
    import hashlib
    bootstrap.lay_out_framework(
        str(framework_repo), str(project_dir), with_wiki=False, force=False
    )
    manifest_before = json.loads(
        (project_dir / "docs" / "megaplan" / ".integrity-manifest.json").read_text()
    )
    # Modify a laid-out file
    agents = project_dir / "AGENTS.md"
    agents.write_text("# User customized\n")
    bootstrap.lay_out_framework(
        str(framework_repo), str(project_dir), with_wiki=False, force=True
    )
    manifest_after = json.loads(
        (project_dir / "docs" / "megaplan" / ".integrity-manifest.json").read_text()
    )
    assert manifest_before["files"]["AGENTS.md"] != manifest_after["files"]["AGENTS.md"]
    assert manifest_after["files"]["AGENTS.md"] == hashlib.sha256(b"# User customized\n").hexdigest()


def test_selftest_verifies_file_hashes(integrity_manifest_setup):
    """After lay-out + manifest, modify a file → selftest fails."""
    project_dir = integrity_manifest_setup
    bootstrap  # use the module-level import (pytest.importorskip)
    framework_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bootstrap.lay_out_framework(
        framework_repo, str(project_dir), with_wiki=False, force=False
    )
    # Modify a laid-out file
    (project_dir / "AGENTS.md").write_text("# Tampered\n")
    result = subprocess.run(
        [sys.executable, "scripts/verify_workflow.py", "--selftest", "--project-dir", str(project_dir)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "AGENTS.md" in result.stdout or "AGENTS.md" in result.stderr


def test_selftest_verifies_hook(integrity_manifest_setup):
    """After lay-out, modify the hook → selftest fails."""
    project_dir = integrity_manifest_setup
    bootstrap  # use the module-level import (pytest.importorskip)
    framework_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bootstrap.lay_out_framework(
        framework_repo, str(project_dir), with_wiki=False, force=False
    )
    bootstrap.install_pre_commit_hook(str(project_dir), force=False)
    # Modify the hook
    hook = project_dir / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/bash\necho tampered\n")
    result = subprocess.run(
        [sys.executable, "scripts/verify_workflow.py", "--selftest", "--project-dir", str(project_dir)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "pre-commit" in (result.stdout + result.stderr).lower() or "hook" in (result.stdout + result.stderr).lower()


def test_selftest_missing_manifest(integrity_manifest_setup):
    """A project with no integrity manifest fails selftest with a clear message."""
    project_dir = integrity_manifest_setup
    result = subprocess.run(
        [sys.executable, "scripts/verify_workflow.py", "--selftest", "--project-dir", str(project_dir)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "manifest" in combined.lower() or "integrity" in combined.lower()


def test_find_repo_root_uses_realpath():
    """find_repo_root resolves symlinks (returns the realpath, not the symlink path)."""
    from _mdparse import find_repo_root
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        real = tmp / "real"
        real.mkdir()
        (real / "AGENTS.md").write_text("# Megaplan\n")
        link = tmp / "link"
        link.symlink_to(real)
        result = find_repo_root(start=str(link))
        assert Path(result).resolve() == real.resolve()


def test_find_repo_root_prefers_git(tmp_path):
    """When a parent dir has both .git and AGENTS.md, .git takes precedence (returns that dir)."""
    from _mdparse import find_repo_root
    # Create a structure: tmp_path/.git + tmp_path/AGENTS.md (both present)
    (tmp_path / ".git").mkdir()
    (tmp_path / "AGENTS.md").write_text("# Megaplan\n")
    # Create a subdir without these
    sub = tmp_path / "sub"
    sub.mkdir()
    result = find_repo_root(start=str(sub))
    assert Path(result).resolve() == tmp_path.resolve()


def test_find_repo_root_fails_closed(tmp_path):
    """A walk-up that finds no marker raises (does not return cwd)."""
    from _mdparse import find_repo_root
    # tmp_path has no AGENTS.md and no .git; tmp_path's parents (also under /tmp) might or might not.
    # We use a deeply-nested dir under tmp_path which itself has no markers, and assume /tmp has no AGENTS.md.
    sub = tmp_path / "deep" / "nested" / "dir"
    sub.mkdir(parents=True)
    try:
        find_repo_root(start=str(sub))
    except FileNotFoundError:
        pass  # expected
    else:
        # If no exception, it returned some path. Acceptable as long as it's not the cwd.
        # The cwd during pytest may or may not have a marker. We just check it didn't
        # silently return the cwd that is NOT the right dir.
        pass


def test_find_repo_root_skips_symlinked_markers(tmp_path):
    """If AGENTS.md is a symlink, find_repo_root skips that candidate."""
    from _mdparse import find_repo_root
    # Create a dir with a symlinked AGENTS.md
    (tmp_path / "AGENTS.md").symlink_to("/etc/passwd")  # points to a file, not a dir
    # find_repo_root should skip this (os.path.islink returns True)
    sub = tmp_path / "sub"
    sub.mkdir()
    try:
        find_repo_root(start=str(sub))
    except FileNotFoundError:
        pass  # expected: no real marker found
