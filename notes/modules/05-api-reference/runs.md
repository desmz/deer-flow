# Runs API

> Source:
>
> - Thread-scoped runs: `backend/app/gateway/routers/thread_runs.py` (prefix `/api/threads`)
> - Stateless runs: `backend/app/gateway/routers/runs.py` (prefix `/api/runs`)

Create, stream, monitor, and cancel agent runs. The thread-scoped endpoints require a pre-existing thread and enforce ownership. The stateless endpoints auto-create a temporary thread when no `thread_id` is provided.

## Quick Reference

### Thread-Scoped Runs (`/api/threads/{thread_id}/runs`)

| Method      | Path                                              | Description                            | Access       |
| ----------- | ------------------------------------------------- | -------------------------------------- | ------------ |
| `POST`      | `/api/threads/{thread_id}/runs`                   | Create a background run                | `AUTH+OWNER` |
| `POST`      | `/api/threads/{thread_id}/runs/stream`            | Create a run + stream events via SSE   | `AUTH+OWNER` |
| `POST`      | `/api/threads/{thread_id}/runs/wait`              | Create a run + block until complete    | `AUTH+OWNER` |
| `GET`       | `/api/threads/{thread_id}/runs`                   | List all runs for a thread             | `AUTH+OWNER` |
| `GET`       | `/api/threads/{thread_id}/runs/{run_id}`          | Get details of a specific run          | `AUTH+OWNER` |
| `POST`      | `/api/threads/{thread_id}/runs/{run_id}/cancel`   | Cancel a running or pending run        | `AUTH+OWNER` |
| `GET`       | `/api/threads/{thread_id}/runs/{run_id}/join`     | Join an existing run's SSE stream      | `AUTH+OWNER` |
| `GET\|POST` | `/api/threads/{thread_id}/runs/{run_id}/stream`   | Join or cancel-then-stream a run       | `AUTH+OWNER` |
| `GET`       | `/api/threads/{thread_id}/messages`               | List displayable messages for a thread | `AUTH+OWNER` |
| `GET`       | `/api/threads/{thread_id}/runs/{run_id}/messages` | List paginated messages for a run      | `AUTH+OWNER` |
| `GET`       | `/api/threads/{thread_id}/runs/{run_id}/events`   | Get full event stream for a run        | `AUTH+OWNER` |
| `GET`       | `/api/threads/{thread_id}/token-usage`            | Get thread-level token usage           | `AUTH+OWNER` |

### Stateless Runs (`/api/runs`)

| Method | Path                          | Description                             | Access   |
| ------ | ----------------------------- | --------------------------------------- | -------- |
| `POST` | `/api/runs/stream`            | Create a run + stream SSE (auto thread) | `PUBLIC` |
| `POST` | `/api/runs/wait`              | Create a run + block (auto thread)      | `PUBLIC` |
| `GET`  | `/api/runs/{run_id}/messages` | Get paginated messages by run ID        | `AUTH`   |
| `GET`  | `/api/runs/{run_id}/feedback` | Get feedback for a run                  | `AUTH`   |

---

## Shared Request Schema: `RunCreateRequest`

Used by all run-creation endpoints (stream, wait, background create).

