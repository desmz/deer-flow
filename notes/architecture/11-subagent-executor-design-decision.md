# Architectural Decision: Why DeerFlow Built Its Own Subagent Executor

> **Type:** Architectural Decision Record
> **Scope:** `deerflow/subagents/executor.py` + `task_tool.py`
> **Related sections:** [[11a-subagents-primitives]], [[11b-subagents-executor]]

## Context

LangChain provides a straightforward pattern for subagents: wrap a sub-agent as a `@tool`,
call `subagent.invoke()` inside it, return the last message. Five lines of code.

```python
@tool("research", description="Research a topic")
def call_research_agent(query: str):
    result = subagent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content
```

DeerFlow's subagent system is ~800 lines. This document records why.

## The Gaps

### 1 — The event loop nesting problem (the core driver)

LangGraph and FastAPI both run inside an `asyncio` event loop. Python forbids calling
`asyncio.run()` from inside a running loop. LangChain's basic `invoke()` pattern silently
assumes a synchronous caller. In DeerFlow's environment, every subagent call originates
from inside LangGraph's async graph — so `asyncio.run()` crashes immediately.

**DeerFlow's solution:** A single persistent event loop running in a daemon thread
(`subagent-persistent-loop`). All subagent coroutines are submitted to it via
`asyncio.run_coroutine_threadsafe()` from a `_scheduler_pool` worker thread. This is the
structural foundation of `executor.py`; everything else follows from it.

### 2 — Background execution with a single polling tool

LangChain's docs describe a conceptual "three-tool async pattern" (start/check/get result)
but provide no implementation. Leaving this to the LLM means the model must manually manage
job IDs across three separate tool calls, which is fragile and verbose.

**DeerFlow's solution:** `execute_async()` starts the background task and stores a
`SubagentResult` in a module-level `_background_tasks` registry. The lead agent calls one
`task` tool; `task_tool.py` handles the polling loop internally (every 5 seconds, up to the
15-minute timeout). Background mechanics are invisible to the LLM.

### 3 — Token attribution across agent boundaries

When a subagent makes LLM calls, those tokens are invisible to the parent run's monitoring
in the basic LangChain pattern. At scale (multiple concurrent subagents, long tasks) this
produces significant gaps in token usage reporting.

**DeerFlow's solution:** `SubagentTokenCollector` — a LangChain callback injected into the
subagent's `run_config.callbacks`. It captures every `on_llm_end` event inside the subagent
and accumulates records in `SubagentResult.token_usage_records`. After the subagent
completes, `task_tool.py` reads those records and calls
`RunJournal.record_external_llm_usage_records()` on the parent run's journal. The full
attribution chain spans four hops across the thread boundary.

### 4 — Middleware inheritance

DeerFlow's lead agent runs through 18+ middlewares: guardrails, tool error handling,
dangling tool call patching, loop detection, sandbox audit. The subagent needs a subset of
these. Without middleware reuse, a raw exception from a tool inside a subagent would abort
the subagent run with no structured error message back to the lead agent.

**DeerFlow's solution:** `build_subagent_runtime_middlewares()` reuses the same
`_build_runtime_middlewares()` factory as the lead agent, omitting only what doesn't apply
to subagents (uploads, summarization, subagent limit, clarification). A plain `@tool`
wrapper has no hook into this pipeline.

### 5 — Platform context: sandbox, ContextVars, ThreadState

DeerFlow subagents share the parent's sandbox (same user filesystem, same `thread_id`) and
need the parent's `user_id` ContextVar to route to the correct user's memory and sandbox
paths. LangChain has no model for per-user isolation, sandbox lifecycle, or ContextVar
propagation across thread boundaries.

**DeerFlow's solution:**

- `copy_context()` captures the calling thread's full ContextVar snapshot (including
  `user_id`) and `context.run()` restores it on the isolated loop thread before the
  coroutine is created.
- `sandbox_state` and `thread_data` from the lead agent's `ThreadState` are passed
  directly into `_build_initial_state()` and injected into the subagent's initial state.
- The subagent uses `ThreadState` (with `sandbox`, `thread_data`, `artifacts` fields) as
  its state schema — not bare `AgentState` — because the middleware pipeline and sandbox
  tools require those fields.

## What LangChain Provides

DeerFlow does not reinvent the agent. Inside `SubagentExecutor._create_agent()`:

```python
return create_agent(
    model=model,
    tools=tools,
    middleware=middlewares,
    system_prompt=None,
    state_schema=ThreadState,
)
```

`create_agent` is standard LangChain. `SubagentExecutor` is the production harness
around it — solving the five problems above that LangChain's pattern leaves to the caller.

## The Design Principle This Reflects

This is the clearest single-file demonstration of DeerFlow's general architectural split:

> **LangChain/LangGraph provides the agent runtime primitive. The `deerflow-harness`
> package provides the production-grade infrastructure layer on top.**

The pattern repeats throughout the codebase:

- Middleware pipeline wraps `create_agent` in 18 layers LangChain knows nothing about
- `StreamBridge` wraps LangGraph's event stream for SSE delivery
- `RunManager` wraps LangGraph graph invocation with lifecycle, persistence, and observability
- `SubagentExecutor` wraps `create_agent` for safe multi-tenant async execution

The subagent executor is the most self-contained example because the gap is visible:
the LangChain pattern is ~5 lines; the production-grade version is ~800 lines.

## The Gap as a Medium Article Angle

The five-line LangChain pattern works in a notebook. The gap to production includes:

| Concern              | LangChain pattern            | DeerFlow's answer                              |
| -------------------- | ---------------------------- | ---------------------------------------------- |
| Event loop isolation | Not addressed                | Persistent isolated loop in daemon thread      |
| Background execution | Conceptual (not implemented) | `execute_async` + `_background_tasks` registry |
| Token attribution    | Invisible                    | `SubagentTokenCollector` + 4-hop transfer      |
| Middleware reuse     | Not applicable               | `build_subagent_runtime_middlewares()`         |
| Platform context     | Not applicable               | `copy_context()` + `ThreadState` passthrough   |

The article angle: _"What does it actually take to run subagents safely in a multi-tenant
async production system?"_ The answer is this file.
