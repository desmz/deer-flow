# API Endpoints Overview

> Section 05 — Backend: Gateway API (FastAPI)
> Companion to: [`05a-gateway-api.md`](05a-gateway-api.md) (app bootstrap, middleware, deps, services)
> Detailed reference: [`05-api-reference/`](05-api-reference/) (one file per API set)

This document maps every HTTP endpoint exposed by the DeerFlow Gateway API, grouped by API set. Use it as a navigation index to the detailed per-set files.

---

## Access Level Legend

All endpoints in the Gateway API fall into one of four access levels:

| Symbol       | Name                  | Mechanism                                  | Behavior                                                                                           |
| ------------ | --------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| `PUBLIC`     | Public                | None                                       | No credentials required — callable by anyone                                                       |
| `AUTH`       | Authenticated         | Valid `access_token` HttpOnly cookie (JWT) | Returns `401` if cookie is missing or expired                                                      |
| `AUTH+OWNER` | Authenticated + Owner | JWT **and** thread ownership check         | Returns `401` if unauthenticated; returns `404` if authenticated but caller doesn't own the thread |
| `FEATURE`    | Feature-gated         | Server-side config flag                    | No user authentication; returns `403` if the feature is disabled in `config.yaml`                  |

> **Note on auth-disabled mode:** When `auth.enabled: false` is set in `config.yaml`, the auth middleware injects a synthetic `"default"` user for every request. In this mode, `AUTH` and `AUTH+OWNER` routes behave as `PUBLIC` — no cookie is required. `FEATURE`-gated routes are unaffected by the auth toggle.

> **Token revocation:** Changing a password increments `token_version`, which invalidates all existing JWTs. The `AUTH` check compares the cookie's `ver` claim against the stored version; a mismatch returns `401` even for a structurally valid token.

---

## API Sets

| API Set         | Prefix                                 | Responsibility                                                                             | # Endpoints | Reference                                         |
| --------------- | -------------------------------------- | ------------------------------------------------------------------------------------------ | ----------- | ------------------------------------------------- |
| **Auth**        | `/api/v1/auth`                         | User login, registration, logout, password management, OAuth stubs                         | 9           | [auth.md](05-api-reference/auth.md)               |
| **Agents**      | `/api/agents`, `/api/user-profile`     | CRUD for custom per-user agents and global USER.md profile                                 | 8           | [agents.md](05-api-reference/agents.md)           |
| **Assistants**  | `/api/assistants`                      | LangGraph Platform-compatible assistant stubs (satisfies `useStream` SDK)                  | 4           | [assistants.md](05-api-reference/assistants.md)   |
| **Threads**     | `/api/threads`                         | Thread lifecycle: create, search, read, patch, delete, state, history                      | 8           | [threads.md](05-api-reference/threads.md)         |
| **Runs**        | `/api/threads/{id}/runs`, `/api/runs`  | Agent run execution: create, stream SSE, wait, cancel, join, messages, events, token usage | 16          | [runs.md](05-api-reference/runs.md)               |
| **Feedback**    | `/api/threads/{id}/runs/{id}/feedback` | Thumbs-up/down feedback on runs                                                            | 6           | [feedback.md](05-api-reference/feedback.md)       |
| **Uploads**     | `/api/threads/{id}/uploads`            | File uploads to thread-scoped directories, with optional document conversion               | 4           | [uploads.md](05-api-reference/uploads.md)         |
| **Artifacts**   | `/api/threads/{id}/artifacts`          | Serve agent-generated files with MIME-aware delivery and active content protection         | 1           | [artifacts.md](05-api-reference/artifacts.md)     |
| **Suggestions** | `/api/threads/{id}/suggestions`        | LLM-generated follow-up question suggestions                                               | 1           | [suggestions.md](05-api-reference/suggestions.md) |
| **Models**      | `/api/models`                          | List and inspect configured AI models                                                      | 2           | [models.md](05-api-reference/models.md)           |
| **Skills**      | `/api/skills`                          | Enable/disable skills; install, edit, rollback custom skills                               | 10          | [skills.md](05-api-reference/skills.md)           |
| **Memory**      | `/api/memory`                          | Read/write the persistent per-user memory store (context sections + discrete facts)        | 10          | [memory.md](05-api-reference/memory.md)           |
| **MCP**         | `/api/mcp`                             | Read and update MCP server configurations (persisted to `extensions_config.json`)          | 2           | [mcp.md](05-api-reference/mcp.md)                 |
| **Channels**    | `/api/channels`                        | Runtime status and restart control for IM platform channels                                | 2           | [channels.md](05-api-reference/channels.md)       |