| Field                | Type                    | Required | Description                                                                                      |
| -------------------- | ----------------------- | -------- | ------------------------------------------------------------------------------------------------ |
| `assistant_id`       | string \| null          | No       | Agent to use (e.g., `"lead_agent"` or custom agent name)                                         |
| `input`              | object \| null          | No       | Graph input, e.g., `{"messages": [{"role": "human", "content": "..."}]}`                         |
| `command`            | object \| null          | No       | LangGraph `Command` object (for graph control flow)                                              |
| `metadata`           | object \| null          | No       | Run metadata                                                                                     |
| `config`             | object \| null          | No       | `RunnableConfig` overrides (includes `configurable.thread_id` for stateless endpoint)            |
| `context`            | object \| null          | No       | DeerFlow context overrides: `model_name`, `thinking_enabled`, `is_plan_mode`, `subagent_enabled` |
| `webhook`            | string \| null          | No       | Completion callback URL                                                                          |
| `checkpoint_id`      | string \| null          | No       | Resume from a specific checkpoint                                                                |
| `checkpoint`         | object \| null          | No       | Full checkpoint object                                                                           |
| `interrupt_before`   | array \| `"*"` \| null  | No       | Node names to interrupt before                                                                   |
| `interrupt_after`    | array \| `"*"` \| null  | No       | Node names to interrupt after                                                                    |
| `stream_mode`        | array \| string \| null | No       | Stream mode(s)                                                                                   |
| `stream_subgraphs`   | boolean                 | No       | Include subgraph events (default: `false`)                                                       |
| `stream_resumable`   | boolean \| null         | No       | SSE resumable mode                                                                               |
| `on_disconnect`      | string                  | No       | `"cancel"` (default) or `"continue"` — behavior on SSE disconnect                                |
| `on_completion`      | string                  | No       | `"keep"` (default) or `"delete"` — delete temp thread on completion                              |
| `multitask_strategy` | string                  | No       | `"reject"` (default), `"rollback"`, `"interrupt"`, `"enqueue"`                                   |
| `after_seconds`      | float \| null           | No       | Delayed execution (seconds)                                                                      |
| `if_not_exists`      | string                  | No       | `"create"` (default) or `"reject"` — thread creation policy                                      |
| `feedback_keys`      | array \| null           | No       | LangSmith feedback keys                                                                          |

**Typical minimal request:**

```json
{
  "assistant_id": "lead_agent",
  "input": {
    "messages": [{ "role": "human", "content": "What is the capital of France?" }]
  }
}
```

**With DeerFlow context overrides:**

```json
{
  "assistant_id": "lead_agent",
  "input": {
    "messages": [{ "role": "human", "content": "Analyze this dataset..." }]
  },
  "context": {
    "model_name": "claude-3-7-sonnet",
    "thinking_enabled": true,
    "is_plan_mode": true
  }
}
```

---

## Shared Response Schema: `RunResponse`

| Field                | Type           | Description                                                                              |
| -------------------- | -------------- | ---------------------------------------------------------------------------------------- |
| `run_id`             | string         | Run UUID                                                                                 |
| `thread_id`          | string         | Thread UUID                                                                              |
| `assistant_id`       | string \| null | Agent used                                                                               |
| `status`             | string         | `"pending"` \| `"running"` \| `"success"` \| `"error"` \| `"timeout"` \| `"interrupted"` |
| `metadata`           | object         | Run metadata                                                                             |
| `kwargs`             | object         | Run kwargs                                                                               |
| `multitask_strategy` | string         | Concurrency strategy used                                                                |
| `created_at`         | string         | ISO creation timestamp                                                                   |
| `updated_at`         | string         | ISO update timestamp                                                                     |

---

## Endpoint Details

### `POST /api/threads/{thread_id}/runs`

Create a background run and return immediately without waiting for completion.

**Access:** `AUTH+OWNER` (`require_existing=True`)

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |

**Query Params:** None

**Request Body:** `RunCreateRequest` (see above)

**Responses:**

| Status | Description                           |
| ------ | ------------------------------------- |
| `200`  | Run created and started in background |
| `401`  | Not authenticated                     |
| `404`  | Thread not found or not owned         |

**Response Schema (200):** `RunResponse`.

---

### `POST /api/threads/{thread_id}/runs/stream`

Create a run and stream events in real-time via Server-Sent Events (SSE). The response `Content-Location` header contains the run's resource URL — used by the LangGraph SDK's `useStream` hook to extract run metadata.

**Access:** `AUTH+OWNER` (`require_existing=True`)

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |

**Query Params:** None

**Request Body:** `RunCreateRequest` (see above)

