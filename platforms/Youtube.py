import asyncio
import logging
from typing import Optional, Dict, Any
import aiohttp
from youtubesearchpython.__future__ import VideosSearch

LOGGER = logging.getLogger(__name__)

# Global persistent aiohttp session
_session: Optional[aiohttp.ClientSession] = None
API_URL = "http://127.0.0.1:8080/extract"


async def get_session() -> aiohttp.ClientSession:
    """Get or initialize the global persistent aiohttp ClientSession with TCPConnector limit=100."""
    global _session
    if _session is None or _session.closed:
        connector = aiohttp.TCPConnector(limit=100, keepalive_timeout=60)
        _session = aiohttp.ClientSession(connector=connector)
    return _session


async def close_session() -> None:
    """Close the global persistent session when shutting down."""
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None


class YouTubeAPI:
    def __init__(self, api_url: str = API_URL):
        self.api_url = api_url

    async def search_youtube(self, query: str) -> Optional[str]:
        """
        Sub-second YouTube Search: Resolves a query or title into an exact YouTube URL.
        If query is already a YouTube URL, returns it as is.
        """
        query = query.strip()
        if query.startswith("http://") or query.startswith("https://") or "youtube.com" in query or "youtu.be" in query:
            return query

        try:
            search = VideosSearch(query, limit=1)
            results = await search.next()
            if results and results.get("result"):
                video_link = results["result"][0].get("link")
                if video_link:
                    return video_link
        except Exception as e:
            LOGGER.error(f"Error during YouTube search: {e}")

        return None

    async def extract_stream(self, url_or_query: str) -> Optional[Dict[str, Any]]:
        """
        1. Resolves text query to exact YouTube URL in sub-second time.
        2. Calls local FastAPI endpoint with exact URL using persistent aiohttp session.
        """
        exact_url = await self.search_youtube(url_or_query)
        if not exact_url:
            LOGGER.error(f"Could not resolve query/URL: {url_or_query}")
            return None

        session = await get_session()
        params = {"url": exact_url}

        try:
            async with session.get(self.api_url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
                else:
                    LOGGER.error(f"API extraction error: status {resp.status}")
        except Exception as e:
            LOGGER.error(f"Failed to connect or extract from API endpoint: {e}")

        return None


# Global instance for Pyrogram / SONALI_MUSIC integration
YouTube = YouTubeAPI()
