import json
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "qwiki/1.0"
REQUEST_DELAY = 0.5
MAX_RETRIES = 3


class MediaWikiClient:
    def __init__(self):
        self._last_request_time = 0

    def _get(self, params):
        url = f"{WIKIPEDIA_API_URL}?{urlencode(params)}"

        for attempt in range(MAX_RETRIES):
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < REQUEST_DELAY:
                time.sleep(REQUEST_DELAY - elapsed)

            req = Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urlopen(req, timeout=10) as resp:
                    self._last_request_time = time.time()
                    return json.loads(resp.read())
            except HTTPError as e:
                self._last_request_time = time.time()
                if e.code == 429:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise

        raise RuntimeError(f"Wikipedia API rate limited after {MAX_RETRIES} retries")

    def search(self, query, limit=5):
        data = self._get({
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        })
        results = data.get("query", {}).get("search", [])
        return [
            {"title": r["title"], "pageid": r["pageid"], "snippet": r.get("snippet", "")}
            for r in results
        ]

    def get_extract(self, title):
        data = self._get({
            "action": "query",
            "titles": title,
            "prop": "extracts|info",
            "explaintext": "true",
            "inprop": "url",
            "format": "json",
        })
        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        return {
            "title": title,
            "extract": page.get("extract", ""),
            "url": page.get("fullurl", f"https://en.wikipedia.org/wiki/{quote(title)}"),
        }

    def page_exists(self, title):
        data = self._get({
            "action": "query",
            "titles": title,
            "format": "json",
        })
        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        return "missing" not in page and int(page.get("pageid", -1)) > 0
