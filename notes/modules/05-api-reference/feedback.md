# Feedback API

> Source: `backend/app/gateway/routers/feedback.py`
> Prefix: `/api/threads`

Submit and manage thumbs-up/thumbs-down feedback on agent runs. Feedback is scoped to a `(thread_id, run_id)` pair and optionally to a specific message within the run.

## Quick Reference

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `PUT` | `/api/threads/{thread_id}/runs/{run_id}/feedback` | Create or update feedback (idempotent) | `AUTH+OWNER` |
| `POST` | `/api/threads/{thread_id}/runs/{run_id}/feedback` | Create feedback (new record) | `AUTH+OWNER` |
| `GET` | `/api/threads/{thread_id}/runs/{run_id}/feedback` | List all feedback for a run | `AUTH+OWNER` |
| `GET` | `/api/threads/{thread_id}/runs/{run_id}/feedback/stats` | Get aggregated feedback stats | `AUTH+OWNER` |
| `DELETE` | `/api/threads/{thread_id}/runs/{run_id}/feedback` | Delete the current user's feedback for a run | `AUTH+OWNER` |
| `DELETE` | `/api/threads/{thread_id}/runs/{run_id}/feedback/{feedback_id}` | Delete a specific feedback record | `AUTH+OWNER` |

---

## Shared Response Schema

### `FeedbackResponse`

| Field | Type | Description |
|-------|------|-------------|
| `feedback_id` | string | Unique feedback record ID |
| `run_id` | string | Run ID this feedback is for |
| `thread_id` | string | Thread ID |
| `user_id` | string \| null | User who submitted the feedback |
| `message_id` | string \| null | Optional: specific message the feedback targets |
| `rating` | integer | `1` (positive / thumbs-up) or `-1` (negative / thumbs-down) |
| `comment` | string \| null | Optional text comment |
| `created_at` | string | ISO creation timestamp |

---

## Endpoint Details

### `PUT /api/threads/{thread_id}/runs/{run_id}/feedback`

Create or update (upsert) feedback for a run. Idempotent — calling again overwrites the existing record for this user.

**Access:** `AUTH+OWNER` (`require_existing=True`)

**Path Params:**

| Param | Description |
|-------|-------------|
| `thread_id` | Thread UUID |
| `run_id` | Run UUID |

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `rating` | integer | Yes | `1` or `-1` | Positive or negative feedback |
| `comment` | string \| null | No | — | Optional text comment |

**Example Request:**
```json
{
  "rating": 1,
  "comment": "Very helpful answer!"
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Feedback upserted |
| `400` | Invalid rating value |
| `401` | Not authenticated |
| `404` | Thread or run not found / not owned |

**Response Schema (200):** `FeedbackResponse`.

---

### `POST /api/threads/{thread_id}/runs/{run_id}/feedback`

Submit new feedback for a run. Creates a separate record (does not upsert). Allows scoping feedback to a specific message.

**Access:** `AUTH+OWNER` (`require_existing=True`)

**Path Params:**

| Param | Description |
|-------|-------------|
| `thread_id` | Thread UUID |
| `run_id` | Run UUID |

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `rating` | integer | Yes | `1` or `-1` | Positive or negative feedback |
| `comment` | string \| null | No | — | Optional text comment |
| `message_id` | string \| null | No | — | Scope feedback to a specific message ID |

**Example Request:**
```json
{
  "rating": -1,
  "comment": "The answer was incomplete.",
  "message_id": "msg_abc123"
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Feedback created |
| `400` | Invalid rating value |
| `401` | Not authenticated |
| `404` | Thread or run not found / not owned |

**Response Schema (200):** `FeedbackResponse`.

**Example (200):**
```json
{
  "feedback_id": "fb_xyz789",
  "run_id": "run_abc123",
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_001",
  "message_id": "msg_abc123",
  "rating": -1,
  "comment": "The answer was incomplete.",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### `GET /api/threads/{thread_id}/runs/{run_id}/feedback`

List all feedback records for a specific run.

**Access:** `AUTH+OWNER`

**Path Params:**

| Param | Description |
|-------|-------------|
| `thread_id` | Thread UUID |
| `run_id` | Run UUID |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Array of feedback records |
| `401` | Not authenticated |
| `404` | Thread not found or not owned |

**Response Schema (200):** Array of `FeedbackResponse`.

---

### `GET /api/threads/{thread_id}/runs/{run_id}/feedback/stats`

Get aggregated feedback statistics for a run: total, positive, and negative counts.

**Access:** `AUTH+OWNER`

**Path Params:**

| Param | Description |
|-------|-------------|
| `thread_id` | Thread UUID |
| `run_id` | Run UUID |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Aggregated stats |
| `401` | Not authenticated |
| `404` | Thread not found or not owned |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Run UUID |
| `total` | integer | Total number of feedback records |
| `positive` | integer | Count of `rating = 1` records |
| `negative` | integer | Count of `rating = -1` records |

**Example (200):**
```json
{
  "run_id": "run_abc123",
  "total": 3,
  "positive": 2,
  "negative": 1
}
```

---

### `DELETE /api/threads/{thread_id}/runs/{run_id}/feedback`

Delete the current user's feedback for a run (any record they submitted, regardless of `feedback_id`).

**Access:** `AUTH+OWNER` (`require_existing=True`)

**Path Params:**

| Param | Description |
|-------|-------------|
| `thread_id` | Thread UUID |
| `run_id` | Run UUID |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Feedback deleted |
| `401` | Not authenticated |
| `404` | No feedback found for this run |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Always `true` |

---

### `DELETE /api/threads/{thread_id}/runs/{run_id}/feedback/{feedback_id}`

Delete a specific feedback record by ID. Verifies the record belongs to the specified thread and run before deletion.

**Access:** `AUTH+OWNER` (`require_existing=True`)

**Path Params:**

| Param | Description |
|-------|-------------|
| `thread_id` | Thread UUID |
| `run_id` | Run UUID |
| `feedback_id` | Feedback record UUID |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Feedback deleted |
| `401` | Not authenticated |
| `404` | Feedback not found or doesn't belong to this thread/run |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Always `true` |
