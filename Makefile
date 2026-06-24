.DEFAULT_GOAL := help

.PHONY: help up down build migrate \
        test-backend test-frontend test-e2e test \
        lint lint-backend lint-frontend \
        shell-backend shell-frontend logs

help: ## Show this help
	@python -c "import re; [print('\033[36m{:<22}\033[0m {}'.format(m.group(1), m.group(2))) for line in open('Makefile').readlines() for m in [re.match(r'^([a-zA-Z_-]+):.*?## (.+)', line)] if m]"

# ── Docker Compose ────────────────────────────────────────────────────────────

up: ## Start all services (detached)
	docker compose up -d

up-build: ## Build images and start all services
	docker compose up -d --build

down: ## Stop and remove containers
	docker compose down

build: ## Build all images without starting
	docker compose build

reset: ## Teardown volumes and rebuild from scratch
	docker compose down -v
	docker compose up -d --build

logs: ## Tail logs for all services
	docker compose logs -f

# ── Database ──────────────────────────────────────────────────────────────────

migrate: ## Run Alembic migrations inside the backend container
	docker compose exec backend alembic upgrade head

migrate-down: ## Roll back the latest Alembic migration
	docker compose exec backend alembic downgrade -1

# ── Testing ───────────────────────────────────────────────────────────────────

test-backend: ## Run Python pytest suite
	docker compose exec backend pytest --cov=app --cov-report=term-missing

test-frontend: ## Run Laravel PHPUnit suite
	docker compose exec frontend ./vendor/bin/phpunit

test-e2e: ## Run Playwright end-to-end tests
	cd e2e && npx playwright test

test: test-backend test-frontend ## Run backend and frontend test suites

# ── Linting ───────────────────────────────────────────────────────────────────

lint-backend: ## Run ruff check + format check on backend/
	docker compose exec backend ruff check app tests
	docker compose exec backend ruff format --check app tests

lint-frontend: ## Run Laravel Pint on frontend/
	docker compose exec frontend ./vendor/bin/pint --test

lint: lint-backend lint-frontend ## Run all linters

# ── Utility ───────────────────────────────────────────────────────────────────

shell-backend: ## Open a shell in the backend container
	docker compose exec backend bash

shell-frontend: ## Open a shell in the frontend container
	docker compose exec frontend sh

key-generate: ## Generate a new Laravel APP_KEY (update .env with the output)
	docker compose exec frontend php artisan key:generate --show
