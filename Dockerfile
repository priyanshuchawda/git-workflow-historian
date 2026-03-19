FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
RUN useradd --create-home appuser

COPY --chown=appuser:appuser pyproject.toml uv.lock README.md ./
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser mcp_server ./mcp_server
COPY --chown=appuser:appuser service ./service

RUN chown -R appuser:appuser /app

USER appuser

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}" \
    PORT=8080

EXPOSE 8080

CMD ["gwh-api"]
