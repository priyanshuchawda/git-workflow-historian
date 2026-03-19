"""Programmatic runner helpers for the historian agent."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import APP_NAME, root_agent

HistoryMode = Literal["auto", "story", "focused"]


def _build_user_message(
    question: str,
    repo_path: str | None = None,
    *,
    history_mode: HistoryMode = "auto",
) -> str:
    tool_guidance = (
        "Tool usage rules for this request:\n"
        "- Never invent file paths or line numbers.\n"
        "- For broad implementation, architecture, refactor, or 'whole story' requests, use "
        "get_repo_story to load repo-wide history context.\n"
        "- Do not infer module purpose from file names alone. If you need to explain what code "
        "does, ground that explanation in commit history or current code evidence.\n"
        "- Separate explicit history evidence from inference. If the current direction is not "
        "clear from the repo history, say that directly instead of guessing a roadmap.\n"
        "- Avoid speculative wording such as 'likely', 'probably', 'presumably', or "
        "'suggests'. If an inference is unavoidable, label it explicitly as inference and keep "
        "it minimal.\n"
        "- Do not suggest next implementation steps unless the user explicitly asks for them.\n"
        "- If the user asks for the current direction, describe only the latest observed work. "
        "If the direction is not explicit in history, say 'The current direction is not "
        "explicit in the repo history.'\n"
        "- If the question mentions a function, method, class, or symbol without an exact file "
        "path, call locate_symbol first.\n"
        "- Only call deep_blame after you have a verified file path and line number from the "
        "user or locate_symbol.\n"
        "- Use get_project_evolution for recent-history questions.\n"
        "- Use find_related_changes for subsystem or keyword evolution questions."
    )
    if history_mode == "story":
        tool_guidance += (
            "\n- This request requires full-project context. Call get_repo_story before any "
            "other history tool."
        )
    elif history_mode == "focused":
        tool_guidance += "\n- Keep tool use narrowly scoped to the specific question."
    if not repo_path:
        return f"{tool_guidance}\n\nUser question: {question}"
    return (
        f"Repository path for this request: {repo_path}\n"
        "Use this repo_path value when calling MCP tools.\n\n"
        f"{tool_guidance}\n\n"
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
    history_mode: HistoryMode = "auto",
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

    prompt = _build_user_message(
        question=question,
        repo_path=repo_path,
        history_mode=history_mode,
    )
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
