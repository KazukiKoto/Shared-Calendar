# Stage 11 — Deployment & Production Readiness

## Goal

Harden the Docker images for production using multi-stage builds (minimal image size, non-root users), configure Nginx for SSL termination and security headers, expand health check endpoints to probe dependencies, wire up automatic database migrations on container startup, and write the operations runbook. This stage adds no new features — it hardens, optimises, and documents everything built in Stages 01–10 for a real deployment.

---

## User Stories

1. As a DevOps engineer, I want multi-stage Docker builds producing lean production images (< 300 MB backend, < 200 MB frontend), so that deployment artefacts are small and have a reduced attack surface.
2. As a security engineer, I want all HTTP responses to carry standard security headers and the application to enforce HTTPS, so that common web vulnerabilities are mitigated out of the box.
3. As an operations engineer, I want `/health` endpoints to report the status of all dependencies (DB, Redis, backend), so that a load balancer can route traffic away from unhealthy instances automatically.
4. As a system administrator, I want database migrations to run automatically on container startup in production, so that deployments require no manual intervention.
5. As a developer, I want `docker compose --profile prod up` to start the production stack locally, so that production behaviour is testable before a real deployment.
6. As any new team member, I want a documented `RUNBOOK.md` covering all common operations, so that I can operate the system without help from the original author.

---

## Acceptance Criteria

1. `docker build --target production -t backend:prod ./backend` completes and the resulting image is < 300 MB (using `python:3.12-slim`).
2. `docker build --target production -t frontend:prod ./frontend` completes and the resulting image is < 200 MB (using `php:8.3-fpm-alpine`).
3. Both production images run processes as a non-root user with `uid=1000`.
4. The Nginx production config sets the following response headers on all responses:
   - `Strict-Transport-Security: max-age=63072000; includeSubDomains`
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: SAMEORIGIN`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Content-Security-Policy: default-src 'self'; ...` (configured for the app's actual asset sources)
5. Nginx enables gzip compression for `text/html`, `text/css`, `application/javascript`, `application/json`.
6. `GET /health` on the backend returns:
   - `200 {"status": "ok", "db": "ok", "redis": "ok"}` when both are reachable.
   - `503 {"status": "degraded", "db": "error", "redis": "ok"}` (or equivalent) when a dependency is down.
7. `GET /health` on the Laravel frontend returns:
   - `200 {"status": "ok", "backend": "ok"}` when the FastAPI `/health` endpoint is reachable.
   - `503 {"status": "degraded", "backend": "error"}` when it is not.
8. The backend `Dockerfile` production stage uses an `entrypoint.sh` script that runs `alembic upgrade head` before starting uvicorn; a failed migration causes the container to exit non-zero.
9. The Laravel production image runs `php artisan config:cache && php artisan route:cache && php artisan view:cache` as part of the image build step (not at runtime).
10. `docker-compose.prod.yml` override exists that: removes source-code bind mounts, sets `restart: unless-stopped`, and uses pre-built image tags instead of `build:` directives.
11. `.env.production.example` documents every variable from `.env.example` plus: `SENTRY_DSN`, `LOG_LEVEL`, `WORKERS` (uvicorn worker count), `PHP_FPM_MAX_CHILDREN`.
12. `docs/RUNBOOK.md` covers:
    - Starting and stopping all services.
    - Running and rolling back database migrations.
    - Viewing live logs for each service.
    - Rotating the `SECRET_KEY` (FastAPI) and `APP_KEY` (Laravel) without downtime.
    - Emergency procedures: taking the app offline, restoring from a database backup.
13. `README.md` is updated with: an ASCII architecture diagram, quick-start instructions (`git clone`, copy `.env.example`, `docker compose up --build`), link to `docs/RUNBOOK.md`, and a table of all service URLs.
14. The CI `build-images` job (from Stage 01) is updated to build the production targets and push to a container registry (e.g., GitHub Container Registry `ghcr.io`) when commits are pushed to `main`.

---

## Key Files / Directories to Create / Update

```
backend/
├── Dockerfile                         # updated: add 'production' multi-stage target
└── entrypoint.sh                      # alembic upgrade head && exec uvicorn ...

frontend/
├── Dockerfile                         # updated: add 'production' multi-stage target
└── app/Http/Controllers/
    └── HealthController.php           # updated: probe FastAPI /health, return 503 if down

nginx/
├── Dockerfile                         # updated: production target copies certs, hardened config
└── nginx.conf                         # updated: security headers, gzip, SSL stanza

docker-compose.prod.yml                # new: production override file
.env.production.example                # new

docs/
└── RUNBOOK.md                         # new

README.md                              # updated: architecture diagram, quick-start, service table

.github/workflows/ci.yml              # updated: push production images to GHCR on main
```

---

## Dockerfile Multi-Stage Pattern (Backend)

```dockerfile
# ---- base ----
FROM python:3.12-slim AS base
WORKDIR /app
RUN adduser --disabled-password --uid 1000 appuser

# ---- builder ----
FROM base AS builder
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[prod]" --prefix=/install

# ---- development ----
FROM base AS development
COPY --from=builder /install /usr/local
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---- production ----
FROM base AS production
COPY --from=builder /install /usr/local
COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
USER appuser
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

---

## ASCII Architecture Diagram (for README.md)

```
┌──────────────────────────────────────────────────────────┐
│                        Client Browser                    │
└───────────────────────────┬──────────────────────────────┘
                            │ HTTP :80 / :443
                ┌───────────▼───────────┐
                │       Nginx           │
                │  /api/* → backend     │
                │  /*     → frontend    │
                └───┬───────────────┬───┘
                    │               │
        ┌───────────▼──┐     ┌──────▼────────┐
        │  FastAPI      │     │  Laravel      │
        │  :8000        │◄────│  :9000        │
        │  Python 3.12  │     │  PHP 8.3      │
        └──────┬────────┘     └───────────────┘
               │  SQLAlchemy
    ┌──────────▼──────────┐
    │      PostgreSQL      │
    │   calendar_app  /   │
    │      laravel        │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │        Redis         │
    │  sessions / cache /  │
    │  celery task queue   │
    └─────────────────────┘
```

---

## Dependencies

- All prior stages (01–10) must be complete. This stage adds no new features; it hardens and documents what exists.
