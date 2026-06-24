# Stage 10 — Testing & Quality Assurance

## Goal

Bring the entire test suite to production quality: pytest unit and integration tests for the FastAPI backend (≥ 80% total line coverage), PHPUnit feature tests for the Laravel frontend (≥ 80% method coverage on all controllers), and five end-to-end Playwright scenarios covering the core user journeys across the fully integrated stack. All three suites run in CI on every pull request; `make test` orchestrates them locally. Coverage reports are published as CI artefacts.

---

## User Stories

1. As a developer, I want pytest tests to cover all API endpoints with at least 80% line coverage, so that regressions are caught automatically.
2. As a developer, I want PHPUnit tests to cover all Laravel controllers using faked HTTP calls, so that I can refactor confidently without running a live backend.
3. As a QA engineer, I want Playwright E2E tests covering the five core user journeys, so that the full system is validated as an integrated whole before any release.
4. As a CI maintainer, I want a single `make test` command to run all three suites and fail fast on any error, so that feedback is quick and unambiguous.
5. As a developer, I want coverage reports published as CI artefacts, so that I can identify gaps without running tests locally.

---

## Acceptance Criteria

1. `pytest --cov=app --cov-report=xml --cov-fail-under=80` exits `0` in CI.
2. `./vendor/bin/phpunit --coverage-text` reports ≥ 80% method coverage across all `app/Http/Controllers/` classes.
3. All pytest tests run against a dedicated test database (`POSTGRES_DB=test_calendar`) using transaction rollback after each test (no data bleeds between tests).
4. FastAPI tests use `httpx.AsyncClient` with the FastAPI app and a pytest fixture that wraps each test case in a DB savepoint rolled back after the test.
5. PHPUnit tests use `Http::fake()` for all `ApiClient` calls; no real HTTP requests leave the PHP process during test execution.
6. Playwright tests run inside a Docker Compose profile `--profile e2e` that starts `mailpit` and a seeded database containing two pre-registered users.
7. Five mandatory Playwright test scenarios:

   | ID     | Scenario |
   |--------|----------|
   | E2E-01 | Register → Login → Create calendar → Create event → Event visible on calendar |
   | E2E-02 | Share calendar with second user → Second user accepts invitation → Shared event visible to second user |
   | E2E-03 | Create weekly recurring event → Verify occurrences appear on correct weekday dates across two months |
   | E2E-04 | Edit single occurrence of recurring event → Verify only that date changes, others unchanged |
   | E2E-05 | Create event → Add 15-minute reminder → Verify reminder email received in Mailpit API |

8. Each Playwright test file uses Page Object Models defined in `e2e/pages/`.
9. CI `test` job produces three artefacts: `backend/coverage.xml`, `frontend/coverage/index.html`, `e2e/playwright-report/`.
10. `make test` runs `make test-backend`, `make test-frontend`, `make test-e2e` in sequence; non-zero exit on any failure.
11. The CI workflow runs the full test suite (all three jobs) on every push to `develop` and every pull request to `main`.
12. All existing tests introduced in Stages 02–09 remain passing; no regressions introduced in this stage.

---

## Key Files / Directories to Create

```
backend/tests/
├── conftest.py                        # async client fixture, DB transaction rollback, test user factory
├── factories/
│   ├── user_factory.py                # factory_boy User factory
│   ├── calendar_factory.py
│   └── event_factory.py
├── test_auth.py                       # expanded from Stage 02
├── test_calendars.py                  # expanded from Stage 03
├── test_events.py                     # expanded from Stage 03
├── test_recurrence.py                 # unit tests for recurrence_service.py expansion logic
├── test_invitations.py                # expanded from Stage 04
├── test_permissions.py                # expanded from Stage 04
└── test_notifications.py              # Stage 05 (mocked BackgroundTasks + Celery)

frontend/tests/
├── Feature/
│   ├── AuthControllerTest.php         # expanded from Stage 06
│   ├── CalendarControllerTest.php     # expanded from Stage 07
│   ├── EventControllerTest.php        # expanded from Stage 08
│   ├── SharingControllerTest.php      # expanded from Stage 09
│   └── InvitationControllerTest.php   # expanded from Stage 09
└── Unit/
    └── ApiClientTest.php              # unit tests for ApiClient (error handling, retry, refresh)

e2e/
├── playwright.config.ts               # baseURL, workers, test dir, reporter: html
├── package.json                       # @playwright/test, typescript
├── pages/
│   ├── LoginPage.ts
│   ├── RegisterPage.ts
│   ├── CalendarPage.ts
│   ├── EventModal.ts
│   ├── ShareModal.ts
│   └── InvitationsPage.ts
└── tests/
    ├── auth.spec.ts                   # E2E-01
    ├── sharing.spec.ts                # E2E-02
    ├── recurrence.spec.ts             # E2E-03 & E2E-04
    └── reminders.spec.ts              # E2E-05 (uses Mailpit REST API to check email)

.github/workflows/ci.yml              # updated: add test-backend, test-frontend, e2e jobs
Makefile                              # updated: test-backend, test-frontend, test-e2e, test
```

---

## CI Workflow Structure (ci.yml additions)

```yaml
test-backend:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:16-alpine
      env: { POSTGRES_DB: test_calendar, POSTGRES_USER: app, POSTGRES_PASSWORD: changeme }
    redis:
      image: redis:7-alpine
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: '3.12' }
    - run: pip install -e ".[dev]"
      working-directory: backend
    - run: pytest --cov=app --cov-report=xml --cov-fail-under=80
      working-directory: backend
    - uses: actions/upload-artifact@v4
      with: { name: backend-coverage, path: backend/coverage.xml }

test-frontend:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: shivammathur/setup-php@v2
      with: { php-version: '8.3', coverage: xdebug }
    - run: composer install --no-interaction
      working-directory: frontend
    - run: ./vendor/bin/phpunit --coverage-html coverage/
      working-directory: frontend
    - uses: actions/upload-artifact@v4
      with: { name: frontend-coverage, path: frontend/coverage/ }

e2e:
  runs-on: ubuntu-latest
  needs: [test-backend, test-frontend]
  steps:
    - uses: actions/checkout@v4
    - run: docker compose --profile e2e up -d --build --wait
    - run: npx playwright install --with-deps
      working-directory: e2e
    - run: npx playwright test
      working-directory: e2e
    - uses: actions/upload-artifact@v4
      with: { name: playwright-report, path: e2e/playwright-report/ }
```

---

## Dependencies

- All prior stages (01–09) must be complete and their own test stubs passing before this stage expands coverage.
