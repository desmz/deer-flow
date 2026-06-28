# Open Questions

Running log of unresolved questions across all study sections.

---

## Section 01 — Product Overview & Positioning

- How does the LangGraph-compatible API surface (`/api/langgraph/*`) map internally? Is it thin nginx routing, or does the Gateway implement the LangGraph HTTP protocol itself?
- What exactly does the provisioner container do? The README implies Kubernetes sandbox pod scheduling — what RPC protocol connects Gateway → provisioner?
- v1 Deep Research architecture: what was its LangGraph graph structure? Knowing the baseline clarifies what v2 replaced.
- `DEER_FLOW_PROJECT_ROOT` vs `DEER_FLOW_HOME` — why two separate env vars? One for config, one for runtime state?
- How does LangGraph's concept of "assistant" (`assistant_id: lead_agent`) map to DeerFlow's internal agent model?

---

## Section 04 — Infrastructure & DevOps

- The sandbox image is on `enterprise-public-cn-beijing.cr.volces.com`. Is it publicly pullable, or does it require credentials? This matters for non-Chinese deployments.
- How does the gateway know when a sandbox Pod is actually ready (readiness probe passing) after `POST /api/sandboxes` returns `status: Pending`? Does it poll `GET /api/sandboxes/{id}` or retry at the call site?
- `detect_sandbox_mode` in `deploy.sh` uses a minimal awk YAML parser. What happens if `config.yaml` has inline comments on the `use:` line or is reformatted — does it silently fall back to `local`?
- With 4 uvicorn workers in production, how does `RunManager` handle shared state across worker processes? Is there a Redis layer, or does it rely on the database for coordination?
- No integration test workflow exists in CI — E2E tests run with a mocked API (`SKIP_ENV_VALIDATION=1`). How is full backend+frontend integration validated before a release tag is pushed?

---

## Section 02 — System Architecture (Runtime Package)

- `converters.py` is not re-exported from `__init__.py` and not used by `RunJournal` (which calls `model_dump()` directly). Is it dead code, or consumed by something outside this folder?
- `make_stream_bridge` has a `"redis"` branch that raises `NotImplementedError("Redis stream bridge planned for Phase 2")`. Is this actively on the roadmap?
- `DbRunEventStore` uses PostgreSQL advisory locks for monotonic `seq` assignment. Is there a concurrent-write test verifying this guarantee?
- `JsonlRunEventStore.list_messages()` scans all run files per thread (O(runs)) while `list_events()` reads one file (O(1)). Is this a performance concern at scale?
- `run_events_config.track_token_usage` flag: which config key controls it, and is there a documented rationale for ever disabling it?

---

## Section 05 — Backend: Gateway API (FastAPI) — app.py

- The orphan thread migration (`_migrate_orphaned_threads`) runs on every boot after admin exists. Is there a flag to mark migration as "already done" to avoid scanning all threads on every startup?
- `_iter_store_items` uses `store.asearch(("threads",), ...)` — is `("threads",)` the only namespace that may have orphans, or could other namespaces (e.g. per-user namespaces) also have pre-auth data?
- `_SHUTDOWN_HOOK_TIMEOUT_SECONDS = 5.0`: on `TimeoutError`, channel service teardown is abandoned. What is the impact on in-flight IM messages — are they lost, or do the platform retry mechanisms handle it?
- `get_configured_cors_origins()` is imported from `csrf_middleware.py`. Why is the CORS origin list sourced from the CSRF middleware module rather than from `config.py`? _(Resolved: they share the list intentionally so CORS and CSRF origin checks can never drift — co-location is the enforcement mechanism)_
- `csrf_middleware.py`: `should_check_csrf` has a hard-coded exemption for `/api/v1/auth/me` even though it's a POST. Is `me` actually a POST in the router, or is this a vestigial exemption from an older design?
- `deps.py`: `_cached_local_provider` and `_cached_repo` are module-level globals, not on `app.state`. This means they survive across test client instances in unit tests — could this cause cross-test state pollution if two tests configure different session factories?
- `services.py`: `normalize_input` converts all non-user message types (system, ai, tool) to `HumanMessage` with a TODO comment. Is this currently a real limitation affecting callers who send multi-turn history, or is the API only used for single human messages?
- `services.py`: `start_run` validates `model_name` against the allowlist but only when it is set in `body.context`. Can a client bypass this by injecting `model_name` directly into `body.config.configurable`?

---

## Section 05 — Backend: Gateway API (FastAPI) — routers/threads.py

- **`search_threads` returns stale status** — `search_threads` projects `status` straight from the stored `threads_meta` row (`r.get("status", "idle")`), while `get_thread` recomputes live status from the checkpoint via `_derive_thread_status`. So a thread mid-run shows `running` in `/search` but the single-thread GET derives `idle`/`interrupted`/`error` from checkpoint state. Is the search status intentionally stale (cheap list view) vs. the canonical per-thread view, and does the frontend rely on either being authoritative?
- **`busy` vs `running` vocabulary mismatch** — the `ThreadResponse.status` field doc advertises `idle, busy, interrupted, error` (the LangGraph Platform vocabulary), but the runtime actually writes `running` (`services.py:319`, `worker.py:417`) and never `busy`. Should DeerFlow emit `busy` to fully match the LangGraph Platform contract, or is `running` an accepted DeerFlow extension the frontend already understands?
- **`writes` metadata key is off-contract drift risk** — `update_thread_state` writes `metadata["writes"] = {as_node: values}` for HITL-resume attribution, but `writes` was **removed from LangGraph's typed `CheckpointMetadata` in `langgraph-checkpoint` ≥ ~3.x** (installed `4.0.2` only declares `source`/`step`/`parents`/`run_id`). It still round-trips because the TypedDict is `total=False` (extra keys persisted untyped). If a future checkpointer backend stops persisting unknown metadata keys, HITL-resume routing would silently break. **No contract test currently guards the Gateway's LangGraph-protocol fidelity** — `TestGatewayConformance` only covers `DeerFlowClient` vs Gateway models, not Gateway vs `langgraph-sdk`. Should a symmetric `langgraph-sdk`-vs-Gateway contract test be added to catch wire-protocol drift at upgrade time? (See [[protocol-mirror-anti-corruption]].)
- **Title lives in two stores** — `update_thread_state` writes `title` into both the checkpoint `channel_values` and the `thread_meta.display_name` (best-effort, non-fatal). If the `update_display_name` sync fails, the checkpoint and `/search` projection diverge until the next state write. Is eventual reconciliation guaranteed anywhere, or can the search title stay permanently stale after a transient failure?

