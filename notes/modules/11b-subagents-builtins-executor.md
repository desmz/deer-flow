# Subagents — Phase 2: Built-in Agents & Executor

## Purpose

This note covers the execution layer of the subagent system: the two built-in agent definitions
that ship with DeerFlow, and the `SubagentExecutor` that runs them. The built-ins establish the
two canonical subagent archetypes (general-purpose vs restricted shell specialist); the executor
solves the hardest concurrency problem in the system — running async agent coroutines from inside
an already-running async parent without blocking it.

## Key Files

- `deerflow/subagents/builtins/general_purpose.py` — `GENERAL_PURPOSE_CONFIG`; the default all-tools subagent
- `deerflow/subagents/builtins/bash_agent.py` — `BASH_AGENT_CONFIG`; the sandbox-only command executor
- `deerflow/subagents/builtins/__init__.py` — `BUILTIN_SUBAGENTS` dict; the registry source of truth
- `deerflow/subagents/executor.py` — `SubagentExecutor`, `SubagentResult`, module-level loop/thread globals, cancellation helpers

---

## Built-in Agent Definitions

### `general-purpose` — The Default Workhorse

```python
GENERAL_PURPOSE_CONFIG = SubagentConfig(
    name="general-purpose",
    tools=None,                                               # inherit ALL tools from parent
    disallowed_tools=["task", "ask_clarification", "present_files"],
    model="inherit",
    max_turns=100,
)
```

**What it can do:** Everything the lead agent can do except spawn further subagents, interrupt the
user, or surface files directly. It sees MCP tools, web search, sandbox tools — the full set.

**System prompt design:** Three explicit sections —

- `<guidelines>` — focus on autonomous completion, never ask for clarification
- `<output_format>` — structured summary: accomplishments, findings, file paths, citations
- `<working_directory>` — maps the virtual sandbox paths (`/mnt/user-data/{uploads,workspace,outputs}`)
  and instructs it to prefer relative paths from workspace

The "Do NOT ask for clarification" instruction in the guidelines is what `ask_clarification` in
`disallowed_tools` enforces at the tool level. The two guards are complementary: the prompt is a
hint to the model; the denylist is a hard block.

### `bash` — The Command Specialist

```python
BASH_AGENT_CONFIG = SubagentConfig(
    name="bash",
    tools=["bash", "ls", "read_file", "write_file", "str_replace"],  # strict allowlist
    disallowed_tools=["task", "ask_clarification", "present_files"],
    model="inherit",
    max_turns=60,
)
```

**What it can do:** Only the five sandbox tools. No MCP, no web search, no skills. It is a pure
command executor with a fixed capability surface.

**Why an allowlist here instead of a denylist:** The lead agent has many tools at any given time
(MCP servers, community tools, etc.). An allowlist is safe regardless of what other tools are
registered — the bash agent stays tool-stable even when new tools are added to the platform.

**`max_turns=60` vs `general-purpose`'s 100:** The bash agent runs commands, not reasoning loops.
60 turns is generous for any realistic build/test/deploy pipeline.

### Builtin Comparison

| Field | `general-purpose` | `bash` |
| ----- | ----------------- | ------ |
| `tools` | `None` (inherit all) | `["bash", "ls", "read_file", "write_file", "str_replace"]` |
| `disallowed_tools` | `["task", "ask_clarification", "present_files"]` | same |
| `max_turns` | 100 | 60 |
| `model` | `"inherit"` | `"inherit"` |
| `system_prompt` | Structured output format, citation style | Command-by-command reporting |

Both builtins block `ask_clarification` and `present_files` — subagents must complete autonomously
and return results through their `result` field, not by interrupting the user.

### `BUILTIN_SUBAGENTS` dict — the registry source of truth

```python
BUILTIN_SUBAGENTS = {
    "general-purpose": GENERAL_PURPOSE_CONFIG,
    "bash": BASH_AGENT_CONFIG,
}
```

