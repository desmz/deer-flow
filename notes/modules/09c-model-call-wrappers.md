# Middleware Pipeline — Phase 3: Model Call Wrappers

## Purpose

Two middlewares sit at positions 4 and 5 in the chain and share the same hook: `wrap_model_call`. They surround every LLM invocation — not before it, not after it, but _around_ it. This lets them retry the call, rewrite its inputs, or substitute a synthetic response without the rest of the chain knowing. Neither could do its job with `before_model` or `after_model` alone.

## Key Files

- `agents/middlewares/dangling_tool_call_middleware.py` — pos 4; rewrites the message list before the model sees it
- `agents/middlewares/llm_error_handling_middleware.py` — pos 5; retries transient failures and absorbs terminal errors

---

## DanglingToolCallMiddleware (pos 4)

### What it solves

When a run is interrupted mid-flight (user cancels, network drops), `AIMessage.tool_calls` entries can be left with no corresponding `ToolMessage`. Strict OpenAI-compatible providers reject this with a 400. The middleware detects and patches these gaps _before_ the model call, inserting synthetic error `ToolMessage`s in the correct position.

### Three sources of tool calls

`_message_tool_calls(msg)` normalises tool calls from three distinct locations on an `AIMessage`:

| Source       | Field                                 | When it's used                                                                                                         |
| ------------ | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Structured   | `msg.tool_calls`                      | Always scraped first                                                                                                   |
| Raw provider | `msg.additional_kwargs["tool_calls"]` | Only when `tool_calls` is empty — avoids double-counting the same call in two representations                          |
| Malformed    | `msg.invalid_tool_calls`              | Always appended regardless of `tool_calls` state — malformed calls coexist with valid ones and still need placeholders |

### The patching algorithm

`_build_patched_messages(messages)` does **two jobs**: it fills gaps (inserts synthetic `ToolMessage`s for missing responses) and **reorders** existing `ToolMessage`s to sit immediately after their `AIMessage`. Both are needed because `add_messages` reducer can scatter `ToolMessage`s throughout history.

Three passes:

```
Pass 1 — build id→ToolMessage index from all existing ToolMessages
Pass 2 — collect all tool_call_ids referenced by AIMessages
Pass 3 — rebuild list:
  for each message:
    if ToolMessage AND its id is in tool_call_ids → SKIP (will be re-inserted)
    else → append to patched
    if AIMessage → for each tool_call:
      if existing ToolMessage found in index → re-insert here (reorder)
      else → insert synthetic error ToolMessage (gap-fill)
```

Orphan `ToolMessage`s (whose `tool_call_id` matches no `AIMessage`) pass through unchanged in their original position.

Returns `None` if `patched == messages` (history already in canonical form) — `wrap_model_call` forwards the original request object unmodified.

### Why `wrap_model_call` not `before_model`

Using `before_model` with the `add_messages` reducer would append synthetic `ToolMessage`s to the _tail_ of the message list, not immediately after their `AIMessage`. `wrap_model_call` intercepts the `ModelRequest` object and rebuilds the full list inline. `request.override(messages=patched)` creates a new immutable request — no mutation of the shared object.

### Dry run — broken history patched

**Input history:**

```
[0] AIMessage(tool_calls=[call_1(bash), call_2(read_file)])
[1] HumanMessage("user interrupted here")
[2] ToolMessage(tool_call_id="call_1")   ← exists but displaced
    ← call_2 has NO ToolMessage (dangling)
```

**Pass 1 — index:**

```
tool_messages_by_id = {"call_1": ToolMessage(call_1)}
```

**Pass 2 — tool_call_ids:**

```
tool_call_ids = {"call_1", "call_2"}
```

**Pass 3 — rebuild:**

