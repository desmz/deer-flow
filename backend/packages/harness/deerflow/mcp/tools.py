"""Load MCP tools using langchain-mcp-adapters."""

import logging

from langchain_core.tools import BaseTool

from deerflow.config.extensions_config import ExtensionsConfig
from deerflow.mcp.client import build_servers_config
from deerflow.mcp.oauth import build_oauth_tool_interceptor, get_initial_oauth_headers
from deerflow.reflection import resolve_variable
from deerflow.tools.sync import make_sync_tool_wrapper

logger = logging.getLogger(__name__)


async def get_mcp_tools() -> list[BaseTool]:
    """Get all tools from enabled MCP servers.

    Returns:
        List of LangChain tools from all enabled MCP servers.
    """
    try:
        # [DL-NOTE] Lazy import makes langchain-mcp-adapters optional; missing install
        # degrades gracefully to an empty tool list rather than a module-level ImportError.
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        logger.warning("langchain-mcp-adapters not installed. Install it to enable MCP tools: pip install langchain-mcp-adapters")
        return []

    # NOTE: We use ExtensionsConfig.from_file() instead of get_extensions_config()
    # to always read the latest configuration from disk. This ensures that changes
    # made through the Gateway API (which runs in a separate process) are immediately
    # reflected when initializing MCP tools.
    extensions_config = ExtensionsConfig.from_file()
    servers_config = build_servers_config(extensions_config)

    if not servers_config:
        logger.info("No enabled MCP servers configured")
        return []

    try:
        # Create the multi-server MCP client
        logger.info(f"Initializing MCP client with {len(servers_config)} server(s)")

        # [DL-INSIGHT] Two-layer OAuth: connection-time header (for transport handshake) + per-call
        # interceptor (for token refresh). SSE/HTTP transports need auth at the protocol level
        # before any tool call; the interceptor alone only fires after the session is established.
        initial_oauth_headers = await get_initial_oauth_headers(extensions_config)
        for server_name, auth_header in initial_oauth_headers.items():
            if server_name not in servers_config:
                continue
            if servers_config[server_name].get("transport") in ("sse", "http"):
                existing_headers = dict(servers_config[server_name].get("headers", {}))
                existing_headers["Authorization"] = auth_header
                servers_config[server_name]["headers"] = existing_headers

        # [DL-NOTE] OAuth interceptor is always first so it runs before any custom interceptors.
        tool_interceptors = []
        oauth_interceptor = build_oauth_tool_interceptor(extensions_config)
        if oauth_interceptor is not None:
            tool_interceptors.append(oauth_interceptor)

        # [DL-INSIGHT] Undocumented extension point: mcpInterceptors in extensions_config.json
        # is not a declared field — it lives in Pydantic's model_extra (extra="allow"). Users can
        # inject custom tool interceptors without modifying DeerFlow's source code.
        # Load custom interceptors declared in extensions_config.json
        # Format: "mcpInterceptors": ["pkg.module:builder_func", ...]
        raw_interceptor_paths = (extensions_config.model_extra or {}).get("mcpInterceptors")
        if isinstance(raw_interceptor_paths, str):
            raw_interceptor_paths = [raw_interceptor_paths]
        elif not isinstance(raw_interceptor_paths, list):
            if raw_interceptor_paths is not None:
                logger.warning(f"mcpInterceptors must be a list of strings, got {type(raw_interceptor_paths).__name__}; skipping")
            raw_interceptor_paths = []
        for interceptor_path in raw_interceptor_paths:
            try:
                builder = resolve_variable(interceptor_path)
                interceptor = builder()
                if callable(interceptor):
                    tool_interceptors.append(interceptor)
                    logger.info(f"Loaded MCP interceptor: {interceptor_path}")
                elif interceptor is not None:
                    logger.warning(f"Builder {interceptor_path} returned non-callable {type(interceptor).__name__}; skipping")
            except Exception as e:
                logger.warning(f"Failed to load MCP interceptor {interceptor_path}: {e}", exc_info=True)

        # [DL-NOTE] tool_name_prefix=True prefixes each tool name with its server name
        # (e.g. "my-server__my-tool") to prevent name collisions across multiple servers.
        client = MultiServerMCPClient(servers_config, tool_interceptors=tool_interceptors, tool_name_prefix=True)

        # Get all tools from all servers
        tools = await client.get_tools()
        logger.info(f"Successfully loaded {len(tools)} tool(s) from MCP servers")

        # [DL-INSIGHT] langchain-mcp-adapters produces async-only tools (coroutine set, func=None).
        # DeerFlowClient's streaming path calls tools synchronously, so each async-only tool gets
        # a sync wrapper that escapes the running event loop via _SYNC_TOOL_EXECUTOR. See tools/sync.py.
        for tool in tools:
            if getattr(tool, "func", None) is None and getattr(tool, "coroutine", None) is not None:
                tool.func = make_sync_tool_wrapper(tool.coroutine, tool.name)

        return tools

    except Exception as e:
        # [DL-NOTE] Total failure tolerance: any exception during client setup or tool fetch
        # returns [] rather than propagating — MCP tools are always optional.
        logger.error(f"Failed to load MCP tools: {e}", exc_info=True)
        return []
