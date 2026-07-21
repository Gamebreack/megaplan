"""Tests for `scripts/_wiki_map.py` and the wiki ingestion manifest.

These tests cover B-item 0-B1: the deterministic `suggest_pages` helper
that writes `suggested_pages` into `_meta/manifest.json`.
"""
import json
import os
import subprocess
import sys

import pytest

# Add scripts directory to path so we can import the framework modules
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
)

import _wiki_map  # noqa: E402
import ingest_wiki  # noqa: E402
import validate_wiki  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

SOURCE_ROOTS = ("src", "lib", "app", "pkg", "internal", "cmd")


def _git(cwd, *args, check=True):
    """Run a git command in cwd, return CompletedProcess."""
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


@pytest.fixture
def wiki_repo(tmp_path):
    """Temp git repo with a populated wiki/ and at least one source file.

    Layout:
        tmp_path/
          docs/megaplan/wiki/
            _meta/
            architecture/{users.md, payments.md}
            notes/users.md
            contracts/api.md
          src/users/service.py
    """
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@test.local")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "config", "commit.gpgsign", "false")

    wiki = tmp_path / "docs" / "megaplan" / "wiki"
    (wiki / "_meta").mkdir(parents=True)
    (wiki / "architecture").mkdir()
    (wiki / "notes").mkdir()
    (wiki / "contracts").mkdir()

    (wiki / "architecture" / "users.md").write_text(
        "---\n"
        "type: architecture\n"
        "module: users\n"
        "---\n"
        "# Architecture: Users\n"
        "\n"
        "## Responsibility\n"
        "\nblah\n"
        "\n"
        "## Boundaries\n"
        "\n- depends on: nothing\n"
        "\n"
        "## Key symbols\n"
        "\n- `UserService`\n"
    )
    (wiki / "architecture" / "payments.md").write_text(
        "---\n"
        "type: architecture\n"
        "module: payments\n"
        "---\n"
        "# Architecture: Payments\n"
        "\n"
        "## Responsibility\n"
        "\nblah\n"
    )
    (wiki / "notes" / "users.md").write_text(
        "---\n"
        "type: note\n"
        "module: users\n"
        "---\n"
        "# Notes: Users\n"
        "\n"
        "## Gotchas\n"
        "\n- one\n"
    )
    (wiki / "contracts" / "api.md").write_text(
        "---\n"
        "type: contract\n"
        "module: api\n"
        "---\n"
        "# Contract: API\n"
        "\n"
        "## Inputs\n"
    )

    (tmp_path / "src" / "users").mkdir(parents=True)
    (tmp_path / "src" / "users" / "service.py").write_text("# service\n")

    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "init")
    return tmp_path


@pytest.fixture
def wiki_repo_with_b_item(wiki_repo):
    """wiki_repo plus a minimal B-item file at the expected path."""
    b_item = (
        "# 0-T1: Test fixture B-item\n"
        "\n"
        "## Metadata\n"
        "\n"
        "| Field | Value |\n"
        "|-------|-------|\n"
        "| ID | 0-T1 |\n"
        "| Status | in-progress |\n"
        "\n"
        "## Outcome\n"
        "\nFixture.\n"
    )
    b_item_path = wiki_repo / "docs" / "megaplan" / "backlog-items" / "0-T1.md"
    b_item_path.parent.mkdir(parents=True, exist_ok=True)
    b_item_path.write_text(b_item)
    _git(wiki_repo, "add", "-A")
    _git(wiki_repo, "commit", "-m", "0-T1: fixture b-item")
    return wiki_repo, b_item_path


# --------------------------------------------------------------------------- #
# Unit tests: suggest_pages
# --------------------------------------------------------------------------- #


def test_suggest_pages_src_prefix(wiki_repo):
    """`src/users/service.py` → module slug `users`."""
    result = _wiki_map.suggest_pages(str(wiki_repo), ["src/users/service.py"])
    paths = [p for p, _ in result]
    assert "docs/megaplan/wiki/architecture/users.md" in paths


def test_suggest_pages_tests_prefix(wiki_repo):
    """`tests/test_users.py` → module slug `users` (test prefix stripped)."""
    tests_dir = wiki_repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_users.py").write_text("# test\n")
    _git(wiki_repo, "add", "-A")
    _git(wiki_repo, "commit", "-m", "add test")

    result = _wiki_map.suggest_pages(str(wiki_repo), ["tests/test_users.py"])
    paths = [p for p, _ in result]
    assert "docs/megaplan/wiki/architecture/users.md" in paths


def test_suggest_pages_internal_skipped(wiki_repo):
    """`pkg/internal/auth.go` → module slug `auth` (the `internal` middle is dropped)."""
    pkg = wiki_repo / "pkg" / "internal" / "auth"
    pkg.mkdir(parents=True)
    (pkg / "auth.go").write_text("package auth\n")
    arch = wiki_repo / "docs" / "megaplan" / "wiki" / "architecture" / "auth.md"
    arch.write_text(
        "---\ntype: architecture\nmodule: auth\n---\n# Auth\n\n## Responsibility\n"
    )
    _git(wiki_repo, "add", "-A")
    _git(wiki_repo, "commit", "-m", "add auth")

    result = _wiki_map.suggest_pages(str(wiki_repo), ["pkg/internal/auth/auth.go"])
    paths = [p for p, _ in result]
    assert "docs/megaplan/wiki/architecture/auth.md" in paths