| Iteration | Message             | Action                                                                                                                                       |
| --------- | ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 0         | AIMessage           | append; then for call_1: re-insert ToolMessage(call_1) from index; for call_2: no entry → insert synthetic ToolMessage(call_2, status=error) |
| 1         | HumanMessage        | append                                                                                                                                       |
| 2         | ToolMessage(call_1) | `tool_call_id in tool_call_ids` → **SKIP** (already re-inserted in iter 0)                                                                   |

**Output:**

```
[0] AIMessage(tool_calls=[call_1, call_2])
[1] ToolMessage(call_1)        ← real, repositioned
[2] ToolMessage(call_2-synth)  ← synthetic, status=error
[3] HumanMessage
```

Both results now sit immediately after their `AIMessage`. The LLM receives a well-formed conversation.

---

## LLMErrorHandlingMiddleware (pos 5)

### What it does

Three layers of resilience around every LLM invocation:

1. **Retry loop** — exponential backoff for transient failures
2. **Circuit breaker** — fast-fail when the provider is continuously down
3. **Error absorption** — terminal failures become `AIMessage` responses, not exceptions

### Error classification

`_classify_error(exc)` returns `(retriable: bool, reason: str)`. Four categories:

| Reason      | Retriable | Example                                    |
| ----------- | --------- | ------------------------------------------ |
| `quota`     | No        | `insufficient_quota`, billing error        |
| `auth`      | No        | invalid API key, 401/403                   |
| `transient` | Yes       | `APIConnectionError`, `ReadError`, 502/503 |
| `busy`      | Yes       | "server busy", "rate limit", "负载较高"    |
| `generic`   | No        | anything else                              |

**Key ordering rule:** quota and auth text are checked _before_ the status code. A quota-rejected 429 (`"insufficient_quota"`) is classified as `quota` (non-retriable) rather than as a 429-based transient — the two behave very differently. Both English and Chinese patterns are matched because DeerFlow targets Chinese LLM providers.

### Retry loop

```
attempt=1 → base delay (1s)
attempt=2 → 2s
attempt=3 → 4s (cap at 8s)
```

`Retry-After` / `Retry-After-Ms` header overrides the computed delay. `_extract_retry_after_ms` handles three formats: numeric ms (header name contains "ms"), numeric seconds, and RFC 2822 HTTP date string. Each retry emits an `llm_retry` custom event via a lazy-imported `get_stream_writer()` so the frontend can render a "retrying…" indicator.

### Error absorption — why return AIMessage?

When retries are exhausted or the error is non-retriable, the middleware returns `AIMessage(content=user_message)` instead of raising. The exception never reaches LangGraph.

```
Normal:   agent node → wrap_model_call → LLM → AIMessage("results")
                                                      ↓ agent continues

Error:    agent node → wrap_model_call → LLM fails × N retries
                                                      ↓
                                    AIMessage("LLM temporarily unavailable...")
                                                      ↓ agent continues
```

The agent node receives an `AIMessage` with plain text and no `tool_calls`. LangGraph sees no tool calls → turn is done → run reaches `END` normally. The user sees a readable message in the chat window rather than an error indicator. This is graceful degradation — the system stays communicative even when the provider is down.

### Circuit breaker

Three-state machine: `closed → open → half_open → closed/open`.

```
                  threshold reached
    closed  ─────────────────────────────► open
       ▲                                    │
       │   probe succeeds                   │ timeout expires
       │                                    ▼
       └──────────────────────────── half_open ──► open
                                       probe fails
```

State is guarded by `threading.Lock` shared by both `wrap_model_call` (sync) and `awrap_model_call` (async).

**Only retriable failures trip the circuit.** Quota/auth failures skip `_record_failure()` — a billing problem is not an infra outage.

**Half-open single-probe mechanic:** when the recovery timeout expires, `_check_circuit()` transitions to `half_open` and lets exactly one request through (`_circuit_probe_in_flight = True`). All concurrent requests fast-fail until that probe resolves.

### Circuit breaker dry run

**Setup:** `circuit_failure_threshold=2`, `circuit_recovery_timeout=10s`, `retry_max_attempts=1`, provider raises 502 (transient).