---

## Section 05 — Backend: Gateway API (FastAPI) — routers/thread_runs.py

- **`list_thread_messages` last-AI detection assumes ordered rows** — feedback is attached to the last `ai_message` per run by iterating `messages` in returned order and overwriting `last_ai_per_run[run_id]` with each later index. This is only correct if `event_store.list_messages()` returns rows in ascending `seq`. Is that ordering a guaranteed contract of the event store, or could a backend (e.g. an unordered scan) break feedback attachment?
- **`wait_run` reads the checkpoint by `thread_id` only** — final state is fetched with `config = {"configurable": {"thread_id": thread_id}}`, no `checkpoint_ns`/`checkpoint_id`. With the default `multitask_strategy="reject"` concurrent runs can't overlap, so "latest checkpoint for the thread" == "this run's result". Does any non-reject strategy (`enqueue`, `interrupt`) open a window where `wait_run` could return another run's final state?
- **`stream_existing_run` GET after completion** — if a run already finished and its stream-bridge buffer was released, does a late `GET .../stream` (join) replay terminal events from the event store, or does it hang/return empty? Behaviour depends on the bridge's post-completion semantics (Section 07).
- **`body.command` is declared but never consumed** — `RunCreateRequest.command` (a LangGraph `Command`) is part of the wire contract, but `start_run` only forwards `body.input`/`body.config`; nothing builds `Command(resume=...)`. DeerFlow implements HITL resume as "new run on the same thread_id" instead (see `execution-flow/human-in-the-loop.md`). Is native `Command` resume planned, or is the field pure SDK-compat ballast? (See [[protocol-mirror-anti-corruption]].)

---

## Section 05 — Backend: Gateway API (FastAPI) — routers/runs.py

- **`_resolve_run` ownership claim vs. interface reality** — the docstring says "with user ownership check", and the call site comments `# user_id=AUTO filters by contextvar`, but the abstract `RunStore.get(run_id)` (`runtime/runs/store/base.py:42`) takes **no** `user_id` parameter and `MemoryRunStore` does no filtering. So cross-user isolation on `/api/runs/{run_id}/messages` and `/feedback` exists only if the _concrete production_ store reads a user contextvar internally. Which store is wired in production, and does it actually scope by user — or is this an isolation gap in non-DB deployments?
- **Stateless create endpoints have no `@require_permission`** — `POST /api/runs/stream` and `/wait` rely solely on the global `AuthMiddleware` (401 for unauthenticated) and skip the explicit `runs:create` permission check that `thread_runs.create_run` applies. Today this is moot because `AuthMiddleware` grants every authenticated user `_ALL_PERMISSIONS`, but if a real RBAC permission set is ever introduced, these two routes would silently bypass the `runs:create` gate. Intentional, or latent drift?
- **`stateless_wait` duplicates `thread_runs.wait_run`** — the checkpoint-read-then-fallback block (`aget_tuple` → `serialize_channel_values` → `{status, error}`) is copy-pasted between the two routers. Worth extracting into `services.py` (e.g. `fetch_final_state(thread_id, record)`) alongside `start_run`/`sse_consumer`, or is the duplication tolerated to keep the two surfaces independent?

---

## Section 05 — Backend: Gateway API (FastAPI) — routers/agents.py

- **`USER.md` is global while agents and memory are per-user** — `get_user_profile`/`update_user_profile` read and write `{base_dir}/USER.md` with no `user_id`, but custom agents live at `users/{user_id}/agents/{name}` and memory at `users/{user_id}/memory.json`. The profile is documented as "injected into all custom agents", so in a multi-user deployment one user can read and overwrite the profile that flows into every other user's agents. Is this an intentional single-tenant assumption for the agents-management API (gated off by default), or an isolation gap that should move USER.md under `users/{user_id}/`?
- **Agents-management API has no per-resource authz, only a global on/off flag** — every route is gated solely by `_require_agents_api_enabled()` (config `agents_api.enabled`, default False) plus the global `AuthMiddleware`. There's no `@require_permission` and no ownership check beyond resolving `user_id` from the contextvar. Once enabled, any authenticated user can CRUD their own agents — fine for single-user, but is there a planned RBAC story for multi-tenant, or is "enabled ⇒ full trust" the intended model?
- **No `reset_agent()` / cache invalidation after agent create/update/delete** — `tools/sync.py` and `DeerFlowClient.update_skill()` invalidate the cached agent on change, but these HTTP routes write `config.yaml`/`SOUL.md` directly with no equivalent invalidation. Does a running agent pick up an edited SOUL.md on the next run (config reload by mtime), or can a stale agent definition persist until process restart? (Cross-check with the agent factory caching in Section 08.) **Partial answer (Section 05 — skills.py):** the skills router calls `refresh_skills_system_prompt_cache_async()` after every mutation precisely to avoid this; agents.py has no analogous call, strengthening the suspicion that SOUL.md edits rely solely on mtime-based reload.

---

## Section 05 — Backend: Gateway API (FastAPI) — routers/skills.py

