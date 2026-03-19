from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from app.runner import _build_user_message

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATED_DIR = PROJECT_ROOT / "tests" / "eval" / "generated"
REPO_PATH = GENERATED_DIR / "sample_repo"
EVALSET_PATH = GENERATED_DIR / "core_historians.evalset.json"
REPO_PATH_FOR_PROMPTS = "tests/eval/generated/sample_repo"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_sample_repo() -> None:
    if REPO_PATH.exists():
        shutil.rmtree(REPO_PATH)

    REPO_PATH.mkdir(parents=True)

    _git(REPO_PATH, "init", "-b", "main")
    _git(REPO_PATH, "config", "user.name", "Eval User")
    _git(REPO_PATH, "config", "user.email", "eval@example.com")

    _write(REPO_PATH / "README.md", "# Eval repo\n")
    _git(REPO_PATH, "add", "README.md")
    _git(REPO_PATH, "commit", "-m", "docs: bootstrap repository")

    auth_file = REPO_PATH / "src" / "auth.py"
    _write(
        auth_file,
        "\n".join(
            [
                "def authenticate(token: str) -> bool:",
                "    return bool(token)",
                "",
                "",
                "def validate_token(token: str) -> bool:",
                "    return authenticate(token)",
                "",
            ]
        ),
    )
    _git(REPO_PATH, "add", "src/auth.py")
    _git(REPO_PATH, "commit", "-m", "feat: add auth validation helpers")

    _write(
        auth_file,
        "\n".join(
            [
                "def authenticate(token: str) -> bool:",
                "    normalized = token.strip()",
                "    return bool(normalized)",
                "",
                "",
                "def validate_token(token: str) -> bool:",
                "    normalized = token.strip()",
                "    return authenticate(normalized)",
                "",
            ]
        ),
    )
    _git(REPO_PATH, "add", "src/auth.py")
    _git(REPO_PATH, "commit", "-m", "refactor: improve auth flow")

    _write(
        REPO_PATH / "src" / "recorder.py",
        "\n".join(
            [
                "def start_recording(output_path: str) -> str:",
                "    return output_path",
                "",
            ]
        ),
    )
    _git(REPO_PATH, "add", "src/recorder.py")
    _git(REPO_PATH, "commit", "-m", "feat: add recorder module")


def build_evalset() -> None:
    evalset = {
        "eval_set_id": "git_workflow_historian_core",
        "name": "Git Workflow Historian core flows",
        "description": "Core evals for recent history, symbol intent, and keyword evolution.",
        "eval_cases": [
            {
                "eval_id": "recent_history",
                "conversation": [
                    {
                        "invocation_id": "recent_history_turn_1",
                        "user_content": {
                            "role": "user",
                            "parts": [
                                {
                                    "text": _build_user_message(
                                        "What changed recently?",
                                        repo_path=REPO_PATH_FOR_PROMPTS,
                                    )
                                }
                            ],
                        },
                        "final_response": {
                            "role": "model",
                            "parts": [
                                {
                                    "text": (
                                        "The repository has recently undergone several "
                                        "foundational updates, focusing on authentication and new "
                                        "feature modules. Authentication improvements introduced "
                                        "validation helpers in src/auth.py and then refactored "
                                        "the auth flow. A new recorder module was added in "
                                        "src/recorder.py, and the repository was initially "
                                        "bootstrapped with a README."
                                    )
                                }
                            ],
                        },
                        "intermediate_data": {
                            "tool_uses": [
                                {
                                    "name": "get_project_evolution",
                                    "args": {"repo_path": REPO_PATH_FOR_PROMPTS},
                                }
                            ],
                            "intermediate_responses": [],
                        },
                    }
                ],
                "session_input": {"app_name": "app", "user_id": "eval-user", "state": {}},
            },
            {
                "eval_id": "symbol_intent",
                "conversation": [
                    {
                        "invocation_id": "symbol_intent_turn_1",
                        "user_content": {
                            "role": "user",
                            "parts": [
                                {
                                    "text": _build_user_message(
                                        "Why does validate_token exist?",
                                        repo_path=REPO_PATH_FOR_PROMPTS,
                                    )
                                }
                            ],
                        },
                        "final_response": {
                            "role": "model",
                            "parts": [
                                {
                                    "text": (
                                        "validate_token was introduced to serve as an "
                                        "authentication helper function. History shows it began "
                                        "as a wrapper around authenticate, then was refactored so "
                                        "it strips whitespace before delegating to the core auth "
                                        "logic. That evolution made token validation more robust "
                                        "against padded input."
                                    )
                                }
                            ],
                        },
                        "intermediate_data": {
                            "tool_uses": [
                                {
                                    "name": "locate_symbol",
                                    "args": {
                                        "repo_path": REPO_PATH_FOR_PROMPTS,
                                        "symbol": "validate_token",
                                    },
                                },
                                {
                                    "name": "deep_blame",
                                    "args": {
                                        "repo_path": REPO_PATH_FOR_PROMPTS,
                                        "file_path": "src/auth.py",
                                        "line_number": 6,
                                    },
                                },
                            ],
                            "intermediate_responses": [],
                        },
                    }
                ],
                "session_input": {"app_name": "app", "user_id": "eval-user", "state": {}},
            },
            {
                "eval_id": "keyword_evolution",
                "conversation": [
                    {
                        "invocation_id": "keyword_evolution_turn_1",
                        "user_content": {
                            "role": "user",
                            "parts": [
                                {
                                    "text": _build_user_message(
                                        "Explain auth evolution",
                                        repo_path=REPO_PATH_FOR_PROMPTS,
                                    )
                                }
                            ],
                        },
                        "final_response": {
                            "role": "model",
                            "parts": [
                                {
                                    "text": (
                                        "The authentication system evolves in two clear steps. "
                                        "First, the repository creates src/auth.py and adds auth "
                                        "validation helpers. Shortly after, the auth flow is "
                                        "refactored to normalize token input and improve how "
                                        "authentication helpers are invoked."
                                    )
                                }
                            ],
                        },
                        "intermediate_data": {
                            "tool_uses": [
                                {
                                    "name": "find_related_changes",
                                    "args": {
                                        "repo_path": REPO_PATH_FOR_PROMPTS,
                                        "keyword": "auth",
                                    },
                                }
                            ],
                            "intermediate_responses": [],
                        },
                    }
                ],
                "session_input": {"app_name": "app", "user_id": "eval-user", "state": {}},
            },
        ],
    }
    EVALSET_PATH.write_text(json.dumps(evalset, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    build_sample_repo()
    build_evalset()
    print(f"Prepared eval repo: {REPO_PATH}")
    print(f"Prepared eval set: {EVALSET_PATH}")


if __name__ == "__main__":
    main()
