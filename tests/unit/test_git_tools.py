from __future__ import annotations

import subprocess
from pathlib import Path

from mcp_server.git_tools import (
    deep_blame,
    find_related_changes,
    get_project_evolution,
    locate_symbol,
)


def test_get_project_evolution_returns_recent_commit_summaries(sample_repo: Path) -> None:
    result = get_project_evolution(limit=2, repo_path=str(sample_repo))

    assert "Recent project evolution (2 commits)" in result
    assert "feat: add recorder module" in result
    assert "refactor: improve auth flow" in result
    assert "src/recorder.py" in result


def test_deep_blame_returns_commit_message_and_diff(sample_repo: Path) -> None:
    result = deep_blame("src/auth.py", 7, repo_path=str(sample_repo))

    assert "Commit message: refactor: improve auth flow" in result
    assert "Commit diff:" in result
    assert "normalized = token.strip()" in result


def test_find_related_changes_groups_matching_history(sample_repo: Path) -> None:
    result = find_related_changes("auth", repo_path=str(sample_repo))

    assert "Commit history related to keyword: auth" in result
    assert "feat: add auth validation helpers" in result
    assert "refactor: improve auth flow" in result


def test_find_related_changes_ignores_commit_trailers(sample_repo: Path) -> None:
    notes = sample_repo / "NOTES.md"
    notes.write_text("notes\n", encoding="utf-8")
    subprocess.run(["git", "add", "NOTES.md"], cwd=sample_repo, check=True)
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "chore: update notes",
            "-m",
            "Co-authored-by: helper <helper@example.com>",
        ],
        cwd=sample_repo,
        check=True,
    )

    result = find_related_changes("auth", repo_path=str(sample_repo))

    assert "chore: update notes" not in result
    assert "feat: add auth validation helpers" in result
    assert "refactor: improve auth flow" in result


def test_locate_symbol_finds_current_code(sample_repo: Path) -> None:
    result = locate_symbol("validate_token", repo_path=str(sample_repo))

    assert "Current code matches for: validate_token" in result
    assert "src/auth.py" in result
    assert "validate_token" in result
