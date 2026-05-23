# Models API

> Source: `backend/app/gateway/routers/models.py`
> Prefix: `/api`

Exposes the list of configured AI models from `config.yaml`. Sensitive provider fields (API keys, internal configs) are excluded. Also surfaces whether token usage display is enabled.

## Quick Reference

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET` | `/api/models` | List all configured models | `PUBLIC` |
| `GET` | `/api/models/{model_name}` | Get a specific model by name | `PUBLIC` |

---

## Endpoint Details

### `GET /api/models`

List all available AI models configured in `config.yaml`, along with token usage display settings.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Model list returned |
| `503` | Configuration not available |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `models` | array | List of `ModelResponse` objects |
| `models[].name` | string | Unique model identifier (used in API calls) |
| `models[].model` | string | Actual provider model string (e.g., `"gpt-4o"`) |
| `models[].display_name` | string \| null | Human-readable label for UI |
| `models[].description` | string \| null | Model description |
| `models[].supports_thinking` | boolean | Whether model supports extended thinking mode |
| `models[].supports_reasoning_effort` | boolean | Whether model supports reasoning effort control |
| `token_usage` | object | Token usage UI config |
| `token_usage.enabled` | boolean | Whether token usage display is enabled |

**Example (200):**
```json
{
  "models": [
    {
      "name": "claude-3-7-sonnet",
      "model": "claude-3-7-sonnet-20250219",
      "display_name": "Claude 3.7 Sonnet",
      "description": "Anthropic's balanced model with extended thinking",
      "supports_thinking": true,
      "supports_reasoning_effort": false
    },
    {
      "name": "gpt-4o",
      "model": "gpt-4o",
      "display_name": "GPT-4o",
      "description": "OpenAI's multimodal flagship model",
      "supports_thinking": false,
      "supports_reasoning_effort": true
    }
  ],
  "token_usage": {
    "enabled": true
  }
}
```

---

### `GET /api/models/{model_name}`

Retrieve detailed information about a specific AI model by its configured name.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `model_name` | The `name` field of the model as defined in `config.yaml` |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Model details returned |
| `404` | Model not found |
| `503` | Configuration not available |

**Response Schema (200):** Same as a single element in `models[]` from `GET /api/models`.

**Example (200):**
```json
{
  "name": "claude-3-7-sonnet",
  "model": "claude-3-7-sonnet-20250219",
  "display_name": "Claude 3.7 Sonnet",
  "description": null,
  "supports_thinking": true,
  "supports_reasoning_effort": false
}
```
