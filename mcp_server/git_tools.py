"""Git history retrieval helpers used by the FastMCP server."""

from __future__ import annotations

import os
import subprocess
from collections import Counter
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


def get_repo_story(
    limit: int = 30,
    repo_path: str | None = None,
    max_files: int = 8,
) -> str:
    """Return a repo-wide history context window with milestones and hotspots."""
    repo_root = resolve_repo_root(repo_path)
    if limit < 1:
        raise GitToolError("limit must be at least 1")
    if max_files < 1:
        raise GitToolError("max_files must be at least 1")

    commits = _recent_commits(repo_root, limit)
    if not commits:
        return f"Repository: {repo_root}\nNo commits found."

    touched_files: Counter[str] = Counter()
    touched_areas: Counter[str] = Counter()
    commit_themes: Counter[str] = Counter()
    milestones_by_day: dict[str, list[str]] = {}

    for commit in reversed(commits):
        files = _commit_files(repo_root, commit.sha)
        touched_files.update(files)
        touched_areas.update(_top_level_area(file_path) for file_path in files)
        commit_themes.update([_commit_theme(commit.subject)])
        milestones_by_day.setdefault(_iso_day(commit.date), []).append(
            "\n".join(
                [
                    f"- {commit.subject}",
                    f"  SHA: {commit.sha}",
                    f"  Author: {commit.author}",
                    f"  Files: {_format_file_list(files, max_files)}",
                ]
            )
        )

    oldest_commit = commits[-1]
    newest_commit = commits[0]

    sections = [
        f"Repository: {repo_root}",
        (
            "Repo story context "
            f"({len(commits)} recent commit{'s' if len(commits) != 1 else ''} analyzed)"
        ),
        (
            "Commit window: "
            f"{oldest_commit.date} -> {newest_commit.date}"
        ),
        "Milestones by day:",
    ]
    for day in sorted(milestones_by_day):
        sections.append(f"Day: {day}")
        sections.extend(milestones_by_day[day])

    sections.extend(
        [
            "",
            "Most repeatedly touched files:",
            _format_ranked_counts(touched_files, max_files),
            "",
            "Most active areas:",
            _format_ranked_counts(touched_areas, max_files),
            "",
            "Commit themes:",
            _format_ranked_counts(commit_themes, max_files),
            "",
            "Current code anchors:",
            _format_code_anchors(repo_root, touched_files, max_files),
            "",
            "Latest direction:",
        ]
    )
    for commit in commits[: min(3, len(commits))]:
        files = _commit_files(repo_root, commit.sha)
        sections.append(
            "\n".join(
                [
                    f"- {commit.subject}",
                    f"  SHA: {commit.sha}",
                    f"  Files: {_format_file_list(files, max_files)}",
                ]
            )
        )

    return "\n".join(sections)


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


def _commit_files(repo_root: Path, sha: str) -> list[str]:
    result = _run_git(
        repo_root,
        ["show", "--name-only", "--format=", "--find-renames", sha],
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _commit_theme(subject: str) -> str:
    prefix, separator, _ = subject.partition(":")
    if separator:
        return prefix.strip().lower()
    first_word = subject.split(maxsplit=1)[0] if subject.split() else "other"
    return first_word.lower()


def _format_file_list(files: list[str], max_files: int) -> str:
    if not files:
        return "No files listed."
    visible = files[:max_files]
    remaining = len(files) - len(visible)
    body = ", ".join(visible)
    if remaining > 0:
        return f"{body}, +{remaining} more"
    return body


def _format_ranked_counts(counter: Counter[str], limit: int) -> str:
    if not counter:
        return "No entries."
    lines = [
        f"- {name}: {count} commit{'s' if count != 1 else ''}"
        for name, count in counter.most_common(limit)
    ]
    return "\n".join(lines)


def _format_code_anchors(repo_root: Path, counter: Counter[str], limit: int) -> str:
    if not counter:
        return "No anchors."

    blocks: list[str] = []
    for file_path, _ in counter.most_common(limit):
        anchors = _current_code_anchors(repo_root, file_path)
        if not anchors:
            continue
        blocks.append(
            "\n".join(
                [
                    f"- {file_path}",
                    _indent_block("\n".join(anchors), "  "),
                ]
            )
        )

    return "\n".join(blocks) if blocks else "No anchors."


def _current_code_anchors(repo_root: Path, file_path: str, max_lines: int = 3) -> list[str]:
    result = _run_git(
        repo_root,
        [
            "grep",
            "-n",
            "-I",
            "-e",
            "def ",
            "-e",
            "class ",
            "-e",
            "function ",
            "-e",
            "export function",
            "-e",
            "export const",
            "-e",
            "async def ",
            "-e",
            "bool ",
            "-e",
            "void ",
            "-e",
            "int ",
            "--",
            file_path,
        ],
        allow_exit_codes={0, 1},
    )
    anchors = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if anchors:
        return anchors[:max_lines]

    target = repo_root / file_path
    if not target.exists():
        return []

    fallback: list[str] = []
    for index, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        fallback.append(f"{index}:{line.strip()}")
        if len(fallback) >= max_lines:
            break
    return fallback


def _iso_day(date_value: str) -> str:
    return datetime.fromisoformat(date_value).date().isoformat()


def _top_level_area(file_path: str) -> str:
    path = Path(file_path)
    parts = path.parts
    if len(parts) <= 1:
        return parts[0] if parts else "."
    return parts[0]


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
