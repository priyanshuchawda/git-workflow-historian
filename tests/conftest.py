from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture()
def sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "sample-repo"
    repo.mkdir()

    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.com")

    (repo / "README.md").write_text("# Sample repo\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "docs: bootstrap repository")

    src = repo / "src"
    src.mkdir()

    (src / "auth.py").write_text(
        "\n".join(
            [
                "def authenticate(token: str) -> bool:",
                "    return bool(token)",
                "",
                "",
                "def validate_token(token: str) -> bool:",
                "    return authenticate(token)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _git(repo, "add", "src/auth.py")
    _git(repo, "commit", "-m", "feat: add auth validation helpers")

    (src / "auth.py").write_text(
        "\n".join(
            [
                "def authenticate(token: str) -> bool:",
                "    normalized = token.strip()",
                "    return bool(normalized)",
                "",
                "",
                "def validate_token(token: str) -> bool:",
                "    normalized = token.strip()",
                "    return authenticate(normalized)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _git(repo, "add", "src/auth.py")
    _git(repo, "commit", "-m", "refactor: improve auth flow")

    (src / "recorder.py").write_text(
        "\n".join(
            [
                "def start_recording(output_path: str) -> str:",
                "    return output_path",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _git(repo, "add", "src/recorder.py")
    _git(repo, "commit", "-m", "feat: add recorder module")

    return repo
