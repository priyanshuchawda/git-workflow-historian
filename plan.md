# Git Workflow Historian Plan

## Goal
Build a minimal production-ready system that uses:

- an ADK agent as the reasoning layer
- a custom Python FastMCP server as the tool layer
- a local or mounted Git repository as the history source
- a FastAPI `/ask` endpoint for local use and Cloud Run deployment

The system should answer history-aware questions by reconstructing intent from commits, blame, and related change clusters instead of relying only on current code.

## Core Design

### 1. Agent layer
- Use a single ADK `LlmAgent`.
- Give it the exact system prompt you provided.
- Connect it to MCP tools through ADK `McpToolset`.
- Make it decide when history is required and which MCP tool to call.
- Keep reasoning in the agent only, never in the MCP server.

### 2. MCP server layer
- Build a standalone Python FastMCP server.
- Expose only Git data retrieval tools.
- Use `subprocess` for `git log`, `git show`, `git blame`, and commit search commands.
- Return clean structured text, not analysis.

### 3. API layer
- Add a small FastAPI service with `POST /ask`.
- The endpoint will pass the user query into the ADK runner and return the synthesized answer.
- Keep the HTTP layer thin and stateless.

## Planned Tooling
- `get_project_evolution(limit: int = 5)`
  Returns recent commits with commit message, sha, changed files, and short file-level summary.
- `deep_blame(file_path: str, line_number: int)`
  Finds the owning commit for a line using `git blame`, then returns commit message plus full commit diff.
- `find_related_changes(keyword: str)`
  Searches commit messages, groups relevant commits, and returns short summaries.

## Project Shape
- `app/agent.py`
  ADK agent definition with exact historian prompt.
- `app/__init__.py`
  ADK package entry.
- `mcp_server/server.py`
  FastMCP server and Git tool implementations.
- `service/main.py`
  FastAPI app with `/ask`.
- `tests/`
  Unit tests for MCP tool behavior and integration tests for the `/ask` flow.
- `requirements.txt`
  Python dependencies.
- `Dockerfile`
  Cloud Run container image.
- `README.md`
  Local run, test, and deploy instructions.

## Delivery Phases

### Phase 0: Spec and repo baseline
- Write `DESIGN_SPEC.md` from your requirements plus the exact prompt and success criteria.
- Initialize the project structure from scratch in this directory.
- Because this directory is not currently a Git repo, real PR creation cannot happen yet.
- If you want strict PR-per-phase workflow, we should initialize Git and connect a remote before implementation starts.

### Phase 1: MCP server
- Implement the FastMCP server and the 3 Git tools.
- Add input validation and safe path/repo handling.
- Test each tool against a real sample Git repository.
- Stop after tests pass and review the output shape.

### Phase 2: ADK historian agent
- Implement the ADK agent as an MCP client using `McpToolset`.
- Use synchronous agent definition so deployment stays compatible with ADK Cloud Run guidance.
- Ensure the agent uses tools for code/history questions and synthesizes intent instead of dumping logs.
- Test the 3 demo prompts against a sample repo.

### Phase 3: FastAPI service
- Build `POST /ask`.
- Wire request -> ADK runner -> final answer.
- Add minimal request/response schemas and error handling.
- Test locally with `curl`.

### Phase 4: Production packaging
- Add `requirements.txt`, `Dockerfile`, and environment variable handling.
- Make the app runnable locally and deployable on Cloud Run.
- Add deployment commands for both `adk deploy cloud_run` and `gcloud run deploy` with Dockerfile.
- Test container startup locally if Docker is available.

### Phase 5: Final validation
- Run unit and integration tests.
- Verify the 3 required demo questions:
  - `What changed recently?`
  - `Why does this function exist?`
  - `Explain auth evolution`
- Confirm the system returns synthesized history-aware answers.

## Testing Strategy
- Unit tests for Git command wrappers and parsing.
- Integration tests with a temporary Git repo created during test setup.
- Endpoint test for `/ask`.
- Manual smoke test with `curl`.
- Each phase only moves forward after its tests pass.

## PR / Merge Workflow
- Intended workflow:
  1. Implement one phase.
  2. Run tests for that phase.
  3. Create a branch and PR.
  4. Merge after review.
  5. Start the next phase.
- Current blocker:
  This folder is not a Git repo and has no remote, so I cannot literally open and merge PRs yet.
- Practical option:
  After your confirmation, I can either:
  - proceed with local phased commits and testing first, or
  - initialize Git here and pause for remote details before any PR-based workflow.

## Minimal Architecture Decision
- Local development:
  ADK agent connects to the FastMCP server over stdio for simplicity.
- Production-ready direction:
  Keep the code structured so the MCP server can later move to a separate HTTP-deployed service if needed.
- For this first version, stdio is the minimal reliable choice.

## What I will do after your confirmation
1. Write `DESIGN_SPEC.md`.
2. Scaffold the minimal codebase.
3. Build Phase 1 and test it.
4. Pause at each phase boundary with concrete test results before moving on.

## Important assumptions
- Python implementation only.
- One ADK historian agent, not a multi-agent system.
- The Git repository to analyze will be local or mounted into the container.
- We will keep the first release minimal and avoid vector stores, databases, UI, and extra memory layers.
