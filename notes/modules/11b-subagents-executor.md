# Subagents — Phase 2: Executor Thread & Event Loop Model

## Purpose

`SubagentExecutor` is the background execution engine for subagents. Its core design challenge
is running async agent coroutines (`_aexecute`) from inside an already-running async parent
(FastAPI/LangGraph), without blocking the parent loop and without creating a new event loop per
execution. It solves this with a three-zone concurrency model: a scheduler thread pool, a single
persistent isolated asyncio loop, and a shared result object protected by a lock.

## Key Files

- `deerflow/subagents/executor.py` — `SubagentExecutor`, `SubagentResult`, `SubagentStatus`, module-level thread/loop globals, `execute_async`, `_aexecute`, cancellation helpers

## Three Execution Zones

| Zone                  | What it is                                                                                           |
| --------------------- | ---------------------------------------------------------------------------------------------------- |
| **Thread 1 / Loop A** | The FastAPI/LangGraph async event loop — the parent. Calls `execute_async()`.                        |
| **Thread 2**          | A `_scheduler_pool` worker. Runs `run_task()` synchronously. Blocks waiting for subagent completion. |
| **Thread 3 / Loop B** | The `subagent-persistent-loop` daemon thread. Runs `_aexecute` as an asyncio coroutine.              |

## Execution Flow

### 1 — `execute_async()` on Thread 1 (Loop A)

```python
parent_context = copy_context()   # ← snapshot of ContextVars (user_id, etc.) RIGHT NOW
_scheduler_pool.submit(run_task)  # ← hand off to Thread 2; returns immediately
return task_id                    # ← Thread 1 is FREE again
```

`copy_context()` snapshots the entire `ContextVar` state from Thread 1's current context —
critically including `user_id`. This snapshot is captured **before** `submit`, while Thread 1's
context is still active.

---

### 2 — `run_task()` begins on Thread 2

Thread 2 is a scheduler worker. Its only real job is to **block** while waiting for the subagent
to finish, so Thread 1 doesn't have to.

```python
def run_task():
    with _background_tasks_lock:
        _background_tasks[task_id].status = RUNNING   # ← visible to polling on Thread 1
        result_holder = _background_tasks[task_id]    # ← shared object

    execution_future = _submit_to_isolated_loop_in_context(
        parent_context,
        lambda: self._aexecute(task, result_holder),
    )
    exec_result = execution_future.result(timeout=self.config.timeout_seconds)  # ← BLOCKS Thread 2
```

Thread 2 blocks on `execution_future.result()`. It stays blocked for up to 900 seconds (the
subagent timeout). This is fine because the scheduler pool has 3 workers — one per possible
concurrent subagent.

---

### 3 — Getting (or creating) Loop B

`_submit_to_isolated_loop_in_context` calls `_get_isolated_subagent_loop()` which does this
**once** (idempotently):

```python
with _isolated_subagent_loop_lock:   # ← only one thread creates the loop
    if not loop_is_usable:
        loop = asyncio.new_event_loop()
        started_event = threading.Event()
        thread = threading.Thread(target=_run_isolated_subagent_loop, args=(loop, started_event), daemon=True)
        thread.start()
        started_event.wait(timeout=5)   # ← Thread 2 blocks here briefly until Loop B is running
```

Inside Thread 3:

```python
def _run_isolated_subagent_loop(loop, started_event):
    asyncio.set_event_loop(loop)
    loop.call_soon(started_event.set)   # ← schedules the signal as Loop B's first task
    loop.run_forever()                  # ← Loop B now spins indefinitely
```

`started_event.wait()` on Thread 2 is the **synchronization gate** — Thread 2 cannot proceed
until Loop B has actually started. Once `started_event.set()` fires (Loop B's first scheduled
callback), Thread 2 unblocks and receives the loop reference.

The loop is created **once** and reused across all subagent runs. `_isolated_subagent_loop_lock`
prevents two scheduler threads from racing to create it simultaneously.

---

### 4 — Submitting the coroutine to Loop B (the ContextVar bridge)

