# Model Layer — Phase 3: Provider Implementations

## Purpose

Phase 3 covers the four concrete LLM provider classes that form the bulk of the model
layer. Each wraps a different underlying API and solves a different set of compatibility
problems that LangChain doesn't handle out of the box.

Phases 1–2 established the package surface and the three OpenAI-compatible patch classes
(`PatchedChatOpenAI`, `PatchedChatDeepSeek`, `PatchedChatMiniMax`). Phase 3 goes deeper:
these providers have richer auth flows, streaming quirks, or entirely different wire
protocols that require more invasive engineering.

## Key Files

- `models/claude_provider.py` — OAuth Bearer auth, prompt caching, auto-thinking budget
- `models/vllm_provider.py` — preserves vLLM's `reasoning` field across all three surfaces
- `models/mindie_provider.py` — full bidirectional XML adapter for Huawei MindIE engine
- `models/openai_codex_provider.py` — implements Responses API from scratch on `BaseChatModel`

## Provider Taxonomy

Three distinct patterns appear across the four providers:

```
Pattern 1 — Field patch (extend ChatXxx, override 2–4 methods)
  ClaudeChatModel   extends ChatAnthropic
  VllmChatModel     extends ChatOpenAI

Pattern 2 — Protocol adapter (extend ChatOpenAI, replace message schema)
  MindIEChatModel   extends ChatOpenAI

Pattern 3 — From scratch (extend BaseChatModel, implement full HTTP layer)
  CodexChatModel    extends BaseChatModel
```

The pattern chosen reflects how different the target API is from what LangChain already
handles. Claude and vLLM speak a recognisable dialect; MindIE speaks a different dialect;
Codex speaks a completely different language.

## Important Concepts

### `reasoning` vs `reasoning_content` — two keys, two consumers

All providers that surface reasoning output store it under two keys in
`AIMessage.additional_kwargs`:

| Key                 | Value                                                            | Who reads it                                                                    |
| ------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `reasoning`         | Raw value exactly as the API sent it (may be str, list, or dict) | Re-injection on the next turn — vLLM expects the original structure echoed back |
| `reasoning_content` | Normalized text string (`_reasoning_to_text()`)                  | DeerFlow frontend + downstream prompt injection                                 |

`reasoning` is kept raw because re-injection must be verbatim. `reasoning_content` is the
cross-provider text convention (same key that DeepSeek, MiniMax, and Codex all use).

Empty-string `reasoning = ""` sets `additional_kwargs["reasoning"]` but NOT
`reasoning_content` (falsy string skips the `if reasoning_text` guard in
`_convert_delta_to_message_chunk_with_reasoning`).

### OAuth credential reuse — the shared motivation

`ClaudeChatModel` and `CodexChatModel` both implement the same user-facing value
proposition: re-use an existing CLI tool's authenticated session so the user doesn't need
a separate API key for DeerFlow.

```
ClaudeChatModel  →  ~/.claude/.credentials.json  (Claude Code CLI OAuth)
CodexChatModel   →  ~/.codex/auth.json            (Codex CLI OAuth)
```

`credential_loader.py` (phase 2) provides the loading functions for both. The model layer
picks up whatever the user already has installed. This is the "super agent harness" design
principle: orchestrate across whatever LLM backends the user already has access to.

### Prompt caching requires a static system prompt

`ClaudeChatModel._apply_prompt_caching` places `cache_control: ephemeral` on the last 4
candidates (system text blocks → recent message blocks → last tool). This only works if the
system prompt is identical on every request for the same agent — so DeerFlow bans
per-user and per-turn content from the system prompt entirely. Dynamic context
(`DynamicContextMiddleware`) injects current date and memory into the **first HumanMessage**
as a `<system-reminder>` block instead.

```
System prompt (static, cached):
  "You are DeerFlow, a super agent..."

First HumanMessage (per-turn, not cached):
  <system-reminder>
    Date: 2026-06-14
    <memory>User's name is Alice...</memory>
  </system-reminder>
  [user's actual message]
```

### OAuth disables prompt caching — belt and suspenders

When an OAuth token is detected in `ClaudeChatModel.model_post_init`:

1. `enable_prompt_caching = False` — prevents `_apply_prompt_caching` from running
2. `_create`/`_acreate` call `_strip_cache_control(payload)` before the HTTP call

Both guards exist because the Anthropic API rejects `cache_control` blocks with OAuth tokens.
The first guard handles the normal path; the second is a safety net for test scenarios or
future code paths where caching might be applied before `_create` is reached.

### Streaming is always required for Codex

`CodexChatModel` hardcodes `"stream": True` in every request. The Codex private endpoint
(`chatgpt.com/backend-api/codex/responses`) requires streaming — non-streaming requests
fail. `_stream_response` collects all SSE events synchronously and returns a single
completed dict, so from LangChain's perspective `_generate()` behaves like a normal
blocking call.

