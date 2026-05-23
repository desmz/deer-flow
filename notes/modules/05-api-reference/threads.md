# Threads API

> Source: `backend/app/gateway/routers/threads.py`
> Prefix: `/api/threads`

Thread lifecycle management: create, search, read, patch, delete, and state/checkpoint operations. Implements the LangGraph Platform thread API surface so the `useStream` React hook works without modification.

## Quick Reference

| Method   | Path                               | Description                                          | Access       |
| -------- | ---------------------------------- | ---------------------------------------------------- | ------------ |
| `POST`   | `/api/threads`                     | Create a new thread                                  | `PUBLIC`     |
| `POST`   | `/api/threads/search`              | Search and list threads                              | `PUBLIC`     |
| `GET`    | `/api/threads/{thread_id}`         | Get thread info                                      | `AUTH+OWNER` |
| `PATCH`  | `/api/threads/{thread_id}`         | Merge metadata into a thread                         | `AUTH+OWNER` |
| `DELETE` | `/api/threads/{thread_id}`         | Delete thread data (filesystem + checkpoints + meta) | `AUTH+OWNER` |
| `GET`    | `/api/threads/{thread_id}/state`   | Get latest thread state snapshot                     | `AUTH+OWNER` |
| `POST`   | `/api/threads/{thread_id}/state`   | Update thread state (human-in-the-loop)              | `AUTH+OWNER` |
| `POST`   | `/api/threads/{thread_id}/history` | Get checkpoint history                               | `AUTH+OWNER` |

---

## Endpoint Details

### `POST /api/threads`

Create a new thread. Writes a `thread_meta` record and an empty checkpoint so state endpoints work immediately. Idempotent — returns the existing record when `thread_id` already exists.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body** (`application/json`):

| Field          | Type           | Required | Description                                                                    |
| -------------- | -------------- | -------- | ------------------------------------------------------------------------------ |
| `thread_id`    | string \| null | No       | Custom thread ID (UUID auto-generated if omitted)                              |
| `assistant_id` | string \| null | No       | Associate thread with an assistant                                             |
| `metadata`     | object         | No       | Initial metadata (keys `owner_id`, `user_id` are stripped — server-controlled) |

**Example Request:**

```json
{
  "metadata": {
    "source": "web-ui"
  }
}
```

**Responses:**

| Status | Description                                                |
| ------ | ---------------------------------------------------------- |
| `200`  | Thread created (or existing thread returned if idempotent) |
| `500`  | Failed to create thread                                    |

**Response Schema (200):**

| Field        | Type   | Description                                          |
| ------------ | ------ | ---------------------------------------------------- |
| `thread_id`  | string | Thread UUID                                          |
| `status`     | string | `"idle"` \| `"busy"` \| `"interrupted"` \| `"error"` |
| `created_at` | string | ISO timestamp                                        |
| `updated_at` | string | ISO timestamp                                        |
| `metadata`   | object | Thread metadata                                      |
| `values`     | object | Current channel values (empty on new thread)         |
| `interrupts` | object | Pending interrupt payloads                           |

**Example (200):**

```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "idle",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "metadata": {},
  "values": {},
  "interrupts": {}
}
```

---

### `POST /api/threads/search`

Search and list threads. Delegates to the configured `ThreadMetaStore` (SQL or memory-backed).

**Access:** `PUBLIC`

**Query Params:** None

**Request Body** (`application/json`):

| Field      | Type           | Required | Constraints                                                 | Description                      |
| ---------- | -------------- | -------- | ----------------------------------------------------------- | -------------------------------- |
| `metadata` | object         | No       | Keys must be alphanumeric/underscore; values must be scalar | Filter by metadata (exact match) |
| `limit`    | integer        | No       | 1–1000, default `100`                                       | Max results                      |
| `offset`   | integer        | No       | ≥0, default `0`                                             | Pagination offset                |
| `status`   | string \| null | No       | —                                                           | Filter by thread status          |

**Example Request:**

```json
{
  "metadata": { "source": "web-ui" },
  "limit": 20,
  "offset": 0
}
```

**Responses:**

| Status | Description              |
| ------ | ------------------------ |
| `200`  | List of matching threads |
| `400`  | Invalid metadata filter  |

**Response Schema (200):** Array of `ThreadResponse` (same schema as `POST /api/threads` response).

---

### `GET /api/threads/{thread_id}`

Get thread info. Reads metadata from `ThreadMetaStore` and derives accurate execution status from the checkpointer.

**Access:** `AUTH+OWNER`

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description                             |
| ------ | --------------------------------------- |
| `200`  | Thread info returned                    |
| `401`  | Not authenticated                       |
| `404`  | Thread not found or not owned by caller |
| `500`  | Failed to get checkpoint                |

**Response Schema (200):** Same as `POST /api/threads` response (with populated `values`).

---

### `PATCH /api/threads/{thread_id}`

Merge additional metadata into a thread record.

**Access:** `AUTH+OWNER` (`require_existing=True` — thread must exist)

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |

**Query Params:** None

**Request Body** (`application/json`):

| Field      | Type   | Required | Description                                                             |
| ---------- | ------ | -------- | ----------------------------------------------------------------------- |
| `metadata` | object | Yes      | Metadata key-value pairs to merge (keys `owner_id`, `user_id` stripped) |

**Example Request:**

```json
{
  "metadata": {
    "label": "research-session"
  }
}
```

**Responses:**

| Status | Description                          |
| ------ | ------------------------------------ |
| `200`  | Thread returned with merged metadata |
| `401`  | Not authenticated                    |
| `404`  | Thread not found or not owned        |
| `500`  | Failed to update thread              |

---

### `DELETE /api/threads/{thread_id}`

