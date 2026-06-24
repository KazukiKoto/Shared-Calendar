# Stage 02 — FastAPI: User Authentication

## Goal

Implement the complete user authentication system in the FastAPI backend: user registration, login with JWT access + refresh tokens, token refresh, logout (token revocation via a Redis blocklist), and a password-reset flow. All inputs are validated with Pydantic v2 models. Passwords are hashed with `bcrypt` at cost factor ≥ 12. The `users` table lives in the `calendar_app` PostgreSQL schema. An Alembic migration creates and is independently reversible.

---

## User Stories

1. As a new user, I want to register with my name, email, and password, so that I can create an account.
2. As a registered user, I want to log in with my email and password and receive a JWT, so that subsequent API calls are authenticated.
3. As an authenticated user, I want to refresh my access token without re-entering my password, so that my session stays alive seamlessly.
4. As an authenticated user, I want to log out and have my tokens invalidated server-side, so that my account is secure on shared devices.
5. As a user who forgot my password, I want to request a reset link sent to my email, so that I can regain access to my account.
6. As a user with a reset link, I want to set a new password using the link's token, so that my account is secured with a new credential.
7. As an authenticated user, I want to view and update my profile (name, timezone), so that my display name and event times are correct.

---

## Acceptance Criteria

1. `POST /api/v1/auth/register` with valid `{name, email, password}` returns `201` with `{id, name, email, created_at}` — no password field in the response.
2. Registering with an already-used email returns `409 Conflict` with `{"detail": "Email already registered"}`.
3. Registering with a password shorter than 8 characters returns `422 Unprocessable Entity` with a Pydantic validation error body.
4. `POST /api/v1/auth/login` with valid credentials returns `200` with `{access_token, refresh_token, token_type: "bearer", expires_in}`.
5. `POST /api/v1/auth/login` with wrong password or unknown email returns `401 Unauthorized` with `{"detail": "Invalid credentials"}` — no distinction between the two cases (no user enumeration).
6. `POST /api/v1/auth/refresh` with a valid refresh token returns `200` with a new `{access_token, token_type, expires_in}`.
7. `POST /api/v1/auth/refresh` with an expired or revoked refresh token returns `401`.
8. `POST /api/v1/auth/logout` with a valid `Authorization: Bearer <token>` header blacklists the access token in Redis and returns `204 No Content`.
9. Any protected endpoint called with a blacklisted access token returns `401`.
10. `POST /api/v1/auth/password-reset/request` with a registered email returns `200 {"message": "..."}`  and queues a reset email; an unregistered email returns the same `200` response (no enumeration).
11. `POST /api/v1/auth/password-reset/confirm` with a valid `{token, new_password}` updates the password hash, invalidates the token, and returns `200`.
12. `POST /api/v1/auth/password-reset/confirm` with an expired or already-used token returns `400 Bad Request`.
13. `GET /api/v1/users/me` with a valid Bearer token returns `{id, name, email, timezone, created_at, updated_at}`.
14. `PATCH /api/v1/users/me` accepts `{name?, timezone?}` and returns the updated user object.
15. Passwords are stored as bcrypt hashes; plaintext passwords never appear in logs or responses.
16. All auth endpoints are covered by pytest tests achieving ≥ 90% line coverage for `app/api/v1/auth.py` and `app/core/security.py`.
17. Alembic migration `001_create_users_table.py` runs on a clean database and is reversible (`alembic downgrade -1` restores the prior state).

---

## API Endpoint Signatures

```
POST   /api/v1/auth/register
       Body:   RegisterRequest(name: str, email: EmailStr, password: str min_length=8)
       201:    UserResponse(id: UUID, name: str, email: str, created_at: datetime)

POST   /api/v1/auth/login
       Body:   LoginRequest(email: EmailStr, password: str)
       200:    TokenResponse(access_token: str, refresh_token: str, token_type: str, expires_in: int)

POST   /api/v1/auth/refresh
       Body:   RefreshRequest(refresh_token: str)
       200:    AccessTokenResponse(access_token: str, token_type: str, expires_in: int)

POST   /api/v1/auth/logout
       Header: Authorization: Bearer <access_token>
       204:    (no body)

POST   /api/v1/auth/password-reset/request
       Body:   PasswordResetRequestBody(email: EmailStr)
       200:    MessageResponse(message: str)

POST   /api/v1/auth/password-reset/confirm
       Body:   PasswordResetConfirmBody(token: str, new_password: str min_length=8)
       200:    MessageResponse(message: str)

GET    /api/v1/users/me
       Header: Authorization: Bearer <access_token>
       200:    UserDetailResponse(id, name, email, timezone, created_at, updated_at)

PATCH  /api/v1/users/me
       Header: Authorization: Bearer <access_token>
       Body:   UpdateUserRequest(name?: str, timezone?: str)
       200:    UserDetailResponse
```

---

## Key Files / Directories to Create

```
backend/
├── alembic/
│   └── versions/
│       └── 001_create_users_table.py
└── app/
    ├── api/
    │   └── v1/
    │       ├── __init__.py
    │       ├── router.py             # aggregates all v1 sub-routers
    │       ├── auth.py               # register, login, refresh, logout, password-reset routes
    │       └── users.py              # /users/me routes
    ├── core/
    │   ├── config.py                 # pydantic-settings BaseSettings
    │   ├── database.py               # SQLAlchemy async engine + session factory
    │   ├── redis.py                  # Redis connection pool
    │   └── security.py              # JWT create/decode, bcrypt, token blocklist
    ├── models/
    │   └── user.py                   # SQLAlchemy ORM User model
    ├── schemas/
    │   └── auth.py                   # Pydantic v2 request/response schemas
    └── services/
        ├── auth_service.py           # register, login, refresh, reset business logic
        └── email_service.py          # stub — completed in Stage 05
```

```
backend/tests/
├── conftest.py                       # async test client, DB session override, test fixtures
└── test_auth.py
```

---

## Database Schema

```sql
-- schema: calendar_app
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    timezone        VARCHAR(50)  NOT NULL DEFAULT 'UTC',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_email ON users(email);
```

---

## Dependencies

- Stage 01 (Docker infrastructure, PostgreSQL running with `calendar_app` schema, `pyproject.toml` with all dependencies, `app/main.py` stub).
