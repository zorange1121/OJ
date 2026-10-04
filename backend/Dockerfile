FROM python:3.12-slim

COPY --from=docker:29-cli /usr/local/bin/docker /usr/local/bin/docker

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

RUN chmod +x docker-entrypoint.sh
RUN mkdir -p /app/data/problem_data && chown -R 10001:10001 /app/data
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
