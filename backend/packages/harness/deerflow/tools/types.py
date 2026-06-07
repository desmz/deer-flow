from typing import Any

# [DL-NOTE] ToolRuntime is LangChain's per-tool injection container: .state (ThreadState),
# .context (per-run dict with thread_id/user_id/sandbox_id), .config, .stream_writer, .store.
from langchain.tools import ToolRuntime

from deerflow.agents.thread_state import ThreadState

# Concrete runtime type used by all DeerFlow tools.
# Using dict[str, Any] for the context parameter instead of the unbound ContextT
# TypeVar prevents PydanticSerializationUnexpectedValue warnings when LangChain
# calls model_dump() on a tool's auto-generated args_schema.
# [DL-INSIGHT] .state = LangGraph graph state persisted via checkpoint (survives turns); .context =
# transient per-run dict injected by worker.py at startup (not persisted, carries user_id etc.).
Runtime = ToolRuntime[dict[str, Any], ThreadState]
