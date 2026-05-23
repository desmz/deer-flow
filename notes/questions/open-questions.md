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