- **Mutating shared skills with no per-resource authz** — install/enable/edit/delete/rollback all write a global, config-driven skills directory and `extensions_config.json` with only global `AuthMiddleware` (no `@require_permission`, no ownership). In a multi-tenant deployment any authenticated user can edit or delete a skill that affects every other user's agent. Is the skills system intentionally single-tenant/admin-only, or should skill mutations be gated (admin role, or per-user custom skills)? (Mirrors the USER.md global-isolation question for agents.py.)
- **`update_skill` whole-file read-modify-write race** — toggling one skill's `enabled` flag rebuilds the entire `extensions_config.json` (all `mcpServers` + all `skills`) and overwrites it with no file lock or atomic temp-rename. A concurrent skill toggle or MCP-config `PUT` (`routers/mcp.py`) could lose one of the two writes (last-writer-wins). Memory/agent writes use atomic temp+rename — should this path too?
- **`config_path` fallback writes to `Path.cwd().parent`** — when `ExtensionsConfig.resolve_config_path()` returns None, `update_skill` falls back to `Path.cwd().parent / "extensions_config.json"`. That's process-CWD-dependent: a Gateway started from a different directory than expected could persist skill state to an unexpected location that the next load won't find. Is CWD guaranteed by the launch scripts, or is this a latent footgun?
- **Rollback indexing semantics** — `rollback_custom_skill` indexes `history[request.history_index]` (default `-1` = latest) and restores that record's `prev_content`. So default rollback undoes the most recent change, but there's no bounds feedback beyond a generic `IndexError → 400`. Should the API expose the history length / valid index range (the `/history` endpoint returns it, but the two calls aren't transactional — history could change between them)?

## Section 06 — Backend: Auth & Authorization (`auth/` folder)

- **GitHub OAuth fields** (`oauth_github_client_id`, `oauth_github_client_secret` in `AuthConfig`) — no consumer found in `providers.py`, `local_provider.py`, or any router. Are these wired somewhere not yet studied, or placeholder config for a future OAuth provider?
- **`iat` claim in `TokenPayload`** — parsed and stored on the model, but `deps.py` and `langgraph_auth.py` only read `sub` and `ver`. Is `iat` purely RFC 7519 compliance, or does a consumer exist elsewhere?
- **`credential_file.py` `label="initial"` default** — no active caller passes `label="initial"`. The `initialize_admin` endpoint takes credentials from the request body. Is the "initial" path dead code, or reserved for a future headless first-boot provisioning flow?

---

## Section 06 — Backend: Auth & Authorization (`auth_middleware.py`)

- **`AUTH_TEST_PLAN test 7.5.8`** — the comment references a specific test plan document that identified the "junk cookie bypass gap". Where does this plan live in the repo (if at all), and what other identified gaps have not yet been closed?
- **Internal user as `SimpleNamespace`** — `get_internal_user()` returns `SimpleNamespace(id=DEFAULT_USER_ID, system_role="internal")`, which lacks `User` model fields like `email`, `token_version`, `system_role`. If a downstream route handler calls `user.email` or `user.token_version`, it will `AttributeError`. Is there a contract that internal-auth paths never hit routes that access those fields?
- **Dual state stamps** — both `request.state.user` and the `user_context` contextvar carry the same user object. Who consumes `request.state.user` directly vs the contextvar? Is there a pattern where one is needed and the other is not sufficient?
- **`require_auth` has no production callsites** — every router uses `@require_permission` directly. Is `require_auth` kept for future routes that need only authentication (no resource model), or is it effectively dead code that could be removed?

---

## Section 06 — Backend: Auth & Authorization (`langgraph_auth.py`)

- **CSRF duplication** — `_check_csrf` in `langgraph_auth.py` duplicates the Double Submit Cookie logic from `CSRFMiddleware`. Is there a shared utility these could both call, or is the duplication intentional (no shared dependency between Gateway middleware and LangGraph auth handler)?
- **`@auth.on` fires on both writes and reads** — the `value.setdefault("metadata", {})` mutation happens on every call, including read-only operations where `metadata` injection is meaningless. Does LangGraph's `Auth.on` provide a way to dispatch separately for reads vs writes, or is the unconditional mutation harmless?

---

## Section 07 — Backend: LangGraph Runtime (Phase 1 Primitives)

- **`resolve_runtime_user_id` adoption gap** — only `summarization_hook.py` and `setup_agent_tool.py` call it today. `memory_middleware`, `uploads_middleware`, and `thread_data_middleware` still use `get_effective_user_id()` directly. Is this an intentional distinction (those middlewares are always in-task and safe), or a gradual migration in progress?
- **`on_tool_start` no-op** — `RunJournal.on_tool_start` does nothing except debug logging. Given that `llm.tool.result` events exist, is a `llm.tool.call` event (capturing tool inputs before execution) planned?
- **`record_middleware` callers** — `RunJournal.record_middleware()` is public API for middlewares to log state changes, but no callers were found in the initial grep of non-test files. Which middlewares actually call it?
- **`converters.py` roadmap** — no production callers exist. The `langchain_to_openai_completion` function implements a full `/v1/chat/completions` response envelope. Is an OpenAI-compatible API endpoint on the roadmap, or was this an abandoned experiment?

## Section 07 — Backend: LangGraph Runtime (Phases 2 & 3 — Checkpointer & Store)

- **`make_store()` missing `database:` config path** — `make_checkpointer()` supports the unified `database:` section as a second-tier fallback; `make_store()` only reads `app_config.checkpointer`. A `database:`-only deployment gets a real checkpointer backend but an in-memory store, silently losing thread metadata and user memory on restart.
- **Two config sources for sync providers** — `get_checkpointer()` reads the module-global `_checkpointer_config`; `checkpointer_context()` reads `AppConfig.checkpointer` from the Pydantic object. Tests that call `set_checkpointer_config()` affect `get_checkpointer()` but not `checkpointer_context()`. Intentional asymmetry or should they unify?
- **`POSTGRES_CONN_REQUIRED` error message** — the store raises `"checkpointer.connection_string is required"` even though the user has no `checkpointer:` section to look at. Should say `store` or `database` depending on the caller context.
- **Blocking `ensure_sqlite_parent_dir` in async paths** — three out of four async providers call it synchronously on the event loop (only `checkpointer/async_provider._async_checkpointer` correctly offloads via `asyncio.to_thread`). Likely harmless in practice but worth auditing.
- **`_async_checkpointer_from_database` vs `_async_checkpointer` for `ensure_sqlite_parent_dir`** — the legacy path uses `asyncio.to_thread`; the unified path does not. Intentional decision (e.g., the unified path is newer and never got the same review) or an oversight?

## Section 07 — Backend: LangGraph Runtime (Phase 4 — Run Event Store)

- **`list_messages_by_run` cursor divergence** — uses two separate `if` statements (allowing simultaneous `before_seq` + `after_seq` range queries), while `list_messages` uses `if/elif` (only one cursor active). No test covers both cursors at once. Is simultaneous range filtering intentional contract, or an oversight replicated from memory → JSONL → DB?
- **`list_events` 500-item limit with no `has_more`** — the hard limit of 500 is returned without a pagination signal. Long runs with heavy tool use could silently truncate the trace. Should there be a `has_more` bool or a streaming read path for large event streams?
- **`_max_seq_for_thread` concurrent-write guarantee** — a test (`test_postgres_max_seq_uses_advisory_lock_without_for_update`) verifies the advisory-lock path is taken, but does not verify correctness under actual concurrent writes. Is there a race test against the SQLite path where `FOR UPDATE` behaviour is exercised?
- **`put_batch` cross-thread assumption** — the comment "assume all events in batch belong to same thread" is a correctness invariant, not validated in code. `RunJournal._flush_sync` always buffers events for a single run (hence a single thread), so the assumption holds today. But if a future caller batches across threads the seq counter will corrupt silently.
- **`_ensure_seq_loaded` cold-start cost (JSONL)** — on first write after a process restart, the JSONL store scans all `.jsonl` files for the thread to find the max seq. For a long-lived thread with hundreds of runs, this could block the event loop for a noticeable duration. No cap or async offload exists.
- **`delete_by_run` seq gap behaviour** — deleting a run leaves a gap in the seq sequence for that thread. All three backends (memory, JSONL, DB) share this behaviour. The `UniqueConstraint("thread_id", "seq")` in the DB model confirms gaps are intentional, but pagination cursors that assume contiguous seqs could break if any consumer ever relies on that assumption.

## Section 07 — Backend: LangGraph Runtime (Phase 5 — Run Storage)

- **`RunStatus.timeout` is never written** — it is defined in `schemas.py` and exported, but no callsite in `worker.py` or `manager.py` transitions a run to `timeout`. Is it set by an external caller (e.g., the channels system via `runs.wait()` timeout), or is it dead code reserved for a future watchdog?
- **`list_pending` is untriggered in production** — both `MemoryRunStore` and `RunRepository` implement `list_pending` and tests exercise it, but `RunManager` never calls it. Is crash-recovery on the roadmap and the method is forward-looking infrastructure, or is it vestigial from an earlier design?
- **`RunStore` dict return schema has no formal contract** — `get()` and `list_by_thread()` return `dict[str, Any]`. `RunRepository.sql.py` explicitly remaps columns to match `MemoryRunStore`'s layout, confirming the dict keys are the implicit contract. Should there be a Pydantic/dataclass model formalising this shape, or does the Gateway router serve as the accidental enforcer?
- **Token counts for `interrupted`/`timeout` runs are excluded from `aggregate_tokens_by_thread`** — only `success` and `error` runs contribute. Tokens consumed by a run that timed out or was interrupted are silently dropped from thread-level reporting. Is this intentional (interrupted runs are partial; their token counts are unreliable)?

---

## Section 07 — Run Orchestration (`worker.py` + `manager.py`)

- **`list_by_thread` ordering bug**: The docstring says "newest first" and the internal comment describes a reversal, but the code returns oldest-first (dict insertion order). Tests confirm oldest-first. Do any callers depend on the undocumented oldest-first behaviour? Should the docstring be corrected or the code fixed?
- **`_extract_human_message` dead code in `worker.py`**: Defined but never called anywhere. Was it used when the journal manually recorded human message events before the LangChain callback approach? Safe to delete?
- **`"events"` stream_mode gap**: `astream()` cannot produce events + values simultaneously; the JS LangGraph Platform server works around this via internal checkpoint callbacks not exposed in the Python API. Is there a tracking issue or plan to bridge this for the Python harness?
- **`RunManager.cleanup` is not scheduled in `services.py`**: The 300-second default cleanup delay exists but is never wired in the HTTP path. Do run records accumulate in `_runs` for the process lifetime, or is there a background sweep elsewhere?
- **`cancel()` skips the store write**: `cancel()` updates `record.status` in-memory but defers the store write to the worker's `finally` block. If the worker process crashes after `task.cancel()` but before the finally runs, the store records the run as still `running`. Is crash-recovery via `list_pending` intended to fix these orphaned records?

## Section 08 — Lead Agent

- **`DynamicContextMiddleware` lazy import**: It is imported inside `_build_middlewares()` while all other middlewares are imported at the module top. Is this guarding against a circular import, and if so, which cycle?
- **`get_enabled_skills_for_config` identity cache**: The outer cache keys by `id(app_config)`. If a config object is GC'd and a new object lands at the same address (CPython reuses addresses), would the cache serve a stale entry? Is this a real risk given config object lifetimes?
- **`config["metadata"]` mutation**: `_make_lead_agent` mutates the dict in-place. Is LangGraph's `RunnableConfig` treated as immutable per invocation, or can this mutation propagate unexpectedly between nodes?
- **Phase 2 config-free runtime**: The `create_deerflow_agent` docstring notes "Full config-free runtime is a Phase 2 goal" — some feature-injected tools (e.g. `task_tool`) still read global config at invocation time. Is there a tracking issue?
- **`todos` untyped list**: `ThreadState.todos` is `NotRequired[list | None]` with no element type, unlike every other collection field. Is this intentional (dynamic shape) or a missed tightening?
- **`__init__.py` import side effect in tests**: `prime_enabled_skills_cache()` starts a background thread on any import of `deerflow.agents`. How do tests that need to control this guard against it — via `sys.modules` mocks in `conftest.py`?

---

## Section 09 — Backend: Middleware Pipeline (Phase 2 — Before-Agent Middlewares)

- **Lazy sandbox acquisition path**: With `lazy_init=True`, `SandboxMiddleware.before_agent` is a no-op. Who calls `provider.acquire(thread_id)` on the first tool call? Likely inside `SandboxProvider.get()` from a sandbox tool — needs confirmation in `sandbox/tools.py`.
- **`uses_thread_data_mounts` flag**: `SandboxProvider.uses_thread_data_mounts: bool = False` is declared on the ABC. Does `AioSandboxProvider` set this to `True`? Is it read anywhere to enforce the `ThreadData → Sandbox` ordering constraint, or is ordering enforced only by convention?
- **`_get_memory_context` sync call in async context**: `DynamicContextMiddleware._build_full_reminder` calls `_get_memory_context()` synchronously. If memory is loaded lazily from disk on first access, this could block the event loop. Is the cache always warm before `before_agent` runs?
- **`"summary"` name guard**: `_is_user_injection_target` excludes messages with `name == "summary"`. Is `"summary"` the exact attribute written by `SummarizationMiddleware`? Needs confirmation when reading that middleware.
- **Cross-user memory isolation in async**: `_get_memory_context` calls `get_effective_user_id()` which reads a contextvar. Does this correctly scope memory to the current request's user under concurrent async execution?
- **Historical uploads scan includes `.md` companion files**: `UploadsMiddleware` scans `uploads/` via `iterdir()` with no suffix filter. Companion `.md` files produced by the conversion pipeline would appear as `historical_files`. Is this intentional or an oversight?

---

## Section 09 — Backend: Middleware Pipeline (Phase 3 — DanglingToolCallMiddleware)

- **`patched == messages` comparison cost**: The no-op early-exit at line 172 relies on Python list equality, which compares each element via `BaseMessage.__eq__`. For a long thread with hundreds of messages, is this O(n) comparison with deep equality a performance concern before every model call?
- **`additional_kwargs["tool_calls"]` mutual-exclusivity assumption**: The guard `if not tool_calls:` assumes that when `tool_calls` is populated, `additional_kwargs["tool_calls"]` is a duplicate representation of the same calls. Is this always true across all LangChain provider adapters? Could an adapter set both with different call IDs (e.g., a partial streaming response where one field is partially written)?
- **`setdefault` for duplicate `tool_call_id`**: `tool_messages_by_id.setdefault(msg.tool_call_id, msg)` keeps only the first `ToolMessage` for a given `tool_call_id` if duplicates appear in history. In what scenario could the same ID appear twice — LangGraph state re-hydration, a retry, or a bug upstream?

---

## Section 09 — Backend: Middleware Pipeline (Phase 5 — SummarizationMiddleware)

- **`"summary"` name now confirmed**: `DeerFlowSummarizationMiddleware._build_new_messages` sets `name="summary"` on the injected HumanMessage. The guard in `DynamicContextMiddleware._is_user_injection_target` correctly matches this. (Answers the open question from Phase 2.)
- **`_find_skill_bundles` ToolMessage lookahead**: The inner `while j < n and isinstance(messages[j], ToolMessage)` advances `j` past all consecutive ToolMessages after an AIMessage, then walks `range(i+1, j)` to match results. Does this correctly handle interleaved non-ToolMessages (e.g., a HumanMessage injected between AIMessage and its ToolMessages)? In practice LangGraph guarantees contiguity, but the parser silently misses them if that invariant breaks.
- **Skill bundle splitting on AIMessage with mixed tool calls**: When an AIMessage has both skill reads and non-skill reads, the code creates two clones — one preserved (skill calls, empty content), one summarized (non-skill calls, original content). Does the model correctly reconstruct the intent from a content-empty AIMessage with only skill tool_calls in the preserved portion?
- **`before_summarization` hook ordering contract**: Hooks fire in registration order, but this is implicit (list iteration). Should this be documented as a public API guarantee, or is it an implementation detail that could change?

---

## Section 11 — Backend: Subagents (Phase 2 — Builtins & Executor)

- **Cooperative cancellation gap for long tools**: `future.cancel()` has no effect on a
  `run_coroutine_threadsafe`-submitted future once the coroutine has started. A bash command
  running for 14 minutes inside a 15-minute timeout will trigger TIMED_OUT on the scheduler
  thread, but `_aexecute` continues on the isolated loop until the tool returns. The
  `cancel_event` check only fires at the next `astream` boundary.
- **`_background_tasks` leak on lead agent crash**: `cleanup_background_task` is called by
  `task_tool.py` after polling completes. If the lead agent crashes after `execute_async`
  but before polling, the task entry stays in `_background_tasks` for the process lifetime.
  Is there a TTL expiry or GC sweep?
- **Vision middleware at agent-creation vs executor-init**: For `model="inherit"` subagents,
  model resolution is deferred from `__init__` to `_create_agent`. Does `build_subagent_runtime_middlewares`
  correctly pick up the resolved model name, ensuring the vision check is accurate?
- **`ai_messages` dict-equality fallback performance**: When an `AIMessage` has no `id`
  field, deduplication falls back to `message_dict in ai_messages` (full dict equality).
  For a 100-turn subagent with large messages, this is O(n×m) per chunk.

---

## Section 12 — Backend: Tools System (Phase 3 — tool_search.py)

- **Regex score tie-breaking is registration order**: `DeferredToolRegistry.search()` uses `scored.sort(key=lambda x: x[0], reverse=True)` — Python's stable sort preserves insertion order within the same score bucket. Is relying on MCP tool registration order as a tiebreaker intentional, or should ties be broken alphabetically?
- **`convert_to_openai_function` model-agnosticism**: The tool serializes matched tools to OpenAI function-call format via `langchain_core.utils.function_calling.convert_to_openai_function`. For models that natively use Anthropic tool format (e.g. Claude via `langchain_anthropic`), does LangChain's `bind_tools` transparently translate this, or could the JSON shape mismatch cause silent schema errors?
- **`reset_deferred_registry` is only safe between runs**: In production code, no call site calls `reset_deferred_registry()` — only test fixtures do. If a future feature needs to reset mid-run (e.g. hot-reload of MCP config), the ContextVar isolation guarantee must be re-evaluated against issue #2884.

---

## Section 12 — Backend: Tools System (Phase 3 — invoke_acp_agent_tool.py)

- **`proc` is unpacked but never used**: `spawn_agent_process` yields `(conn, proc)` but `proc` is never referenced inside the `async with` block. Is it available for sending SIGTERM on a manual timeout? The async context manager owns the process lifetime, but explicit cancellation hooks may be needed for long-running ACP agents.
- **No timeout on `conn.prompt()`**: The ACP `prompt()` call has no explicit timeout. A misbehaving ACP agent (or a long coding task) could block indefinitely. Is there a timeout at the ACP protocol level, or does the outer LangGraph run timeout apply here?
- **MCP passthrough format mismatch risk**: `_build_acp_mcp_servers()` converts DeerFlow's name→config dict into ACP's list-with-`name` field format. If the ACP protocol version bumps and renames fields (e.g., `type` → `transport`), this conversion silently produces invalid payloads. Is there an ACP version check?

---

## Section 15 — Backend: Sandbox (Phase 1 — Primitives)

- **`execute_command` stdout/stderr merging**: Does `LocalSandbox.execute_command` genuinely merge stdout and stderr into one string, or does it capture them separately and pick one? The `Sandbox` interface docstring says "standard or error output" — ambiguous. Verify in `local/local_sandbox.py`.
- **`str_replace` lock scope**: The lock in `tools.py` is acquired around the `str_replace` operation (line 1564). Does it cover the entire read-modify-write sequence, or only the final write? A TOCTOU race exists if two threads both read before either writes — verify in `tools.py` Phase 3.
- **`update_file` callers**: What calls `update_file` in practice? The interface defines it for binary writes, but no callsite was found in Phase 1. Likely surfaced in Phase 3 (tools) or Phase 5 (AIO sandbox).
- **`id(sandbox)` key collision risk**: `get_file_operation_lock_key` falls back to `f"instance:{id(sandbox)}"` for sandboxes with no `id` attribute. If a sandbox is GC'd and a new one allocated at the same memory address, two distinct sandbox instances could share a lock key. Only a real risk if anonymous sandboxes are used in production (they appear to be test-only), but worth confirming.

## Section 18 — Backend: Persistence Layer (Phase 3 repositories)

- **Backend dict-shape parity**: `MemoryThreadMetaStore` and `ThreadMetaRepository` both return plain `dict`, with parity enforced only by mirrored hand-written builders (`_item_to_dict` vs `_row_to_dict`). Does `test_memory_thread_meta_isolation.py` assert identical key sets between the two backends, or only owner-isolation behaviour? A field added to one and forgotten in the other would not fail to compile.
- **Feedback `rating` has no DB CHECK**: the `+1/-1` invariant is Python-only (`sql.py` raises `ValueError`). A direct DB/migration write of an out-of-range rating would make `aggregate_by_run` report `total > positive + negative` (case()-sum buckets miss it). Acceptable while the repo is the only writer — but should a CHECK be added when Postgres becomes primary?
- **Feedback `created_at` semantics**: `upsert` re-stamps `created_at` on every edit and there is no `updated_at` column, so for an edited rating the field means "last modified", not "first created". Does any consumer rely on it meaning first-created?

## Section 18 — Backend: Persistence Layer (Phase 1 — Foundation)

- **Postgres auto-create matches on error text, not a typed exception**: `engine.py` keys the auto-create-database fallback off `"does not exist" in str(exc)`. Could this substring match unrelated errors (missing table/schema/role)? Would catching asyncpg's typed `InvalidCatalogName` be safer? Low risk (only fires on first boot) but fragile.
- **`create_all` vs schema evolution**: `init_engine` auto-creates tables, but `create_all` is a no-op on existing tables — adding a column to a model will not alter a live DB. There are Alembic migrations in `persistence/migrations/`; how is their state kept consistent with the dev-time `create_all` path? (Defer to migrations study.)
- **Default `@compiles` unreachable today**: `JsonMatch`'s fallback compiler raises `NotImplementedError` for non-sqlite/postgres dialects, but only `memory`/`sqlite`/`postgres` are supported — so it can't fire. Clean fail-closed guard for a future 4th backend; noting intent only.
- **`sqlite_where` partial index is SQLite-only** (carried over from `18b` `UserRow`): if Postgres becomes a prod backend, partial unique indexes need a `postgresql_where` mirror or the predicate is silently ignored.

## Section 19 — Backend: Channels (IM Integrations)

- **ChannelStore read path is unlocked**: `store.py` guards writes with `self._lock` but `get_thread_id`/`list_entries` read `self._data` unlocked. `list_entries` iterating `self._data.items()` during a concurrent `set_thread_id`/`remove` could raise "dict changed size during iteration". Is this concurrently reachable? **Phase 2 confirms it is plausible**: each inbound message is handled in its own `create_task` (`_handle_message`), and threaded SDKs (Slack/Discord) publish via `run_coroutine_threadsafe`, so multiple handlers — plus `/status` calling `get_thread_id` — can touch the store while another writes. Worth a real fix.
- **Service ↔ Manager circular dependency** (`manager.py`/`service.py`): `ChannelService` constructs and owns `ChannelManager`, but `ChannelManager` reaches back into the service via the `get_channel_service()` module global to look up live `Channel` instances (`_channel_supports_streaming`, `receive_file`). This is a service-locator + layering inversion (dependency invisible in the constructor, hence the defensive `if service:`/`if channel:` guards). Not a construction-time cycle (lookup is lazy). Cleaner: inject `channel_lookup: Callable[[str], Channel | None]` into the manager constructor so it depends on an abstraction.
- **`resolve_class(import_path, base_class=None)`** (`service.py:_start_channel`): channel classes are resolved with no base-class validation — no enforcement that the resolved class is a `Channel` subclass. Intentional flexibility or a missing guard? The implicit contract is just the `(bus=, config=)` constructor signature.
- **Per-thread serialization rejects rather than queues** (`manager.py`): `multitask_strategy="reject"` → `ConflictError` → `THREAD_BUSY_MESSAGE`. Is "tell the user to retry" the intended UX for _all_ platforms, including streaming ones (Feishu/WeCom)? Confirm against the adapters in Phase 3.
- **`gateway_url` vs `langgraph_url` asymmetry footgun** (`manager.py`/`service.py`): `langgraph_url` must include `/api` (SDK base that appends subpaths), `gateway_url` must omit it (`_fetch_gateway` call sites write the full `/api/...` path). The two keys look symmetric in `config.yaml` but aren't — setting `gateway_url: http://gateway:8001/api` silently breaks `/models`/`/memory` with `…/api/api/...` 404s. Should this be validated/normalized?

### Phase 3 — `slack.py`

- **No unit test for `SlackChannel`** (`slack.py`): unlike `dingtalk`/`discord`/`wechat`, there is no `test_slack_channel.py`. The store tests only use `"slack"` as a key string. The thread→loop bridge, retry/backoff in `send()`, the bot-loop guard, and `_normalize_allowed_users` coercion are all untested. Worth at least a unit test around `_handle_message_event` (bot-message drop, allowed-user gating, topic_id derivation).
- **`stop()` does not await the connect executor thread** (`slack.py`): `stop()` calls `self._socket_client.close()` and clears the reference, but the `run_in_executor(None, ...connect)` thread is never explicitly joined and `self._running`/`self._loop` teardown is best-effort. Is there a window where an in-flight `_on_socket_event` (already past the `_running` check) still calls `run_coroutine_threadsafe` on a closing loop? Compare with how the other threaded adapter (Discord) shuts down.
- **`send()` is the only adapter method with explicit retry/backoff** (`slack.py:send`, `_max_retries=3`): the base `_on_outbound` already wraps `send()` in try/except. Why does Slack additionally retry internally while other adapters rely solely on the bus-level swallow? Is this Slack-specific rate-limit handling (HTTP 429) or just defensiveness? Note `send_file` has _no_ retry — asymmetric.
- **`send()` failure still raises after the reaction** (`slack.py`): on exhaustion it adds the ❌ reaction and then re-raises `last_exc`, which `base._on_outbound` catches and logs, and crucially _skips file uploads_. Confirm the intended ordering: the ❌ signals failure to the user, but is re-raising (vs returning) load-bearing anywhere beyond the upload-skip?

### Phase 3 — `telegram.py`

- **`/bootstrap` drift** (`telegram.py:62-67`): `/bootstrap` is in `KNOWN_CHANNEL_COMMANDS` and handled by `manager._handle_command`, but Telegram never registers a `CommandHandler` for it. Since PTB's text handler is `filters.TEXT & ~filters.COMMAND`, `/bootstrap` is excluded there too → **silently swallowed** on Telegram. Fix: register PTB handlers by iterating `KNOWN_CHANNEL_COMMANDS` so the two lists can't drift.
- **Running-reply for instant commands** (`telegram.py:_cmd_generic`): `_cmd_generic` calls `_process_incoming_with_reply`, which sends "Working on it..." even for commands like `/help`/`/status` that resolve instantly. Slack only sends a running reply for chat, not commands. Intended for all commands, or only long-running ones?
- **`_last_bot_message` is chat-wide, not topic-wide** (`telegram.py:37,103-112`): the emulated-threading cursor is keyed by `chat_id` only. In a group with two logical `topic_id` threads, the bot's reply chains onto whichever message it last sent in the chat, ignoring the topic split. Also updated by both `send` and `send_file` — concurrent outbounds in one chat could anchor a reply onto the wrong message. Does the manager serialize outbound per chat?

### Phase 3 — `wecom.py`

- **SDK-internals coupling** (`wecom.py:_send_ws_upload_command`): media upload reaches into the private `ws_client._ws_manager.send_reply`, guarded by a version check that raises if absent. Works for `wecom-aibot-python-sdk==0.1.6` but a SDK refactor would break uploads. Is there a public API path, or is pinning the SDK version the intended mitigation?
- **Fallback `send_message` path under streaming** (`wecom.py:_send_ws`): when `thread_ts` is missing or its frame was already cleared, outbound falls back to a proactive `send_message` markdown post instead of patching the stream. Can a late/out-of-order outbound after `_clear_ws_context` (fired on `is_final`) accidentally take this path and post a duplicate standalone message?
- **`generate_req_id` import swallowed** (`wecom.py:_send_ws`, `_upload_media_ws`): the `from aibot import generate_req_id` is wrapped in try/except that sets it to `None` or returns early. If the symbol ever disappears, streaming/upload degrade silently rather than erroring. Intended graceful degradation or a masking risk?
- **`send_file` defers ALL uploads to `is_final`** (`wecom.py:135-137`): returns `True` for non-final messages so `_on_outbound` doesn't log "skipped". Confirm there's no case where a non-final message is the _only_ carrier of an attachment (i.e. attachments always ride the final outbound).

### Phase 3 — `discord.py`

- **`send_file` leaks the file descriptor on failure** (`discord.py:_send_file`): `fp = open(...)` is opened with `# noqa: SIM115` and handed to `discord.File`, relying on the library to own/close it. If `send_future` raises (network/permission), the `except` logs and returns `False` but never closes `fp` — the fd leaks until GC. Should this use a `with` or `try/finally`?
- **Two thread-identity stores, no shared lifecycle** (`discord.py` + `store.py`): Discord persists `channel_id → discord_thread_id` in its own `discord_threads.json`, while `ChannelStore` persists `channel:chat:topic → deerflow_thread_id`. These can drift independently — e.g. the Discord thread is deleted by a user but the ChannelStore mapping survives (or vice versa). Is there any reconciliation, or does the orphaned-thread path silently paper over divergence?
- **Orphaned-thread handling can proliferate threads** (`discord.py:_on_message`): a message in a Discord thread not in `_active_thread_ids` resets routing and creates a _new_ thread. After a restart where `discord_threads.json` failed to load, every existing live thread would be treated as orphaned, spawning a fresh thread per channel on the next message. Bounded by channel count, but is the UX (abandoned threads) acceptable?
- **Fire-and-forget inbound publish** (`discord.py:_publish`): `run_coroutine_threadsafe(...).add_done_callback(log-on-error)` — the future is never awaited and back-pressure is invisible. If `_main_loop` is wedged or the bus queue is unbounded-but-starved, inbound Discord messages are silently dropped/queued without the user ever knowing. Same fire-and-forget shape as `asyncio.create_task(self._add_reaction(...))` and `_start_typing` — none are tracked.
- **`_active_threads` mutated outside the lock** (`discord.py:_on_message`): `_load_active_threads`/`_save_thread` take `_thread_store_lock`, but `_on_message` (on the discord loop) does `self._active_threads[channel_id] = target_thread_id` directly before calling `_save_thread`. Reads/writes of the in-memory dict from the discord loop vs the lock-guarded save path aren't fully serialized — is the single-discord-loop assumption enough to make this safe, or is there a real race with `_load_active_threads` at startup?

### Phase 3 — `dingtalk.py`

- **Streaming correlation rests on an implicit contract** (`dingtalk.py:_make_card_source_key_from_outbound`): inbound and outbound source keys must hash equal for an agent reply to find the card its question opened. Outbound falls back `message_id → thread_ts`. This works only because the manager copies the original `message_id` into outbound metadata. If that ever stops, every streamed reply posts a _duplicate_ card. Should the correlation id be an explicit, single-sourced field rather than two functions that must agree?
- **Card-create-before-publish adds inbound latency** (`dingtalk.py:_prepare_inbound`): the running reply (which creates the AI card and registers `out_track_id`) is awaited _before_ `publish_inbound`, unlike Feishu which fires it non-blockingly. Necessary so `send()` always has a track id — but it serializes card creation in front of dispatch. Is the latency meaningful under load, and could it adopt Feishu's await-in-`send` pattern instead?
- **`_incoming_messages` leak if no outbound arrives** (`dingtalk.py:_on_chatbot_message`): the SDK `chatbot_message` is stashed by `source_key` for card creation and only `pop`ped in `_send_running_reply`. If a message is filtered/dropped after stashing but before the running reply runs, does the entry ever get cleaned up, or does it accumulate?
- **`@`-mentions not passed to group sends** (`dingtalk.py:_send_group_message`): `at_user_ids` is accepted for call-site compatibility but never sent to the API (`sampleMarkdown` can't @mention). Group replies therefore never ping the asker. Intended limitation or a feature gap vs other group-capable adapters?

### Phase 3 — `feishu.py`

- **lark-oapi module-loop monkey-patch is brittle** (`feishu.py:_run_ws`): `_ws_client_mod.loop = loop` overwrites an SDK module global to dodge a uvloop-vs-`run_until_complete` conflict. A lark-oapi refactor of where it reads `loop` would silently break the WS client. Is there a supported way to pass a loop, or is pinning the SDK version the mitigation? (Sibling to WeCom's `_ws_manager.send_reply` reach-in.)
- **`_send_card_message` race matrix is intricate and under-tested** (`feishu.py`): the branch set (card ready / task in-flight / task finished without id / final fallback) handles several orderings between the non-blocking running-card task and incoming outbounds. Which of these branches have explicit test coverage? The "task finished without message_id" path in particular looks easy to regress.
- **Background-task strong-ref set is unbounded in principle** (`feishu.py:_track_background_task`): `_background_tasks` holds refs until the done-callback discards them. If a task hangs (e.g. a wedged `to_thread` API call), it stays referenced indefinitely. Is there any timeout on these reaction/card tasks, or can they pile up?
- **`receive_file` non-local sandbox sync path** (`feishu.py:_receive_single_file`): files are written to the host uploads dir _and_ pushed into a non-local sandbox via `sandbox.update_file`. If the sandbox sync fails, the function returns an error string but the host file already exists — is there a partial-state risk where the agent sees the path but the sandbox lacks the bytes?

### Phase 3 — `wechat.py`

- **`-14` token expiry has no auto-recovery** (`wechat.py:_poll_loop`): on errcode `-14` the channel wipes `bot_token` and sets `_running = False`, stopping entirely. The operator must re-scan the QR or update config and restart. Should expiry instead trigger the QR re-bind flow automatically when `qrcode_login_enabled`?
- **`context_token`-less outbounds are silently dropped** (`wechat.py:send`): without a resolved `context_token` the message can't be delivered, so it's logged and dropped. If the in-memory `_context_tokens_by_*` maps are lost (restart) before an outbound, the agent's reply vanishes with only a warning. Should the token be persisted alongside the cursor/auth state?
- **Hand-rolled AES + multi-encoding key parsing tracks an unstable contract** (`wechat.py:_resolve_media_aes_key`): the resolver tries every field name × hex/base64/urlsafe encoding × nested media. This defensiveness implies the iLink API is inconsistent about the key format. Is there documentation pinning the actual format, or is the shotgun parse load-bearing?
- **Inbound media staged to `state_dir/downloads`, not the thread sandbox** (`wechat.py:_stage_downloaded_file`): unlike Feishu's `receive_file` (which stages into the per-thread sandbox uploads dir and rewrites text to virtual paths), WeChat writes decrypted files to a shared `downloads/` dir under `state_dir` and passes host paths in `files`. Does downstream consumption translate these to sandbox-visible paths, or are WeChat inbound files invisible to the agent's sandbox tools?
- **No `supports_streaming` despite size** — confirm intent: WeChat is one-shot text only. Is incremental/streamed reply simply unsupported by the iLink bot API, or a deferred feature?

## Section 21 — Backend: Community Integrations

- **`image_search` returns thumbnails as "reference images" (likely bug)** (`community/image_search/tools.py`): both `image_url` and `thumbnail_url` map to `r["thumbnail"]`; the full-resolution `r["image"]` field from `ddgs.images()` is discarded. Since the tool's stated purpose is supplying high-quality references *before* image generation, low-res thumbnails undercut that. Should `image_url` be `r.get("image")`?
- **Search-adapter schema drift across providers** (`community/{tavily,ddg_search,serper,exa,firecrawl}/tools.py`): the six `web_search` adapters split into two camps on *both* result shape and error convention — Camp A (tavily/exa/firecrawl): `snippet` key, bare JSON array, `"Error: ..."` string; Camp B (ddg/serper): `content` key, `{query,total_results,results}` envelope, `{"error":...}` JSON. Test docstrings show DDG is the intended template, so Tavily is the outlier. A user swapping providers in `config.yaml` gets different JSON keys/shapes with no normalization layer reconciling them. Intentional, or should a shared normalizer unify them?
- **`web_fetch` 4096-char truncation is hardcoded, not config-driven** (`community/{tavily,exa,firecrawl}/tools.py`): unlike `max_results` (config-overridable), the page-body cap is a fixed `[:4096]` slice with no marker/ellipsis. Should it be promoted to a config knob like `contents_max_characters` (which exa already exposes for search)?
- **Async (Jina) vs sync (InfoQuest) tool implementations** (`community/{jina_ai,infoquest}/tools.py`): Jina is `async def` + `httpx`; InfoQuest is sync `def` + `requests`. Compatibility is already bridged both ways (`_ensure_sync_invocable_tool` attaches a sync wrapper to async tools; LangChain `ainvoke` threadpools sync tools), so the only real stake is **threadpool saturation** under high concurrency. Naively adding `async def` to InfoQuest while keeping `requests` would be _worse_ (blocks the loop). Should both be made async for concurrency, or should Jina be made sync to match InfoQuest and delete its `to_thread` complexity — absent a measured I/O-thread bottleneck?
- **InfoQuest `fetch()` "neither field" path returns raw JSON, not an error** (`community/infoquest/infoquest_client.py`): when the response JSON has neither `reader_result` nor `content`, it logs a warning and falls through to `return response.text`, handing the model raw JSON — inconsistent with every other failure path in the method (which return `"Error: ..."`). Intentional graceful degradation or a gap?
- **InfoQuest is the only adapter that hedges the two-camps schism** (`community/infoquest/infoquest_client.py`): `clean_results` emits _both_ `desc` and `snippet` (snippet=desc) so it satisfies either camp's key reader. Should this double-key hedge become the standard normalization across all search adapters? (Extends the Section 21 schema-drift question above.)
- **`Article.to_message()` (multimodal/vision path) appears unused by web_fetch** (`utils/readability.py`): both Jina and InfoQuest `web_fetch` call only `to_markdown()`; nothing in the fetch path calls `to_message()` (which builds interleaved text/image_url parts for vision models, and reads `self.url` that `__init__` never sets). Who, if anyone, consumes `to_message()`?