```python
def _submit_to_isolated_loop_in_context(context, coro_factory):
    return context.run(
        lambda: asyncio.run_coroutine_threadsafe(coro_factory(), loop)
    )
```

`context.run(fn)` executes `fn` **inside the captured parent context**. This means
`asyncio.run_coroutine_threadsafe` is called with the parent's ContextVars active on Thread 2.
When asyncio internally creates a `Handle` for the callback via `call_soon_threadsafe`, it
captures the current context at Handle-creation time — which is the parent's context. When that
Handle fires on Thread 3, it runs inside the parent's context, and `loop.create_task(coro)`
captures it for the `_aexecute` Task.

Without `context.run`, Thread 3's empty default context would bleed into `_aexecute`, and
`get_effective_user_id()` would return `"default"` instead of the real user's ID.

`asyncio.run_coroutine_threadsafe` returns a `concurrent.futures.Future` — the bridge between
Thread 2 (sync world) and Loop B (async world). Thread 2 holds this future.

---

### 5 — `_aexecute` runs on Thread 3 / Loop B

Loop B now runs `_aexecute` as an asyncio coroutine. It directly mutates the `result_holder`
object (the same `SubagentResult` in `_background_tasks[task_id]`):

```python
result.status = SubagentStatus.RUNNING
# ... agent.astream() ...
result.status = SubagentStatus.COMPLETED
result.result = "..."
```

Simultaneously, `task_tool.py` on Thread 1 is polling `_background_tasks[task_id]` every 5
seconds. Both sides access `_background_tasks` under `_background_tasks_lock`.

---

### 6 — Cancellation

If Thread 1 calls `request_cancel_background_task(task_id)`:

```python
with _background_tasks_lock:
    result.cancel_event.set()   # ← threading.Event, no lock needed for the event itself
```

On Thread 3, inside `agent.astream()`:

```python
async for chunk in agent.astream(...):
    if result.cancel_event.is_set():   # ← checked at each iteration boundary
        result.status = CANCELLED
        return result
```

`threading.Event` is thread-safe without a lock. The only constraint is that cancellation only
fires at `astream` iteration boundaries — a slow tool call inside an iteration (e.g. a 30-second
bash command) will complete before the check runs.

---

### 7 — Thread 2 unblocks and writes final state

When `_aexecute` returns, `execution_future` resolves. Thread 2's blocked
`execution_future.result()` returns `exec_result`.

```python
with _background_tasks_lock:
    _background_tasks[task_id].status = exec_result.status   # redundant — same object
    _background_tasks[task_id].completed_at = datetime.now() # ← fresh timestamp
```

Since `exec_result IS result_holder IS _background_tasks[task_id]`, most of these are no-ops —
the object was mutated in-place by `_aexecute`. The one meaningful update is the fresh
`completed_at` timestamp stamped under the lock, which is what Thread 1's polling uses to confirm
terminal state.

---

## Full Picture

```text
Thread 1 (Loop A — FastAPI/LangGraph)
│
├── execute_async()
│   ├── copy_context()              ← snapshot ContextVars
│   ├── _background_tasks[id] = PENDING  (under lock)
│   └── _scheduler_pool.submit(run_task) ──────────────────────────► Thread 2
│       return task_id              ← Thread 1 free; starts polling
│
│   [every 5s: read _background_tasks[id] under lock]
│
Thread 2 (scheduler pool worker)
├── _background_tasks[id].status = RUNNING  (under lock)
├── _submit_to_isolated_loop_in_context()
│   ├── _get_isolated_subagent_loop()
│   │   ├── [first call only] asyncio.new_event_loop()
│   │   ├── Thread(target=_run_isolated_subagent_loop).start() ───► Thread 3
│   │   └── started_event.wait()    ← BLOCKS until Loop B running
│   └── context.run(lambda: run_coroutine_threadsafe(_aexecute, loop))
│       └── returns concurrent.futures.Future
└── execution_future.result(timeout=900) ── BLOCKS ─────────────────────────────┐
                                                                                 │
Thread 3 (subagent-persistent-loop / Loop B)                                    │
├── loop.run_forever()                                                           │
├── ← _aexecute coroutine scheduled here                                         │
│   ├── result_holder.status = RUNNING                                           │
│   ├── agent.astream()...                                                       │
│   │   └── [check cancel_event at each iteration boundary]                     │
│   ├── result_holder.status = COMPLETED                                         │
│   └── return result_holder    ─────── resolves Future ──────────────────────► │
                                                                                 │
Thread 2 unblocks:                                                               │
├── _background_tasks[id].completed_at = now()  (under lock) ◄──────────────────┘
└── run_task() exits

Thread 1 polling detects COMPLETED (under lock) → returns result to lead agent
```

