# DeerFlow Technical Study Plan

> **Branch:** `study` | **Approach:** Top-down, from product surface to implementation depth
> **Purpose:** Drive the `/study` custom command. Each section = one study session.
> **Status legend:** `[ ]` Not started · `[~]` In progress · `[x]` Complete

---

## Section 01 — Product Overview & Positioning

**Goal:** Understand what DeerFlow *is* before touching any code.

- What problem does it solve? Who is the target user?
- How does it differentiate from other agent frameworks (AutoGen, CrewAI, OpenDevin)?
- Version history: v1 (Deep Research) → v2 (Super Agent Harness) — what changed and why
- Official website, README, release notes, CONTRIBUTING.md, SECURITY.md

**Key files:**
- `README.md`, `README_zh.md`
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- `Install.md`

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
- `backend/CLAUDE.md` (architecture section)
- `backend/langgraph.json`
- `docker/nginx/` config
- `backend/packages/harness/deerflow/runtime/`

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
- `Makefile`, `backend/Makefile`, `frontend/Makefile`
- `backend/pyproject.toml`, `backend/packages/harness/pyproject.toml`
- `frontend/package.json`, `frontend/pnpm-workspace.yaml`
- `config.yaml`, `extensions_config.json`
- `scripts/setup_wizard.py`, `scripts/doctor.py`, `scripts/configure.py`

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
- `docker/docker-compose-dev.yaml`, `docker/docker-compose.yaml`
- `docker/nginx/`
- `docker/dev-entrypoint.sh`
- `docker/provisioner/`
- `scripts/deploy.sh`, `scripts/serve.sh`
- `.github/workflows/` (if present)

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
- `backend/app/gateway/app.py`
- `backend/app/gateway/routers/`
- `backend/app/gateway/deps.py`
- `backend/app/gateway/services.py`
- `backend/app/gateway/csrf_middleware.py`

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
- `backend/app/gateway/auth/`
- `backend/app/gateway/auth_middleware.py`
- `backend/app/gateway/langgraph_auth.py`
- `backend/app/gateway/authz.py`
- `backend/app/gateway/internal_auth.py`

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
- `backend/packages/harness/deerflow/runtime/`
- `backend/packages/harness/deerflow/runtime/checkpointer/`
- `backend/packages/harness/deerflow/runtime/stream_bridge/`
- `backend/packages/harness/deerflow/runtime/runs/`
- `backend/packages/harness/deerflow/runtime/events/`

---

## Section 08 — Backend: Lead Agent

**Goal:** Understand the core AI agent that handles user requests.

- Agent factory (`agents/factory.py`) — how the LangGraph graph is constructed
- Lead agent directory (`agents/lead_agent/`) — system prompt, agent definition
- Thread state (`agents/thread_state.py`) — the full state schema flowing through the graph
- Agent features (`agents/features.py`) — feature flags controlling agent behaviour
- How the agent graph nodes and edges are wired

**Key files:**
- `backend/packages/harness/deerflow/agents/factory.py`
- `backend/packages/harness/deerflow/agents/lead_agent/`
- `backend/packages/harness/deerflow/agents/thread_state.py`
- `backend/packages/harness/deerflow/agents/features.py`

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
- `backend/packages/harness/deerflow/agents/middlewares/`
- All `test_*_middleware.py` files for reference

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
- `backend/packages/harness/deerflow/agents/memory/`
- `backend/tests/test_memory_*.py`

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
- `backend/packages/harness/deerflow/subagents/`
- `backend/tests/test_subagent_*.py`

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
- `backend/packages/harness/deerflow/tools/`
- `backend/tests/test_tool_*.py`

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
- `backend/packages/harness/deerflow/skills/`
- `skills/public/`
- `backend/tests/test_skills_*.py`

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
- `backend/packages/harness/deerflow/mcp/`
- `backend/app/gateway/routers/mcp.py`
- `backend/tests/test_mcp_*.py`

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
- `backend/packages/harness/deerflow/sandbox/`
- `backend/packages/harness/deerflow/community/aio_sandbox/`
- `backend/tests/test_aio_sandbox*.py`, `test_sandbox_*.py`

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
- `backend/packages/harness/deerflow/models/`
- `backend/tests/test_model_*.py`, `test_patched_*.py`

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
- `backend/packages/harness/deerflow/config/`
- `config.yaml`, `config.example.yaml`

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
- `backend/packages/harness/deerflow/persistence/`
- `backend/tests/test_persistence_*.py`, `test_run_repository.py`, `test_thread_meta_repo.py`

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
- `backend/app/channels/`
- `backend/app/gateway/routers/channels.py`
- `backend/tests/test_channels.py`, `test_discord_channel.py`, `test_dingtalk_channel.py`, `test_feishu_parser.py`

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
- `backend/packages/harness/deerflow/tracing/`
- `backend/tests/test_tracing_*.py`

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
- AIO sandbox (`community/aio_sandbox/`) — remote async sandbox