**Total: 83 endpoints**

---

## Flat Endpoint Index

A complete alphabetical-by-prefix listing of all endpoints for quick lookup.

### `/api/agents`

| Method   | Path                 | Access    | Description                      |
| -------- | -------------------- | --------- | -------------------------------- |
| `GET`    | `/api/agents`        | `FEATURE` | List all custom agents           |
| `POST`   | `/api/agents`        | `FEATURE` | Create a custom agent            |
| `GET`    | `/api/agents/check`  | `FEATURE` | Validate agent name availability |
| `GET`    | `/api/agents/{name}` | `FEATURE` | Get a specific agent             |
| `PUT`    | `/api/agents/{name}` | `FEATURE` | Update an agent                  |
| `DELETE` | `/api/agents/{name}` | `FEATURE` | Delete an agent                  |

### `/api/assistants`

| Method | Path                                     | Access   | Description                |
| ------ | ---------------------------------------- | -------- | -------------------------- |
| `POST` | `/api/assistants/search`                 | `PUBLIC` | Search/list assistants     |
| `GET`  | `/api/assistants/{assistant_id}`         | `PUBLIC` | Get an assistant           |
| `GET`  | `/api/assistants/{assistant_id}/graph`   | `PUBLIC` | Get graph structure (stub) |
| `GET`  | `/api/assistants/{assistant_id}/schemas` | `PUBLIC` | Get JSON schemas (stub)    |

### `/api/channels`

| Method | Path                           | Access   | Description              |
| ------ | ------------------------------ | -------- | ------------------------ |
| `GET`  | `/api/channels/`               | `PUBLIC` | Get all channel statuses |
| `POST` | `/api/channels/{name}/restart` | `PUBLIC` | Restart a channel        |

### `/api/mcp`

| Method | Path              | Access   | Description              |
| ------ | ----------------- | -------- | ------------------------ |
| `GET`  | `/api/mcp/config` | `PUBLIC` | Get MCP configuration    |
| `PUT`  | `/api/mcp/config` | `PUBLIC` | Update MCP configuration |

### `/api/memory`

| Method   | Path                          | Access   | Description                 |
| -------- | ----------------------------- | -------- | --------------------------- |
| `GET`    | `/api/memory`                 | `PUBLIC` | Get memory data             |
| `POST`   | `/api/memory/reload`          | `PUBLIC` | Reload memory from file     |
| `DELETE` | `/api/memory`                 | `PUBLIC` | Clear all memory data       |
| `GET`    | `/api/memory/export`          | `PUBLIC` | Export memory as JSON       |
| `POST`   | `/api/memory/import`          | `PUBLIC` | Import and overwrite memory |
| `POST`   | `/api/memory/facts`           | `PUBLIC` | Create a fact manually      |
| `DELETE` | `/api/memory/facts/{fact_id}` | `PUBLIC` | Delete a fact               |
| `PATCH`  | `/api/memory/facts/{fact_id}` | `PUBLIC` | Partially update a fact     |
| `GET`    | `/api/memory/config`          | `PUBLIC` | Get memory config           |
| `GET`    | `/api/memory/status`          | `PUBLIC` | Get config + data combined  |

### `/api/models`

| Method | Path                       | Access   | Description                |
| ------ | -------------------------- | -------- | -------------------------- |
| `GET`  | `/api/models`              | `PUBLIC` | List all configured models |
| `GET`  | `/api/models/{model_name}` | `PUBLIC` | Get model details          |

### `/api/runs`

| Method | Path                          | Access   | Description                   |
| ------ | ----------------------------- | -------- | ----------------------------- |
| `POST` | `/api/runs/stream`            | `PUBLIC` | Stateless run + SSE stream    |
| `POST` | `/api/runs/wait`              | `PUBLIC` | Stateless run + blocking wait |
| `GET`  | `/api/runs/{run_id}/messages` | `AUTH`   | Paginated messages by run ID  |
| `GET`  | `/api/runs/{run_id}/feedback` | `AUTH`   | Feedback by run ID            |

### `/api/skills`

