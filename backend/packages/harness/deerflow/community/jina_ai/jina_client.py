import logging
import os

import httpx

logger = logging.getLogger(__name__)

# [DL-INSIGHT] Module-level warn-once flag: keyless mode is supported, but the missing-key
# warning fires only once per process (across all instances/calls) to avoid log spam.
# [DL-WARN] Plain global, mutated without a lock — not strictly thread-safe; worst case is a
# duplicate warning. Tests reset it directly (jina_client_module._api_key_warned = False).
_api_key_warned = False


class JinaClient:
    # [DL-INSIGHT] Stateless client — no __init__, no stored key. JINA_API_KEY is read from the
    # env per-call (Path B: vendor-style soft fallback), so the tool layer never passes a key in.
    async def crawl(self, url: str, return_format: str = "html", timeout: int = 10) -> str:
        global _api_key_warned
        headers = {
            "Content-Type": "application/json",
            # [DL-NOTE] Output format is server-side: X-Return-Format=html means Jina returns raw
            # HTML; the tool layer chooses "html" so it can run its own readability extraction.
            "X-Return-Format": return_format,
            "X-Timeout": str(timeout),
        }
        if os.getenv("JINA_API_KEY"):
            headers["Authorization"] = f"Bearer {os.getenv('JINA_API_KEY')}"
        elif not _api_key_warned:
            _api_key_warned = True
            logger.warning("Jina API key is not set. Provide your own key to access a higher rate limit. See https://jina.ai/reader for more information.")
        data = {"url": url}
        try:
            # [DL-NOTE] `timeout` serves double duty: Jina's server-side X-Timeout header AND the
            # httpx client timeout, so the local read won't hang past what the remote was told.
            async with httpx.AsyncClient() as client:
                response = await client.post("https://r.jina.ai/", headers=headers, json=data, timeout=timeout)

            # [DL-INSIGHT] Errors-as-values: every failure path returns an "Error: ..." STRING
            # instead of raising, so the tool layer's startswith("Error:") short-circuit works and
            # the agent reads the failure as a recoverable tool result.
            if response.status_code != 200:
                error_message = f"Jina API returned status {response.status_code}: {response.text}"
                logger.error(error_message)
                return f"Error: {error_message}"

            # [DL-NOTE] Empty/whitespace body treated as failure — a 200 with no content is useless
            # to readability extraction, so guard it before returning.
            if not response.text or not response.text.strip():
                error_message = "Jina API returned empty response"
                logger.error(error_message)
                return f"Error: {error_message}"

            return response.text
        except Exception as e:
            # [DL-INSIGHT] Broad catch logs at WARNING with no traceback (no exc_info) — transient
            # network blips are expected, not bugs; includes type(e).__name__ for triage. Asserted
            # by test_crawl_transient_failure_logs_without_traceback.
            error_message = f"Request to Jina API failed: {type(e).__name__}: {e}"
            logger.warning(error_message)
            return f"Error: {error_message}"