These are module-level constants. The registry (`registry.py`) reads from this dict and uses
`dataclasses.replace()` to produce modified copies — the originals are never mutated, making them
safe for concurrent access.

---

## Executor: Thread & Event Loop Model

### Three Execution Zones

| Zone | What it is |
| ---- | ---------- |
| **Thread 1 / Loop A** | The FastAPI/LangGraph async event loop — the parent. Calls `execute_async()`. |
| **Thread 2** | A `_scheduler_pool` worker. Runs `run_task()` synchronously. Blocks waiting for subagent completion. |
| **Thread 3 / Loop B** | The `subagent-persistent-loop` daemon thread. Runs `_aexecute` as an asyncio coroutine. |

### Step-by-Step Trace

#### 1 — `execute_async()` on Thread 1 (Loop A)

```python
parent_context = copy_context()   # ← snapshot ContextVars (user_id, etc.) NOW
_scheduler_pool.submit(run_task)  # ← hands off to Thread 2; returns immediately
return task_id                    # ← Thread 1 is FREE again
```

`copy_context()` snapshots the entire `ContextVar` state from Thread 1's current context —
critically including `user_id`. The snapshot is captured **before** `submit`, while Thread 1's
context is still active.

#### 2 — `run_task()` begins on Thread 2

Thread 2's only job is to **block** while waiting for the subagent, so Thread 1 doesn't have to.

```python
def run_task():
    with _background_tasks_lock:
        _background_tasks[task_id].status = RUNNING   # ← visible to Thread 1 polling
        result_holder = _background_tasks[task_id]    # ← shared object

    execution_future = _submit_to_isolated_loop_in_context(
        parent_context,
        lambda: self._aexecute(task, result_holder),
    )
    exec_result = execution_future.result(timeout=self.config.timeout_seconds)  # ← BLOCKS Thread 2
```

Thread 2 blocks here for up to 900 seconds. This is fine because the scheduler pool has 3
workers — one per possible concurrent subagent.

#### 3 — Getting (or creating) Loop B

`_get_isolated_subagent_loop()` is idempotent — it creates the loop and thread once:

```python
with _isolated_subagent_loop_lock:       # ← only one thread creates the loop
    if not loop_is_usable:
        loop = asyncio.new_event_loop()
        started_event = threading.Event()
        thread = threading.Thread(
            target=_run_isolated_subagent_loop,
            args=(loop, started_event),
            daemon=True,
        )
        thread.start()
        started_event.wait(timeout=5)    # ← Thread 2 blocks until Loop B is running
```

Inside Thread 3 (`_run_isolated_subagent_loop`):

```python
asyncio.set_event_loop(loop)
loop.call_soon(started_event.set)  # ← Loop B's first scheduled callback signals readiness
loop.run_forever()                 # ← spins indefinitely, processing coroutines
```

`started_event.wait()` is the synchronization gate — Thread 2 cannot proceed until Loop B
has processed its first callback and called `started_event.set()`.

#### 4 — Submitting the coroutine to Loop B (ContextVar bridge)

```python
def _submit_to_isolated_loop_in_context(context, coro_factory):
    return context.run(
        lambda: asyncio.run_coroutine_threadsafe(coro_factory(), loop)
    )
```

`context.run(fn)` executes `fn` inside the captured parent context. This means
`asyncio.run_coroutine_threadsafe` is called with the parent's ContextVars active on Thread 2.
When asyncio creates a `Handle` via `call_soon_threadsafe`, it captures the current context at
Handle-creation time. When that Handle fires on Thread 3, it runs inside the parent's context,
and `loop.create_task(coro)` captures it for the `_aexecute` Task.

Without `context.run`, Thread 3's empty default context would bleed into `_aexecute`, and
`get_effective_user_id()` would return `"default"` instead of the real user's ID.

`asyncio.run_coroutine_threadsafe` returns a `concurrent.futures.Future` — the bridge between
Thread 2 (sync world) and Loop B (async world).

#### 5 — `_aexecute` runs on Thread 3 / Loop B

