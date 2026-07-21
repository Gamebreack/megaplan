"""Tests for the user-facing install docs (README, AGENTS.md, SKILL.md, next-steps).

Covers B4: pipe-args in the one-liner, harness compatibility table,
self-test exit code, next-steps content, and marketplace install paths.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).parent.parent
README = REPO_ROOT / "README.md"
AGENTS = REPO_ROOT / "AGENTS.md"
SKILL = REPO_ROOT / "skills" / "megaplan" / "SKILL.md"
METHODOLOGY = REPO_ROOT / "docs" / "methodology.md"
BACKLOG_TEMPLATE = REPO_ROOT / "templates" / "backlog.md"
BOOTSTRAP = REPO_ROOT / "scripts" / "bootstrap.py"


# --------------------------------------------------------------------------- #
# B4: user-facing install UX
# --------------------------------------------------------------------------- #


def test_readme_one_liner_uses_python3_dash():
    """The README's one-liner uses `python3 -` (not bare `python3`)."""
    content = README.read_text()
    assert "python3 -" in content, "README.md must use `python3 -` in the one-liner (so flags pass through the pipe)"


def test_readme_documents_pipe_args():
    """The README has an explicit example showing how to pass --ref through the pipe."""
    content = README.read_text()
    assert "python3 - --" in content or "python3 - <flags>" in content, (
        "README.md must show how to pass flags through the pipe (e.g., `python3 - --ref v2.0.0`)"
    )


def test_harness_table_includes_cursor():
    content = README.read_text()
    assert "Cursor" in content, "README.md harness table must include Cursor"


def test_harness_table_includes_aider():
    content = README.read_text()
    assert "Aider" in content, "README.md harness table must include Aider"


def test_harness_table_includes_windsurf():
    content = README.read_text()
    assert "Windsurf" in content, "README.md harness table must include Windsurf"


def test_harness_table_includes_copilot():
    content = README.read_text()
    assert "Copilot" in content or "copilot" in content, (
        "README.md harness table must include Copilot (or GitHub Copilot)"
    )


def test_readme_troubleshooting_has_python_version():
    content = README.read_text()
    if "Troubleshooting" not in content:
        pytest.skip("README.md has no Troubleshooting section")
    troubleshooting_start = content.find("Troubleshooting")
    troubleshooting = content[troubleshooting_start:]
    assert "Python" in troubleshooting[:2000] and ("3.10" in troubleshooting or "3.12" in troubleshooting), (
        "README.md Troubleshooting section must include a Python version entry"
    )


def test_readme_marketplace_section():
    content = README.read_text()
    assert "Marketplace" in content or "marketplace" in content, (
        "README.md must have a Marketplace install section"
    )


def test_next_steps_uses_relative_paths(tmp_path):
    """bootstrap.main()'s Next steps use project-relative paths, not absolute."""
    sys.path.append(str(REPO_ROOT / "scripts"))
    import bootstrap
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / ".git").mkdir()
    (project_dir / ".git" / "hooks").mkdir()
    with patch("sys.argv", [
        "bootstrap.py",
        "--from-local", str(REPO_ROOT),
        "--ref", "main",
        "--project-dir", str(project_dir),
    ]):
        bootstrap.main()
    src = BOOTSTRAP.read_text()
    import re
    m = re.search(r"def _print_next_steps.*?(?=\n\ndef |\nclass |\Z)", src, re.DOTALL)
    assert m, "could not locate _print_next_steps in bootstrap.py"
    fn_body = m.group(0)
    assert "os.path.abspath(project_dir)" not in fn_body, (
        "_print_next_steps should use project-relative paths, not os.path.abspath(project_dir)"
    )


def test_next_steps_explains_b_item_creation(tmp_path):
    """The bootstrap's _print_next_steps mentions copying _template.md to 0-B1.md."""
    src = BOOTSTRAP.read_text()
    import re
    m = re.search(r"def _print_next_steps.*?(?=\n\ndef |\nclass |\Z)", src, re.DOTALL)
    assert m
    fn_body = m.group(0)
    assert "_template.md" in fn_body and "0-B1.md" in fn_body, (
        "_print_next_steps should mention copying _template.md to 0-B1.md"
    )


def test_next_steps_points_to_example(tmp_path):
    """The bootstrap's _print_next_steps mentions the example project URL."""
    src = BOOTSTRAP.read_text()
    import re
    m = re.search(r"def _print_next_steps.*?(?=\n\ndef |\nclass |\Z)", src, re.DOTALL)
    assert m
    fn_body = m.group(0)
    assert "github.com/Gamebreack/megaplan" in fn_body and "examples" in fn_body, (
        "_print_next_steps should point at the example project"
    )


def test_self_test_failure_exit_code_nonzero(tmp_path):
    """When self-test fails, bootstrap.main() returns non-zero."""
    sys.path.append(str(REPO_ROOT / "scripts"))
    import bootstrap
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / ".git").mkdir()
    (project_dir / ".git" / "hooks").mkdir()
    bootstrap.lay_out_framework(
        str(REPO_ROOT), str(project_dir), with_wiki=False, force=False
    )
    manifest = project_dir / "docs" / "megaplan" / ".integrity-manifest.json"
    if manifest.exists():
        manifest.unlink()
    with patch("sys.argv", [
        "bootstrap.py",
        "--from-local", str(REPO_ROOT),
        "--ref", "main",
        "--project-dir", str(project_dir),
    ]):
        rc = bootstrap.main()
    assert rc != 0, "bootstrap should return non-zero when self-test fails"


def test_backlog_template_no_templates_path():
    content = BACKLOG_TEMPLATE.read_text()
    assert "backlog-items/_template.md" in content or "<!-- templates/backlog-item.md" in content, (
        "templates/backlog.md should reference the new template path or have a comment marking the change"
    )


def test_agents_md_under_kiss_limit():
    content = AGENTS.read_text()
    lines = content.count("\n") + 1
    assert lines <= 200, f"AGENTS.md is {lines} lines, exceeds the 200-line K.I.S.S. limit"
