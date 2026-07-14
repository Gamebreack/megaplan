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