### Codex `response.completed.output` is often empty

A documented Codex API quirk: the `response.completed` event's `response.output` list can
arrive empty or incomplete. The actual message content only arrives through
`response.output_item.done` events during the stream. `_stream_response` handles this by:

1. Collecting stream events into `streamed_output_items` (dict indexed by `output_index`)
2. Merging them into `completed_response.output`, only filling slots that are not already
   a dict (so `completed_response` wins where both sources have data)

## Execution Flow

### ClaudeChatModel — request call stack

```
ClaudeChatModel._generate(messages)
  │
  ├─ _patch_client_oauth(_client)          ← re-patch on every call (defensive)
  │
  └─ super()._generate(messages)           ← ChatAnthropic._generate
       │
       ├─ self._get_request_payload()      ← ClaudeChatModel override
       │    ├─ super()._get_request_payload()   ← base LangChain serialization
       │    ├─ _apply_oauth_billing()      ← inject billing block + user_id
       │    ├─ _apply_prompt_caching()     ← stamp cache_control on last-4 candidates
       │    └─ _apply_thinking_budget()    ← fill in budget_tokens if missing
       │
       └─ self._create(payload)            ← ClaudeChatModel override
            ├─ _strip_cache_control()      ← if OAuth: remove cache_control
            └─ super()._create(payload)    ← self._client.messages.create(**payload)
```

`_get_request_payload` and `_create` are called from within `super()._generate()`.
Python's method dispatch means the overridden versions in `ClaudeChatModel` fire even
though the call originates from the parent class.

### vLLM — bidirectional reasoning flow

```
INBOUND (model → LangChain)
─────────────────────────────────────────────────────────────
Non-streaming:
  super()._create_chat_result(response)     ← drops "reasoning"
  → iterate (generation, choice) pairs
  → generation.message.additional_kwargs["reasoning"] = choice["message"]["reasoning"]
  → additional_kwargs["reasoning_content"] = _reasoning_to_text(...)

Streaming:
  _convert_chunk_to_generation_chunk(chunk)
  → _convert_delta_to_message_chunk_with_reasoning(choice["delta"])
  → additional_kwargs["reasoning"] = delta["reasoning"]     ← raw
  → additional_kwargs["reasoning_content"] = text version   ← normalized

OUTBOUND (LangChain → model, multi-turn)
─────────────────────────────────────────────────────────────
  original_messages = self._convert_input(input_).to_messages()   ← snapshot BEFORE parent
  payload = super()._get_request_payload(...)                       ← drops reasoning
  _normalize_vllm_chat_template_kwargs(payload)                     ← thinking → enable_thinking
  for payload_msg, orig_msg in zip(...):
      _restore_reasoning_field(payload_msg, orig_msg)
          → payload_msg["reasoning"] = orig_msg.additional_kwargs.get("reasoning")
             or .get("reasoning_content")  ← fallback
```

### Codex — SSE collection and merge

```
_call_codex_api(messages, tools)
  → _stream_response(headers, payload)
       │
       ├─ open httpx stream to /responses
       │
       ├─ for each SSE line:
       │    _parse_sse_data_line(line) → data dict or None
       │    if type == "response.output_item.done":
       │        streamed_output_items[output_index] = item
       │    if type == "response.completed":
       │        completed_response = data["response"]
       │
       └─ merge:
            merged_output  ← from completed_response.output (may be [])
            pad with None  ← to fit highest output_index from stream
            fill None slots ← from streamed_output_items (dict wins over None)
            filter None    ← remove any remaining None slots
            return completed_response (with patched output)

_parse_response(completed_response)
  for output_item in response["output"]:
      type="reasoning" → reasoning_content += summary[*].text
      type="message"   → content += content[*].output_text
      type="function_call" → _parse_tool_call_arguments → tool_calls / invalid_tool_calls
```

## Architecture Diagram — Provider Comparison

```
Provider           Parent           Auth              Reasoning field    Streaming fix?
─────────────────────────────────────────────────────────────────────────────────────────
ClaudeChatModel    ChatAnthropic    OAuth Bearer /     Anthropic native   No
                                   x-api-key          thinking blocks
VllmChatModel      ChatOpenAI       API key            "reasoning"        Yes (full reimpl)
                                   (standard)         raw + text
MindIEChatModel    ChatOpenAI       API key            None               Yes (tools fallback)
                                   (standard)
CodexChatModel     BaseChatModel    Codex CLI OAuth    "reasoning_content" Always streaming
                                                      from summary items
```

## My Insights

### Three levels of LangChain extension depth

The providers represent a spectrum of how invasive the fix needs to be:

