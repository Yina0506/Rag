FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /uvx /usr/local/bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Cache-friendly: resolve deps before copying the rest of the source.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY src ./src
COPY README.md ./
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:${PATH}"

CMD ["python", "-m", "rag"]
