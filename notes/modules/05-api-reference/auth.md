# Auth API

> Source: `backend/app/gateway/routers/auth.py`
> Prefix: `/api/v1/auth`

Handles user authentication lifecycle: login, registration, logout, password change, setup, and OAuth stubs.

## Quick Reference

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `POST` | `/api/v1/auth/login/local` | Email/password login | `PUBLIC` |
| `POST` | `/api/v1/auth/register` | Register a new user account | `PUBLIC` |
| `POST` | `/api/v1/auth/logout` | Logout (clear session cookie) | `PUBLIC` |
| `POST` | `/api/v1/auth/change-password` | Change password for current user | `AUTH` |
| `GET` | `/api/v1/auth/me` | Get current authenticated user | `AUTH` |
| `GET` | `/api/v1/auth/setup-status` | Check if admin account exists | `PUBLIC` |
| `POST` | `/api/v1/auth/initialize` | Create first admin on initial setup | `PUBLIC` |
| `GET` | `/api/v1/auth/oauth/{provider}` | Initiate OAuth login (stub) | `PUBLIC` |
| `GET` | `/api/v1/auth/callback/{provider}` | OAuth callback (stub) | `PUBLIC` |

---

## Endpoint Details

### `POST /api/v1/auth/login/local`

Local email/password login. Sets an `access_token` HttpOnly cookie on success.

**Access:** `PUBLIC` — Rate-limited: 5 failures per IP trigger a 5-minute lockout. Multi-worker deployments multiply this limit per worker.

**Query Params:** None

**Request Body** (`application/x-www-form-urlencoded` — OAuth2PasswordRequestForm):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | User email address |
| `password` | string | Yes | Account password |

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Login successful; `access_token` HttpOnly cookie set |
| `401` | Invalid credentials (`INVALID_CREDENTIALS`) |
| `429` | IP rate-limited — too many failed attempts |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `expires_in` | integer | Cookie TTL in seconds (based on `auth.token_expiry_days`) |
| `needs_setup` | boolean | `true` if user hasn't completed first-boot setup |

**Example (200):**
```json
{
  "expires_in": 86400,
  "needs_setup": false
}
```

---

### `POST /api/v1/auth/register`

Register a new user account with role `user`. Auto-logs in by setting the session cookie.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `email` | string (email) | Yes | Valid email format | User email address |
| `password` | string | Yes | Min 8 chars; not in common-password blocklist | Account password |

**Responses:**

| Status | Description |
|--------|-------------|
| `201` | User created; `access_token` cookie set |
| `400` | Email already registered (`EMAIL_ALREADY_EXISTS`) |

**Response Schema (201):**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | User UUID |
| `email` | string | Registered email |
| `system_role` | string | Always `"user"` for this endpoint |

**Example (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "system_role": "user"
}
```

---

### `POST /api/v1/auth/logout`

Logout the current user by deleting the `access_token` cookie.

**Access:** `PUBLIC` (no JWT required; simply clears the cookie)

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Cookie cleared |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | `"Successfully logged out"` |

**Example (200):**
```json
{
  "message": "Successfully logged out"
}
```

---

### `POST /api/v1/auth/change-password`

Change password for the currently authenticated user. Also handles the first-boot setup flow (update email + clear `needs_setup`). Increments `token_version` to invalidate all existing sessions and re-issues a new cookie.

**Access:** `AUTH`

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `current_password` | string | Yes | — | Current account password |
| `new_password` | string | Yes | Min 8 chars; not in common blocklist | New password |
| `new_email` | string (email) | No | Valid email, unique | If provided, updates the email too. Required during setup flow to clear `needs_setup`. |

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Password changed; new `access_token` cookie set |
| `400` | Current password incorrect, or email already in use, or OAuth user |
| `401` | Not authenticated |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | `"Password changed successfully"` |

**Example (200):**
```json
{
  "message": "Password changed successfully"
}
```

---

### `GET /api/v1/auth/me`

Return the currently authenticated user's profile.

**Access:** `AUTH`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Authenticated user info |
| `401` | Not authenticated |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | User UUID |
| `email` | string | User email |
| `system_role` | string | `"admin"` or `"user"` |
| `needs_setup` | boolean | Whether first-boot setup is pending |

**Example (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "admin@example.com",
  "system_role": "admin",
  "needs_setup": false
}
```

---

### `GET /api/v1/auth/setup-status`

Check whether any admin account exists. Returns `needs_setup: true` when the system is uninitialized. Rate-limited to once per 60 seconds per IP.

**Access:** `PUBLIC` — Rate-limited: 1 request per IP per 60 seconds.

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Setup status returned |
| `429` | Rate-limited; `Retry-After` header included |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `needs_setup` | boolean | `true` if no admin account exists yet |

**Example (200):**
```json
{
  "needs_setup": true
}
```

---

### `POST /api/v1/auth/initialize`

Create the first admin account on initial system setup. Callable only once — returns `409 Conflict` if any admin already exists.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `email` | string (email) | Yes | Valid email | Admin email |
| `password` | string | Yes | Min 8 chars; not in common blocklist | Admin password |

**Responses:**

| Status | Description |
|--------|-------------|
| `201` | Admin created; `access_token` cookie set |
| `409` | System already initialized (`SYSTEM_ALREADY_INITIALIZED`) |

**Response Schema (201):**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Admin user UUID |
| `email` | string | Admin email |
| `system_role` | string | Always `"admin"` |

**Example (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "admin@example.com",
  "system_role": "admin"
}
```

---

### `GET /api/v1/auth/oauth/{provider}`

Initiate OAuth login flow. **Not yet implemented** — always returns `501`.

**Access:** `PUBLIC`

**Path Params:**

| Param | Values | Description |
|-------|--------|-------------|
| `provider` | `github`, `google` | OAuth provider name |

**Query Params:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `400` | Unsupported provider |
| `501` | Not implemented |

---

### `GET /api/v1/auth/callback/{provider}`

OAuth provider callback endpoint. **Not yet implemented** — always returns `501`.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `provider` | OAuth provider name |

**Query Params:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | string | Yes | Authorization code from provider |
| `state` | string | Yes | CSRF state token |

**Responses:**

| Status | Description |
|--------|-------------|
| `501` | Not implemented |
