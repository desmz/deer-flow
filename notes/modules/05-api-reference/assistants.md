# Assistants Compatibility API

> Source: `backend/app/gateway/routers/assistants_compat.py`
> Prefix: `/api/assistants`

Provides a minimal LangGraph Platform-compatible assistants API. This is a **stub implementation** — it satisfies the `useStream` React hook's initialization requirements (`assistants.search()` and `assistants.get()`) without a real assistants backend. Custom agents from `config.yaml` are surfaced here alongside the default `lead_agent`.

## Quick Reference

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `POST` | `/api/assistants/search` | Search/list assistants | `PUBLIC` |
| `GET` | `/api/assistants/{assistant_id}` | Get an assistant by ID | `PUBLIC` |
| `GET` | `/api/assistants/{assistant_id}/graph` | Get the graph structure | `PUBLIC` |
| `GET` | `/api/assistants/{assistant_id}/schemas` | Get assistant JSON schemas | `PUBLIC` |

---

## Endpoint Details

### `POST /api/assistants/search`

Search and list available assistants. Returns `lead_agent` plus all custom agents.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body** (`application/json`, optional):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `graph_id` | string \| null | No | Filter by graph ID |
| `name` | string \| null | No | Filter by name (substring, case-insensitive) |
| `metadata` | object \| null | No | Metadata filter (not currently used) |
| `limit` | integer | No | Max results (default: `10`) |
| `offset` | integer | No | Pagination offset (default: `0`) |

**Example Request:**
```json
{
  "graph_id": "lead_agent",
  "limit": 20
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | List of matching assistants |

**Response Schema (200):** Array of `AssistantResponse`:

| Field | Type | Description |
|-------|------|-------------|
| `assistant_id` | string | Unique assistant identifier |
| `graph_id` | string | Always `"lead_agent"` (all assistants share one graph) |
| `name` | string | Display name |
| `config` | object | Always `{}` (stub) |
| `metadata` | object | `{"created_by": "system"}` or `{"created_by": "user"}` |
| `description` | string \| null | Human-readable description |
| `created_at` | string | ISO timestamp |
| `updated_at` | string | ISO timestamp |
| `version` | integer | Always `1` |

**Example (200):**
```json
[
  {
    "assistant_id": "lead_agent",
    "graph_id": "lead_agent",
    "name": "lead_agent",
    "config": {},
    "metadata": {"created_by": "system"},
    "description": "DeerFlow lead agent",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "version": 1
  }
]
```

---

### `GET /api/assistants/{assistant_id}`

Get a specific assistant by its ID.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `assistant_id` | Assistant identifier (e.g., `"lead_agent"` or a custom agent name) |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Assistant returned |
| `404` | Assistant not found |

**Response Schema (200):** Same as a single element in `POST /api/assistants/search`.

---

### `GET /api/assistants/{assistant_id}/graph`

Get the graph structure for an assistant. Returns a minimal stub — full graph introspection is not supported in the Gateway.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `assistant_id` | Assistant identifier |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Minimal graph description |
| `404` | Assistant not found |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `graph_id` | string | Always `"lead_agent"` |
| `nodes` | array | Always `[]` (stub) |
| `edges` | array | Always `[]` (stub) |

**Example (200):**
```json
{
  "graph_id": "lead_agent",
  "nodes": [],
  "edges": []
}
```

---

### `GET /api/assistants/{assistant_id}/schemas`

Get JSON schemas for an assistant's input, output, and state. Returns empty schemas — full introspection is not supported in the Gateway.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `assistant_id` | Assistant identifier |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Schema stub returned |
| `404` | Assistant not found |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `graph_id` | string | Always `"lead_agent"` |
| `input_schema` | object | Always `{}` |
| `output_schema` | object | Always `{}` |
| `state_schema` | object | Always `{}` |
| `config_schema` | object | Always `{}` |

**Example (200):**
```json
{
  "graph_id": "lead_agent",
  "input_schema": {},
  "output_schema": {},
  "state_schema": {},
  "config_schema": {}
}
```
