import json

from langchain.tools import tool
from tavily import TavilyClient

from deerflow.config import get_app_config


# [DL-INSIGHT] api_key comes from the tool's open-schema model_extra (see config/tool_config.py).
# When None, TavilyClient falls back to the TAVILY_API_KEY env var — so config and env both work.
def _get_tavily_client() -> TavilyClient:
    # [DL-NOTE] Config is re-fetched every call (no module-level client). get_app_config() caches
    # + mtime-reloads, so this stays cheap while picking up config.yaml edits without a restart.
    config = get_app_config().get_tool_config("web_search")
    api_key = None
    if config is not None and "api_key" in config.model_extra:
        api_key = config.model_extra.get("api_key")
    return TavilyClient(api_key=api_key)


# [DL-INSIGHT] The tool's registered name "web_search" is the contract: it must match the config
# tool `name` so get_tool_config("web_search") finds its extras, and so swapping Tavily↔DDG↔Serper
# in config.yaml is a drop-in change. parse_docstring=True derives the arg schema from the Args block.
@tool("web_search", parse_docstring=True)
def web_search_tool(query: str) -> str:
    """Search the web.

    Args:
        query: The query to search for.
    """
    config = get_app_config().get_tool_config("web_search")
    max_results = 5
    if config is not None and "max_results" in config.model_extra:
        max_results = config.model_extra.get("max_results")

    client = _get_tavily_client()
    res = client.search(query, max_results=max_results)
    # [DL-INSIGHT] Provider-specific result shape is normalized to {title,url,snippet} — the common
    # schema every community web_search adapter returns, so the model sees one stable format.
    normalized_results = [
        {
            "title": result["title"],
            "url": result["url"],
            "snippet": result["content"],
        }
        for result in res["results"]
    ]
    # [DL-NOTE] Tools must return str; results are serialized to indented JSON. ensure_ascii=False
    # preserves non-Latin text (CJK) instead of \uXXXX escapes — matters for a multilingual product.
    json_results = json.dumps(normalized_results, indent=2, ensure_ascii=False)
    return json_results


@tool("web_fetch", parse_docstring=True)
def web_fetch_tool(url: str) -> str:
    """Fetch the contents of a web page at a given URL.
    Only fetch EXACT URLs that have been provided directly by the user or have been returned in results from the web_search and web_fetch tools.
    This tool can NOT access content that requires authentication, such as private Google Docs or pages behind login walls.
    Do NOT add www. to URLs that do NOT have them.
    URLs must include the schema: https://example.com is a valid URL while example.com is an invalid URL.

    Args:
        url: The URL to fetch the contents of.
    """
    client = _get_tavily_client()
    # [DL-NOTE] Tavily's extract() takes a list; web_fetch is single-URL, so it wraps [url] and
    # reads results[0]. Errors are returned as plain "Error: ..." strings, not raised — the model
    # sees the failure inline as the tool result and can decide how to recover.
    res = client.extract([url])
    if "failed_results" in res and len(res["failed_results"]) > 0:
        return f"Error: {res['failed_results'][0]['error']}"
    elif "results" in res and len(res["results"]) > 0:
        result = res["results"][0]
        # [DL-WARN] Hard 4096-char truncation of page body — silent, no ellipsis/marker. Long pages
        # are clipped; for full-content extraction the jina_ai/infoquest adapters are the alternative.
        return f"# {result['title']}\n\n{result['raw_content'][:4096]}"
    else:
        return "Error: No results found"
