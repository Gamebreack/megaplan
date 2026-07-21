import os
from unittest.mock import patch, mock_open
import sys

# Add scripts directory to path to import verify_workflow
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
)
import verify_workflow


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