Loop B runs `_aexecute` as an asyncio coroutine. It directly mutates `result_holder` — the same
`SubagentResult` stored in `_background_tasks[task_id]` — so Thread 1's polling on the dict sees
live updates:

```python
result.status = SubagentStatus.RUNNING
# ... _build_initial_state, _create_agent, agent.astream() ...
result.status = SubagentStatus.COMPLETED
result.result = "<last AIMessage text>"
```

#### 6 — Cancellation

Thread 1 calls `request_cancel_background_task(task_id)`:

```python
with _background_tasks_lock:
    result.cancel_event.set()        # ← threading.Event; no lock needed on the event itself
```

Thread 3 checks cooperatively at every `astream` iteration boundary:

```python
async for chunk in agent.astream(...):
    if result.cancel_event.is_set():
        result.status = CANCELLED
        return result
```

A slow tool call (e.g. a 30-second bash command) blocks until it returns and the next chunk is
yielded — cancellation is cooperative, not pre-emptive.

#### 7 — Thread 2 unblocks and writes final state

When `_aexecute` returns, the `concurrent.futures.Future` resolves. Thread 2's blocked
`execution_future.result()` unblocks:

```python
with _background_tasks_lock:
    _background_tasks[task_id].status = exec_result.status    # mostly no-op — same object
    _background_tasks[task_id].completed_at = datetime.now() # ← fresh terminal timestamp
```

`exec_result IS result_holder IS _background_tasks[task_id]` — the field assignments are
redundant except for the fresh `completed_at`, which Thread 1's polling uses to confirm terminal
state before reading the result.

### Full Picture

```text
Thread 1 (Loop A — FastAPI/LangGraph)
│
├── execute_async()
│   ├── copy_context()                        ← snapshot ContextVars
│   ├── _background_tasks[id] = PENDING       (under lock)
│   └── _scheduler_pool.submit(run_task) ───────────────────────────► Thread 2
│       return task_id                        ← Thread 1 free; starts polling
│
│   [every 5s: read _background_tasks[id] under lock]
│
Thread 2 (scheduler pool worker)
├── _background_tasks[id].status = RUNNING    (under lock)
├── _submit_to_isolated_loop_in_context()
│   ├── _get_isolated_subagent_loop()
│   │   ├── [first call only] asyncio.new_event_loop()
│   │   ├── Thread(target=loop.run_forever).start() ─────────────────► Thread 3
│   │   └── started_event.wait()              ← BLOCKS until Loop B running
│   └── context.run(lambda: run_coroutine_threadsafe(_aexecute, loop))
│       └── returns concurrent.futures.Future
└── execution_future.result(timeout=900) ── BLOCKS ──────────────────────────────┐
                                                                                  │
Thread 3 (subagent-persistent-loop / Loop B)                                     │
├── loop.run_forever()                                                            │
└── ← _aexecute coroutine scheduled here                                          │
    ├── result_holder.status = RUNNING                                            │
    ├── agent.astream() ...                                                       │
    │   └── [check cancel_event at each iteration boundary]                      │
    ├── result_holder.status = COMPLETED                                          │
    └── return result_holder ────────── resolves Future ─────────────────────────►│
                                                                                  │
Thread 2 unblocks:                                                                │
├── _background_tasks[id].completed_at = now()  (under lock) ◄────────────────────┘
└── run_task() exits

Thread 1 polling detects COMPLETED (under lock) → returns result to lead agent
```

### Synchronization Summary

| Shared resource | Guard | Who uses it |
| --------------- | ----- | ----------- |
| `_background_tasks` dict | `_background_tasks_lock` (Lock) | Threads 1, 2, 3 read/write |
| `result.cancel_event` | `threading.Event` (lock-free) | Thread 1 sets; Thread 3 reads |
| `_isolated_subagent_loop` | `_isolated_subagent_loop_lock` (Lock) | Thread 2 reads/creates; once |
| Loop B startup | `started_event.wait()` (Event) | Thread 2 gates on Thread 3 ready |
| `concurrent.futures.Future` | Internal (asyncio + threading) | Thread 2 waits; Thread 3 resolves |

