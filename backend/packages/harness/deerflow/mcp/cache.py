"""Cache for MCP tools to avoid repeated loading."""

import asyncio
import logging
import os

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

# [DL-INSIGHT] Module-singleton pattern: four globals act as process-local shared state.
# Each process (Gateway and LangGraph server) holds its own independent cache.
_mcp_tools_cache: list[BaseTool] | None = None
_cache_initialized = False
# [DL-NOTE] asyncio.Lock() at module level is safe in Python 3.10+ — no loop binding at creation.
_initialization_lock = asyncio.Lock()
_config_mtime: float | None = None  # Track config file modification time


def _get_config_mtime() -> float | None:
    """Get the modification time of the extensions config file.

    Returns:
        The modification time as a float, or None if the file doesn't exist.
    """
    # [DL-NOTE] Lazy import breaks potential circular: extensions_config → mcp → cache → extensions_config.
    from deerflow.config.extensions_config import ExtensionsConfig

    config_path = ExtensionsConfig.resolve_config_path()
    if config_path and config_path.exists():
        return os.path.getmtime(config_path)
    return None


# [DL-INSIGHT] Staleness detection uses filesystem mtime instead of TTL. When the Gateway API
# writes extensions_config.json, the LangGraph server process detects the change on the next call.
def _is_cache_stale() -> bool:
    """Check if the cache is stale due to config file changes.

    Returns:
        True if the cache should be invalidated, False otherwise.
    """
    global _config_mtime

    if not _cache_initialized:
        return False  # Not initialized yet, not stale

    current_mtime = _get_config_mtime()

    # If we couldn't get mtime before or now, assume not stale
    if _config_mtime is None or current_mtime is None:
        return False

    # If the config file has been modified since we cached, it's stale
    if current_mtime > _config_mtime:
        logger.info(f"MCP config file has been modified (mtime: {_config_mtime} -> {current_mtime}), cache is stale")
        return True

    return False


async def initialize_mcp_tools() -> list[BaseTool]:
    """Initialize and cache MCP tools.

    This should be called once at application startup.

    Returns:
        List of LangChain tools from all enabled MCP servers.
    """
    global _mcp_tools_cache, _cache_initialized, _config_mtime

    # [DL-INSIGHT] Lock guards against concurrent async callers racing to initialize.
    # This is a double-checked locking pattern: check _cache_initialized inside the lock.
    async with _initialization_lock:
        if _cache_initialized:
            logger.info("MCP tools already initialized")
            return _mcp_tools_cache or []

        # [DL-NOTE] Lazy import of get_mcp_tools breaks circular: mcp.cache ← mcp.tools ← mcp.client.
        from deerflow.mcp.tools import get_mcp_tools

        logger.info("Initializing MCP tools...")
        _mcp_tools_cache = await get_mcp_tools()
        _cache_initialized = True
        _config_mtime = _get_config_mtime()  # Record config file mtime
        logger.info(f"MCP tools initialized: {len(_mcp_tools_cache)} tool(s) loaded (config mtime: {_config_mtime})")

        return _mcp_tools_cache


def get_cached_mcp_tools() -> list[BaseTool]:
    """Get cached MCP tools with lazy initialization.

    If tools are not initialized, automatically initializes them.
    This ensures MCP tools work in both FastAPI and LangGraph Studio contexts.

    Also checks if the config file has been modified since last initialization,
    and re-initializes if needed. This ensures that changes made through the
    Gateway API (which runs in a separate process) are reflected in the
    LangGraph Server.

    Returns:
        List of cached MCP tools.
    """
    global _cache_initialized

    # Check if cache is stale due to config file changes
    if _is_cache_stale():
        logger.info("MCP cache is stale, resetting for re-initialization...")
        reset_mcp_tools_cache()

    if not _cache_initialized:
        logger.info("MCP tools not initialized, performing lazy initialization...")
        try:
            # Try to initialize in the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running (e.g., in LangGraph Studio),
                # we need to create a new loop in a thread
                import concurrent.futures

                # [DL-WARN] Spawning a thread and calling asyncio.run() there escapes the running
                # loop. The async Lock inside initialize_mcp_tools() lives on its own loop in the
                # new thread — so it doesn't guard against the outer loop's concurrent callers.
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, initialize_mcp_tools())
                    future.result()
            else:
                # If no loop is running, we can use the current loop
                loop.run_until_complete(initialize_mcp_tools())
        except RuntimeError:
            # No event loop exists, create one
            try:
                asyncio.run(initialize_mcp_tools())
            except Exception:
                logger.exception("Failed to lazy-initialize MCP tools")
                return []
        except Exception:
            logger.exception("Failed to lazy-initialize MCP tools")
            return []

    return _mcp_tools_cache or []


# [DL-NOTE] Also called by the hot-reload path in get_cached_mcp_tools() when _is_cache_stale() is True.
def reset_mcp_tools_cache() -> None:
    """Reset the MCP tools cache.

    This is useful for testing or when you want to reload MCP tools.
    """
    global _mcp_tools_cache, _cache_initialized, _config_mtime
    _mcp_tools_cache = None
    _cache_initialized = False
    _config_mtime = None
    logger.info("MCP tools cache reset")