| Method   | Path                                       | Access   | Description                        |
| -------- | ------------------------------------------ | -------- | ---------------------------------- |
| `GET`    | `/api/skills`                              | `PUBLIC` | List all skills                    |
| `POST`   | `/api/skills/install`                      | `PUBLIC` | Install from `.skill` archive      |
| `GET`    | `/api/skills/custom`                       | `PUBLIC` | List custom skills                 |
| `GET`    | `/api/skills/custom/{skill_name}`          | `PUBLIC` | Get custom skill with content      |
| `PUT`    | `/api/skills/custom/{skill_name}`          | `PUBLIC` | Edit custom skill SKILL.md         |
| `DELETE` | `/api/skills/custom/{skill_name}`          | `PUBLIC` | Delete custom skill                |
| `GET`    | `/api/skills/custom/{skill_name}/history`  | `PUBLIC` | Get skill edit history             |
| `POST`   | `/api/skills/custom/{skill_name}/rollback` | `PUBLIC` | Rollback skill to previous version |
| `GET`    | `/api/skills/{skill_name}`                 | `PUBLIC` | Get skill details                  |
| `PUT`    | `/api/skills/{skill_name}`                 | `PUBLIC` | Enable or disable a skill          |

### `/api/threads`

| Method   | Path                                   | Access       | Description                    |
| -------- | -------------------------------------- | ------------ | ------------------------------ |
| `POST`   | `/api/threads`                         | `PUBLIC`     | Create a thread                |
| `POST`   | `/api/threads/search`                  | `PUBLIC`     | Search threads                 |
| `GET`    | `/api/threads/{thread_id}`             | `AUTH+OWNER` | Get thread info                |
| `PATCH`  | `/api/threads/{thread_id}`             | `AUTH+OWNER` | Patch thread metadata          |
| `DELETE` | `/api/threads/{thread_id}`             | `AUTH+OWNER` | Delete thread data             |
| `GET`    | `/api/threads/{thread_id}/state`       | `AUTH+OWNER` | Get thread state snapshot      |
| `POST`   | `/api/threads/{thread_id}/state`       | `AUTH+OWNER` | Update thread state            |
| `POST`   | `/api/threads/{thread_id}/history`     | `AUTH+OWNER` | Get checkpoint history         |
| `GET`    | `/api/threads/{thread_id}/messages`    | `AUTH+OWNER` | Thread messages with feedback  |
| `GET`    | `/api/threads/{thread_id}/token-usage` | `AUTH+OWNER` | Thread token usage aggregation |

### `/api/threads/{thread_id}/artifacts`

| Method | Path                                        | Access       | Description            |
| ------ | ------------------------------------------- | ------------ | ---------------------- |
| `GET`  | `/api/threads/{thread_id}/artifacts/{path}` | `AUTH+OWNER` | Serve an artifact file |

### `/api/threads/{thread_id}/runs`

| Method      | Path                                              | Access       | Description                |
| ----------- | ------------------------------------------------- | ------------ | -------------------------- |
| `POST`      | `/api/threads/{thread_id}/runs`                   | `AUTH+OWNER` | Create background run      |
| `POST`      | `/api/threads/{thread_id}/runs/stream`            | `AUTH+OWNER` | Create run + SSE stream    |
| `POST`      | `/api/threads/{thread_id}/runs/wait`              | `AUTH+OWNER` | Create run + blocking wait |
| `GET`       | `/api/threads/{thread_id}/runs`                   | `AUTH+OWNER` | List runs for thread       |
| `GET`       | `/api/threads/{thread_id}/runs/{run_id}`          | `AUTH+OWNER` | Get run details            |
| `POST`      | `/api/threads/{thread_id}/runs/{run_id}/cancel`   | `AUTH+OWNER` | Cancel a run               |
| `GET`       | `/api/threads/{thread_id}/runs/{run_id}/join`     | `AUTH+OWNER` | Join run SSE stream        |
| `GET\|POST` | `/api/threads/{thread_id}/runs/{run_id}/stream`   | `AUTH+OWNER` | Join or cancel-then-stream |
| `GET`       | `/api/threads/{thread_id}/runs/{run_id}/messages` | `AUTH+OWNER` | Paginated run messages     |
| `GET`       | `/api/threads/{thread_id}/runs/{run_id}/events`   | `AUTH+OWNER` | Full run event stream      |

### `/api/threads/{thread_id}/runs/{run_id}/feedback`

