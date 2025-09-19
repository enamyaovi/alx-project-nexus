import json
import requests
from datetime import datetime
import environ

# Setup environ
env = environ.Env()
environ.Env.read_env(".env")  # make sure .env is in the same folder

TMDB_API_KEY = env("TMDB_API_KEY")
if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY is missing in .env file")

OUTPUT_FILE = "data.json"
ERROR_LOG = "errors.txt"
MAX_PAGES = 3  # manually control how many pages you want

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

# initialize structure
all_results = {"results": []}

for page in range(1, MAX_PAGES + 1):
    print(f"Fetching page {page} ...")
    try:
        resp = requests.get(BASE_URL, params={**PARAMS, "page": page}, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            all_results["results"].extend(data.get("results", []))
        else:
            with open(ERROR_LOG, "a") as f:
                f.write(f"[{datetime.now()}] Request failed. "
                        f"HTTP Status: {resp.status_code} (page {page})\n")
                f.write(resp.text + "\n")
    except Exception as e:
        with open(ERROR_LOG, "a") as f:
            f.write(f"[{datetime.now()}] Exception fetching page {page}: {e}\n")


with open(OUTPUT_FILE, "w") as f:
    json.dump(all_results, f, indent=2)

print(f"Done, Combined results written to {OUTPUT_FILE}")
