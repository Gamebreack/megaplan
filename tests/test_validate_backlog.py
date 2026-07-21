import json
import os
import subprocess
import sys
from unittest.mock import mock_open, patch

import pytest

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


# --------------------------------------------------------------------------- #
# 0-B3: waiver + freshness advisories
# --------------------------------------------------------------------------- #


def _git(cwd, *args, check=True):
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


def _b_item_md(item_id, wiki_impact="—"):
    """Render a minimal valid B-item detail file body."""
    return (
        f"# {item_id}: Test item\n"
        "\n"
        "## Metadata\n"
        "\n"
        "| Field | Value |\n"
        "|-------|-------|\n"
        f"| ID | {item_id} |\n"
        "| Status | done |\n"
        f"| Wiki-Impact | {wiki_impact} |\n"
    )


def _init_repo_with_b_items(tmp_path, items):
    """Create a git repo with `items` = [(cycle_id, wiki_impact), ...] B-items."""
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@test.local")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "config", "commit.gpgsign", "false")

    items_dir = tmp_path / "docs" / "megaplan" / "backlog-items"
    items_dir.mkdir(parents=True)
    for item_id, wi in items:
        (items_dir / f"{item_id}.md").write_text(_b_item_md(item_id, wi))

    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "init")
    return tmp_path


def test_waiver_rate_zero(tmp_path):
    """Cycle with 0/3 waived → advisory reports '0/3 (0%)'."""
    repo = _init_repo_with_b_items(
        tmp_path, [("0-B1", "—"), ("0-B2", "—"), ("0-B3", "—")]
    )
    advisories = validate_backlog.waiver_advisory(str(repo), cycle_id="0")
    text = " ".join(advisories)
    assert "0/3" in text
    assert "0%" in text


def test_waiver_rate_partial(tmp_path):
    """Cycle with 2/4 waived → advisory reports '2/4 (50%)'."""
    repo = _init_repo_with_b_items(
        tmp_path,
        [
            ("0-B1", "none"),
            ("0-B2", "—"),
            ("0-B3", "none"),
            ("0-B4", "—"),
        ],
    )
    advisories = validate_backlog.waiver_advisory(str(repo), cycle_id="0")
    text = " ".join(advisories)
    assert "2/4" in text
    assert "50%" in text


def test_waiver_rate_all(tmp_path):
    """Cycle with 3/3 waived → advisory reports '3/3 (100%)'."""
    repo = _init_repo_with_b_items(
        tmp_path, [("0-B1", "none"), ("0-B2", "none"), ("0-B3", "none")]
    )
    advisories = validate_backlog.waiver_advisory(str(repo), cycle_id="0")
    text = " ".join(advisories)
    assert "3/3" in text
    assert "100%" in text


def test_waiver_rate_no_cycle(tmp_path):
    """No matching cycle → empty advisory list."""
    repo = _init_repo_with_b_items(tmp_path, [("A-B1", "none")])
    advisories = validate_backlog.waiver_advisory(str(repo), cycle_id="0")
    assert advisories == []


def test_freshness_zero_lag(tmp_path):
    """Manifest item at HEAD → no advisory for that item."""
    repo = _init_repo_with_b_items(tmp_path, [("0-B1", "none")])
    wiki_meta = repo / "docs" / "megaplan" / "wiki" / "_meta"
    wiki_meta.mkdir(parents=True)
    head_sha = _git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    manifest = {"items": {"0-B1": {"updated_at_commit": head_sha, "touched_files": []}}}
    (wiki_meta / "manifest.json").write_text(json.dumps(manifest))

    advisories = validate_backlog.freshness_advisory(str(repo))
    assert advisories == []


def test_freshness_lag_reported(tmp_path):
    """Manifest item 3 commits behind → advisory says '3 commits behind'."""
    repo = _init_repo_with_b_items(tmp_path, [("0-B1", "none")])
    wiki_meta = repo / "docs" / "megaplan" / "wiki" / "_meta"
    wiki_meta.mkdir(parents=True)
    head_sha = _git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
    # Advance 3 commits ahead of the recorded one.
    for i in range(3):
        (repo / "f.txt").write_text(f"v{i}\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", f"bump {i}")
    manifest = {"items": {"0-B1": {"updated_at_commit": head_sha, "touched_files": []}}}
    (wiki_meta / "manifest.json").write_text(json.dumps(manifest))

    advisories = validate_backlog.freshness_advisory(str(repo))
    text = " ".join(advisories)
    assert "0-B1" in text
    assert "3 commits behind" in text


def test_freshness_unknown_commit(tmp_path):
    """Manifest item with updated_at_commit == 'unknown' → no advisory."""
    repo = _init_repo_with_b_items(tmp_path, [("0-B1", "none")])
    wiki_meta = repo / "docs" / "megaplan" / "wiki" / "_meta"
    wiki_meta.mkdir(parents=True)
    manifest = {
        "items": {"0-B1": {"updated_at_commit": "unknown", "touched_files": []}}
    }
    (wiki_meta / "manifest.json").write_text(json.dumps(manifest))

    advisories = validate_backlog.freshness_advisory(str(repo))
    assert advisories == []


def test_no_wiki_no_freshness_advisory(tmp_path):
    """No wiki dir → freshness_advisory returns [] (opt-in)."""
    repo = _init_repo_with_b_items(tmp_path, [("0-B1", "none")])
    advisories = validate_backlog.freshness_advisory(str(repo))
    assert advisories == []


def test_no_manifest_no_freshness_advisory(tmp_path):
    """wiki/ exists, no manifest.json → freshness_advisory returns []."""
    repo = _init_repo_with_b_items(tmp_path, [("0-B1", "none")])
    (repo / "docs" / "megaplan" / "wiki" / "_meta").mkdir(parents=True)
    advisories = validate_backlog.freshness_advisory(str(repo))
    assert advisories == []


def test_advisories_dont_block_main(tmp_path, capsys):
    """A high waiver rate does not cause validate_backlog.main() to exit non-zero."""
    repo = _init_repo_with_b_items(
        tmp_path, [("0-B1", "none"), ("0-B2", "none"), ("0-B3", "none")]
    )
    # Provide a minimal backlog.md + glossary.md so the parser doesn't bail early.
    backlog = repo / "docs" / "megaplan" / "backlog.md"
    backlog.parent.mkdir(parents=True, exist_ok=True)
    backlog.write_text(
        "# Backlog\n\n## Index\n"
        "| ID | Title | Status | Owner | Depends on | Detail |\n"
        "|----|-------|--------|-------|------------|--------|\n"
        "| 0-B1 | a | done | — | — | [0-B1](backlog-items/0-B1.md) |\n"
        "| 0-B2 | b | done | — | — | [0-B2](backlog-items/0-B2.md) |\n"
        "| 0-B3 | c | done | — | — | [0-B3](backlog-items/0-B3.md) |\n"
    )
    glossary = repo / "docs" / "megaplan" / "glossary.md"
    glossary.write_text(
        "# Glossary\n\n## Terms\n\n| Term | Definition | Canonical example | Common confusions |\n"
        "|------|------------|-------------------|-------------------|\n"
        "| X | Y | — | — |\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "backlog + glossary")

    with patch("sys.argv", ["validate_backlog.py", str(repo)]):
        try:
            validate_backlog.main()
            rc = 0
        except SystemExit as e:
            rc = e.code
    # Should pass (no errors); advisories are printed to stderr but don't fail.
    assert rc == 0
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "3/3" in combined and "100%" in combined
