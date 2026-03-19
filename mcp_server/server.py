"""FastMCP entrypoint for Git Workflow Historian tools."""

from __future__ import annotations

import argparse
import os

from mcp.server.fastmcp import FastMCP

from mcp_server.git_tools import (
    deep_blame,
    find_related_changes,
    get_project_evolution,
    locate_symbol,
)

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
def get_project_evolution_tool(limit: int = 5, repo_path: str | None = None) -> str:
    """Return the latest commits with file-level summaries for a repository."""
    return get_project_evolution(limit=limit, repo_path=repo_path)


@app.tool()
def deep_blame_tool(
    file_path: str,
    line_number: int,
    repo_path: str | None = None,
) -> str:
    """Find the commit responsible for a line and return the full owning diff."""
    return deep_blame(file_path=file_path, line_number=line_number, repo_path=repo_path)


@app.tool()
def find_related_changes_tool(keyword: str, repo_path: str | None = None) -> str:
    """Search commit messages for a keyword and summarize matching changes."""
    return find_related_changes(keyword=keyword, repo_path=repo_path)


@app.tool()
def locate_symbol_tool(
    symbol: str,
    limit: int = 10,
    repo_path: str | None = None,
) -> str:
    """Search the current repository tree for a symbol or keyword."""
    return locate_symbol(symbol=symbol, limit=limit, repo_path=repo_path)


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.transport == "streamable-http":
        app.run(transport="streamable-http", port=args.port)
        return
    app.run()


if __name__ == "__main__":
    main()
