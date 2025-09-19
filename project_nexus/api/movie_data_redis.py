import requests
from datetime import datetime
import environ
from api.utils import get_or_set_cache

env = environ.Env()
environ.Env.read_env(".env")

TMDB_API_KEY = env("TMDB_API_KEY")
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


def fetch_movies_from_tmdb(max_pages=3):
    """
    Fetch movies from TMDB (does not touch cache directly).
    """
    all_results = {"results": []}

    for page in range(1, max_pages + 1):
        resp = requests.get(BASE_URL, params={**PARAMS, "page": page}, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            all_results["results"].extend(data.get("results", []))
        else:
            #remember to change to logging
            print(f"[{datetime.now()}] TMDB fetch failed (page {page}): {resp.status_code}")
            print(resp.text)

    return all_results


def get_trending_movies(max_pages=3, cache_key="trending_movies"):
    """
    Cached wrapper around TMDB fetch.
    """
    return get_or_set_cache(
        cache_key, fetch_movies_from_tmdb, 60 * 60 * 24, max_pages=max_pages)