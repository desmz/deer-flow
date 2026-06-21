"""
Web Search Tool - Search the web using DuckDuckGo (no API key required).
"""

import json
import logging

from langchain.tools import tool

from deerflow.config import get_app_config

logger = logging.getLogger(__name__)


def _search_text(
    query: str,
    max_results: int = 5,
    region: str = "wt-wt",
    safesearch: str = "moderate",
) -> list[dict]:
    """
    Execute text search using DuckDuckGo.

    Args:
        query: Search keywords
        max_results: Maximum number of results
        region: Search region
        safesearch: Safe search level

    Returns:
        List of search results
    """
    # [DL-INSIGHT] ddgs is imported lazily, not at module top. The optional dependency only loads
    # when the tool actually runs, so wiring a different provider never forces ddgs to be installed.
    try:
        from ddgs import DDGS
    except ImportError:
        logger.error("ddgs library not installed. Run: pip install ddgs")
        return []

    ddgs = DDGS(timeout=30)

    # [DL-NOTE] region/safesearch are hardcoded defaults here — not surfaced to config or the model,
    # unlike max_results. Keyless search trades configurability for zero setup.
    try:
        results = ddgs.text(
            query,
            region=region,
            safesearch=safesearch,
            max_results=max_results,
        )
        return list(results) if results else []

    # [DL-NOTE] All search failures collapse to [] (logged, not raised). The tool layer turns an
    # empty list into a structured "no results" message — the agent never sees a raw exception.
    except Exception as e:
        logger.error(f"Failed to search web: {e}")
        return []


@tool("web_search", parse_docstring=True)
def web_search_tool(
    query: str,
    max_results: int = 5,
) -> str:
    """Search the web for information. Use this tool to find current information, news, articles, and facts from the internet.

    Args:
        query: Search keywords describing what you want to find. Be specific for better results.
        max_results: Maximum number of results to return. Default is 5.
    """
    config = get_app_config().get_tool_config("web_search")

    # [DL-INSIGHT] max_results is BOTH a model-facing tool arg (default 5) and a config override.
    # Config wins when set — the operator can cap the model's requested count. Contrast tavily, which
    # exposes no model-facing arg and reads max_results only from config.
    # Override max_results from config if set
    if config is not None and "max_results" in config.model_extra:
        max_results = config.model_extra.get("max_results", max_results)

    results = _search_text(
        query=query,
        max_results=max_results,
    )

    if not results:
        return json.dumps({"error": "No results found", "query": query}, ensure_ascii=False)

    # [DL-WARN] Schema drift across adapters: this emits "content" but tavily/exa/firecrawl emit
    # "snippet" for the same field. The model sees different key names depending on the wired provider.
    # [DL-NOTE] href/link and body/snippet fallbacks defend against ddgs return-key changes.
    normalized_results = [
        {
            "title": r.get("title", ""),
            "url": r.get("href", r.get("link", "")),
            "content": r.get("body", r.get("snippet", "")),
        }
        for r in results
    ]

    # [DL-NOTE] Result envelope {query,total_results,results} differs from tavily's bare JSON array —
    # another inter-adapter inconsistency. serper follows this envelope convention; tavily does not.
    output = {
        "query": query,
        "total_results": len(normalized_results),
        "results": normalized_results,
    }

    return json.dumps(output, indent=2, ensure_ascii=False)
