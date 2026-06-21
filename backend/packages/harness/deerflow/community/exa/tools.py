import json

from exa_py import Exa
from langchain.tools import tool

from deerflow.config import get_app_config


# [DL-INSIGHT] tool_name is parameterized so web_search and web_fetch read SEPARATE config entries
# (each may carry its own api_key). First adapter to support distinct configs per tool, not one shared.
# api_key=None lets the Exa SDK fall back to EXA_API_KEY env — same SDK-delegation pattern as tavily.
def _get_exa_client(tool_name: str = "web_search") -> Exa:
    config = get_app_config().get_tool_config(tool_name)
    api_key = None
    if config is not None and "api_key" in config.model_extra:
        api_key = config.model_extra.get("api_key")
    return Exa(api_key=api_key)


@tool("web_search", parse_docstring=True)
def web_search_tool(query: str) -> str:
    """Search the web.

    Args:
        query: The query to search for.
    """
    try:
        # [DL-INSIGHT] Richest config surface of the search adapters: beyond max_results it reads
        # search_type (auto/neural/keyword) and contents_max_characters — all carried on model_extra
        # via the open-schema ToolConfig, proving extras scale to provider-specific knobs with no schema change.
        config = get_app_config().get_tool_config("web_search")
        max_results = 5
        search_type = "auto"
        contents_max_characters = 1000
        if config is not None:
            max_results = config.model_extra.get("max_results", max_results)
            search_type = config.model_extra.get("search_type", search_type)
            contents_max_characters = config.model_extra.get("contents_max_characters", contents_max_characters)

        client = _get_exa_client()
        res = client.search(
            query,
            type=search_type,
            num_results=max_results,
            contents={"highlights": {"max_characters": contents_max_characters}},
        )

        # [DL-NOTE] Neural search returns highlight spans, not one body blob — joined with \n into snippet.
        # Emits "snippet" + bare array → follows the tavily shape, NOT ddg/serper's "content"+envelope.
        normalized_results = [
            {
                "title": result.title or "",
                "url": result.url or "",
                "snippet": "\n".join(result.highlights) if result.highlights else "",
            }
            for result in res.results
        ]
        json_results = json.dumps(normalized_results, indent=2, ensure_ascii=False)
        return json_results
    # [DL-NOTE] Whole body wrapped in try/except → "Error: ..." string (tavily-style), unlike serper/ddg
    # which return structured {"error":...} JSON. Confirms two error conventions split along the same camps.
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
        # [DL-NOTE] Passes "web_fetch" so a distinct config entry (and its own api_key) can apply.
        # 4096-char cap is requested via the API (text max_characters) AND re-clamped below — double guard.
        client = _get_exa_client("web_fetch")
        res = client.get_contents([url], text={"max_characters": 4096})

        if res.results:
            result = res.results[0]
            title = result.title or "Untitled"
            text = result.text or ""
            return f"# {title}\n\n{text[:4096]}"
        else:
            return "Error: No results found"
    except Exception as e:
        return f"Error: {str(e)}"
