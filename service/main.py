"""FastAPI application exposing the historian agent via POST /ask."""

from __future__ import annotations

import asyncio
import os

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.runner import ask_question

REQUEST_TIMEOUT_SECONDS = float(os.getenv("GWH_REQUEST_TIMEOUT_SECONDS", "120"))


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question for the historian agent.")
    repo_path: str | None = Field(
        default=None,
        description="Optional absolute path to the repository for this request.",
    )
    user_id: str = Field(default="api-user", description="Logical caller identifier.")
    session_id: str | None = Field(default=None, description="Optional session identifier.")


class AskResponse(BaseModel):
    answer: str
    session_id: str | None = None


app = FastAPI(title="Git Workflow Historian", version="0.1.0")


@app.post("/ask", response_model=AskResponse)
async def ask_endpoint(request: AskRequest) -> AskResponse:
    try:
        answer = await asyncio.wait_for(
            ask_question(
                request.question,
                repo_path=request.repo_path,
                user_id=request.user_id,
                session_id=request.session_id,
            ),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Historian request timed out.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AskResponse(answer=answer, session_id=request.session_id)


def main() -> None:
    uvicorn.run(
        "service.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
    )


if __name__ == "__main__":
    main()
