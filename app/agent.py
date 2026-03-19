"""ADK historian agent configuration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from mcp import StdioServerParameters

SYSTEM_PROMPT = """You are a Codebase Historian AI.

You do not answer questions based only on the current code.
You reconstruct developer intent using git history.

When a user asks a question:

1. Decide if historical context is needed.
2. If yes, call the appropriate MCP tool.
3. Analyze:

   * Why the change was made
   * What problem it solved
   * How the system evolved
4. Provide an answer that explains intent, not just code.

Do not dump raw git logs. Always synthesize insights."""

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

APP_NAME = "app"
DEFAULT_MODEL = os.getenv("GWH_MODEL", "gemini-2.5-flash-lite")
DEFAULT_TOOL_NAMES = [
    "get_project_evolution",
    "locate_symbol",
    "deep_blame",
    "find_related_changes",
]


def build_connection_params():
    server_url = os.getenv("GWH_MCP_SERVER_URL")
    if server_url:
        return StreamableHTTPConnectionParams(
            url=server_url,
            timeout=float(os.getenv("GWH_MCP_CONNECT_TIMEOUT", "10")),
            sse_read_timeout=float(os.getenv("GWH_MCP_READ_TIMEOUT", "300")),
        )

    child_env = os.environ.copy()
    return StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
            cwd=PROJECT_ROOT,
            env=child_env,
        ),
    )


def build_toolset() -> McpToolset:
    return McpToolset(
        connection_params=build_connection_params(),
        tool_filter=DEFAULT_TOOL_NAMES,
    )


def build_root_agent() -> LlmAgent:
    return LlmAgent(
        name="codebase_historian",
        model=DEFAULT_MODEL,
        description="Reconstructs why a codebase changed using git history and code lookup tools.",
        instruction=SYSTEM_PROMPT,
        tools=[build_toolset()],
    )


root_agent = build_root_agent()
