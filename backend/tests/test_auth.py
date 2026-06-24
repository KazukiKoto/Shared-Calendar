import redis.asyncio as aioredis
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import store_reset_token
from app.models.user import User

# ── helpers ──────────────────────────────────────────────────────────────────


async def register(client: AsyncClient, email: str = "alice@example.com") -> dict:
    r = await client.post(
        "/api/v1/auth/register",
        json={"name": "Alice", "email": email, "password": "secret99"},
    )
    return r.json()


async def login(client: AsyncClient, email: str = "alice@example.com") -> dict:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "secret99"},
    )
    return r.json()


# ── register ─────────────────────────────────────────────────────────────────


async def test_register_success(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "secret99"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert "id" in body
    assert "password" not in body
    assert "hashed_password" not in body


async def test_register_duplicate_email(client: AsyncClient) -> None:
    await register(client)
    r = await client.post(
        "/api/v1/auth/register",
        json={"name": "Alice2", "email": "alice@example.com", "password": "secret99"},
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "Email already registered"


async def test_register_short_password(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "short"},
    )
    assert r.status_code == 422


# ── login ─────────────────────────────────────────────────────────────────────


async def test_login_success(client: AsyncClient) -> None:
    await register(client)
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "secret99"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


async def test_login_wrong_password(client: AsyncClient) -> None:
    await register(client)
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "wrongpass"},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid credentials"


async def test_login_unknown_email(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "secret99"},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid credentials"


# ── refresh ───────────────────────────────────────────────────────────────────


async def test_refresh_success(client: AsyncClient) -> None:
    await register(client)
    tokens = await login(client)
    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" not in body


async def test_refresh_invalid_token(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not.a.valid.token"},
    )
    assert r.status_code == 401


# ── logout ────────────────────────────────────────────────────────────────────


async def test_logout_success(client: AsyncClient) -> None:
    await register(client)
    tokens = await login(client)
    r = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 204


async def test_logout_missing_token(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 401


async def test_logout_invalid_token(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer bad.token.here"},
    )
    assert r.status_code == 401


async def test_protected_endpoint_rejects_revoked_token(client: AsyncClient) -> None:
    await register(client)
    tokens = await login(client)
    access = tokens["access_token"]
    await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access}"},
    )
    r = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 401


# ── password reset ────────────────────────────────────────────────────────────


async def test_password_reset_request_registered(client: AsyncClient) -> None:
    await register(client)
    r = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "alice@example.com"},
    )
    assert r.status_code == 200
    assert "reset link" in r.json()["message"].lower()


async def test_password_reset_request_unknown_email(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "nobody@example.com"},
    )
    assert r.status_code == 200  # no enumeration


async def test_password_reset_confirm_invalid_token(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "invalid-token", "new_password": "newpassword1"},
    )
    assert r.status_code == 400


async def test_password_reset_full_flow(
    client: AsyncClient, db: AsyncSession, redis_client: aioredis.Redis
) -> None:
    await register(client)
    user = await db.scalar(select(User).where(User.email == "alice@example.com"))
    assert user is not None

    reset_token = "test-reset-token-xyz789"
    await store_reset_token(redis_client, reset_token, user.id)

    r = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "newpassword1"},
    )
    assert r.status_code == 200
    assert "updated" in r.json()["message"].lower()

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "newpassword1"},
    )
    assert r.status_code == 200


# ── users/me ─────────────────────────────────────────────────────────────────


async def test_get_me(client: AsyncClient) -> None:
    await register(client)
    tokens = await login(client)
    r = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["timezone"] == "UTC"
    assert "updated_at" in body


async def test_get_me_no_token(client: AsyncClient) -> None:
    r = await client.get("/api/v1/users/me")
    assert r.status_code == 401


async def test_patch_me(client: AsyncClient) -> None:
    await register(client)
    tokens = await login(client)
    r = await client.patch(
        "/api/v1/users/me",
        json={"name": "Alicia", "timezone": "Europe/London"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Alicia"
    assert body["timezone"] == "Europe/London"