def test_suggest_pages_root_level_file(wiki_repo):
    """Root-level file → use parent dir name as slug."""
    schema = wiki_repo / "schema"
    schema.mkdir()
    (schema / "contract.graphql").write_text("# graphql\n")
    arch = wiki_repo / "docs" / "megaplan" / "wiki" / "architecture" / "schema.md"
    arch.write_text(
        "---\ntype: architecture\nmodule: schema\n---\n# Schema\n\n## Responsibility\n"
    )
    _git(wiki_repo, "add", "-A")
    _git(wiki_repo, "commit", "-m", "add schema")

    result = _wiki_map.suggest_pages(str(wiki_repo), ["schema/contract.graphql"])
    paths = [p for p, _ in result]
    assert "docs/megaplan/wiki/architecture/schema.md" in paths


def test_suggest_pages_no_match(wiki_repo):
    """Unknown module returns no architecture/notes suggestions."""
    result = _wiki_map.suggest_pages(
        str(wiki_repo), ["totally/unknown/thing.py"]
    )
    assert result == []


def test_suggest_pages_architecture_first(wiki_repo):
    """When both architecture/ and notes/ exist for a module, architecture is first."""
    result = _wiki_map.suggest_pages(str(wiki_repo), ["src/users/service.py"])
    paths = [p for p, _ in result]
    assert paths.index("docs/megaplan/wiki/architecture/users.md") < paths.index(
        "docs/megaplan/wiki/notes/users.md"
    )


def test_suggest_pages_contract_heuristic(wiki_repo):
    """`src/api/routes.py` → suggests `contracts/api.md` (filename matches heuristic)."""
    api = wiki_repo / "src" / "api"
    api.mkdir(parents=True)
    (api / "routes.py").write_text("# routes\n")
    _git(wiki_repo, "add", "-A")
    _git(wiki_repo, "commit", "-m", "add api")

    result = _wiki_map.suggest_pages(str(wiki_repo), ["src/api/routes.py"])
    paths = [p for p, _ in result]
    assert "docs/megaplan/wiki/contracts/api.md" in paths


def test_suggest_pages_no_contract_for_non_match(wiki_repo):
    """`src/users/service.py` does NOT match the contract heuristic."""
    # Make a contract page that should NOT be suggested for this file.
    contracts = wiki_repo / "docs" / "megaplan" / "wiki" / "contracts"
    (contracts / "users.md").write_text(
        "---\ntype: contract\n---\n# Contract: Users\n\n## Inputs\n"
    )
    _git(wiki_repo, "add", "-A")
    _git(wiki_repo, "commit", "-m", "spurious contract")

    result = _wiki_map.suggest_pages(str(wiki_repo), ["src/users/service.py"])
    paths = [p for p, _ in result]
    assert "docs/megaplan/wiki/contracts/users.md" not in paths


def test_suggest_pages_heading_extraction(wiki_repo):
    """Matched page's H2 headings are returned as the second element of each tuple."""
    result = _wiki_map.suggest_pages(str(wiki_repo), ["src/users/service.py"])
    arch_entry = next(
        (p, h) for p, h in result if p == "docs/megaplan/wiki/architecture/users.md"
    )
    assert arch_entry is not None
    _, headings = arch_entry
    assert "Responsibility" in headings
    assert "Boundaries" in headings
    assert "Key symbols" in headings


def test_suggest_pages_empty_touched(wiki_repo):
    """Empty touched_files → empty suggested_pages."""
    result = _wiki_map.suggest_pages(str(wiki_repo), [])
    assert result == []


# --------------------------------------------------------------------------- #
# Integration: ingest writes suggested_pages into the manifest
# --------------------------------------------------------------------------- #


def test_ingest_writes_suggested_pages(wiki_repo_with_b_item):
    """After ingest, manifest.items[<id>].suggested_pages is populated."""
    repo, b_item_path = wiki_repo_with_b_item
    # Touch a tracked file so changed_files() returns it.
    (repo / "src" / "users" / "service.py").write_text("# service updated\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "0-T1: touch service.py")

    rc = ingest_wiki.ingest(str(b_item_path))
    assert rc == 0

    manifest_path = repo / "docs" / "megaplan" / "wiki" / "_meta" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    entry = manifest["items"]["0-T1"]
    assert "suggested_pages" in entry
    paths = [p for p, _ in entry["suggested_pages"]]
    assert "docs/megaplan/wiki/architecture/users.md" in paths


# --------------------------------------------------------------------------- #
# Integration: validate_wiki advisory
# --------------------------------------------------------------------------- #


def test_validate_wiki_advisory_suggested_pages_no_pages(wiki_repo_with_b_item):
    """validate_wiki warns when suggested_pages populated but pages empty."""
    repo, b_item_path = wiki_repo_with_b_item
    (repo / "src" / "users" / "service.py").write_text("# service updated\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "0-T1: touch service.py")

    ingest_wiki.ingest(str(b_item_path))

    errors, warnings = validate_wiki.validate_wiki(str(repo))
    assert errors == []
    assert any("suggested_pages" in w and "pages" in w for w in warnings)