**Level 1 — Override 1–2 methods, inherit everything else** (`VllmChatModel`): The API
is OpenAI-compatible; only specific fields need preservation. Three overrides suffice:
`_get_request_payload`, `_create_chat_result`, `_convert_chunk_to_generation_chunk`.

**Level 2 — Override the whole message input/output schema** (`MindIEChatModel`): The
API is OpenAI-compatible at the transport layer but speaks a different message language
(XML tool calls, no `tool` role). `_generate` and `_agenerate` intercept the message list
before it reaches the parent; `_patch_result_with_tools` intercepts the result after.

**Level 3 — Implement everything** (`CodexChatModel`): The API is a completely different
protocol. No parent method is useful. `BaseChatModel` is chosen specifically because it
imposes minimal structure while satisfying LangChain's `Runnable` interface contract.

### Why `_convert_delta_to_message_chunk_with_reasoning` is a full reimplementation

LangChain's internal `_convert_delta_to_message_chunk` constructs the chunk object and
returns it immediately with no hook to inject custom fields. There's no way to post-process
an already-constructed `AIMessageChunk` and add `additional_kwargs` — the constructor takes
them, but the returned object's `additional_kwargs` dict is immutable in practice.
`VllmChatModel` therefore replaces the entire function rather than wrapping it.

The same constraint drove `MindIEChatModel` to replace `_astream` wholesale rather than
patching streaming output.

### The `user_id` JSON string in ClaudeChatModel

Anthropic's OAuth billing API requires `metadata.user_id` to be a **JSON-encoded string**
containing `{device_id, account_uuid, session_id}` — not a plain string. This mirrors
the Claude Code CLI's wire format exactly. The `device_id` is SHA-256 of the hostname
(stable per machine, anonymized). The `session_id` is a fresh UUID per request — not per
session. Whether this granularity matches Anthropic's billing expectations is unclear.

### MindIE is a full protocol adapter, not a patch

The distinction matters for mental model: every other provider is patching around a gap
in LangChain's model (a field dropped, a format not recognized). MindIE requires a
complete bidirectional translation — the entire message schema going in, the entire
response schema coming out. It's the adapter pattern in the GoF sense.

The 15-character chunk size for simulated streaming is a pragmatic UI heuristic:
large enough to avoid per-character scheduling overhead, small enough that the frontend's
markdown parser gets chunks frequently enough to render smoothly.

### CodexChatModel's `_access_token` — PrivateAttr vs plain annotation

`ClaudeChatModel` uses `PrivateAttr(default=False)` for `_is_oauth` and
`_oauth_access_token`. `CodexChatModel` uses plain `_access_token: str = ""`.

Both approaches keep the field out of Pydantic serialization. The difference:

- `PrivateAttr` is the documented Pydantic v2 mechanism for private instance state
- Plain `_field: type = default` annotations are excluded from the model schema by Pydantic
  v2's convention (underscore prefix = class variable, not model field)

Both work. `PrivateAttr` is more explicit; the plain annotation is more concise. The
test `test_to_json_does_not_leak_access_token` explicitly verifies the Codex approach.

## Dry Run Examples

### ClaudeChatModel — OAuth request with billing block injection

```
Input: messages=[HumanMessage("What is 2+2?")]
       _is_oauth=True, enable_prompt_caching=False

_get_request_payload():
  super()._get_request_payload()  →  payload = {
      "model": "claude-sonnet-4-6",
      "system": "You are DeerFlow...",   ← still a string at this point
      "messages": [{"role": "user", "content": "What is 2+2?"}],
      "max_tokens": 16384,
  }

  _apply_oauth_billing(payload):
    billing_block = {"type": "text", "text": "x-anthropic-billing-header: cc_version=..."}
    system is a string → payload["system"] = [billing_block, {"type": "text", "text": "You are DeerFlow..."}]
    payload["metadata"] = {"user_id": '{"device_id":"abc123...","account_uuid":"deerflow","session_id":"uuid4"}'}

  _apply_prompt_caching():  ← SKIPPED (enable_prompt_caching=False)
  _apply_thinking_budget():  ← SKIPPED (no thinking key in payload)

  payload = {
      "model": "...",
      "system": [{"type": "text", "text": "x-anthropic-billing-header: ..."}, {"type": "text", "text": "You are DeerFlow..."}],
      "messages": [...],
      "max_tokens": 16384,
      "metadata": {"user_id": "{...}"}
  }

_create(payload):
  _is_oauth=True → _strip_cache_control(payload)   ← no-op here (none were added)
  super()._create(payload)  →  self._client.messages.create(**payload)
```

### vLLM — `reasoning` vs `reasoning_content` in streaming

