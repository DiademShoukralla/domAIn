FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts/entrypoint.sh ./scripts/entrypoint.sh

RUN pip install --no-cache-dir .

RUN chmod +x ./scripts/entrypoint.sh

EXPOSE 8080

CMD ["./scripts/entrypoint.sh"]
