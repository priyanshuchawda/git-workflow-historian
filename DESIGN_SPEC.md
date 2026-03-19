# DESIGN_SPEC.md

## Overview
Git Workflow Historian is a minimal AI reasoning system that reconstructs developer
intent from Git history rather than answering from the current codebase alone.
The system has three strict layers: an ADK agent for reasoning, a custom FastMCP
server for Git and code lookup tools, and a local or mounted Git repository as
the external source of truth.

The primary job of the system is to turn raw repository history into a coherent
explanation of why the code evolved the way it did. It should answer questions
such as what changed recently, why a function exists, or how a subsystem
evolved over time. It must synthesize history instead of dumping logs.

The first release will optimize for correctness, testability, and clean
architecture rather than breadth. It will use a Python FastMCP server for Git
tooling, a Python ADK `LlmAgent` as the historian, and a thin FastAPI service
that exposes `POST /ask` for local use and Cloud Run deployment.

## Example Use Cases
1. A user asks, "What changed recently?"
   Expected behavior: the agent calls the recent-history MCP tool, inspects the
   last few commits, and returns a concise synthesis of the latest direction of
   development.

2. A user asks, "Why does this function exist?"
   Expected behavior: the agent first locates the symbol in the repository, then
   uses blame and commit diff history to explain the original intent and what
   problem the change appears to have solved.

3. A user asks, "Explain auth evolution."
   Expected behavior: the agent searches commit history for related terms,
   examines grouped changes, and summarizes the progression of the auth system.

4. A user asks, "What was the reasoning behind the last refactor in recorder?"
   Expected behavior: the agent combines recent history, symbol search, and
   blame results to describe the refactor intent, likely regression concerns,
   and how the system moved from one state to another.

5. A user tests the system against an external repository path.
   Expected behavior: the MCP server safely resolves the repo path, runs Git
   commands inside that repo only, and returns tool data that the agent can use.

## Tools Required
### MCP tools
1. `get_project_evolution(limit: int = 5, repo_path: str | None = None) -> str`
   Purpose: return the most recent commits with a file-level summary.
   Data source: `git log`, `git show --stat --summary`.

2. `deep_blame(file_path: str, line_number: int, repo_path: str | None = None) -> str`
   Purpose: find which commit owns a line and return the owning commit plus full
   diff content.
   Data source: `git blame --porcelain`, `git show`.

3. `find_related_changes(keyword: str, repo_path: str | None = None) -> str`
   Purpose: search commit messages for concept evolution.
   Data source: `git log --grep`.

4. `locate_symbol(symbol: str, limit: int = 10, repo_path: str | None = None) -> str`
   Purpose: locate the current file and line number for a symbol or keyword so
   the agent can bridge current code and history when answering "why does this
   function exist?" style questions.
   Data source: `git grep`.

### ADK agent
- Single `LlmAgent` using the exact system prompt from the user.
- MCP client integration through `McpToolset`.
- Reasoning-only layer: decides if history is required, selects tools, and
  produces synthesized answers.

### FastAPI service
- `POST /ask`
- Accepts at least a user question and optional repo path/session ids.
- Runs the ADK historian and returns the synthesized answer.

## Constraints & Safety Rules
- The MCP server must do data retrieval only, not interpretation.
- The agent must never rely only on model priors for history or code-evolution
  questions when tool use is relevant.
- Git commands must only execute inside the resolved repository root.
- File paths passed into tools must be normalized and rejected if they escape the
  repository root.
- The first release must stay minimal: no UI, no database, no vector store, no
  unnecessary multi-agent orchestration.
- The system must remain deployable on Cloud Run.
- The agent prompt provided by the user must be used exactly as the agent system
  prompt.

## Success Criteria
- The MCP server tools return stable, parseable, human-readable outputs for a
  real Git repo.
- Automated tests cover recent-history lookup, blame lookup, keyword history
  lookup, and symbol lookup against a temporary Git repository.
- The ADK agent can call MCP tools and synthesize answers for the required demo
  prompts.
- The FastAPI service exposes a working `POST /ask` endpoint.
- The project runs locally with `uv sync` and can be containerized for Cloud
  Run.
- The repository is developed in small mergeable branches with test evidence at
  each step.

## Edge Cases to Handle
1. The target path is not a Git repository.
2. The repo exists but has no commits yet.
3. `deep_blame` is asked for a missing file or an invalid line number.
4. `find_related_changes` finds no matching commits.
5. `locate_symbol` finds multiple matches across files.
6. The repository contains renamed files and the history output should still be
   readable.
7. The deployment environment has no explicit repo path, so the server must fall
   back to the current working directory or configured environment variable.
