import requests
from django.core.cache import cache
from django.conf import settings
from datetime import datetime
import environ
from api.utils import get_or_set_cache

TMDB_API_KEY = settings.TMDB_API_KEY
if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY is missing in .env file")

BASE_URL = "https://api.themoviedb.org/3/discover/movie"
PARAMS = {
    "include_adult": "false",
    "include_video": "false",
    "language": "en-US",
    "sort_by": "popularity.desc"
}


HEADERS = {
    "Authorization": f"Bearer {TMDB_API_KEY}",
    "accept": "application/json"
}


def fetch_movies_from_tmdb(
    max_pages: int = 3,
    language: str = "en-US"
    ) -> dict:
    """
    Fetch movies from TMDB (does not touch cache directly).

    Args:
        max_pages (int): Number of pages to fetch.
        language (str): Language code for results (default: "en-US").

    Returns:
        dict: Dictionary with aggregated movie results.
    """
    all_results = {"results": []}

    for page in range(1, max_pages + 1):
        params = {**PARAMS, "page": page, "language": language}
        resp = requests.get(BASE_URL, params=params, headers=HEADERS)

        if resp.status_code == 200:
            data = resp.json()
            all_results["results"].extend(data.get("results", []))
        else:
            # TODO: replace print with proper logging later
            print(f"[{datetime.now()}] TMDB fetch failed (page {page}): {resp.status_code}")
            print(resp.text)

    return all_results


def search_movies_from_tmdb(
    query: str,
    page: int = 1,
    language: str = "en-US",
    ttl: int = 3600
) -> dict:
    """
    Search TMDB for movies by query.
    Caches results in Redis for faster repeated access.

    Args:
        query (str): Search query string.
        page (int): Page number for results (default: 1).
        language (str): Language code for results (default: "en-US").
        ttl (int): Cache time-to-live in seconds (default: 1 hour).

    Returns:
        dict: TMDB search results or an error message.
    """
    cache_key = f"search:{language}:{query}:{page}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    url = "https://api.themoviedb.org/3/search/movie"
    params = {**PARAMS, "query": query, "page": page, "language": language}

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            cache.set(cache_key, data, ttl)
            return data
        else:
            return {
                "results": [],
                "error": f"TMDB error: {resp.status_code}"
            }
    except requests.RequestException as e:
        return {
            "results": [],
            "error": f"Request failed: {str(e)}"
        }


def get_trending_movies(
        max_pages: int = 3, language: str = "en-US", ttl: int = 60 * 60 * 24):
    """
    Cached wrapper around TMDB fetch.
    
    Args:
        max_pages (int): Number of pages to fetch from TMDB.
        language (str): Language code for movie results (default: "en-US").
        ttl (int): Time to live for cache in seconds (default: 24h).

    Returns:
        dict: Dictionary containing movie results.
    """
    cache_key = f"movies:trending:{language}:pages={max_pages}"
    return get_or_set_cache(
        cache_key,
        fetch_movies_from_tmdb,
        ttl,
        max_pages=max_pages
    )