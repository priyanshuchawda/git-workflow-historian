from __future__ import annotations

from argparse import Namespace
from types import SimpleNamespace

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
