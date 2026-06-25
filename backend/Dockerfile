FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV VIRTUAL_ENV=/opt/venv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN python -m venv /opt/venv \
  && pip install --upgrade pip \
  && pip install uv \
  && uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN addgroup --system app \
  && adduser --system --ingroup app app

COPY --from=builder /opt/venv /opt/venv

COPY src ./src

USER app

EXPOSE 8000

CMD ["uvicorn", "src.retrieval.api:app", "--host", "0.0.0.0", "--port", "8000"]
