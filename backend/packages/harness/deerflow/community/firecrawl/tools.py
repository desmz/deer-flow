import json

from firecrawl import FirecrawlApp
from langchain.tools import tool

from deerflow.config import get_app_config


def _get_firecrawl_client(tool_name: str = "web_search") -> FirecrawlApp:
    config = get_app_config().get_tool_config(tool_name)
    api_key = None
    if config is not None and "api_key" in config.model_extra:
        api_key = config.model_extra.get("api_key")
    return FirecrawlApp(api_key=api_key)  # type: ignore[arg-type]


@tool("web_search", parse_docstring=True)
def web_search_tool(query: str) -> str:
    """Search the web.

    Args:
        query: The query to search for.
    """
    try:
        config = get_app_config().get_tool_config("web_search")
        max_results = 5
        if config is not None:
            max_results = config.model_extra.get("max_results", max_results)

        client = _get_firecrawl_client("web_search")
        result = client.search(query, limit=max_results)

        # [DL-NOTE] Structural twin of exa: per-tool config via _get_firecrawl_client(tool_name), SDK env
        # fallback, "snippet"+bare-array shape and "Error:" string errors (tavily camp). getattr(...) reads
        # SDK objects defensively — survives FirecrawlApp result-attr renames where exa uses direct access.
        # result.web contains list of SearchResultWeb objects
        web_results = result.web or []
        normalized_results = [
            {
                "title": getattr(item, "title", "") or "",
                "url": getattr(item, "url", "") or "",
                "snippet": getattr(item, "description", "") or "",
            }
            for item in web_results
        ]
        json_results = json.dumps(normalized_results, indent=2, ensure_ascii=False)
        return json_results
    except Exception as e:
        return f"Error: {str(e)}"


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
    try:
        # [DL-INSIGHT] Firecrawl's niche: scrape() returns clean markdown (formats=["markdown"]) — its
        # value over tavily/exa is rendered-page→markdown conversion, not raw text. No API-level char
        # cap requested; only the [:4096] client slice applies (contrast exa, which caps at both layers).
        client = _get_firecrawl_client("web_fetch")
        result = client.scrape(url, formats=["markdown"])

        markdown_content = result.markdown or ""
        metadata = result.metadata
        title = metadata.title if metadata and metadata.title else "Untitled"

        if not markdown_content:
            return "Error: No content found"
    except Exception as e:
        return f"Error: {str(e)}"

    # [DL-NOTE] Success return sits OUTSIDE the try — title/markdown_content are guaranteed bound here
    # because every in-try exit (exception or empty content) returns first.
    return f"# {title}\n\n{markdown_content[:4096]}"
