"""
Web search tool used by the Research Agent.

Production changes vs. the notebook version:
- DDGS is a free, unauthenticated, rate-limited service. It WILL occasionally
  throw (timeouts, rate limiting, transient DNS issues). We retry with
  backoff instead of letting one flaky call kill the whole research run.
- Errors are caught and turned into a clear string result instead of an
  unhandled exception, so the agent can gracefully tell the user "no results"
  rather than crashing the pipeline.
"""

from __future__ import annotations

import time

from agents import function_tool
from ddgs import DDGS

from .config import MAX_RETRIES, RETRY_BACKOFF_SECONDS, logger


def _search_with_retries(query: str, max_results: int = 5) -> list[dict]:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return DDGS().text(query, max_results=max_results) or []
        except Exception as exc:  # DDGS can raise several different exception types
            last_error = exc
            logger.warning(
                "search_web attempt %s/%s failed for query=%r: %s",
                attempt, MAX_RETRIES, query, exc,
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)  # simple linear backoff
    logger.error("search_web exhausted retries for query=%r: %s", query, last_error)
    return []


def search_web(query: str) -> str:
    """Search the web using DuckDuckGo and return formatted, readable results."""
    results = _search_with_retries(query, max_results=5)

    if not results:
        return f"No search results found for query: {query!r}"

    formatted_results = [
        f"Title: {r.get('title', 'No title')}\n"
        f"URL: {r.get('href', '')}\n"
        f"Snippet: {r.get('body', '')}"
        for r in results
    ]
    return "\n\n---\n\n".join(formatted_results)


web_search = function_tool(search_web, name_override="web_search")
