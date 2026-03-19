from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

from mcp_server import server


def test_main_runs_stdio_transport(monkeypatch) -> None:
    calls: list[str] = []

    class FakeApp:
        def __init__(self) -> None:
            self.settings = SimpleNamespace(host="127.0.0.1", port=8000)

        def run(self, transport: str = "stdio") -> None:
            calls.append(transport)

    monkeypatch.setattr(server, "app", FakeApp())
    monkeypatch.setattr(
        server,
        "parse_args",
        lambda: Namespace(transport="stdio", port=8080, host="0.0.0.0"),
    )

    server.main()

    assert calls == ["stdio"]


def test_main_runs_streamable_http_with_configured_host_and_port(monkeypatch) -> None:
    calls: list[tuple[str, str, int]] = []

    class FakeApp:
        def __init__(self) -> None:
            self.settings = SimpleNamespace(host="127.0.0.1", port=8000)

        def run(self, transport: str = "stdio") -> None:
            calls.append((transport, self.settings.host, self.settings.port))

    monkeypatch.setattr(server, "app", FakeApp())
    monkeypatch.setattr(
        server,
        "parse_args",
        lambda: Namespace(transport="streamable-http", port=8081, host="0.0.0.0"),
    )

    server.main()

    assert calls == [("streamable-http", "0.0.0.0", 8081)]


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _server_params() -> StdioServerParameters:
    project_root = Path(__file__).resolve().parents[2]
    return StdioServerParameters(
        command="uv",
        args=["run", "gwh-mcp"],
        cwd=str(project_root),
    )


@pytest.mark.asyncio
async def test_mcp_server_uses_single_root_as_default_repo(sample_repo: Path) -> None:
    async def list_roots(_context) -> types.ListRootsResult:
        return types.ListRootsResult(
            roots=[types.Root(uri=sample_repo.as_uri(), name="sample-repo")]
        )

    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write, list_roots_callback=list_roots) as session:
            await session.initialize()
            result = await session.call_tool("get_project_evolution", {"limit": 1})

    assert result.isError is False
    assert result.content[0].text is not None
    assert "Repository:" in result.content[0].text
    assert str(sample_repo) in result.content[0].text
    assert "feat: add recorder module" in result.content[0].text


@pytest.mark.asyncio
async def test_mcp_server_rejects_ambiguous_multiple_git_roots(
    sample_repo: Path,
    tmp_path: Path,
) -> None:
    other_repo = tmp_path / "other-repo"
    other_repo.mkdir()
    _git(other_repo, "init", "-b", "main")
    _git(other_repo, "config", "user.name", "Test User")
    _git(other_repo, "config", "user.email", "test@example.com")
    (other_repo / "README.md").write_text("# Other repo\n", encoding="utf-8")
    _git(other_repo, "add", "README.md")
    _git(other_repo, "commit", "-m", "docs: bootstrap other repository")

    async def list_roots(_context) -> types.ListRootsResult:
        return types.ListRootsResult(
            roots=[
                types.Root(uri=sample_repo.as_uri(), name="sample-repo"),
                types.Root(uri=other_repo.as_uri(), name="other-repo"),
            ]
        )

    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write, list_roots_callback=list_roots) as session:
            await session.initialize()
            result = await session.call_tool("get_project_evolution", {"limit": 1})

    assert result.isError is True
    assert result.content[0].text is not None
    assert "Multiple git repositories found in MCP roots" in result.content[0].text