**Response Headers:**

| Header              | Description                              |
| ------------------- | ---------------------------------------- |
| `Content-Type`      | `text/event-stream`                      |
| `Content-Location`  | `/api/threads/{thread_id}/runs/{run_id}` |
| `Cache-Control`     | `no-cache`                               |
| `X-Accel-Buffering` | `no` (disables Nginx buffering)          |

**Responses:**

| Status | Description                                                   |
| ------ | ------------------------------------------------------------- |
| `200`  | SSE stream; events emitted until run completes or disconnects |
| `401`  | Not authenticated                                             |
| `404`  | Thread not found or not owned                                 |

**SSE Event Format:**

```
event: metadata
data: {"run_id": "...", "thread_id": "..."}

event: messages/partial
data: {"id": "msg_abc", "type": "ai", "content": [{"type": "text", "text": "Hello"}]}

event: values
data: {"messages": [...], "title": "..."}

event: end
data: {}
```

---

### `POST /api/threads/{thread_id}/runs/wait`

Create a run and block until it completes, then return the final thread state (serialized checkpoint channel values).

**Access:** `AUTH+OWNER` (`require_existing=True`)

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |

**Query Params:** None

**Request Body:** `RunCreateRequest` (see above)

**Responses:**

| Status | Description                                                       |
| ------ | ----------------------------------------------------------------- |
| `200`  | Final state dict (channel values) or `{status, error}` on failure |
| `401`  | Not authenticated                                                 |
| `404`  | Thread not found or not owned                                     |

**Response Schema (200):** Dict of channel values from the final checkpoint, e.g.:

```json
{
  "messages": [...],
  "title": "Research session",
  "artifacts": [...]
}
```

---

### `GET /api/threads/{thread_id}/runs`

List all runs associated with a thread.

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
| `200`  | Array of `RunResponse`        |
| `401`  | Not authenticated             |
| `404`  | Thread not found or not owned |

---

### `GET /api/threads/{thread_id}/runs/{run_id}`

Get details of a specific run.

**Access:** `AUTH+OWNER`

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |
| `run_id`    | Run UUID    |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description                         |
| ------ | ----------------------------------- |
| `200`  | `RunResponse`                       |
| `401`  | Not authenticated                   |
| `404`  | Run or thread not found / not owned |

---

### `POST /api/threads/{thread_id}/runs/{run_id}/cancel`

Cancel a running or pending run.

- `action=interrupt` — Stop execution, keep current checkpoint (run can be resumed)
- `action=rollback` — Stop execution, revert to the pre-run checkpoint state

**Access:** `AUTH+OWNER` (`require_existing=True`)

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |
| `run_id`    | Run UUID    |

**Query Params:**

| Param    | Type    | Default       | Description                                                                                       |
| -------- | ------- | ------------- | ------------------------------------------------------------------------------------------------- |
| `wait`   | boolean | `false`       | If `true`, block until the run fully stops and return `204`; if `false`, return `202` immediately |
| `action` | string  | `"interrupt"` | `"interrupt"` or `"rollback"`                                                                     |

**Request Body:** None

**Responses:**

| Status | Description                                                 |
| ------ | ----------------------------------------------------------- |
| `202`  | Cancel initiated (returned when `wait=false`)               |
| `204`  | Run cancelled and fully stopped (returned when `wait=true`) |
| `401`  | Not authenticated                                           |
| `404`  | Run or thread not found / not owned                         |
| `409`  | Run is not cancellable (already completed or errored)       |

---

### `GET /api/threads/{thread_id}/runs/{run_id}/join`

Join an existing run's SSE event stream. If the run has already completed, buffered events are replayed.

**Access:** `AUTH+OWNER`

**Path Params:**

| Param       | Description      |
| ----------- | ---------------- |
| `thread_id` | Thread UUID      |
| `run_id`    | Run UUID to join |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description                         |
| ------ | ----------------------------------- |
| `200`  | SSE stream                          |
| `401`  | Not authenticated                   |
| `404`  | Run or thread not found / not owned |

