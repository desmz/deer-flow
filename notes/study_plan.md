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
| `backend/langgraph.json`                     | `[ ]`  | LangGraph graph definition: nodes, edges, entrypoints                                                                                                         |
| `docker/nginx/`                              | `[x]`  | Nginx reverse proxy config: routing rules for port 2026 → 8001/3000                                                                                           |
| `backend/packages/harness/deerflow/runtime/` | `[ ]`  | Runtime package (overview depth): journal.py, converters.py, serialization.py, user_context.py + 5 subdirs (checkpointer, events, runs, store, stream_bridge) |

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
| `docker/docker-compose-dev.yaml` | `[ ]`  | Development Docker Compose stack                        |
| `docker/docker-compose.yaml`     | `[ ]`  | Production Docker Compose stack                         |
| `docker/nginx/`                  | `[ ]`  | Nginx config: path rewriting, /api/langgraph/\* routing |
| `docker/dev-entrypoint.sh`       | `[ ]`  | Container bootstrap script for dev mode                 |
| `docker/provisioner/`            | `[ ]`  | Provisioner container: initial DB setup and seeding     |
| `scripts/deploy.sh`              | `[ ]`  | Production deployment script                            |
| `scripts/serve.sh`               | `[ ]`  | Start the production server                             |
| `.github/workflows/`             | `[ ]`  | CI/CD pipeline definitions (if present)                 |

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

| Path                                     | Status | Notes                                                                 |
| ---------------------------------------- | ------ | --------------------------------------------------------------------- |
| `backend/app/gateway/app.py`             | `[ ]`  | FastAPI app bootstrap: lifespan, middleware, router mounting          |
| `backend/app/gateway/routers/`           | `[ ]`  | All HTTP route handlers (agents, auth, channels, runs, threads, etc.) |
| `backend/app/gateway/deps.py`            | `[ ]`  | Dependency injection: config and services flowing into handlers       |
| `backend/app/gateway/services.py`        | `[ ]`  | Service abstraction layer                                             |
| `backend/app/gateway/csrf_middleware.py` | `[ ]`  | CSRF protection middleware                                            |

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
| `backend/app/gateway/auth/`              | `[ ]`  | Auth providers, local auth, JWT, password hashing, credential file |
| `backend/app/gateway/auth_middleware.py` | `[ ]`  | Per-request authentication enforcement                             |
| `backend/app/gateway/langgraph_auth.py`  | `[ ]`  | Translates Gateway auth context into LangGraph identity            |
| `backend/app/gateway/authz.py`           | `[ ]`  | Authorization rules (who can access what)                          |
| `backend/app/gateway/internal_auth.py`   | `[ ]`  | Service-to-service auth for internal calls                         |

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
| `backend/packages/harness/deerflow/runtime/`               | `[ ]`  | Runtime package root: RunManager, journal, converters, serialization, user_context |
| `backend/packages/harness/deerflow/runtime/checkpointer/`  | `[ ]`  | Async state persistence for LangGraph graph checkpoints                            |
| `backend/packages/harness/deerflow/runtime/stream_bridge/` | `[ ]`  | Bridges LangGraph event stream to SSE (async_provider, memory, base)               |
| `backend/packages/harness/deerflow/runtime/runs/`          | `[ ]`  | RunManager, worker, schemas, run store                                             |
| `backend/packages/harness/deerflow/runtime/events/`        | `[ ]`  | Run event types, store, and pagination                                             |

---

## Section 08 — Backend: Lead Agent

**Goal:** Understand the core AI agent that handles user requests.

- Agent factory (`agents/factory.py`) — how the LangGraph graph is constructed
- Lead agent directory (`agents/lead_agent/`) — system prompt, agent definition
- Thread state (`agents/thread_state.py`) — the full state schema flowing through the graph
- Agent features (`agents/features.py`) — feature flags controlling agent behaviour
- How the agent graph nodes and edges are wired

**Key files:**

| Path                                                       | Status | Notes                                                    |
| ---------------------------------------------------------- | ------ | -------------------------------------------------------- |
| `backend/packages/harness/deerflow/agents/factory.py`      | `[ ]`  | Constructs the LangGraph agent graph                     |
| `backend/packages/harness/deerflow/agents/lead_agent/`     | `[ ]`  | Lead agent: system prompt, agent definition, node wiring |
| `backend/packages/harness/deerflow/agents/thread_state.py` | `[ ]`  | Full state schema flowing through the LangGraph graph    |
| `backend/packages/harness/deerflow/agents/features.py`     | `[ ]`  | Feature flags controlling agent behaviour                |

