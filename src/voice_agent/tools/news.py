
import os
import asyncio
import logging

from tavily import TavilyClient
from livekit.agents import function_tool, RunContext

logger = logging.getLogger("voiceagent.news")

_tavily_client = None


def get_tavily_client():
    global _tavily_client

    if _tavily_client is None:
        api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            raise RuntimeError("TAVILY_API_KEY is missing.")

        _tavily_client = TavilyClient(api_key=api_key)

    return _tavily_client


@function_tool()
async def search_news(
    context: RunContext,
    query: str,
    time_range: str = "day",
    max_results: int = 10,
) -> dict:
    """
    Search the internet for current news using Tavily.

    Use this for current events, breaking news,curent affairs, AI news,
    technology, business, startups, science, finance,
    India news and world news.

    time_range must be day, week, month or year.
    Use day for today's news and week for this week's news.
    Never invent search results or publication dates.
    """

    if time_range not in ("day", "week", "month", "year"):
        time_range = "day"

    max_results = max(1, min(max_results, 12))

    try:
        client = get_tavily_client()

        # Tavily's Python client is synchronous.
        # Run it in a worker thread so it doesn't block
        # the LiveKit voice event loop.
        response = await asyncio.to_thread(
            client.search,
            query=query,
            topic="news",
            time_range=time_range,
            search_depth="basic",
            max_results=max_results,
            include_answer=False,
            include_raw_content=False,
        )

        results = []

        for item in response.get("results", []):
            results.append({
                "title": item.get("title"),
                "summary": item.get("content"),
                "source_url": item.get("url"),
                "published_date": item.get("published_date"),
                "relevance_score": item.get("score"),
            })

        logger.info(
            "Tavily search completed | query=%s | results=%d",
            query,
            len(results),
        )

        logger.info(
            "[NEWS SEARCH] Tavily returned %d results",
            len(response.get("results", [])),
        )

        logger.info(
            "[NEWS SEARCH] Returning %d stories to the agent",
            len(results),
        )
        
        return {
            "query": query,
            "time_range": time_range,
            "result_count": len(results),
            "results": results,
        }

    except Exception:
        logger.exception("Tavily news search failed")
        return {
            "query": query,
            "error": "News search is temporarily unavailable.",
            "result_count": 0,
            "results": [],
        }
