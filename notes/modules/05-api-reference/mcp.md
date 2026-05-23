# MCP Configuration API

> Source: `backend/app/gateway/routers/mcp.py`
> Prefix: `/api`

Read and update Model Context Protocol (MCP) server configurations. Changes are persisted to `extensions_config.json`; the LangGraph runtime detects file changes via mtime and reinitializes MCP tools automatically.

## Quick Reference

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET` | `/api/mcp/config` | Get current MCP server configuration | `PUBLIC` |
| `PUT` | `/api/mcp/config` | Update and save MCP server configuration | `PUBLIC` |

---

## Endpoint Details

### `GET /api/mcp/config`

Retrieve the current MCP server configuration loaded from `extensions_config.json`.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body:** None

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | MCP configuration returned |

**Response Schema (200):**

| Field | Type | Description |
|-------|------|-------------|
| `mcp_servers` | object | Map of server name → `McpServerConfigResponse` |
| `mcp_servers.{name}.enabled` | boolean | Whether this server is active |
| `mcp_servers.{name}.type` | string | Transport type: `"stdio"`, `"sse"`, or `"http"` |
| `mcp_servers.{name}.command` | string \| null | Command to run (stdio only) |
| `mcp_servers.{name}.args` | array | Command arguments (stdio only) |
| `mcp_servers.{name}.env` | object | Environment variables for the server |
| `mcp_servers.{name}.url` | string \| null | Server URL (sse/http only) |
| `mcp_servers.{name}.headers` | object | HTTP headers to send (sse/http only) |
| `mcp_servers.{name}.oauth` | object \| null | OAuth config for HTTP/SSE servers (see below) |
| `mcp_servers.{name}.description` | string | Human-readable description |

**OAuth sub-schema** (`mcp_servers.{name}.oauth`):

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Whether OAuth token injection is active |
| `token_url` | string | OAuth token endpoint URL |
| `grant_type` | string | `"client_credentials"` or `"refresh_token"` |
| `client_id` | string \| null | OAuth client ID |
| `client_secret` | string \| null | OAuth client secret |
| `refresh_token` | string \| null | OAuth refresh token |
| `scope` | string \| null | OAuth scope |
| `audience` | string \| null | OAuth audience |
| `token_field` | string | Token response field (default: `"access_token"`) |
| `token_type_field` | string | Token type field (default: `"token_type"`) |
| `expires_in_field` | string | Expires-in field (default: `"expires_in"`) |
| `default_token_type` | string | Fallback token type (default: `"Bearer"`) |
| `refresh_skew_seconds` | integer | Refresh this many seconds before expiry (default: `60`) |
| `extra_token_params` | object | Extra form params sent to token endpoint |

**Example (200):**
```json
{
  "mcp_servers": {
    "github": {
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "ghp_xxx"},
      "url": null,
      "headers": {},
      "oauth": null,
      "description": "GitHub MCP server for repository operations"
    }
  }
}
```

---

### `PUT /api/mcp/config`

Update the MCP server configuration and save it to `extensions_config.json`. Preserves existing skills configuration. The LangGraph runtime will detect the file change and reinitialize tools automatically.

**Access:** `PUBLIC`

**Query Params:** None

**Request Body** (`application/json`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mcp_servers` | object | Yes | Complete map of server name → server config (replaces existing `mcp_servers` section) |

Each server config object accepts the same fields as in `GET /api/mcp/config` (all fields optional except they must be valid for the transport type).

**Example Request:**
```json
{
  "mcp_servers": {
    "github": {
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "$GITHUB_TOKEN"},
      "description": "GitHub MCP server for repository operations"
    },
    "filesystem": {
      "enabled": false,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "description": "Local filesystem access"
    }
  }
}
```

**Responses:**

| Status | Description |
|--------|-------------|
| `200` | Configuration saved; reloaded config returned |
| `500` | Failed to write configuration file |

**Response Schema (200):** Same as `GET /api/mcp/config`.
