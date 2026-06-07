# DeerFlow Technical Study Plan

> **Branch:** `study` | **Approach:** Top-down, from product surface to implementation depth
> **Purpose:** Drive the `/study` custom command. Each section = one study session.
> **Status legend:** `[ ]` Not started · `[~]` In progress · `[x]` Complete

> **Key files table status:** `[ ]` not read · `[~]` reading · `[x]` annotated

---

## Section 01 — Product Overview & Positioning

**Goal:** Understand what DeerFlow _is_ before touching any code.

- What problem does it solve? Who is the target user?
- How does it differentiate from other agent frameworks (AutoGen, CrewAI, OpenDevin)?
- Version history: v1 (Deep Research) → v2 (Super Agent Harness) — what changed and why
- Official website, README, release notes, CONTRIBUTING.md, SECURITY.md

**Key files:**

| Path                 | Status | Notes                                                    |
| -------------------- | ------ | -------------------------------------------------------- |
| `README.md`          | `[x]`  | Project overview, setup instructions, feature highlights |
| `README_zh.md`       | `[x]`  | Chinese-language version of README                       |
| `CONTRIBUTING.md`    | `[x]`  | Contribution guidelines and PR process                   |
| `SECURITY.md`        | `[x]`  | Security policy and vulnerability reporting              |
| `CODE_OF_CONDUCT.md` | `[x]`  | Community standards                                      |
| `Install.md`         | `[x]`  | Detailed installation walkthrough                        |

---

## Section 02 — System Architecture

**Goal:** Build the full mental model of the system before diving into any module.

- Component map: Gateway API, Frontend, Nginx reverse proxy, Provisioner
- Port assignments and traffic flow (2026 → Nginx → 8001/3000)
- How LangGraph integrates as the agent runtime backbone
- Monorepo boundaries: `backend/` vs `frontend/` vs shared `scripts/`
- The harness package (`deerflow.*`) vs the application layer (`app.*`) — why the split?
- Request lifecycle: browser → Nginx → Gateway → RunManager → LangGraph → StreamBridge → SSE → browser

**Key files:**