## Synchronization Summary

| Shared resource             | Guard                                 | Who uses it                       |
| --------------------------- | ------------------------------------- | --------------------------------- |
| `_background_tasks` dict    | `_background_tasks_lock` (Lock)       | Threads 1, 2, 3 all read/write    |
| `result.cancel_event`       | `threading.Event` (lock-free)         | Thread 1 sets; Thread 3 reads     |
| `_isolated_subagent_loop`   | `_isolated_subagent_loop_lock` (Lock) | Thread 2 reads/creates; only once |
| Loop B startup              | `started_event.wait()` (Event)        | Thread 2 gates on Thread 3 ready  |
| `concurrent.futures.Future` | Internal (asyncio + threading)        | Thread 2 waits; Thread 3 resolves |

## Important Concepts

### Why a persistent isolated loop instead of `asyncio.run()` per subagent

`asyncio.run()` creates a fresh event loop, runs the coroutine, then **closes** the loop. Any
async resource bound to that loop (httpx clients, database connections) is destroyed. The next
subagent execution would need to reinitialise everything.

The persistent Loop B sidesteps this: shared async resources live as long as the loop lives
(which is the process lifetime). The cost of loop creation and teardown is paid once at startup,
not per subagent.

### Why not run `_aexecute` directly on Loop A

`asyncio.run()` cannot be called when a loop is already running (Python raises
`RuntimeError: This event loop is already running`). FastAPI and LangGraph own Loop A and it is
always running during request handling. Submitting to Loop A via `asyncio.ensure_future` would
work but would mean the subagent competes for the same event loop as the parent — a slow subagent
tool call would starve the parent's SSE streaming.

Loop B provides isolation: the parent's responsiveness is independent of subagent execution time.

### The two concurrency limits

**`SubagentLimitMiddleware`** (upstream, on Thread 1): fires in `after_model` and truncates
excess `task` tool calls from the AIMessage before they're dispatched. The hard cap is
`MAX_CONCURRENT_SUBAGENTS = 3` — at most 3 `task` calls reach the tool executor per turn.

**`_scheduler_pool` with 3 workers** (downstream): if all 3 scheduler threads are occupied
(each blocking on a subagent future), a 4th `submit` queues in the pool — it waits, not fails.
The two limits are aligned: `SubagentLimitMiddleware` prevents the 4th submission from happening
in normal operation.

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

When `uvicorn --reload` re-imports the module, the new module's globals replace the old ones —
but the old Loop B thread is still running. This block shuts down the previous loop before the
new module-level globals are initialised, preventing an orphaned daemon thread.

## Open Questions

- Does the isolated Loop B have any back-pressure mechanism if all 3 coroutines are CPU-bound
  (e.g. all doing heavy file IO via `asyncio.to_thread`)? The `ThreadPoolExecutor` inside
  `asyncio.to_thread` has its own worker limit — worth checking what the default is.
- `cleanup_background_task` removes completed entries from `_background_tasks`. If `task_tool.py`
  crashes before calling cleanup, entries accumulate indefinitely. Is there a periodic GC? → Check
  `task_tool.py`.

## Links to Related Sections

- [[11a-subagents-primitives]] — `SubagentConfig`, `SubagentTokenCollector`, registry; the config
  shapes and token accounting that the executor consumes
- [[09-middleware-pipeline]] — `SubagentLimitMiddleware` (pos 16) caps concurrent `task` calls
  upstream of the executor
- [[07-langgraph-runtime]] — `RunJournal.record_external_llm_usage_records` is the final
  destination of `token_usage_records` after the executor snapshots them
