# MCP Transport Types

In the context of the **Model Context Protocol (MCP)**, these three terms refer to the
**transport layer** — the underlying communication mechanism used by the client (DeerFlow)
and the MCP server (the tool provider) to exchange messages.

The primary difference lies in **where the server runs** (locally vs. remotely) and
**how data flows** between them.

---

## 1. `stdio` (Standard Input/Output)

The default and most common transport for local MCP servers.

**How it works:** The client spins up the MCP server as a **local subprocess** on the same
machine. Instead of communicating over a network, they talk via `sys.stdin` and `sys.stdout`.
The client writes JSON-RPC commands to the server's stdin; the server writes responses to stdout.

**When to use it:** When the MCP server runs locally on the same container or machine as the
DeerFlow backend.

**Required config fields:** `command` + `args`. `env` is optional — pass environment variables
the subprocess needs (e.g. API keys that the server process will read from `os.environ`).

**`extensions_config.json` example:**

```json
{
  "mcpServers": {
    "github": {
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "$GITHUB_TOKEN" },
      "description": "GitHub MCP server"
    }
  }
}
```

**Auth:** No OAuth support — stdio servers authenticate via environment variables or
command-line arguments injected at subprocess launch time.

---

## 2. `sse` (Server-Sent Events)

A web technology that allows a remote server to maintain a **one-way, persistent connection**
to push real-time data to the client.

**How it works:** In MCP, SSE is typically paired with HTTP requests. The client opens a
persistent HTTP connection to the server's SSE endpoint to receive asynchronous responses or
event streams _from_ the server. To send data _to_ the server, the client makes separate
HTTP POST requests. The connection stays open between calls.

**When to use it:** When the MCP server is hosted remotely and needs to stream continuous,
real-time responses (e.g. long-running tool executions where progress is streamed back).

**Required config fields:** `url`. `headers` for static headers (e.g. API key). `oauth` for
token-based auth.

**`extensions_config.json` example:**

```json
{
  "mcpServers": {
    "streaming-search": {
      "enabled": true,
      "type": "sse",
      "url": "https://mcp.example.com/sse",
      "headers": { "X-Api-Key": "static-key" },
      "oauth": {
        "enabled": true,
        "token_url": "https://auth.example.com/oauth/token",
        "grant_type": "client_credentials",
        "client_id": "my-client-id",
        "client_secret": "my-client-secret"
      },
      "description": "Streaming search MCP server"
    }
  }
}
```

**Auth:** Supports both static `headers` (passed at connection time) and OAuth via the
`oauth` config block (tokens are fetched, cached, and refreshed automatically by
`OAuthTokenManager` in `mcp/oauth.py`).

---

## 3. `http` (Standard HTTP)

Traditional, stateless web communication.

**How it works:** The client makes a standard HTTP POST request to a remote endpoint, the
server processes it and returns a single response, and the connection closes. There is no
persistent stream or long-lived connection.

**When to use it:** When the MCP server is a standard remote web API and you don't need
real-time streaming or asynchronous push events from the server.

**Required config fields:** `url`. `headers` for static headers. `oauth` for token-based auth.

**`extensions_config.json` example:**

```json
{
  "mcpServers": {
    "company-tools": {
      "enabled": true,
      "type": "http",
      "url": "https://internal.company.com/mcp",
      "headers": { "Authorization": "Bearer static-token" },
      "description": "Internal company tool server"
    }
  }
}
```

**Auth:** Same options as `sse` — static `headers` and/or OAuth. The `Authorization` header
in `headers` is a static value; use `oauth` when tokens expire and must be refreshed.

---

## Summary Comparison

| Feature             | `stdio`                        | `sse`                                               | `http`                                |
| ------------------- | ------------------------------ | --------------------------------------------------- | ------------------------------------- |
| **Location**        | Local (same machine/container) | Remote (over a network)                             | Remote (over a network)               |
| **Connection**      | Persistent process pipe        | Persistent downstream stream                        | Short-lived request/response          |
| **Data Flow**       | Bidirectional via stdin/stdout | Server pushes continuously; client POSTs separately | Client requests, server responds once |
| **Required field**  | `command` + `args`             | `url`                                               | `url`                                 |
| **Optional fields** | `env`                          | `headers`, `oauth`                                  | `headers`, `oauth`                    |
| **OAuth support**   | No                             | Yes                                                 | Yes                                   |
| **Setup overhead**  | Low — no network config        | Medium — requires web server + SSE endpoint         | Medium — requires standard web server |

---

## How DeerFlow Uses This

`build_server_params()` in `mcp/client.py` translates `McpServerConfig` into the dict format
`MultiServerMCPClient` expects. The transport type determines which fields are included:

```python
if transport_type == "stdio":
    params["command"] = config.command
    params["args"] = config.args          # always included, even as []
    if config.env: params["env"] = ...    # only when non-empty

elif transport_type in ("sse", "http"):
    params["url"] = config.url
    if config.headers: params["headers"] = ...   # static headers only
    # OAuth headers are injected separately — not in this params dict
```

OAuth is handled in two layers on top of the params dict (for `sse`/`http` only):

1. **Connection-time** — `get_initial_oauth_headers()` fetches a token and merges it into
   `servers_config[name]["headers"]` before `MultiServerMCPClient` is constructed.
   This covers the transport handshake (SSE connection negotiation).

2. **Per-call** — `build_oauth_tool_interceptor()` returns a closure that re-evaluates the
   token on every tool invocation, refreshing it proactively before expiry.

Regardless of transport, all loaded tools are namespaced as `{server-name}__{tool-name}`
(`tool_name_prefix=True`) to prevent naming collisions across servers.