**Phase 1 — failures accumulate (closed):**

```
Call A: _check_circuit() → closed → proceed
        handler() → 502
        _record_failure(): failure_count = 1 (below threshold)
        return AIMessage("temporarily unavailable")

Call B: _check_circuit() → closed → proceed
        handler() → 502
        _record_failure(): failure_count = 2 → TRIP
          _circuit_state = "open"
          _circuit_open_until = now + 10
        return AIMessage("temporarily unavailable")
```

**Phase 2 — fast-fail (open, t < timeout):**

```
Call C: _check_circuit() → state "open", now < open_until → return True
        → AIMessage("Circuit breaker is engaged...")   ← handler never called
```

**Phase 3 — recovery probe (t > timeout):**

```
Call D (at t+11):
  _check_circuit():
    state "open", now >= open_until → transition to half_open
    probe_in_flight=False → set True, return False   ← probe allowed through

  Concurrent Call D2 at same moment:
    _check_circuit(): half_open + probe_in_flight=True → return True → fast-fail

Call D — probe succeeds:
  handler() → AIMessage("ok")
  _record_success(): failure_count=0, state="closed"   ← fully recovered

Call D — probe fails instead:
  handler() → 502
  _record_failure(): state=="half_open" → state="open", new timeout
```

### GraphBubbleUp — why it must be re-raised

`GraphBubbleUp` is LangGraph's internal control-flow exception. It is not an error.
The `GraphBubbleUp` guard in `wrap_model_call` is for control-flow signals that originate _within_ the LLM call itself — for example, a `NodeInterrupt` raised during streaming callbacks — not for the clarification intercept (which happens later in the tool phase).

---

## My Insights

### Same hook, opposite problems

Both middlewares use `wrap_model_call` but solve opposite failure modes: `DanglingToolCallMiddleware` fixes malformed _inputs_ (message history gaps); `LLMErrorHandlingMiddleware` fixes malformed _outputs_ (provider errors). Together they make the LLM invocation robust from both sides.

### `wrap_model_call` is the retry boundary

`wrap_model_call` is the only hook that can call `handler` multiple times. `before_model` fires once and can't loop. `after_model` fires after the call and can't restart it. This is why retry logic must live in `wrap_model_call`.

### Absorption vs propagation

`LLMErrorHandlingMiddleware` establishes a clear policy: everything except `GraphBubbleUp` is absorbed. No LLM provider error ever reaches the LangGraph runtime as an exception. This keeps run states clean — runs end in `success` or `interrupted`, never in an unhandled exception crash.

### Circuit breaker scope

The circuit breaker lives on the middleware instance, which is created once per agent construction. In the LangGraph Server HTTP path, a new agent is created per request (`make_lead_agent()`), so each user session gets a fresh circuit. A process-level or cross-user circuit would require the instance to be shared at a higher scope.

---

## Open Questions

- The circuit breaker is per-instance (per agent construction). A provider outage affects every user, but each user's circuit counts failures independently — user A's failures don't trip user B's circuit. Is a process-level shared circuit on the roadmap?
- `time.sleep` in `wrap_model_call` (sync) blocks the calling thread. In the LangGraph HTTP path this runs on a uvicorn worker thread, so blocking is acceptable. Is there a scenario where the sync path could run on the event loop?
- `patched == messages` comparison in `_build_patched_messages` relies on `BaseMessage.__eq__`. For long threads with hundreds of messages, is this O(n) deep equality comparison a concern before every model call?

## Links to Related Sections

- [[09a-middleware-pipeline-overview]] — chain assembly and execution order context
- [[09b-before-agent-middlewares]] — Phase 2 middlewares (ThreadData, Uploads, Sandbox, DynamicContext)
- [[15-sandbox]] — `SandboxMiddleware` (pos 3) is the infrastructure that pos 4 and 5 sit just above
