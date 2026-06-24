# Stage 06 — Laravel: Foundation & Authentication

## Goal

Scaffold the Laravel 11 application as a pure frontend that delegates all user data concerns to the FastAPI backend over HTTP. Implement registration, login, and logout flows via Blade views. A centralised `ApiClient` service class wraps all HTTP calls using Laravel's `Http` facade; a dedicated middleware auto-refreshes the FastAPI JWT before it expires. Laravel stores the JWT, refresh token, and user data in the server-side session — Sanctum is used only for CSRF protection on form submissions, not for its own token system.

---

## User Stories

1. As a new user, I want to register through a web form, so that I can create an account.
2. As a registered user, I want to log in with my email and password, so that I can access my calendar.
3. As an authenticated user, I want to log out and have my session cleared, so that my account is secure on shared devices.
4. As a developer, I want all FastAPI HTTP calls centralised in a single `ApiClient` service, so that HTTP logic is not scattered across controllers.
5. As an authenticated user, I want the app to silently refresh my JWT before it expires, so that I am not unexpectedly logged out mid-session.

---

## Acceptance Criteria

1. Navigating to `GET /` while unauthenticated redirects to `GET /login`.
2. `GET /register` renders a Blade form with fields: `name`, `email`, `password`, `password_confirmation`.
3. `POST /register` calls FastAPI `POST /api/v1/auth/register`, stores `{access_token, refresh_token, expires_at, user}` in the Laravel session, and redirects to `/dashboard` on success.
4. A registration validation error from the FastAPI 422 response is surfaced back to the Blade form beside the relevant field.
5. `GET /login` renders a Blade form with fields: `email`, `password`.
6. `POST /login` calls FastAPI `POST /api/v1/auth/login`; on success stores session data and redirects to `/dashboard`; on `401` from the API, flashes an error message and re-renders the login form.
7. `POST /logout` calls FastAPI `POST /api/v1/auth/logout` with the stored access token, clears all session data, and redirects to `/login`.
8. `GET /dashboard` is protected by the `auth` Laravel middleware; unauthenticated requests redirect to `/login`; authenticated requests render `dashboard.blade.php`.
9. `App\Services\ApiClient`:
   - Constructor accepts base URL and optional JWT (passed as `Authorization: Bearer` header when present).
   - Has methods: `get(string $path, array $query = [])`, `post(string $path, array $data = [])`, `patch(string $path, array $data = [])`, `delete(string $path)`.
   - Throws `App\Exceptions\ApiException` (wrapping the HTTP status and JSON body) on any non-2xx response.
10. `App\Http\Middleware\RefreshApiToken` runs on every authenticated request; if `session('expires_at') - now() < 300` seconds, it calls FastAPI `POST /api/v1/auth/refresh` and updates the session.
11. `config/api.php` holds `base_url` (from `BACKEND_API_BASE_URL`), `timeout` (from `BACKEND_API_TIMEOUT`, default `10`).
12. PHPUnit `AuthControllerTest` covers: register success, register duplicate email (409 flash), login success, login failure (401 flash), logout; all using `Http::fake()`.
13. `GET /health` returns `200 {"status": "ok", "service": "frontend"}`.
14. All Blade views extend a shared `layouts/app.blade.php` that includes a navigation bar with links to Dashboard, Calendar, and (when pending invitations exist) a bell icon.

---

## Laravel Routes

```php
// routes/web.php
Route::get('/', fn() => redirect('/dashboard'));

Route::get('/login',    [AuthController::class, 'showLogin'])->name('login');
Route::post('/login',   [AuthController::class, 'login']);
Route::get('/register', [AuthController::class, 'showRegister'])->name('register');
Route::post('/register',[AuthController::class, 'register']);
Route::post('/logout',  [AuthController::class, 'logout'])->name('logout')->middleware('auth');

Route::get('/dashboard', [DashboardController::class, 'index'])->name('dashboard')->middleware('auth');

Route::get('/health', [HealthController::class, 'index']);
```

---

## Key Files / Directories to Create

```
frontend/
├── app/
│   ├── Exceptions/
│   │   └── ApiException.php          # wraps HTTP status + JSON body
│   ├── Http/
│   │   ├── Controllers/
│   │   │   ├── AuthController.php
│   │   │   ├── DashboardController.php
│   │   │   └── HealthController.php
│   │   └── Middleware/
│   │       └── RefreshApiToken.php
│   └── Services/
│       └── ApiClient.php
├── config/
│   └── api.php
├── resources/
│   └── views/
│       ├── layouts/
│       │   └── app.blade.php         # base layout with nav + CSRF meta tag
│       ├── auth/
│       │   ├── login.blade.php
│       │   └── register.blade.php
│       └── dashboard.blade.php
├── routes/
│   └── web.php
└── tests/
    └── Feature/
        └── AuthControllerTest.php
```

---

## Session Data Contract

Laravel session stores the following keys after login:

| Key              | Type     | Description                                  |
|------------------|----------|----------------------------------------------|
| `api_token`      | `string` | FastAPI JWT access token                     |
| `refresh_token`  | `string` | FastAPI refresh token                        |
| `expires_at`     | `int`    | Unix timestamp when access token expires     |
| `user`           | `array`  | `{id, name, email, timezone}` from FastAPI   |

The `auth` middleware checks for the presence of `api_token` in the session.

---

## Dependencies

- Stage 01 (Laravel Docker container running, `BACKEND_API_BASE_URL` env var configured).
- Stage 02 (FastAPI auth endpoints live at `/api/v1/auth/*`).