Delete all local filesystem data for a thread, remove checkpoints (best-effort), and remove the `thread_meta` row.

**Access:** `AUTH+OWNER` (`require_existing=True`)

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description                                      |
| ------ | ------------------------------------------------ |
| `200`  | Thread data deleted                              |
| `401`  | Not authenticated                                |
| `404`  | Thread not found or not owned                    |
| `422`  | Invalid thread ID (e.g., path traversal attempt) |
| `500`  | Failed to delete thread data                     |

**Response Schema (200):**

| Field     | Type    | Description                     |
| --------- | ------- | ------------------------------- |
| `success` | boolean | `true` on success               |
| `message` | string  | Description of what was deleted |

**Example (200):**

```json
{
  "success": true,
  "message": "Deleted local thread data for 550e8400-e29b-41d4-a716-446655440000"
}
```

---

### `GET /api/threads/{thread_id}/state`

Get the latest state snapshot for a thread. Channel values are serialized to JSON-safe dicts (LangChain message objects are converted to match LangGraph Platform wire format).

**Access:** `AUTH+OWNER`

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description                   |
| ------ | ----------------------------- |
| `200`  | Thread state snapshot         |
| `401`  | Not authenticated             |
| `404`  | Thread not found or not owned |
| `500`  | Failed to get checkpoint      |

**Response Schema (200):**

| Field                  | Type           | Description                                                 |
| ---------------------- | -------------- | ----------------------------------------------------------- |
| `values`               | object         | Current channel values (includes `messages`, `title`, etc.) |
| `next`                 | array          | Names of next tasks to execute                              |
| `metadata`             | object         | Checkpoint metadata                                         |
| `checkpoint`           | object         | `{ id, ts }` — checkpoint ID and timestamp                  |
| `checkpoint_id`        | string \| null | Current checkpoint ID                                       |
| `parent_checkpoint_id` | string \| null | Parent checkpoint ID                                        |
| `created_at`           | string \| null | Checkpoint timestamp                                        |
| `tasks`                | array          | Interrupted task details (`[{ id, name }]`)                 |

**Example (200):**

```json
{
  "values": {
    "messages": [...],
    "title": "Research session"
  },
  "next": [],
  "metadata": {"step": 5, "source": "loop"},
  "checkpoint": {"id": "abc123", "ts": "2024-01-15T10:30:00Z"},
  "checkpoint_id": "abc123",
  "parent_checkpoint_id": "abc122",
  "created_at": "2024-01-15T10:30:00Z",
  "tasks": []
}
```

---

### `POST /api/threads/{thread_id}/state`

Update thread state — used for human-in-the-loop resume or title rename. Writes a new checkpoint merging provided values into the current channel values.

**Access:** `AUTH+OWNER` (`require_existing=True`)

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |

**Query Params:** None

**Request Body** (`application/json`):

| Field           | Type           | Required | Description                                                        |
| --------------- | -------------- | -------- | ------------------------------------------------------------------ |
| `values`        | object \| null | No       | Channel values to merge into current state                         |
| `checkpoint_id` | string \| null | No       | Branch from a specific checkpoint (latest if omitted)              |
| `checkpoint`    | object \| null | No       | Full checkpoint object (alternative to `checkpoint_id`)            |
| `as_node`       | string \| null | No       | Node identity — when set, marks the update as from a specific node |

**Example Request (resume with clarification answer):**

```json
{
  "values": {
    "messages": [{ "role": "human", "content": "Yes, proceed with the analysis." }]
  },
  "as_node": "agent"
}
```

**Responses:**

| Status | Description                           |
| ------ | ------------------------------------- |
| `200`  | State updated; new checkpoint created |
| `401`  | Not authenticated                     |
| `404`  | Thread not found or not owned         |
| `500`  | Failed to get or write state          |

**Response Schema (200):** Same as `GET /api/threads/{thread_id}/state`.

---

### `POST /api/threads/{thread_id}/history`

Get checkpoint history for a thread. Only the latest entry carries the `messages` key.

**Access:** `AUTH+OWNER`

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |

**Query Params:** None

**Request Body** (`application/json`):

| Field    | Type           | Required | Constraints         | Description                                       |
| -------- | -------------- | -------- | ------------------- | ------------------------------------------------- |
| `limit`  | integer        | No       | 1–100, default `10` | Maximum entries to return                         |
| `before` | string \| null | No       | —                   | Pagination cursor — checkpoint ID to start before |

**Example Request:**

```json
{
  "limit": 5
}
```

**Responses:**

| Status | Description                                |
| ------ | ------------------------------------------ |
| `200`  | Checkpoint history returned (newest first) |
| `401`  | Not authenticated                          |
| `404`  | Thread not found or not owned              |
| `500`  | Failed to read history                     |

**Response Schema (200):** Array of `HistoryEntry`:

| Field                  | Type           | Description                                                       |
| ---------------------- | -------------- | ----------------------------------------------------------------- |
| `checkpoint_id`        | string         | Checkpoint UUID                                                   |
| `parent_checkpoint_id` | string \| null | Parent checkpoint UUID                                            |
| `metadata`             | object         | Checkpoint metadata (step, source, etc.)                          |
| `values`               | object         | Channel values at this checkpoint (messages only in latest entry) |
| `created_at`           | string \| null | ISO timestamp                                                     |
| `next`                 | array          | Next tasks at this checkpoint                                     |

**Example (200):**

```json
[
  {
    "checkpoint_id": "abc123",
    "parent_checkpoint_id": "abc122",
    "metadata": {"step": 5},
    "values": {"title": "Research session", "messages": [...]},
    "created_at": "2024-01-15T10:30:00Z",
    "next": []
  }
]
```
