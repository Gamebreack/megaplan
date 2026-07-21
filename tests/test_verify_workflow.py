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
