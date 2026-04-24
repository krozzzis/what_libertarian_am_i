FROM ghcr.io/astral-sh/uv:latest

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src /app/src
COPY data /app/data

ENV BOT_TOKEN=${BOT_TOKEN}
ENV QUIZ_PATH=/app/data/quiz.json5
ENV PARTY_URL=${PARTY_URL:-https://lpr.ural.vrn.ru/join}

CMD ["python", "-m", "src.main"]