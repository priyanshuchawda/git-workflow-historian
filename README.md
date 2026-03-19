# Git Workflow Historian

Git Workflow Historian is an ADK-based reasoning system that explains developer
intent from Git history. The project is being built in mergeable feature slices:
MCP Git tooling first, then the ADK historian agent, then the FastAPI `/ask`
service and deployment packaging.

The current branch contains:
- the approved design spec
- Python project metadata
- a FastMCP server for Git history and symbol lookup
- automated tests against a temporary Git repository

## Current commands
```bash
uv sync --all-extras
uv run pytest
uv run gwh-mcp
```

The full local run instructions, Cloud Run deployment steps, and curl examples
will be finalized once the ADK agent and FastAPI service are added.
