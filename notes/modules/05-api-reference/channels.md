# Channels API

> Source: `backend/app/gateway/routers/channels.py`
> Prefix: `/api/channels`

Runtime management of IM platform channel integrations (Feishu, Slack, Telegram, DingTalk). Provides status inspection and restart capability for individual channels.

## Quick Reference

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET` | `/api/channels/` | Get status of all IM channels | `PUBLIC` |
| `POST` | `/api/channels/{name}/restart` | Restart a specific IM channel | `PUBLIC` |

---

## Endpoint Details

### `GET /api/channels/`

Get the running status of all configured IM channels and the overall channel service.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Channel status returned (even if service is not running) |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `service_running` | boolean | Whether the channel service is active |
| `channels` | object | Map of channel name → channel status dict |

> When the channel service is not configured/running, `service_running` is `false` and `channels` is `{}`.

**Example (200 — service running):**
```json
{
  "service_running": true,
  "channels": {
    "feishu": {
      "name": "feishu",
      "running": true,
      "error": null
    },
    "slack": {
      "name": "slack",
      "running": false,
      "error": "Bot token not configured"
    }
  }
}
```

**Example (200 — service not running):**
```json
{
  "service_running": false,
  "channels": {}
}
```

---

### `POST /api/channels/{name}/restart`

Restart a specific IM channel by name.

**Access:** `PUBLIC`

**Path Params:**

| Param | Description |
|-------|-------------|
| `name` | Channel name (e.g., `"feishu"`, `"slack"`, `"telegram"`, `"dingtalk"`) |

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Restart result (success or failure) |
| `503` | Channel service is not running |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the restart succeeded |
| `message` | string | Human-readable result message |

**Example (200 — success):**
```json
{
  "success": true,
  "message": "Channel feishu restarted successfully"
}
```

**Example (200 — failure):**
```json
{
  "success": false,
  "message": "Failed to restart channel feishu"
}
```