```
vLLM SSE event arrives:
  {"choices": [{"delta": {"role": "assistant", "reasoning": "Let me think...", "content": "42"}}]}

_convert_delta_to_message_chunk_with_reasoning(delta):
  reasoning = delta.get("reasoning")  →  "Let me think..."
  additional_kwargs["reasoning"] = "Let me think..."      ← raw, for re-injection
  reasoning_text = _reasoning_to_text("Let me think...")  →  "Let me think..."  (it's a str)
  additional_kwargs["reasoning_content"] = "Let me think..."  ← text, for frontend

  → AIMessageChunk(content="42", additional_kwargs={
        "reasoning": "Let me think...",
        "reasoning_content": "Let me think..."
    })

Next turn — outgoing payload rebuild:
  original_messages has AIMessage with additional_kwargs["reasoning"] = "Let me think..."
  super()._get_request_payload() → drops reasoning from payload
  _restore_reasoning_field(payload_msg, orig_msg):
      reasoning = orig_msg.additional_kwargs.get("reasoning")  →  "Let me think..."
      payload_msg["reasoning"] = "Let me think..."   ← echoed back to vLLM
```

### Codex — `_stream_response` merge (three cases)

**Case 1 — `response.completed.output` is empty (the Codex API quirk)**

```
Stream events:
  output_index=0 → {type:"reasoning", summary:[{type:"summary_text", text:"I thought..."}]}
  output_index=1 → {type:"message",   content:[{type:"output_text", text:"Answer is 42."}]}
  response.completed → {output:[], model:"gpt-5.4", usage:{...}}

streamed_output_items = {0: {reasoning...}, 1: {message...}}
completed_response    = {output: []}

Merge:
  merged_output = []
  max_index = max(max(0,1), len([])-1) = max(1, -1) = 1
  extend:  [None, None]
  index=0: None → fill  →  {type:"reasoning",...}
  index=1: None → fill  →  {type:"message",...}

final output = [{type:"reasoning"}, {type:"message"}]
```

**Case 2 — Both sources agree: `completed_response` wins**

```
output_index=0 → {type:"message", content:[{text:"Hello"}]}   (stream event)
completed_response.output = [{type:"message", content:[{text:"Hello"}]}]  (same)

Merge:
  merged_output = [{type:"message",...}]   (1 item, from completed_response)
  max_index = max(0, 0) = 0
  extend:  len=1 > max_index=0 → no extend needed
  index=0: existing=dict → IS a dict → SKIP stream event

final output = [{type:"message",...}]   ← completed_response version kept
```

**Case 3 — Partial: `completed_response` has index 0, stream adds index 1**

```
Stream:  {0: {reasoning...}, 1: {message...}}
completed_response.output = [{type:"reasoning",...}]   ← only index 0

Merge:
  merged_output = [{reasoning}]
  max_index = max(max(0,1), 0) = 1
  extend:  [{reasoning}, None]
  index=0: dict → skip
  index=1: None → fill  →  {message...}

final output = [{reasoning}, {message}]
```

## Open Questions

- Does `ClaudeChatModel`'s per-request `session_id` UUID in `metadata.user_id` affect
  Anthropic's billing attribution? The Claude Code CLI presumably sends a stable
  session-scoped UUID; DeerFlow sends a fresh one per API call.
- `CodexChatModel` has no `_agenerate`. If LangGraph ever calls the async path, it falls
  back to LangChain's thread-executor wrapper around sync `_generate`, blocking a thread.
  Is async streaming from Codex ever needed?
- `VllmChatModel._reasoning_to_text` has no recursion depth guard. The `reasoning` key
  in a nested dict recurses into itself — is there a known bound on nesting depth from
  vLLM's actual output?
- Does `PatchedChatMiniMax` need multi-turn `reasoning_content` re-injection (like
  DeepSeek)? The file doesn't override `_get_request_payload` for that purpose.
  (Carried over from [[16a-model-layer-credential-patches]])
- `MindIEChatModel._astream` fallback calls `_agenerate(messages, ...)` with unfixed
  messages, but `_agenerate` itself calls `_fix_messages`. Is `_fix_messages` idempotent
  for already-converted messages?

## Links to Related Sections

- [[16a-model-layer-credential-patches]] — phases 1–2: `__init__`, `credential_loader`,
  `patched_openai`, `patched_deepseek`, `patched_minimax`
- [[16c-model-layer-factory-config]] — phase 4: `factory.py` and `model_config.py`
  (not yet studied)
- [[09c-model-call-wrappers]] — `LLMErrorHandlingMiddleware` wraps the model call;
  errors from all providers surface here
- [[08a-lead-agent]] — `create_chat_model()` called inside `make_lead_agent` with
  `thinking_enabled` from runtime config
- [[10-memory-system]] — memory updater calls `create_chat_model` for a separate
  extraction model instance
