from __future__ import annotations

import httpx
import pytest

from service.main import app


@pytest.mark.asyncio
async def test_ask_endpoint_returns_answer(monkeypatch) -> None:
    async def fake_ask_question(
        question: str,
        *,
        repo_path: str | None = None,
        history_mode: str = "auto",
        user_id: str = "api-user",
        session_id: str | None = None,
    ) -> str:
        assert question == "What changed recently?"
        assert repo_path == "/tmp/repo"
        assert history_mode == "story"
        assert user_id == "alice"
        assert session_id == "session-1"
        return "Recent work focused on auth cleanup."

    monkeypatch.setattr("service.main.ask_question", fake_ask_question)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ask",
            json={
                "question": "What changed recently?",
                "repo_path": "/tmp/repo",
                "history_mode": "story",
                "user_id": "alice",
                "session_id": "session-1",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Recent work focused on auth cleanup.",
        "session_id": "session-1",
    }


@pytest.mark.asyncio
async def test_ask_endpoint_translates_value_errors(monkeypatch) -> None:
    async def fake_ask_question(*args, **kwargs) -> str:
        raise ValueError("question must not be empty")

    monkeypatch.setattr("service.main.ask_question", fake_ask_question)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ask",
            json={"question": "x", "repo_path": "/tmp/repo"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "question must not be empty"
