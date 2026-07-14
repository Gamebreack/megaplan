import os
import pytest
from unittest.mock import patch, mock_open
import sys

# Add scripts directory to path to import validate_backlog
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
)
import validate_backlog


def test_parse_id_parts():
    assert validate_backlog.parse_id_parts("0-B1") == ("0", 1)
    assert validate_backlog.parse_id_parts("A-B12") == ("A", 12)
    assert validate_backlog.parse_id_parts("Cycle1-B3") == ("Cycle1", 3)
    assert validate_backlog.parse_id_parts("A-B1.B2") == ("A", 1)
    assert validate_backlog.parse_id_parts("invalid") == (None, None)


def test_cycle_key():
    assert validate_backlog.cycle_key("0") == ("", 0, "")
    assert validate_backlog.cycle_key("A") == ("A",)
    assert validate_backlog.cycle_key("Cycle1") == ("CYCLE", 1, "")
    assert validate_backlog.cycle_key("Cycle10") == ("CYCLE", 10, "")
    assert validate_backlog.cycle_key("Cycle2") == ("CYCLE", 2, "")
    # Check that sorting cycle names works correctly with cycle_key
    cycles = ["Cycle10", "Cycle2", "0", "A", "Cycle1"]
    sorted_cycles = sorted(cycles, key=validate_backlog.cycle_key)
    assert sorted_cycles == ["0", "A", "Cycle1", "Cycle2", "Cycle10"]


def test_parse_markdown_section():
    content = """# Header

## Metadata
| Field | Value |
|---|---|
| Status | in-progress |

## Scope
- Task 1
- Task 2
"""
    metadata = validate_backlog.parse_markdown_section(content, "Metadata")
    assert "Status | in-progress" in metadata

    scope = validate_backlog.parse_markdown_section(content, "Scope")
    assert "- Task 1" in scope
    assert "- Task 2" in scope

    nonexistent = validate_backlog.parse_markdown_section(content, "Nonexistent")
    assert nonexistent == ""


def test_parse_detail_metadata():
    content = """# B-item

## Metadata
| Field | Value |
|---|---|
| Status | done |
| Workflow Step | Complete |
"""
    with patch("builtins.open", mock_open(read_data=content)):
        with patch("os.path.exists", return_value=True):
            metadata = validate_backlog.parse_detail_metadata("dummy_path")
            assert metadata == {"status": "done", "workflow step": "complete"}


def test_parse_backlog_index():
    backlog_content = """# Backlog

## Index
| ID | Title | Status | Owner | Depends on | Detail |
|----|-------|--------|-------|------------|--------|
| 0-B1 | Scaffold | done | team | — | [0-B1](0-B1.md) |
| A-B1 | Feature | pending | team | 0-B1 | [A-B1](A-B1.md) |
"""
    with patch("builtins.open", mock_open(read_data=backlog_content)):
        with patch("os.path.exists", return_value=True):
            items = validate_backlog.parse_backlog_index("dummy_path")
            assert len(items) == 2
            assert items[0]["id"] == "0-B1"
            assert items[0]["status"] == "done"
            assert items[1]["id"] == "A-B1"
            assert items[1]["status"] == "pending"
            assert items[1]["depends on"] == "0-B1"


def test_validate_glossary_single_success():
    glossary_content = """# Glossary

## Terms
| Term | Definition | Canonical example | Common confusions |
|------|------------|-------------------|-------------------|
| Client | A user program | `client.connect()` | Synonyms: consumer |
"""

    def mock_exists(path):
        if path.endswith("glossary-map.md"):
            return False
        if path.endswith("glossary.md"):
            return True
        return False

    with patch("builtins.open", mock_open(read_data=glossary_content)):
        with patch("os.path.exists", mock_exists):
            errors = validate_backlog.validate_glossary("dummy_root")
            assert len(errors) == 0