| Method   | Path                                                            | Access       | Description              |
| -------- | --------------------------------------------------------------- | ------------ | ------------------------ |
| `PUT`    | `/api/threads/{thread_id}/runs/{run_id}/feedback`               | `AUTH+OWNER` | Upsert feedback          |
| `POST`   | `/api/threads/{thread_id}/runs/{run_id}/feedback`               | `AUTH+OWNER` | Create feedback          |
| `GET`    | `/api/threads/{thread_id}/runs/{run_id}/feedback`               | `AUTH+OWNER` | List feedback            |
| `GET`    | `/api/threads/{thread_id}/runs/{run_id}/feedback/stats`         | `AUTH+OWNER` | Feedback stats           |
| `DELETE` | `/api/threads/{thread_id}/runs/{run_id}/feedback`               | `AUTH+OWNER` | Delete user's feedback   |
| `DELETE` | `/api/threads/{thread_id}/runs/{run_id}/feedback/{feedback_id}` | `AUTH+OWNER` | Delete specific feedback |

### `/api/threads/{thread_id}/uploads`

| Method   | Path                                          | Access       | Description             |
| -------- | --------------------------------------------- | ------------ | ----------------------- |
| `POST`   | `/api/threads/{thread_id}/uploads`            | `AUTH+OWNER` | Upload files            |
| `GET`    | `/api/threads/{thread_id}/uploads/limits`     | `AUTH+OWNER` | Get upload limits       |
| `GET`    | `/api/threads/{thread_id}/uploads/list`       | `AUTH+OWNER` | List uploaded files     |
| `DELETE` | `/api/threads/{thread_id}/uploads/{filename}` | `AUTH+OWNER` | Delete an uploaded file |

### `/api/user-profile`

| Method | Path                | Access    | Description                |
| ------ | ------------------- | --------- | -------------------------- |
| `GET`  | `/api/user-profile` | `FEATURE` | Get global USER.md content |
| `PUT`  | `/api/user-profile` | `FEATURE` | Update global USER.md      |

### `/api/v1/auth`

| Method | Path                               | Access   | Description               |
| ------ | ---------------------------------- | -------- | ------------------------- |
| `POST` | `/api/v1/auth/login/local`         | `PUBLIC` | Email/password login      |
| `POST` | `/api/v1/auth/register`            | `PUBLIC` | Register new user         |
| `POST` | `/api/v1/auth/logout`              | `PUBLIC` | Logout (clear cookie)     |
| `POST` | `/api/v1/auth/change-password`     | `AUTH`   | Change password           |
| `GET`  | `/api/v1/auth/me`                  | `AUTH`   | Get current user          |
| `GET`  | `/api/v1/auth/setup-status`        | `PUBLIC` | Check admin setup status  |
| `POST` | `/api/v1/auth/initialize`          | `PUBLIC` | Create first admin        |
| `GET`  | `/api/v1/auth/oauth/{provider}`    | `PUBLIC` | OAuth login (501 stub)    |
| `GET`  | `/api/v1/auth/callback/{provider}` | `PUBLIC` | OAuth callback (501 stub) |

---

## Architectural Notes

### Why are Memory, Skills, MCP, Models, and Channels PUBLIC?

These management endpoints have no `@require_permission` decorator. In a single-user or intranet deployment (the primary DeerFlow deployment model), these are internal configuration surfaces not intended to be exposed to the public internet — Nginx acts as the perimeter. In multi-user deployments with `auth.enabled: true`, callers still need network access to reach these endpoints, but no per-user ownership check is enforced.

### Why are Threads/Runs PUBLICLY creatable but ownership-checked on read/write?

`POST /api/threads` and `POST /api/threads/search` are open so the `useStream` React hook and the IM channel integrations can create threads without first having a session cookie. Once a thread has an owning `user_id` in `threads_meta`, subsequent read/write/delete operations require that the caller's JWT matches the owner.

### Stateless vs Thread-Scoped Runs

`/api/runs/stream` and `/api/runs/wait` are public "fire and forget" endpoints that auto-create a temporary thread. They are used by direct API callers and the embedded `DeerFlowClient`. Thread-scoped run endpoints (`/api/threads/{id}/runs/*`) are the authoritative path used by the web frontend — they provide full ownership checks, history, and event replay.

### LangGraph Platform Compatibility

The runs, threads, and assistants endpoints implement the LangGraph Platform wire protocol so the `@langchain/langgraph-sdk` React hooks work without modification. The `/api/langgraph/*` Nginx rewrite aliases the entire Gateway as a LangGraph Server.
