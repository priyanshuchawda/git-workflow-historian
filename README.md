# Git Workflow Historian

Git Workflow Historian is an ADK-based reasoning system that explains developer
intent from Git history instead of relying only on the current codebase.

It has three layers:
- `app/`: ADK reasoning layer
- `mcp_server/`: FastMCP Git and code lookup tools
- `service/`: FastAPI `POST /ask` entrypoint

## Features
- Recent-history summaries via `get_project_evolution`
- Line-level intent lookup via `deep_blame`
- Commit-message evolution search via `find_related_changes`
- Current symbol discovery via `locate_symbol`
- ADK historian agent with the exact prompt requested
- FastAPI `POST /ask` endpoint for local use and Cloud Run deployment

## Project structure
```text
.
├── app/
├── mcp_server/
├── service/
├── tests/
├── DESIGN_SPEC.md
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

## Requirements
- Python 3.11+
- `uv`
- `git`
- One of:
  - `GOOGLE_API_KEY` for Gemini API, or
  - Vertex/Google Cloud credentials plus `GOOGLE_GENAI_USE_VERTEXAI=True`

## Local setup
```bash
uv sync --extra dev
```

### Environment
For Gemini API key based usage:
```bash
export GOOGLE_API_KEY="your-api-key"
export GOOGLE_GENAI_USE_VERTEXAI="False"
```

For Vertex AI based usage:
```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI="True"
```

Optional runtime settings:
```bash
export GIT_WORKFLOW_REPO_PATH="/absolute/path/to/the/repo/you-want-to-analyze"
export GWH_MODEL="gemini-3-flash-preview"
export GWH_MCP_SERVER_URL=""  # leave unset to use local stdio MCP
```

## Run locally
Start the FastAPI service:
```bash
uv run gwh-api
```

Send a request:
```bash
curl -X POST http://127.0.0.1:8080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What changed recently?",
    "repo_path": "/absolute/path/to/repo"
  }'
```

Example request for intent lookup:
```bash
curl -X POST http://127.0.0.1:8080/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Why does validate_token exist?",
    "repo_path": "/absolute/path/to/repo"
  }'
```

## Run tests
```bash
uv run ruff check .
uv run pytest
```

## MCP server only
Run the MCP server directly over stdio:
```bash
uv run gwh-mcp
```

Run it as streamable HTTP:
```bash
uv run gwh-mcp --transport streamable-http --port 8081
```

## Cloud Run deployment
Build locally:
```bash
docker build -t git-workflow-historian .
```

Deploy with `gcloud`:
```bash
gcloud run deploy git-workflow-historian \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=False,GOOGLE_API_KEY=YOUR_API_KEY"
```

If using Vertex AI instead of an API key:
```bash
gcloud run deploy git-workflow-historian \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=YOUR_PROJECT,GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=True"
```

## Notes
- The agent uses local stdio MCP by default because it is the simplest reliable
  deployment shape for a single-container Cloud Run service.
- If you later deploy the MCP server separately, set `GWH_MCP_SERVER_URL` and
  the agent will switch to streamable HTTP MCP.
