"""FastMCP entrypoint for Git Workflow Historian tools."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP

from mcp_server.git_tools import GitToolError, resolve_repo_root
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


def _path_from_root_uri(uri: str) -> Path | None:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None
    return Path(unquote(parsed.path)).resolve()


async def _resolve_request_repo_path(
    repo_path: str | None,
    ctx: Context | None = None,
) -> str | None:
    if repo_path:
        return repo_path
    if ctx is None:
        return None

    client_params = getattr(ctx.session, "client_params", None)
    client_capabilities = getattr(client_params, "capabilities", None)
    if getattr(client_capabilities, "roots", None) is None:
        return None

    roots_result = await ctx.session.list_roots()
    repo_roots: list[Path] = []
    for root in roots_result.roots:
        root_path = _path_from_root_uri(str(root.uri))
        if root_path is None:
            continue
        try:
            repo_roots.append(resolve_repo_root(str(root_path)))
        except GitToolError:
            continue

    unique_repo_roots = list(dict.fromkeys(repo_roots))
    if len(unique_repo_roots) == 1:
        return str(unique_repo_roots[0])
    if len(unique_repo_roots) > 1:
        raise GitToolError(
            "Multiple git repositories found in MCP roots. Pass repo_path explicitly."
        )
    return None


@app.tool()
async def get_project_evolution(
    limit: int = 5,
    repo_path: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Return the latest commits with file-level summaries for a repository."""
    resolved_repo_path = await _resolve_request_repo_path(repo_path, ctx)
    return get_project_evolution_impl(limit=limit, repo_path=resolved_repo_path)


@app.tool()
async def get_repo_story(
    limit: int = 30,
    repo_path: str | None = None,
    max_files: int = 8,
    ctx: Context | None = None,
) -> str:
    """Load repo-wide history context before broader coding or architecture questions."""
    resolved_repo_path = await _resolve_request_repo_path(repo_path, ctx)
    return get_repo_story_impl(limit=limit, repo_path=resolved_repo_path, max_files=max_files)


@app.tool()
async def locate_symbol(
    symbol: str,
    limit: int = 10,
    repo_path: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Find symbol locations first when the user names code but not a file path."""
    resolved_repo_path = await _resolve_request_repo_path(repo_path, ctx)
    return locate_symbol_impl(symbol=symbol, limit=limit, repo_path=resolved_repo_path)


@app.tool()
async def deep_blame(
    file_path: str,
    line_number: int,
    repo_path: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Inspect history for a known file path and line number after locate_symbol."""
    resolved_repo_path = await _resolve_request_repo_path(repo_path, ctx)
    return deep_blame_impl(
        file_path=file_path,
        line_number=line_number,
        repo_path=resolved_repo_path,
    )


@app.tool()
async def find_related_changes(
    keyword: str,
    repo_path: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Search commit-message history when the user asks about subsystem evolution."""
    resolved_repo_path = await _resolve_request_repo_path(repo_path, ctx)
    return find_related_changes_impl(keyword=keyword, repo_path=resolved_repo_path)


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
