"""
tools/search.py — Web search tool with Tavily primary, DuckDuckGo fallback.

Key improvement over original:
  • Returns structured results with URLs so the writer can cite sources properly.
  • Graceful fallback if both services fail.
"""

import os
from langchain.tools import tool
from utils.logger import get_logger

log = get_logger("tool.search")


def _get_search_backend():
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if tavily_key:
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults
            log.info("Search backend: Tavily")
            return TavilySearchResults(
                max_results=6,
                search_depth="advanced",
                include_answer=True,
                include_raw_content=False,
            )
        except Exception as e:
            log.warning(f"Tavily init failed ({e}), falling back to DuckDuckGo")

    from langchain_community.tools import DuckDuckGoSearchRun
    log.info("Search backend: DuckDuckGo")
    return DuckDuckGoSearchRun()


_search_backend = _get_search_backend()


@tool
def web_search(query: str) -> str:
    """
    Search the web for current information on a topic.
    Use this to find recent news, facts, statistics, and sources.
    Run at least 3-5 DIFFERENT queries to cover a topic from multiple angles.
    Input: a specific search query string (keep it concise, 4-8 words).
    Returns: search snippets with source URLs where available.
    """
    log.debug(f"web_search: {query!r}")
    try:
        results = _search_backend.run(query)
        if not results or len(results) < 20:
            return f"No useful results for: {query!r}. Try rephrasing the query."
        return results
    except Exception as e:
        log.error(f"Search failed: {e}")
        return f"Search failed for {query!r}: {e}. Try a different query."
