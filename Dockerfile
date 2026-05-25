FROM ghcr.io/astral-sh/uv:0.6.14-python3.13-bookworm-slim

LABEL org.opencontainers.image.source="https://github.com/krozzzis/libertest"
LABEL org.opencontainers.image.description="Libertest bot"

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HOME=/app \
    QUIZ_PATH=/app/data/quiz.json5

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src /app/src
RUN uv sync --frozen --no-dev && \
    rm -rf /root/.cache/uv && \
    addgroup --system --gid 1001 app && \
    adduser --system --uid 1001 --gid 1001 app && \
    mkdir -p /app/logs && \
    chown -R app:app /app

USER app

CMD ["uv", "run", "src/main.py"]
