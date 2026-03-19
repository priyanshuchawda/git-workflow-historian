"""Git history retrieval helpers used by the FastMCP server."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class GitToolError(RuntimeError):
    """Raised when a Git tool cannot produce a valid result."""


@dataclass(slots=True)
class CommitSummary:
    sha: str
    date: str
    author: str
    subject: str
    stats: str


def resolve_repo_root(repo_path: str | None = None) -> Path:
    """Resolve and validate the repository root."""
    candidate = repo_path or os.getenv("GIT_WORKFLOW_REPO_PATH") or os.getcwd()
    repo_dir = Path(candidate).expanduser().resolve()
    if not repo_dir.exists():
        raise GitToolError(f"Repository path does not exist: {repo_dir}")

    result = _run_git(repo_dir, ["rev-parse", "--show-toplevel"])
    return Path(result.stdout.strip()).resolve()


def normalize_repo_file(repo_root: Path, file_path: str) -> Path:
    """Resolve a file path and ensure it stays inside the repository root."""
    candidate = Path(file_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (repo_root / candidate).resolve()

    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise GitToolError(f"File path escapes repository root: {file_path}") from exc

    if not resolved.exists():
        raise GitToolError(f"File does not exist in repository: {file_path}")

    return resolved


def get_project_evolution(limit: int = 5, repo_path: str | None = None) -> str:
    """Return the latest commits with file-level summaries."""
    repo_root = resolve_repo_root(repo_path)
    if limit < 1:
        raise GitToolError("limit must be at least 1")

    commits = _recent_commits(repo_root, limit)
    if not commits:
        return f"Repository: {repo_root}\nNo commits found."

    sections = [
        f"Repository: {repo_root}",
        f"Recent project evolution ({len(commits)} commit{'s' if len(commits) != 1 else ''})",
    ]

    for index, commit in enumerate(commits, start=1):
        sections.append(
            "\n".join(
                [
                    f"Commit {index}",
                    f"SHA: {commit.sha}",
                    f"Date: {commit.date}",
                    f"Author: {commit.author}",
                    f"Message: {commit.subject}",
                    "Files changed summary:",
                    commit.stats or "No file-level summary available.",
                ]
            )
        )

    return "\n\n".join(sections)


def deep_blame(
    file_path: str,
    line_number: int,
    repo_path: str | None = None,
) -> str:
    """Find the commit responsible for a line and return its full diff."""
    repo_root = resolve_repo_root(repo_path)
    if line_number < 1:
        raise GitToolError("line_number must be at least 1")

    target_file = normalize_repo_file(repo_root, file_path)
    relative_path = target_file.relative_to(repo_root).as_posix()

    blame_result = _run_git(
        repo_root,
        [
            "blame",
            "--porcelain",
            "-L",
            f"{line_number},{line_number}",
            "--",
            relative_path,
        ],
    )
    commit_sha, blame_summary, author, authored_at, source_line = _parse_blame(blame_result.stdout)

    show_result = _run_git(repo_root, ["show", "--find-renames", "--format=fuller", commit_sha])

    return "\n".join(
        [
            "Line ownership",
            f"Repository: {repo_root}",
            f"File: {relative_path}",
            f"Line: {line_number}",
            f"Commit: {commit_sha}",
            f"Author: {author}",
            f"Authored at: {authored_at}",
            f"Commit message: {blame_summary}",
            f"Source line: {source_line}",
            "",
            "Commit diff:",
            show_result.stdout.rstrip(),
        ]
    )


def find_related_changes(keyword: str, repo_path: str | None = None) -> str:
    """Search commit messages by keyword and group matches by day."""
    repo_root = resolve_repo_root(repo_path)
    if not keyword.strip():
        raise GitToolError("keyword must not be empty")
    normalized_keyword = keyword.casefold()

    result = _run_git(
        repo_root,
        [
            "log",
            "--fixed-strings",
            "--regexp-ignore-case",
            f"--grep={keyword}",
            "--date=iso-strict",
            "--format=%H%x1f%ad%x1f%an%x1f%s",
        ],
        allow_exit_codes={0, 1},
    )
    if not result.stdout.strip():
        return f"Repository: {repo_root}\nNo commit messages matched keyword: {keyword}"

    grouped: dict[str, list[CommitSummary]] = {}
    for line in result.stdout.splitlines():
        sha, date_raw, author, subject = line.split("\x1f")
        if normalized_keyword not in subject.casefold():
            continue
        stats = _commit_stats(repo_root, sha)
        day = datetime.fromisoformat(date_raw).date().isoformat()
        grouped.setdefault(day, []).append(
            CommitSummary(sha=sha, date=date_raw, author=author, subject=subject, stats=stats)
        )

    if not grouped:
        return f"Repository: {repo_root}\nNo commit messages matched keyword: {keyword}"

    sections = [f"Repository: {repo_root}", f"Commit history related to keyword: {keyword}"]
    for day in sorted(grouped.keys(), reverse=True):
        sections.append(f"Day: {day}")
        for commit in grouped[day]:
            sections.append(
                "\n".join(
                    [
                        f"- SHA: {commit.sha}",
                        f"  Date: {commit.date}",
                        f"  Author: {commit.author}",
                        f"  Message: {commit.subject}",
                        "  Summary:",
                        _indent_block(commit.stats or "No file-level summary available.", "    "),
                    ]
                )
            )

    return "\n\n".join(sections)


def locate_symbol(
    symbol: str,
    limit: int = 10,
    repo_path: str | None = None,
) -> str:
    """Search the current repository tree for a symbol or keyword."""
    repo_root = resolve_repo_root(repo_path)
    if not symbol.strip():
        raise GitToolError("symbol must not be empty")
    if limit < 1:
        raise GitToolError("limit must be at least 1")

    result = _run_git(
        repo_root,
        ["grep", "-n", "-I", "--heading", "-C", "2", "-e", symbol, "--", "."],
        allow_exit_codes={0, 1},
    )
    if not result.stdout.strip():
        return f"Repository: {repo_root}\nNo symbol or text matches found for: {symbol}"

    blocks = [block.strip() for block in result.stdout.split("\n\n") if block.strip()]
    limited = blocks[:limit]
    body = "\n\n".join(limited)
    return "\n".join(
        [
            f"Repository: {repo_root}",
            f"Current code matches for: {symbol}",
            body,
        ]
    )


def _recent_commits(repo_root: Path, limit: int) -> list[CommitSummary]:
    log_result = _run_git(
        repo_root,
        [
            "log",
            f"-n{limit}",
            "--date=iso-strict",
            "--format=%H%x1f%ad%x1f%an%x1f%s",
        ],
    )
    commits: list[CommitSummary] = []
    for line in log_result.stdout.splitlines():
        sha, date_raw, author, subject = line.split("\x1f")
        commits.append(
            CommitSummary(
                sha=sha,
                date=date_raw,
                author=author,
                subject=subject,
                stats=_commit_stats(repo_root, sha),
            )
        )
    return commits


def _commit_stats(repo_root: Path, sha: str) -> str:
    result = _run_git(
        repo_root,
        ["show", "--stat", "--summary", "--format=", "--find-renames", sha],
    )
    return result.stdout.strip()


def _parse_blame(blame_output: str) -> tuple[str, str, str, str, str]:
    lines = blame_output.splitlines()
    if not lines:
        raise GitToolError("git blame returned no output")

    first = lines[0].split()
    commit_sha = first[0]
    metadata: dict[str, str] = {}
    source_line = ""

    for line in lines[1:]:
        if line.startswith("\t"):
            source_line = line[1:]
            break
        key, _, value = line.partition(" ")
        metadata[key] = value

    authored_at = metadata.get("author-time", "")
    if authored_at:
        authored_at = datetime.fromtimestamp(int(authored_at)).isoformat()

    return (
        commit_sha,
        metadata.get("summary", ""),
        metadata.get("author", ""),
        authored_at,
        source_line,
    )


def _run_git(
    repo_root: Path,
    args: list[str],
    *,
    allow_exit_codes: set[int] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    allowed = allow_exit_codes or {0}
    if completed.returncode not in allowed:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown git error"
        raise GitToolError(f"git {' '.join(args)} failed: {stderr}")
    return completed


def _indent_block(text: str, prefix: str) -> str:
    return "\n".join(f"{prefix}{line}" for line in text.splitlines())