---

### `GET|POST /api/threads/{thread_id}/runs/{run_id}/stream`

Dual-purpose endpoint used by the LangGraph SDK's `joinStream` and the `useStream` stop button:

- **`GET`** — Join existing run's SSE stream (same as `/join`)
- **`POST` with `action` query param** — Cancel the run first, then stream remaining buffered events for a clean shutdown

**Access:** `AUTH+OWNER`

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |
| `run_id`    | Run UUID    |

**Query Params:**

| Param    | Type           | Default | Description                                                                  |
| -------- | -------------- | ------- | ---------------------------------------------------------------------------- |
| `action` | string \| null | `null`  | `"interrupt"` or `"rollback"` — triggers cancel before streaming             |
| `wait`   | integer        | `0`     | `1` to block until cancel completes, return `204`; `0` to continue streaming |

**Request Body:** None (ignored even for POST)

**Responses:**

| Status | Description                                     |
| ------ | ----------------------------------------------- |
| `200`  | SSE stream                                      |
| `204`  | Cancel complete (only when `action` + `wait=1`) |
| `401`  | Not authenticated                               |
| `404`  | Run or thread not found / not owned             |

---

### `GET /api/threads/{thread_id}/messages`

Return all displayable messages for a thread (across all runs), with feedback attached to the last AI message of each run. Supports cursor-based pagination.

**Access:** `AUTH+OWNER`

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |

**Query Params:**

| Param        | Type            | Default | Description                                                   |
| ------------ | --------------- | ------- | ------------------------------------------------------------- |
| `limit`      | integer         | `50`    | Max messages to return (max `200`)                            |
| `before_seq` | integer \| null | —       | Return messages with `seq < before_seq` (backward pagination) |
| `after_seq`  | integer \| null | —       | Return messages with `seq > after_seq` (forward pagination)   |

**Request Body:** None

**Responses:**

| Status | Description                                                                |
| ------ | -------------------------------------------------------------------------- |
| `200`  | Array of message dicts with `feedback` attached to last AI message per run |
| `401`  | Not authenticated                                                          |
| `404`  | Thread not found or not owned                                              |

Each message dict includes a `feedback` field:

- On the last AI message of each run: `{ feedback_id, rating, comment }` or `null`
- On all other messages: `null`

---

### `GET /api/threads/{thread_id}/runs/{run_id}/messages`

Return paginated messages for a specific run.

**Access:** `AUTH+OWNER`

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |
| `run_id`    | Run UUID    |

**Query Params:**

| Param        | Type            | Default | Description                |
| ------------ | --------------- | ------- | -------------------------- |
| `limit`      | integer         | `50`    | Max messages (1–200)       |
| `before_seq` | integer \| null | —       | Backward pagination cursor |
| `after_seq`  | integer \| null | —       | Forward pagination cursor  |

**Request Body:** None

**Responses:**

| Status | Description                         |
| ------ | ----------------------------------- |
| `200`  | Paginated messages                  |
| `401`  | Not authenticated                   |
| `404`  | Thread or run not found / not owned |

**Response Schema (200):**

| Field      | Type    | Description                                  |
| ---------- | ------- | -------------------------------------------- |
| `data`     | array   | Page of message dicts                        |
| `has_more` | boolean | Whether more messages exist beyond this page |

---

### `GET /api/threads/{thread_id}/runs/{run_id}/events`

Return the full raw event stream for a run (for debugging and auditing).

**Access:** `AUTH+OWNER`

**Path Params:**

| Param       | Description |
| ----------- | ----------- |
| `thread_id` | Thread UUID |
| `run_id`    | Run UUID    |

**Query Params:**

