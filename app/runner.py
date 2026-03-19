"""Programmatic runner helpers for the historian agent."""

from __future__ import annotations

from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import APP_NAME, root_agent


def _build_user_message(question: str, repo_path: str | None = None) -> str:
    if not repo_path:
        return question
    return (
        f"Repository path for this request: {repo_path}\n"
        "Use this repo_path value when calling MCP tools.\n\n"
        f"User question: {question}"
    )


def _extract_text(content: types.Content | None) -> str:
    if content is None or not content.parts:
        return ""

    text_parts: list[str] = []
    for part in content.parts:
        if getattr(part, "text", None):
            text_parts.append(part.text)
    return "\n".join(text_parts).strip()


async def ask_question(
    question: str,
    *,
    repo_path: str | None = None,
    user_id: str = "local-user",
    session_id: str | None = None,
) -> str:
    """Run the historian agent once and return the final response text."""
    if not question.strip():
        raise ValueError("question must not be empty")

    active_session_id = session_id or uuid4().hex
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=active_session_id,
        state={},
    )
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    prompt = _build_user_message(question=question, repo_path=repo_path)
    content = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    final_response = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=active_session_id,
        new_message=content,
    ):
        if event.is_final_response():
            final_response = _extract_text(event.content)

    if not final_response:
        raise RuntimeError("The agent did not return a final response.")
    return final_response