---

## Important Concepts

### Why a persistent isolated loop instead of `asyncio.run()` per subagent

`asyncio.run()` creates a new event loop, runs the coroutine, then **closes** the loop. Async
resources bound to it (httpx clients, DB connections) are destroyed on close — the next subagent
must reinitialise them. The persistent Loop B pays the creation cost once at startup and shares
resources across all subagent runs for the lifetime of the process.

### Why not run `_aexecute` directly on Loop A

`asyncio.run()` raises `RuntimeError: This event loop is already running` when called inside a
running loop. FastAPI and LangGraph own Loop A — it is always running during request handling.
Submitting to Loop A via `asyncio.ensure_future` would work but the subagent would compete with
the parent's SSE streaming. A slow tool call inside the subagent would starve the parent's output.
Loop B provides isolation: the parent stays responsive regardless of subagent execution time.

### The two concurrency limits

**`SubagentLimitMiddleware`** (upstream, on Thread 1): fires in `after_model` and strips excess
`task` tool calls from the AIMessage *before* they are dispatched. The cap is
`MAX_CONCURRENT_SUBAGENTS = 3`. At most 3 `task` calls reach the tool executor per turn.

**`_scheduler_pool` with 3 workers** (downstream): if all 3 scheduler threads are occupied
(each blocking on a subagent future), a 4th `submit` queues — it waits, not fails. The two
limits are aligned by design: `SubagentLimitMiddleware` prevents the 4th submission from
occurring in normal operation.

All 3 subagent coroutines run **concurrently** (not in parallel) on the single Loop B thread via
asyncio cooperative multitasking. The 3 scheduler threads exist only as "blockers" so Thread 1
stays free.

### Hot-reload guard

```python
_previous_shutdown = globals().get("_shutdown_isolated_subagent_loop")
if callable(_previous_shutdown):
    atexit.unregister(_previous_shutdown)
    _previous_shutdown()
```

When `uvicorn --reload` re-imports the module, new globals replace the old ones but the old Loop
B thread is still running. This block shuts it down before the new module initialises, preventing
an orphaned daemon thread that would persist until process exit.

### `SubagentResult` is the contract between all three threads

`SubagentResult` is a dataclass, not a queue or a channel. It is created on Thread 1, written by
Thread 3 (inside `_aexecute`), read by Thread 2 (after `future.result()` returns), and read by
Thread 1 (polling). The `_background_tasks_lock` serialises all access. The `cancel_event` field
is a `threading.Event` — a lock-free flag that Thread 1 can set and Thread 3 can read without
acquiring the main lock (Events are internally thread-safe via their own internal lock).

## Open Questions

- Does Loop B have any back-pressure if all 3 coroutines are concurrently waiting on
  `asyncio.to_thread` (e.g. heavy disk IO)? The default `ThreadPoolExecutor` inside
  `asyncio.to_thread` uses `min(32, os.cpu_count() + 4)` workers — on a typical machine that's
  around 8–12. Worth verifying this doesn't become a bottleneck under 3 concurrent subagents each
  doing parallel `asyncio.to_thread` calls.
- `cleanup_background_task` is called by `task_tool.py` after polling completes. If the task tool
  crashes mid-poll, `_background_tasks` entries accumulate. Is there a periodic GC sweep? → Check
  `task_tool.py`.

## Links to Related Sections

- [[11a-subagents-primitives]] — `SubagentConfig`, `SubagentTokenCollector`, registry; the shapes
  and accounting the executor consumes
- [[09-middleware-pipeline]] — `SubagentLimitMiddleware` (pos 16) caps concurrent `task` calls
  before they reach the executor
- [[07-langgraph-runtime]] — `RunJournal.record_external_llm_usage_records` is the final
  destination of the executor's collected token records
- [[15-sandbox]] — `is_host_bash_allowed` gates whether `bash` appears in the available names
  list; relevant to bash agent availability
