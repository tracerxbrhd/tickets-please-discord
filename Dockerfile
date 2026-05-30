FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE alembic.ini ./
COPY bot ./bot
COPY web ./web

RUN pip install --upgrade pip \
    && pip install --no-cache-dir .

CMD ["python", "-m", "bot.main"]
