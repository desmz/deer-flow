# Agents & User Profile API

> Source: `backend/app/gateway/routers/agents.py`
> Prefix: `/api`

CRUD management for custom agents (per-user isolated) and the global USER.md profile that is injected into all agents.

**Important:** All endpoints in this file are protected by the `agents_api.enabled` feature gate. If `agents_api.enabled: false` in `config.yaml`, every endpoint returns `403 Forbidden`, regardless of authentication status.

## Quick Reference

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET` | `/api/agents` | List all custom agents | `FEATURE` |
| `GET` | `/api/agents/check` | Validate agent name availability | `FEATURE` |
| `GET` | `/api/agents/{name}` | Get a specific agent | `FEATURE` |
| `POST` | `/api/agents` | Create a new custom agent | `FEATURE` |
| `PUT` | `/api/agents/{name}` | Update an existing agent | `FEATURE` |
| `DELETE` | `/api/agents/{name}` | Delete a custom agent | `FEATURE` |
| `GET` | `/api/user-profile` | Get the global USER.md content | `FEATURE` |
| `PUT` | `/api/user-profile` | Update the global USER.md content | `FEATURE` |

> `FEATURE` = No user authentication required, but `agents_api.enabled: true` must be set in `config.yaml`.

---

## Endpoint Details

### `GET /api/agents`

List all custom agents available for the current user, including each agent's SOUL.md content.

**Access:** `FEATURE`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | List of agents returned |
| `403` | `agents_api` feature is disabled |
| `500` | Failed to load agents |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `agents` | array | List of `AgentResponse` objects |
| `agents[].name` | string | Agent name (hyphen-case, lowercase) |
| `agents[].description` | string | Agent description |
| `agents[].model` | string \| null | Optional model override |
| `agents[].tool_groups` | array \| null | Whitelisted tool group names |
| `agents[].skills` | array \| null | Whitelisted skill names (`null` = all, `[]` = none) |
| `agents[].soul` | string \| null | SOUL.md content |

**Example (200):**
```json
{
  "agents": [
    {
      "name": "my-researcher",
      "description": "Focused research agent",
      "model": "claude-3-opus",
      "tool_groups": null,
      "skills": null,
      "soul": "You are a focused research assistant..."
    }
  ]
}
```

---

### `GET /api/agents/check`

Validate an agent name and check whether it is available (case-insensitive).

**Access:** `FEATURE`

**Query Params:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Agent name to check. Must match `^[A-Za-z0-9-]+$`. |

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Name check result |
| `403` | `agents_api` feature is disabled |
| `422` | Name does not match the allowed pattern |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `available` | boolean | `true` if the name is not yet taken |
| `name` | string | Normalized (lowercased) name |

**Example (200):**
```json
{
  "available": true,
  "name": "my-researcher"
}
```

---

### `GET /api/agents/{name}`

Retrieve details and SOUL.md content for a specific custom agent.

**Access:** `FEATURE`

**Path Params:**

| Param | Description |
|-------|-------------|
| `name` | Agent name (case-insensitive; normalized to lowercase internally) |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Agent details returned |
| `403` | `agents_api` feature is disabled |
| `404` | Agent not found |
| `422` | Invalid agent name format |
| `500` | Failed to load agent |

**Response Schema (200):** Same as `agents[]` element in `GET /api/agents`.

**Example (200):**
```json
{
  "name": "my-researcher",
  "description": "Focused research agent",
  "model": null,
  "tool_groups": null,
  "skills": null,
  "soul": "You are a focused research assistant..."
}
```

---

### `POST /api/agents`

Create a new custom agent with a `config.yaml` and `SOUL.md` stored in the per-user agent directory.

**Access:** `FEATURE`

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `name` | string | Yes | `^[A-Za-z0-9-]+$`; stored as lowercase | Agent identifier |
| `description` | string | No | — | Human-readable description |
| `model` | string \| null | No | — | Model override (e.g., `"claude-3-opus"`) |
| `tool_groups` | array \| null | No | — | Whitelisted tool group names |
| `skills` | array \| null | No | `null` = all enabled skills; `[]` = no skills | Skill whitelist |
| `soul` | string | No | — | SOUL.md content — personality and behavioral guardrails |

**Example Request:**
```json
{
  "name": "my-researcher",
  "description": "Focused research agent",
  "soul": "You are a focused research assistant. Always cite sources."
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `201` | Agent created |
| `403` | `agents_api` feature is disabled |
| `409` | Agent name already exists |
| `422` | Invalid agent name format |
| `500` | Failed to create agent (partial writes cleaned up) |

**Response Schema (201):** Same as `AgentResponse` (see `GET /api/agents/{name}`).

---

### `PUT /api/agents/{name}`

Update an existing custom agent's config and/or SOUL.md. All fields are optional; omitted fields are preserved.

**Access:** `FEATURE`

**Path Params:**

| Param | Description |
|-------|-------------|
| `name` | Agent name to update |

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string \| null | No | New description |
| `model` | string \| null | No | New model override |
| `tool_groups` | array \| null | No | New tool group whitelist |
| `skills` | array \| null | No | New skill whitelist (`null` = all, `[]` = none) |
| `soul` | string \| null | No | New SOUL.md content |

**Example Request:**
```json
{
  "soul": "Updated personality instructions..."
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Agent updated |
| `403` | `agents_api` disabled, or agent is in legacy shared layout (run migration script) |
| `404` | Agent not found |
| `409` | Agent only exists in legacy shared layout |
| `422` | Invalid agent name format |
| `500` | Failed to update agent |

**Response Schema (200):** Same as `AgentResponse`.

---

### `DELETE /api/agents/{name}`

Delete a custom agent and all its files (config, SOUL.md, memory).

**Access:** `FEATURE`

**Path Params:**

| Param | Description |
|-------|-------------|
| `name` | Agent name to delete |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `204` | Agent deleted |
| `403` | `agents_api` disabled |
| `404` | Agent not found |
| `409` | Agent only exists in legacy shared layout — run migration script first |
| `422` | Invalid agent name format |
| `500` | Failed to delete agent |

---

### `GET /api/user-profile`

Read the global `USER.md` file that is injected into all custom agents as user context.

**Access:** `FEATURE`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | User profile content returned |
| `403` | `agents_api` feature is disabled |
| `500` | Failed to read profile |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `content` | string \| null | USER.md text, or `null` if it has not been created yet |

**Example (200):**
```json
{
  "content": "I am a software engineer who prefers concise, direct answers..."
}
```

---

### `PUT /api/user-profile`

Create or overwrite the global `USER.md` file.

**Access:** `FEATURE`

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | New USER.md content (empty string allowed to clear) |

**Example Request:**
```json
{
  "content": "I am a software engineer who prefers concise, direct answers..."
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | User profile saved |
| `403` | `agents_api` feature is disabled |
| `500` | Failed to write profile |

**Response Schema (200):** Same as `GET /api/user-profile`.
