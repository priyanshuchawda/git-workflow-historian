from __future__ import annotations

from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)

from app.agent import DEFAULT_TOOL_NAMES, SYSTEM_PROMPT, build_connection_params
from app.runner import _build_user_message

EXPECTED_PROMPT = """You are a Codebase Historian AI.

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


def test_system_prompt_matches_requested_text() -> None:
    assert SYSTEM_PROMPT == EXPECTED_PROMPT


def test_build_connection_params_defaults_to_stdio(monkeypatch) -> None:
    monkeypatch.delenv("GWH_MCP_SERVER_URL", raising=False)

    params = build_connection_params()

    assert isinstance(params, StdioConnectionParams)


def test_build_connection_params_can_use_streamable_http(monkeypatch) -> None:
    monkeypatch.setenv("GWH_MCP_SERVER_URL", "http://localhost:8080/mcp")

    params = build_connection_params()

    assert isinstance(params, StreamableHTTPConnectionParams)
    assert params.url == "http://localhost:8080/mcp"


def test_prompt_includes_repo_path_when_present() -> None:
    prompt = _build_user_message("What changed recently?", repo_path="/tmp/repo")

    assert "Repository path for this request: /tmp/repo" in prompt
    assert "Use this repo_path value when calling MCP tools." in prompt
    assert "Never invent file paths or line numbers." in prompt
    assert "call locate_symbol first" in prompt
    assert "Only call deep_blame after you have a verified file path" in prompt
    assert "User question: What changed recently?" in prompt


def test_required_tool_names_are_exposed() -> None:
    assert DEFAULT_TOOL_NAMES == [
        "get_project_evolution",
        "locate_symbol",
        "deep_blame",
        "find_related_changes",
    ]