**Key files:**
- `backend/packages/harness/deerflow/community/`
- `backend/tests/test_exa_tools.py`, `test_firecrawl_tools.py`, `test_serper_tools.py`, etc.

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
- `frontend/src/app/`
- `frontend/next.config.js`, `frontend/tsconfig.json`
- `frontend/src/env.js`

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
- `frontend/src/core/`

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
- `frontend/src/components/workspace/`
- `frontend/src/app/workspace/`
- `frontend/src/components/ai-elements/`

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
- `frontend/src/core/streamdown/`
- `frontend/src/core/api/` (stream-mode)
- `frontend/tests/unit/core/streamdown/plugins.test.ts`

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
- `backend/tests/conftest.py`
- `frontend/vitest.config.ts`, `frontend/playwright.config.ts`
- `frontend/tests/`

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
- `backend/app/gateway/csrf_middleware.py`
- `backend/packages/harness/deerflow/sandbox/security.py`
- `backend/packages/harness/deerflow/skills/security_scanner.py`
- `backend/packages/harness/deerflow/guardrails/`
- `backend/tests/test_sandbox_tools_security.py`, `test_memory_prompt_injection.py`, `test_subagent_prompt_security.py`

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
- `backend/packages/harness/deerflow/reflection/`
- `backend/packages/harness/deerflow/skills/`
- `backend/packages/harness/deerflow/community/`
- `extensions_config.json`, `extensions_config.example.json`

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

| Section | Title | Status | Notes File |
|---------|-------|--------|------------|
| 01 | Product Overview & Positioning | [ ] | |
| 02 | System Architecture | [ ] | |
| 03 | Project Setup & Tooling | [ ] | |
| 04 | Infrastructure & DevOps | [ ] | |
| 05 | Backend: Gateway API | [ ] | |
| 06 | Backend: Auth & Authorization | [ ] | |
| 07 | Backend: LangGraph Runtime | [ ] | |
| 08 | Backend: Lead Agent | [ ] | |
| 09 | Backend: Middleware Pipeline | [ ] | |
| 10 | Backend: Memory System | [ ] | |
| 11 | Backend: Subagents | [ ] | |
| 12 | Backend: Tools System | [ ] | |
| 13 | Backend: Skills System | [ ] | |
| 14 | Backend: MCP Integration | [ ] | |
| 15 | Backend: Sandbox | [ ] | |
| 16 | Backend: Model Layer | [ ] | |
| 17 | Backend: Config System | [ ] | |
| 18 | Backend: Persistence Layer | [ ] | |
| 19 | Backend: Channels | [ ] | |
| 20 | Backend: Tracing & Observability | [ ] | |
| 21 | Backend: Community Integrations | [ ] | |
| 22 | Frontend: Architecture | [ ] | |
| 23 | Frontend: Core Modules | [ ] | |
| 24 | Frontend: Workspace UI | [ ] | |
| 25 | Frontend: Streaming & Rendering | [ ] | |
| 26 | Testing Strategy | [ ] | |
| 27 | Security Design | [ ] | |
| 28 | Extension Points | [ ] | |
| 29 | Patterns & Design Insights | [ ] | |
