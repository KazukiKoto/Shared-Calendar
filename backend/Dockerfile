FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Development ──────────────────────────────────────────────────────────────
FROM base AS development

COPY pyproject.toml .
# Stub lets hatchling resolve the editable install before real source arrives.
# COPY . . below overwrites it without busting the pip layer cache.
RUN mkdir -p app && touch app/__init__.py
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ── Production ───────────────────────────────────────────────────────────────
FROM base AS production

# Copy only what pip needs to install, so the layer is cached independently
# of future source changes.
COPY pyproject.toml .
COPY app/ app/
RUN pip install --no-cache-dir "."

RUN useradd --system --no-create-home --shell /bin/false appuser
USER appuser

EXPOSE 8000
# Four workers; tune WEB_CONCURRENCY at runtime for the target host.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