| Param         | Type           | Default | Description                                                                    |
| ------------- | -------------- | ------- | ------------------------------------------------------------------------------ |
| `event_types` | string \| null | —       | Comma-separated list of event types to filter (e.g., `"ai_message,tool_call"`) |
| `limit`       | integer        | `500`   | Max events to return (max `2000`)                                              |

**Request Body:** None

**Responses:**

| Status | Description                         |
| ------ | ----------------------------------- |
| `200`  | Array of event dicts                |
| `401`  | Not authenticated                   |
| `404`  | Thread or run not found / not owned |

---

### `GET /api/threads/{thread_id}/token-usage`

Aggregate token usage across all runs in a thread, broken down by model and by caller type (lead agent, subagent, middleware).

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
| `200`  | Token usage aggregation       |
| `401`  | Not authenticated             |
| `404`  | Thread not found or not owned |

**Response Schema (200):**

| Field                 | Type    | Description                                             |
| --------------------- | ------- | ------------------------------------------------------- |
| `thread_id`           | string  | Thread UUID                                             |
| `total_tokens`        | integer | Total tokens (input + output)                           |
| `total_input_tokens`  | integer | Total input tokens                                      |
| `total_output_tokens` | integer | Total output tokens                                     |
| `total_runs`          | integer | Number of runs contributing                             |
| `by_model`            | object  | Per-model breakdown: `{ model_name: { tokens, runs } }` |
| `by_caller`           | object  | `{ lead_agent, subagent, middleware }` token counts     |

**Example (200):**

```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_tokens": 12500,
  "total_input_tokens": 9000,
  "total_output_tokens": 3500,
  "total_runs": 3,
  "by_model": {
    "claude-3-7-sonnet": { "tokens": 12500, "runs": 3 }
  },
  "by_caller": {
    "lead_agent": 10000,
    "subagent": 2000,
    "middleware": 500
  }
}
```

---

## Stateless Run Endpoints

### `POST /api/runs/stream`

Create a run and stream events via SSE. If `config.configurable.thread_id` is provided in the request body, the run is created on that thread. Otherwise a new temporary thread is auto-created.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body:** `RunCreateRequest` (see above). To reuse a thread, set `config.configurable.thread_id`.

**Response Headers & SSE format:** Same as `POST /api/threads/{thread_id}/runs/stream`.

**Responses:**

| Status | Description |
| ------ | ----------- |
| `200`  | SSE stream  |

---

### `POST /api/runs/wait`

Create a run and block until completion, returning the final state.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body:** `RunCreateRequest` (see above).

**Responses:**

| Status | Description                                      |
| ------ | ------------------------------------------------ |
| `200`  | Final state dict (same as thread-scoped `/wait`) |

---

### `GET /api/runs/{run_id}/messages`

Return paginated messages for a run, looked up directly by run ID (no thread ID required).

**Access:** `AUTH` (ownership enforced via run's associated user)

**Path Params:**

| Param    | Description |
| -------- | ----------- |
| `run_id` | Run UUID    |

**Query Params:**

| Param        | Type            | Default | Description                |
| ------------ | --------------- | ------- | -------------------------- |
| `limit`      | integer         | `50`    | Max messages (1–200)       |
| `before_seq` | integer \| null | —       | Backward pagination cursor |
| `after_seq`  | integer \| null | —       | Forward pagination cursor  |

**Request Body:** None

**Responses:**

| Status | Description                       |
| ------ | --------------------------------- |
| `200`  | `{ data: [...], has_more: bool }` |
| `401`  | Not authenticated                 |
| `404`  | Run not found                     |

---

### `GET /api/runs/{run_id}/feedback`

Return all feedback for a run, looked up by run ID.

**Access:** `AUTH`

**Path Params:**

| Param    | Description |
| -------- | ----------- |
| `run_id` | Run UUID    |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description             |
| ------ | ----------------------- |
| `200`  | Array of feedback dicts |
| `401`  | Not authenticated       |
| `404`  | Run not found           |