def test_validate_glossary_single_failure_no_terms():
    glossary_content = """# Glossary

## Terms
| Term | Definition | Canonical example | Common confusions |
|------|------------|-------------------|-------------------|
| | | | |
"""

    def mock_exists(path):
        if path.endswith("glossary-map.md"):
            return False
        if path.endswith("glossary.md"):
            return True
        return False

    with patch("builtins.open", mock_open(read_data=glossary_content)):
        with patch("os.path.exists", mock_exists):
            errors = validate_backlog.validate_glossary("dummy_root")
            assert len(errors) > 0
            assert any("contains no terms" in err for err in errors)


def test_validate_glossary_multi_domain_success():
    map_content = """# Glossary Map
| Domain | Path |
|---|---|
| Domain A | [glossary-a.md](docs/megaplan/glossary-a.md) |
| Domain B | [glossary-b.md](docs/megaplan/glossary-b.md) |
"""
    glossary_a_content = """# Glossary A
## Terms
| Term | Definition | Canonical example | Common confusions |
|---|---|---|---|
| Account | User login | `Account()` | — |
"""
    glossary_b_content = """# Glossary B
## Terms
| Term | Definition | Canonical example | Common confusions |
|---|---|---|---|
| Billing | Billing state | `Billing()` | — |
"""

    def mock_exists(path):
        return True

    class MockOpen:
        def __init__(self, path, *args, **kwargs):
            self.path = path

        def __enter__(self):
            if "glossary-map.md" in self.path:
                return mock_open(read_data=map_content).return_value
            elif "glossary-a.md" in self.path:
                return mock_open(read_data=glossary_a_content).return_value
            elif "glossary-b.md" in self.path:
                return mock_open(read_data=glossary_b_content).return_value
            return mock_open(read_data="").return_value

        def __exit__(self, *args):
            pass

    with patch("builtins.open", MockOpen):
        with patch("os.path.exists", mock_exists):
            errors = validate_backlog.validate_glossary("dummy_root")
            assert len(errors) == 0


def test_main_duplicate_id_detection():
    mock_items = [
        {"id": "0-B1", "status": "done"},
        {"id": "0-B1", "status": "done"},
    ]
    with patch("sys.argv", ["validate_backlog.py", "dummy_root"]):
        with patch("validate_backlog.parse_backlog_index", return_value=mock_items):
            with patch("validate_backlog.validate_glossary", return_value=[]):
                with patch("os.path.exists", return_value=True):
                    with patch("os.listdir", return_value=[]):
                        with pytest.raises(SystemExit) as excinfo:
                            with patch(
                                "validate_backlog.parse_detail_status",
                                return_value="done",
                            ):
                                validate_backlog.main()
                        assert excinfo.value.code == 1


def test_main_workflow_step_mismatch():
    import builtins

    mock_items = [
        {"id": "0-B1", "status": "in-progress", "workflow step": "red"},
    ]
    mock_metadata = {"status": "in-progress", "workflow step": "green"}

    original_open = builtins.open

    def custom_open(file, mode="r", *args, **kwargs):
        if "SPEC.md" in str(file):
            return mock_open(read_data="compiled from 0-B1.md").return_value
        return original_open(file, mode, *args, **kwargs)

    with patch("sys.argv", ["validate_backlog.py", "dummy_root"]):
        with patch("validate_backlog.parse_backlog_index", return_value=mock_items):
            with patch("validate_backlog.validate_glossary", return_value=[]):
                with patch("os.path.exists", return_value=True):
                    with patch("os.listdir", return_value=[]):
                        with patch("os.path.getmtime", return_value=100):
                            with patch("builtins.open", custom_open):
                                with patch(
                                    "validate_backlog.parse_detail_metadata",
                                    return_value=mock_metadata,
                                ):
                                    with patch(
                                        "validate_backlog.parse_detail_status",
                                        return_value="in-progress",
                                    ):
                                        with pytest.raises(SystemExit) as excinfo:
                                            validate_backlog.main()
                                        assert excinfo.value.code == 1