| Path                                         | Status | Notes                                                                                                                                                         |
| -------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/CLAUDE.md`                          | `[x]`  | Architecture reference: component map, port assignments, request lifecycle                                                                                    |
| `backend/docs/ARCHITECTURE.md`               | `[x]`  | Architecture reference: component map, port assignments, request lifecycle                                                                                    |
| `backend/langgraph.json`                     | `[x]`  | LangGraph graph definition: nodes, edges, entrypoints                                                                                                         |
| `docker/nginx/`                              | `[x]`  | Nginx reverse proxy config: routing rules for port 2026 → 8001/3000                                                                                           |
| `backend/packages/harness/deerflow/runtime/` | `[x]`  | Runtime package (overview depth): journal.py, converters.py, serialization.py, user_context.py + 5 subdirs (checkpointer, events, runs, store, stream_bridge) |

---

## Section 03 — Project Setup & Tooling

**Goal:** Understand how the project is wired together before any code runs.

- Root `Makefile` — targets: `check`, `install`, `dev`, `start`, `stop`
- Backend toolchain: `uv` (dependency manager), `pyproject.toml`, `ruff.toml`
- Frontend toolchain: `pnpm`, `pnpm-workspace.yaml`, `next.config.js`, `tsconfig.json`
- `config.yaml` + `config.example.yaml` — YAML-driven config system
- `extensions_config.json` — MCP servers and skills wiring
- Setup wizard (`scripts/setup_wizard.py`) and doctor (`scripts/doctor.py`)
- VS Code workspace file (`deer-flow.code-workspace`)

**Key files:**

| Path                                      | Status | Notes                                                               |
| ----------------------------------------- | ------ | ------------------------------------------------------------------- |
| `Makefile`                                | `[ ]`  | Root-level build targets: check, install, dev, start, stop          |
| `backend/Makefile`                        | `[ ]`  | Backend-specific build targets                                      |
| `frontend/Makefile`                       | `[ ]`  | Frontend-specific build targets                                     |
| `backend/pyproject.toml`                  | `[ ]`  | Backend Python package metadata, uv dependency config, ruff linting |
| `backend/packages/harness/pyproject.toml` | `[ ]`  | Harness package metadata and dependencies                           |
| `frontend/package.json`                   | `[ ]`  | Frontend npm package config, scripts, and dependencies              |
| `frontend/pnpm-workspace.yaml`            | `[ ]`  | pnpm monorepo workspace config                                      |
| `config.yaml`                             | `[ ]`  | Live YAML config file (models, auth, extensions)                    |
| `extensions_config.json`                  | `[ ]`  | MCP servers and skills wiring registry                              |
| `scripts/setup_wizard.py`                 | `[ ]`  | Interactive setup wizard for first-time config                      |
| `scripts/doctor.py`                       | `[ ]`  | Checks system health and diagnoses config issues                    |
| `scripts/configure.py`                    | `[ ]`  | Programmatic config writer used by setup_wizard                     |

---

## Section 04 — Infrastructure & DevOps

**Goal:** Understand how the system is deployed, containerised, and maintained.

- Docker Compose (dev vs prod): `docker/docker-compose-dev.yaml` vs `docker/docker-compose.yaml`
- Nginx configuration: reverse proxy, path rewriting, `/api/langgraph/*` → Gateway
- Dev entrypoint script (`docker/dev-entrypoint.sh`) — what it bootstraps
- Provisioner container (`docker/provisioner/`) — when and why it runs
- CI/CD: GitHub Actions workflows (`.github/workflows/`)
- Deployment script (`scripts/deploy.sh`, `scripts/serve.sh`, `scripts/start-daemon.sh`)
- Health checks, container cleanup (`scripts/cleanup-containers.sh`)
- Config upgrade path (`scripts/config-upgrade.sh`)

**Key files:**

| Path                             | Status | Notes                                                   |
| -------------------------------- | ------ | ------------------------------------------------------- |
| `docker/docker-compose-dev.yaml` | `[x]`  | Development Docker Compose stack                        |
| `.dockerignore`                  | `[x]`  |                                                         |
| `backend/Dockerfile`             | `[x]`  |                                                         |
| `frontend/Dockerfile`            | `[x]`  |                                                         |
| `docker/docker-compose.yaml`     | `[x]`  | Production Docker Compose stack                         |
| `docker/nginx/`                  | `[x]`  | Nginx config: path rewriting, /api/langgraph/\* routing |
| `docker/dev-entrypoint.sh`       | `[x]`  | Container bootstrap script for dev mode                 |
| `docker/provisioner/`            | `[x]`  | Provisioner container: initial DB setup and seeding     |
| `scripts/deploy.sh`              | `[x]`  | Production deployment script                            |
| `scripts/serve.sh`               | `[ ]`  | Start the production server                             |
| `.github/workflows/`             | `[x]`  | CI/CD pipeline definitions (if present)                 |

---

## Section 05 — Backend: Gateway API (FastAPI)

**Goal:** Understand the HTTP surface area of DeerFlow.

- FastAPI app bootstrap (`app/gateway/app.py`) — lifespan, middleware registration, router mounting
- All routers: agents, artifacts, auth, channels, feedback, mcp, memory, models, runs, skills, suggestions, thread_runs, threads, uploads, assistants_compat
- Dependency injection (`deps.py`) — how config and services flow into handlers
- CSRF middleware (`csrf_middleware.py`) — protection strategy
- Path utilities (`path_utils.py`)
- Services layer (`services.py`) — what it abstracts
- Interaction between Gateway and the LangGraph runtime (how `/api/langgraph/*` is handled)

**Key files:**

| Path                                     | Status | Notes                                                                                         |
| ---------------------------------------- | ------ | --------------------------------------------------------------------------------------------- |
| `backend/app/gateway/app.py`             | `[x]`  | FastAPI app bootstrap: lifespan, middleware, router mounting                                  |
| `backend/app/gateway/routers/`           | `[x]`  | All HTTP route handlers (agents, auth, channels, runs, threads, etc.) — documented separately |
| `backend/app/gateway/deps.py`            | `[x]`  | Dependency injection: config and services flowing into handlers                               |
| `backend/app/gateway/services.py`        | `[x]`  | Service abstraction layer                                                                     |
| `backend/app/gateway/csrf_middleware.py` | `[x]`  | CSRF protection middleware                                                                    |
| `backend/app/gateway/config.py`          | `[x]`  | Gateway server settings (host, port, docs toggle)                                             |
| `backend/app/gateway/path_utils.py`      | `[x]`  | Virtual → physical path resolution                                                            |
| `backend/app/gateway/utils.py`           | `[x]`  | Log injection sanitizer                                                                       |

**Notes files:**

- `notes/modules/05a-gateway-api.md` — app bootstrap, middleware, deps, services (all files except routers/)
- `notes/modules/05b-api-endpoints-overview.md` — overview of all 14 API sets + flat endpoint index
- `notes/modules/05-api-reference/` — per-router detailed API reference (auth, agents, assistants, threads, runs, feedback, uploads, artifacts, suggestions, models, skills, memory, mcp, channels)

---

## Section 06 — Backend: Authentication & Authorization

**Goal:** Understand the full security model around identity.

- Auth providers system (`auth/providers.py`) — pluggable auth backends
- Local provider (`auth/local_provider.py`) — username/password flow
- JWT system (`auth/jwt.py`) — token generation, validation, persistence of auto-generated secrets
- Password hashing (`auth/password.py`)
- Auth middleware (`auth_middleware.py`) — how every request is authenticated
- LangGraph auth bridge (`langgraph_auth.py`) — translating Gateway auth to LangGraph context
- Internal auth (`internal_auth.py`) — service-to-service auth
- Authorization rules (`authz.py`)
- Auth repositories: base interface + SQLite implementation
- Credential file (`auth/credential_file.py`)

**Key files:**

| Path                                     | Status | Notes                                                              |
| ---------------------------------------- | ------ | ------------------------------------------------------------------ |
| `backend/app/gateway/auth/`              | `[x]`  | Auth providers, local auth, JWT, password hashing, credential file |
| `backend/app/gateway/auth_middleware.py` | `[x]`  | Per-request authentication enforcement                             |
| `backend/app/gateway/langgraph_auth.py`  | `[x]`  | Translates Gateway auth context into LangGraph identity            |
| `backend/app/gateway/authz.py`           | `[x]`  | Authorization rules (who can access what)                          |
| `backend/app/gateway/internal_auth.py`   | `[x]`  | Service-to-service auth for internal calls                         |
| `backend/app/gateway/routers/auth.py`    | `[x]`  | Api endpoints for authentication subsystem                         |

**Study order:**

Inside auth/ — primitives first:

1. auth/errors.py — error types used by every other file; read first so the names are familiar when you encounter them downstream.
2. auth/config.py — establishes what auth modes exist (no-auth, local, etc.). Shapes the mental model before reading any logic.
3. auth/models.py — the data shapes (User, AuthContext, Token). Everything else produces or consumes these.
4. auth/password.py — atomic primitive; no dependencies on the other auth files.
5. auth/jwt.py — the token currency. Depends on models.py (signs a User) and config.py (secret key).
6. auth/credential_file.py — persists credentials to disk. Depends on password.py for hashing.
7. auth/repositories/base.py — user CRUD interface. Depends on models.py.
8. auth/repositories/sqlite.py — SQLite implementation of that interface.
9. auth/providers.py — pluggable provider abstraction. Now that you know models, JWT, and repos, the interface contract is clear.
10. auth/local_provider.py — the concrete username/password flow. Pulls in everything above.
11. auth/reset_admin.py — small utility; read right after local_provider.py since it exercises the same code path.

Outside auth/ — enforcement layer:

12. auth_middleware.py — wraps every request; consumes providers and JWT validation.
13. authz.py — who can do what once authenticated (authorization is logically after authentication).
14. internal_auth.py — service-to-service auth; a parallel trust model, easier to read after the user auth pattern is solid.
15. langgraph_auth.py — the final integration point; translates Gateway auth context into LangGraph's identity system.
16. routers/auth.py - Api endpoints for authentication subsystem

---

## Section 07 — Backend: LangGraph Runtime & Run Lifecycle

**Goal:** Understand how agent runs are created, executed, and streamed.

- `RunManager` — the central coordinator of agent runs
- `run_agent()` — how a run is kicked off inside LangGraph
- `StreamBridge` — bridging LangGraph event streams to SSE
- Checkpointer system (`runtime/checkpointer/`) — async state persistence
- Run events (`runtime/events/`) — event types, store, pagination
- Run journal (`runtime/journal.py`) — run audit log
- Runs storage (`runtime/runs/`) — run repository
- Serialization (`runtime/serialization.py`) and converters (`runtime/converters.py`)
- User context (`runtime/user_context.py`) — how `user_id` flows through the system
- Store layer (`runtime/store/`) — key-value persistence for runtime state

**Key files:**

| Path                                                       | Status | Notes                                                                              |
| ---------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------- |
| `backend/packages/harness/deerflow/runtime/`               | `[x]`  | Runtime package root: RunManager, journal, converters, serialization, user_context |
| `backend/packages/harness/deerflow/runtime/checkpointer/`  | `[x]`  | Async state persistence for LangGraph graph checkpoints                            |
| `backend/packages/harness/deerflow/runtime/stream_bridge/` | `[x]`  | Bridges LangGraph event stream to SSE (async_provider, memory, base)               |
| `backend/packages/harness/deerflow/runtime/runs/`          | `[x]`  | RunManager, worker, schemas, run store                                             |
| `backend/packages/harness/deerflow/runtime/events/`        | `[x]`  | Run event types, store, and pagination                                             |
| `backend/packages/harness/deerflow/runtime/store/`         | `[x]`  | KV persistence layer: sync provider, async provider, SQLite utilities              |

**Study order:**

Phase 1 — Primitives (no intra-package dependencies, read first so names are familiar):

1. `runtime/serialization.py` — data serialization primitives used across the runtime
2. `runtime/user_context.py` — how `user_id` is threaded through async context vars
3. `runtime/converters.py` — LangGraph ↔ Gateway type conversions; depends on serialization
4. `runtime/journal.py` — run audit log; lightweight, depends on user_context

Phase 2 — Checkpointer (LangGraph graph state persistence):

5. `runtime/checkpointer/provider.py` — sync checkpointer interface and SQLite impl
6. `runtime/checkpointer/async_provider.py` — async wrapper over the sync provider

Phase 3 — Store (key-value runtime persistence):

7. `runtime/store/provider.py` — sync KV store interface
8. `runtime/store/_sqlite_utils.py` — SQLite helpers shared by the store impls
9. `runtime/store/async_provider.py` — async KV store (wraps provider with thread executor)

Phase 4 — Run Events (event sourcing layer for a run's history):

10. `runtime/events/store/base.py` — abstract event store interface
11. `runtime/events/store/memory.py` — in-memory impl (used in tests)
12. `runtime/events/store/jsonl.py` — JSONL file-backed impl
13. `runtime/events/store/db.py` — DB-backed impl (default in production)

Phase 5 — Run Storage (CRUD for run records):

14. `runtime/runs/schemas.py` — run data shapes (input, output, status enums)
15. `runtime/runs/store/base.py` — abstract run store interface
16. `runtime/runs/store/memory.py` — in-memory run store (used in tests)

Phase 6 — Stream Bridge (LangGraph events → SSE):

17. `runtime/stream_bridge/base.py` — abstract stream bridge interface
18. `runtime/stream_bridge/memory.py` — in-memory stream (write side + read side)
19. `runtime/stream_bridge/async_provider.py` — async provider coordinating stream lifecycle

Phase 7 — Run Orchestration (the top of the call stack):

20. `runtime/runs/worker.py` — executes a single run inside LangGraph
21. `runtime/runs/manager.py` — RunManager: the central coordinator (launch, cancel, stream)

---

## Section 08 — Backend: Lead Agent

**Goal:** Understand the core AI agent that handles user requests.

- Agent factory (`agents/factory.py`) — how the LangGraph graph is constructed
- Lead agent directory (`agents/lead_agent/`) — system prompt, agent definition
- Thread state (`agents/thread_state.py`) — the full state schema flowing through the graph
- Agent features (`agents/features.py`) — feature flags controlling agent behaviour
- How the agent graph nodes and edges are wired

**Key files:**

| Path                                                            | Status | Notes                                                                                  |
| --------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------- |
| `backend/packages/harness/deerflow/agents/thread_state.py`      | `[x]`  | Full state schema flowing through the LangGraph graph                                  |
| `backend/packages/harness/deerflow/agents/features.py`          | `[x]`  | Feature flags controlling agent behaviour                                              |
| `backend/packages/harness/deerflow/agents/lead_agent/prompt.py` | `[x]`  | System prompt assembly; primed eagerly at import time                                  |
| `backend/packages/harness/deerflow/agents/lead_agent/agent.py`  | `[x]`  | LangGraph node: calls model, handles tool calls, returns state updates                 |
| `backend/packages/harness/deerflow/agents/factory.py`           | `[x]`  | Wires the full LangGraph graph: nodes, edges, middleware wrapping                      |
| `backend/packages/harness/deerflow/agents/__init__.py`          | `[x]`  | Package bootstrap: public API exports + eager skills cache priming on LangGraph import |

**Study order:**

Phase 1 — Primitives (data shapes and flags, no agent logic yet):

1. `agents/thread_state.py` — full state schema; read first so field names are familiar everywhere else
2. `agents/features.py` — feature flags that alter agent behaviour; shapes the mental model before reading any conditional logic

Phase 2 — Lead agent internals (bottom-up within `lead_agent/`):

3. `agents/lead_agent/prompt.py` — system prompt assembly; depends on thread_state and features
4. `agents/lead_agent/agent.py` — the LangGraph node: calls model, handles tool calls, returns state updates

Phase 3 — Graph assembly:

5. `agents/factory.py` — wires the full LangGraph graph: nodes, edges, middleware wrapping
6. `agents/__init__.py` — package bootstrap: understand what LangGraph sees on import and why the skills cache is primed here

---

## Section 09 — Backend: Middleware Pipeline

**Goal:** Understand every transformation layer the agent goes through.

- Middleware architecture: how middlewares wrap the agent
- Two-stage assembly: Stage 1 (`_build_runtime_middlewares()` in `tool_error_handling_middleware.py`) builds positions 1–8; Stage 2 (`_build_middlewares()` in `lead_agent/agent.py`) appends positions 9–18
- Complete list of middlewares (18 when Guardrail is disabled; 19 when enabled):
  - Sandbox infrastructure: ThreadData, Uploads, SandboxMiddleware
  - Model call wrappers: DanglingToolCall, LLMErrorHandling
  - Tool execution guards: GuardrailMiddleware (lives in `guardrails/`, not `agents/middlewares/`), SandboxAudit, ToolErrorHandling, DeferredToolFilter
  - Before-agent context: DynamicContext
  - Before-model injection: Summarization, ViewImage
  - After-model processing (fires in reverse): LoopDetection, SubagentLimit, Title, TokenUsage, Todo
  - After-agent teardown: Memory (SandboxMiddleware also has after_agent release)
- `ClarificationMiddleware` is pinned last (pos 18) and uses `wrap_tool_call` — it intercepts `ask_clarification` as the innermost tool wrapper, returning `Command(goto=END)` without calling `handler(request)`

**Key files:**

| Path                                                                                     | Status | Notes                                                                                                                                                                                                                                                                                   |
| ---------------------------------------------------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/packages/harness/deerflow/agents/middlewares/`                                  | `[x]`  | all phases annotated: phases 2–6 (thread_data, uploads, dynamic_context; dangling_tool_call, llm_error_handling; sandbox_audit, deferred_tool_filter, clarification; summarization, view_image; loop_detection, subagent_limit, title, token_usage, todo) + phase 7 (memory_middleware) |
| `backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py` | `[x]`  | Stage 1 assembly + ToolErrorHandlingMiddleware class (pos 8) annotated                                                                                                                                                                                                                  |
| `backend/packages/harness/deerflow/guardrails/`                                          | `[x]`  | GuardrailMiddleware, provider.py, builtin.py all annotated                                                                                                                                                                                                                              |
| `backend/packages/harness/deerflow/sandbox/middleware.py`                                | `[x]`  | SandboxMiddleware — pos 3; has both `before_agent` (acquire) and `after_agent` (release)                                                                                                                                                                                                |
| `backend/packages/harness/deerflow/config/loop_detection_config.py`                      | `[x]`  | Config for LoopDetectionMiddleware                                                                                                                                                                                                                                                      |
| `backend/packages/harness/deerflow/config/summarization_config.py`                       | `[x]`  | Config for SummarizationMiddleware                                                                                                                                                                                                                                                      |
| `backend/packages/harness/deerflow/config/title_config.py`                               | `[x]`  | Config for TitleMiddleware                                                                                                                                                                                                                                                              |
| `backend/packages/harness/deerflow/config/token_usage_config.py`                         | `[x]`  | Config for TokenUsageMiddleware                                                                                                                                                                                                                                                         |

**Study order:**

Phase 1 — Assembly (understand chain wiring before reading individual middlewares):

1. `agents/middlewares/tool_error_handling_middleware.py` — focus on `_build_runtime_middlewares()` and `build_lead_runtime_middlewares()`; Stage 1 builds positions 1–8
2. `agents/lead_agent/agent.py` — focus on `_build_middlewares()`; Stage 2 appends positions 9–18 (already annotated in §08, re-read this function specifically)
3. `agents/middlewares/__init__.py` — public exports; confirms the complete set

Phase 2 — Before-agent (outer lifecycle, runs once at invocation start, forward order 1→9):

1. `thread_data_middleware.py` [pos 1] — creates per-thread user directories
2. `uploads_middleware.py` [pos 2] — injects uploaded files into state
3. `sandbox/middleware.py` [pos 3] — acquires sandbox; also releases in `after_agent`
4. `dynamic_context_middleware.py` [pos 9] — injects current date + memory as system reminder

Phase 3 — Model call wrappers (wrap_model_call, surrounds each LLM invocation):

1. `dangling_tool_call_middleware.py` [pos 4] — patches tool_call/ToolMessage gaps
2. `llm_error_handling_middleware.py` [pos 5] — retries transient LLM API errors

Phase 4 — Tool execution guards (wrap_tool_call, surrounds each tool invocation):

1. `guardrails/provider.py` → `guardrails/builtin.py` → `guardrails/middleware.py` [pos 6, optional]
2. `sandbox_audit_middleware.py` [pos 7] — security logging for shell/file ops
3. `tool_error_handling_middleware.py` class [pos 8] — revisit the middleware class itself after Phase 1 covered the assembly functions
4. `deferred_tool_filter_middleware.py` [pos 16] — also has `before_model`; read here since tool guard concern dominates
5. `clarification_middleware.py` [pos Last] — innermost `wrap_tool_call`; intercepts `ask_clarification`, returns `Command(goto=END)` without executing the tool

Phase 5 — Before-model (per-turn injection, runs every LLM call, forward order):

1. `summarization_middleware.py` + `config/summarization_config.py` [pos 10]
2. `view_image_middleware.py` [pos 15] — injects base64 images before model call

Phase 6 — After-model (post-response processing; fires in reverse chain order, read high→low):

1. `loop_detection_middleware.py` + `config/loop_detection_config.py` [pos 17] — fires 1st; hard-stop on detected loops
2. `subagent_limit_middleware.py` [pos 16] — fires 2nd; truncates excess task tool calls
3. `title_middleware.py` + `config/title_config.py` [pos 13] — fires 5th; auto-generates thread title
4. `token_usage_middleware.py` + `config/token_usage_config.py` [pos 12] — fires 6th; records usage metrics
5. `todo_middleware.py` [pos 11] — fires 7th; also has before_model + after_agent hooks

Phase 6 notes file: `notes/modules/09f-after-model-middlewares.md`

Phase 7 — After-agent teardown (runs once after the full agent run completes):

1. `memory_middleware.py` [pos 14] — queues conversation for async memory update (SandboxMiddleware's after_agent covered in Phase 2)

---

## Section 10 — Backend: Memory System

**Goal:** Understand how DeerFlow builds persistent per-user knowledge.

- Memory updater (`agents/memory/updater.py`) — LLM-driven fact extraction
- Memory queue (`agents/memory/queue.py`) — debounce strategy and thread-safety
- Memory prompt (`agents/memory/prompt.py`) — extraction prompt design
- Memory storage (`agents/memory/storage.py`) — per-user file isolation model
- Data structure: `workContext`, `personalContext`, `topOfMind`, facts with categories/confidence
- How memory is injected into the system prompt at inference time
- Per-user isolation path: `users/{user_id}/memory.json`
- Migration path for legacy installations

**Key files:**

| Path                                                                    | Status | Notes                                                         |
| ----------------------------------------------------------------------- | ------ | ------------------------------------------------------------- |
| `backend/packages/harness/deerflow/agents/memory/prompt.py`             | `[x]`  | Extraction prompt; defines the LLM contract for fact mining   |
| `backend/packages/harness/deerflow/agents/memory/storage.py`            | `[x]`  | Per-user file isolation; data structure and persistence model |
| `backend/packages/harness/deerflow/agents/memory/message_processing.py` | `[x]`  | Pre-processes conversation messages before extraction         |
| `backend/packages/harness/deerflow/agents/memory/queue.py`              | `[x]`  | Debounce strategy and thread-safety for the update write path |
| `backend/packages/harness/deerflow/agents/memory/updater.py`            | `[x]`  | LLM-driven fact extraction; top-level coordinator             |
| `backend/packages/harness/deerflow/agents/memory/summarization_hook.py` | `[x]`  | Hooks memory updates into the summarization pipeline          |

**Study order:**

Phase 1 — Primitives (data shapes, storage, and message pre-processing):

1. `agents/memory/prompt.py` — extraction prompt; read first so the LLM contract (what facts are extracted and how) is clear before reading any logic
2. `agents/memory/storage.py` — per-user file isolation; defines the `workContext`/`personalContext`/`topOfMind` data shapes that everything else reads and writes
3. `agents/memory/message_processing.py` — pre-processes raw conversation messages into a form the extractor can consume

Phase 2 — Orchestration (the write path):

4. `agents/memory/queue.py` — debounce strategy and thread-safety; gates how and when updates are triggered
5. `agents/memory/updater.py` — LLM-driven extraction; top-level coordinator that ties prompt, storage, and queue together
6. `agents/memory/summarization_hook.py` — hooks memory updates into the summarization middleware lifecycle; read last as the integration point with the wider agent pipeline

---

## Section 11 — Backend: Subagents

**Goal:** Understand how DeerFlow delegates to specialised sub-agents.

- Subagent executor (`subagents/executor.py`) — background execution engine
- Subagent registry (`subagents/registry.py`) — how agents are discovered
- Subagent config (`subagents/config.py`)
- Token collector (`subagents/token_collector.py`) — cross-agent token accounting
- Built-in subagents (`subagents/builtins/`) — general-purpose, bash agents
- How the lead agent invokes subagents (tool call pattern)
- Security: prompt injection prevention, timeout config, skill filtering

**Key files:**

| Path                                                                      | Status | Notes                                               |
| ------------------------------------------------------------------------- | ------ | --------------------------------------------------- |
| `backend/packages/harness/deerflow/subagents/config.py`                   | `[x]`  | Subagent configuration shapes                       |
| `backend/packages/harness/deerflow/subagents/token_collector.py`          | `[x]`  | Cross-agent token accounting primitive              |
| `backend/packages/harness/deerflow/subagents/registry.py`                 | `[x]`  | Agent discovery and registration; depends on config |
| `backend/packages/harness/deerflow/subagents/executor.py`                 | `[x]`  | Background execution engine; top-level coordinator  |
| `backend/packages/harness/deerflow/subagents/builtins/general_purpose.py` | `[x]`  | General-purpose built-in subagent definition        |
| `backend/packages/harness/deerflow/subagents/builtins/bash_agent.py`      | `[x]`  | Bash built-in subagent definition                   |

**Study order:**

Phase 1 — Primitives (data shapes and discovery, no execution logic yet):

1. `subagents/config.py` — subagent configuration shapes; read first so field names are familiar everywhere else
2. `subagents/token_collector.py` — cross-agent token accounting; lightweight primitive with no major intra-package dependencies
3. `subagents/registry.py` — how subagents are discovered and registered; depends on config

Phase 2 — Execution and builtins (runtime and built-in agent implementations):

1. `subagents/builtins/general_purpose.py` — general-purpose subagent; simpler than bash, read first
2. `subagents/builtins/bash_agent.py` — bash subagent; more specialised form, read after general_purpose
3. `subagents/executor.py` — background execution engine; top-level coordinator that ties config, registry, and builtins together

---

## Section 12 — Backend: Tools System

**Goal:** Understand how tools are defined, discovered, and executed.

- Tool types (`tools/types.py`) — ToolDef, ToolResult abstractions
- Tools registry (`tools/tools.py`) — how tools are assembled per-run
- Tool sync (`tools/sync.py`) — keeping tools in sync with config
- Skill management tool (`tools/skill_manage_tool.py`)
- Built-in tools (`tools/builtins/`) — `present_files`, `ask_clarification`, `view_image`
- Tool deduplication logic
- Tool search (`deerflow/config/tool_search_config.py`)
- Tool output truncation (truncation middleware + config)

**Key files:**

| Path                                                                        | Status | Notes                                                                                |
| --------------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------ |
| `backend/packages/harness/deerflow/tools/__init__.py`                       | `[x]`  | Package public API exports                                                           |
| `backend/packages/harness/deerflow/tools/types.py`                          | `[x]`  | ToolDef and ToolResult abstractions                                                  |
| `backend/packages/harness/deerflow/tools/tools.py`                          | `[x]`  | Tools registry; assembles the per-run tool set with deduplication                    |
| `backend/packages/harness/deerflow/tools/sync.py`                           | `[x]`  | Keeps tools in sync with config and skill changes                                    |
| `backend/packages/harness/deerflow/tools/skill_manage_tool.py`              | `[x]`  | Built-in tool for listing, enabling, and disabling skills                            |
| `backend/packages/harness/deerflow/tools/builtins/clarification_tool.py`    | `[x]`  | `ask_clarification` tool — prompts for input; intercepted by ClarificationMiddleware |
| `backend/packages/harness/deerflow/tools/builtins/present_file_tool.py`     | `[x]`  | `present_files` tool — surfaces sandbox files to the user                            |
| `backend/packages/harness/deerflow/tools/builtins/view_image_tool.py`       | `[x]`  | `view_image` tool — loads an image for model inspection                              |
| `backend/packages/harness/deerflow/tools/builtins/task_tool.py`             | `[x]`  | Task management tool; create and update tasks within a thread                        |
| `backend/packages/harness/deerflow/tools/builtins/tool_search.py`           | `[x]`  | Semantic tool search for dynamic tool discovery                                      |
| `backend/packages/harness/deerflow/tools/builtins/invoke_acp_agent_tool.py` | `[x]`  | Invokes an ACP agent as a tool call; integrates with the ACP config layer            |
| `backend/packages/harness/deerflow/tools/builtins/setup_agent_tool.py`      | `[x]`  | Tool for creating and configuring custom agents                                      |
| `backend/packages/harness/deerflow/tools/builtins/update_agent_tool.py`     | `[x]`  | Tool for updating existing custom agent definitions                                  |

**Study order:**

Phase 1 — Primitives (data shapes and package API, read first so type names are familiar):

1. `tools/types.py` — ToolDef and ToolResult abstractions; read first so the type vocabulary is clear before reading any registry or tool implementation
2. `tools/__init__.py` — package public exports; confirms what callers outside the package see

Phase 2 — Registry and sync (how tools are assembled per-run):

1. `tools/tools.py` — tools registry; the per-run tool assembly logic including deduplication; depends on types.py
2. `tools/sync.py` — keeps tool state in sync with config changes; depends on tools.py
3. `tools/skill_manage_tool.py` — built-in tool for listing/enabling/disabling skills; a tool that manages other tools

Phase 3 — Built-in tools (concrete tool implementations; read in ascending complexity):

1. `tools/builtins/clarification_tool.py` — `ask_clarification`; the simplest built-in; read first to see the tool construction pattern
2. `tools/builtins/present_file_tool.py` — `present_files`; surfaces sandbox files to the user
3. `tools/builtins/view_image_tool.py` — `view_image`; loads base64 images into the model context
4. `tools/builtins/task_tool.py` — task management within a thread
5. `tools/builtins/tool_search.py` — semantic tool search for dynamic tool discovery
6. `tools/builtins/invoke_acp_agent_tool.py` — invokes an ACP agent as a tool call; read after task_tool.py since both follow the async invocation pattern
7. `tools/builtins/setup_agent_tool.py` — creates and configures custom agents
8. `tools/builtins/update_agent_tool.py` — updates existing custom agent definitions; read after setup_agent_tool.py as they share the same pattern

---

## Section 13 — Backend: Skills System

**Goal:** Understand the extensible skills layer (DeerFlow's plugin system).

- Skills as YAML-defined tool wrappers — what a skill looks like
- Parser (`skills/parser.py`) — how skills are read from disk
- Installer (`skills/installer.py`) — how skills are installed/activated
- Security scanner (`skills/security_scanner.py`) — what it checks and blocks
- Skill validation (`skills/validation.py`)
- Tool policy (`skills/tool_policy.py`)
- Skill storage (`skills/storage/`) — where skills live on disk
- Skill types (`skills/types.py`)
- Bundled skills (`skills/public/`) vs custom skills
- Skills evolution config (`config/skill_evolution_config.py`)
- The `extensions_config.json` wiring

**Key files:**

| Path                                        | Status | Notes                                                                                          |
| ------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------- |
| `backend/packages/harness/deerflow/skills/` | `[ ]`  | Skills subsystem: parser, installer, security scanner, validation, tool policy, storage, types |
| `skills/public/`                            | `[ ]`  | Bundled built-in skills (YAML definitions)                                                     |
| `backend/tests/test_skills_*.py`            | `[ ]`  | Skills tests (glob pattern)                                                                    |

---

## Section 14 — Backend: MCP Integration

**Goal:** Understand how DeerFlow connects to Model Context Protocol servers.

- MCP client (`mcp/client.py`) — connection and protocol handling
- MCP tools (`mcp/tools.py`) — how MCP tools become LangGraph tools
- MCP cache (`mcp/cache.py`) — tool schema caching strategy
- MCP OAuth (`mcp/oauth.py`) — auth flow for remote MCP servers
- MCP router (`app/gateway/routers/mcp.py`) — HTTP API for MCP management
- How `extensions_config.json` configures MCP servers

**Key files:**

| Path                                     | Status | Notes                                     |
| ---------------------------------------- | ------ | ----------------------------------------- |
| `backend/packages/harness/deerflow/mcp/` | `[ ]`  | MCP client, tools, cache, OAuth           |
| `backend/app/gateway/routers/mcp.py`     | `[ ]`  | HTTP router for MCP server management API |
| `backend/tests/test_mcp_*.py`            | `[ ]`  | MCP integration tests (glob pattern)      |

---

## Section 15 — Backend: Sandbox

**Goal:** Understand how DeerFlow executes untrusted code safely.

- Sandbox abstraction (`sandbox/sandbox.py`) — the interface contract
- Sandbox provider (`sandbox/sandbox_provider.py`) — factory and provider selection
- Local sandbox (`sandbox/local/`) — filesystem-based execution
- Sandbox tools (`sandbox/tools.py`) — `bash`, `ls`, `read_file`, `write_file`, `str_replace`
- Sandbox middleware (`sandbox/middleware.py`) — lifecycle management per-run
- Security module (`sandbox/security.py`) — what's blocked and why
- File operation lock (`sandbox/file_operation_lock.py`) — concurrency safety
- Sandbox search (`sandbox/search.py`)
- Community sandbox (`community/aio_sandbox/`) — remote/async sandbox alternative
- Sandbox mode detection (Docker vs local)

**Notes:**

- Study this as well `docker/provisioner/` in section 4

**Key files:**

| Path                                                       | Status | Notes                                                                         |
| ---------------------------------------------------------- | ------ | ----------------------------------------------------------------------------- |
| `backend/packages/harness/deerflow/sandbox/`               | `[ ]`  | Sandbox abstraction, provider, local impl, tools, middleware, security, locks |
| `backend/packages/harness/deerflow/community/aio_sandbox/` | `[ ]`  | Remote async sandbox alternative                                              |
| `backend/tests/test_aio_sandbox*.py`                       | `[ ]`  | AIO sandbox tests (glob pattern)                                              |
| `backend/tests/test_sandbox_*.py`                          | `[ ]`  | Sandbox unit and security tests (glob pattern)                                |

---

## Section 16 — Backend: Model Layer

**Goal:** Understand how DeerFlow abstracts across LLM providers.

- Model factory (`models/factory.py`) — how model instances are created from config
- Provider implementations:
  - `claude_provider.py` — Anthropic/Claude (with prompt caching, OAuth billing)
  - `patched_openai.py` — OpenAI compatibility fixes
  - `patched_deepseek.py` — DeepSeek-specific patches
  - `patched_minimax.py` — Minimax patches
  - `vllm_provider.py` — self-hosted vLLM
  - `mindie_provider.py` — Huawei Mindie
  - `openai_codex_provider.py` — Codex
- Credential loader (`models/credential_loader.py`) — per-user or global API keys
- Thinking/reasoning mode support
- Model config (`config/model_config.py`)

**Key files:**

| Path                                        | Status | Notes                                                                                   |
| ------------------------------------------- | ------ | --------------------------------------------------------------------------------------- |
| `backend/packages/harness/deerflow/models/` | `[ ]`  | Model factory, provider impls (Claude, OpenAI, DeepSeek, vLLM, etc.), credential loader |
| `backend/tests/test_model_*.py`             | `[ ]`  | Model layer tests (glob pattern)                                                        |
| `backend/tests/test_patched_*.py`           | `[ ]`  | Provider-specific patch tests (glob pattern)                                            |

---

## Section 17 — Backend: Config System

**Goal:** Understand the full configuration architecture.

- `app_config.py` — root config loader, YAML parsing, hot reload
- Every config module in `deerflow/config/` and what it controls:
  - `agents_config.py`, `agents_api_config.py`
  - `acp_config.py` (Agent Collaboration Protocol)
  - `checkpointer_config.py`
  - `database_config.py`
  - `extensions_config.py`
  - `guardrails_config.py`
  - `loop_detection_config.py`
  - `memory_config.py`
  - `model_config.py`
  - `runtime_paths.py`, `paths.py`
  - `run_events_config.py`
  - `sandbox_config.py`
  - `skill_evolution_config.py`
  - `skills_config.py`
  - `stream_bridge_config.py`
  - `subagents_config.py`
  - `summarization_config.py`
  - `title_config.py`
  - `token_usage_config.py`
  - `tool_config.py`, `tool_search_config.py`
  - `tracing_config.py`
- Config versioning and upgrade path

**Key files:**

| Path                                        | Status | Notes                                                                                                       |
| ------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------- |
| `backend/packages/harness/deerflow/config/` | `[ ]`  | All config modules: agents, database, extensions, guardrails, memory, model, sandbox, skills, tracing, etc. |
| `config.yaml`                               | `[ ]`  | Live config file — the user-facing face of the config system                                                |
| `config.example.yaml`                       | `[ ]`  | Annotated example showing all available config options                                                      |

---

## Section 18 — Backend: Persistence Layer

**Goal:** Understand how DeerFlow stores data durably.

- Persistence engine (`persistence/engine.py`) — SQLAlchemy setup, connection pooling
- Base models (`persistence/base.py`)
- ORM models (`persistence/models/`)
- Repositories: runs, thread_meta, user, feedback
- Migrations (`persistence/migrations/`) — Alembic or manual?
- JSON compatibility (`persistence/json_compat.py`)
- Per-user data isolation at the DB level
- SQLite as the default database

**Key files:**

| Path                                             | Status | Notes                                                                             |
| ------------------------------------------------ | ------ | --------------------------------------------------------------------------------- |
| `backend/packages/harness/deerflow/persistence/` | `[ ]`  | SQLAlchemy engine, base models, ORM models, repositories, migrations, JSON compat |
| `backend/tests/test_persistence_*.py`            | `[ ]`  | Persistence layer tests (glob pattern)                                            |
| `backend/tests/test_run_repository.py`           | `[ ]`  | Run repository tests                                                              |
| `backend/tests/test_thread_meta_repo.py`         | `[ ]`  | Thread metadata repository tests                                                  |

---

## Section 19 — Backend: Channels (IM Integrations)

**Goal:** Understand how DeerFlow talks to messaging platforms.

- Channel base class (`channels/base.py`) — the interface all channels implement
- Channel manager (`channels/manager.py`) — registration and lifecycle
- Message bus (`channels/message_bus.py`) — internal pub-sub
- Channel service (`channels/service.py`) — orchestration layer
- Channel store (`channels/store.py`)
- Command handling (`channels/commands.py`) — `/new`, `/status`, etc.
- Per-platform implementations:
  - Slack (`slack.py`) — bot token + app token, `runs.wait()` pattern
  - Discord (`discord.py`) — mention-only mode, thread routing, typing indicators
  - Telegram (`telegram.py`)
  - Feishu/Lark (`feishu.py`) — card streaming, `is_final` patch flow
  - DingTalk (`dingtalk.py`) — AI Card streaming mode
  - WeChat (`wechat.py`)
  - WeCom/WeWork (`wecom.py`)

**Key files:**

| Path                                      | Status | Notes                                                                                                  |
| ----------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------ |
| `backend/app/channels/`                   | `[ ]`  | All channel implementations: base, manager, message bus, service, store, commands, 7 platform adapters |
| `backend/app/gateway/routers/channels.py` | `[ ]`  | HTTP router for channel management API                                                                 |
| `backend/tests/test_channels.py`          | `[ ]`  | General channel tests                                                                                  |
| `backend/tests/test_discord_channel.py`   | `[ ]`  | Discord-specific tests                                                                                 |
| `backend/tests/test_dingtalk_channel.py`  | `[ ]`  | DingTalk-specific tests                                                                                |
| `backend/tests/test_feishu_parser.py`     | `[ ]`  | Feishu message parser tests                                                                            |

---

## Section 20 — Backend: Tracing & Observability

**Goal:** Understand how DeerFlow is monitored and debugged in production.

- Tracing factory (`tracing/factory.py`) — LangSmith and Langfuse integration
- Tracing config (`config/tracing_config.py`)
- Logging configuration — log levels, structured logging
- Run journal (`runtime/journal.py`) — per-run audit trail
- Blocking I/O detector (`tests/support/detectors/blocking_io.py`) — async hygiene enforcement
- `scripts/tool-error-degradation-detection.sh`

**Key files:**

| Path                                         | Status | Notes                                               |
| -------------------------------------------- | ------ | --------------------------------------------------- |
| `backend/packages/harness/deerflow/tracing/` | `[ ]`  | Tracing factory: LangSmith and Langfuse integration |
| `backend/tests/test_tracing_*.py`            | `[ ]`  | Tracing tests (glob pattern)                        |

---

## Section 21 — Backend: Community Integrations

**Goal:** Understand the pluggable search and tool ecosystem.

- Tavily (`community/tavily/`) — web search
- Jina AI (`community/jina_ai/`) — reader/embeddings
- Firecrawl (`community/firecrawl/`) — web scraping
- Serper (`community/serper/`) — Google Search API
- Exa (`community/exa/`) — neural search
- InfoQuest (`community/infoquest/`) — BytePlus search/crawl
- DuckDuckGo search (`community/ddg_search/`)
- Image search (`community/image_search/`)
- AIO sandbox (`community/aio_sandbox/`) — remote async sandbox alternative

**Key files:**

| Path                                           | Status | Notes                                                                                                       |
| ---------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------- |
| `backend/packages/harness/deerflow/community/` | `[ ]`  | All community integrations: Tavily, Jina, Firecrawl, Serper, Exa, InfoQuest, DDG, image search, AIO sandbox |
| `backend/tests/test_exa_tools.py`              | `[ ]`  | Exa neural search tool tests                                                                                |
| `backend/tests/test_firecrawl_tools.py`        | `[ ]`  | Firecrawl web scraping tests                                                                                |
| `backend/tests/test_serper_tools.py`           | `[ ]`  | Serper Google Search API tests                                                                              |

---

## Section 22 — Frontend: Architecture & Project Structure

**Goal:** Build a mental model of the Next.js frontend before reading any component code.

- Next.js App Router structure: `app/`, `[lang]/`, `(auth)/`, `workspace/`, `api/`
- Internationalisation (`core/i18n/`, `src/content/en|zh/`, `[lang]` route segment)
- Environment variable setup (`src/env.js`)
- Styling: Tailwind CSS, `postcss.config.js`, `globals.css`
- Component system: shadcn/ui (`components.json`), custom components
- TypeScript configuration (`tsconfig.json`)
- ESLint (`eslint.config.js`) and Prettier (`prettier.config.js`)
- MDX support (`mdx-components.ts`, blog system)

**Key files:**

| Path                      | Status | Notes                                                                      |
| ------------------------- | ------ | -------------------------------------------------------------------------- |
| `frontend/src/app/`       | `[ ]`  | Next.js App Router root: [lang] routing, auth pages, workspace, API routes |
| `frontend/next.config.js` | `[ ]`  | Next.js build config: MDX, env vars, rewrites                              |
| `frontend/tsconfig.json`  | `[ ]`  | TypeScript config                                                          |
| `frontend/src/env.js`     | `[ ]`  | Environment variable schema and validation                                 |

---

## Section 23 — Frontend: Core Modules

**Goal:** Understand the business logic layer of the frontend.

- API layer (`core/api/`) — HTTP client, stream handling, type definitions
- Auth (`core/auth/`) — gateway config, auth state management
- Thread management (`core/threads/`) — CRUD, message merging, token usage
- Message system (`core/messages/`) — message models, usage tracking
- Settings (`core/settings/`) — local settings persistence
- Models (`core/models/`) — LLM model selection
- Tasks (`core/tasks/`) — task tracking inside threads
- Todos (`core/todos/`)
- Memory (`core/memory/`) — memory display
- Artifacts (`core/artifacts/`) — file/artifact handling
- Uploads (`core/uploads/`)
- Skills (`core/skills/`) — skill management UI
- MCP (`core/mcp/`) — MCP server management UI
- Agents (`core/agents/`) — custom agent UI
- Config (`core/config/`) — runtime config from backend
- Notification (`core/notification/`)
- Blog (`core/blog/`)
- Rehype plugins (`core/rehype/`)
- Utils (`core/utils/`)

**Key files:**

| Path                 | Status | Notes                                                                                                                                                                                |
| -------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `frontend/src/core/` | `[ ]`  | All business logic modules: api, auth, threads, messages, settings, models, tasks, todos, memory, artifacts, uploads, skills, mcp, agents, config, notification, blog, rehype, utils |

---

## Section 24 — Frontend: Workspace UI & UX

**Goal:** Understand how the chat interface is built and rendered.

- Workspace layout (`src/app/workspace/`) — page structure
- Chat components (`src/components/workspace/`) — message list, input area, sidebar
- AI elements (`src/components/ai-elements/`) — thinking indicators, tool call displays
- Landing page (`src/components/landing/`)
- Thread history sidebar — pagination, search
- Artifact viewer — file display, code highlighting
- Global keyboard shortcuts (`hooks/use-global-shortcuts.ts`)
- Mobile responsive layout (`hooks/use-mobile.ts`)

**Key files:**

| Path                                   | Status | Notes                                                          |
| -------------------------------------- | ------ | -------------------------------------------------------------- |
| `frontend/src/components/workspace/`   | `[ ]`  | Chat UI components: message list, input area, sidebar          |
| `frontend/src/app/workspace/`          | `[ ]`  | Workspace page layout                                          |
| `frontend/src/components/ai-elements/` | `[ ]`  | AI-specific rendering: thinking indicators, tool call displays |

---

## Section 25 — Frontend: Real-time Streaming & Rendering

**Goal:** Understand how streaming AI responses reach the browser.

- Streamdown (`core/streamdown/`) — custom streaming markdown renderer
- SSE stream parsing (`core/api/` — stream mode)
- How tool calls are rendered incrementally
- Rehype plugins for AI content (`core/rehype/`)
- Message deduplication after restore
- IME-safe input (`lib/ime.ts`) — handling CJK input methods

**Key files:**

| Path                                                  | Status | Notes                              |
| ----------------------------------------------------- | ------ | ---------------------------------- |
| `frontend/src/core/streamdown/`                       | `[ ]`  | Custom streaming markdown renderer |
| `frontend/src/core/api/`                              | `[ ]`  | HTTP client and SSE stream parsing |
| `frontend/tests/unit/core/streamdown/plugins.test.ts` | `[ ]`  | Streamdown plugin unit tests       |

---

## Section 26 — Testing Strategy & Patterns

**Goal:** Understand how DeerFlow's quality is maintained.

- Backend: pytest setup (`backend/tests/conftest.py`), fixture patterns
- Test categories: unit, integration, e2e, live (with real LLMs)
- Helper patterns: `_agent_e2e_helpers.py`, `_router_auth_helpers.py`
- Blocking I/O detection in async tests (`support/detectors/blocking_io.py`)
- Frontend: Vitest for unit tests (`vitest.config.ts`)
- Frontend: Playwright for E2E (`playwright.config.ts`, `tests/e2e/`)
- Mock API strategy (`tests/e2e/utils/mock-api.ts`)
- What's NOT tested and why (gaps to understand)

**Key files:**

| Path                            | Status | Notes                                            |
| ------------------------------- | ------ | ------------------------------------------------ |
| `backend/tests/conftest.py`     | `[ ]`  | pytest fixtures, test setup, async configuration |
| `frontend/vitest.config.ts`     | `[ ]`  | Vitest unit test config                          |
| `frontend/playwright.config.ts` | `[ ]`  | Playwright E2E test config                       |
| `frontend/tests/`               | `[ ]`  | Frontend test suite: unit tests + E2E tests      |

---

## Section 27 — Security Design

**Goal:** Understand the full security posture of DeerFlow.

- Authentication model (JWT, local, no-auth mode)
- CSRF protection strategy
- Sandbox security (`sandbox/security.py`) — blocked paths, commands
- Skill security scanner — what malicious skills look like
- Subagent prompt injection prevention
- Memory prompt injection defences
- Guardrails system (`guardrails/`) — content filtering
- Internal auth (service-to-service)
- Per-user data isolation (memory, threads, agents, paths)
- Security notice in README

**Key files:**

| Path                                                           | Status | Notes                                               |
| -------------------------------------------------------------- | ------ | --------------------------------------------------- |
| `backend/app/gateway/csrf_middleware.py`                       | `[ ]`  | CSRF protection strategy                            |
| `backend/packages/harness/deerflow/sandbox/security.py`        | `[ ]`  | Blocked paths, commands, and sandbox security rules |
| `backend/packages/harness/deerflow/skills/security_scanner.py` | `[ ]`  | Detects malicious patterns in skill definitions     |
| `backend/packages/harness/deerflow/guardrails/`                | `[ ]`  | Content filtering and guardrail system              |
| `backend/tests/test_sandbox_tools_security.py`                 | `[ ]`  | Sandbox security enforcement tests                  |
| `backend/tests/test_memory_prompt_injection.py`                | `[ ]`  | Memory prompt injection defence tests               |
| `backend/tests/test_subagent_prompt_security.py`               | `[ ]`  | Subagent prompt injection prevention tests          |

---

## Section 28 — Extension Points & Plugin Architecture

**Goal:** Understand how DeerFlow is designed to be extended.

- Skills as the primary extension mechanism — creating a skill from scratch
- MCP server integration — connecting external tool servers
- Community tools — how to add a new search/web provider
- Custom agents — SOUL.md + config.yaml pattern
- Reflection system (`reflection/resolvers.py`) — dynamic class loading
- `extensions_config.json` as the single extension registry
- Agent Collaboration Protocol (ACP) config

**Key files:**

| Path                                            | Status | Notes                                                           |
| ----------------------------------------------- | ------ | --------------------------------------------------------------- |
| `backend/packages/harness/deerflow/reflection/` | `[ ]`  | Dynamic class loading via reflection resolvers                  |
| `backend/packages/harness/deerflow/skills/`     | `[ ]`  | Primary extension mechanism: skills as YAML tool wrappers       |
| `backend/packages/harness/deerflow/community/`  | `[ ]`  | Community search/tool providers as extension examples           |
| `extensions_config.json`                        | `[ ]`  | Single registry for all extensions: MCP servers, skills, agents |
| `extensions_config.example.json`                | `[ ]`  | Annotated example extension config                              |

---

## Section 29 — Patterns & Design Insights

**Goal:** Extract the architectural wisdom embedded in DeerFlow's design.

- Why LangGraph? Comparison to raw async queues or Celery
- The middleware-as-composition pattern vs inheritance
- Harness package boundary — why separate `deerflow.*` from `app.*`?
- Actor-model influences in the subagent system
- Event-driven run tracking (journal + event store)
- Per-user isolation as a first-class design principle
- Config-driven everything — flexibility vs complexity trade-off
- Debounce-and-batch pattern in memory updates
- Streaming-first design: SSE over WebSockets — why?
- The "super agent harness" mental model vs traditional agent frameworks

---

## Study Progress Tracker

| Section | Title                            | Status | Notes Files                                                                                                                                                                                                                                                                                                                                                               |
| ------- | -------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 01      | Product Overview & Positioning   | [x]    | `architecture/01-product-overview.md`                                                                                                                                                                                                                                                                                                                                     |
| 02      | System Architecture              | [x]    | `architecture/02-system-architecture-runtime-package.md`<br>`glossary/nginx-cheatsheet.md`<br>`glossary/nginx-concepts.md`<br>`glossary/nginx-deerflow.md`<br>`glossary/nginx-location-matching-detailed-explaination.md`                                                                                                                                                 |
| 03      | Project Setup & Tooling          | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 04      | Infrastructure & DevOps          | [~]    | `architecture/04-infrastructure-devops.md`                                                                                                                                                                                                                                                                                                                                |
| 05      | Backend: Gateway API             | [x]    | `modules/05a-gateway-api.md`, `modules/05b-api-endpoints-overview.md`, `modules/05-api-reference/`                                                                                                                                                                                                                                                                        |
| 06      | Backend: Auth & Authorization    | [x]    | `modules/06a-auth-internals.md`, `modules/06b-auth-enforcement.md`                                                                                                                                                                                                                                                                                                        |
| 07      | Backend: LangGraph Runtime       | [x]    | `modules/07a-runtime-primitives.md`, `modules/07b-checkpointer-store.md`, `modules/07c-runtime-events.md`, `modules/07d-run-storage.md`, `modules/07e-stream-bridge.md`, `modules/07f-run-orchestration.md`                                                                                                                                                               |
| 08      | Backend: Lead Agent              | [x]    | `modules/08a-lead-agent.md`, `modules/08b-skills-cache-pipeline.md`                                                                                                                                                                                                                                                                                                       |
| 09      | Backend: Middleware Pipeline     | [x]    | `modules/09a-middleware-pipeline-overview.md` (assembly), `modules/09b-before-agent-middlewares.md` (phase 2), `modules/09c-model-call-wrappers.md` (phase 3), `modules/09d-tool-call-wrappers.md` (phase 4), `modules/09e-before-model-middlewares.md` (phase 5), `modules/09f-after-model-middlewares.md` (phase 6), `modules/09g-after-agent-middlewares.md` (phase 7) |
| 10      | Backend: Memory System           | [x]    | `modules/10-memory-system.md`                                                                                                                                                                                                                                                                                                                                             |
| 11      | Backend: Subagents               | [x]    | `modules/11a-subagents-primitives.md` (phase 1: config, token_collector, registry), `modules/11b-subagents-builtins-executor.md` (phase 2: builtins, executor, background task lifecycle)                                                                                                                                                                                 |
| 12      | Backend: Tools System            | [x]    | `modules/12a-tools-primitives-registry.md` (phases 1–2), `modules/12b-tools-builtins.md` (phase 3: clarification, present_files, view_image, task), `modules/12c-tools-agent-builtins.md` (phase 3: tool_search, invoke_acp_agent, setup_agent, update_agent)                                                                                                           |
| 13      | Backend: Skills System           | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 14      | Backend: MCP Integration         | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 15      | Backend: Sandbox                 | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 16      | Backend: Model Layer             | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 17      | Backend: Config System           | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 18      | Backend: Persistence Layer       | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 19      | Backend: Channels                | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 20      | Backend: Tracing & Observability | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 21      | Backend: Community Integrations  | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 22      | Frontend: Architecture           | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 23      | Frontend: Core Modules           | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 24      | Frontend: Workspace UI           | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 25      | Frontend: Streaming & Rendering  | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 26      | Testing Strategy                 | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 27      | Security Design                  | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 28      | Extension Points                 | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
| 29      | Patterns & Design Insights       | [ ]    |                                                                                                                                                                                                                                                                                                                                                                           |
