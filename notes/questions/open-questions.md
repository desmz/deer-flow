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
