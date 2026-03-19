"""FastMCP entrypoint for Git Workflow Historian tools."""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from mcp_server.git_tools import deep_blame as deep_blame_impl
from mcp_server.git_tools import find_related_changes as find_related_changes_impl
from mcp_server.git_tools import get_project_evolution as get_project_evolution_impl
from mcp_server.git_tools import get_repo_story as get_repo_story_impl
from mcp_server.git_tools import locate_symbol as locate_symbol_impl

load_dotenv()

app = FastMCP(
    "Git Workflow Historian MCP",
    instructions=(
        "Expose repository history and current-code lookup tools. "
        "Return data only. Do not interpret the history."
    ),
    stateless_http=True,
    json_response=True,
)


@app.tool()
def get_project_evolution(limit: int = 5, repo_path: str | None = None) -> str:
    """Return the latest commits with file-level summaries for a repository."""
    return get_project_evolution_impl(limit=limit, repo_path=repo_path)


@app.tool()
def get_repo_story(
    limit: int = 30,
    repo_path: str | None = None,
    max_files: int = 8,
) -> str:
    """Load repo-wide history context before broader coding or architecture questions."""
    return get_repo_story_impl(limit=limit, repo_path=repo_path, max_files=max_files)


@app.tool()
def locate_symbol(
    symbol: str,
    limit: int = 10,
    repo_path: str | None = None,
) -> str:
    """Find symbol locations first when the user names code but not a file path."""
    return locate_symbol_impl(symbol=symbol, limit=limit, repo_path=repo_path)


@app.tool()
def deep_blame(
    file_path: str,
    line_number: int,
    repo_path: str | None = None,
) -> str:
    """Inspect history for a known file path and line number after locate_symbol."""
    return deep_blame_impl(file_path=file_path, line_number=line_number, repo_path=repo_path)


@app.tool()
def find_related_changes(keyword: str, repo_path: str | None = None) -> str:
    """Search commit-message history when the user asks about subsystem evolution."""
    return find_related_changes_impl(keyword=keyword, repo_path=repo_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Git Workflow Historian MCP server.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default=os.getenv("GWH_MCP_TRANSPORT", "stdio"),
        help="Transport to use when serving MCP tools.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8080")),
        help="Port used for streamable HTTP transport.",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("GWH_MCP_HOST", "0.0.0.0"),
        help="Host used for streamable HTTP transport.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.transport == "streamable-http":
        app.settings.host = args.host
        app.settings.port = args.port
        app.run(transport="streamable-http")
        return
    app.run()


if __name__ == "__main__":
    main()
