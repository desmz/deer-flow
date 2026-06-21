import asyncio

from langchain.tools import tool

from deerflow.community.jina_ai.jina_client import JinaClient
from deerflow.config import get_app_config
from deerflow.utils.readability import ReadabilityExtractor

# [DL-NOTE] Module-level singleton: ReadabilityExtractor is stateless, built once at import.
readability_extractor = ReadabilityExtractor()


# [DL-INSIGHT] Same `web_fetch` slot as Tavily/Exa/Firecrawl — the swap contract. But this is
# the only ASYNC adapter (Tavily's web_fetch is sync), because crawl() does network I/O via httpx.
@tool("web_fetch", parse_docstring=True)
async def web_fetch_tool(url: str) -> str:
    """Fetch the contents of a web page at a given URL.
    Only fetch EXACT URLs that have been provided directly by the user or have been returned in results from the web_search and web_fetch tools.
    This tool can NOT access content that requires authentication, such as private Google Docs or pages behind login walls.
    Do NOT add www. to URLs that do NOT have them.
    URLs must include the schema: https://example.com is a valid URL while example.com is an invalid URL.

    Args:
        url: The URL to fetch the contents of.
    """
    jina_client = JinaClient()
    # [DL-NOTE] `timeout` is the one config-driven knob (via open-schema model_extra); default 10s.
    timeout = 10
    config = get_app_config().get_tool_config("web_fetch")
    if config is not None and "timeout" in config.model_extra:
        timeout = config.model_extra.get("timeout")
    # [DL-INSIGHT] Asks Jina for raw HTML, not markdown — DeerFlow runs its OWN readability pass
    # locally. Contrast Tavily, which trusts the vendor's pre-extracted `raw_content`.
    html_content = await jina_client.crawl(url, return_format="html", timeout=timeout)
    # [DL-NOTE] Errors-as-values (Camp A): crawl() returns "Error: ..." strings, never raises.
    # Short-circuit so a failed fetch surfaces to the model as a readable result, not an exception.
    if isinstance(html_content, str) and html_content.startswith("Error:"):
        return html_content
    # [DL-INSIGHT] extract_article shells out to Node's Readability.js (subprocess) — blocking CPU/IO.
    # to_thread offloads it so the event loop isn't stalled. Verified by test_..._offloads_extraction.
    article = await asyncio.to_thread(readability_extractor.extract_article, html_content)
    # [DL-WARN] Same hardcoded 4096-char cap as the other web_fetch adapters; silent, not config-driven.
    return article.to_markdown()[:4096]
