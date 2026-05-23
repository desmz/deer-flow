# Memory API

> Source: `backend/app/gateway/routers/memory.py`
> Prefix: `/api`

Read, write, and manage the per-user persistent memory store. Memory data consists of structured context sections (work context, personal context, history) and discrete facts that are injected into the agent's system prompt on subsequent conversations.

## Quick Reference

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET` | `/api/memory` | Get current memory data | `PUBLIC` |
| `POST` | `/api/memory/reload` | Reload memory from storage file | `PUBLIC` |
| `DELETE` | `/api/memory` | Clear all memory data | `PUBLIC` |
| `GET` | `/api/memory/export` | Export memory as JSON | `PUBLIC` |
| `POST` | `/api/memory/import` | Import and overwrite memory data | `PUBLIC` |
| `POST` | `/api/memory/facts` | Create a single fact manually | `PUBLIC` |
| `DELETE` | `/api/memory/facts/{fact_id}` | Delete a specific fact | `PUBLIC` |
| `PATCH` | `/api/memory/facts/{fact_id}` | Partially update a specific fact | `PUBLIC` |
| `GET` | `/api/memory/config` | Get memory system configuration | `PUBLIC` |
| `GET` | `/api/memory/status` | Get config + current data in one request | `PUBLIC` |

> All memory endpoints operate on the **current effective user's** memory (resolved via `get_effective_user_id()`). When `auth.enabled: false`, this is always `"default"`.

---

## Shared Response Schemas

### `MemoryResponse`

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Memory schema version (e.g., `"1.0"`) |
| `lastUpdated` | string | ISO timestamp of last update |
| `user` | object | User context sections |
| `user.workContext` | object | `{ summary, updatedAt }` |
| `user.personalContext` | object | `{ summary, updatedAt }` |
| `user.topOfMind` | object | `{ summary, updatedAt }` |
| `history` | object | Historical context sections |
| `history.recentMonths` | object | `{ summary, updatedAt }` |
| `history.earlierContext` | object | `{ summary, updatedAt }` |
| `history.longTermBackground` | object | `{ summary, updatedAt }` |
| `facts` | array | List of discrete facts |
| `facts[].id` | string | Unique fact ID |
| `facts[].content` | string | Fact text |
| `facts[].category` | string | `"preference"` \| `"knowledge"` \| `"context"` \| `"behavior"` \| `"goal"` |
| `facts[].confidence` | float | Confidence score 0.0–1.0 |
| `facts[].createdAt` | string | ISO creation timestamp |
| `facts[].source` | string | Source thread ID |
| `facts[].sourceError` | string \| null | Description of a prior mistake this fact corrects |

---

## Endpoint Details

### `GET /api/memory`

Retrieve the current global memory data.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Memory data returned |

**Response Schema (200):** `MemoryResponse` (see above).

**Example (200):**
```json
{
  "version": "1.0",
  "lastUpdated": "2024-01-15T10:30:00Z",
  "user": {
    "workContext": {"summary": "Working on DeerFlow project", "updatedAt": "2024-01-15T10:00:00Z"},
    "personalContext": {"summary": "Prefers concise responses", "updatedAt": ""},
    "topOfMind": {"summary": "", "updatedAt": ""}
  },
  "history": {
    "recentMonths": {"summary": "", "updatedAt": ""},
    "earlierContext": {"summary": "", "updatedAt": ""},
    "longTermBackground": {"summary": "", "updatedAt": ""}
  },
  "facts": [
    {
      "id": "fact_abc123",
      "content": "User prefers TypeScript over JavaScript",
      "category": "preference",
      "confidence": 0.9,
      "createdAt": "2024-01-15T10:30:00Z",
      "source": "thread_xyz",
      "sourceError": null
    }
  ]
}
```

---

### `POST /api/memory/reload`

Force-reload memory data from the storage file, refreshing the in-memory cache. Useful when the file has been modified externally.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Reloaded memory data |

**Response Schema (200):** `MemoryResponse`.

---

### `DELETE /api/memory`

Delete all persisted memory data and reset the memory structure to an empty state.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Empty memory structure returned |
| `500` | Failed to clear memory data (filesystem error) |

**Response Schema (200):** `MemoryResponse` (all sections empty).

---

### `GET /api/memory/export`

Export the current memory data as JSON. Functionally identical to `GET /api/memory` — intended for backup/transfer workflows.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Memory data for export |

**Response Schema (200):** `MemoryResponse`.

---

### `POST /api/memory/import`

Import and overwrite the current memory data from a JSON payload. Completely replaces existing data.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body** (`application/json`): Full `MemoryResponse` object (same schema as `GET /api/memory` response).

**Example Request:**
```json
{
  "version": "1.0",
  "lastUpdated": "2024-01-15T10:30:00Z",
  "user": {
    "workContext": {"summary": "Working on DeerFlow", "updatedAt": "2024-01-15T10:00:00Z"},
    "personalContext": {"summary": "", "updatedAt": ""},
    "topOfMind": {"summary": "", "updatedAt": ""}
  },
  "history": {
    "recentMonths": {"summary": "", "updatedAt": ""},
    "earlierContext": {"summary": "", "updatedAt": ""},
    "longTermBackground": {"summary": "", "updatedAt": ""}
  },
  "facts": []
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Memory imported successfully |
| `500` | Failed to write memory data |

**Response Schema (200):** `MemoryResponse` (the imported data).

---

### `POST /api/memory/facts`

Create a single memory fact manually.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `content` | string | Yes | Min length 1 | Fact text |
| `category` | string | No | Default: `"context"` | Fact category (`preference`, `knowledge`, `context`, `behavior`, `goal`) |
| `confidence` | float | No | 0.0–1.0, default `0.5` | Confidence score |

**Example Request:**
```json
{
  "content": "User prefers dark mode for all interfaces",
  "category": "preference",
  "confidence": 0.95
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Updated memory data with new fact |
| `400` | Empty content or invalid confidence value |
| `500` | Failed to save fact |

**Response Schema (200):** `MemoryResponse` (full data including the new fact).

---

### `DELETE /api/memory/facts/{fact_id}`

Delete a single memory fact by its ID.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `fact_id` | Fact ID (e.g., `"fact_abc123"`) |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Updated memory data with fact removed |
| `404` | Fact not found |
| `500` | Failed to delete fact |

**Response Schema (200):** `MemoryResponse`.

---

### `PATCH /api/memory/facts/{fact_id}`

Partially update a memory fact. Only provided fields are updated; omitted fields are preserved.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `fact_id` | Fact ID to update |

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `content` | string \| null | No | Min length 1 | New fact text |
| `category` | string \| null | No | — | New category |
| `confidence` | float \| null | No | 0.0–1.0 | New confidence score |

**Example Request:**
```json
{
  "confidence": 0.75
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Updated memory data |
| `400` | Invalid content (empty) or invalid confidence value |
| `404` | Fact not found |
| `500` | Failed to update fact |

**Response Schema (200):** `MemoryResponse`.

---

### `GET /api/memory/config`

Retrieve the current memory system configuration from `config.yaml`.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Memory configuration |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Whether memory system is active |
| `storage_path` | string | Path to `memory.json` storage file |
| `debounce_seconds` | integer | Wait time before processing updates (default: 30s) |
| `max_facts` | integer | Maximum number of facts to store (default: 100) |
| `fact_confidence_threshold` | float | Minimum confidence for fact retention (default: 0.7) |
| `injection_enabled` | boolean | Whether memory is injected into agent prompts |
| `max_injection_tokens` | integer | Token limit for memory prompt injection (default: 2000) |

**Example (200):**
```json
{
  "enabled": true,
  "storage_path": ".deer-flow/users/default/memory.json",
  "debounce_seconds": 30,
  "max_facts": 100,
  "fact_confidence_threshold": 0.7,
  "injection_enabled": true,
  "max_injection_tokens": 2000
}
```

---

### `GET /api/memory/status`

Retrieve both memory configuration and current data in a single request.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Combined config and data |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `config` | object | `MemoryConfigResponse` (see `GET /api/memory/config`) |
| `data` | object | `MemoryResponse` (see `GET /api/memory`) |
