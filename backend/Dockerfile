FROM python:3.12-slim AS base

WORKDIR /app

# Install system packages needed for native extensions and health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Development ──────────────────────────────────────────────────────────────
FROM base AS development

# Copy only the dependency manifest first so pip install is cached separately
# from source code changes (pyproject.toml rarely changes; app/ changes often).
COPY pyproject.toml .

# Create a minimal package stub so hatchling can resolve the editable install
# before the real source is present. COPY . . below overwrites this with
# the real source without busting the cached pip layer.
RUN mkdir -p app && touch app/__init__.py

RUN pip install --no-cache-dir -e ".[dev]"

# Copy the real application source (overwrites the stub above)
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