---

## Section 09 — Backend: Middleware Pipeline

**Goal:** Understand every transformation layer the agent goes through.

- Middleware architecture: how middlewares wrap the agent
- Complete list of middlewares in `agents/middlewares/`:
  - Clarification middleware
  - Dangling tool call middleware
  - Dynamic context middleware
  - Guardrail middleware
  - LLM error handling middleware
  - Loop detection middleware
  - Memory middleware
  - Subagent limit middleware
  - Summarization middleware
  - Thread data middleware
  - Title middleware
  - Todo middleware
  - Token usage middleware
  - Tool error handling middleware
  - Tool output truncation middleware
  - Uploads middleware
  - View image middleware
- Ordering and composition of the middleware chain

**Key files:**

| Path                                                    | Status | Notes                                                                             |
| ------------------------------------------------------- | ------ | --------------------------------------------------------------------------------- |
| `backend/packages/harness/deerflow/agents/middlewares/` | `[ ]`  | All 17 middleware implementations wrapping the lead agent                         |
| `backend/tests/test_*_middleware.py`                    | `[ ]`  | Unit tests illustrating each middleware's behaviour and edge cases (glob pattern) |

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

| Path                                               | Status | Notes                                             |
| -------------------------------------------------- | ------ | ------------------------------------------------- |
| `backend/packages/harness/deerflow/agents/memory/` | `[ ]`  | Memory subsystem: updater, queue, prompt, storage |
| `backend/tests/test_memory_*.py`                   | `[ ]`  | Memory unit and integration tests (glob pattern)  |

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

| Path                                           | Status | Notes                                                          |
| ---------------------------------------------- | ------ | -------------------------------------------------------------- |
| `backend/packages/harness/deerflow/subagents/` | `[ ]`  | Subagent executor, registry, config, token collector, builtins |
| `backend/tests/test_subagent_*.py`             | `[ ]`  | Subagent tests (glob pattern)                                  |

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

| Path                                       | Status | Notes                                                   |
| ------------------------------------------ | ------ | ------------------------------------------------------- |
| `backend/packages/harness/deerflow/tools/` | `[ ]`  | Tool types, registry, sync, skill manage tool, builtins |
| `backend/tests/test_tool_*.py`             | `[ ]`  | Tools unit tests (glob pattern)                         |

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

| Section | Title                            | Status | Notes File                            |
| ------- | -------------------------------- | ------ | ------------------------------------- |
| 01      | Product Overview & Positioning   | [x]    | `architecture/01-product-overview.md` |
| 02      | System Architecture              | [ ]    |                                       |
| 03      | Project Setup & Tooling          | [ ]    |                                       |
| 04      | Infrastructure & DevOps          | [ ]    |                                       |
| 05      | Backend: Gateway API             | [ ]    |                                       |
| 06      | Backend: Auth & Authorization    | [ ]    |                                       |
| 07      | Backend: LangGraph Runtime       | [ ]    |                                       |
| 08      | Backend: Lead Agent              | [ ]    |                                       |
| 09      | Backend: Middleware Pipeline     | [ ]    |                                       |
| 10      | Backend: Memory System           | [ ]    |                                       |
| 11      | Backend: Subagents               | [ ]    |                                       |
| 12      | Backend: Tools System            | [ ]    |                                       |
| 13      | Backend: Skills System           | [ ]    |                                       |
| 14      | Backend: MCP Integration         | [ ]    |                                       |
| 15      | Backend: Sandbox                 | [ ]    |                                       |
| 16      | Backend: Model Layer             | [ ]    |                                       |
| 17      | Backend: Config System           | [ ]    |                                       |
| 18      | Backend: Persistence Layer       | [ ]    |                                       |
| 19      | Backend: Channels                | [ ]    |                                       |
| 20      | Backend: Tracing & Observability | [ ]    |                                       |
| 21      | Backend: Community Integrations  | [ ]    |                                       |
| 22      | Frontend: Architecture           | [ ]    |                                       |
| 23      | Frontend: Core Modules           | [ ]    |                                       |
| 24      | Frontend: Workspace UI           | [ ]    |                                       |
| 25      | Frontend: Streaming & Rendering  | [ ]    |                                       |
| 26      | Testing Strategy                 | [ ]    |                                       |
| 27      | Security Design                  | [ ]    |                                       |
| 28      | Extension Points                 | [ ]    |                                       |
| 29      | Patterns & Design Insights       | [ ]    |                                       |
