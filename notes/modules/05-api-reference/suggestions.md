# Suggestions API

> Source: `backend/app/gateway/routers/suggestions.py`
> Prefix: `/api`

Generate follow-up question suggestions based on recent conversation context. Uses an LLM to produce short, relevant questions the user might want to ask next. Rich list/block model content in messages is normalized before the LLM call.

## Quick Reference

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `POST` | `/api/threads/{thread_id}/suggestions` | Generate follow-up suggestions | `AUTH+OWNER` |

---

## Endpoint Details

### `POST /api/threads/{thread_id}/suggestions`

Generate up to `n` follow-up questions a user might ask based on recent conversation messages. Questions are written in the same language as the user's messages and kept concise (≤20 words / ≤40 Chinese characters).

On any LLM error or empty input, returns an empty suggestions list rather than a 5xx error.

**Access:** `AUTH+OWNER`

**Path Params:**

| Param | Description |
|-------|-------------|
| `thread_id` | Thread UUID (used for ownership check only; no thread data is read) |

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `messages` | array | Yes | At least one entry | Recent conversation messages for context |
| `messages[].role` | string | Yes | `"user"` / `"human"` / `"assistant"` / `"ai"` | Message role |
| `messages[].content` | string | Yes | — | Message content as plain text |
| `n` | integer | No | 1–5, default `3` | Number of suggestions to generate |
| `model_name` | string \| null | No | — | Optional model override (defaults to system default model) |

**Example Request:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What are the main differences between SQL and NoSQL databases?"
    },
    {
      "role": "assistant",
      "content": "SQL databases use structured tables with predefined schemas, while NoSQL databases offer flexible schemas..."
    }
  ],
  "n": 3
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Suggestions returned (may be empty list if input is empty or LLM fails) |
| `401` | Not authenticated |
| `404` | Thread not found or not owned |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `suggestions` | array of string | Generated follow-up questions (length ≤ `n`) |

**Example (200):**
```json
{
  "suggestions": [
    "When should I choose a NoSQL database over SQL?",
    "What are the most popular NoSQL databases available?",
    "How does data consistency work in distributed NoSQL systems?"
  ]
}
```

**Example (200 — empty input or failure):**
```json
{
  "suggestions": []
}
```
